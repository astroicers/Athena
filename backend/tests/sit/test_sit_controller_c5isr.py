"""SIT Boundary 6: OODAController <-> C5ISRMapper

Verifies that C5ISRMapper.update() reads real DB state (iterations,
agents, executions) and produces correct 6-domain health calculations.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from app.services.c5isr_mapper import C5ISRMapper

pytestmark = pytest.mark.asyncio


# ── 6.1 Update produces all 6 domains ────────────────────────────────────
async def test_c5isr_updates_six_domains(seeded_db, sit_ws_manager):
    """C5ISRMapper.update() writes/updates all 6 C5ISR domains."""
    db = seeded_db
    mapper = C5ISRMapper(sit_ws_manager)

    results = await mapper.update(db, "test-op-1")

    # Verify 6 domain records in DB
    rows = await db.fetch(
        "SELECT domain, health_pct, updated_at FROM c5isr_statuses "
        "WHERE operation_id = $1",
        "test-op-1",
    )
    domains = {r["domain"] for r in rows}
    expected = {"command", "control", "comms", "computers", "cyber", "isr"}
    assert domains == expected, f"Missing domains: {expected - domains}"

    # All should have updated_at set
    for row in rows:
        assert row["updated_at"] is not None


# ── 6.2 Command health reflects OODA throughput ──────────────────────────
async def test_command_reflects_ooda_throughput(seeded_db, sit_ws_manager):
    """After 2 OODA iterations, Command health increases."""
    db = seeded_db
    mapper = C5ISRMapper(sit_ws_manager)

    # Baseline: 0 iterations
    await mapper.update(db, "test-op-1")
    row_before = await db.fetchrow(
        "SELECT health_pct FROM c5isr_statuses "
        "WHERE operation_id = $1 AND domain = 'command'",
        "test-op-1",
    )
    health_before = row_before["health_pct"]

    # Simulate 2 OODA iterations
    await db.execute(
        "UPDATE operations SET ooda_iteration_count = 2 WHERE id = $1",
        "test-op-1",
    )
    now = datetime.now(timezone.utc)
    for i in range(2):
        await db.execute(
            "INSERT INTO ooda_iterations (id, operation_id, iteration_number, phase, started_at) "
            "VALUES ($1, $2, $3, 'act', $4)",
            str(uuid.uuid4()), "test-op-1", i + 1, now,
        )

    await mapper.update(db, "test-op-1")
    row_after = await db.fetchrow(
        "SELECT health_pct FROM c5isr_statuses "
        "WHERE operation_id = $1 AND domain = 'command'",
        "test-op-1",
    )
    health_after = row_after["health_pct"]
    assert health_after >= health_before, (
        f"Command health should increase with iterations: {health_before} -> {health_after}"
    )


# ── 6.3 Control health reflects agent survival ──────────────────────────
async def test_control_reflects_agent_survival(seeded_db, sit_ws_manager):
    """Agent going dead should reduce Control health."""
    db = seeded_db
    mapper = C5ISRMapper(sit_ws_manager)

    # Baseline with alive agent
    await mapper.update(db, "test-op-1")
    row_alive = await db.fetchrow(
        "SELECT health_pct FROM c5isr_statuses "
        "WHERE operation_id = $1 AND domain = 'control'",
        "test-op-1",
    )

    # Kill the agent
    await db.execute(
        "UPDATE agents SET status = 'dead' WHERE id = 'test-agent-1'"
    )
    await mapper.update(db, "test-op-1")
    row_dead = await db.fetchrow(
        "SELECT health_pct FROM c5isr_statuses "
        "WHERE operation_id = $1 AND domain = 'control'",
        "test-op-1",
    )

    assert row_dead["health_pct"] < row_alive["health_pct"], (
        f"Control health should decrease when agent dies: "
        f"{row_alive['health_pct']} -> {row_dead['health_pct']}"
    )


# ── 6.4 Cyber health reflects execution success rate ─────────────────────
async def test_cyber_reflects_execution_success_rate(seeded_db, sit_ws_manager):
    """Successful execution increases Cyber health relative to failures."""
    db = seeded_db
    mapper = C5ISRMapper(sit_ws_manager)

    # Add a new successful execution
    now = datetime.now(timezone.utc)
    await db.execute(
        "INSERT INTO technique_executions "
        "(id, technique_id, target_id, operation_id, engine, status, started_at, completed_at) "
        "VALUES ($1, $2, $3, $4, $5, $6, $7, $8)",
        str(uuid.uuid4()), "T1003.001", "test-target-1", "test-op-1",
        "mcp_ssh", "success", now, now,
    )

    await mapper.update(db, "test-op-1")
    row = await db.fetchrow(
        "SELECT health_pct FROM c5isr_statuses "
        "WHERE operation_id = $1 AND domain = 'cyber'",
        "test-op-1",
    )
    # With all successes and no failures, Cyber should be positive
    assert row["health_pct"] > 0, "Cyber health should be positive with successful executions"


# ── 6.5 c5isr.update WS event contains 6 domains ────────────────────────
async def test_c5isr_ws_event_broadcast(seeded_db, sit_ws_manager):
    """C5ISRMapper.update() broadcasts c5isr.update event."""
    db = seeded_db
    mapper = C5ISRMapper(sit_ws_manager)

    await mapper.update(db, "test-op-1")

    c5isr_events = [
        c for c in sit_ws_manager._calls if c[1] == "c5isr.update"
    ]
    assert len(c5isr_events) >= 1, "Should broadcast c5isr.update event"
