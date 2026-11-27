"""athena-osint-mcp — FastMCP MCP container. Returns {"facts": [...]} format.

Tools:
  crtsh_query(target)     T1596.001 — certificate transparency subdomains via crt.sh
  shodan_query(target)    T1596.005 — Shodan host info (requires SHODAN_API_KEY)
  whois_lookup(target)    T1590    — WHOIS domain/IP lookup

Security:
  - All inputs validated against strict regex; shell metacharacters rejected.
  - Commands constructed from fixed templates; no eval() or f-string injection.
  - Credentials accepted via parameter or env var; never logged.
"""

from __future__ import annotations

import asyncio
import os
import re
import sys

import aiohttp
from fastmcp import FastMCP

mcp = FastMCP("athena-osint-mcp")

# ── validation ────────────────────────────────────────────────────────────────

# Strict RFC-1123 hostname or IPv4/IPv6 — no shell metacharacters
_HOST_RE = re.compile(
    r"^(?:"
    r"(?:\d{1,3}\.){3}\d{1,3}"                                               # IPv4
    r"|(?:[0-9a-fA-F]{1,4}:){1,7}[0-9a-fA-F]{1,4}"                         # IPv6 (abbreviated forms not exhaustive — good-enough guard)
    r"|(?:[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)"                  # single label
    r"(?:\.(?:[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?))*"           # dotted labels
    r")$"
)

# Shell metacharacter blocklist (belt-and-suspenders on top of regex allow-list)
_SHELL_BAD_RE = re.compile(r"[;&|`$<>(){}\[\]\\!\n\r\t]")


def _validate_host(value: str) -> str | None:
    """Return None if valid host/domain/IP, else an error string."""
    if not value or len(value) > 253:
        return "target must be 1–253 characters"
    if _SHELL_BAD_RE.search(value):
        return f"target contains forbidden shell metacharacters: {value!r}"
    if not _HOST_RE.match(value):
        return f"target {value!r} is not a valid IP address or hostname"
    return None


# ── helpers ───────────────────────────────────────────────────────────────────

def _error_facts(msg: str) -> dict:
    return {"facts": [{"trait": "error", "value": msg, "confidence": 0}]}


async def _run(cmd: str, timeout: int = 60) -> str:
    """Run a shell command safely and return combined stdout+stderr."""
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        return (stdout + stderr).decode(errors="replace")
    except asyncio.TimeoutError:
        proc.kill()
        await proc.communicate()
        return "timeout"


# ── tool: crtsh_query ─────────────────────────────────────────────────────────

@mcp.tool()
async def crtsh_query(target: str) -> dict:
    """T1596.001 — Query crt.sh certificate transparency logs for subdomains.

    Args:
        target: Domain name to search (e.g. "example.com"). No wildcards needed.

    Returns:
        {"facts": [{"trait": "crt.subdomain", "value": "sub.example.com",
                    "confidence": 85}, ...]}
    """
    err = _validate_host(target)
    if err:
        return _error_facts(err)

    url = f"https://crt.sh/?q=%25.{target}&output=json"
    facts: list[dict] = [{"trait": "scan.target", "value": target, "confidence": 100}]

    try:
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30)
        ) as session:
            async with session.get(url, headers={"Accept": "application/json"}) as resp:
                if resp.status != 200:
                    return _error_facts(f"crt.sh returned HTTP {resp.status}")
                raw = await resp.json(content_type=None)
    except asyncio.TimeoutError:
        return _error_facts("crt.sh query timed out")
    except aiohttp.ClientError as exc:
        return _error_facts(f"crt.sh request failed: {exc}")

    # Deduplicate subdomains; crt.sh returns one row per cert/SAN entry
    seen: set[str] = set()
    for entry in raw:
        name_value: str = entry.get("name_value", "")
        # name_value may contain multiple names separated by newlines
        for name in name_value.splitlines():
            name = name.strip().lstrip("*.")
            if not name or name in seen:
                continue
            seen.add(name)
            facts.append({
                "trait": "crt.subdomain",
                "value": name,
                "confidence": 85,
            })

    issuer_counts: dict[str, int] = {}
    for entry in raw:
        issuer = entry.get("issuer_name", "")
        if issuer:
            issuer_counts[issuer] = issuer_counts.get(issuer, 0) + 1

    if issuer_counts:
        top_issuer = max(issuer_counts, key=lambda k: issuer_counts[k])
        facts.append({
            "trait": "crt.top_issuer",
            "value": top_issuer,
            "confidence": 70,
        })

    facts.append({
        "trait": "crt.subdomain_count",
        "value": str(len(seen)),
        "confidence": 100,
    })

    return {"facts": facts}


# ── tool: shodan_query ────────────────────────────────────────────────────────

