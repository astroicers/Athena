"""osint-recon MCP Server for Athena.

Exposes subdomain enumeration and DNS resolution as MCP tools.
Returns JSON with {"facts": [{"trait": ..., "value": ...}]}
to integrate with Athena's fact collection pipeline.
"""

import asyncio
import json

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

# Allow Docker internal network hostnames (mcp-osint, etc.)
_security = TransportSecuritySettings(
    enable_dns_rebinding_protection=False,
)

mcp = FastMCP("athena-osint-recon", transport_security=_security)


@mcp.tool()
async def crtsh_query(domain: str) -> str:
    """Query crt.sh certificate transparency logs for subdomains.

    Args:
        domain: The apex domain to enumerate (e.g., "example.com").

    Returns:
        JSON with facts: osint.subdomain for each discovered subdomain.
    """
    import httpx

    try:
        url = f"https://crt.sh/?q=%.{domain}&output=json"
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                return json.dumps({
                    "facts": [],
                    "raw_output": f"crt.sh returned status {resp.status_code}",
                })
            data = resp.json()
    except Exception as exc:
        return json.dumps({
            "facts": [],
            "raw_output": f"crt.sh query failed: {exc}",
        })

    subdomains: set[str] = set()
    for entry in data:
        name_value = entry.get("name_value", "")
        for name in name_value.split("\n"):
            name = name.strip().lower()
            if name.endswith(f".{domain}") and not name.startswith("*"):
                subdomains.add(name)

    facts = [
        {"trait": "osint.subdomain", "value": sub}
        for sub in sorted(subdomains)
    ]
    return json.dumps({
        "facts": facts,
        "raw_output": f"Found {len(subdomains)} subdomains via crt.sh",
    })


@mcp.tool()
async def subfinder_query(domain: str) -> str:
    """Run subfinder binary for subdomain enumeration.

    Args:
        domain: The apex domain to enumerate.

    Returns:
        JSON with facts: osint.subdomain for each discovered subdomain.
        Returns empty facts if subfinder is not installed.
    """
    try:
        proc = await asyncio.create_subprocess_exec(
            "subfinder", "-d", domain, "-silent",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=60)
        lines = stdout.decode(errors="ignore").strip().split("\n")
        subdomains = sorted(set(
            ln.strip().lower()
            for ln in lines
            if ln.strip() and domain in ln
        ))
    except FileNotFoundError:
        return json.dumps({
            "facts": [],
            "raw_output": "subfinder not available",
        })
    except asyncio.TimeoutError:
        return json.dumps({
            "facts": [],
            "raw_output": f"subfinder timed out for {domain}",
        })
    except Exception as exc:
        return json.dumps({
            "facts": [],
            "raw_output": f"subfinder error: {exc}",
        })

    facts = [
        {"trait": "osint.subdomain", "value": sub}
        for sub in subdomains
    ]
    return json.dumps({
        "facts": facts,
        "raw_output": f"Found {len(subdomains)} subdomains via subfinder",
    })


@mcp.tool()
async def dns_resolve(subdomains: str) -> str:
    """DNS A/AAAA resolution for a comma-separated list of subdomains.

    Args:
        subdomains: Comma-separated list of subdomains to resolve.

    Returns:
        JSON with facts: osint.resolved_ip as "subdomain:ip" pairs.
    """
    try:
        import dns.asyncresolver
        import dns.exception
    except ImportError:
        return json.dumps({
            "facts": [],
            "raw_output": "dnspython not installed — DNS resolution unavailable",
        })

    sub_list = [s.strip() for s in subdomains.split(",") if s.strip()]
    resolver = dns.asyncresolver.Resolver()
    resolver.timeout = 3
    resolver.lifetime = 5

    result: dict[str, list[str]] = {}
    semaphore = asyncio.Semaphore(20)

    async def resolve_one(sub: str) -> None:
        ips: list[str] = []
        for rdtype in ("A", "AAAA"):
            try:
                async with semaphore:
                    answers = await resolver.resolve(sub, rdtype)
                    ips.extend(str(r) for r in answers)
            except (dns.exception.DNSException, Exception):
                pass
        if ips:
            result[sub] = ips

    await asyncio.gather(*[resolve_one(s) for s in sub_list])

    facts: list[dict[str, str]] = []
    for sub, ips in sorted(result.items()):
        for ip in ips:
            facts.append({
                "trait": "osint.resolved_ip",
                "value": f"{sub}:{ip}",
            })

    return json.dumps({
        "facts": facts,
        "raw_output": f"Resolved {len(result)} subdomains to {sum(len(v) for v in result.values())} IPs",
    })


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
