# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: [TODO: contact email]

"""Observe phase — extract and store facts from execution results."""

import re as _re
import uuid
from datetime import datetime, timezone

import asyncpg

from app.models.enums import FactCategory
from app.services.vulnerability_manager import VulnerabilityManager
from app.ws_manager import WebSocketManager

_vuln_mgr = VulnerabilityManager()


class FactCollector:
    """Observe phase: standardize and persist intelligence from execution results."""

    def __init__(self, ws_manager: WebSocketManager):
        self._ws = ws_manager

    async def collect(self, db: asyncpg.Connection, operation_id: str) -> list[dict]:
        """Extract facts from recent technique executions that have results."""

        # Batch-load existing (trait, value) pairs for in-memory dedup
        dup_rows = await db.fetch(
            "SELECT trait, value FROM facts WHERE operation_id = $1",
            operation_id,
        )
        existing = {(r["trait"], r["value"]) for r in dup_rows}

        rows = await db.fetch(
            "SELECT te.id, te.technique_id, te.target_id, te.result_summary "
            "FROM technique_executions te "
            "WHERE te.operation_id = $1 AND te.status = 'success' "
            "AND te.result_summary IS NOT NULL "
            "ORDER BY te.completed_at DESC LIMIT 20",
            operation_id,
        )

        new_facts: list[dict] = []
        for row in rows:
            technique_id = row["technique_id"]
            target_id = row["target_id"]
            summary = row["result_summary"] or ""

            category = self._infer_category(technique_id, summary)
            if not summary.strip():
                continue

            trait = f"execution.{technique_id}"
            value = summary[:500]
            if (trait, value) in existing:
                continue
            existing.add((trait, value))

            fact_id = str(uuid.uuid4())
            now = datetime.now(timezone.utc)
            await db.execute(
                "INSERT INTO facts (id, trait, value, category, source_technique_id, "
                "source_target_id, operation_id, score, collected_at) "
                "VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9) "
                "ON CONFLICT DO NOTHING",
                fact_id, trait, value, category.value, technique_id,
                target_id, operation_id, 1, now,
            )
            fact = {
                "id": fact_id, "trait": trait, "value": value,
                "category": category.value, "source_technique_id": technique_id,
                "source_target_id": target_id, "operation_id": operation_id,
            }
            new_facts.append(fact)
            await self._ws.broadcast(operation_id, "fact.new", fact)

        # --- SPEC-044: Auto-populate vulnerabilities from vuln.cve facts ---
        for fact in new_facts:
            if fact["trait"].startswith("vuln.cve") or fact["trait"].startswith("vulnerability.cve"):
                cve_match = _re.match(r"(CVE-\d{4}-\d+)", fact["value"])
                if cve_match and fact.get("source_target_id"):
                    await _vuln_mgr.upsert_from_fact(
                        db, operation_id,
                        fact_id=fact["id"],
                        cve_id=cve_match.group(1),
                        target_id=fact["source_target_id"],
                    )

        return new_facts

    async def collect_from_result(
        self, db: asyncpg.Connection, operation_id: str,
        technique_id: str, target_id: str, raw_facts: list[dict],
    ) -> list[dict]:
        """Store facts extracted from an ExecutionResult.facts list."""
        new_facts: list[dict] = []
        now = datetime.now(timezone.utc)

        for rf in raw_facts:
            trait = rf.get("trait", "unknown")
            value = rf.get("value", "")
            if not value:
                continue

            category = self._category_from_trait(trait)
            fact_id = str(uuid.uuid4())
            await db.execute(
                "INSERT INTO facts (id, trait, value, category, source_technique_id, "
                "source_target_id, operation_id, score, collected_at) "
                "VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9) "
                "ON CONFLICT DO NOTHING",
                fact_id, trait, str(value)[:500], category.value,
                technique_id, target_id, operation_id, 1, now,
            )
            new_facts.append({
                "id": fact_id, "trait": trait, "value": str(value)[:500],
                "category": category.value, "operation_id": operation_id,
            })

        for fact in new_facts:
            await self._ws.broadcast(operation_id, "fact.new", fact)

        # --- SPEC-044: Auto-populate vulnerabilities from vuln.cve facts ---
        for fact in new_facts:
            if fact["trait"].startswith("vuln.cve") or fact["trait"].startswith("vulnerability.cve"):
                cve_match = _re.match(r"(CVE-\d{4}-\d+)", fact["value"])
                if cve_match:
                    await _vuln_mgr.upsert_from_fact(
                        db, operation_id,
                        fact_id=fact["id"],
                        cve_id=cve_match.group(1),
                        target_id=target_id,
                    )

        return new_facts

    async def summarize(self, db: asyncpg.Connection, operation_id: str) -> str:
        """Produce an Observe-phase summary for Orient to consume."""
        rows = await db.fetch(
            "SELECT trait, value, category FROM facts "
            "WHERE operation_id = $1 ORDER BY collected_at DESC LIMIT 30",
            operation_id,
        )
        if not rows:
            return "No intelligence collected yet."

        lines = [f"- [{r['category']}] {r['trait']}: {r['value']}" for r in rows]
        return f"Collected {len(rows)} intelligence items:\n" + "\n".join(lines)

    @staticmethod
    def _infer_category(technique_id: str, summary: str) -> FactCategory:
        lower = (technique_id + summary).lower()
        if any(w in lower for w in ("cred", "hash", "password", "lsass", "t1003")):
            return FactCategory.CREDENTIAL
        if any(w in lower for w in ("network", "scan", "host.ip", "t1595")):
            return FactCategory.NETWORK
        if any(w in lower for w in ("service", "port")):
            return FactCategory.SERVICE
        return FactCategory.HOST

    @staticmethod
    def _category_from_trait(trait: str) -> FactCategory:
        if "credential" in trait or "hash" in trait:
            return FactCategory.CREDENTIAL
        if "network" in trait or "ip" in trait:
            return FactCategory.NETWORK
        if "service" in trait or "port" in trait:
            return FactCategory.SERVICE
        if "host" in trait:
            return FactCategory.HOST
        return FactCategory.HOST
