# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: [TODO: contact email]

"""SPEC-040: Composite confidence scoring tests.

Validates the four-source composite confidence formula:

    composite = 0.30 * llm + 0.30 * historical + 0.25 * graph + 0.15 * target_state - kc_penalty
    final     = clamp(composite, 0.0, 1.0)

Test cases TC-A1 through TC-A8 cover normal calculation, fallback defaults,
EDR detection, clamping, and various target state combinations.
"""

import uuid
from unittest.mock import AsyncMock

import aiosqlite
import pytest

from app.services.decision_engine import DecisionEngine
from app.services.kill_chain_enforcer import KillChainPenalty


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _uid() -> str:
    return str(uuid.uuid4())


async def _insert_operation(db: aiosqlite.Connection, op_id: str) -> None:
    await db.execute(
        "INSERT INTO operations (id, code, name, codename, strategic_intent, "
        "status, current_ooda_phase) "
        "VALUES (?, 'OP-CC', 'Composite Test', 'CC-TEST', 'test', 'active', 'decide')",
        (op_id,),
    )


async def _insert_target(
    db: aiosqlite.Connection,
    target_id: str,
    op_id: str,
    *,
    is_compromised: int = 0,
    privilege_level: str | None = None,
    access_status: str = "unknown",
    ip: str | None = None,
) -> None:
    ip = ip or f"10.0.0.{uuid.uuid4().int % 254 + 1}"
    await db.execute(
        "INSERT INTO targets (id, hostname, ip_address, os, role, operation_id, "
        "is_compromised, privilege_level, access_status) "
        "VALUES (?, 'host', ?, 'Linux', 'server', ?, ?, ?, ?)",
        (target_id, ip, op_id, is_compromised, privilege_level, access_status),
    )


async def _insert_technique_executions(
    db: aiosqlite.Connection,
    technique_id: str,
    target_id: str,
    op_id: str,
    *,
    success_count: int = 0,
    fail_count: int = 0,
) -> None:
    for _ in range(success_count):
        await db.execute(
            "INSERT INTO technique_executions (id, technique_id, target_id, operation_id, "
            "engine, status, started_at, completed_at) "
            "VALUES (?, ?, ?, ?, 'mcp_ssh', 'success', datetime('now'), datetime('now'))",
            (_uid(), technique_id, target_id, op_id),
        )
    for _ in range(fail_count):
        await db.execute(
            "INSERT INTO technique_executions (id, technique_id, target_id, operation_id, "
            "engine, status, started_at, completed_at) "
            "VALUES (?, ?, ?, ?, 'mcp_ssh', 'failed', datetime('now'), datetime('now'))",
            (_uid(), technique_id, target_id, op_id),
        )


async def _insert_graph_node(
    db: aiosqlite.Connection,
    op_id: str,
    target_id: str,
    technique_id: str,
    tactic_id: str,
    confidence: float,
) -> None:
    await db.execute(
        "INSERT INTO attack_graph_nodes (id, operation_id, target_id, technique_id, "
        "tactic_id, status, confidence) "
        "VALUES (?, ?, ?, ?, ?, 'pending', ?)",
        (_uid(), op_id, target_id, technique_id, tactic_id, confidence),
    )


async def _insert_edr_fact(
    db: aiosqlite.Connection,
    target_id: str,
    op_id: str,
    trait: str = "host.edr",
) -> None:
    await db.execute(
        "INSERT INTO facts (id, trait, value, category, source_target_id, operation_id) "
        "VALUES (?, ?, 'CrowdStrike', 'host', ?, ?)",
        (_uid(), trait, target_id, op_id),
    )


def _kc_enforcer_mock() -> AsyncMock:
    """Create a mock enforcer whose evaluate_skip returns zero penalty."""
    enforcer = AsyncMock()
    enforcer.evaluate_skip = AsyncMock(
        return_value=KillChainPenalty(penalty=0.0, skipped_stages=[], warning=None),
    )
    return enforcer


