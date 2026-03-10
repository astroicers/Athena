# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: [TODO: contact email]

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
        target = await db.fetchrow(
            "SELECT id, hostname, ip_address, is_compromised FROM targets "
            "WHERE id = $1 AND operation_id = $2",
            target_id, operation_id,
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

        # Look up SSH credential from facts table
        cred_row = await db.fetchrow(
            "SELECT value FROM facts "
            "WHERE operation_id = $1 AND source_target_id = $2 "
            "AND trait = 'credential.ssh' "
            "ORDER BY collected_at DESC LIMIT 1",
            operation_id, target_id,
        )

        # Check for Metasploit root shell as fallback
        msf_row = await db.fetchrow(
            "SELECT value FROM facts "
            "WHERE operation_id = $1 AND source_target_id = $2 "
            "AND trait = 'credential.root_shell' "
            "ORDER BY collected_at DESC LIMIT 1",
            operation_id, target_id,
        )

    # Decide backend: SSH or Metasploit
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

    # Fallback: Metasploit shell session
    if msf_row:
        use_msf = True
    else:
        await websocket.send_text(json.dumps({
            "error": "No valid credential found — SSH failed and no Metasploit shell available"
        }))
        await websocket.close()
        return

    if use_msf:
        await _run_msf_terminal(websocket, ip_address, hostname)


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
        except Exception:
            pass
        logger.info("SSH terminal session closed for %s", hostname)


async def _run_msf_terminal(
    websocket: WebSocket, target_ip: str, hostname: str
) -> None:
    """Run interactive terminal via Metasploit shell session."""
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

    # Find session for this target
    shell = None
    sid = None
    for s_id, info in client.sessions.list.items():
        if info.get("target_host") == target_ip:
            shell = client.sessions.session(s_id)
            sid = s_id
            break

    if shell is None:
        await websocket.send_text(json.dumps({
            "error": f"No active Metasploit session for {target_ip}"
        }))
        await websocket.close()
        return

    logger.info("Terminal using Metasploit session %s for %s", sid, target_ip)
    await websocket.send_text(json.dumps({
        "output": f"Connected to {hostname} ({target_ip}) via Metasploit shell (session {sid})\r\n",
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
                await websocket.send_text(json.dumps({"error": "Command too long (max 1024 chars)"}))
                continue
            if _is_dangerous(cmd):
                await websocket.send_text(json.dumps({"error": "Command refused: potentially destructive operation"}))
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
                await websocket.send_text(json.dumps({"error": f"Shell error: {exc}"}))
    except WebSocketDisconnect:
        pass
    finally:
        logger.info("Metasploit terminal session closed for %s (session %s)", hostname, sid)
