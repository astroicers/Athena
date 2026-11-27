"""
athena-dns-recon-mcp — FastMCP MCP container

Tools: dns_enum
Returns {"facts": [...]} format.

Trait naming:
  dns.subdomain           Discovered subdomain (FQDN)
  dns.record.{type}       DNS record value (A, AAAA, MX, NS, TXT, CNAME, SOA)
  dns.zone_transfer       Zone transfer data (AXFR success — high value)
  dns.nameserver          Authoritative nameserver for the target domain
  scan.target             The domain/host under reconnaissance

Security:
  - target validated against strict domain/IP regex (no shell metacharacters)
  - subprocess calls use list-form args (no shell=True) where possible
  - zone transfer is a passive read — no modification or injection
"""

from __future__ import annotations

import asyncio
import re
import subprocess
from fastmcp import FastMCP

mcp = FastMCP("athena-dns-recon-mcp")

# ── validation ────────────────────────────────────────────────────────────────

# Accepts IPv4, IPv6, or RFC-1123 hostnames/FQDNs (with optional trailing dot)
_TARGET_RE = re.compile(
    r"^(?:"
    r"(?:\d{1,3}\.){3}\d{1,3}"                                           # IPv4
    r"|(?:[0-9a-fA-F:]+)"                                                 # IPv6
    r"|(?:[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)"              # single label
    r"(?:\.(?:[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?))*\.?"     # more labels
    r")$"
)

# Common subdomains to brute-force when passive enumeration is exhausted
_COMMON_SUBDOMAINS = [
    "www", "mail", "remote", "blog", "webmail", "server", "ns1", "ns2",
    "smtp", "secure", "vpn", "api", "dev", "staging", "test", "portal",
    "admin", "ftp", "ssh", "mx", "pop", "imap", "mx1", "mx2", "autodiscover",
    "autoconfig", "m", "mobile", "static", "cdn", "assets", "media",
    "shop", "help", "support", "git", "gitlab", "jenkins", "jira",
    "confluence", "wiki", "docs", "monitor", "status", "health",
    "intranet", "internal", "corp", "vpn2", "proxy", "gateway",
    "auth", "sso", "login", "app", "apps", "cloud", "store",
]

# DNS record types to query for the root domain
_RECORD_TYPES = ["A", "AAAA", "MX", "NS", "TXT", "SOA", "CNAME"]


def _validate_target(target: str) -> str | None:
    """Return None if valid, error string if invalid."""
    t = target.rstrip(".")
    if not t or len(t) > 253:
        return "target must be a non-empty string of at most 253 characters"
    if not _TARGET_RE.match(target):
        return f"target '{target}' contains invalid characters or is not a valid domain/IP"
    return None


def _error_fact(msg: str) -> dict:
    return {"facts": [{"trait": "error", "value": msg}]}


# ── async subprocess helper ───────────────────────────────────────────────────

