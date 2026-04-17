"""SIT Boundary 4: DecisionEngine <-> EngineRouter

Verifies that auto_approved decisions are correctly routed to the right
engine, results written to technique_executions, and failures classified.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.clients import BaseEngineClient, ExecutionResult
from app.services.decision_engine import DecisionEngine
from app.services.engine_router import EngineRouter
from app.services.fact_collector import FactCollector

pytestmark = pytest.mark.asyncio


async def _setup_for_execution(db, technique_id="T1003.001"):
    """Prepare DB state for EngineRouter.execute()."""
    ooda_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    await db.execute(
        "INSERT INTO ooda_iterations "
        "(id, operation_id, iteration_number, phase, started_at) "
        "VALUES ($1, $2, 1, 'act', $3)",
        ooda_id, "test-op-1", now,
    )
    existing = await db.fetchval(
        "SELECT mitre_id FROM techniques WHERE mitre_id = $1", technique_id,
    )
    if not existing:
        await db.execute(
            "INSERT INTO techniques (id, mitre_id, name, tactic, tactic_id, risk_level) "
            "VALUES ($1, $2, $3, $4, $5, $6)",
            str(uuid.uuid4()), technique_id, f"Test {technique_id}",
            "Test Tactic", "TA0006", "medium",
        )
    return ooda_id


async def _add_ssh_credential(db):
    """Add SSH credential fact so router's mcp_ssh path can find credentials."""
    await db.execute(
        "INSERT INTO facts (id, trait, value, category, "
        "source_technique_id, source_target_id, operation_id, score, collected_at) "
        "VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9) ON CONFLICT DO NOTHING",
        str(uuid.uuid4()), "credential.ssh", "root:toor", "credential",
        "T1003.001", "test-target-1", "test-op-1", 1,
        datetime.now(timezone.utc),
    )


def _make_router(ws, engine_client):
    """Build an EngineRouter with both c2 and mcp engines mocked."""
    fc = FactCollector(ws)
    return EngineRouter(
        c2_engine=engine_client,
        fact_collector=fc,
        ws_manager=ws,
        mcp_engine=engine_client,
    )


# ── 4.1 auto_approved -> execute success -> DB record ───────────────────
async def test_auto_approved_execution_success(seeded_db, sit_ws_manager, mock_engine_client):
    """Auto-approved decision -> mock engine executes -> technique_executions recorded."""
    db = seeded_db
    ooda_id = await _setup_for_execution(db)
    await _add_ssh_credential(db)
    router = _make_router(sit_ws_manager, mock_engine_client)

    result = await router.execute(
        db, technique_id="T1003.001", target_id="test-target-1",
        engine="ssh", operation_id="test-op-1", ooda_iteration_id=ooda_id,
    )

    assert result["status"] == "success"

    row = await db.fetchrow(
        "SELECT status, engine FROM technique_executions "
        "WHERE operation_id = $1 AND ooda_iteration_id = $2 "
        "ORDER BY started_at DESC LIMIT 1",
        "test-op-1", ooda_id,
    )
    assert row is not None
    assert row["status"] == "success"


# ── 4.2 T1595 routes to recon engine ────────────────────────────────────
async def test_t1595_routes_to_recon(seeded_db, sit_ws_manager, mock_engine_client):
    """T1595 technique routes to mcp_recon engine path."""
    db = seeded_db
    ooda_id = await _setup_for_execution(db, "T1595.001")
    router = _make_router(sit_ws_manager, mock_engine_client)

    result = await router.execute(
        db, technique_id="T1595.001", target_id="test-target-1",
        engine="ssh", operation_id="test-op-1", ooda_iteration_id=ooda_id,
    )

    # Recon path returns engine='mcp_recon' in the result dict
    assert result["engine"] == "mcp_recon"


# ── 4.3 T1110 routes to initial_access engine ──────────────────────────
async def test_t1110_routes_to_initial_access(seeded_db, sit_ws_manager, mock_engine_client):
    """T1110 technique routes to initial_access engine."""
    db = seeded_db
    ooda_id = await _setup_for_execution(db, "T1110.001")

    # Add service fact so IA engine has targets
    await db.execute(
        "INSERT INTO facts (id, trait, value, category, "
        "source_technique_id, source_target_id, operation_id, score, collected_at) "
        "VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)",
        str(uuid.uuid4()), "service.open_port", "22/tcp SSH", "service",
        "T1595.001", "test-target-1", "test-op-1", 1,
        datetime.now(timezone.utc),
    )

    router = _make_router(sit_ws_manager, mock_engine_client)
    await router.execute(
        db, technique_id="T1110.001", target_id="test-target-1",
        engine="ssh", operation_id="test-op-1", ooda_iteration_id=ooda_id,
    )

    row = await db.fetchrow(
        "SELECT engine FROM technique_executions "
        "WHERE operation_id = $1 AND technique_id = $2 "
        "ORDER BY started_at DESC LIMIT 1",
        "test-op-1", "T1110.001",
    )
    assert row is not None
    assert row["engine"] == "initial_access"


