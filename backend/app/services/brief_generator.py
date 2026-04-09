# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: azz093093.830330@gmail.com

"""BriefGenerator — auto-generates OPERATION_BRIEF.md after each OODA cycle."""

import logging
from datetime import datetime, timezone

import asyncpg

logger = logging.getLogger(__name__)

# MITRE ATT&CK tactics in kill-chain order
_KILL_CHAIN_TACTICS = [
    ("TA0043", "Reconnaissance"),
    ("TA0042", "Resource Development"),
    ("TA0001", "Initial Access"),
    ("TA0002", "Execution"),
    ("TA0003", "Persistence"),
    ("TA0004", "Privilege Escalation"),
    ("TA0005", "Defense Evasion"),
    ("TA0006", "Credential Access"),
    ("TA0007", "Discovery"),
    ("TA0008", "Lateral Movement"),
    ("TA0009", "Collection"),
    ("TA0011", "Command and Control"),
    ("TA0010", "Exfiltration"),
    ("TA0040", "Impact"),
]


def _trunc(text: str | None, max_len: int = 60) -> str:
    """Truncate text to max_len, adding ellipsis if needed."""
    if not text:
        return "-"
    text = text.replace("\n", " ").strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def _escape_md(text: str | None) -> str:
    """Escape pipe characters for markdown table cells."""
    if not text:
        return ""
    return text.replace("|", "\\|").replace("\n", " ")


