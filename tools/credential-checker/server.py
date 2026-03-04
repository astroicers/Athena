"""credential-checker MCP Server for Athena.

Exposes SSH credential testing as MCP tools.
Returns JSON with {"facts": [{"trait": ..., "value": ...}]}
to integrate with Athena's fact collection pipeline.
"""

import json

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("athena-credential-checker")


@mcp.tool()
async def ssh_credential_check(
    target: str,
    username: str,
    password: str,
    port: int = 22,
    timeout: int = 10,
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
    import asyncssh

    try:
        async with asyncssh.connect(
            target,
            port=port,
            username=username,
            password=password,
            known_hosts=None,
            connect_timeout=timeout,
        ) as conn:
            result = await conn.run("id", timeout=5)
            uid_output = result.stdout.strip() if result.stdout else ""

            return json.dumps({
                "facts": [
                    {
                        "trait": "credential.ssh",
                        "value": f"{username}:{password}@{target}:{port} (uid: {uid_output})",
                    }
                ],
                "raw_output": f"SSH auth success: {username}@{target}:{port} — {uid_output}",
            })

    except asyncssh.PermissionDenied:
        return json.dumps({
            "facts": [],
            "raw_output": f"SSH auth_failure: {username}@{target}:{port}",
        })
    except Exception as exc:
        return json.dumps({
            "facts": [],
            "raw_output": f"SSH connection error: {target}:{port} — {exc}",
        })


if __name__ == "__main__":
    mcp.run()
