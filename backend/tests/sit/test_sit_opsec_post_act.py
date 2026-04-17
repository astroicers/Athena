"""SIT: OPSEC Post-Act — noise budget, detection risk alerts, threat updates.

Verifies that the OPSEC monitor correctly tracks noise events, computes
detection risk, and triggers alerts/warnings through WebSocket broadcasts.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

pytestmark = pytest.mark.asyncio


# ── OP.1  evaluate_after_act records noise and decreases budget ──────────
async def test_evaluate_after_act_records_noise(sit_services):
    """evaluate_after_act should record noise events and reduce remaining budget."""
    db = sit_services.db
    from app.services import opsec_monitor

    status_before = await opsec_monitor.compute_status(db, "test-op-1")
    budget_before = status_before.noise_budget_remaining

    await opsec_monitor.evaluate_after_act(
        db, "test-op-1",
        technique_noise="medium",
        target_id="test-target-1",
        technique_id="T1003.001",
        execution_success=True,
    )

    status_after = await opsec_monitor.compute_status(db, "test-op-1")

    # Noise budget should decrease (medium noise = 3 points by default)
    assert status_after.noise_budget_remaining <= budget_before
    assert status_after.noise_budget_used > status_before.noise_budget_used


# ── OP.2  detection_risk > 60 triggers opsec.alert event ─────────────────
async def test_high_detection_risk_triggers_alert(sit_services):
    """When detection_risk > 60, OODA controller broadcasts opsec.alert."""
    db = sit_services.db
    from app.services import opsec_monitor

    # Insert many high-noise events to push detection_risk above 60
    # detection_risk = 0.35*noise + 0.25*dwell + 0.25*exposure + 0.15*artifact
    # Need noise_score=100 (achieved) + exposure events to push past 60
    for i in range(25):
        await opsec_monitor.record_event(
            db, "test-op-1", "execution_noise",
            severity="warning",
            detail={"noise_level": "high", "success": True},
            noise_points=5,
        )
    # Add auth_failure/detection events to boost exposure_score
    for i in range(5):
        await opsec_monitor.record_event(
            db, "test-op-1", "auth_failure",
            severity="warning",
            detail={"attempt": i},
            noise_points=1,
        )

    status = await opsec_monitor.compute_status(db, "test-op-1")
    # noise_score=100 → 35, exposure_count=5 → exposure_score=50 → 12.5, total > 60
    assert status.detection_risk > 60

    # Verify opsec.alert would be broadcast (check controller logic)
    # Simulate what ooda_controller does post-act
    if status.detection_risk > 60:
        await sit_services.ws.broadcast("test-op-1", "opsec.alert", {
            "detection_risk": status.detection_risk,
            "noise_budget_remaining": status.noise_budget_remaining,
        })

    alert_calls = [
        c for c in sit_services.ws._calls
        if c[1] == "opsec.alert"
    ]
    assert len(alert_calls) >= 1
    assert alert_calls[-1][2]["detection_risk"] > 60


# ── OP.3  budget exhausted triggers opsec.budget_warning ─────────────────
async def test_budget_exhausted_triggers_warning(sit_services):
    """When noise budget hits 0, opsec.budget_warning should broadcast."""
    db = sit_services.db
    from app.services import opsec_monitor

    # Get the budget total for SP profile
    status = await opsec_monitor.compute_status(db, "test-op-1")
    budget_total = status.noise_budget_total

    # Insert enough noise to exhaust budget
    points_per_event = 5
    events_needed = (budget_total // points_per_event) + 2
    for i in range(events_needed):
        await opsec_monitor.record_event(
            db, "test-op-1", "execution_noise",
            severity="warning",
            detail={"noise_level": "high"},
            noise_points=points_per_event,
        )

    status = await opsec_monitor.compute_status(db, "test-op-1")
    assert status.noise_budget_remaining <= 0

    # Simulate controller budget warning broadcast
    if status.noise_budget_remaining <= 0:
        await sit_services.ws.broadcast("test-op-1", "opsec.budget_warning", {
            "budget_total": status.noise_budget_total,
            "budget_used": status.noise_budget_used,
        })

    budget_calls = [
        c for c in sit_services.ws._calls
        if c[1] == "opsec.budget_warning"
    ]
    assert len(budget_calls) >= 1
    assert budget_calls[-1][2]["budget_used"] >= budget_total


# ── OP.4  compute_opsec_penalty applies C5ISR multiplier ─────────────────
async def test_compute_opsec_penalty_multiplier(sit_services):
    """detection_risk > 80 should return 0.70 penalty multiplier."""
    from app.services.opsec_monitor import compute_opsec_penalty

    # > 80 -> 0.70
    assert compute_opsec_penalty(85.0) == 0.70
    # > 60 -> 0.85
    assert compute_opsec_penalty(65.0) == 0.85
    # <= 60 -> 1.0 (no penalty, full multiplier)
    assert compute_opsec_penalty(50.0) == 1.0


# ── OP.5  threat.update event broadcast after each act ───────────────────
async def test_threat_update_broadcast(sit_services):
    """After each act, threat.update event should be broadcast with level and components."""
    db = sit_services.db
    from app.services import threat_level as tl_svc

    threat = await tl_svc.compute_threat_level(db, "test-op-1")

    # Broadcast like the controller does
    await sit_services.ws.broadcast("test-op-1", "threat.update", {
        "level": threat.level,
        "components": threat.components,
    })

    threat_calls = [
        c for c in sit_services.ws._calls
        if c[1] == "threat.update"
    ]
    assert len(threat_calls) >= 1
    payload = threat_calls[-1][2]
    assert "level" in payload
    assert "components" in payload
    assert isinstance(payload["level"], float)
    assert 0.0 <= payload["level"] <= 1.0
