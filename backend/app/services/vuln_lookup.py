# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: [TODO: contact email]

"""VulnLookupService — maps service banners to CVEs via NVD NIST API."""

import logging
import uuid
from datetime import datetime, timezone

import asyncpg

from app.config import settings
from app.models.recon import ServiceInfo
from app.models.vuln import VulnFinding
from app.ws_manager import ws_manager

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Static CPE mapping heuristics
# Maps (service_name_lower, version_prefix) → CPE vendor/product
# ---------------------------------------------------------------------------
_CPE_MAP: dict[str, tuple[str, str]] = {
    # SSH
    "ssh": ("openbsd", "openssh"),
    "openssh": ("openbsd", "openssh"),
    # HTTP servers
    "apache": ("apache", "http_server"),
    "http": ("apache", "http_server"),
    "nginx": ("nginx", "nginx"),
    # FTP
    "ftp": ("vsftpd_project", "vsftpd"),
    "vsftpd": ("vsftpd_project", "vsftpd"),
    # Database
    "mysql": ("mysql", "mysql"),
    "postgresql": ("postgresql", "postgresql"),
    "postgres": ("postgresql", "postgresql"),
    "mssql": ("microsoft", "sql_server"),
    "mongodb": ("mongodb", "mongodb"),
    "redis": ("redis", "redis"),
    # SMB/NETBIOS
    "samba": ("samba", "samba"),
    "smb": ("samba", "samba"),
    # Misc
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


class VulnLookupService:
    """Maps service banners → CPE strings → CVEs via NVD NIST API.

    Results are cached in ``vuln_cache`` table for ``NVD_CACHE_TTL_HOURS`` hours.
    """

    async def enrich_services(
        self,
        db: asyncpg.Connection,
        services: list[ServiceInfo],
        operation_id: str,
        target_id: str,
    ) -> list[VulnFinding]:
        """Enrich all services with CVE data. Returns found VulnFindings."""
        all_findings: list[VulnFinding] = []

        for svc in services:
            cpe = self._banner_to_cpe(svc.service, svc.version)
            if cpe is None:
                continue

            findings = await self._lookup_cve(db, cpe, svc, operation_id, target_id)
            all_findings.extend(findings)

        return all_findings

    def _banner_to_cpe(self, service: str, version: str) -> str | None:
        """Build a CPE 2.2 string from nmap service/version banner.

        Example:
            service="ssh", version="OpenSSH 7.4" → "cpe:/a:openbsd:openssh:7.4"
        """
        service_lower = service.lower().strip()
        version_str = version.strip()

        # Try service name directly
        vendor_product = _CPE_MAP.get(service_lower)

        # Also try first token of version string (e.g., "OpenSSH 7.4" → "openssh")
        if vendor_product is None and version_str:
            first_token = version_str.split()[0].lower()
            vendor_product = _CPE_MAP.get(first_token)

        if vendor_product is None:
            return None

        vendor, product = vendor_product

        # Extract version number from the version string
        # "OpenSSH 7.4" → "7.4",  "Apache 2.4.6" → "2.4.6"
        import re
        version_match = re.search(r"(\d+\.\d+[\d.]*)", version_str)
        version_num = version_match.group(1) if version_match else "*"

        return f"cpe:/a:{vendor}:{product}:{version_num}"

    async def _lookup_cve(
        self,
        db: asyncpg.Connection,
        cpe: str,
        svc: ServiceInfo,
        operation_id: str,
        target_id: str,
    ) -> list[VulnFinding]:
        """Look up CVEs for a CPE string. Uses cache, falls back to NVD API."""
        # Check cache
        cached = await self._get_cached(db, cpe)
        if cached is not None:
            findings = []
            for row in cached:
                finding = VulnFinding(
                    cve_id=row["cve_id"],
                    service=svc.service,
                    version=svc.version,
                    cvss_score=row["cvss_score"] or 0.0,
                    severity=row["severity"] or "info",
                    description=row["description"] or "",
                    exploit_available=bool(row["exploit_available"]),
                    target_id=target_id,
                    operation_id=operation_id,
                )
                await self._write_finding_fact(db, finding)
                findings.append(finding)
            return findings

        # Cache miss → MCP or direct NVD query (with graceful fallback)
        try:
            _mcp_ok = False
            if settings.MCP_ENABLED:
                try:
                    nvd_results = await self._query_nvd_via_mcp(cpe)
                    _mcp_ok = True
                except ConnectionError:
                    logger.warning(
                        "MCP vuln-lookup unavailable, falling back to direct NVD API"
                    )
            if not _mcp_ok:
                nvd_results = await self._query_nvd(cpe)
        except Exception as exc:
            logger.warning("NVD API query failed for %s: %s", cpe, exc)
            return []

        findings = []
        for nvd_item in nvd_results[:10]:  # limit to 10 CVEs per service
            finding = VulnFinding(
                cve_id=nvd_item["cve_id"],
                service=svc.service,
                version=svc.version,
                cvss_score=nvd_item["cvss_score"],
                severity=_cvss_to_severity(nvd_item["cvss_score"]),
                description=nvd_item["description"],
                exploit_available=nvd_item["exploit_available"],
                target_id=target_id,
                operation_id=operation_id,
            )
            # Cache the result
            await self._cache_finding(db, cpe, nvd_item)
            # Write fact
            await self._write_finding_fact(db, finding)
            findings.append(finding)

        # Cache empty result too (avoids repeated lookups for unknown CPEs)
        if not findings:
            await self._cache_empty(db, cpe)

        return findings

    async def _get_cached(
        self, db: asyncpg.Connection, cpe: str
    ) -> list | None:
        """Return cached rows if they exist and haven't expired. None = cache miss."""
        rows = await db.fetch(
            """
            SELECT cve_id, cvss_score, severity, description, exploit_available
            FROM vuln_cache
            WHERE cpe_string = $1
              AND cached_at > NOW() - INTERVAL '1 hours' * $2
            """,
            cpe, settings.NVD_CACHE_TTL_HOURS,
        )
        # Return None only if not in cache at all (empty result is still a cache hit)
        # We distinguish by checking if ANY row exists with expired=false
        if rows is not None:  # rows is a list (possibly empty)
            # Check if there's any non-expired entry for this CPE
            count_row = await db.fetchrow(
                "SELECT COUNT(*) FROM vuln_cache WHERE cpe_string = $1", cpe,
            )
            if count_row and count_row[0] > 0:
                return list(rows)  # Cache hit (may be empty list if no CVEs found)
        return None  # Cache miss

    async def _query_nvd_via_mcp(self, cpe: str) -> list[dict]:
        """Query NVD via MCP vuln-lookup server."""
        import json as _json
        import re

        from app.services.mcp_client_manager import get_mcp_manager

        manager = get_mcp_manager()
        if manager is None or not manager.is_connected("vuln-lookup"):
            raise ConnectionError("MCP vuln-lookup server is not connected")

        result = await manager.call_tool(
            "vuln-lookup", "nvd_cve_lookup", {"cpe": cpe}
        )

        text_parts = [
            block.get("text", "")
            for block in result.get("content", [])
            if isinstance(block, dict) and block.get("type") == "text"
        ]
        text = "\n".join(text_parts)

        try:
            data = _json.loads(text)
        except _json.JSONDecodeError:
            logger.warning("MCP nvd_cve_lookup returned non-JSON: %s", text[:200])
            return []

        results: list[dict] = []
        for fact in data.get("facts", []):
            if fact.get("trait") != "vuln.cve":
                continue
            value = fact.get("value", "")
            # Parse: "CVE-ID:cvss=N:severity=X:exploit=BOOL:desc=..."
            cve_id_match = re.match(r"(CVE-\d+-\d+)", value)
            cvss_match = re.search(r"cvss=([\d.]+)", value)
            exploit_match = re.search(r"exploit=(true|false)", value)
            desc_match = re.search(r"desc=(.+)$", value)

            results.append({
                "cve_id": cve_id_match.group(1) if cve_id_match else "",
                "cvss_score": float(cvss_match.group(1)) if cvss_match else 0.0,
                "description": desc_match.group(1) if desc_match else "",
                "exploit_available": exploit_match.group(1) == "true" if exploit_match else False,
            })

        return results

    async def _query_nvd(self, cpe: str) -> list[dict]:
        """Query NVD NIST API v2 for CVEs matching a CPE string."""
        import httpx

        headers: dict[str, str] = {}
        if settings.NVD_API_KEY:
            headers["apiKey"] = settings.NVD_API_KEY

        url = "https://services.nvd.nist.gov/rest/json/cves/2.0"
        params = {"cpeName": cpe, "resultsPerPage": "10"}

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url, params=params, headers=headers)
            if resp.status_code == 404:
                return []
            resp.raise_for_status()
            data = resp.json()

        results = []
        for vuln in data.get("vulnerabilities", []):
            cve_data = vuln.get("cve", {})
            cve_id = cve_data.get("id", "")

            # Extract CVSS score (prefer v3.1, fallback to v3.0, then v2)
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

            # Check for known exploits (weaknesses / references)
            references = cve_data.get("references", [])
            exploit_available = any(
                "exploit" in ref.get("url", "").lower()
                or any("exploit" in tag.lower() for tag in ref.get("tags", []))
                for ref in references
            )

            results.append({
                "cve_id": cve_id,
                "cvss_score": cvss_score,
                "description": desc[:500],  # truncate for DB
                "exploit_available": exploit_available,
            })

        return results

    async def _cache_finding(self, db: asyncpg.Connection, cpe: str, nvd_item: dict) -> None:
        """Insert a CVE into the cache table."""
        cache_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        try:
            await db.execute(
                """
                INSERT INTO vuln_cache
                    (id, cpe_string, cve_id, cvss_score, severity, description,
                     exploit_available, cached_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8) ON CONFLICT DO NOTHING
                """,
                cache_id, cpe, nvd_item["cve_id"],
                nvd_item["cvss_score"],
                _cvss_to_severity(nvd_item["cvss_score"]),
                nvd_item.get("description", "")[:500],
                True if nvd_item.get("exploit_available") else False,
                now,
            )
        except Exception as exc:
            logger.debug("Cache insert failed: %s", exc)

    async def _cache_empty(self, db: asyncpg.Connection, cpe: str) -> None:
        """Insert a sentinel row to cache 'no CVEs found' for this CPE."""
        cache_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        try:
            await db.execute(
                """
                INSERT INTO vuln_cache
                    (id, cpe_string, cve_id, cvss_score, severity, description,
                     exploit_available, cached_at)
                VALUES ($1, $2, '__empty__', 0, 'info', 'No CVEs found', FALSE, $3)
                ON CONFLICT DO NOTHING
                """,
                cache_id, cpe, now,
            )
        except Exception as exc:
            logger.debug("Cache empty-sentinel insert failed: %s", exc)

    async def _write_finding_fact(self, db: asyncpg.Connection, finding: VulnFinding) -> None:
        """Write a vuln.cve fact to the facts table and broadcast."""
        fact_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        value = (
            f"{finding.cve_id}:{finding.service}:{finding.version.replace(' ', '_')}"
            f":cvss={finding.cvss_score:.1f}:exploit={'true' if finding.exploit_available else 'false'}"
        )
        try:
            await db.execute(
                "INSERT INTO facts "
                "(id, trait, value, category, source_technique_id, "
                "source_target_id, operation_id, score, collected_at) "
                "VALUES ($1, $2, $3, $4, NULL, $5, $6, 1, $7) ON CONFLICT DO NOTHING",
                fact_id, "vuln.cve", value, "vulnerability",
                finding.target_id, finding.operation_id, now,
            )
            payload = {
                "id": fact_id,
                "trait": "vuln.cve",
                "value": value,
                "category": "vulnerability",
                "source_target_id": finding.target_id,
                "operation_id": finding.operation_id,
            }
            await ws_manager.broadcast(finding.operation_id, "fact.new", payload)
        except Exception as exc:
            logger.warning("Failed to write vuln fact: %s", exc)
