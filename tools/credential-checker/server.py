"""credential-checker MCP Server for Athena.

Exposes SSH, RDP, and WinRM credential testing as MCP tools.
Uses a protocol handler registry so adding new protocols requires
only a handler function + a one-line @mcp.tool() wrapper.

Returns JSON with {"facts": [{"trait": ..., "value": ...}], "raw_output": "..."}
to integrate with Athena's fact collection pipeline.
"""

from __future__ import annotations

import asyncio
import json
from typing import Callable, Awaitable

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

# Allow Docker internal network hostnames (mcp-credential-checker, etc.)
_security = TransportSecuritySettings(
    enable_dns_rebinding_protection=False,
)

mcp = FastMCP("athena-credential-checker", transport_security=_security)

# ---------------------------------------------------------------------------
# Protocol handler registry
# ---------------------------------------------------------------------------
_HANDLERS: dict[str, Callable[..., Awaitable[dict]]] = {}


def _register(protocol: str):
    """Decorator to register a credential-check handler for *protocol*."""
    def decorator(fn: Callable[..., Awaitable[dict]]):
        _HANDLERS[protocol] = fn
        return fn
    return decorator


async def _check_credential(
    protocol: str, target: str, username: str, password: str,
    port: int, timeout: int,
) -> dict:
    """Unified entry point — dispatches to the registered handler."""
    handler = _HANDLERS[protocol]
    return await handler(target, username, password, port, timeout)


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------

@_register("ssh")
async def _ssh_handler(
    target: str, username: str, password: str, port: int, timeout: int,
) -> dict:
    import asyncssh

    try:
        async with asyncssh.connect(
            target, port=port, username=username, password=password,
            known_hosts=None, connect_timeout=timeout,
        ) as conn:
            result = await conn.run("id", timeout=5)
            uid_output = result.stdout.strip() if result.stdout else ""
            return {
                "facts": [{
                    "trait": "credential.ssh",
                    "value": f"{username}:{password}@{target}:{port} (uid: {uid_output})",
                }],
                "raw_output": f"SSH auth success: {username}@{target}:{port} — {uid_output}",
            }
    except asyncssh.PermissionDenied:
        return {"facts": [], "raw_output": f"SSH auth_failure: {username}@{target}:{port}"}
    except Exception as exc:
        return {"facts": [], "raw_output": f"SSH connection error: {target}:{port} — {exc}"}


@_register("rdp")
async def _rdp_handler(
    target: str, username: str, password: str, port: int, timeout: int,
) -> dict:
    cmd = [
        "xfreerdp3", f"/v:{target}:{port}", f"/u:{username}", f"/p:{password}",
        "/auth-only", "/cert:ignore", f"/timeout:{timeout * 1000}",
    ]
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        await asyncio.wait_for(proc.communicate(), timeout=timeout + 5)

        if proc.returncode == 0:
            return {
                "facts": [{
                    "trait": "credential.rdp",
                    "value": f"{username}:{password}@{target}:{port}",
                }],
                "raw_output": f"RDP auth success: {username}@{target}:{port}",
            }
        return {"facts": [], "raw_output": f"RDP auth_failure: {username}@{target}:{port} (exit={proc.returncode})"}
    except asyncio.TimeoutError:
        return {"facts": [], "raw_output": f"RDP timeout: {target}:{port}"}
    except Exception as exc:
        return {"facts": [], "raw_output": f"RDP connection error: {target}:{port} — {exc}"}


@_register("winrm")
async def _winrm_handler(
    target: str, username: str, password: str, port: int, timeout: int,
) -> dict:
    def _check():
        import winrm  # noqa: deferred import — pywinrm is sync
        scheme = "https" if port == 5986 else "http"
        session = winrm.Session(
            f"{scheme}://{target}:{port}/wsman",
            auth=(username, password), transport="ntlm",
            read_timeout_sec=timeout, operation_timeout_sec=timeout,
        )
        result = session.run_ps("whoami")
        return result.status_code, result.std_out.decode(errors="ignore").strip()

    try:
        loop = asyncio.get_running_loop()
        status_code, whoami = await asyncio.wait_for(
            loop.run_in_executor(None, _check), timeout=timeout + 5,
        )
        if status_code == 0 and whoami:
            return {
                "facts": [{
                    "trait": "credential.winrm",
                    "value": f"{username}:{password}@{target}:{port}",
                }],
                "raw_output": f"WinRM auth success: {username}@{target}:{port} (whoami: {whoami})",
            }
        return {"facts": [], "raw_output": f"WinRM auth_failure: {username}@{target}:{port} (status={status_code})"}
    except asyncio.TimeoutError:
        return {"facts": [], "raw_output": f"WinRM timeout: {target}:{port}"}
    except Exception as exc:
        return {"facts": [], "raw_output": f"WinRM connection error: {target}:{port} — {exc}"}


# ---------------------------------------------------------------------------
# MCP tool wrappers (thin — one line each)
# ---------------------------------------------------------------------------

@mcp.tool()
async def ssh_credential_check(
    target: str, username: str, password: str, port: int = 22, timeout: int = 10,
) -> str:
    """Test SSH credentials against a target host.

    Args:
        target: Target IP address or hostname.
        username: SSH username to test.
        password: SSH password to test.
        port: SSH port (default 22).
        timeout: Connection timeout in seconds.

    Returns:
        JSON with facts: credential.ssh if successful, empty if auth fails.
    """
    return json.dumps(await _check_credential("ssh", target, username, password, port, timeout))


@mcp.tool()
async def rdp_credential_check(
    target: str, username: str, password: str, port: int = 3389, timeout: int = 10,
) -> str:
    """Test RDP credentials against a target host using xfreerdp3 /auth-only.

    Args:
        target: Target IP address or hostname.
        username: RDP username to test.
        password: RDP password to test.
        port: RDP port (default 3389).
        timeout: Connection timeout in seconds.

    Returns:
        JSON with facts: credential.rdp if successful, empty if auth fails.
    """
    return json.dumps(await _check_credential("rdp", target, username, password, port, timeout))


@mcp.tool()
async def winrm_credential_check(
    target: str, username: str, password: str, port: int = 5985, timeout: int = 10,
) -> str:
    """Test WinRM credentials against a target host via NTLM auth.

    Args:
        target: Target IP address or hostname.
        username: WinRM username to test.
        password: WinRM password to test.
        port: WinRM port (default 5985 for HTTP, 5986 for HTTPS).
        timeout: Connection timeout in seconds.

    Returns:
        JSON with facts: credential.winrm if successful, empty if auth fails.
    """
    return json.dumps(await _check_credential("winrm", target, username, password, port, timeout))


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