@mcp.tool()
async def shodan_query(target: str, api_key: str = "") -> dict:
    """T1596.005 — Query Shodan API for host information.

    Args:
        target:  IPv4 address to look up (Shodan /host endpoint requires IP).
        api_key: Shodan API key. Falls back to SHODAN_API_KEY env var.

    Returns:
        {"facts": [{"trait": "shodan.open_port", "value": "22/tcp/ssh",
                    "confidence": 90}, ...]}
    """
    err = _validate_host(target)
    if err:
        return _error_facts(err)

    key = api_key.strip() or os.environ.get("SHODAN_API_KEY", "").strip()
    if not key:
        return _error_facts(
            "Shodan API key not provided. Pass api_key= or set SHODAN_API_KEY env var."
        )

    url = f"https://api.shodan.io/shodan/host/{target}?key={key}"
    facts: list[dict] = [{"trait": "scan.target", "value": target, "confidence": 100}]

    try:
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30)
        ) as session:
            async with session.get(url) as resp:
                if resp.status == 404:
                    facts.append({
                        "trait": "shodan.result",
                        "value": "host not found in Shodan",
                        "confidence": 80,
                    })
                    return {"facts": facts}
                if resp.status == 401:
                    return _error_facts("Shodan API key is invalid or unauthorised")
                if resp.status != 200:
                    return _error_facts(f"Shodan returned HTTP {resp.status}")
                data = await resp.json()
    except asyncio.TimeoutError:
        return _error_facts("Shodan query timed out")
    except aiohttp.ClientError as exc:
        return _error_facts(f"Shodan request failed: {exc}")

    # Organisation / ISP
    for trait_key, field in [
        ("shodan.org", "org"),
        ("shodan.isp", "isp"),
        ("shodan.country", "country_name"),
        ("shodan.city", "city"),
        ("shodan.asn", "asn"),
        ("shodan.os", "os"),
        ("shodan.hostnames", "hostnames"),
    ]:
        val = data.get(field)
        if val is None:
            continue
        if isinstance(val, list):
            val = ", ".join(str(v) for v in val) if val else None
        if val:
            facts.append({"trait": trait_key, "value": str(val), "confidence": 90})

    # Last-seen
    last_update = data.get("last_update")
    if last_update:
        facts.append({"trait": "shodan.last_update", "value": last_update, "confidence": 100})

    # Ports / services
    for svc in data.get("data", []):
        port = svc.get("port")
        transport = svc.get("transport", "tcp")
        product = svc.get("product") or ""
        if port:
            facts.append({
                "trait": "shodan.open_port",
                "value": f"{port}/{transport}/{product}".rstrip("/"),
                "confidence": 90,
            })
            # CVEs reported by Shodan
            for vuln in svc.get("vulns", {}).keys():
                facts.append({
                    "trait": "shodan.vuln",
                    "value": f"{vuln} on port {port}/{transport}",
                    "confidence": 75,
                })

    # Top-level CVEs summary
    all_vulns = data.get("vulns", {})
    if all_vulns:
        facts.append({
            "trait": "shodan.vuln_count",
            "value": str(len(all_vulns)),
            "confidence": 90,
        })

    return {"facts": facts}


# ── tool: whois_lookup ────────────────────────────────────────────────────────

@mcp.tool()
async def whois_lookup(target: str) -> dict:
    """T1590 — WHOIS domain/IP lookup via system whois CLI.

    Args:
        target: Domain name or IPv4/IPv6 address.

    Returns:
        {"facts": [{"trait": "whois.registrar", "value": "...", "confidence": 80}, ...]}
    """
    err = _validate_host(target)
    if err:
        return _error_facts(err)

    facts: list[dict] = [{"trait": "scan.target", "value": target, "confidence": 100}]

    output = await _run(f"whois {target}", timeout=30)

    if output == "timeout":
        return _error_facts("whois timed out")
    if not output.strip():
        return _error_facts("whois returned no output")

    # Extract key fields with flexible regex (handles varied WHOIS server formats)
    _WHOIS_FIELDS = [
        ("whois.registrar",         r"(?:Registrar|registrar)\s*:\s*(.+)"),
        ("whois.registrant_org",    r"(?:Registrant Organization|org)\s*:\s*(.+)"),
        ("whois.registrant_email",  r"(?:Registrant Email|e-mail)\s*:\s*(.+)"),
        ("whois.creation_date",     r"(?:Creation Date|created)\s*:\s*(.+)"),
        ("whois.expiry_date",       r"(?:Registry Expiry Date|expires)\s*:\s*(.+)"),
        ("whois.updated_date",      r"(?:Updated Date|changed)\s*:\s*(.+)"),
        ("whois.name_server",       r"Name Server\s*:\s*(.+)"),
        ("whois.status",            r"Domain Status\s*:\s*(.+)"),
        ("whois.dnssec",            r"DNSSEC\s*:\s*(.+)"),
        # IP-centric fields
        ("whois.netname",           r"(?:netname|NetName)\s*:\s*(.+)"),
        ("whois.netrange",          r"(?:NetRange|inetnum)\s*:\s*(.+)"),
        ("whois.country",           r"(?:Country|country)\s*:\s*(.+)"),
        ("whois.cidr",              r"CIDR\s*:\s*(.+)"),
        ("whois.abuse_email",       r"(?:OrgAbuseEmail|abuse-mailbox)\s*:\s*(.+)"),
    ]

    seen_traits: set[str] = set()
    for line in output.splitlines():
        for trait, pattern in _WHOIS_FIELDS:
            m = re.search(pattern, line, re.IGNORECASE)
            if m:
                value = m.group(1).strip()
                # Allow multiple name-server and status entries
                key = f"{trait}:{value}" if trait in ("whois.name_server", "whois.status") else trait
                if key not in seen_traits and value:
                    seen_traits.add(key)
                    facts.append({"trait": trait, "value": value, "confidence": 80})

    # Append raw excerpt (first 60 lines) as a low-confidence dump fact
    excerpt_lines = [ln for ln in output.splitlines() if ln.strip()][:60]
    facts.append({
        "trait": "whois.raw_excerpt",
        "value": "\n".join(excerpt_lines),
        "confidence": 50,
    })

    return {"facts": facts}


# ── entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Allow CLI override for transport/host/port (mirrors nmap container pattern)
    import argparse

    parser = argparse.ArgumentParser(description="athena-osint-mcp FastMCP server")
    parser.add_argument("--transport", default="streamable-http")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=9104)
    args = parser.parse_args()

    mcp.run(transport=args.transport, host=args.host, port=args.port)
