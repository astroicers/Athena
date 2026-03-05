"""attack-executor MCP Server for Athena.

Executes MITRE ATT&CK techniques via SSH or WinRM on target hosts.
Maintains a persistent SSH session pool for efficient multi-step operations.

Returns JSON with {"facts": [...], "raw_output": "...", "success": bool}
to integrate with Athena's fact collection pipeline.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import re
import time
from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

logger = logging.getLogger(__name__)

# Allow Docker internal network hostnames (mcp-attack-executor, etc.)
_security = TransportSecuritySettings(
    enable_dns_rebinding_protection=False,
)

mcp = FastMCP("athena-attack-executor", transport_security=_security)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
SESSION_IDLE_TIMEOUT_SEC = int(os.environ.get("SESSION_IDLE_TIMEOUT_SEC", "300"))

# ---------------------------------------------------------------------------
# Technique → command mappings
# ---------------------------------------------------------------------------

# SSH (Linux) technique executors
TECHNIQUE_EXECUTORS: dict[str, str] = {
    "T1592": "uname -a && id && cat /etc/os-release",
    "T1046": "netstat -tulnp 2>/dev/null || ss -tulnp 2>/dev/null",
    "T1059.004": "bash -c 'id && whoami && hostname'",
    "T1003.001": "cat /etc/shadow 2>/dev/null || echo 'NO_SHADOW_ACCESS'",
    "T1087": "cat /etc/passwd | cut -d: -f1,3,7",
    "T1083": "find / -name '*.conf' -readable 2>/dev/null | head -20",
    "T1190": "curl -sI http://localhost/ 2>/dev/null | head -5",
    "T1595.001": "echo 'NMAP_LOCAL_ONLY'",
    "T1595.002": "echo 'NMAP_LOCAL_ONLY'",
    "T1021.004": "id && hostname",
    "T1078.001": "id && cat /etc/passwd | grep -v nologin | grep -v false",
    "T1110.001": "echo 'HANDLED_BY_INITIAL_ACCESS_ENGINE'",
    "T1110.003": "echo 'HANDLED_BY_INITIAL_ACCESS_ENGINE'",
    "T1021.004_priv": "sudo -l 2>/dev/null && sudo -n id 2>/dev/null",
    "T1021.004_recon": "id && hostname && ip addr show && cat /etc/hosts",
    "T1560.001": "tar czf /tmp/.bundle.tgz /etc/passwd /etc/shadow 2>/dev/null && echo BUNDLED",
    "T1105": "which curl wget python3 nc 2>/dev/null | head -5",
    "T1053.003": "ls -la /etc/cron.d/ 2>/dev/null | head -5",
    "T1543.002": "systemctl list-units --type=service --state=running 2>/dev/null | head -10",
    "T1136.001": "id; getent passwd | cut -d: -f1,3,7 | head -10",
}

# WinRM (Windows) technique executors — PowerShell commands
WINRM_TECHNIQUE_EXECUTORS: dict[str, str] = {
    "T1021.001": "whoami; hostname; ipconfig /all | Select-String 'IPv4'",
    "T1053.005": "schtasks /query /fo CSV /nh 2>$null | Select-Object -First 10",
    "T1059.001": "whoami; $env:COMPUTERNAME; Get-Process | Select-Object -First 5 Name,Id",
    "T1087.001": "Get-LocalUser | Select-Object Name,Enabled,LastLogon",
    "T1083": "Get-ChildItem C:\\Users -ErrorAction SilentlyContinue | Select-Object Name",
    "T1016": "Get-NetIPAddress | Select-Object IPAddress,InterfaceAlias",
    "T1049": "netstat -ano | Select-String 'LISTENING' | Select-Object -First 10",
    # AD discovery & privesc
    "T1069.002": "Get-ADGroupMember 'Domain Admins' -ErrorAction SilentlyContinue | Select-Object Name,SamAccountName",
    "T1558.003": 'Get-ADUser -Filter {ServicePrincipalName -ne "$null"} -Properties ServicePrincipalName -ErrorAction SilentlyContinue | Select-Object SamAccountName,ServicePrincipalName',
    "T1003.001_win": "[Security.Principal.WindowsIdentity]::GetCurrent().Groups | ForEach-Object { $_.Translate([Security.Principal.NTAccount]).Value } | Select-Object -First 10",
    "T1003.003": "reg query 'HKLM\\SAM' 2>$null; if ($?) { 'SAM_ACCESSIBLE' } else { 'SAM_DENIED' }",
    "T1018": "Get-ADComputer -Filter * -Properties Name,OperatingSystem -ErrorAction SilentlyContinue | Select-Object -First 20 Name,OperatingSystem",
}

TECHNIQUE_FACT_TRAITS: dict[str, list[str]] = {
    "T1592": ["host.os", "host.user"],
    "T1046": ["service.open_port"],
    "T1059.004": ["host.process"],
    "T1003.001": ["credential.hash"],
    "T1087": ["host.user"],
    "T1083": ["host.file"],
    "T1190": ["service.web"],
    "T1595.001": ["network.host.ip"],
    "T1595.002": ["vuln.cve"],
    "T1021.004": ["host.session"],
    "T1078.001": ["host.user"],
    "T1110.001": ["credential.ssh"],
    "T1110.003": ["credential.ssh"],
    "T1021.004_priv": ["host.privilege"],
    "T1021.004_recon": ["host.os", "host.network"],
    "T1560.001": ["host.file"],
    "T1105": ["host.binary"],
    "T1053.003": ["host.persistence"],
    "T1543.002": ["host.service"],
    "T1136.001": ["host.user"],
}

# ---------------------------------------------------------------------------
# Credential parsers
# ---------------------------------------------------------------------------


def _parse_credential(cred_value: str) -> tuple[str, str, str, int]:
    """Parse 'user:pass@host:port' → (user, pass, host, port)."""
    if cred_value.startswith("uid=") or "\n" in cred_value:
        raise ValueError(f"Value does not look like a credential: {cred_value[:80]}")
    host = ""
    port = 22
    if "@" in cred_value:
        user_pass, host_port = cred_value.rsplit("@", 1)
        if ":" in host_port:
            host, port_str = host_port.rsplit(":", 1)
            try:
                port = int(port_str)
            except ValueError:
                pass
        else:
            host = host_port
    else:
        user_pass = cred_value
    if ":" in user_pass:
        user, password = user_pass.split(":", 1)
    else:
        user, password = user_pass, ""
    return user, password, host, port


def _parse_key_credential(target: str) -> tuple[str, str, int, str]:
    """Parse 'user@host:port#<base64_private_key>' → (user, host, port, key_content)."""
    try:
        conn_part, key_b64 = target.split("#", 1)
        key_content = base64.b64decode(key_b64).decode()
        user, hostport = conn_part.split("@", 1)
        if ":" in hostport:
            host, port_str = hostport.rsplit(":", 1)
            port = int(port_str)
        else:
            host, port = hostport, 22
        return user, host, port, key_content
    except (ValueError, UnicodeDecodeError) as exc:
        raise ValueError(f"Invalid ssh_key credential format: {exc}") from exc
    except Exception as exc:
        raise ValueError(f"Invalid ssh_key credential format: {exc}") from exc


def _parse_winrm_credential(target: str) -> tuple[str, str, str, int]:
    """Parse 'user:pass@host:port' for WinRM. Port defaults to 5985."""
    try:
        userpass, hostport = target.rsplit("@", 1)
        username, password = userpass.split(":", 1)
        if ":" in hostport:
            host, port_str = hostport.rsplit(":", 1)
            port = int(port_str)
        else:
            host, port = hostport, 5985
        return username, password, host, port
    except (ValueError, AttributeError) as exc:
        raise ValueError(f"Invalid WinRM credential format: {exc}") from exc


# ---------------------------------------------------------------------------
# Fact extraction
# ---------------------------------------------------------------------------


def _parse_stdout_to_facts(
    mitre_id: str,
    stdout: str,
    source: str = "attack_executor",
    output_parser: str | None = None,
) -> list[dict[str, Any]]:
    """Extract facts from command stdout based on technique type."""
    if not stdout.strip():
        return []
    traits = TECHNIQUE_FACT_TRAITS.get(mitre_id, [])
    if not traits:
        return []

    if output_parser == "json":
        try:
            parsed = json.loads(stdout)
            value = json.dumps(parsed)[:500]
        except Exception:
            value = stdout.splitlines()[0].strip()[:500]
    elif output_parser and output_parser != "first_line":
        m = re.search(output_parser, stdout)
        value = m.group(1)[:500] if m and m.lastindex else stdout.splitlines()[0].strip()[:500]
    else:
        value = stdout.splitlines()[0].strip()[:500]

    return [{"trait": t, "value": value, "score": 1, "source": source} for t in traits]


# ---------------------------------------------------------------------------
# Persistent SSH session pool
# ---------------------------------------------------------------------------

_SESSION_POOL: dict[tuple[str, str], Any] = {}
_SESSION_LOCKS: dict[tuple[str, str], asyncio.Lock] = {}
_SESSION_LAST_USED: dict[tuple[str, str], float] = {}
_cleanup_task: asyncio.Task | None = None


async def _cleanup_idle_sessions() -> None:
    """Background task: close sessions idle for longer than SESSION_IDLE_TIMEOUT_SEC."""
    while True:
        await asyncio.sleep(60)
        now = time.monotonic()
        keys_to_remove = [
            k for k, last in _SESSION_LAST_USED.items()
            if (now - last) > SESSION_IDLE_TIMEOUT_SEC
        ]
        for key in keys_to_remove:
            conn = _SESSION_POOL.pop(key, None)
            _SESSION_LOCKS.pop(key, None)
            _SESSION_LAST_USED.pop(key, None)
            if conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass
        if keys_to_remove:
            logger.info("Cleaned up %d idle SSH sessions", len(keys_to_remove))


def _ensure_cleanup_task() -> None:
    """Start the idle session cleanup task if not already running."""
    global _cleanup_task
    if _cleanup_task is None or _cleanup_task.done():
        _cleanup_task = asyncio.create_task(_cleanup_idle_sessions())


# ---------------------------------------------------------------------------
# Execution functions
# ---------------------------------------------------------------------------


async def _execute_direct_ssh(
    technique_id: str,
    credential: str,
    output_parser: str,
) -> dict:
    """One-shot SSH execution (new connection per call)."""
    import asyncssh

    command = TECHNIQUE_EXECUTORS.get(technique_id)
    if not command:
        return {"facts": [], "raw_output": "", "success": False,
                "error": f"No SSH executor for technique {technique_id}"}

    user, password, host, port = _parse_credential(credential)
    if not host:
        return {"facts": [], "raw_output": "", "success": False,
                "error": "Could not parse host from credential"}

    command = command.replace("{target_ip}", host)

    try:
        async with asyncssh.connect(
            host, port=port, username=user, password=password,
            known_hosts=None, connect_timeout=15,
        ) as conn:
            result = await conn.run(command, timeout=30)
            stdout = result.stdout or ""
            stderr = result.stderr or ""
            success = result.exit_status == 0

        facts = _parse_stdout_to_facts(
            technique_id, stdout, output_parser=output_parser or None,
        )
        output = stdout if stdout else stderr
        logger.info("DirectSSH executed %s on %s → exit=%s", technique_id, host, result.exit_status)

        return {
            "facts": facts,
            "raw_output": output[:2000],
            "success": success,
            "error": stderr[:500] if not success else None,
        }
    except Exception as exc:
        logger.warning("DirectSSH execution failed for %s: %s", technique_id, exc)
        return {"facts": [], "raw_output": "", "success": False, "error": str(exc)[:500]}


async def _execute_persistent_ssh(
    technique_id: str,
    credential: str,
    output_parser: str,
    session_key: str,
) -> dict:
    """Persistent SSH execution (pooled connection)."""
    import asyncssh

    command = TECHNIQUE_EXECUTORS.get(technique_id)
    if not command:
        return {"facts": [], "raw_output": "", "success": False,
                "error": f"No SSH executor for technique {technique_id}"}

    # Parse host for command substitution
    if "#" in credential:
        conn_part, _ = credential.split("#", 1)
        _, hostport = conn_part.split("@", 1)
        host = hostport.rsplit(":", 1)[0] if ":" in hostport else hostport
    else:
        _, _, host, _ = _parse_credential(credential)

    if not host:
        return {"facts": [], "raw_output": "", "success": False,
                "error": "Could not parse host from credential"}

    command = command.replace("{target_ip}", host)
    pool_key = (session_key, credential)

    _ensure_cleanup_task()

    try:
        if pool_key not in _SESSION_LOCKS:
            _SESSION_LOCKS[pool_key] = asyncio.Lock()
        lock = _SESSION_LOCKS[pool_key]

        async with lock:
            conn = _SESSION_POOL.get(pool_key)
            if conn is None:
                if "#" in credential:
                    user, host, port, key_content = _parse_key_credential(credential)
                    conn = await asyncssh.connect(
                        host, port=port, username=user,
                        client_keys=[asyncssh.import_private_key(key_content)],
                        known_hosts=None, connect_timeout=15,
                    )
                else:
                    user, password, host, port = _parse_credential(credential)
                    conn = await asyncssh.connect(
                        host, port=port, username=user, password=password,
                        known_hosts=None, connect_timeout=15,
                        keepalive_interval=30, keepalive_count_max=5,
                    )
                _SESSION_POOL[pool_key] = conn
                logger.info("PersistentSSH: new session for %s (pool size=%d)", host, len(_SESSION_POOL))
            else:
                logger.debug("PersistentSSH: reusing session for %s", host)

        _SESSION_LAST_USED[pool_key] = time.monotonic()

        result = await conn.run(command, timeout=30)
        stdout = result.stdout or ""
        stderr = result.stderr or ""
        success = result.exit_status == 0

        facts = _parse_stdout_to_facts(
            technique_id, stdout, source="persistent_ssh",
            output_parser=output_parser or None,
        )
        output = stdout if stdout else stderr
        logger.info("PersistentSSH executed %s on %s → exit=%s", technique_id, host, result.exit_status)

        return {
            "facts": facts,
            "raw_output": output[:2000],
            "success": success,
            "error": stderr[:500] if not success else None,
        }

    except Exception as exc:
        stale_conn = _SESSION_POOL.pop(pool_key, None)
        _SESSION_LAST_USED.pop(pool_key, None)
        if stale_conn is not None:
            try:
                stale_conn.close()
            except Exception:
                pass
        logger.warning("PersistentSSH execution failed for %s: %s", technique_id, exc)
        return {"facts": [], "raw_output": "", "success": False, "error": str(exc)[:500]}


async def _execute_winrm(
    technique_id: str,
    credential: str,
    output_parser: str,
) -> dict:
    """WinRM execution via pywinrm in thread executor."""
    # Check both SSH and WinRM technique maps for the command
    command = WINRM_TECHNIQUE_EXECUTORS.get(technique_id)
    if not command:
        return {"facts": [], "raw_output": "", "success": False,
                "error": f"No WinRM executor for technique {technique_id}"}

    try:
        username, password, host, port = _parse_winrm_credential(credential)
    except ValueError as exc:
        return {"facts": [], "raw_output": "", "success": False, "error": str(exc)}

    try:
        import winrm

        session = winrm.Session(
            f"http://{host}:{port}/wsman",
            auth=(username, password),
            transport="ntlm",
            read_timeout_sec=60,
            operation_timeout_sec=60,
        )
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(None, lambda: session.run_ps(command))
        stdout = response.std_out.decode(errors="ignore").strip()
        stderr = response.std_err.decode(errors="ignore").strip()
        success = response.status_code == 0

        facts = _parse_stdout_to_facts(
            technique_id, stdout, source="winrm",
            output_parser=output_parser or None,
        )

        return {
            "facts": facts,
            "raw_output": (stdout or stderr)[:2000],
            "success": success,
            "error": stderr[:500] if not success else None,
        }
    except Exception as exc:
        logger.warning("WinRM execution failed for %s on %s: %s", technique_id, host, exc)
        return {"facts": [], "raw_output": "", "success": False, "error": str(exc)[:500]}


# ---------------------------------------------------------------------------
# MCP tools
# ---------------------------------------------------------------------------


@mcp.tool()
async def execute_technique(
    technique_id: str,
    credential: str,
    protocol: str = "ssh",
    output_parser: str = "",
    persistent_session_key: str = "",
) -> str:
    """Execute a MITRE ATT&CK technique on a target via SSH or WinRM.

    Args:
        technique_id: MITRE ATT&CK technique ID (e.g. "T1592", "T1069.002").
        credential: Credential string. SSH: "user:pass@host:port" or
                    "user@host:port#<base64key>". WinRM: "user:pass@host:port".
        protocol: Execution protocol — "ssh" or "winrm".
        output_parser: How to parse stdout — "" or "first_line" (default),
                       "json", or a regex pattern.
        persistent_session_key: If provided, use persistent SSH session pool
                                keyed by this value (typically operation_id).

    Returns:
        JSON string: {"facts": [...], "raw_output": "...", "success": bool}
    """
    if protocol == "winrm":
        result = await _execute_winrm(technique_id, credential, output_parser)
    elif persistent_session_key:
        result = await _execute_persistent_ssh(
            technique_id, credential, output_parser, persistent_session_key,
        )
    else:
        result = await _execute_direct_ssh(technique_id, credential, output_parser)

    return json.dumps(result)


@mcp.tool()
async def close_sessions(session_key: str) -> str:
    """Close all pooled SSH sessions for a given session key (operation_id).

    Args:
        session_key: The key used when creating persistent sessions
                     (typically the operation_id).

    Returns:
        JSON string: {"closed": <count>}
    """
    keys_to_remove = [k for k in _SESSION_POOL if k[0] == session_key]
    for key in keys_to_remove:
        conn = _SESSION_POOL.pop(key)
        _SESSION_LOCKS.pop(key, None)
        _SESSION_LAST_USED.pop(key, None)
        try:
            conn.close()
        except Exception:
            pass
    if keys_to_remove:
        logger.info("Closed %d sessions for key %s", len(keys_to_remove), session_key)
    return json.dumps({"closed": len(keys_to_remove)})


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--transport", default="stdio", choices=["stdio", "sse", "streamable-http"])
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()

    mcp.settings.host = args.host
    mcp.settings.port = args.port
    mcp.run(transport=args.transport)
