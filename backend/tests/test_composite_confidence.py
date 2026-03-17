# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: azz093093.830330@gmail.com

"""SPEC-040: Composite confidence scoring tests.

Validates the four-source composite confidence formula:

    composite = 0.30 * llm + 0.30 * historical + 0.25 * graph + 0.15 * target_state - kc_penalty
    final     = clamp(composite, 0.0, 1.0)

Test cases TC-A1 through TC-A8 cover normal calculation, fallback defaults,
EDR detection, clamping, and various target state combinations.
"""

import uuid
from unittest.mock import AsyncMock

import asyncpg
import pytest

from app.services.decision_engine import DecisionEngine
from app.services.kill_chain_enforcer import KillChainPenalty


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _uid() -> str:
    return str(uuid.uuid4())


async def _insert_operation(db: asyncpg.Connection, op_id: str) -> None:
    await db.execute(
        "INSERT INTO operations (id, code, name, codename, strategic_intent, "
        "status, current_ooda_phase) "
        "VALUES ($1, 'OP-CC', 'Composite Test', 'CC-TEST', 'test', 'active', 'decide')",
        op_id,
    )


async def _insert_target(
    db: asyncpg.Connection,
    target_id: str,
    op_id: str,
    *,
    is_compromised: bool = False,
    privilege_level: str | None = None,
    access_status: str = "unknown",
    ip: str | None = None,
) -> None:
    ip = ip or f"10.0.0.{uuid.uuid4().int % 254 + 1}"
    await db.execute(
        "INSERT INTO targets (id, hostname, ip_address, os, role, operation_id, "
        "is_compromised, privilege_level, access_status) "
        "VALUES ($1, 'host', $2, 'Linux', 'server', $3, $4, $5, $6)",
        target_id, ip, op_id, is_compromised, privilege_level, access_status,
    )


async def _insert_technique_executions(
    db: asyncpg.Connection,
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
            "VALUES ($1, $2, $3, $4, 'mcp_ssh', 'success', NOW(), NOW())",
            _uid(), technique_id, target_id, op_id,
        )
    for _ in range(fail_count):
        await db.execute(
            "INSERT INTO technique_executions (id, technique_id, target_id, operation_id, "
            "engine, status, started_at, completed_at) "
            "VALUES ($1, $2, $3, $4, 'mcp_ssh', 'failed', NOW(), NOW())",
            _uid(), technique_id, target_id, op_id,
        )


async def _insert_graph_node(
    db: asyncpg.Connection,
    op_id: str,
    target_id: str,
    technique_id: str,
    tactic_id: str,
    confidence: float,
) -> None:
    await db.execute(
        "INSERT INTO attack_graph_nodes (id, operation_id, target_id, technique_id, "
        "tactic_id, status, confidence) "
        "VALUES ($1, $2, $3, $4, $5, 'pending', $6)",
        _uid(), op_id, target_id, technique_id, tactic_id, confidence,
    )


async def _insert_edr_fact(
    db: asyncpg.Connection,
    target_id: str,
    op_id: str,
    trait: str = "host.edr",
) -> None:
    await db.execute(
        "INSERT INTO facts (id, trait, value, category, source_target_id, operation_id) "
        "VALUES ($1, $2, 'CrowdStrike', 'host', $3, $4)",
        _uid(), trait, target_id, op_id,
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
async def test_tc_a1_all_four_sources(tmp_db: asyncpg.Connection):
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
        is_compromised=False, privilege_level="root", access_status="unknown",
    )
    # 3 success + 2 fail = 5 total => rate = 3/5 = 0.60
    await _insert_technique_executions(
        tmp_db, technique_id, target_id, op_id,
        success_count=3, fail_count=2,
    )
    # Graph node with confidence=0.70
    await _insert_graph_node(tmp_db, op_id, target_id, technique_id, "TA0006", 0.70)

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
    assert breakdown["opsec_factor"] == pytest.approx(1.0)  # no OPSEC events
    assert breakdown["kc_penalty"] == pytest.approx(0.0)

    # SPEC-048: 5-source weights = 0.25 LLM + 0.25 hist + 0.20 graph + 0.15 target + 0.15 opsec
    expected = 0.25 * 0.80 + 0.25 * 0.60 + 0.20 * 0.70 + 0.15 * 0.65 + 0.15 * 1.0
    assert composite == pytest.approx(expected)
    assert composite == pytest.approx(0.7375)


