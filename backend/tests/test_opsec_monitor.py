# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.

"""Tests for OPSEC monitoring services — SPEC-048."""

from __future__ import annotations

import pytest

from app.services import opsec_monitor
from app.services.opsec_monitor import (
    compute_opsec_confidence_factor,
    compute_opsec_penalty,
)
from app.services import threat_level as tl_service


# ---------------------------------------------------------------------------
# record_event
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_record_event_inserts_row(seeded_db):
    """record_event should insert into opsec_events and return an id."""
    eid = await opsec_monitor.record_event(
        seeded_db, "test-op-1", "high_noise",
        severity="warning",
        detail={"technique": "T1595.001"},
        noise_points=8,
    )
    assert eid  # non-empty string
    row = await seeded_db.fetchrow(
        "SELECT * FROM opsec_events WHERE id = $1", eid,
    )
    assert row is not None
    assert row["event_type"] == "high_noise"
    assert row["noise_points"] == 8
    assert row["operation_id"] == "test-op-1"


@pytest.mark.asyncio
async def test_record_event_with_target(seeded_db):
    """record_event should store optional target/technique ids."""
    eid = await opsec_monitor.record_event(
        seeded_db, "test-op-1", "auth_failure",
        target_id="test-target-1",
        technique_id="T1003.001",
        noise_points=1,
    )
    row = await seeded_db.fetchrow(
        "SELECT target_id, technique_id FROM opsec_events WHERE id = $1", eid,
    )
    assert row["target_id"] == "test-target-1"
    assert row["technique_id"] == "T1003.001"


# ---------------------------------------------------------------------------
# compute_status
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_compute_status_clean(seeded_db):
    """With no opsec events, status should be all zeros/defaults."""
    status = await opsec_monitor.compute_status(seeded_db, "test-op-1")
    assert status.operation_id == "test-op-1"
    assert status.noise_score == 0.0
    assert status.exposure_count == 0
    # Budget should match SP profile (default 50)
    assert status.noise_budget_total == 50
    assert status.noise_budget_remaining == 50


@pytest.mark.asyncio
async def test_compute_status_with_noise(seeded_db):
    """noise_score should reflect accumulated noise_points."""
    for _ in range(3):
        await opsec_monitor.record_event(
            seeded_db, "test-op-1", "execution_noise",
            noise_points=8,
        )
    status = await opsec_monitor.compute_status(seeded_db, "test-op-1")
    # 3 * 8 = 24 pts * 2.0 = 48.0 noise_score
    assert status.noise_score == 48.0
    assert status.noise_budget_used == 24


@pytest.mark.asyncio
async def test_compute_status_exposure_count(seeded_db):
    """exposure_count should tally auth_failure/burst/detection events."""
    await opsec_monitor.record_event(
        seeded_db, "test-op-1", "auth_failure", noise_points=1,
    )
    await opsec_monitor.record_event(
        seeded_db, "test-op-1", "burst", noise_points=1,
    )
    await opsec_monitor.record_event(
        seeded_db, "test-op-1", "execution_noise", noise_points=3,
    )
    status = await opsec_monitor.compute_status(seeded_db, "test-op-1")
    # Only auth_failure + burst count as exposure (not execution_noise)
    assert status.exposure_count == 2


@pytest.mark.asyncio
async def test_compute_status_recent_events(seeded_db):
    """recent_events should return the last N events."""
    for i in range(3):
        await opsec_monitor.record_event(
            seeded_db, "test-op-1", f"event_{i}", noise_points=1,
        )
    status = await opsec_monitor.compute_status(seeded_db, "test-op-1")
    assert len(status.recent_events) == 3


# ---------------------------------------------------------------------------
# evaluate_after_act
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_evaluate_after_act_records_noise(seeded_db):
    """evaluate_after_act should record execution_noise event."""
    status = await opsec_monitor.evaluate_after_act(
        seeded_db, "test-op-1",
        technique_noise="high",
        target_id="test-target-1",
        technique_id="T1003.001",
    )
    assert status.noise_score > 0
    row = await seeded_db.fetchrow(
        "SELECT * FROM opsec_events WHERE operation_id = $1 AND event_type = 'execution_noise'",
        "test-op-1",
    )
    assert row is not None
    assert row["noise_points"] == 8  # high = 8 pts