class BriefGenerator:
    """Generate a structured markdown Operation Brief from all operation data."""

    async def generate(self, db: asyncpg.Connection, operation_id: str) -> str:
        """Generate OPERATION_BRIEF.md from all operation data."""
        now = datetime.now(timezone.utc)

        # 1. Operation metadata
        op = await db.fetchrow(
            "SELECT * FROM operations WHERE id = $1", operation_id,
        )

        # 2. Targets
        targets = await db.fetch(
            "SELECT * FROM targets WHERE operation_id = $1", operation_id,
        )

        # 3. Facts
        facts = await db.fetch(
            "SELECT * FROM facts WHERE operation_id = $1 ORDER BY collected_at DESC",
            operation_id,
        )

        # 4. OODA iterations
        ooda_iters = await db.fetch(
            "SELECT * FROM ooda_iterations WHERE operation_id = $1 "
            "ORDER BY iteration_number",
            operation_id,
        )

        # 5. Technique executions
        tech_execs = await db.fetch(
            "SELECT * FROM technique_executions WHERE operation_id = $1 "
            "ORDER BY started_at",
            operation_id,
        )

        # 6. C5ISR statuses
        c5isr_rows = await db.fetch(
            "SELECT * FROM c5isr_statuses WHERE operation_id = $1",
            operation_id,
        )

        # 7. Latest recommendation
        rec_row = await db.fetchrow(
            "SELECT * FROM recommendations WHERE operation_id = $1 "
            "ORDER BY created_at DESC LIMIT 1",
            operation_id,
        )

        # --- Derived values ---
        codename = op["codename"] if op else "UNKNOWN"
        mission_profile = (op["mission_profile"] if op else None) or "SP"
        status = (op["status"] if op else None) or "unknown"
        threat_level = (op["threat_level"] if op else None) or "unknown"
        latest_iter = ooda_iters[-1]["iteration_number"] if ooda_iters else 0

        targets_total = len(targets)
        targets_compromised = sum(
            1 for t in targets if t.get("is_compromised")
        )
        facts_count = len(facts)

        # Build kill-chain map: tactic -> list of technique_ids
        tactic_techniques: dict[str, list[str]] = {}
        for te in tech_execs:
            tid = te.get("technique_id", "")
            tactic = te.get("tactic") or ""
            if tactic:
                tactic_techniques.setdefault(tactic, []).append(tid)

        # Also look up tactics via the techniques table for executions without tactic
        exec_technique_ids = list({
            te["technique_id"] for te in tech_execs
            if te.get("technique_id") and not te.get("tactic")
        })
        if exec_technique_ids:
            try:
                tactic_rows = await db.fetch(
                    "SELECT mitre_id, tactic FROM techniques WHERE mitre_id = ANY($1::text[])",
                    exec_technique_ids,
                )
                tech_to_tactic = {r["mitre_id"]: r["tactic"] for r in tactic_rows if r["tactic"]}
                for te in tech_execs:
                    tid = te.get("technique_id", "")
                    if tid in tech_to_tactic and not te.get("tactic"):
                        tactic = tech_to_tactic[tid]
                        tactic_techniques.setdefault(tactic, [])
                        if tid not in tactic_techniques[tactic]:
                            tactic_techniques[tactic].append(tid)
            except Exception:
                pass  # best-effort enrichment

        # Categorize facts
        cred_facts = [f for f in facts if (f.get("category") or "") == "credential"]
        svc_facts = [f for f in facts if (f.get("category") or "") == "service"]
        vuln_facts = [f for f in facts if (f.get("category") or "") == "vulnerability"]

        # --- Build markdown ---
        lines: list[str] = []

        # Header
        lines.append(f"# Operation Brief: {codename}")
        lines.append(
            f"> Auto-generated after OODA #{latest_iter} | {now.strftime('%Y-%m-%d %H:%M:%S UTC')}"
        )
        lines.append(
            f"> Mission Profile: {mission_profile} | Status: {status} | Threat Level: {threat_level}"
        )
        lines.append("")

        # Executive Summary
        lines.append("## Executive Summary")
        lines.append(
            f"{len(ooda_iters)} OODA cycles completed. "
            f"{targets_compromised}/{targets_total} targets compromised. "
            f"{facts_count} facts collected."
        )
        lines.append("")

        # Kill Chain Progress
        lines.append("## Kill Chain Progress")
        lines.append("| Stage | Status | Techniques |")
        lines.append("|-------|--------|------------|")
        for tactic_id, tactic_name in _KILL_CHAIN_TACTICS:
            techs = tactic_techniques.get(tactic_id, [])
            if techs:
                unique_techs = list(dict.fromkeys(techs))  # deduplicate, preserve order
                stage_status = "Active"
                tech_list = _trunc(", ".join(unique_techs), 40)
            else:
                stage_status = "-"
                tech_list = "-"
            lines.append(
                f"| {tactic_name} ({tactic_id}) | {stage_status} | {tech_list} |"
            )
        lines.append("")

        # Targets
        lines.append("## Targets")
        if targets:
            lines.append("| Host | IP | Status | Privilege | Facts |")
            lines.append("|------|-----|--------|-----------|-------|")
            for t in targets:
                hostname = _escape_md(t.get("hostname")) or "-"
                ip = _escape_md(t.get("ip_address")) or "-"
                t_status = "Compromised" if t.get("is_compromised") else (
                    _escape_md(t.get("access_status")) or "pending"
                )
                privilege = _escape_md(t.get("privilege_level")) or "-"
                t_fact_count = sum(
                    1 for f in facts if f.get("source_target_id") == t["id"]
                )
                lines.append(
                    f"| {hostname} | {ip} | {t_status} | {privilege} | {t_fact_count} |"
                )
        else:
            lines.append("_No targets defined._")
        lines.append("")

        # Key Facts
        lines.append(f"## Key Facts ({facts_count} total)")
        lines.append("")

        lines.append("### Credentials")
        if cred_facts:
            for f in cred_facts[:10]:
                lines.append(f"- {_trunc(_escape_md(f.get('value')), 80)}")
        else:
            lines.append("_None collected._")
        lines.append("")

        lines.append("### Services")
        if svc_facts:
            for f in svc_facts[:10]:
                lines.append(f"- {_trunc(_escape_md(f.get('value')), 80)}")
        else:
            lines.append("_None collected._")
        lines.append("")

        lines.append("### Vulnerabilities")
        if vuln_facts:
            for f in vuln_facts[:10]:
                lines.append(f"- {_trunc(_escape_md(f.get('value')), 80)}")
        else:
            lines.append("_None collected._")
        lines.append("")

        # OODA Decision Log
        lines.append("## OODA Decision Log")
        if ooda_iters:
            lines.append("| # | Observe | Orient | Decide | Act |")
            lines.append("|---|---------|--------|--------|-----|")
            for it in ooda_iters:
                num = it["iteration_number"]
                obs = _trunc(it.get("observe_summary"))
                ori = _trunc(it.get("orient_summary"))
                dec = _trunc(it.get("decide_summary"))
                act = _trunc(it.get("act_summary"))
                lines.append(f"| {num} | {obs} | {ori} | {dec} | {act} |")
        else:
            lines.append("_No OODA iterations yet._")
        lines.append("")

        # C5ISR Health
        lines.append("## C5ISR Health")
        if c5isr_rows:
            lines.append("| Domain | Health | Status |")
            lines.append("|--------|--------|--------|")
            for c in c5isr_rows:
                domain = _escape_md(c.get("domain")) or "-"
                health = c.get("health_pct")
                health_str = f"{health:.0f}%" if health is not None else "-"
                c_status = _escape_md(c.get("status")) or "-"
                lines.append(f"| {domain} | {health_str} | {c_status} |")
        else:
            lines.append("_No C5ISR data._")
        lines.append("")

        # Next Recommended Action
        lines.append("## Next Recommended Action")
        if rec_row:
            situation = _trunc(rec_row.get("situation_assessment"), 200)
            rec_tech = rec_row.get("recommended_technique_id") or "N/A"
            lines.append(f"**Situation:** {situation}")
            lines.append("")
            lines.append(f"**Recommended Technique:** {rec_tech}")
        else:
            lines.append("_No recommendation available._")
        lines.append("")

        return "\n".join(lines)
