# Copyright 2026 Athena Contributors
# Licensed under the Apache License, Version 2.0
"""ReportGenerator — assembles PentestReport from DB (A.5)."""

import json
import logging
from datetime import datetime, timezone

import aiosqlite

from app.config import settings
from app.models.report import AttackStep, Finding, PentestReport

logger = logging.getLogger(__name__)

_MOCK_EXECUTIVE_SUMMARY = (
    "The engagement identified {vuln_count} vulnerabilities across {target_count} targets. "
    "Critical findings include exploitable CVEs requiring immediate remediation. "
    "OSINT discovery revealed {subdomain_count} subdomains expanding the attack surface. "
    "Initial access was {access_status}. "
    "Immediate action is recommended to address critical and high severity findings."
)


class ReportGenerator:
    async def generate(self, db: aiosqlite.Connection, operation_id: str) -> PentestReport:
        """Assemble PentestReport from all DB tables for this operation."""
        db.row_factory = aiosqlite.Row
        generated_at = datetime.now(timezone.utc).isoformat()

        # 1. Operation details
        cursor = await db.execute(
            "SELECT id, name, codename, strategic_intent, status FROM operations WHERE id = ?",
            (operation_id,),
        )
        op = await cursor.fetchone()
        op_name = op["name"] if op else "Unknown Operation"
        op_codename = op["codename"] if op else "UNKNOWN"

        # 2. Engagement / Scope
        cursor = await db.execute(
            "SELECT client_name, contact_email, in_scope, out_of_scope, status "
            "FROM engagements WHERE operation_id = ? ORDER BY created_at DESC LIMIT 1",
            (operation_id,),
        )
        eng = await cursor.fetchone()
        client_name = eng["client_name"] if eng else None
        contact_email = eng["contact_email"] if eng else None
        engagement_status = eng["status"] if eng else None
        in_scope: list[str] = json.loads(eng["in_scope"]) if eng else []
        out_of_scope: list[str] = json.loads(eng["out_of_scope"] or "[]") if eng else []

        # 3. Targets
        cursor = await db.execute(
            "SELECT id, ip_address, hostname, role FROM targets WHERE operation_id = ?",
            (operation_id,),
        )
        targets_rows = await cursor.fetchall()
        targets_by_id = {r["id"]: dict(r) for r in targets_rows}
        targets_discovered = len(targets_rows)

        # 4. Subdomain count (OSINT facts)
        cursor = await db.execute(
            "SELECT COUNT(*) as cnt FROM facts "
            "WHERE operation_id = ? AND trait = 'osint.subdomain'",
            (operation_id,),
        )
        row = await cursor.fetchone()
        subdomains_found = row["cnt"] if row else 0

        # 5. Services scanned (recon service facts)
        cursor = await db.execute(
            "SELECT COUNT(*) as cnt FROM facts "
            "WHERE operation_id = ? AND category = 'service'",
            (operation_id,),
        )
        row = await cursor.fetchone()
        services_scanned = row["cnt"] if row else 0

        # 6. Vulnerability findings from vuln.cve facts
        cursor = await db.execute(
            "SELECT f.value, f.source_target_id "
            "FROM facts f "
            "WHERE f.operation_id = ? AND f.trait = 'vuln.cve' "
            "ORDER BY f.collected_at",
            (operation_id,),
        )
        vuln_rows = await cursor.fetchall()
        findings = self._parse_vuln_facts(vuln_rows, targets_by_id)
        # Sort by CVSS descending
        findings.sort(key=lambda f: f.cvss_score, reverse=True)

        # Severity counts
        critical_count = sum(1 for f in findings if f.severity == "critical")
        high_count = sum(1 for f in findings if f.severity == "high")
        medium_count = sum(1 for f in findings if f.severity == "medium")
        low_count = sum(1 for f in findings if f.severity in ("low", "info"))

        # 7. Attack narrative from OODA iterations
        cursor = await db.execute(
            "SELECT oi.iteration_number, oi.phase, oi.observe_summary, oi.act_summary, "
            "       oi.completed_at, r.recommended_technique_id "
            "FROM ooda_iterations oi "
            "LEFT JOIN recommendations r ON oi.recommendation_id = r.id "
            "WHERE oi.operation_id = ? ORDER BY oi.iteration_number",
            (operation_id,),
        )
        ooda_rows = await cursor.fetchall()
        attack_steps = [
            AttackStep(
                iteration_number=r["iteration_number"],
                phase=r["phase"],
                observe_summary=r["observe_summary"],
                act_summary=r["act_summary"],
                technique_id=r["recommended_technique_id"],
                completed_at=r["completed_at"],
            )
            for r in ooda_rows
        ]

        # 8. Orient recommendations (last 5)
        cursor = await db.execute(
            "SELECT situation_assessment, recommended_technique_id, confidence, reasoning_text "
            "FROM recommendations WHERE operation_id = ? ORDER BY created_at DESC LIMIT 5",
            (operation_id,),
        )
        rec_rows = await cursor.fetchall()
        orient_recommendations = [dict(r) for r in rec_rows]

        # 9. MITRE ATT&CK coverage
        cursor = await db.execute(
            "SELECT t.tactic, te.technique_id "
            "FROM technique_executions te "
            "JOIN techniques t ON te.technique_id = t.mitre_id "
            "WHERE te.operation_id = ? AND te.status = 'success'",
            (operation_id,),
        )
        mitre_rows = await cursor.fetchall()
        mitre_coverage: dict[str, list[str]] = {}
        for r in mitre_rows:
            mitre_coverage.setdefault(r["tactic"], [])
            if r["technique_id"] not in mitre_coverage[r["tactic"]]:
                mitre_coverage[r["tactic"]].append(r["technique_id"])

        # 10. Executive summary (mock or LLM)
        # Simpler check via recon_scans
        cursor = await db.execute(
            "SELECT COUNT(*) as cnt FROM recon_scans "
            "WHERE operation_id = ? AND initial_access_method != 'none' "
            "AND initial_access_method IS NOT NULL AND credential_found IS NOT NULL",
            (operation_id,),
        )
        row = await cursor.fetchone()
        access_achieved = (row["cnt"] or 0) > 0
        access_status = "achieved" if access_achieved else "attempted"

        executive_summary = _MOCK_EXECUTIVE_SUMMARY.format(
            vuln_count=len(findings),
            target_count=targets_discovered,
            subdomain_count=subdomains_found,
            access_status=access_status,
        )

        return PentestReport(
            operation_id=operation_id,
            operation_name=op_name,
            codename=op_codename,
            generated_at=generated_at,
            client_name=client_name,
            contact_email=contact_email,
            in_scope=in_scope,
            out_of_scope=out_of_scope,
            engagement_status=engagement_status,
            executive_summary=executive_summary,
            targets_discovered=targets_discovered,
            subdomains_found=subdomains_found,
            services_scanned=services_scanned,
            vulnerabilities_found=len(findings),
            critical_count=critical_count,
            high_count=high_count,
            medium_count=medium_count,
            low_count=low_count,
            findings=findings,
            attack_steps=attack_steps,
            orient_recommendations=orient_recommendations,
            mitre_coverage=mitre_coverage,
        )

    def _parse_vuln_facts(
        self, vuln_rows, targets_by_id: dict
    ) -> list[Finding]:
        """Parse vuln.cve fact values into Finding objects.

        Fact value format: CVE-XXXX-YYYY:service:version_string:cvss=N.N:exploit=true|false
        """
        findings = []
        seen: set[str] = set()  # deduplicate by (cve_id, target_id)

        for row in vuln_rows:
            value = row["value"]
            target_id = row["source_target_id"] or ""
            target_info = targets_by_id.get(target_id, {})
            target_ip = target_info.get("ip_address", "unknown")

            try:
                parts = value.split(":")
                if len(parts) < 4:
                    continue

                cve_id = parts[0]   # CVE-XXXX-YYYY
                service = parts[1]  # ssh
                # version may have colons (e.g. OpenSSH_7.4 doesn't, but be safe)
                # Format is: CVE:service:version:cvss=N:exploit=bool
                # Find cvss= and exploit= parts
                version = ""
                cvss_score = 0.0
                exploit_available = False
                description = ""

                for part in parts[2:]:
                    if part.startswith("cvss="):
                        try:
                            cvss_score = float(part[5:])
                        except ValueError:
                            pass
                    elif part.startswith("exploit="):
                        exploit_available = part[8:].lower() == "true"
                    elif not version and not part.startswith("cvss=") and not part.startswith("exploit="):
                        version = part

                severity = _cvss_to_severity(cvss_score)

                key = f"{cve_id}:{target_id}"
                if key in seen:
                    continue
                seen.add(key)

                findings.append(Finding(
                    cve_id=cve_id,
                    service=service,
                    version=version,
                    cvss_score=cvss_score,
                    severity=severity,
                    description=description,
                    exploit_available=exploit_available,
                    target_id=target_id,
                    target_ip=target_ip,
                ))
            except Exception:
                logger.warning("Failed to parse vuln fact value: %s", value)
                continue

        return findings

    def to_markdown(self, report: PentestReport) -> str:
        """Render PentestReport as Markdown."""
        lines = [
            "# Penetration Test Report",
            f"## Operation: {report.operation_name} ({report.codename})",
            f"**Generated:** {report.generated_at}",
            "",
        ]

        if report.client_name:
            lines += [
                "## Engagement Details",
                f"- **Client:** {report.client_name}",
                f"- **Contact:** {report.contact_email or 'N/A'}",
                f"- **Status:** {report.engagement_status or 'N/A'}",
                f"- **In Scope:** {', '.join(report.in_scope) or 'Not specified'}",
                "",
            ]

        lines += [
            "## Executive Summary",
            report.executive_summary,
            "",
            "## Vulnerability Summary",
            "| Severity | Count |",
            "|----------|-------|",
            f"| Critical | {report.critical_count} |",
            f"| High | {report.high_count} |",
            f"| Medium | {report.medium_count} |",
            f"| Low/Info | {report.low_count} |",
            f"| **Total** | **{report.vulnerabilities_found}** |",
            "",
            "## Metrics",
            f"- Targets Discovered: {report.targets_discovered}",
            f"- Subdomains Found: {report.subdomains_found}",
            f"- Services Scanned: {report.services_scanned}",
            "",
        ]

        if report.findings:
            lines += ["## Findings", ""]
            for i, f in enumerate(report.findings, 1):
                lines += [
                    f"### Finding {i}: {f.cve_id} ({f.severity.upper()})",
                    f"- **Service:** {f.service} {f.version}",
                    f"- **CVSS Score:** {f.cvss_score}",
                    f"- **Exploit Available:** {'Yes' if f.exploit_available else 'No'}",
                    f"- **Target:** {f.target_ip}",
                    "",
                ]

        if report.attack_steps:
            lines += ["## Attack Narrative", ""]
            for step in report.attack_steps:
                lines += [
                    f"### Cycle #{step.iteration_number}",
                    f"- **Technique:** {step.technique_id or 'N/A'}",
                    f"- **Observe:** {step.observe_summary or 'N/A'}",
                    f"- **Act:** {step.act_summary or 'N/A'}",
                    "",
                ]

        if report.mitre_coverage:
            lines += ["## MITRE ATT&CK Coverage", ""]
            for tactic, techs in report.mitre_coverage.items():
                lines.append(f"- **{tactic}:** {', '.join(techs)}")
            lines.append("")

        return "\n".join(lines)


def _cvss_to_severity(score: float) -> str:
    if score >= 9.0:
        return "critical"
    if score >= 7.0:
        return "high"
    if score >= 4.0:
        return "medium"
    if score > 0.0:
        return "low"
    return "info"