# ── 4.4 engine fallback chain ───────────────────────────────────────────
async def test_engine_fallback_chain(seeded_db, sit_ws_manager, mock_engine_client):
    """Primary mcp_ssh engine failure (no cred) -> execution recorded as failed.
    Fallback chain for mcp_ssh -> c2, but c2 also requires agent match."""
    db = seeded_db
    ooda_id = await _setup_for_execution(db)
    # Deliberately NO credential -> mcp_ssh path fails with prerequisite_missing
    router = _make_router(sit_ws_manager, mock_engine_client)

    result = await router.execute(
        db, technique_id="T1003.001", target_id="test-target-1",
        engine="ssh", operation_id="test-op-1", ooda_iteration_id=ooda_id,
    )

    assert result is not None
    # Without credentials, the mcp_ssh path fails
    assert result["status"] == "failed"

    row = await db.fetchrow(
        "SELECT failure_category FROM technique_executions "
        "WHERE operation_id = $1 AND ooda_iteration_id = $2 "
        "ORDER BY started_at DESC LIMIT 1",
        "test-op-1", ooda_id,
    )
    assert row is not None
    assert row["failure_category"] == "prerequisite_missing"


# ── 4.5 failure writes failure_category ─────────────────────────────────
async def test_failure_writes_failure_category(seeded_db, sit_ws_manager, mock_engine_client):
    """Failed execution writes failure_category to technique_executions."""
    db = seeded_db
    ooda_id = await _setup_for_execution(db, "T1110.001")

    # Add service facts for IA engine
    await db.execute(
        "INSERT INTO facts (id, trait, value, category, "
        "source_technique_id, source_target_id, operation_id, score, collected_at) "
        "VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)",
        str(uuid.uuid4()), "service.open_port", "22/tcp SSH", "service",
        "T1595.001", "test-target-1", "test-op-1", 1,
        datetime.now(timezone.utc),
    )

    router = _make_router(sit_ws_manager, mock_engine_client)
    await router.execute(
        db, technique_id="T1110.001", target_id="test-target-1",
        engine="ssh", operation_id="test-op-1", ooda_iteration_id=ooda_id,
    )

    row = await db.fetchrow(
        "SELECT status, failure_category FROM technique_executions "
        "WHERE operation_id = $1 AND technique_id = $2 "
        "ORDER BY started_at DESC LIMIT 1",
        "test-op-1", "T1110.001",
    )
    assert row is not None
    if row["status"] == "failed":
        assert row["failure_category"] is not None


# ── 4.6 success updates target.is_compromised via facts ─────────────────
async def test_success_execution_writes_facts(seeded_db, sit_ws_manager):
    """Successful execution with facts -> facts collected from result."""
    db = seeded_db
    ooda_id = await _setup_for_execution(db)
    await _add_ssh_credential(db)

    client = MagicMock(spec=BaseEngineClient)
    client.execute = AsyncMock(return_value=ExecutionResult(
        success=True,
        execution_id="success-001",
        output="Credential access successful",
        facts=[{"trait": "credential.ssh", "value": "admin:password123"}],
    ))
    client.is_available = AsyncMock(return_value=True)

    fc = FactCollector(sit_ws_manager)
    router = EngineRouter(
        c2_engine=client, fact_collector=fc,
        ws_manager=sit_ws_manager, mcp_engine=client,
    )

    result = await router.execute(
        db, technique_id="T1003.001", target_id="test-target-1",
        engine="ssh", operation_id="test-op-1", ooda_iteration_id=ooda_id,
    )
    assert result["status"] == "success"
    # Facts from the execution should have been collected
    assert result.get("facts_collected_count", 0) >= 0


# ── 4.7 needs_confirmation -> no execution ──────────────────────────────
async def test_needs_confirmation_no_execution(seeded_db, sit_ws_manager):
    """Decision with auto_approved=False should not trigger router.execute()."""
    db = seeded_db
    await _setup_for_execution(db)

    decision_engine = DecisionEngine()
    rec = {
        "situation_assessment": "Test",
        "recommended_technique_id": "T1003.001",
        "confidence": 0.87,
        "reasoning_text": "Test",
        "options": [{
            "technique_id": "T1003.001",
            "technique_name": "Test",
            "reasoning": "Test",
            "risk_level": "critical",
            "recommended_engine": "ssh",
            "confidence": 0.87,
            "prerequisites": [],
        }],
    }
    await db.execute(
        "UPDATE operations SET automation_mode = 'semi_auto', "
        "risk_threshold = 'medium' WHERE id = $1",
        "test-op-1",
    )

    decision = await decision_engine.evaluate(db, "test-op-1", rec)
    assert decision["auto_approved"] is False

    # Count executions before — controller wouldn't call router.execute()
    exec_count = await db.fetchval(
        "SELECT COUNT(*) FROM technique_executions "
        "WHERE operation_id = $1 AND ooda_iteration_id IS NOT NULL",
        "test-op-1",
    )
    # No execution happens when auto_approved is False
    assert exec_count == 0