async def _run(cmd: str, timeout: int = 60) -> str:
    proc = await asyncio.create_subprocess_shell(
        cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        return (stdout + stderr).decode(errors="replace")
    except asyncio.TimeoutError:
        proc.kill()
        return "timeout"


async def _dig(args: list[str], timeout: int = 10) -> str:
    """Run dig with the given argument list; returns combined stdout+stderr."""
    proc = await asyncio.create_subprocess_exec(
        "dig", *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        return (stdout + stderr).decode(errors="replace")
    except asyncio.TimeoutError:
        proc.kill()
        return "timeout"


# ── parsing helpers ───────────────────────────────────────────────────────────

def _parse_dig_short(output: str) -> list[str]:
    """Return non-empty, non-comment lines from dig +short output."""
    return [
        line.strip()
        for line in output.splitlines()
        if line.strip() and not line.strip().startswith(";")
    ]


def _extract_nameservers(ns_output: str) -> list[str]:
    """Parse nameservers from `dig NS <domain> +short`."""
    servers = []
    for line in _parse_dig_short(ns_output):
        ns = line.rstrip(".")
        if ns:
            servers.append(ns)
    return servers


def _parse_zone_transfer(axfr_output: str) -> list[str]:
    """Extract record lines from AXFR output (non-SOA, non-empty, non-comment)."""
    records = []
    for line in axfr_output.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith(";"):
            continue
        # Keep any line that looks like a DNS record (has at least 4 fields)
        parts = stripped.split()
        if len(parts) >= 4:
            records.append(stripped)
    return records


# ── tool ──────────────────────────────────────────────────────────────────────

@mcp.tool()
async def dns_enum(target: str) -> dict:
    """T1596.001, T1018: DNS subdomain enumeration and zone transfer attempt.

    Performs comprehensive passive and active DNS reconnaissance:
      1. Collects A, AAAA, MX, NS, TXT, SOA, CNAME records for the root domain.
      2. Attempts AXFR zone transfer against each authoritative nameserver.
      3. Brute-forces a wordlist of common subdomains via A/AAAA lookups.

    Args:
        target: Domain name or IP address to enumerate (e.g. "example.com").

    Returns:
        {"facts": [{"trait": "dns.subdomain", "value": "mail.example.com",
                    "confidence": 90}, ...]}
    """
    err = _validate_target(target)
    if err:
        return _error_fact(err)

    # Strip trailing dot for display consistency
    domain = target.rstrip(".")
    facts: list[dict] = [{"trait": "scan.target", "value": domain, "confidence": 100}]

    # ── 1. Root domain record enumeration ─────────────────────────────────────
    nameservers: list[str] = []

    record_tasks = {
        rtype: _dig([domain, rtype, "+short", "+time=5", "+tries=2"], timeout=15)
        for rtype in _RECORD_TYPES
    }
    record_results: dict[str, str] = {}
    for rtype, coro in record_tasks.items():
        record_results[rtype] = await coro

    for rtype, output in record_results.items():
        if output == "timeout":
            continue
        values = _parse_dig_short(output)
        if rtype == "NS":
            nameservers = _extract_nameservers(output)
        for val in values:
            val_clean = val.rstrip(".")
            if not val_clean:
                continue
            facts.append({
                "trait": f"dns.record.{rtype.lower()}",
                "value": val_clean,
                "confidence": 95,
            })
            # Emit nameserver trait separately for clarity
            if rtype == "NS":
                facts.append({
                    "trait": "dns.nameserver",
                    "value": val_clean,
                    "confidence": 95,
                })

    # ── 2. Zone transfer attempt (AXFR) ───────────────────────────────────────
    zone_transfer_succeeded = False
    for ns in nameservers:
        axfr_output = await _dig(
            [f"@{ns}", domain, "AXFR", "+time=10", "+tries=1"],
            timeout=20,
        )
        if axfr_output == "timeout":
            continue
        # AXFR success: output contains actual records (not just SOA or error)
        records = _parse_zone_transfer(axfr_output)
        # A successful transfer usually contains more than 2 records (SOA + data)
        if len(records) > 2:
            zone_transfer_succeeded = True
            facts.append({
                "trait": "dns.zone_transfer",
                "value": f"AXFR success via {ns}: {len(records)} records",
                "confidence": 100,
            })
            # Parse individual hostnames from zone data
            seen_zt: set[str] = set()
            for record in records:
                parts = record.split()
                if len(parts) >= 1:
                    host = parts[0].rstrip(".")
                    if host and host not in seen_zt and "." in host:
                        seen_zt.add(host)
                        facts.append({
                            "trait": "dns.subdomain",
                            "value": host,
                            "confidence": 100,
                        })
            break  # One successful AXFR is enough

    # ── 3. Subdomain brute-force ───────────────────────────────────────────────
    if not zone_transfer_succeeded:
        # Run subdomain lookups in batches to avoid overwhelming the resolver
        batch_size = 10
        seen_bf: set[str] = set()

        for i in range(0, len(_COMMON_SUBDOMAINS), batch_size):
            batch = _COMMON_SUBDOMAINS[i : i + batch_size]
            lookup_tasks = {
                sub: _dig(
                    [f"{sub}.{domain}", "A", "+short", "+time=3", "+tries=1"],
                    timeout=8,
                )
                for sub in batch
            }
            for sub, coro in lookup_tasks.items():
                result = await coro
                if result == "timeout" or not result.strip():
                    continue
                resolved = _parse_dig_short(result)
                if not resolved:
                    continue
                fqdn = f"{sub}.{domain}"
                if fqdn not in seen_bf:
                    seen_bf.add(fqdn)
                    # The resolved IP values as a record fact
                    for ip in resolved:
                        ip_clean = ip.rstrip(".")
                        if ip_clean:
                            facts.append({
                                "trait": "dns.record.a",
                                "value": f"{fqdn} -> {ip_clean}",
                                "confidence": 90,
                            })
                    facts.append({
                        "trait": "dns.subdomain",
                        "value": fqdn,
                        "confidence": 90,
                    })

        # Also try AAAA for discovered subdomains (non-duplicative)
        aaaa_tasks = {
            fqdn: _dig(
                [fqdn, "AAAA", "+short", "+time=3", "+tries=1"],
                timeout=8,
            )
            for fqdn in seen_bf
        }
        for fqdn, coro in aaaa_tasks.items():
            result = await coro
            if result == "timeout" or not result.strip():
                continue
            for ip6 in _parse_dig_short(result):
                ip6_clean = ip6.rstrip(".")
                if ip6_clean:
                    facts.append({
                        "trait": "dns.record.aaaa",
                        "value": f"{fqdn} -> {ip6_clean}",
                        "confidence": 90,
                    })

    return {"facts": facts}


if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0", port=9102)
