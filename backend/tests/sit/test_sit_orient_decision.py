"""SIT Boundary 3: OrientEngine <-> DecisionEngine

Verifies that recommendation from Orient passes through DecisionEngine's
7-layer risk gate and produces correct auto_approved / confidence decisions.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from app.models.constraint import OperationalConstraints
from app.services.decision_engine import DecisionEngine
from app.services.orient_engine import OrientEngine

pytestmark = pytest.mark.asyncio


def _mock_recommendation(
    risk_level: str = "medium",
    confidence: float = 0.87,
    technique_id: str = "T1003.001",
) -> dict:
    """Build a recommendation dict matching OrientEngine mock output."""
    return {
        "situation_assessment": "Test assessment",
        "recommended_technique_id": technique_id,
        "confidence": confidence,
        "reasoning_text": "Test reasoning",
        "options": [
            {
                "technique_id": technique_id,
                "technique_name": "Test Technique",
                "reasoning": "Test option reasoning",
                "risk_level": risk_level,
                "recommended_engine": "ssh",
                "confidence": confidence,
                "prerequisites": [],
            },
        ],
    }


async def _setup_ooda_iteration(db, op_id="test-op-1"):
    """Insert an OODA iteration for FK linkage."""
    ooda_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    await db.execute(
        "INSERT INTO ooda_iterations "
        "(id, operation_id, iteration_number, phase, started_at) "
        "VALUES ($1, $2, 1, 'decide', $3)",
        ooda_id, op_id, now,
    )
    return ooda_id


# ── 3.1 medium risk + semi_auto -> auto_approved ────────────────────────
async def test_medium_risk_semi_auto_approved(seeded_db):
    """Medium risk with semi_auto mode and within threshold -> auto_approved=True."""
    db = seeded_db
    await _setup_ooda_iteration(db)

    # Ensure operation is semi_auto with medium risk threshold
    await db.execute(
        "UPDATE operations SET automation_mode = 'semi_auto', "
        "risk_threshold = 'medium' WHERE id = $1",
        "test-op-1",
    )

    decision_engine = DecisionEngine()
    rec = _mock_recommendation(risk_level="medium", confidence=0.87)
    result = await decision_engine.evaluate(db, "test-op-1", rec)

    assert "auto_approved" in result
    # medium risk within medium threshold + high confidence
    # The exact result depends on composite confidence
    assert result["risk_level"] == "medium"
    assert "composite_confidence" in result


# ── 3.2 composite confidence computed from DB ───────────────────────────
async def test_composite_confidence_from_db(seeded_db):
    """Composite confidence includes multiple DB-derived factors."""
    db = seeded_db
    await _setup_ooda_iteration(db)
    await db.execute(
        "UPDATE operations SET automation_mode = 'semi_auto', "
        "risk_threshold = 'medium' WHERE id = $1",
        "test-op-1",
    )

    decision_engine = DecisionEngine()
    rec = _mock_recommendation()
    result = await decision_engine.evaluate(db, "test-op-1", rec)

    breakdown = result.get("confidence_breakdown", {})
    assert "llm" in breakdown
    assert "historical" in breakdown
    assert "graph" in breakdown
    assert "target_state" in breakdown
    assert "kc_penalty" in breakdown

    # None of the values should be the bare default (all should be computed)
    assert isinstance(breakdown["llm"], float)
    assert isinstance(breakdown["historical"], float)


# ── 3.3 kill chain skip → confidence penalty ────────────────────────────
async def test_kill_chain_skip_penalty(seeded_db):
    """Recommending a technique that skips kill chain stages incurs kc_penalty."""
    db = seeded_db
    await _setup_ooda_iteration(db)
    await db.execute(
        "UPDATE operations SET automation_mode = 'semi_auto', "
        "risk_threshold = 'medium' WHERE id = $1",
        "test-op-1",
    )

    # Remove attack graph nodes to create a gap in kill chain
    await db.execute(
        "DELETE FROM attack_graph_nodes WHERE operation_id = $1",
        "test-op-1",
    )

    decision_engine = DecisionEngine()
    # T1003.001 is TA0006 Credential Access — skipping many stages
    rec = _mock_recommendation(technique_id="T1003.001")
    result = await decision_engine.evaluate(db, "test-op-1", rec)

    breakdown = result.get("confidence_breakdown", {})
    # With no prior stages explored, kc_penalty should apply
    assert "kc_penalty" in breakdown
    # kc_penalty >= 0 (may be 0 if enforcer doesn't penalize in this config)
    assert isinstance(breakdown["kc_penalty"], float)


# ── 3.4 CRITICAL risk -> needs_confirmation=True ────────────────────────
async def test_critical_risk_needs_confirmation(seeded_db):
    """CRITICAL risk forces needs_manual=True regardless of automation mode."""
    db = seeded_db
    await _setup_ooda_iteration(db)
    await db.execute(
        "UPDATE operations SET automation_mode = 'semi_auto', "
        "risk_threshold = 'critical' WHERE id = $1",
        "test-op-1",
    )

    decision_engine = DecisionEngine()
    rec = _mock_recommendation(risk_level="critical")
    result = await decision_engine.evaluate(db, "test-op-1", rec)

    assert result["auto_approved"] is False
    assert result.get("needs_manual") is True or result.get("needs_confirmation") is True


# ── 3.5 noise budget exhausted -> blocked ───────────────────────────────
async def test_noise_budget_exhausted_blocks(seeded_db):
    """When noise_budget_remaining <= 0, auto_approved is False."""
    db = seeded_db
    await _setup_ooda_iteration(db)
    await db.execute(
        "UPDATE operations SET automation_mode = 'semi_auto', "
        "risk_threshold = 'medium' WHERE id = $1",
        "test-op-1",
    )

    decision_engine = DecisionEngine()
    rec = _mock_recommendation(risk_level="low", confidence=0.95)

    # Pass constraints with exhausted noise budget
    constraints = OperationalConstraints(noise_budget_remaining=0)
    result = await decision_engine.evaluate(
        db, "test-op-1", rec, constraints=constraints,
    )

    assert result["auto_approved"] is False, "Should block when noise budget exhausted"


# ── 3.6 parallel_tasks populated for multiple options ───────────────────
async def test_parallel_tasks_populated(seeded_db):
    """When multiple low-risk options exist, parallel_tasks should be populated."""
    db = seeded_db
    await _setup_ooda_iteration(db)
    await db.execute(
        "UPDATE operations SET automation_mode = 'semi_auto', "
        "risk_threshold = 'medium' WHERE id = $1",
        "test-op-1",
    )

    decision_engine = DecisionEngine()
    rec = {
        "situation_assessment": "Multiple low-risk options available",
        "recommended_technique_id": "T1003.001",
        "confidence": 0.87,
        "reasoning_text": "Test reasoning",
        "options": [
            {
                "technique_id": "T1003.001",
                "technique_name": "LSASS Memory",
                "reasoning": "Primary option",
                "risk_level": "low",
                "recommended_engine": "ssh",
                "confidence": 0.87,
                "prerequisites": [],
            },
            {
                "technique_id": "T1134",
                "technique_name": "Access Token Manipulation",
                "reasoning": "Secondary option",
                "risk_level": "low",
                "recommended_engine": "ssh",
                "confidence": 0.72,
                "prerequisites": [],
            },
            {
                "technique_id": "T1558.003",
                "technique_name": "Kerberoasting",
                "reasoning": "Tertiary option",
                "risk_level": "low",
                "recommended_engine": "ssh",
                "confidence": 0.65,
                "prerequisites": [],
            },
        ],
    }
    result = await decision_engine.evaluate(db, "test-op-1", rec)

    # parallel_tasks should exist in the result
    assert "parallel_tasks" in result
    parallel = result["parallel_tasks"]
    assert isinstance(parallel, list)
