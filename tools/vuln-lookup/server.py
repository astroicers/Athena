"""vuln-lookup MCP Server for Athena.

Exposes CVE lookup via NVD API and CPE mapping as MCP tools.
Returns JSON with {"facts": [{"trait": ..., "value": ...}]}
to integrate with Athena's fact collection pipeline.
"""

import asyncio
import json
import os
import re
import time

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("athena-vuln-lookup")

# Static CPE mapping — same as Athena's VulnLookupService._banner_to_cpe
_CPE_MAP: dict[str, tuple[str, str]] = {
    "ssh": ("openbsd", "openssh"),
    "openssh": ("openbsd", "openssh"),
    "apache": ("apache", "http_server"),
    "http": ("apache", "http_server"),
    "nginx": ("nginx", "nginx"),
    "ftp": ("vsftpd_project", "vsftpd"),
    "vsftpd": ("vsftpd_project", "vsftpd"),
    "mysql": ("mysql", "mysql"),
    "postgresql": ("postgresql", "postgresql"),
    "postgres": ("postgresql", "postgresql"),
    "mssql": ("microsoft", "sql_server"),
    "mongodb": ("mongodb", "mongodb"),
    "redis": ("redis", "redis"),
    "samba": ("samba", "samba"),
    "smb": ("samba", "samba"),
    "tomcat": ("apache", "tomcat"),
    "iis": ("microsoft", "internet_information_services"),
    "proftpd": ("proftpd_project", "proftpd"),
    "exim": ("exim", "exim"),
    "postfix": ("postfix", "postfix"),
    "bind": ("isc", "bind"),
    "named": ("isc", "bind"),
    "sendmail": ("sendmail", "sendmail"),
    "dovecot": ("dovecot", "dovecot"),
}


def _cvss_to_severity(score: float) -> str:
    if score >= 9.0:
        return "critical"
    if score >= 7.0:
        return "high"
    if score >= 4.0:
        return "medium"
    if score > 0:
        return "low"
    return "info"


@mcp.tool()
async def banner_to_cpe(service: str, version: str) -> str:
    """Convert a service banner to a CPE 2.2 string.

    Args:
        service: Service name from nmap (e.g., "ssh", "http").
        version: Version string from nmap banner (e.g., "OpenSSH 7.4").

    Returns:
        JSON with fact: vuln.cpe with the CPE string, or empty if unmapped.
    """
    service_lower = service.lower().strip()
    version_str = version.strip()

    vendor_product = _CPE_MAP.get(service_lower)

    if vendor_product is None and version_str:
        first_token = version_str.split()[0].lower()
        vendor_product = _CPE_MAP.get(first_token)

    if vendor_product is None:
        return json.dumps({
            "facts": [],
            "raw_output": f"No CPE mapping for service={service}, version={version}",
        })

    vendor, product = vendor_product
    version_match = re.search(r"(\d+\.\d+[\d.]*)", version_str)
    version_num = version_match.group(1) if version_match else "*"

    cpe = f"cpe:/a:{vendor}:{product}:{version_num}"
    return json.dumps({
        "facts": [{"trait": "vuln.cpe", "value": cpe}],
        "raw_output": f"Mapped {service}/{version} -> {cpe}",
    })


# NVD rate limiter: 5/30s (free) or 50/30s (API key)
_NVD_RATE_LOCK = asyncio.Lock()
_NVD_CALL_TIMES: list[float] = []


async def _nvd_rate_limit():
    """Throttle NVD API calls: 5/30s (free) or 50/30s (API key)."""
    api_key = os.environ.get("NVD_API_KEY", "")
    max_calls = 50 if api_key else 5
    window = 30.0
    async with _NVD_RATE_LOCK:
        now = time.monotonic()
        while _NVD_CALL_TIMES and now - _NVD_CALL_TIMES[0] > window:
            _NVD_CALL_TIMES.pop(0)
        if len(_NVD_CALL_TIMES) >= max_calls:
            sleep_for = window - (now - _NVD_CALL_TIMES[0]) + 0.1
            await asyncio.sleep(sleep_for)
        _NVD_CALL_TIMES.append(time.monotonic())


@mcp.tool()
async def nvd_cve_lookup(cpe: str, max_results: int = 10) -> str:
    """Query NVD NIST API v2 for CVEs matching a CPE string.

    Args:
        cpe: CPE 2.2 string (e.g., "cpe:/a:openbsd:openssh:7.4").
        max_results: Maximum number of CVEs to return.

    Returns:
        JSON with facts: vuln.cve for each CVE found.
        Value format: "CVE-ID:cvss=SCORE:severity=LEVEL:exploit=BOOL"
    """
    import httpx

    await _nvd_rate_limit()

    headers: dict[str, str] = {}
    api_key = os.environ.get("NVD_API_KEY", "")
    if api_key:
        headers["apiKey"] = api_key

    url = "https://services.nvd.nist.gov/rest/json/cves/2.0"
    params = {"cpeName": cpe, "resultsPerPage": str(max_results)}

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url, params=params, headers=headers)
            if resp.status_code == 404:
                return json.dumps({
                    "facts": [],
                    "raw_output": f"No CVEs found for {cpe}",
                })
            resp.raise_for_status()
            data = resp.json()
    except Exception as exc:
        return json.dumps({
            "facts": [],
            "raw_output": f"NVD API query failed: {exc}",
        })

    facts: list[dict[str, str]] = []
    for vuln in data.get("vulnerabilities", [])[:max_results]:
        cve_data = vuln.get("cve", {})
        cve_id = cve_data.get("id", "")

        # Extract CVSS score (prefer v3.1 → v3.0 → v2)
        metrics = cve_data.get("metrics", {})
        cvss_score = 0.0
        for key in ("cvssMetricV31", "cvssMetricV30", "cvssMetricV2"):
            metric_list = metrics.get(key, [])
            if metric_list:
                cvss_data = metric_list[0].get("cvssData", {})
                cvss_score = cvss_data.get("baseScore", 0.0)
                break

        # Description
        descriptions = cve_data.get("descriptions", [])
        desc = next(
            (d["value"] for d in descriptions if d.get("lang") == "en"),
            "No description available",
        )

        # Check for known exploits
        references = cve_data.get("references", [])
        exploit_available = any(
            "exploit" in ref.get("url", "").lower()
            or any("exploit" in tag.lower() for tag in ref.get("tags", []))
            for ref in references
        )

        severity = _cvss_to_severity(cvss_score)
        facts.append({
            "trait": "vuln.cve",
            "value": (
                f"{cve_id}:cvss={cvss_score:.1f}:severity={severity}"
                f":exploit={'true' if exploit_available else 'false'}"
                f":desc={desc[:200]}"
            ),
        })

    return json.dumps({
        "facts": facts,
        "raw_output": f"Found {len(facts)} CVEs for {cpe}",
    })


if __name__ == "__main__":
    mcp.run()