# ---------------------------------------------------------------------------
# TC-A2: No history -> historical falls back to 0.5
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_tc_a2_no_history_fallback(tmp_db: asyncpg.Connection):
    """TC-A2: No technique_executions records -> historical = 0.5."""
    op_id = _uid()
    target_id = _uid()
    technique_id = "T1059.001"

    await _insert_operation(tmp_db, op_id)
    await _insert_target(tmp_db, target_id, op_id)
    await _insert_graph_node(tmp_db, op_id, target_id, technique_id, "TA0002", 0.70)

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
async def test_tc_a3_edr_detected(tmp_db: asyncpg.Connection):
    """TC-A3: EDR detected.

    base=0.5, is_compromised(+0.2), has_edr(-0.2) => target_state=0.5
    """
    op_id = _uid()
    target_id = _uid()
    technique_id = "T1003.001"

    await _insert_operation(tmp_db, op_id)
    await _insert_target(
        tmp_db, target_id, op_id,
        is_compromised=True,
    )
    await _insert_edr_fact(tmp_db, target_id, op_id, trait="host.edr")

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
async def test_tc_a4_llm_clamp_high(tmp_db: asyncpg.Connection):
    """TC-A4a: raw_confidence=1.5 -> clamped to 1.0."""
    op_id = _uid()
    target_id = _uid()
    technique_id = "T1059.001"

    await _insert_operation(tmp_db, op_id)
    await _insert_target(tmp_db, target_id, op_id)

    engine = DecisionEngine()
    engine._enforcer = _kc_enforcer_mock()

    _, breakdown = await engine._compute_composite_confidence(
        tmp_db, op_id, technique_id, target_id,
        raw_confidence=1.5,
        tactic_id="TA0002",
    )

    assert breakdown["llm"] == pytest.approx(1.0)


@pytest.mark.asyncio
async def test_tc_a4_llm_clamp_low(tmp_db: asyncpg.Connection):
    """TC-A4b: raw_confidence=-0.3 -> clamped to 0.0."""
    op_id = _uid()
    target_id = _uid()
    technique_id = "T1059.001"

    await _insert_operation(tmp_db, op_id)
    await _insert_target(tmp_db, target_id, op_id)

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
async def test_tc_a5_target_id_none(tmp_db: asyncpg.Connection):
    """TC-A5: target_id=None -> historical=0.5, graph=0.5, target_state=0.5."""
    op_id = _uid()
    technique_id = "T9999.999"  # Non-existent technique ensures no history

    await _insert_operation(tmp_db, op_id)

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

    # SPEC-048: 0.25*0.80 + 0.25*0.5 + 0.20*0.5 + 0.15*0.5 + 0.15*1.0 = 0.65
    expected = 0.25 * 0.80 + 0.25 * 0.5 + 0.20 * 0.5 + 0.15 * 0.5 + 0.15 * 1.0
    assert composite == pytest.approx(expected)
    assert composite == pytest.approx(0.65)


# ---------------------------------------------------------------------------
# TC-A6: Zero success rate -> historical=0.0
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_tc_a6_zero_success_rate(tmp_db: asyncpg.Connection):
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
async def test_tc_a7_root_compromised(tmp_db: asyncpg.Connection):
    """TC-A7: is_compromised + root privilege -> target_state = 0.85."""
    op_id = _uid()
    target_id = _uid()
    technique_id = "T1003.001"

    await _insert_operation(tmp_db, op_id)
    await _insert_target(
        tmp_db, target_id, op_id,
        is_compromised=True, privilege_level="root",
    )

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
async def test_tc_a8_access_lost_edr(tmp_db: asyncpg.Connection):
    """TC-A8: access_lost + EDR -> target_state = 0.2."""
    op_id = _uid()
    target_id = _uid()
    technique_id = "T1003.001"

    await _insert_operation(tmp_db, op_id)
    await _insert_target(
        tmp_db, target_id, op_id,
        is_compromised=False, access_status="lost",
    )
    await _insert_edr_fact(tmp_db, target_id, op_id, trait="host.av")

    engine = DecisionEngine()
    engine._enforcer = _kc_enforcer_mock()

    _, breakdown = await engine._compute_composite_confidence(
        tmp_db, op_id, technique_id, target_id,
        raw_confidence=0.70,
        tactic_id="TA0006",
    )

    # 0.5 - 0.1 (access_lost) - 0.2 (host.av) = 0.2
    assert breakdown["target_state"] == pytest.approx(0.2)
