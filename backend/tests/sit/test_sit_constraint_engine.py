"""SIT: ConstraintEngine integration — C5ISR health to operational constraints."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

import pytest

from app.services import constraint_engine as ce

pytestmark = pytest.mark.asyncio


# -- C.1 normal health -> no hard limits -------------------------------------
async def test_normal_health_no_hard_limits(sit_services):
    """With default seed data (healthy C5ISR), evaluate() returns no hard_limits."""
    db = sit_services.db

    result = await ce.evaluate(db, "test-op-1", "SP")

    assert isinstance(result.hard_limits, list)
    assert len(result.hard_limits) == 0, (
        f"Expected no hard_limits with healthy defaults, got: {result.hard_limits}"
    )


# -- C.2 low command health reduces orient options ----------------------------
async def test_low_command_health_reduces_orient_options(sit_services):
    """Command domain health < 50 -> orient_max_options <= 2."""
    db = sit_services.db

    # Overwrite command health to 25 (below SP warning threshold of 50)
    await db.execute(
        "UPDATE c5isr_statuses SET health_pct = 25.0 "
        "WHERE operation_id = $1 AND domain = 'command'",
        "test-op-1",
    )

    result = await ce.evaluate(db, "test-op-1", "SP")

    assert result.orient_max_options <= 2, (
        f"Low command health should reduce orient_max_options, got {result.orient_max_options}"
    )


# -- C.3 critical control forces recovery ------------------------------------
async def test_critical_control_forces_recovery(sit_services):
    """Control domain health < 25 (critical) -> forced_mode='recovery'."""
    db = sit_services.db

    # Set control health to critical level (below SP critical threshold of 25)
    await db.execute(
        "UPDATE c5isr_statuses SET health_pct = 10.0 "
        "WHERE operation_id = $1 AND domain = 'control'",
        "test-op-1",
    )

    result = await ce.evaluate(db, "test-op-1", "SP")

    assert result.forced_mode == "recovery", (
        f"Critical control health should force recovery mode, got '{result.forced_mode}'"
    )


# -- C.4 noise budget from profile -------------------------------------------
async def test_noise_budget_from_profile(sit_services):
    """Default SP profile provides a reasonable noise_budget_remaining."""
    db = sit_services.db

    result = await ce.evaluate(db, "test-op-1", "SP")

    assert result.noise_budget_remaining is not None, (
        "noise_budget_remaining should not be None"
    )
    assert isinstance(result.noise_budget_remaining, int), (
        f"noise_budget_remaining should be int, got {type(result.noise_budget_remaining)}"
    )
    assert result.noise_budget_remaining > 0, (
        f"noise_budget_remaining should be positive, got {result.noise_budget_remaining}"
    )


# -- C.5 active overrides from event_store -----------------------------------
async def test_active_overrides_from_event_store(sit_services):
    """An override event in event_store causes the domain to appear in active_overrides."""
    db = sit_services.db

    # Insert an override event for the 'comms' domain
    await db.execute(
        "INSERT INTO event_store (id, operation_id, event_type, payload, actor) "
        "VALUES ($1, 'test-op-1', 'constraint.override', $2, 'commander')",
        str(uuid.uuid4()),
        json.dumps({"domain": "comms", "reason": "manual override", "ttl_rounds": 3}),
    )

    result = await ce.evaluate(db, "test-op-1", "SP")

    assert "comms" in result.active_overrides, (
        f"'comms' should appear in active_overrides after override event, "
        f"got: {result.active_overrides}"
    )
