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

"""OSINTEngine — domain subdomain enumeration and IP resolution."""

import asyncio
import logging
import time
import uuid
from datetime import datetime, timezone

import aiosqlite

from app.config import settings
from app.models.osint import OSINTResult, SubdomainInfo
from app.ws_manager import ws_manager

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Mock data — returned when settings.MOCK_C2_ENGINE is True
# ---------------------------------------------------------------------------
_MOCK_SUBDOMAINS = [
    SubdomainInfo(subdomain="www.example.com", resolved_ips=["93.184.216.34"], source="crtsh"),
    SubdomainInfo(subdomain="mail.example.com", resolved_ips=["93.184.216.35"], source="crtsh"),
    SubdomainInfo(subdomain="api.example.com", resolved_ips=["93.184.216.36"], source="subfinder"),
]


class OSINTEngine:
    """OSINT phase — discovers subdomains and resolves IPs before nmap scanning."""

    async def discover(
        self,
        db: aiosqlite.Connection,
        operation_id: str,
        domain: str,
        max_subdomains: int | None = None,
    ) -> OSINTResult:
        """Enumerate subdomains for a domain and persist results as facts and targets.

        Steps:
        1. If mock mode, return deterministic mock result.
        2. Query crt.sh (passive, no binary needed).
        3. Query subfinder if available (graceful degradation if missing).
        4. DNS-resolve all discovered subdomains.
        5. Deduplicate and apply scope limits.
        6. Create Target records in DB for discovered hosts.
        7. Write facts: osint.subdomain, osint.resolved_ip, osint.certificate_san.
        8. Broadcast fact.new events.
        9. Return OSINTResult.
        """
        db.row_factory = aiosqlite.Row
        limit = max_subdomains or settings.OSINT_MAX_SUBDOMAINS
        t_start = time.monotonic()

        if settings.MOCK_C2_ENGINE:
            return await self._mock_result(
                db=db,
                operation_id=operation_id,
                domain=domain,
            )

        # Step 2: crt.sh
        crtsh_subs = await self._crtsh_query(domain)
        sources_used = ["crtsh"] if crtsh_subs else []

        # Step 3: subfinder
        subfinder_subs: list[str] = []
        if settings.SUBFINDER_ENABLED:
            subfinder_subs = await self._subfinder_query(domain)
            if subfinder_subs:
                sources_used.append("subfinder")

        # Step 4: Deduplicate all subdomains
        all_subs: set[str] = set(crtsh_subs) | set(subfinder_subs)
        all_subs.discard(domain)  # exclude apex domain itself
        all_subs_list = sorted(all_subs)[:limit]

        # Step 5: DNS resolve
        resolved = await self._resolve_all(all_subs_list)

        # Build SubdomainInfo list
        subdomain_infos: list[SubdomainInfo] = []
        for sub in all_subs_list:
            ips = resolved.get(sub, [])
            source = "crtsh" if sub in crtsh_subs else "subfinder"
            subdomain_infos.append(SubdomainInfo(subdomain=sub, resolved_ips=ips, source=source))

        # Steps 6–8: Write targets and facts
        facts_written = 0
        targets_created = 0
        ips_seen: set[str] = set()

        for info in subdomain_infos:
            # Write subdomain fact
            facts_written += await self._write_fact(
                db=db,
                operation_id=operation_id,
                trait="osint.subdomain",
                value=info.subdomain,
                category="osint",
            )

            for ip in info.resolved_ips:
                # Write IP fact
                facts_written += await self._write_fact(
                    db=db,
                    operation_id=operation_id,
                    trait="osint.resolved_ip",
                    value=f"{info.subdomain}:{ip}",
                    category="osint",
                )

                # Create Target record for each unique IP
                if ip not in ips_seen:
                    ips_seen.add(ip)
                    created = await self._create_target_if_missing(
                        db=db,
                        operation_id=operation_id,
                        hostname=info.subdomain,
                        ip_address=ip,
                    )
                    if created:
                        targets_created += 1

        scan_duration = time.monotonic() - t_start

        return OSINTResult(
            domain=domain,
            operation_id=operation_id,
            subdomains_found=len(subdomain_infos),
            ips_resolved=len(ips_seen),
            targets_created=targets_created,
            facts_written=facts_written,
            scan_duration_sec=round(scan_duration, 3),
            sources_used=sources_used,
            subdomains=subdomain_infos,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _crtsh_query(self, domain: str) -> list[str]:
        """Query crt.sh certificate transparency logs for subdomains."""
        try:
            import httpx
            url = f"https://crt.sh/?q=%.{domain}&output=json"
            async with httpx.AsyncClient(timeout=settings.OSINT_REQUEST_TIMEOUT_SEC) as client:
                resp = await client.get(url)
                if resp.status_code != 200:
                    logger.warning("crt.sh returned status %s for %s", resp.status_code, domain)
                    return []
                data = resp.json()
        except Exception as exc:
            logger.warning("crt.sh query failed for %s: %s", domain, exc)
            return []

        subdomains: set[str] = set()
        for entry in data:
            name_value = entry.get("name_value", "")
            for name in name_value.split("\n"):
                name = name.strip().lower()
                # Filter: must end with the domain, skip wildcards and apex
                if name.endswith(f".{domain}") and not name.startswith("*"):
                    subdomains.add(name)
        return sorted(subdomains)

    async def _subfinder_query(self, domain: str) -> list[str]:
        """Run subfinder binary if available. Returns empty list on failure."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "subfinder", "-d", domain, "-silent",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            )
            stdout, _ = await asyncio.wait_for(
                proc.communicate(),
                timeout=settings.OSINT_REQUEST_TIMEOUT_SEC,
            )
            lines = stdout.decode(errors="ignore").strip().split("\n")
            return [ln.strip().lower() for ln in lines if ln.strip() and domain in ln]
        except (FileNotFoundError, OSError):
            logger.debug("subfinder not available — skipping")
            return []
        except asyncio.TimeoutError:
            logger.warning("subfinder timed out for %s", domain)
            return []
        except Exception as exc:
            logger.warning("subfinder error for %s: %s", domain, exc)
            return []

    async def _resolve_all(self, subdomains: list[str]) -> dict[str, list[str]]:
        """DNS A/AAAA resolution via dnspython. Returns {subdomain: [ip, ...]}."""
        try:
            import dns.asyncresolver
            import dns.exception
        except ImportError:
            logger.warning("dnspython not installed — DNS resolution unavailable")
            return {}

        result: dict[str, list[str]] = {}
        resolver = dns.asyncresolver.Resolver()
        resolver.timeout = 3
        resolver.lifetime = 5

        async def resolve_one(sub: str) -> None:
            ips: list[str] = []
            for rdtype in ("A", "AAAA"):
                try:
                    answers = await resolver.resolve(sub, rdtype)
                    ips.extend(str(r) for r in answers)
                except (dns.exception.DNSException, Exception):
                    pass
            if ips:
                result[sub] = ips

        # Resolve concurrently (but limit concurrency)
        semaphore = asyncio.Semaphore(20)

        async def resolve_with_sem(sub: str) -> None:
            async with semaphore:
                await resolve_one(sub)

        await asyncio.gather(*[resolve_with_sem(s) for s in subdomains])
        return result

    async def _write_fact(
        self,
        db: aiosqlite.Connection,
        operation_id: str,
        trait: str,
        value: str,
        category: str,
    ) -> int:
        """Write a single fact to the DB and broadcast. Returns 1 on success."""
        fact_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        await db.execute(
            "INSERT INTO facts "
            "(id, trait, value, category, source_technique_id, "
            "source_target_id, operation_id, score, collected_at) "
            "VALUES (?, ?, ?, ?, NULL, NULL, ?, 1, ?)",
            (fact_id, trait, value, category, operation_id, now),
        )
        payload = {
            "id": fact_id,
            "trait": trait,
            "value": value,
            "category": category,
            "operation_id": operation_id,
        }
        await ws_manager.broadcast(operation_id, "fact.new", payload)
        return 1

    async def _create_target_if_missing(
        self,
        db: aiosqlite.Connection,
        operation_id: str,
        hostname: str,
        ip_address: str,
    ) -> bool:
        """Create a Target record if no target with this IP exists in the operation."""
        cursor = await db.execute(
            "SELECT id FROM targets WHERE ip_address = ? AND operation_id = ?",
            (ip_address, operation_id),
        )
        if await cursor.fetchone() is not None:
            return False  # Already exists

        target_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        await db.execute(
            """
            INSERT INTO targets
                (id, hostname, ip_address, os, role, network_segment,
                 is_compromised, privilege_level, operation_id, created_at)
            VALUES (?, ?, ?, NULL, 'discovered', 'external', 0, NULL, ?, ?)
            """,
            (target_id, hostname, ip_address, operation_id, now),
        )
        await db.commit()
        return True

    async def _mock_result(
        self,
        db: aiosqlite.Connection,
        operation_id: str,
        domain: str,
    ) -> OSINTResult:
        """Return deterministic mock result for local development / CI."""
        t_start = time.monotonic()
        facts_written = 0
        targets_created = 0
        ips_seen: set[str] = set()

        for info in _MOCK_SUBDOMAINS:
            facts_written += await self._write_fact(
                db=db, operation_id=operation_id,
                trait="osint.subdomain", value=info.subdomain, category="osint",
            )
            for ip in info.resolved_ips:
                facts_written += await self._write_fact(
                    db=db, operation_id=operation_id,
                    trait="osint.resolved_ip", value=f"{info.subdomain}:{ip}", category="osint",
                )
                if ip not in ips_seen:
                    ips_seen.add(ip)
                    created = await self._create_target_if_missing(
                        db=db, operation_id=operation_id,
                        hostname=info.subdomain, ip_address=ip,
                    )
                    if created:
                        targets_created += 1

        await db.commit()
        scan_duration = time.monotonic() - t_start

        return OSINTResult(
            domain=domain,
            operation_id=operation_id,
            subdomains_found=len(_MOCK_SUBDOMAINS),
            ips_resolved=len(ips_seen),
            targets_created=targets_created,
            facts_written=facts_written,
            scan_duration_sec=round(scan_duration, 3),
            sources_used=["mock"],
            subdomains=list(_MOCK_SUBDOMAINS),
        )
