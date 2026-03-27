# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: azz093093.830330@gmail.com

"""SPEC-044: Dynamic Validation Engine — pre-checks before exploit recommendations."""

import asyncio
import logging
import re
import socket
from dataclasses import dataclass, field

import asyncpg

logger = logging.getLogger(__name__)

# Only validate exploit-related tactics
_EXPLOIT_TACTICS = {"TA0001", "TA0002", "TA0004"}
# TA0001 = Initial Access
# TA0002 = Execution
# TA0004 = Privilege Escalation

VALIDATION_TIMEOUT = 5  # seconds


def _parse_version(version_str: str) -> tuple[int, ...]:
    """Parse a version string like '2.3.4' into a comparable tuple (2, 3, 4).

    Extracts the first dotted-numeric sequence found in the string.
    Returns empty tuple if no version found.
    """
    match = re.search(r"(\d+(?:\.\d+)+)", version_str)
    if not match:
        return ()
    return tuple(int(x) for x in match.group(1).split("."))


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
        self, db: asyncpg.Connection, recommendation: dict,
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
        """Check if detected service version falls within known vulnerable ranges.

        Compares the version extracted from service facts against known vulnerable
        version patterns. Uses simple semantic version comparison — a full CPE/NVD
        integration would require an external data feed (out of scope).

        SPEC-028 Phase 4 / SPEC-044 B3 Phase 4.
        """
        detected_version = self._extract_version(service_facts)
        if not detected_version:
            return {
                "name": "version_range",
                "result": "skipped",
                "detail": "no version detected in service facts",
            }

        # Extract the service name from facts for context
        service_name = self._extract_service_name(service_facts)

        # Build combined context string for matching (service name + version + full fact values)
        context_parts = [service_name, detected_version]
        for f in service_facts:
            context_parts.append(f["value"])
        context_str = " ".join(context_parts)

        # Check against known vulnerable version patterns
        is_vulnerable, detail = self._check_known_vulnerable_versions(
            context_str, detected_version,
        )

        if is_vulnerable is True:
            return {
                "name": "version_range",
                "result": "passed",
                "detail": detail,
            }
        if is_vulnerable is False:
            return {
                "name": "version_range",
                "result": "failed",
                "detail": detail,
            }
        # Inconclusive — version detected but not in known patterns
        return {
            "name": "version_range",
            "result": "skipped",
            "detail": f"detected version: {detected_version}, no known range match",
        }

    @staticmethod
    def _extract_service_name(service_facts: list[dict]) -> str:
        """Extract service name from facts."""
        for f in service_facts:
            if "open_port" in f["trait"]:
                # Format: "21/tcp ftp vsftpd 2.3.4"
                parts = f["value"].split()
                if len(parts) >= 2:
                    return parts[1] if "/" in parts[0] else parts[0]
            if f["trait"] == "service.name":
                return f["value"]
        return ""

    @staticmethod
    def _check_known_vulnerable_versions(
        context: str, version: str,
    ) -> tuple[bool | None, str]:
        """Check version against known vulnerable service/version patterns.

        Args:
            context: Combined string of service name + version + fact values for matching.
            version: The detected version string.

        Returns (True, detail) if vulnerable, (False, detail) if patched/safe,
        (None, detail) if inconclusive.
        """
        context_lower = context.lower()
        version_lower = version.lower()

        # Known vulnerable version ranges: (service_pattern, min_vuln, max_vuln_exclusive, cve_hint)
        _KNOWN_RANGES: list[tuple[str, str, str, str]] = [
            ("vsftpd", "2.3.4", "2.3.5", "CVE-2011-2523 backdoor"),
            ("openssh", "4.3", "4.8", "CVE-2008-0166 weak keys"),
            ("openssh", "7.0", "7.6", "CVE-2016-10009 agent forwarding"),
            ("apache", "2.4.49", "2.4.50", "CVE-2021-41773 path traversal"),
            ("apache", "2.4.50", "2.4.51", "CVE-2021-42013 path traversal bypass"),
            ("nginx", "0.6.18", "1.13.3", "CVE-2017-7529 integer overflow"),
            ("proftpd", "1.3.5", "1.3.6", "CVE-2015-3306 mod_copy"),
            ("samba", "3.5.0", "4.6.4", "CVE-2017-7494 SambaCry"),
            ("unrealircd", "3.2.8.1", "3.2.8.2", "CVE-2010-2075 backdoor"),
            ("mysql", "5.5.0", "5.5.45", "CVE-2012-2122 auth bypass"),
            ("postgresql", "9.3.0", "9.3.5", "CVE-2014-0065 buffer overflow"),
            ("tomcat", "8.5.0", "8.5.51", "CVE-2020-1938 Ghostcat AJP"),
            ("tomcat", "9.0.0", "9.0.31", "CVE-2020-1938 Ghostcat AJP"),
            ("php", "8.1.0", "8.1.1", "CVE-2022-31626 buffer overflow"),
        ]

        for svc_pattern, min_ver, max_ver, cve_hint in _KNOWN_RANGES:
            if svc_pattern not in context_lower:
                continue
            # Compare semantic versions
            detected_parts = _parse_version(version)
            min_parts = _parse_version(min_ver)
            max_parts = _parse_version(max_ver)
            if not detected_parts:
                continue
            if min_parts <= detected_parts < max_parts:
                return True, (
                    f"version {version} in vulnerable range "
                    f"[{min_ver}, {max_ver}) — {cve_hint}"
                )
            if detected_parts >= max_parts:
                return False, (
                    f"version {version} >= {max_ver}, likely patched for {cve_hint}"
                )
        return None, f"version {version} not in any known vulnerable range"

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
        self, db: asyncpg.Connection, technique_id: str,
    ) -> str:
        row = await db.fetchrow(
            "SELECT tactic_id FROM techniques WHERE mitre_id = $1 LIMIT 1",
            technique_id,
        )
        return row["tactic_id"] if row else ""

    async def _get_target_ip(
        self, db: asyncpg.Connection, target_id: str,
    ) -> str | None:
        if not target_id:
            return None
        row = await db.fetchrow(
            "SELECT ip_address FROM targets WHERE id = $1", target_id,
        )
        return row["ip_address"] if row else None

    async def _get_service_facts(
        self, db: asyncpg.Connection,
        operation_id: str, target_id: str,
    ) -> list[dict]:
        rows = await db.fetch(
            "SELECT trait, value FROM facts "
            "WHERE operation_id = $1 AND source_target_id = $2 "
            "AND trait LIKE 'service.%' "
            "ORDER BY collected_at DESC LIMIT 20",
            operation_id, target_id,
        )
        return [dict(r) for r in rows]

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

    async def check(self, db: asyncpg.Connection, context: dict) -> "CheckResult":
        """PreActionValidator interface.

        Context keys:
            operation_id (str): The active operation.
            recommendation (dict): The recommendation being validated.
        """
        from app.services.validation_protocol import CheckResult
        result = await self.validate(
            db, context["recommendation"], context["operation_id"]
        )
        passed = getattr(result, "outcome", "passed") != "failed"
        delta = float(getattr(result, "delta", 0.0))
        return CheckResult(
            passed=passed,
            reason=getattr(result, "outcome", "validated"),
            confidence_delta=delta,
        )
