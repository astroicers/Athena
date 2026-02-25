"""Observe phase — extract and store facts from execution results."""

import uuid
from datetime import datetime, timezone

import aiosqlite

from app.ws_manager import WebSocketManager


class FactCollector:
    """Observe phase: standardize and persist intelligence from execution results."""

    def __init__(self, ws_manager: WebSocketManager):
        self._ws = ws_manager

    async def collect(self, db: aiosqlite.Connection, operation_id: str) -> list[dict]:
        """Extract facts from recent technique executions that have results."""
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT te.id, te.technique_id, te.target_id, te.result_summary "
            "FROM technique_executions te "
            "WHERE te.operation_id = ? AND te.status = 'success' "
            "AND te.result_summary IS NOT NULL "
            "ORDER BY te.completed_at DESC LIMIT 20",
            (operation_id,),
        )
        rows = await cursor.fetchall()

        new_facts: list[dict] = []
        for row in rows:
            technique_id = row["technique_id"]
            target_id = row["target_id"]
            summary = row["result_summary"] or ""

            # Derive fact category from technique
            category = self._infer_category(technique_id, summary)
            if not summary.strip():
                continue

            # Check if a fact with same trait+value already exists
            trait = f"execution.{technique_id}"
            cursor2 = await db.execute(
                "SELECT id FROM facts WHERE trait = ? AND operation_id = ?",
                (trait, operation_id),
            )
            if await cursor2.fetchone():
                continue

            fact_id = str(uuid.uuid4())
            now = datetime.now(timezone.utc).isoformat()
            await db.execute(
                "INSERT INTO facts (id, trait, value, category, source_technique_id, "
                "source_target_id, operation_id, score, collected_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (fact_id, trait, summary[:500], category, technique_id,
                 target_id, operation_id, 1, now),
            )
            fact = {
                "id": fact_id, "trait": trait, "value": summary[:500],
                "category": category, "source_technique_id": technique_id,
                "source_target_id": target_id, "operation_id": operation_id,
            }
            new_facts.append(fact)
            await self._ws.broadcast(operation_id, "fact.new", fact)

        await db.commit()
        return new_facts

    async def collect_from_result(
        self, db: aiosqlite.Connection, operation_id: str,
        technique_id: str, target_id: str, raw_facts: list[dict],
    ) -> list[dict]:
        """Store facts extracted from an ExecutionResult.facts list."""
        new_facts: list[dict] = []
        now = datetime.now(timezone.utc).isoformat()

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
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (fact_id, trait, str(value)[:500], category, technique_id,
                 target_id, operation_id, 1, now),
            )
            fact = {
                "id": fact_id, "trait": trait, "value": str(value)[:500],
                "category": category, "operation_id": operation_id,
            }
            new_facts.append(fact)
            await self._ws.broadcast(operation_id, "fact.new", fact)

        await db.commit()
        return new_facts

    async def summarize(self, db: aiosqlite.Connection, operation_id: str) -> str:
        """Produce an Observe-phase summary for Orient to consume."""
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT trait, value, category FROM facts "
            "WHERE operation_id = ? ORDER BY collected_at DESC LIMIT 30",
            (operation_id,),
        )
        rows = await cursor.fetchall()
        if not rows:
            return "No intelligence collected yet."

        lines = [f"- [{r['category']}] {r['trait']}: {r['value']}" for r in rows]
        return f"Collected {len(rows)} intelligence items:\n" + "\n".join(lines)

    @staticmethod
    def _infer_category(technique_id: str, summary: str) -> str:
        lower = (technique_id + summary).lower()
        if any(w in lower for w in ("cred", "hash", "password", "lsass", "t1003")):
            return "credential"
        if any(w in lower for w in ("network", "scan", "host.ip", "t1595")):
            return "network"
        if any(w in lower for w in ("service", "port")):
            return "service"
        return "host"

    @staticmethod
    def _category_from_trait(trait: str) -> str:
        if "credential" in trait or "hash" in trait:
            return "credential"
        if "network" in trait or "ip" in trait:
            return "network"
        if "service" in trait or "port" in trait:
            return "service"
        if "host" in trait:
            return "host"
        return "host"