# ---------------------------------------------------------------------------
# TC-A1: All four sources available, normal calculation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_tc_a1_all_four_sources(tmp_db: aiosqlite.Connection):
    """TC-A1: All four sources available, normal calculation.

    llm=0.80, historical=0.60 (3/5), graph=0.70, target_state=0.65 (root, not compromised)
    expected = 0.30*0.80 + 0.30*0.60 + 0.25*0.70 + 0.15*0.65 = 0.6925
    """
    op_id = _uid()
    target_id = _uid()
    technique_id = "T1003.001"

    await _insert_operation(tmp_db, op_id)
    await _insert_target(
        tmp_db, target_id, op_id,
        is_compromised=0, privilege_level="root", access_status="unknown",
    )
    # 3 success + 2 fail = 5 total => rate = 3/5 = 0.60
    await _insert_technique_executions(
        tmp_db, technique_id, target_id, op_id,
        success_count=3, fail_count=2,
    )
    # Graph node with confidence=0.70
    await _insert_graph_node(tmp_db, op_id, target_id, technique_id, "TA0006", 0.70)
    await tmp_db.commit()

    engine = DecisionEngine()
    engine._enforcer = _kc_enforcer_mock()

    composite, breakdown = await engine._compute_composite_confidence(
        tmp_db, op_id, technique_id, target_id,
        raw_confidence=0.80,
        tactic_id="TA0006",
    )

    assert breakdown["llm"] == pytest.approx(0.80)
    assert breakdown["historical"] == pytest.approx(0.60)
    assert breakdown["graph"] == pytest.approx(0.70)
    assert breakdown["target_state"] == pytest.approx(0.65)
    assert breakdown["kc_penalty"] == pytest.approx(0.0)

    expected = 0.30 * 0.80 + 0.30 * 0.60 + 0.25 * 0.70 + 0.15 * 0.65
    assert composite == pytest.approx(expected)
    assert composite == pytest.approx(0.6925)


# ---------------------------------------------------------------------------
# TC-A2: No history -> historical falls back to 0.5
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_tc_a2_no_history_fallback(tmp_db: aiosqlite.Connection):
    """TC-A2: No technique_executions records -> historical = 0.5."""
    op_id = _uid()
    target_id = _uid()
    technique_id = "T1059.001"

    await _insert_operation(tmp_db, op_id)
    await _insert_target(tmp_db, target_id, op_id)
    await _insert_graph_node(tmp_db, op_id, target_id, technique_id, "TA0002", 0.70)
    await tmp_db.commit()

    engine = DecisionEngine()
    engine._enforcer = _kc_enforcer_mock()

    _, breakdown = await engine._compute_composite_confidence(
        tmp_db, op_id, technique_id, target_id,
        raw_confidence=0.80,
        tactic_id="TA0002",
    )

    assert breakdown["historical"] == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# TC-A3: EDR detected -> target_state subtracts 0.2
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_tc_a3_edr_detected(tmp_db: aiosqlite.Connection):
    """TC-A3: EDR detected.

    base=0.5, is_compromised(+0.2), has_edr(-0.2) => target_state=0.5
    """
    op_id = _uid()
    target_id = _uid()
    technique_id = "T1003.001"

    await _insert_operation(tmp_db, op_id)
    await _insert_target(
        tmp_db, target_id, op_id,
        is_compromised=1,
    )
    await _insert_edr_fact(tmp_db, target_id, op_id, trait="host.edr")
    await tmp_db.commit()

    engine = DecisionEngine()
    engine._enforcer = _kc_enforcer_mock()

    _, breakdown = await engine._compute_composite_confidence(
        tmp_db, op_id, technique_id, target_id,
        raw_confidence=0.70,
        tactic_id="TA0006",
    )

    # 0.5 (base) + 0.2 (compromised) - 0.2 (EDR) = 0.5
    assert breakdown["target_state"] == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# TC-A4: LLM confidence out of range -> clamp
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_tc_a4_llm_clamp_high(tmp_db: aiosqlite.Connection):
    """TC-A4a: raw_confidence=1.5 -> clamped to 1.0."""
    op_id = _uid()
    target_id = _uid()
    technique_id = "T1059.001"

    await _insert_operation(tmp_db, op_id)
    await _insert_target(tmp_db, target_id, op_id)
    await tmp_db.commit()

    engine = DecisionEngine()
    engine._enforcer = _kc_enforcer_mock()

    _, breakdown = await engine._compute_composite_confidence(
        tmp_db, op_id, technique_id, target_id,
        raw_confidence=1.5,
        tactic_id="TA0002",
    )

    assert breakdown["llm"] == pytest.approx(1.0)


