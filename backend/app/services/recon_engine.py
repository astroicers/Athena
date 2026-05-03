# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: azz093093.830330@gmail.com

"""ReconEngine — delegates nmap scans to MCP and writes results to the facts table."""

import asyncio
import logging
import time
import uuid
from datetime import datetime, timezone

import asyncpg

from app.config import settings
from app.models.enums import FactCategory
from app.models.recon import ReconResult, ServiceInfo
from app.utils.enum_safety import ensure_enum_value
from app.ws_manager import ws_manager

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Mock data — returned when settings.MOCK_C2_ENGINE is True
# ---------------------------------------------------------------------------
_MOCK_SERVICES = [
    ServiceInfo(port=22,  protocol="tcp", service="ssh",  version="OpenSSH 7.4",  state="open"),
    ServiceInfo(port=80,  protocol="tcp", service="http", version="Apache 2.4.6",  state="open"),
    ServiceInfo(port=21,  protocol="tcp", service="ftp",  version="vsftpd 3.0.2", state="open"),
]


class ReconEngine:
    """Reconnaissance phase — wraps python-nmap and writes facts to the DB."""

    async def scan(
        self,
        db: asyncpg.Connection,
        operation_id: str,
        target_id: str,
    ) -> ReconResult:
        """Run an nmap scan against the target and persist results as facts.

        Steps:
        1. Fetch target IP from ``targets`` table.
        2. If mock mode is active, return a mock ReconResult.
        3. Execute nmap in a thread-pool executor (blocking I/O).
        4. Parse nmap output into ServiceInfo objects.
        5. Write facts to the ``facts`` table.
        6. Update ``targets.os`` if nmap detected an OS.
        7. Broadcast a ``fact.new`` WebSocket event per fact written.
        8. Return a fully-populated ReconResult.
        """
        # ------------------------------------------------------------------
        # Step 1: Fetch target IP
        # ------------------------------------------------------------------
        row = await db.fetchrow(
            "SELECT ip_address, hostname FROM targets WHERE id = $1 AND operation_id = $2",
            target_id, operation_id,
        )
        if row is None:
            raise ValueError(
                f"Target {target_id!r} not found in operation {operation_id!r}"
            )
        ip_address: str = row["ip_address"]
        hostname: str | None = row["hostname"]

        # ------------------------------------------------------------------
        # Step 1b: Scope validation — check engagement ROE
        # ------------------------------------------------------------------
        from app.services.scope_validator import ScopeValidator, ScopeViolationError
        validator = ScopeValidator()
        scope_result = await validator.validate_target(db, operation_id, ip_address)
        if not scope_result.in_scope:
            logger.warning(
                "Scope violation blocked recon: %s — %s", ip_address, scope_result.reason
            )
            raise ScopeViolationError(
                f"Target {ip_address!r} is out of scope: {scope_result.reason}"
            )

        # ------------------------------------------------------------------
        # Step 2: Mock mode — skip real nmap
        # ------------------------------------------------------------------
        if settings.MOCK_C2_ENGINE:
            return await self._mock_result(
                db=db,
                operation_id=operation_id,
                target_id=target_id,
                ip_address=ip_address,
            )

        # ------------------------------------------------------------------
        # Step 3: MCP-only nmap (no direct execution)
        # ------------------------------------------------------------------
        if not settings.MCP_ENABLED:
            raise ConnectionError(
                "MCP is required for nmap scanning (MCP_ENABLED=false)"
            )

        try:
            services, os_guess, raw_xml, scan_duration = await asyncio.wait_for(
                self._scan_via_mcp(ip_address),
                timeout=settings.NMAP_SCAN_TIMEOUT_SEC,
            )
        except asyncio.TimeoutError:
            raise ConnectionError(
                f"MCP nmap_scan timed out after {settings.NMAP_SCAN_TIMEOUT_SEC}s"
            )

        if not services:
            logger.warning(
                "nmap scan returned 0 services for %s — raw response: %s",
                ip_address,
                (raw_xml or "N/A")[:500],
            )

        # ------------------------------------------------------------------
        # Steps 5–7: Write facts and broadcast events
        # ------------------------------------------------------------------
        facts_written = await self._write_facts(
            db=db,
            operation_id=operation_id,
            target_id=target_id,
            ip_address=ip_address,
            services=services,
            os_guess=os_guess,
        )

        # Step 5b: Write T1046 execution record so KillChainEnforcer sees TA0043 complete
        await self._write_technique_execution(db, operation_id, target_id, facts_written)

        # Step 6: Update target OS in DB
        if os_guess:
            await db.execute(
                "UPDATE targets SET os = $1 WHERE id = $2",
                os_guess, target_id,
            )

        # ------------------------------------------------------------------
        # Step 8: CVE enrichment (graceful fallback — never breaks recon)
        # ------------------------------------------------------------------
        vuln_findings: list = []
        if settings.VULN_LOOKUP_ENABLED and services:
            try:
                from app.services.vuln_lookup import VulnLookupService
                vuln_findings = await VulnLookupService().enrich_services(
                    db=db,
                    services=services,
                    operation_id=operation_id,
                    target_id=target_id,
                ) or []
            except Exception:
                logger.warning("CVE enrichment failed, continuing without vulnerability data")

        # ------------------------------------------------------------------
        # Step 8b: Web reconnaissance (graceful fallback — never breaks recon)
        # ------------------------------------------------------------------
        http_services = [
            s for s in services
            if s.service in ("http", "https", "http-proxy", "http-alt")
        ]
        if http_services and settings.MCP_ENABLED:
            try:
                from app.services.mcp_client_manager import get_mcp_manager
                manager = get_mcp_manager()
                if manager and manager.is_connected("web-scanner"):
                    http_ports = [s.port for s in http_services]
                    probe_result = await manager.call_tool(
                        "web-scanner", "web_http_probe",
                        {"target": ip_address, "ports": http_ports},
                    )
                    await self._write_web_facts(
                        db=db,
                        operation_id=operation_id,
                        target_id=target_id,
                        probe_result=probe_result,
                    )
                    # Chain SSRF probe after HTTP probe (use hostname for vhost-dependent paths)
                    ssrf_target = hostname or ip_address
                    ssrf_url = f"http://{ssrf_target}"
                    try:
                        ssrf_result = await manager.call_tool(
                            "web-scanner", "web_ssrf_probe",
                            {"target_url": ssrf_url},
                        )
                        await self._write_web_facts(
                            db=db,
                            operation_id=operation_id,
                            target_id=target_id,
                            probe_result=ssrf_result,
                        )
                    except Exception:
                        logger.warning(
                            "SSRF probe failed for %s, continuing",
                            ssrf_target,
                        )
            except Exception:
                logger.warning(
                    "Web reconnaissance failed for %s, continuing without web data",
                    ip_address,
                )
        elif not http_services and hostname and settings.MCP_ENABLED:
            # Fallback: nmap found no HTTP services but target has a hostname
            # (e.g. CloudFront/S3 endpoints that don't respond to nmap).
            # Probe ports 80/443 directly using the hostname.
            try:
                from app.services.mcp_client_manager import get_mcp_manager
                manager = get_mcp_manager()
                if manager and manager.is_connected("web-scanner"):
                    probe_result = await manager.call_tool(
                        "web-scanner", "web_http_probe",
                        {"target": hostname, "ports": [80, 443]},
                    )
                    await self._write_web_facts(
                        db=db,
                        operation_id=operation_id,
                        target_id=target_id,
                        probe_result=probe_result,
                    )
                    try:
                        ssrf_result = await manager.call_tool(
                            "web-scanner", "web_ssrf_probe",
                            {"target_url": f"http://{hostname}"},
                        )
                        await self._write_web_facts(
                            db=db,
                            operation_id=operation_id,
                            target_id=target_id,
                            probe_result=ssrf_result,
                        )
                    except Exception:
                        logger.warning(
                            "SSRF fallback probe failed for %s, continuing",
                            hostname,
                        )
            except Exception:
                logger.warning(
                    "Web fallback probe failed for %s, continuing",
                    hostname,
                )

        # ------------------------------------------------------------------
        # Step 8.5: Exploit validation (graceful fallback — never breaks recon)
        # ------------------------------------------------------------------
        if settings.EXPLOIT_VALIDATION_ENABLED and settings.VULN_LOOKUP_ENABLED:
            try:
                from app.services.exploit_validator import ExploitValidator
                if vuln_findings:
                    await ExploitValidator().validate(
                        db=db,
                        findings=vuln_findings,
                        operation_id=operation_id,
                        target_id=target_id,
                    )
            except Exception:
                logger.warning(
                    "Exploit validation failed, continuing without validation data"
                )

        # ------------------------------------------------------------------
        # Step 9: Return result
        # ------------------------------------------------------------------
        return ReconResult(
            target_id=target_id,
            operation_id=operation_id,
            ip_address=ip_address,
            os_guess=os_guess,
            services=services,
            facts_written=facts_written,
            scan_duration_sec=round(scan_duration, 3),
            raw_xml=raw_xml,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _scan_via_mcp(
        self, ip_address: str
    ) -> "tuple[list[ServiceInfo], str | None, str | None, float]":
        """Delegate nmap scan to MCP nmap-scanner server."""
        import json as _json

        from app.services.mcp_client_manager import get_mcp_manager

        manager = get_mcp_manager()
        if manager is None or not manager.is_connected("nmap-scanner"):
            raise ConnectionError("MCP nmap-scanner server is not connected")

        t_start = time.monotonic()
        result = await manager.call_tool(
            "nmap-scanner", "nmap_scan", {
                "target": ip_address,
                "ports": (
                    "21,22,23,25,53,80,110,135,139,143,443,445,"
                    "1433,3000,3306,3389,3500,5432,5900,5985,5986,6379,"
                    "8080,8443,8888,9090,27017"
                ),
            }
        )
        scan_duration = time.monotonic() - t_start

        # Parse MCP result → ServiceInfo objects
        services: list[ServiceInfo] = []
        os_guess: str | None = None
        raw_xml: str | None = None

        text_parts = [
            block.get("text", "")
            for block in result.get("content", [])
            if isinstance(block, dict) and block.get("type") == "text"
        ]
        text = "\n".join(text_parts)

        try:
            data = _json.loads(text)
        except _json.JSONDecodeError:
            logger.warning("MCP nmap_scan returned non-JSON: %s", text[:200])
            return services, os_guess, raw_xml, scan_duration

        raw_xml = data.get("raw_output")

        for fact in data.get("facts", []):
            trait = fact.get("trait", "")
            value = fact.get("value", "")

            if trait == "service.open_port" and "/" in value:
                parts = value.split("/", 3)
                if len(parts) >= 4:
                    services.append(ServiceInfo(
                        port=int(parts[0]),
                        protocol=parts[1],
                        service=parts[2],
                        version=parts[3].replace("_", " "),
                        state="open",
                    ))
            elif trait == "host.os":
                os_guess = value

        return services, os_guess, raw_xml, scan_duration

    async def _mock_result(
        self,
        db: asyncpg.Connection,
        operation_id: str,
        target_id: str,
        ip_address: str,
    ) -> ReconResult:
        """Return a deterministic mock result for local development / CI."""
        t_start = time.monotonic()
        facts_written = await self._write_facts(
            db=db,
            operation_id=operation_id,
            target_id=target_id,
            ip_address=ip_address,
            services=_MOCK_SERVICES,
            os_guess="Linux_2.6.x",
        )
        await self._write_technique_execution(db, operation_id, target_id, facts_written)
        scan_duration = time.monotonic() - t_start

        return ReconResult(
            target_id=target_id,
            operation_id=operation_id,
            ip_address=ip_address,
            os_guess="Linux_2.6.x",
            services=list(_MOCK_SERVICES),
            facts_written=facts_written,
            scan_duration_sec=round(scan_duration, 3),
            raw_xml=None,
        )

    async def _write_technique_execution(
        self, db: asyncpg.Connection, operation_id: str,
        target_id: str, facts_written: int,
    ) -> None:
        """Write T1046 record so KillChainEnforcer sees TA0043 complete."""
        import uuid as _uuid
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        await db.execute(
            "INSERT INTO technique_executions "
            "(id, technique_id, target_id, operation_id, engine, status, "
            " result_summary, facts_collected_count, started_at, completed_at) "
            "VALUES ($1, $2, $3, $4, 'mcp', 'success', $5, $6, $7, $7) "
            "ON CONFLICT DO NOTHING",
            str(_uuid.uuid4()), "T1046", target_id, operation_id,
            f"MCP nmap scan: {facts_written} facts collected",
            facts_written, now,
        )

    async def _write_web_facts(
        self,
        db: asyncpg.Connection,
        operation_id: str,
        target_id: str,
        probe_result: dict,
    ) -> int:
        """Parse web probe MCP result and persist web facts. Returns count written."""
        import json as _json

        now = datetime.now(timezone.utc)
        facts_written = 0

        text_parts = [
            block.get("text", "")
            for block in probe_result.get("content", [])
            if isinstance(block, dict) and block.get("type") == "text"
        ]
        text = "\n".join(text_parts)

        try:
            data = _json.loads(text)
        except _json.JSONDecodeError:
            logger.warning("MCP web_http_probe returned non-JSON: %s", text[:200])
            return 0

        for fact in data.get("facts", []):
            trait = fact.get("trait", "")
            value = fact.get("value", "")
            if not trait or not value:
                continue

            # Determine category from trait prefix
            if trait.startswith("web.vuln"):
                raw_cat = "vulnerability"
            elif trait.startswith("web.http.waf"):
                raw_cat = "defense"
            else:
                raw_cat = "web"
            category = ensure_enum_value(FactCategory, raw_cat, fallback_member=FactCategory.WEB)

            fact_id = str(uuid.uuid4())
            await db.execute(
                "INSERT INTO facts "
                "(id, trait, value, category, source_technique_id, "
                "source_target_id, operation_id, score, collected_at) "
                "VALUES ($1, $2, $3, $4, NULL, $5, $6, 1, $7) ON CONFLICT DO NOTHING",
                fact_id, trait, value, category, target_id, operation_id, now,
            )
            fact_payload = {
                "id": fact_id,
                "trait": trait,
                "value": value,
                "category": category,
                "source_target_id": target_id,
                "operation_id": operation_id,
            }
            await ws_manager.broadcast(operation_id, "fact.new", fact_payload)
            facts_written += 1

        return facts_written

    async def _write_facts(
        self,
        db: asyncpg.Connection,
        operation_id: str,
        target_id: str,
        ip_address: str,
        services: list[ServiceInfo],
        os_guess: str | None,
    ) -> int:
        """Persist facts and broadcast WebSocket events. Returns count written."""
        now = datetime.now(timezone.utc)
        facts_written = 0

        async def _insert_fact(trait: str, value: str, category: str | FactCategory) -> None:
            category = ensure_enum_value(FactCategory, category if isinstance(category, str) else category.value, fallback_member=FactCategory.HOST)
            nonlocal facts_written
            fact_id = str(uuid.uuid4())
            await db.execute(
                "INSERT INTO facts "
                "(id, trait, value, category, source_technique_id, "
                "source_target_id, operation_id, score, collected_at) "
                "VALUES ($1, $2, $3, $4, NULL, $5, $6, 1, $7) ON CONFLICT DO NOTHING",
                fact_id, trait, value, category, target_id, operation_id, now,
            )
            # Broadcast unconditionally — DB-level UNIQUE index handles dedup
            fact_payload = {
                "id": fact_id,
                "trait": trait,
                "value": value,
                "category": category,
                "source_target_id": target_id,
                "operation_id": operation_id,
            }
            await ws_manager.broadcast(operation_id, "fact.new", fact_payload)
            facts_written += 1

        # One fact per open port/service
        # Value format: "22/tcp/ssh/OpenSSH_7.4" (spaces → "_")
        for svc in services:
            version_normalized = svc.version.replace(" ", "_")
            value = f"{svc.port}/{svc.protocol}/{svc.service}/{version_normalized}"
            await _insert_fact(
                trait="service.open_port",
                value=value,
                category="service",
            )

        # One fact for the IP address
        await _insert_fact(
            trait="network.host.ip",
            value=ip_address,
            category="network",
        )

        # One fact for OS if detected
        if os_guess:
            await _insert_fact(
                trait="host.os",
                value=os_guess,
                category="host",
            )

        return facts_written
