"""SIT: Decision Engine Advanced — auto_full, NR1 matrix, MANUAL, blocked targets.

Verifies DecisionEngine.evaluate() with real DB state and various
automation modes, noise×risk matrix outcomes, and constraint overrides.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.asyncio


def _recommendation(
    technique_id: str = "T1003.001",
    risk_level: str = "low",
    confidence: float = 0.8,
    engine: str = "mcp_ssh",
) -> dict:
    return {
        "situation_assessment": "test",
        "recommended_technique_id": technique_id,
        "confidence": confidence,
        "reasoning_text": "test",
        "options": [{
            "technique_id": technique_id,
            "technique_name": "Test Technique",
            "reasoning": "test",
            "risk_level": risk_level,
            "recommended_engine": engine,
            "confidence": confidence,
            "prerequisites": [],
        }],
    }


# ── AF.1  auto_full bypasses confidence floor ────────────────────────────
async def test_auto_full_bypasses_confidence_floor(sit_services):
    """auto_full mode should auto-approve even with very low confidence."""
    db = sit_services.db

    # Set operation to auto_full mode
    await db.execute(
        "UPDATE operations SET automation_mode = 'auto_full', "
        "risk_threshold = 'medium' WHERE id = 'test-op-1'"
    )

    rec = _recommendation(confidence=0.3, risk_level="low")
    result = await sit_services.decision.evaluate(db, "test-op-1", rec)

    # auto_full bypasses the 0.5 confidence floor
    assert result["auto_approved"] is True


# ── AF.2  NR1 noise×risk matrix blocks auto-approve ─────────────────────
async def test_nr1_matrix_blocks_high_noise_high_risk(sit_services):
    """SR profile + high noise + high risk → needs_manual or needs_confirmation."""
    db = sit_services.db

    # Set SR mission profile (strictest)
    await db.execute(
        "UPDATE operations SET mission_profile = 'SR', "
        "automation_mode = 'semi_auto', risk_threshold = 'high' "
        "WHERE id = 'test-op-1'"
    )

    # Insert a technique record with high noise
    await db.execute(
        "INSERT INTO techniques (id, mitre_id, name, tactic, tactic_id, risk_level, noise_level) "
        "VALUES ('tech-af2', 'T9999.001', 'High Noise Test', 'Discovery', 'TA0007', 'high', 'high') "
        "ON CONFLICT DO NOTHING"
    )

    rec = _recommendation(technique_id="T9999.001", risk_level="high", confidence=0.9)
    result = await sit_services.decision.evaluate(db, "test-op-1", rec)

    # High noise + high risk in SR profile should NOT be auto-approved
    assert result["auto_approved"] is False


# ── AF.3  MANUAL mode never auto-approves ────────────────────────────────
async def test_manual_mode_never_auto_approves(sit_services):
    """MANUAL mode should always require commander approval, even for low risk."""
    db = sit_services.db

    await db.execute(
        "UPDATE operations SET automation_mode = 'manual', "
        "risk_threshold = 'high' WHERE id = 'test-op-1'"
    )

    rec = _recommendation(risk_level="low", confidence=0.95)
    result = await sit_services.decision.evaluate(db, "test-op-1", rec)

    assert result["auto_approved"] is False
    assert result.get("needs_manual") is True
    assert "Manual mode" in result.get("reason", "")


# ── AF.4  blocked_target by constraints → needs_manual ───────────────────
async def test_blocked_target_rejects_decision(sit_services):
    """Target in constraints.blocked_targets should be rejected immediately."""
    db = sit_services.db

    await db.execute(
        "UPDATE operations SET automation_mode = 'semi_auto', "
        "risk_threshold = 'medium' WHERE id = 'test-op-1'"
    )

    # Create constraints with blocked target
    constraints = MagicMock()
    constraints.noise_budget_remaining = 50
    constraints.min_confidence_override = None
    constraints.blocked_targets = ["test-target-1"]

    rec = _recommendation(risk_level="low", confidence=0.9)
    result = await sit_services.decision.evaluate(
        db, "test-op-1", rec, constraints=constraints,
    )

    assert result["auto_approved"] is False
    assert result.get("needs_manual") is True
    assert "blocked" in result.get("reason", "").lower()


# ── AF.5  validation_engine delta affects composite confidence ───────────
async def test_validation_engine_delta_lowers_confidence(sit_services):
    """Negative validation delta should reduce effective confidence."""
    db = sit_services.db

    await db.execute(
        "UPDATE operations SET automation_mode = 'semi_auto', "
        "risk_threshold = 'medium' WHERE id = 'test-op-1'"
    )

    # Patch ValidationEngine to return a negative delta
    from app.services.validation_engine import ValidationResult
    mock_val_result = ValidationResult(
        outcome="failed",
        delta=-0.4,
        checks=["cve_match: failed"],
    )

    original_validate = sit_services.decision._validation_engine.validate
    sit_services.decision._validation_engine.validate = AsyncMock(
        return_value=mock_val_result,
    )

    try:
        # Start with confidence=0.6 — after -0.4 delta, raw becomes 0.2
        # Composite confidence may be higher due to other factors, but
        # validation delta should demonstrably reduce the final confidence
        rec_low = _recommendation(risk_level="low", confidence=0.6)
        result_low = await sit_services.decision.evaluate(db, "test-op-1", rec_low)

        # Restore and run without delta for comparison
        sit_services.decision._validation_engine.validate = original_validate
        rec_high = _recommendation(risk_level="low", confidence=0.6)
        result_high = await sit_services.decision.evaluate(db, "test-op-1", rec_high)

        # The negative delta should produce lower composite confidence
        assert result_low["composite_confidence"] < result_high["composite_confidence"]
    finally:
        sit_services.decision._validation_engine.validate = original_validate
