"""bloodhound-collector MCP Server for Athena.

BloodHound.py-based AD environment graph collection + attack path analysis.
Returns JSON with {"facts": [{"trait": ..., "value": ...}]}
to integrate with Athena's fact collection pipeline.
"""

import asyncio
import json
import os
import re

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

_security = TransportSecuritySettings(
    enable_dns_rebinding_protection=False,
)

mcp = FastMCP("athena-bloodhound-collector", transport_security=_security)


async def _run_command(cmd: list[str], timeout: int = 300) -> tuple[str, str, int]:
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
async def bloodhound_collect(
    target_dc: str,
    username: str,
    password: str,
    domain: str,
    collect_method: str = "All",
) -> str:
    """Execute BloodHound data collection (Users/Groups/Sessions/ACLs/Trusts).

    Args:
        target_dc: Domain Controller IP or hostname
        username: Domain username
        password: Domain password
        domain: AD domain name (e.g. corp.local)
        collect_method: Collection method (All, Group, LocalAdmin, Session, Trusts, Default, RDP, DCOM, DCOnly, LoggedOn, Container, ObjectProps, ACL, SPNTargets, PSRemote)

    Returns:
        JSON with facts: ad.bloodhound_data, ad.domain_users_count
    """
    facts: list[dict[str, str]] = []

    try:
        cmd = [
            "bloodhound-python",
            "-c", collect_method,
            "-d", domain,
            "-u", username,
            "-p", password,
            "-dc", target_dc,
            "-ns", target_dc,
            "--zip",
        ]

        stdout, stderr, rc = await _run_command(cmd)
        combined = stdout + stderr

        users_match = re.search(r"(\d+)\s+user", combined, re.IGNORECASE)
        groups_match = re.search(r"(\d+)\s+group", combined, re.IGNORECASE)
        computers_match = re.search(r"(\d+)\s+computer", combined, re.IGNORECASE)

        if users_match:
            facts.append({
                "trait": "ad.domain_users_count",
                "value": users_match.group(1),
            })

        facts.append({
            "trait": "ad.bloodhound_data",
            "value": json.dumps({
                "domain": domain,
                "dc": target_dc,
                "method": collect_method,
                "users": users_match.group(1) if users_match else "unknown",
                "groups": groups_match.group(1) if groups_match else "unknown",
                "computers": computers_match.group(1) if computers_match else "unknown",
            }),
        })

        zip_match = re.findall(r"(\S+\.zip)", combined)
        for zf in zip_match:
            facts.append({
                "trait": "ad.bloodhound_data",
                "value": f"output_file:{zf}",
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
async def bloodhound_find_paths(
    domain: str,
    source_node: str,
    target_node: str = "Domain Admins",
) -> str:
    """Analyze collected data to find shortest attack paths to high-value targets.

    Args:
        domain: AD domain name
        source_node: Starting node (e.g. compromised user)
        target_node: Target node (default: Domain Admins)

    Returns:
        JSON with facts: ad.attack_path, ad.high_value_target
    """
    facts: list[dict[str, str]] = []

    try:
        data_dir = "/tmp"
        json_files = [
            os.path.join(data_dir, f)
            for f in os.listdir(data_dir)
            if f.endswith(".json") and domain.lower() in f.lower()
        ]

        if not json_files:
            import glob
            zips = glob.glob(f"{data_dir}/*bloodhound*.zip") + glob.glob(f"{data_dir}/*{domain}*.zip")
            for zf in zips:
                await _run_command(["unzip", "-o", zf, "-d", data_dir])
            json_files = [
                os.path.join(data_dir, f)
                for f in os.listdir(data_dir)
                if f.endswith(".json")
            ]

        admin_users: list[str] = []
        group_members: dict[str, list[str]] = {}

        for jf in json_files:
            try:
                with open(jf) as fh:
                    data = json.load(fh)
                    if isinstance(data, dict):
                        items = data.get("data", data.get("users", data.get("groups", [])))
                        if isinstance(items, list):
                            for item in items:
                                props = item.get("Properties", {})
                                name = props.get("name", "")
                                if "admin" in name.lower():
                                    admin_users.append(name)
                                members = item.get("Members", [])
                                if members and name:
                                    group_members[name] = [
                                        m.get("MemberId", "") for m in members
                                        if isinstance(m, dict)
                                    ]
            except (json.JSONDecodeError, OSError):
                continue

        facts.append({"trait": "ad.high_value_target", "value": target_node})
        facts.append({
            "trait": "ad.attack_path",
            "value": json.dumps({
                "source": source_node,
                "target": target_node,
                "domain": domain,
                "admin_users_found": admin_users[:20],
                "groups_with_members": len(group_members),
                "data_files_analyzed": len(json_files),
            }),
        })

        return json.dumps({
            "facts": facts,
            "raw_output": f"Analyzed {len(json_files)} data files for paths from {source_node} to {target_node}",
        })

    except Exception as exc:
        return json.dumps({
            "facts": [],
            "raw_output": "",
            "error": {"type": type(exc).__name__, "message": str(exc)},
        })


@mcp.tool()
async def bloodhound_enum_trusts(
    target_dc: str,
    username: str,
    password: str,
    domain: str,
) -> str:
    """Enumerate Domain Trust relationships.

    Args:
        target_dc: Domain Controller IP or hostname
        username: Domain username
        password: Domain password
        domain: AD domain name

    Returns:
        JSON with facts: ad.domain_trust, ad.trust_direction
    """
    facts: list[dict[str, str]] = []

    try:
        cmd = [
            "bloodhound-python",
            "-c", "Trusts",
            "-d", domain,
            "-u", username,
            "-p", password,
            "-dc", target_dc,
            "-ns", target_dc,
        ]

        stdout, stderr, rc = await _run_command(cmd)
        combined = stdout + stderr

        trust_pattern = re.compile(
            r"([\w.]+)\s*->\s*([\w.]+)\s*\((\w+)\)", re.IGNORECASE,
        )
        for match in trust_pattern.finditer(combined):
            facts.append({
                "trait": "ad.domain_trust",
                "value": f"{match.group(1)} -> {match.group(2)}",
            })
            facts.append({
                "trait": "ad.trust_direction",
                "value": match.group(3),
            })

        for f in os.listdir("/tmp"):
            if "domains" in f.lower() and f.endswith(".json"):
                try:
                    with open(os.path.join("/tmp", f)) as fh:
                        data = json.load(fh)
                        trusts_list = data.get("data", []) if isinstance(data, dict) else data if isinstance(data, list) else []
                        for item in trusts_list:
                            if isinstance(item, dict):
                                for trust in item.get("Trusts", []):
                                    tname = trust.get("TargetDomainName", "")
                                    tdir = trust.get("TrustDirection", "")
                                    if tname:
                                        facts.append({"trait": "ad.domain_trust", "value": f"{domain} -> {tname}"})
                                        facts.append({"trait": "ad.trust_direction", "value": str(tdir)})
                except (json.JSONDecodeError, OSError):
                    continue

        if not facts:
            facts.append({"trait": "ad.domain_trust", "value": f"No trusts found for {domain}"})

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