@pytest.mark.asyncio
async def test_tc_a4_llm_clamp_low(tmp_db: aiosqlite.Connection):
    """TC-A4b: raw_confidence=-0.3 -> clamped to 0.0."""
    op_id = _uid()
    target_id = _uid()
    technique_id = "T1059.001"

    await _insert_operation(tmp_db, op_id)
    await _insert_target(tmp_db, target_id, op_id)
    await tmp_db.commit()

    engine = DecisionEngine()
    engine._enforcer = _kc_enforcer_mock()

    _, breakdown = await engine._compute_composite_confidence(
        tmp_db, op_id, technique_id, target_id,
        raw_confidence=-0.3,
        tactic_id="TA0002",
    )

    assert breakdown["llm"] == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# TC-A5: target_id is None -> all DB queries skipped, use defaults
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_tc_a5_target_id_none(tmp_db: aiosqlite.Connection):
    """TC-A5: target_id=None -> historical=0.5, graph=0.5, target_state=0.5."""
    op_id = _uid()
    technique_id = "T9999.999"  # Non-existent technique ensures no history

    await _insert_operation(tmp_db, op_id)
    await tmp_db.commit()

    engine = DecisionEngine()
    engine._enforcer = _kc_enforcer_mock()

    composite, breakdown = await engine._compute_composite_confidence(
        tmp_db, op_id, technique_id, None,
        raw_confidence=0.80,
        tactic_id=None,
    )

    assert breakdown["historical"] == pytest.approx(0.5)
    assert breakdown["graph"] == pytest.approx(0.5)
    assert breakdown["target_state"] == pytest.approx(0.5)

    # 0.30*0.80 + 0.30*0.5 + 0.25*0.5 + 0.15*0.5 = 0.24 + 0.15 + 0.125 + 0.075 = 0.59
    expected = 0.30 * 0.80 + 0.30 * 0.5 + 0.25 * 0.5 + 0.15 * 0.5
    assert composite == pytest.approx(expected)
    assert composite == pytest.approx(0.59)


# ---------------------------------------------------------------------------
# TC-A6: Zero success rate -> historical=0.0
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_tc_a6_zero_success_rate(tmp_db: aiosqlite.Connection):
    """TC-A6: 5 executions all failed -> historical=0.0."""
    op_id = _uid()
    target_id = _uid()
    technique_id = "T1110.001"

    await _insert_operation(tmp_db, op_id)
    await _insert_target(tmp_db, target_id, op_id)
    await _insert_technique_executions(
        tmp_db, technique_id, target_id, op_id,
        success_count=0, fail_count=5,
    )
    await tmp_db.commit()

    engine = DecisionEngine()
    engine._enforcer = _kc_enforcer_mock()

    _, breakdown = await engine._compute_composite_confidence(
        tmp_db, op_id, technique_id, target_id,
        raw_confidence=0.70,
        tactic_id="TA0006",
    )

    assert breakdown["historical"] == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# TC-A7: Root + compromised -> target_state = 0.5 + 0.2 + 0.15 = 0.85
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_tc_a7_root_compromised(tmp_db: aiosqlite.Connection):
    """TC-A7: is_compromised + root privilege -> target_state = 0.85."""
    op_id = _uid()
    target_id = _uid()
    technique_id = "T1003.001"

    await _insert_operation(tmp_db, op_id)
    await _insert_target(
        tmp_db, target_id, op_id,
        is_compromised=1, privilege_level="root",
    )
    await tmp_db.commit()

    engine = DecisionEngine()
    engine._enforcer = _kc_enforcer_mock()

    _, breakdown = await engine._compute_composite_confidence(
        tmp_db, op_id, technique_id, target_id,
        raw_confidence=0.80,
        tactic_id="TA0006",
    )

    assert breakdown["target_state"] == pytest.approx(0.85)


# ---------------------------------------------------------------------------
# TC-A8: access_lost + EDR -> target_state = max(0.0, 0.5 - 0.1 - 0.2) = 0.2
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_tc_a8_access_lost_edr(tmp_db: aiosqlite.Connection):
    """TC-A8: access_lost + EDR -> target_state = 0.2."""
    op_id = _uid()
    target_id = _uid()
    technique_id = "T1003.001"

    await _insert_operation(tmp_db, op_id)
    await _insert_target(
        tmp_db, target_id, op_id,
        is_compromised=0, access_status="lost",
    )
    await _insert_edr_fact(tmp_db, target_id, op_id, trait="host.av")
    await tmp_db.commit()

    engine = DecisionEngine()
    engine._enforcer = _kc_enforcer_mock()

    _, breakdown = await engine._compute_composite_confidence(
        tmp_db, op_id, technique_id, target_id,
        raw_confidence=0.70,
        tactic_id="TA0006",
    )

    # 0.5 - 0.1 (access_lost) - 0.2 (host.av) = 0.2
    assert breakdown["target_state"] == pytest.approx(0.2)
