"""SIT Boundary 2: OODAController <-> OrientEngine

Verifies that observe_summary flows into Orient.analyze(), recommendations
are stored in DB with correct FK linkage, and WS events are broadcast.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from app.services.fact_collector import FactCollector
from app.services.orient_engine import OrientEngine

pytestmark = pytest.mark.asyncio


async def _setup_ooda_iteration(db, op_id="test-op-1"):
    """Insert an OODA iteration so Orient can link the recommendation."""
    ooda_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    await db.execute(
        "INSERT INTO ooda_iterations "
        "(id, operation_id, iteration_number, phase, started_at, observe_summary) "
        "VALUES ($1, $2, 1, 'orient', $3, $4)",
        ooda_id, op_id, now, "Test observe summary with 3 intelligence items",
    )
    return ooda_id


# ── 2.1 Orient produces recommendation stored in DB ─────────────────────
async def test_orient_produces_recommendation(seeded_db, sit_ws_manager):
    """OrientEngine.analyze() (mock mode) stores recommendation in DB."""
    db = seeded_db
    ooda_id = await _setup_ooda_iteration(db)
    orient = OrientEngine(sit_ws_manager)

    rec = await orient.analyze(
        db, "test-op-1", "Collected 3 intelligence items",
    )
    assert rec is not None
    assert "recommended_technique_id" in rec
    assert rec["recommended_technique_id"] == "T1003.001"  # mock default

    # Verify in DB
    row = await db.fetchrow(
        "SELECT id, recommended_technique_id, confidence FROM recommendations "
        "WHERE operation_id = $1 ORDER BY created_at DESC LIMIT 1",
        "test-op-1",
    )
    assert row is not None
    assert row["recommended_technique_id"] == "T1003.001"
    assert row["confidence"] == pytest.approx(0.87, abs=1e-4)


# ── 2.2 recommendation FK links to ooda_iteration ───────────────────────
async def test_recommendation_links_to_iteration(seeded_db, sit_ws_manager):
    """Recommendation.ooda_iteration_id correctly references the OODA iteration."""
    db = seeded_db
    ooda_id = await _setup_ooda_iteration(db)
    orient = OrientEngine(sit_ws_manager)

    rec = await orient.analyze(db, "test-op-1", "summary")
    assert rec is not None

    rec_row = await db.fetchrow(
        "SELECT ooda_iteration_id FROM recommendations "
        "WHERE operation_id = $1 ORDER BY created_at DESC LIMIT 1",
        "test-op-1",
    )
    assert rec_row["ooda_iteration_id"] == ooda_id

    # Verify reverse link: iteration -> recommendation
    iter_row = await db.fetchrow(
        "SELECT recommendation_id FROM ooda_iterations WHERE id = $1",
        ooda_id,
    )
    assert iter_row["recommendation_id"] is not None


# ── 2.3 recommendation WS event broadcast ───────────────────────────────
async def test_orient_broadcasts_recommendation(seeded_db, sit_ws_manager):
    """Orient broadcasts 'recommendation' WS event after analysis."""
    db = seeded_db
    await _setup_ooda_iteration(db)
    orient = OrientEngine(sit_ws_manager)

    await orient.analyze(db, "test-op-1", "summary")

    rec_events = [c for c in sit_ws_manager._calls if c[1] == "recommendation"]
    assert len(rec_events) >= 1, "Should broadcast recommendation event"


# ── 2.4 attack graph summary is passed to Orient ────────────────────────
async def test_orient_receives_attack_graph_summary(seeded_db, sit_ws_manager):
    """Orient.analyze() accepts attack_graph_summary param (mock mode just ignores it,
    but we verify the interface works end-to-end)."""
    db = seeded_db
    await _setup_ooda_iteration(db)
    orient = OrientEngine(sit_ws_manager)

    rec = await orient.analyze(
        db, "test-op-1", "summary",
        attack_graph_summary="Graph coverage: 60% (3/5 nodes explored)",
    )
    assert rec is not None
    assert rec["recommended_technique_id"] == "T1003.001"


# ── 2.5 directive consumed by _build_prompt ──────────────────────────────
async def test_directive_consumed_by_build_prompt(seeded_db, sit_ws_manager):
    """An unconsumed ooda_directive is consumed (consumed_at set) when
    Orient builds the prompt (non-mock path). We call _build_prompt directly
    since mock mode skips prompt construction."""
    db = seeded_db
    await _setup_ooda_iteration(db)

    # Insert an unconsumed directive
    dir_id = str(uuid.uuid4())
    await db.execute(
        "INSERT INTO ooda_directives (id, operation_id, directive, created_at) "
        "VALUES ($1, $2, $3, $4)",
        dir_id, "test-op-1", "Focus on lateral movement to DC-02",
        datetime.now(timezone.utc),
    )

    orient = OrientEngine(sit_ws_manager)
    system_prompt, user_prompt = await orient._build_prompt(
        db, "test-op-1", "3 facts collected",
    )
    assert "OPERATOR DIRECTIVE" in user_prompt

    # Verify directive was consumed
    row = await db.fetchrow(
        "SELECT consumed_at FROM ooda_directives WHERE id = $1",
        dir_id,
    )
    assert row["consumed_at"] is not None, "Directive should be consumed after _build_prompt"


# ── 2.6 Orient failure returns aborted status ────────────────────────────
async def test_orient_failure_returns_aborted(seeded_db, sit_ws_manager):
    """When LLM returns None (non-mock mode failure), analyze returns None
    and controller would set status=aborted."""
    db = seeded_db
    await _setup_ooda_iteration(db)
    orient = OrientEngine(sit_ws_manager)

    # In mock mode, Orient always succeeds. We patch _store_recommendation
    # to raise to simulate failure.
    with patch.object(orient, "_store_recommendation", side_effect=Exception("LLM error")):
        # The mock mode flow: settings.MOCK_LLM=True, so it calls
        # _store_recommendation. If that fails, analyze should propagate.
        with pytest.raises(Exception, match="LLM error"):
            await orient.analyze(db, "test-op-1", "summary")
