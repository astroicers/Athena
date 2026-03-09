# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: [TODO: contact email]

"""SPEC-044: Dynamic Validation Engine — pre-checks before exploit recommendations."""

import asyncio
import logging
import re
import socket
from dataclasses import dataclass, field

import aiosqlite

logger = logging.getLogger(__name__)

# Only validate exploit-related tactics
_EXPLOIT_TACTICS = {"TA0001", "TA0002", "TA0004"}
# TA0001 = Initial Access
# TA0002 = Execution
# TA0004 = Privilege Escalation

VALIDATION_TIMEOUT = 5  # seconds


@dataclass
class ValidationResult:
    outcome: str          # "validated" | "failed" | "skipped"
    checks: list[dict] = field(default_factory=list)
    delta: float = 0.0    # confidence adjustment


class ValidationEngine:
    """Dynamic validation engine between Orient->Decide.

    Runs three lightweight pre-checks on exploit recommendations and
    adjusts confidence scores:
      - validated: +0.15 (all passed)
      - failed:    -0.30 (any failed)
      - skipped:    0.00 (non-exploit or all timed out)
    """

    async def validate(
        self, db: aiosqlite.Connection, recommendation: dict,
        operation_id: str,
    ) -> ValidationResult:
        """Run pre-validation checks on an exploit recommendation."""
        technique_id = recommendation.get("recommended_technique_id", "")
        target_id = recommendation.get("target_id")

        # 1. Check tactic — skip non-exploit tactics
        tactic_id = await self._get_tactic_id(db, technique_id)
        if tactic_id not in _EXPLOIT_TACTICS:
            return ValidationResult("skipped", [], 0.0)

        # 2. Get target IP
        target_ip = await self._get_target_ip(db, target_id)
        if not target_ip:
            return ValidationResult("skipped", [], 0.0)

        # 3. Get service facts
        service_facts = await self._get_service_facts(
            db, operation_id, target_id,
        )

        # 4. Run checks in parallel
        checks = await self._run_checks(
            target_ip, technique_id, service_facts,
        )

        # 5. Determine outcome
        failed_checks = [c for c in checks if c["result"] == "failed"]
        passed_checks = [c for c in checks if c["result"] == "passed"]

        if failed_checks:
            return ValidationResult("failed", checks, -0.30)
        if passed_checks:
            return ValidationResult("validated", checks, +0.15)
        return ValidationResult("skipped", checks, 0.0)

    # ------------------------------------------------------------------
    # Check orchestration
    # ------------------------------------------------------------------

    async def _run_checks(
        self, target_ip: str, technique_id: str,
        service_facts: list[dict],
    ) -> list[dict]:
        """Run three validation checks in parallel, each with timeout."""
        tasks = [
            self._check_port_reachability(target_ip, service_facts),
            self._check_service_banner(target_ip, service_facts),
            self._check_version_range(technique_id, service_facts),
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        check_names = ["port_reachability", "service_banner", "version_range"]
        checks = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                checks.append({
                    "name": check_names[i],
                    "result": "skipped",
                    "detail": str(result),
                })
            else:
                checks.append(result)
        return checks

    # ------------------------------------------------------------------
    # Individual checks
    # ------------------------------------------------------------------

    async def _check_port_reachability(
        self, target_ip: str, service_facts: list[dict],
    ) -> dict:
        """TCP connect to verify target port is still reachable."""
        port = self._extract_port(service_facts)
        if not port:
            return {
                "name": "port_reachability",
                "result": "skipped",
                "detail": "no port info available",
            }

        try:
            loop = asyncio.get_event_loop()
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(VALIDATION_TIMEOUT)
            await asyncio.wait_for(
                loop.run_in_executor(
                    None, sock.connect, (target_ip, port),
                ),
                timeout=VALIDATION_TIMEOUT,
            )
            sock.close()
            return {
                "name": "port_reachability",
                "result": "passed",
                "detail": f"port {port} open",
            }
        except (asyncio.TimeoutError, OSError) as e:
            return {
                "name": "port_reachability",
                "result": "failed",
                "detail": str(e),
            }

    async def _check_service_banner(
        self, target_ip: str, service_facts: list[dict],
    ) -> dict:
        """Compare expected service banner with actual banner."""
        expected_banner = self._extract_banner(service_facts)
        if not expected_banner:
            return {
                "name": "service_banner",
                "result": "skipped",
                "detail": "no expected banner info available",
            }

        port = self._extract_port(service_facts)
        if not port:
            return {
                "name": "service_banner",
                "result": "skipped",
                "detail": "no port for banner grab",
            }

        try:
            loop = asyncio.get_event_loop()
            actual_banner = await asyncio.wait_for(
                loop.run_in_executor(
                    None, self._grab_banner, target_ip, port,
                ),
                timeout=VALIDATION_TIMEOUT,
            )
            if expected_banner.lower() in actual_banner.lower():
                return {
                    "name": "service_banner",
                    "result": "passed",
                    "detail": f"banner matches: {actual_banner[:80]}",
                }
            return {
                "name": "service_banner",
                "result": "failed",
                "detail": (
                    f"expected '{expected_banner}', "
                    f"got '{actual_banner[:80]}'"
                ),
            }
        except (asyncio.TimeoutError, OSError) as e:
            # Fail-open: timeout is skipped
            return {
                "name": "service_banner",
                "result": "skipped",
                "detail": f"timeout: {e}",
            }

    async def _check_version_range(
        self, technique_id: str, service_facts: list[dict],
    ) -> dict:
        """Check CVE affected version range vs detected version.

        Currently only does existence check. Full CPE match / NVD
        version range comparison deferred to future SPEC.
        """
        detected_version = self._extract_version(service_facts)
        if not detected_version:
            return {
                "name": "version_range",
                "result": "skipped",
                "detail": "no version detected in service facts",
            }

        # Phase 1: record detected version only, no range comparison
        return {
            "name": "version_range",
            "result": "skipped",
            "detail": (
                f"detected version: {detected_version}, "
                f"range check deferred to future SPEC"
            ),
        }

    # ------------------------------------------------------------------
    # Network helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _grab_banner(ip: str, port: int) -> str:
        """Synchronous banner grab (runs in executor)."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(VALIDATION_TIMEOUT)
        try:
            sock.connect((ip, port))
            banner = sock.recv(1024).decode(
                "utf-8", errors="replace",
            ).strip()
            return banner
        finally:
            sock.close()

    # ------------------------------------------------------------------
    # DB helpers
    # ------------------------------------------------------------------

    async def _get_tactic_id(
        self, db: aiosqlite.Connection, technique_id: str,
    ) -> str:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT tactic_id FROM techniques WHERE mitre_id = ? LIMIT 1",
            (technique_id,),
        )
        row = await cursor.fetchone()
        return row["tactic_id"] if row else ""

    async def _get_target_ip(
        self, db: aiosqlite.Connection, target_id: str,
    ) -> str | None:
        if not target_id:
            return None
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT ip_address FROM targets WHERE id = ?", (target_id,),
        )
        row = await cursor.fetchone()
        return row["ip_address"] if row else None

    async def _get_service_facts(
        self, db: aiosqlite.Connection,
        operation_id: str, target_id: str,
    ) -> list[dict]:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT trait, value FROM facts "
            "WHERE operation_id = ? AND source_target_id = ? "
            "AND trait LIKE 'service.%' "
            "ORDER BY collected_at DESC LIMIT 20",
            (operation_id, target_id),
        )
        return [dict(r) for r in await cursor.fetchall()]

    # ------------------------------------------------------------------
    # Value extraction helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_port(service_facts: list[dict]) -> int | None:
        """Extract port number from service facts."""
        for f in service_facts:
            if "port" in f["trait"]:
                # Try "21/tcp" format
                match = re.search(r"(\d+)/", f["value"])
                if match:
                    return int(match.group(1))
                # Fallback: bare number
                match = re.search(r"(\d+)", f["value"])
                if match:
                    port = int(match.group(1))
                    if 1 <= port <= 65535:
                        return port
        return None

    @staticmethod
    def _extract_banner(service_facts: list[dict]) -> str | None:
        """Extract expected banner from service facts."""
        for f in service_facts:
            if "banner" in f["value"].lower() or "service" in f["trait"]:
                return f["value"]
        return None

    @staticmethod
    def _extract_version(service_facts: list[dict]) -> str | None:
        """Extract version number from service facts."""
        for f in service_facts:
            match = re.search(r"(\d+\.\d+[\.\d]*)", f["value"])
            if match:
                return match.group(1)
        return None
