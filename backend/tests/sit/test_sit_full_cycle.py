"""SIT Full Cycle Integration: Complete OODA Loop

Verifies the end-to-end chain: Observe -> Orient -> Decide -> Act -> C5ISR
using real PostgreSQL for all service interactions.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.clients import BaseEngineClient, ExecutionResult
from app.services.c5isr_mapper import C5ISRMapper
from app.services.decision_engine import DecisionEngine
from app.services.engine_router import EngineRouter
from app.services.fact_collector import FactCollector
from app.services.orient_engine import OrientEngine
from app.services.agent_swarm import SwarmExecutor
from app.services.ooda_controller import OODAController

pytestmark = pytest.mark.asyncio


def _build_controller(ws, engine_client):
    """Build a full OODA controller stack.

    Note: swarm_executor is set to None to avoid db_manager.pool dependency.
    The controller falls through to the single-execution path instead.
    """
    fc = FactCollector(ws)
    orient = OrientEngine(ws)
    decision = DecisionEngine()
    router = EngineRouter(
        c2_engine=engine_client,
        fact_collector=fc,
        ws_manager=ws,
        mcp_engine=engine_client,
    )
    c5isr = C5ISRMapper(ws)
    return OODAController(
        fact_collector=fc,
        orient_engine=orient,
        decision_engine=decision,
        engine_router=router,
        c5isr_mapper=c5isr,
        ws_manager=ws,
        swarm_executor=None,  # No swarm — avoids pool dependency
    )


async def _seed_execution_for_observe(db):
    """Add a completed execution so Observe has data to collect."""
    await db.execute(
        "INSERT INTO technique_executions "
        "(id, technique_id, target_id, operation_id, engine, status, "
        "result_summary, started_at, completed_at) "
        "VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)",
        str(uuid.uuid4()), "T1595.001", "test-target-1", "test-op-1",
        "mcp_recon", "success",
        "Nmap scan: 22/tcp SSH OpenSSH 8.9, 445/tcp SMB",
        datetime.now(timezone.utc), datetime.now(timezone.utc),
    )


async def _seed_credential_for_act(db):
    """Add SSH credential so Act phase can execute."""
    await db.execute(
        "INSERT INTO facts (id, trait, value, category, "
        "source_technique_id, source_target_id, operation_id, score, collected_at) "
        "VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9) ON CONFLICT DO NOTHING",
        str(uuid.uuid4()), "credential.ssh", "root:toor", "credential",
        "T1003.001", "test-target-1", "test-op-1", 1,
        datetime.now(timezone.utc),
    )


# ── F.1 Happy path: complete cycle ──────────────────────────────────────
async def test_full_cycle_happy_path(seeded_db, sit_ws_manager, mock_engine_client):
    """Complete OODA cycle: Observe->Orient->Decide->Act->C5ISR all succeed."""
    db = seeded_db
    await _seed_execution_for_observe(db)
    await _seed_credential_for_act(db)

    controller = _build_controller(sit_ws_manager, mock_engine_client)
    result = await controller.trigger_cycle(db, "test-op-1")

    # Should not be aborted or skipped
    assert result.get("status") not in ("aborted", "skipped"), (
        f"Cycle should complete, got status={result.get('status')}, reason={result.get('reason')}"
    )

    # Verify OODA iteration was created
    iter_row = await db.fetchrow(
        "SELECT iteration_number, observe_summary, orient_summary "
        "FROM ooda_iterations WHERE operation_id = $1 "
        "ORDER BY iteration_number DESC LIMIT 1",
        "test-op-1",
    )
    assert iter_row is not None
    assert iter_row["iteration_number"] >= 1
    assert iter_row["observe_summary"] is not None


# ── F.2 WS event sequence verified ──────────────────────────────────────
async def test_full_cycle_ws_event_sequence(seeded_db, sit_ws_manager, mock_engine_client):
    """WS events follow the expected OODA phase sequence."""
    db = seeded_db
    await _seed_execution_for_observe(db)
    await _seed_credential_for_act(db)

    controller = _build_controller(sit_ws_manager, mock_engine_client)
    await controller.trigger_cycle(db, "test-op-1")

    # Extract phase events
    phase_events = [
        c[2].get("phase") for c in sit_ws_manager._calls
        if c[1] == "ooda.phase"
    ]

    # Should see at least observe, orient, decide, act in order
    expected_phases = ["observe", "orient", "decide", "act"]
    for phase in expected_phases:
        assert phase in phase_events, (
            f"Phase '{phase}' missing from WS events: {phase_events}"
        )

    # Verify order: observe before orient before decide before act
    idx = {p: phase_events.index(p) for p in expected_phases}
    assert idx["observe"] < idx["orient"] < idx["decide"] < idx["act"]

    # Should have ooda.completed event
    completed = [c for c in sit_ws_manager._calls if c[1] == "ooda.completed"]
    assert len(completed) >= 1


# ── F.3 Consecutive cycles increment iteration_number ───────────────────
async def test_consecutive_cycles_increment(seeded_db, sit_ws_manager, mock_engine_client):
    """Two consecutive trigger_cycle() calls produce iteration_number 1 and 2."""
    db = seeded_db
    await _seed_execution_for_observe(db)
    await _seed_credential_for_act(db)

    controller = _build_controller(sit_ws_manager, mock_engine_client)

    r1 = await controller.trigger_cycle(db, "test-op-1")
    assert r1.get("status") not in ("aborted", "skipped")

    r2 = await controller.trigger_cycle(db, "test-op-1")
    assert r2.get("status") not in ("aborted", "skipped")

    # Verify iteration numbers
    rows = await db.fetch(
        "SELECT iteration_number FROM ooda_iterations "
        "WHERE operation_id = $1 ORDER BY iteration_number",
        "test-op-1",
    )
    numbers = [r["iteration_number"] for r in rows]
    assert 1 in numbers
    assert 2 in numbers
    assert len(numbers) >= 2


# ── F.4 Concurrent trigger -> skipped ───────────────────────────────────
async def test_concurrent_trigger_skipped(seeded_db, sit_ws_manager, mock_engine_client):
    """Simultaneous trigger_cycle() for same operation -> second returns skipped."""
    db = seeded_db
    await _seed_execution_for_observe(db)
    await _seed_credential_for_act(db)

    controller = _build_controller(sit_ws_manager, mock_engine_client)

    # Manually acquire the lock to simulate a running cycle
    from app.services.ooda_controller import _get_operation_lock
    lock = _get_operation_lock("test-op-1")

    async with lock:
        # While lock is held, trigger_cycle should return skipped
        result = await controller.trigger_cycle(db, "test-op-1")
        assert result["status"] == "skipped"
        assert result["reason"] == "concurrent_cycle_in_progress"


# ── F.5 Orient LLM failure -> aborted ───────────────────────────────────
async def test_orient_failure_aborts_cycle(seeded_db, sit_ws_manager, mock_engine_client):
    """When Orient LLM fails, the cycle aborts at orient phase."""
    db = seeded_db
    await _seed_execution_for_observe(db)

    controller = _build_controller(sit_ws_manager, mock_engine_client)

    # Patch orient.analyze to return None (simulating LLM failure)
    with patch.object(
        controller._orient, "analyze",
        new_callable=AsyncMock, return_value=None,
    ):
        result = await controller.trigger_cycle(db, "test-op-1")

    assert result["status"] == "aborted"
    assert "orient" in result.get("reason", "").lower()


# ── F.6 log_entries written for each phase ──────────────────────────────
async def test_log_entries_per_phase(seeded_db, sit_ws_manager, mock_engine_client):
    """Each OODA phase writes at least one log_entry."""
    db = seeded_db
    await _seed_execution_for_observe(db)
    await _seed_credential_for_act(db)

    controller = _build_controller(sit_ws_manager, mock_engine_client)
    await controller.trigger_cycle(db, "test-op-1")

    log_count = await db.fetchval(
        "SELECT COUNT(*) FROM log_entries WHERE operation_id = $1",
        "test-op-1",
    )
    # Should have at least 4 log entries (Observe, Orient, Decide, Act/C5ISR)
    assert log_count >= 4, f"Expected >= 4 log entries, got {log_count}"


# ── F.7 operation.current_ooda_phase updated ────────────────────────────
async def test_operation_phase_updated(seeded_db, sit_ws_manager, mock_engine_client):
    """After cycle completes, operation.current_ooda_phase is updated."""
    db = seeded_db
    await _seed_execution_for_observe(db)
    await _seed_credential_for_act(db)

    controller = _build_controller(sit_ws_manager, mock_engine_client)
    await controller.trigger_cycle(db, "test-op-1")

    op = await db.fetchrow(
        "SELECT current_ooda_phase, ooda_iteration_count FROM operations "
        "WHERE id = $1",
        "test-op-1",
    )
    assert op is not None
    # After a complete cycle, the phase should be 'act' (last phase written)
    # and iteration_count should be >= 1
    assert op["ooda_iteration_count"] >= 1
    # Phase could be 'act' or 'observe' depending on implementation
    assert op["current_ooda_phase"] in ("act", "observe", "completed")
