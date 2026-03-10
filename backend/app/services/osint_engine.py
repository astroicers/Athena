# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: [TODO: contact email]

"""OSINTEngine — delegates subdomain enumeration to MCP and processes results."""

import logging
import time
import uuid
from datetime import datetime, timezone

import asyncpg

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
        db: asyncpg.Connection,
        operation_id: str,
        domain: str,
        max_subdomains: int | None = None,
    ) -> OSINTResult:
        """Enumerate subdomains for a domain via MCP and persist results.

        Steps:
        1. If mock mode, return deterministic mock result.
        2. Delegate discovery to MCP osint-recon server.
        3. Create Target records in DB for discovered hosts.
        4. Write facts and broadcast events.
        5. Return OSINTResult.
        """
        limit = max_subdomains or settings.OSINT_MAX_SUBDOMAINS
        t_start = time.monotonic()

        if settings.MOCK_C2_ENGINE:
            return await self._mock_result(
                db=db,
                operation_id=operation_id,
                domain=domain,
            )

        # Steps 2–5: MCP-only (no direct crtsh/subfinder/DNS execution)
        if not settings.MCP_ENABLED:
            raise ConnectionError(
                "MCP is required for OSINT discovery (MCP_ENABLED=false)"
            )

        subdomain_infos, sources_used = await self._discover_via_mcp(domain, limit)

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

    async def _discover_via_mcp(
        self, domain: str, limit: int
    ) -> "tuple[list[SubdomainInfo], list[str]]":
        """Delegate OSINT discovery to MCP osint-recon server."""
        import json as _json

        from app.services.mcp_client_manager import get_mcp_manager

        manager = get_mcp_manager()
        if manager is None or not manager.is_connected("osint-recon"):
            raise ConnectionError("MCP osint-recon server is not connected")

        sources_used: list[str] = []

        # 1. crt.sh query
        crtsh_result = await manager.call_tool(
            "osint-recon", "crtsh_query", {"domain": domain}
        )
        crtsh_subs = self._parse_mcp_subdomains(crtsh_result)
        if crtsh_subs:
            sources_used.append("crtsh")

        # 2. subfinder query (if enabled)
        subfinder_subs: set[str] = set()
        if settings.SUBFINDER_ENABLED:
            sf_result = await manager.call_tool(
                "osint-recon", "subfinder_query", {"domain": domain}
            )
            subfinder_subs = set(self._parse_mcp_subdomains(sf_result))
            if subfinder_subs:
                sources_used.append("subfinder")

        # 3. Deduplicate
        all_subs = sorted((set(crtsh_subs) | subfinder_subs) - {domain})[:limit]

        # 4. DNS resolve
        if all_subs:
            resolve_result = await manager.call_tool(
                "osint-recon", "dns_resolve", {"subdomains": ",".join(all_subs)}
            )
            resolved = self._parse_mcp_resolved_ips(resolve_result)
        else:
            resolved = {}

        # 5. Build SubdomainInfo list
        subdomain_infos: list[SubdomainInfo] = []
        for sub in all_subs:
            ips = resolved.get(sub, [])
            source = "crtsh" if sub in crtsh_subs else "subfinder"
            subdomain_infos.append(SubdomainInfo(subdomain=sub, resolved_ips=ips, source=source))

        return subdomain_infos, sources_used

    @staticmethod
    def _parse_mcp_subdomains(mcp_result: dict) -> list[str]:
        """Parse osint.subdomain facts from MCP result."""
        import json as _json

        text_parts = [
            block.get("text", "")
            for block in mcp_result.get("content", [])
            if isinstance(block, dict) and block.get("type") == "text"
        ]
        text = "\n".join(text_parts)
        try:
            data = _json.loads(text)
        except _json.JSONDecodeError:
            return []
        return [
            f["value"]
            for f in data.get("facts", [])
            if f.get("trait") == "osint.subdomain"
        ]

    @staticmethod
    def _parse_mcp_resolved_ips(mcp_result: dict) -> dict[str, list[str]]:
        """Parse osint.resolved_ip facts from MCP result → {subdomain: [ip, ...]}."""
        import json as _json

        text_parts = [
            block.get("text", "")
            for block in mcp_result.get("content", [])
            if isinstance(block, dict) and block.get("type") == "text"
        ]
        text = "\n".join(text_parts)
        try:
            data = _json.loads(text)
        except _json.JSONDecodeError:
            return {}
        resolved: dict[str, list[str]] = {}
        for f in data.get("facts", []):
            if f.get("trait") == "osint.resolved_ip" and ":" in f.get("value", ""):
                sub, ip = f["value"].rsplit(":", 1)
                resolved.setdefault(sub, []).append(ip)
        return resolved

    async def _write_fact(
        self,
        db: asyncpg.Connection,
        operation_id: str,
        trait: str,
        value: str,
        category: str,
    ) -> int:
        """Write a single fact to the DB and broadcast. Returns 1 on success."""
        fact_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        await db.execute(
            "INSERT INTO facts "
            "(id, trait, value, category, source_technique_id, "
            "source_target_id, operation_id, score, collected_at) "
            "VALUES ($1, $2, $3, $4, NULL, NULL, $5, 1, $6) ON CONFLICT DO NOTHING",
            fact_id, trait, value, category, operation_id, now,
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
        db: asyncpg.Connection,
        operation_id: str,
        hostname: str,
        ip_address: str,
    ) -> bool:
        """Create a Target record if no target with this IP exists in the operation.

        Uses INSERT OR IGNORE with UNIQUE(ip_address, operation_id) constraint
        to avoid race conditions under concurrent discovery.
        """
        target_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        result = await db.execute(
            """
            INSERT INTO targets
                (id, hostname, ip_address, os, role, network_segment,
                 is_compromised, privilege_level, operation_id, created_at)
            VALUES ($1, $2, $3, NULL, 'discovered', 'external', FALSE, NULL, $4, $5)
            ON CONFLICT DO NOTHING
            """,
            target_id, hostname, ip_address, operation_id, now,
        )
        return result.split()[-1] != '0' if result else False

    async def _mock_result(
        self,
        db: asyncpg.Connection,
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