@pytest.mark.asyncio
async def test_evaluate_after_act_failure_records_auth_failure(seeded_db):
    """Failed execution should also record an auth_failure event."""
    await opsec_monitor.evaluate_after_act(
        seeded_db, "test-op-1",
        technique_noise="medium",
        execution_success=False,
    )
    row = await seeded_db.fetchrow(
        "SELECT * FROM opsec_events WHERE operation_id = $1 AND event_type = 'auth_failure'",
        "test-op-1",
    )
    assert row is not None


@pytest.mark.asyncio
async def test_evaluate_after_act_burst_detection(seeded_db):
    """When >5 events in 10 min, evaluate_after_act should record burst event."""
    # Create 6 prior events
    for _ in range(6):
        await opsec_monitor.record_event(
            seeded_db, "test-op-1", "execution_noise", noise_points=1,
        )
    await opsec_monitor.evaluate_after_act(
        seeded_db, "test-op-1",
        technique_noise="low",
    )
    burst = await seeded_db.fetchrow(
        "SELECT * FROM opsec_events WHERE operation_id = $1 AND event_type = 'burst'",
        "test-op-1",
    )
    assert burst is not None


# ---------------------------------------------------------------------------
# compute_opsec_penalty (pure function)
# ---------------------------------------------------------------------------

def test_opsec_penalty_low_risk():
    assert compute_opsec_penalty(30.0) == 1.0

def test_opsec_penalty_medium_risk():
    assert compute_opsec_penalty(65.0) == 0.85

def test_opsec_penalty_high_risk():
    assert compute_opsec_penalty(85.0) == 0.70

def test_opsec_penalty_boundary():
    assert compute_opsec_penalty(60.0) == 1.0   # <= 60 is OK
    assert compute_opsec_penalty(60.1) == 0.85


# ---------------------------------------------------------------------------
# compute_opsec_confidence_factor (pure function)
# ---------------------------------------------------------------------------

def test_confidence_factor_clean():
    assert compute_opsec_confidence_factor(10.0) == 1.0

def test_confidence_factor_moderate():
    assert compute_opsec_confidence_factor(50.0) == 0.7

def test_confidence_factor_high():
    assert compute_opsec_confidence_factor(70.0) == 0.4

def test_confidence_factor_critical():
    assert compute_opsec_confidence_factor(90.0) == 0.1


# ---------------------------------------------------------------------------
# threat_level.compute_threat_level
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_threat_level_clean(seeded_db):
    """With no OPSEC events, threat_level should be low (mainly dwell_exposure)."""
    result = await tl_service.compute_threat_level(seeded_db, "test-op-1")
    assert result.operation_id == "test-op-1"
    assert 0.0 <= result.level <= 1.0
    # No noise or auth failures
    assert result.components["opsec_noise"] == 0.0
    assert result.components["auth_failures"] == 0.0
    assert result.components["detection_events"] == 0.0


@pytest.mark.asyncio
async def test_threat_level_with_noise(seeded_db):
    """Noise events should increase threat_level."""
    for _ in range(5):
        await opsec_monitor.record_event(
            seeded_db, "test-op-1", "execution_noise", noise_points=8,
        )
    result = await tl_service.compute_threat_level(seeded_db, "test-op-1")
    # 5 * 8 = 40 pts / 50.0 = 0.8 noise_factor * 0.35 weight = 0.28
    assert result.components["opsec_noise"] == 0.8
    assert result.level > 0.2


@pytest.mark.asyncio
async def test_threat_level_updates_operations(seeded_db):
    """compute_threat_level should write level to operations.threat_level."""
    for _ in range(3):
        await opsec_monitor.record_event(
            seeded_db, "test-op-1", "execution_noise", noise_points=8,
        )
    result = await tl_service.compute_threat_level(seeded_db, "test-op-1")
    row = await seeded_db.fetchrow(
        "SELECT threat_level FROM operations WHERE id = $1", "test-op-1",
    )
    assert abs(row["threat_level"] - result.level) < 0.001


@pytest.mark.asyncio
async def test_threat_level_auth_failures(seeded_db):
    """Auth failure events should contribute to threat_level."""
    for _ in range(10):
        await opsec_monitor.record_event(
            seeded_db, "test-op-1", "auth_failure", noise_points=1,
        )
    result = await tl_service.compute_threat_level(seeded_db, "test-op-1")
    # 10 / 20.0 = 0.5 auth_factor
    assert result.components["auth_failures"] == 0.5
