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

"""ReconEngine — runs nmap scans and writes results to the facts table."""

import asyncio
import logging
import time
import uuid
from datetime import datetime, timezone

import aiosqlite
import nmap

from app.config import settings
from app.models.recon import ReconResult, ServiceInfo
from app.ws_manager import ws_manager

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Mock data — returned when settings.MOCK_CALDERA is True
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
        db: aiosqlite.Connection,
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
        db.row_factory = aiosqlite.Row

        # ------------------------------------------------------------------
        # Step 1: Fetch target IP
        # ------------------------------------------------------------------
        cursor = await db.execute(
            "SELECT ip_address FROM targets WHERE id = ? AND operation_id = ?",
            (target_id, operation_id),
        )
        row = await cursor.fetchone()
        if row is None:
            raise ValueError(
                f"Target {target_id!r} not found in operation {operation_id!r}"
            )
        ip_address: str = row["ip_address"]

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
        if settings.MOCK_CALDERA:
            return await self._mock_result(
                db=db,
                operation_id=operation_id,
                target_id=target_id,
                ip_address=ip_address,
            )

        # ------------------------------------------------------------------
        # Step 3: Run nmap in executor (blocking call)
        # ------------------------------------------------------------------
        loop = asyncio.get_event_loop()
        t_start = time.monotonic()
        nm: nmap.PortScanner = await loop.run_in_executor(
            None,
            self._run_nmap,
            ip_address,
        )
        scan_duration = time.monotonic() - t_start

        # ------------------------------------------------------------------
        # Step 4: Parse results
        # ------------------------------------------------------------------
        services: list[ServiceInfo] = []
        os_guess: str | None = None

        if ip_address in nm.all_hosts():
            host_data = nm[ip_address]

            # OS detection
            if "osmatch" in host_data and host_data["osmatch"]:
                raw_os = host_data["osmatch"][0].get("name", "")
                os_guess = raw_os.replace(" ", "_") if raw_os else None

            # Open ports / services
            for proto in host_data.all_protocols():
                for port in host_data[proto].keys():
                    port_data = host_data[proto][port]
                    if port_data.get("state") != "open":
                        continue
                    svc_name = port_data.get("name", "unknown")
                    svc_version = (
                        " ".join(
                            filter(
                                None,
                                [
                                    port_data.get("product", ""),
                                    port_data.get("version", ""),
                                    port_data.get("extrainfo", ""),
                                ],
                            )
                        ).strip()
                        or "unknown"
                    )
                    services.append(
                        ServiceInfo(
                            port=port,
                            protocol=proto,
                            service=svc_name,
                            version=svc_version,
                            state="open",
                        )
                    )

        # Raw XML from the scan command string is not readily available via
        # python-nmap's high-level API; we leave raw_xml as the CSV summary
        # produced by nm.csv() which is close enough for audit purposes.
        raw_xml: str | None = nm.get_nmap_last_output() or None

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

        # Step 6: Update target OS in DB
        if os_guess:
            await db.execute(
                "UPDATE targets SET os = ? WHERE id = ?",
                (os_guess, target_id),
            )
            await db.commit()

        # ------------------------------------------------------------------
        # Step 8: Return result
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

    @staticmethod
    def _run_nmap(ip: str) -> nmap.PortScanner:
        """Synchronous nmap call — intended to run inside an executor."""
        nm = nmap.PortScanner()
        nm.scan(
            hosts=ip,
            arguments=(
                "-sV -Pn --script=banner "
                "-p 21,22,23,25,53,80,110,135,139,143,443,445,"
                "1433,3000,3306,3389,3500,5432,5900,6379,"
                "8080,8443,8888,9090,27017"
            ),
        )
        return nm

    async def _mock_result(
        self,
        db: aiosqlite.Connection,
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

    async def _write_facts(
        self,
        db: aiosqlite.Connection,
        operation_id: str,
        target_id: str,
        ip_address: str,
        services: list[ServiceInfo],
        os_guess: str | None,
    ) -> int:
        """Persist facts and broadcast WebSocket events. Returns count written."""
        now = datetime.now(timezone.utc).isoformat()
        facts_written = 0

        async def _insert_fact(trait: str, value: str, category: str) -> None:
            nonlocal facts_written
            fact_id = str(uuid.uuid4())
            await db.execute(
                "INSERT INTO facts "
                "(id, trait, value, category, source_technique_id, "
                "source_target_id, operation_id, score, collected_at) "
                "VALUES (?, ?, ?, ?, NULL, ?, ?, 1, ?)",
                (fact_id, trait, value, category, target_id, operation_id, now),
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

        await db.commit()
        return facts_written
