# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: [TODO: contact email]

"""OODA loop orchestrator — coordinates Observe → Orient → Decide → Act."""

import logging
import uuid
from datetime import datetime, timezone

import aiosqlite

from app.config import settings
from app.models.enums import OODAPhase
from app.services.c5isr_mapper import C5ISRMapper
from app.services.decision_engine import DecisionEngine
from app.services.engine_router import EngineRouter
from app.services.fact_collector import FactCollector
from app.services.mcp_client_manager import get_mcp_manager
from app.services.orient_engine import OrientEngine
from app.ws_manager import WebSocketManager

logger = logging.getLogger(__name__)


class OODAController:
    """
    OODA cycle orchestrator — manages Observe → Orient → Decide → Act transitions.
    Contains no business logic, only coordinates the 5 specialized services.
    """

    def __init__(
        self,
        fact_collector: FactCollector,
        orient_engine: OrientEngine,
        decision_engine: DecisionEngine,
        engine_router: EngineRouter,
        c5isr_mapper: C5ISRMapper,
        ws_manager: WebSocketManager,
    ):
        self._fact_collector = fact_collector
        self._orient = orient_engine
        self._decision = decision_engine
        self._router = engine_router
        self._c5isr = c5isr_mapper
        self._ws = ws_manager

    async def trigger_cycle(
        self, db: aiosqlite.Connection, operation_id: str
    ) -> dict:
        """
        Trigger one complete OODA iteration:
        1. Observe: fact_collector.collect()
        2. Orient:  orient_engine.analyze()
        3. Decide:  decision_engine.evaluate()
        4. Act:     engine_router.execute() (if auto-approved)
        5. Cross:   c5isr_mapper.update()
        """
        db.row_factory = aiosqlite.Row

        # Create new OODA iteration
        cursor = await db.execute(
            "SELECT COALESCE(MAX(iteration_number), 0) + 1 AS next_num "
            "FROM ooda_iterations WHERE operation_id = ?",
            (operation_id,),
        )
        row = await cursor.fetchone()
        next_num = row["next_num"]
        ooda_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        await db.execute(
            "INSERT INTO ooda_iterations "
            "(id, operation_id, iteration_number, phase, started_at) "
            "VALUES (?, ?, ?, 'observe', ?)",
            (ooda_id, operation_id, next_num, now),
        )
        await db.execute(
            "UPDATE operations SET current_ooda_phase = 'observe', "
            "ooda_iteration_count = ? WHERE id = ?",
            (next_num, operation_id),
        )
        await db.commit()

        # Set operation status to active on first cycle
        await self._activate_if_planning(db, operation_id)
        await self._broadcast_phase(operation_id, OODAPhase.OBSERVE)

        # ── 1. OBSERVE ──
        logger.info("OODA[%s] Observe phase", ooda_id[:8])
        new_facts = await self._fact_collector.collect(db, operation_id)
        observe_summary = await self._fact_collector.summarize(db, operation_id)
        await db.execute(
            "UPDATE ooda_iterations SET observe_summary = ? WHERE id = ?",
            (observe_summary[:1000], ooda_id),
        )
        await db.commit()
        await self._write_log(db, operation_id, "info",
            f"OODA #{next_num} Observe: collected {len(new_facts)} new facts")

        # ── 2. ORIENT ──
        await self._update_phase(db, operation_id, ooda_id, OODAPhase.ORIENT)
        logger.info("OODA[%s] Orient phase — calling PentestGPT", ooda_id[:8])
        recommendation = await self._orient.analyze(db, operation_id, observe_summary)
        orient_summary = recommendation.get("situation_assessment", "")
        await db.execute(
            "UPDATE ooda_iterations SET orient_summary = ? WHERE id = ?",
            (orient_summary[:1000], ooda_id),
        )
        await db.commit()
        await self._advance_mission_step(db, operation_id, step_index=0, status="completed")
        await self._advance_mission_step(db, operation_id, step_index=1, status="running")
        await self._write_log(db, operation_id, "info",
            f"OODA #{next_num} Orient: {orient_summary[:80]}")

        # ── 3. DECIDE ──
        await self._update_phase(db, operation_id, ooda_id, OODAPhase.DECIDE)
        logger.info("OODA[%s] Decide phase", ooda_id[:8])
        decision = await self._decision.evaluate(db, operation_id, recommendation)
        decide_summary = decision.get("reason", "")
        await db.execute(
            "UPDATE ooda_iterations SET decide_summary = ? WHERE id = ?",
            (decide_summary[:1000], ooda_id),
        )
        await db.commit()
        await self._advance_mission_step(db, operation_id, step_index=1, status="completed")
        await self._advance_mission_step(db, operation_id, step_index=2, status="running")
        await self._write_log(db, operation_id, "info",
            f"OODA #{next_num} Decide: {decide_summary[:80]}")

        # ── 4. ACT ──
        await self._update_phase(db, operation_id, ooda_id, OODAPhase.ACT)
        execution_result = None
        act_summary = ""

        if decision.get("auto_approved") and decision.get("technique_id") and decision.get("target_id"):
            logger.info("OODA[%s] Act phase — executing %s", ooda_id[:8], decision["technique_id"])
            execution_result = await self._router.execute(
                db,
                technique_id=decision["technique_id"],
                target_id=decision["target_id"],
                engine=decision.get("engine", "ssh"),
                operation_id=operation_id,
                ooda_iteration_id=ooda_id,
            )
            act_summary = (
                f"Executed {decision['technique_id']} via {decision.get('engine', 'ssh')}: "
                f"{execution_result.get('status', 'unknown')}"
            )
            # Link execution to iteration
            if execution_result.get("execution_id"):
                await db.execute(
                    "UPDATE ooda_iterations SET technique_execution_id = ? WHERE id = ?",
                    (execution_result["execution_id"], ooda_id),
                )
            if execution_result and execution_result.get("status") == "success":
                # Mark target as compromised
                if decision.get("target_id"):
                    await db.execute(
                        "UPDATE targets SET is_compromised = 1, privilege_level = 'User' "
                        "WHERE id = ? AND operation_id = ?",
                        (decision["target_id"], operation_id),
                    )
                # Activate one pending agent
                completed_at_now = datetime.now(timezone.utc).isoformat()
                await db.execute(
                    "UPDATE agents SET status = 'alive', last_beacon = ? "
                    "WHERE operation_id = ? AND status = 'pending' "
                    "ORDER BY ROWID LIMIT 1",
                    (completed_at_now, operation_id),
                )
                # Advance mission steps
                await self._advance_mission_step(db, operation_id, step_index=2, status="completed")
                await self._advance_mission_step(db, operation_id, step_index=3, status="running")
                # Update operation counters
                await db.execute(
                    "UPDATE operations SET techniques_executed = techniques_executed + 1, "
                    "active_agents = (SELECT COUNT(*) FROM agents WHERE operation_id = ? AND status = 'alive') "
                    "WHERE id = ?",
                    (operation_id, operation_id),
                )
                await db.commit()
                await self._write_log(db, operation_id, "success",
                    f"OODA #{next_num} Act: {decision['technique_id']} executed successfully on {decision.get('target_id', 'unknown')}")
            elif execution_result:
                await self._write_log(db, operation_id, "warning",
                    f"OODA #{next_num} Act: {decision['technique_id']} returned {execution_result.get('status', 'unknown')}")
        else:
            act_summary = f"Awaiting commander approval: {decision.get('reason', 'manual required')}"
            logger.info("OODA[%s] Act phase — needs approval: %s", ooda_id[:8], act_summary)
            await self._write_log(db, operation_id, "warning",
                f"OODA #{next_num} Act: awaiting commander approval — {decision.get('reason', 'manual required')}")

        completed_at = datetime.now(timezone.utc).isoformat()
        await db.execute(
            "UPDATE ooda_iterations SET act_summary = ?, completed_at = ? WHERE id = ?",
            (act_summary[:1000], completed_at, ooda_id),
        )
        await db.commit()

        # ── 5. C5ISR UPDATE ──
        logger.info("OODA[%s] C5ISR update", ooda_id[:8])
        await self._c5isr.update(db, operation_id)
        await self._write_log(db, operation_id, "info",
            f"OODA #{next_num} complete — C5ISR domains updated")

        # Update operation success rate
        cursor = await db.execute(
            "SELECT COUNT(*) as total, "
            "SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as success "
            "FROM technique_executions WHERE operation_id = ?",
            (operation_id,),
        )
        stats = await cursor.fetchone()
        if stats["total"] > 0:
            rate = round(stats["success"] / stats["total"] * 100, 1)
            await db.execute(
                "UPDATE operations SET success_rate = ? WHERE id = ?",
                (rate, operation_id),
            )
            await db.commit()

        # Return iteration summary
        cursor = await db.execute(
            "SELECT * FROM ooda_iterations WHERE id = ?", (ooda_id,)
        )
        final = await cursor.fetchone()
        return dict(final) if final else {"id": ooda_id}

    async def advance_phase(
        self, db: aiosqlite.Connection, operation_id: str, phase: OODAPhase
    ):
        """Manual phase advancement (commander override)."""
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT id FROM ooda_iterations WHERE operation_id = ? "
            "ORDER BY iteration_number DESC LIMIT 1",
            (operation_id,),
        )
        row = await cursor.fetchone()
        if row:
            await db.execute(
                "UPDATE ooda_iterations SET phase = ? WHERE id = ?",
                (phase.value, row["id"]),
            )
        await db.execute(
            "UPDATE operations SET current_ooda_phase = ? WHERE id = ?",
            (phase.value, operation_id),
        )
        await db.commit()
        await self._broadcast_phase(operation_id, phase)

    async def get_current(self, db: aiosqlite.Connection, operation_id: str) -> dict | None:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM ooda_iterations WHERE operation_id = ? "
            "ORDER BY iteration_number DESC LIMIT 1",
            (operation_id,),
        )
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def _activate_if_planning(
        self, db: aiosqlite.Connection, operation_id: str
    ):
        """Set operation status to 'active' if currently 'planning'."""
        cursor = await db.execute(
            "SELECT status FROM operations WHERE id = ?", (operation_id,),
        )
        op_row = await cursor.fetchone()
        if op_row and op_row["status"] == "planning":
            await db.execute(
                "UPDATE operations SET status = 'active' WHERE id = ?",
                (operation_id,),
            )
            await db.commit()

    async def _update_phase(
        self, db: aiosqlite.Connection, operation_id: str,
        ooda_id: str, phase: OODAPhase,
    ):
        await db.execute(
            "UPDATE ooda_iterations SET phase = ? WHERE id = ?",
            (phase.value, ooda_id),
        )
        await db.execute(
            "UPDATE operations SET current_ooda_phase = ? WHERE id = ?",
            (phase.value, operation_id),
        )
        await db.commit()
        await self._broadcast_phase(operation_id, phase)

    async def _broadcast_phase(self, operation_id: str, phase: OODAPhase):
        try:
            await self._ws.broadcast(
                operation_id, "ooda.phase", {"phase": phase.value}
            )
        except Exception:
            pass  # fire-and-forget per SPEC-007

    async def _write_log(
        self, db: aiosqlite.Connection, operation_id: str,
        severity: str, message: str,
    ) -> None:
        """Write a log entry and broadcast via WebSocket."""
        log_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        await db.execute(
            "INSERT INTO log_entries "
            "(id, operation_id, timestamp, severity, source, message) "
            "VALUES (?, ?, ?, ?, 'ooda_controller', ?)",
            (log_id, operation_id, now, severity, message),
        )
        await db.commit()
        try:
            await self._ws.broadcast(operation_id, "log.new", {
                "id": log_id, "timestamp": now, "severity": severity,
                "source": "ooda_controller", "message": message,
            })
        except Exception:
            pass  # fire-and-forget

    async def _advance_mission_step(
        self, db: aiosqlite.Connection, operation_id: str,
        step_index: int, status: str,
    ) -> None:
        """Update a mission step by its order index (0-based)."""
        now = datetime.now(timezone.utc).isoformat()
        cursor = await db.execute(
            "SELECT id FROM mission_steps "
            "WHERE operation_id = ? ORDER BY step_number "
            "LIMIT 1 OFFSET ?",
            (operation_id, step_index),
        )
        row = await cursor.fetchone()
        if not row:
            return
        step_id = row["id"] if isinstance(row, dict) or hasattr(row, "__getitem__") else row[0]
        if status == "running":
            await db.execute(
                "UPDATE mission_steps SET status = ?, started_at = ? WHERE id = ?",
                (status, now, step_id),
            )
        elif status == "completed":
            await db.execute(
                "UPDATE mission_steps SET status = ?, completed_at = ? WHERE id = ?",
                (status, now, step_id),
            )
        else:
            await db.execute(
                "UPDATE mission_steps SET status = ? WHERE id = ?",
                (status, step_id),
            )
        await db.commit()


