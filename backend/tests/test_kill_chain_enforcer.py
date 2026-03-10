# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: [TODO: contact email]

"""Tests for SPEC-040: KillChainEnforcer skip-stage penalty calculator.

Uses the ``tmp_db`` fixture (PostgreSQL with full Athena schema) so
that ``_get_completed_tactics`` exercises real SQL JOINs against
``technique_executions`` and ``attack_graph_nodes``.
"""

import uuid

import pytest

from app.services.kill_chain_enforcer import KillChainEnforcer, KillChainPenalty

# ---------------------------------------------------------------------------
#  Constants
# ---------------------------------------------------------------------------

OP_ID = "test-op-1"
TARGET_ID = "test-target-1"


# ---------------------------------------------------------------------------
#  Helpers
# ---------------------------------------------------------------------------

async def _seed_operation(db):
    """Insert a minimal operation row."""
    await db.execute(
        "INSERT INTO operations (id, code, name, codename, strategic_intent, "
        "status, current_ooda_phase) "
        "VALUES ($1, $2, $3, $4, $5, $6, $7)",
        OP_ID, "OP-001", "Test", "PHANTOM", "intent", "active", "observe",
    )


async def _seed_target(db, target_id: str = TARGET_ID):
    """Insert a minimal target row."""
    await db.execute(
        "INSERT INTO targets (id, hostname, ip_address, os, role, operation_id) "
        "VALUES ($1, $2, $3, $4, $5, $6)",
        target_id, "DC-01", "10.0.1.5", "Windows Server 2022",
        "Domain Controller", OP_ID,
    )


async def _mark_tactic_completed(
    db,
    tactic_id: str,
    technique_id: str | None = None,
    target_id: str = TARGET_ID,
):
    """Insert matching rows in ``technique_executions`` and
    ``attack_graph_nodes`` to simulate a successfully completed tactic stage.
    """
    tech_id = technique_id or f"T{uuid.uuid4().hex[:6]}"
    exec_id = str(uuid.uuid4())
    node_id = str(uuid.uuid4())

    await db.execute(
        "INSERT INTO technique_executions "
        "(id, technique_id, target_id, operation_id, engine, status) "
        "VALUES ($1, $2, $3, $4, $5, $6)",
        exec_id, tech_id, target_id, OP_ID, "mock", "success",
    )
    await db.execute(
        "INSERT INTO attack_graph_nodes "
        "(id, operation_id, target_id, technique_id, tactic_id, status, confidence) "
        "VALUES ($1, $2, $3, $4, $5, $6, $7)",
        node_id, OP_ID, target_id, tech_id, tactic_id, "completed", 0.9,
    )


# ---------------------------------------------------------------------------
#  TC-C1: No skip -> penalty = 0.0
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_no_skip_penalty_zero(tmp_db):
    """Recommend TA0002 (Execution, stage 3) with TA0043 + TA0001 completed.

    All prior required stages are done -> penalty = 0.0.
    """
    await _seed_operation(tmp_db)
    await _seed_target(tmp_db)
    await _mark_tactic_completed(tmp_db, "TA0043")  # Reconnaissance
    await _mark_tactic_completed(tmp_db, "TA0001")  # Initial Access

    enforcer = KillChainEnforcer()
    result = await enforcer.evaluate_skip(tmp_db, OP_ID, "TA0002", TARGET_ID)

    assert result.penalty == pytest.approx(0.0)
    assert result.skipped_stages == []
    assert result.warning is None


# ---------------------------------------------------------------------------
#  TC-C2: Skip 1 required stage -> penalty = 0.05
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_skip_one_required_stage(tmp_db):
    """Recommend TA0002 (Execution). Only TA0043 completed; TA0001 (Initial
    Access, required) is skipped -> penalty = 0.05.
    """
    await _seed_operation(tmp_db)
    await _seed_target(tmp_db)
    await _mark_tactic_completed(tmp_db, "TA0043")  # Reconnaissance only

    enforcer = KillChainEnforcer()
    result = await enforcer.evaluate_skip(tmp_db, OP_ID, "TA0002", TARGET_ID)

    assert result.penalty == pytest.approx(0.05)
    assert len(result.skipped_stages) == 1
    assert "TA0001" in result.skipped_stages[0]
    assert result.warning is not None


