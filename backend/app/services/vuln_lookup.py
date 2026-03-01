# Copyright 2026 Athena Contributors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""VulnLookupService — maps service banners to CVEs via NVD NIST API."""

import logging
import uuid
from datetime import datetime, timezone

import aiosqlite

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
        db: aiosqlite.Connection,
        services: list[ServiceInfo],
        operation_id: str,
        target_id: str,
    ) -> list[VulnFinding]:
        """Enrich all services with CVE data. Returns found VulnFindings."""
        db.row_factory = aiosqlite.Row
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
        db: aiosqlite.Connection,
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

        # Cache miss → query NVD API
        try:
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
        self, db: aiosqlite.Connection, cpe: str
    ) -> list[aiosqlite.Row] | None:
        """Return cached rows if they exist and haven't expired. None = cache miss."""
        cursor = await db.execute(
            """
            SELECT cve_id, cvss_score, severity, description, exploit_available
            FROM vuln_cache
            WHERE cpe_string = ?
              AND datetime(cached_at) > datetime('now', ? || ' hours')
            """,
            (cpe, f"-{settings.NVD_CACHE_TTL_HOURS}"),
        )
        rows = await cursor.fetchall()
        # Return None only if not in cache at all (empty result is still a cache hit)
        # We distinguish by checking if ANY row exists with expired=false
        if rows is not None:  # rows is a list (possibly empty)
            # Check if there's any non-expired entry for this CPE
            count_cursor = await db.execute(
                "SELECT COUNT(*) FROM vuln_cache WHERE cpe_string = ?", (cpe,)
            )
            count_row = await count_cursor.fetchone()
            if count_row and count_row[0] > 0:
                return list(rows)  # Cache hit (may be empty list if no CVEs found)
        return None  # Cache miss

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

    async def _cache_finding(self, db: aiosqlite.Connection, cpe: str, nvd_item: dict) -> None:
        """Insert a CVE into the cache table."""
        cache_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        try:
            await db.execute(
                """
                INSERT OR IGNORE INTO vuln_cache
                    (id, cpe_string, cve_id, cvss_score, severity, description,
                     exploit_available, cached_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    cache_id, cpe, nvd_item["cve_id"],
                    nvd_item["cvss_score"],
                    _cvss_to_severity(nvd_item["cvss_score"]),
                    nvd_item.get("description", "")[:500],
                    1 if nvd_item.get("exploit_available") else 0,
                    now,
                ),
            )
            await db.commit()
        except Exception as exc:
            logger.debug("Cache insert failed: %s", exc)

    async def _cache_empty(self, db: aiosqlite.Connection, cpe: str) -> None:
        """Insert a sentinel row to cache 'no CVEs found' for this CPE."""
        cache_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        try:
            await db.execute(
                """
                INSERT OR IGNORE INTO vuln_cache
                    (id, cpe_string, cve_id, cvss_score, severity, description,
                     exploit_available, cached_at)
                VALUES (?, ?, '__empty__', 0, 'info', 'No CVEs found', 0, ?)
                """,
                (cache_id, cpe, now),
            )
            await db.commit()
        except Exception as exc:
            logger.debug("Cache empty-sentinel insert failed: %s", exc)

    async def _write_finding_fact(self, db: aiosqlite.Connection, finding: VulnFinding) -> None:
        """Write a vuln.cve fact to the facts table and broadcast."""
        fact_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        value = (
            f"{finding.cve_id}:{finding.service}:{finding.version.replace(' ', '_')}"
            f":cvss={finding.cvss_score:.1f}:exploit={'true' if finding.exploit_available else 'false'}"
        )
        try:
            await db.execute(
                "INSERT INTO facts "
                "(id, trait, value, category, source_technique_id, "
                "source_target_id, operation_id, score, collected_at) "
                "VALUES (?, ?, ?, ?, NULL, ?, ?, 1, ?)",
                (
                    fact_id, "vuln.cve", value, "vulnerability",
                    finding.target_id, finding.operation_id, now,
                ),
            )
            await db.commit()
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