def build_ooda_controller() -> "OODAController":
    """Factory for creating OODAController without request context (used by scheduler)."""
    from app.clients.c2_client import C2EngineClient
    from app.clients.mock_c2_client import MockC2Client
    from app.ws_manager import ws_manager

    fc = FactCollector(ws_manager)
    orient = OrientEngine(ws_manager)
    decision = DecisionEngine()
    c5isr = C5ISRMapper(ws_manager)

    # Mirror _get_controller() logic: respect MOCK_C2_ENGINE setting
    c2_engine: MockC2Client | C2EngineClient = MockC2Client()
    if not settings.MOCK_C2_ENGINE:
        try:
            c2_engine = C2EngineClient(settings.C2_ENGINE_URL, settings.C2_ENGINE_API_KEY)
        except Exception:
            logger.warning("build_ooda_controller: failed to connect to C2 engine, falling back to mock")

    mcp_engine_client = None
    if settings.MCP_ENABLED:
        from app.clients.mcp_engine_client import MCPEngineClient

        mcp_mgr = get_mcp_manager()
        if mcp_mgr is not None:
            mcp_engine_client = MCPEngineClient(mcp_mgr)

    router_svc = EngineRouter(c2_engine, fc, ws_manager, mcp_engine=mcp_engine_client)

    return OODAController(fc, orient, decision, router_svc, c5isr, ws_manager)