# ---------------------------------------------------------------------------
#  TC-C3: Skip optional stage -> penalty = 0.0
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_skip_optional_stage_no_penalty(tmp_db):
    """Recommend TA0004 (Privilege Escalation, stage 5). Prior required stages
    TA0043, TA0001, TA0002 completed. TA0003 (Persistence, optional) skipped
    -> penalty = 0.0.
    """
    await _seed_operation(tmp_db)
    await _seed_target(tmp_db)
    await _mark_tactic_completed(tmp_db, "TA0043")  # Reconnaissance
    await _mark_tactic_completed(tmp_db, "TA0001")  # Initial Access
    await _mark_tactic_completed(tmp_db, "TA0002")  # Execution

    enforcer = KillChainEnforcer()
    result = await enforcer.evaluate_skip(tmp_db, OP_ID, "TA0004", TARGET_ID)

    assert result.penalty == pytest.approx(0.0)
    assert result.skipped_stages == []
    assert result.warning is None


# ---------------------------------------------------------------------------
#  TC-C4: Max penalty -> 0.25
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_max_penalty_capped(tmp_db):
    """Recommend TA0040 (Impact, stage 13) with nothing completed.

    9 required stages skipped -> 9 * 0.05 = 0.45, capped at 0.25.
    """
    await _seed_operation(tmp_db)
    await _seed_target(tmp_db)

    enforcer = KillChainEnforcer()
    result = await enforcer.evaluate_skip(tmp_db, OP_ID, "TA0040", TARGET_ID)

    assert result.penalty == pytest.approx(0.25)
    assert len(result.skipped_stages) == 9
    assert result.warning is not None


# ---------------------------------------------------------------------------
#  TC-C5: Unknown tactic_id -> penalty = 0.0
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_unknown_tactic_id_penalty_zero(tmp_db):
    """tactic_id = 'TA9999' is not in the Kill Chain mapping -> penalty = 0.0."""
    await _seed_operation(tmp_db)

    enforcer = KillChainEnforcer()
    result = await enforcer.evaluate_skip(tmp_db, OP_ID, "TA9999", TARGET_ID)

    assert result.penalty == pytest.approx(0.0)
    assert result.skipped_stages == []
    assert result.warning is None


# ---------------------------------------------------------------------------
#  TC-C6: target_id is None -> operation-level query
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_target_id_none_operation_level(tmp_db):
    """target_id = None -> query at operation level (no target_id in SQL).

    Complete TA0043 + TA0001 for a specific target, then query with
    target_id=None. The operation-level query should still find them.
    """
    await _seed_operation(tmp_db)
    await _seed_target(tmp_db)
    await _mark_tactic_completed(tmp_db, "TA0043")  # Reconnaissance
    await _mark_tactic_completed(tmp_db, "TA0001")  # Initial Access

    enforcer = KillChainEnforcer()
    result = await enforcer.evaluate_skip(tmp_db, OP_ID, "TA0002", None)

    assert result.penalty == pytest.approx(0.0)
    assert result.skipped_stages == []


# ---------------------------------------------------------------------------
#  TC-C7: tactic_id is None -> penalty = 0.0
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_tactic_id_none_penalty_zero(tmp_db):
    """tactic_id = None -> early return with penalty = 0.0."""
    await _seed_operation(tmp_db)

    enforcer = KillChainEnforcer()
    result = await enforcer.evaluate_skip(tmp_db, OP_ID, None, TARGET_ID)

    assert result.penalty == pytest.approx(0.0)
    assert result.skipped_stages == []
    assert result.warning is None


# ---------------------------------------------------------------------------
#  TC-C8: Recommend stage 0 (TA0043) -> penalty = 0.0
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_recommend_stage_zero_no_penalty(tmp_db):
    """Recommend TA0043 (Reconnaissance, stage 0) -> no prior stages exist
    -> penalty = 0.0.
    """
    await _seed_operation(tmp_db)
    await _seed_target(tmp_db)

    enforcer = KillChainEnforcer()
    result = await enforcer.evaluate_skip(tmp_db, OP_ID, "TA0043", TARGET_ID)

    assert result.penalty == pytest.approx(0.0)
    assert result.skipped_stages == []
    assert result.warning is None
