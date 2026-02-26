# Copyright 2026 Athena Contributors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""OODA service unit tests — SPEC-007 acceptance criteria."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import aiosqlite

from app.clients import ExecutionResult
from app.models.enums import C5ISRDomainStatus
from app.services.c5isr_mapper import C5ISRMapper
from app.services.decision_engine import DecisionEngine
from app.services.engine_router import EngineRouter
from app.services.fact_collector import FactCollector
from app.services.orient_engine import OrientEngine
from app.services.ooda_controller import OODAController


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_ws():
    ws = MagicMock()
    ws.broadcast = AsyncMock()
    return ws


def _mock_recommendation(
    risk_level="medium", confidence=0.87, technique_id="T1003.001",
):
    """Return a recommendation dict matching OrientEngine mock output shape."""
    return {
        "situation_assessment": "Test situation assessment",
        "recommended_technique_id": technique_id,
        "confidence": confidence,
        "reasoning_text": "Test reasoning",
        "options": [
            {
                "technique_id": technique_id,
                "technique_name": "Test Technique",
                "reasoning": "Test reasoning",
                "risk_level": risk_level,
                "recommended_engine": "caldera",
                "confidence": confidence,
                "prerequisites": [],
            },
            {
                "technique_id": "T1134",
                "technique_name": "Access Token Manipulation",
                "reasoning": "Lower risk",
                "risk_level": "low",
                "recommended_engine": "caldera",
                "confidence": 0.72,
                "prerequisites": [],
            },
            {
                "technique_id": "T1548.002",
                "technique_name": "Bypass UAC",
                "reasoning": "Alternative",
                "risk_level": "low",
                "recommended_engine": "shannon",
                "confidence": 0.65,
                "prerequisites": [],
            },
        ],
    }


# ===================================================================
# DecisionEngine (7 tests)
# ===================================================================


async def test_decision_manual_mode_always_needs_approval(seeded_db):
    """MANUAL mode → auto_approved=False regardless of risk level."""
    await seeded_db.execute(
        "UPDATE operations SET automation_mode = 'manual', risk_threshold = 'medium' "
        "WHERE id = 'test-op-1'"
    )
    await seeded_db.commit()

    engine = DecisionEngine()
    result = await engine.evaluate(
        seeded_db, "test-op-1", _mock_recommendation(risk_level="low"),
    )
    assert result["auto_approved"] is False
    assert result["needs_manual"] is True


async def test_decision_low_confidence_forces_manual(seeded_db):
    """confidence < 0.5 → needs_confirmation=True."""
    await seeded_db.execute(
        "UPDATE operations SET automation_mode = 'semi_auto', risk_threshold = 'medium' "
        "WHERE id = 'test-op-1'"
    )
    await seeded_db.commit()

    engine = DecisionEngine()
    result = await engine.evaluate(
        seeded_db, "test-op-1", _mock_recommendation(confidence=0.3),
    )
    assert result["auto_approved"] is False
    assert result["needs_confirmation"] is True


async def test_decision_critical_risk_always_manual(seeded_db):
    """CRITICAL risk → needs_manual=True."""
    engine = DecisionEngine()
    result = await engine.evaluate(
        seeded_db, "test-op-1", _mock_recommendation(risk_level="critical"),
    )
    assert result["auto_approved"] is False
    assert result["needs_manual"] is True


async def test_decision_high_risk_needs_confirmation(seeded_db):
    """HIGH risk → auto_approved=False, needs_confirmation=True (HexConfirmModal)."""
    engine = DecisionEngine()
    result = await engine.evaluate(
        seeded_db, "test-op-1", _mock_recommendation(risk_level="high"),
    )
    assert result["auto_approved"] is False
    assert result["needs_confirmation"] is True
    assert result["needs_manual"] is False


async def test_decision_low_risk_auto_approved(seeded_db):
    """LOW risk with threshold=medium → auto_approved=True."""
    await seeded_db.execute(
        "UPDATE operations SET automation_mode = 'semi_auto', risk_threshold = 'medium' "
        "WHERE id = 'test-op-1'"
    )
    await seeded_db.commit()

    engine = DecisionEngine()
    result = await engine.evaluate(
        seeded_db, "test-op-1", _mock_recommendation(risk_level="low"),
    )
    assert result["auto_approved"] is True
    assert result["needs_confirmation"] is False


async def test_decision_medium_risk_within_threshold(seeded_db):
    """MEDIUM risk with threshold=medium → auto_approved=True."""
    await seeded_db.execute(
        "UPDATE operations SET automation_mode = 'semi_auto', risk_threshold = 'medium' "
        "WHERE id = 'test-op-1'"
    )
    await seeded_db.commit()

    engine = DecisionEngine()
    result = await engine.evaluate(
        seeded_db, "test-op-1", _mock_recommendation(risk_level="medium"),
    )
    assert result["auto_approved"] is True


async def test_decision_medium_risk_above_threshold(seeded_db):
    """MEDIUM risk with threshold=low → needs_confirmation=True."""
    await seeded_db.execute(
        "UPDATE operations SET automation_mode = 'semi_auto', risk_threshold = 'low' "
        "WHERE id = 'test-op-1'"
    )
    await seeded_db.commit()

    engine = DecisionEngine()
    result = await engine.evaluate(
        seeded_db, "test-op-1", _mock_recommendation(risk_level="medium"),
    )
    assert result["auto_approved"] is False
    assert result["needs_confirmation"] is True


# ===================================================================
# OrientEngine (3 tests)
# ===================================================================


async def test_orient_mock_returns_recommendation(seeded_db):
    """MOCK_LLM=true → returns dict with situation_assessment + options."""
    ws = _make_ws()
    orient = OrientEngine(ws)
    rec = await orient.analyze(seeded_db, "test-op-1", "No intelligence yet.")
    assert "situation_assessment" in rec
    assert isinstance(rec["options"], list)
    assert len(rec["options"]) == 3


async def test_orient_mock_confidence(seeded_db):
    """Mock confidence = 0.87 per SPEC-007."""
    ws = _make_ws()
    orient = OrientEngine(ws)
    rec = await orient.analyze(seeded_db, "test-op-1", "No intelligence yet.")
    assert rec["confidence"] == 0.87


async def test_orient_mock_recommended_technique(seeded_db):
    """Mock recommended technique = T1003.001 per SPEC-007."""
    ws = _make_ws()
    orient = OrientEngine(ws)
    rec = await orient.analyze(seeded_db, "test-op-1", "No intelligence yet.")
    assert rec["recommended_technique_id"] == "T1003.001"
    # Verify it was stored in DB
    cursor = await seeded_db.execute(
        "SELECT recommended_technique_id FROM recommendations WHERE operation_id = 'test-op-1'"
    )
    row = await cursor.fetchone()
    assert row is not None


# ===================================================================
# OrientEngine — Prompt Structure (5 tests, SPEC-015)
# ===================================================================


async def test_orient_build_prompt_returns_tuple(seeded_db):
    """_build_prompt() returns (system_prompt, user_prompt) tuple."""
    seeded_db.row_factory = aiosqlite.Row
    ws = _make_ws()
    orient = OrientEngine(ws)
    result = await orient._build_prompt(seeded_db, "test-op-1", "Test summary")
    assert isinstance(result, tuple)
    assert len(result) == 2
    system_prompt, user_prompt = result
    assert isinstance(system_prompt, str)
    assert isinstance(user_prompt, str)
    # System prompt contains analytical framework keywords
    assert "Kill Chain" in system_prompt
    assert "Dead Branch Pruning" in system_prompt
    assert "Prerequisite Verification" in system_prompt


async def test_orient_build_prompt_includes_mission_steps(seeded_db):
    """User prompt includes mission task tree when mission_steps exist."""
    await seeded_db.execute(
        "INSERT INTO mission_steps "
        "(id, operation_id, step_number, technique_id, technique_name, "
        "target_id, target_label, engine, status) "
        "VALUES ('ms-1', 'test-op-1', 1, 'T1003.001', 'LSASS Memory', "
        "'test-target-1', 'DC-01', 'caldera', 'completed')"
    )
    await seeded_db.commit()

    seeded_db.row_factory = aiosqlite.Row
    ws = _make_ws()
    orient = OrientEngine(ws)
    _, user_prompt = await orient._build_prompt(seeded_db, "test-op-1", "Test summary")
    assert "LSASS Memory" in user_prompt
    assert "MISSION TASK TREE" in user_prompt


async def test_orient_build_prompt_includes_ooda_history(seeded_db):
    """User prompt includes OODA history when iterations exist."""
    await seeded_db.execute(
        "INSERT INTO ooda_iterations "
        "(id, operation_id, iteration_number, phase, observe_summary, act_summary) "
        "VALUES ('iter-1', 'test-op-1', 1, 'act', 'Scanned network', 'Ran T1046')"
    )
    await seeded_db.execute(
        "INSERT INTO ooda_iterations "
        "(id, operation_id, iteration_number, phase, observe_summary, act_summary) "
        "VALUES ('iter-2', 'test-op-1', 2, 'act', 'Found open SMB', 'Ran T1021.002')"
    )
    await seeded_db.commit()

    seeded_db.row_factory = aiosqlite.Row
    ws = _make_ws()
    orient = OrientEngine(ws)
    _, user_prompt = await orient._build_prompt(seeded_db, "test-op-1", "Test summary")
    assert "OPERATIONAL HISTORY" in user_prompt
    assert "Scanned network" in user_prompt
    assert "Cycle #" in user_prompt


async def test_orient_build_prompt_categorized_facts(seeded_db):
    """User prompt includes categorized intelligence when facts exist."""
    await seeded_db.execute(
        "INSERT INTO facts (id, trait, value, category, operation_id) "
        "VALUES ('fact-1', 'credential.ntlm', 'aad3b435b51404ee', 'credential', 'test-op-1')"
    )
    await seeded_db.commit()

    seeded_db.row_factory = aiosqlite.Row
    ws = _make_ws()
    orient = OrientEngine(ws)
    _, user_prompt = await orient._build_prompt(seeded_db, "test-op-1", "Test summary")
    assert "CREDENTIAL INTELLIGENCE" in user_prompt
    assert "credential.ntlm" in user_prompt


async def test_orient_call_claude_sends_system_param(seeded_db):
    """_call_claude() sends system parameter in API payload."""
    ws = _make_ws()
    orient = OrientEngine(ws)

    captured_payload = {}

    async def mock_post(url, headers=None, json=None):
        captured_payload.update(json or {})
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json = MagicMock(return_value={
            "content": [{"text": '{"test": true}'}]
        })
        return mock_resp

    with patch("app.services.orient_engine.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post = mock_post
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        await orient._call_claude("Test system prompt", "Test user prompt")

    assert "system" in captured_payload
    assert captured_payload["system"] == "Test system prompt"
    assert captured_payload["messages"] == [{"role": "user", "content": "Test user prompt"}]


# ===================================================================
# FactCollector (3 tests)
# ===================================================================


async def test_fact_collect_empty_when_no_executions(seeded_db):
    """No executions → empty facts list."""
    ws = _make_ws()
    collector = FactCollector(ws)
    facts = await collector.collect(seeded_db, "test-op-1")
    assert facts == []


async def test_fact_collect_from_execution(seeded_db):
    """Extract facts from a successful technique execution."""
    # Insert a successful execution with result
    await seeded_db.execute(
        "INSERT INTO technique_executions "
        "(id, technique_id, target_id, operation_id, engine, status, "
        "result_summary, started_at, completed_at) "
        "VALUES ('exec-1', 'T1003.001', 'test-target-1', 'test-op-1', "
        "'caldera', 'success', 'Extracted 5 NTLM hashes from LSASS', "
        "datetime('now'), datetime('now'))"
    )
    await seeded_db.commit()

    ws = _make_ws()
    collector = FactCollector(ws)
    facts = await collector.collect(seeded_db, "test-op-1")
    assert len(facts) >= 1
    assert facts[0]["category"] == "credential"  # T1003 → credential


async def test_fact_summarize_empty(seeded_db):
    """Summarize with no facts → 'No intelligence collected yet.'"""
    ws = _make_ws()
    collector = FactCollector(ws)
    summary = await collector.summarize(seeded_db, "test-op-1")
    assert "No intelligence" in summary


# ===================================================================
# C5ISRMapper (4 tests)
# ===================================================================


async def test_c5isr_health_to_status_operational():
    """health >= 95 → OPERATIONAL."""
    assert C5ISRMapper._health_to_status(100.0) == C5ISRDomainStatus.OPERATIONAL
    assert C5ISRMapper._health_to_status(95.0) == C5ISRDomainStatus.OPERATIONAL


async def test_c5isr_health_to_status_degraded():
    """health 30-49 → DEGRADED."""
    assert C5ISRMapper._health_to_status(30.0) == C5ISRDomainStatus.DEGRADED
    assert C5ISRMapper._health_to_status(49.9) == C5ISRDomainStatus.DEGRADED


async def test_c5isr_health_to_status_critical():
    """health < 1 → CRITICAL; health >= 1 → OFFLINE."""
    assert C5ISRMapper._health_to_status(0.0) == C5ISRDomainStatus.CRITICAL
    assert C5ISRMapper._health_to_status(0.5) == C5ISRDomainStatus.CRITICAL
    assert C5ISRMapper._health_to_status(1.0) == C5ISRDomainStatus.OFFLINE


async def test_c5isr_update_creates_six_domains(seeded_db):
    """update() → produces 6 C5ISR domain records."""
    ws = _make_ws()
    mapper = C5ISRMapper(ws)
    results = await mapper.update(seeded_db, "test-op-1")
    assert len(results) == 6
    domains = {r["domain"] for r in results}
    assert domains == {"command", "control", "comms", "computers", "cyber", "isr"}


# ===================================================================
# OODAController (3 tests)
# ===================================================================


async def test_ooda_trigger_cycle_mock_mode(seeded_db):
    """trigger_cycle → completes full OODA iteration (observe→act)."""
    ws = _make_ws()
    fact_collector = FactCollector(ws)
    orient_engine = OrientEngine(ws)
    decision_engine = DecisionEngine()

    # Mock caldera client
    mock_caldera = MagicMock()
    mock_caldera.execute = AsyncMock(return_value=ExecutionResult(
        success=True,
        execution_id="mock-exec-1",
        output="Mock execution complete",
        facts=[{"trait": "credential.hash", "value": "aad3b435b51404ee"}],
        error=None,
    ))

    engine_router = EngineRouter(mock_caldera, None, fact_collector, ws)
    c5isr_mapper = C5ISRMapper(ws)
    controller = OODAController(
        fact_collector, orient_engine, decision_engine,
        engine_router, c5isr_mapper, ws,
    )

    result = await controller.trigger_cycle(seeded_db, "test-op-1")
    assert result["operation_id"] == "test-op-1"
    assert result["iteration_number"] == 1


async def test_ooda_trigger_creates_iteration_record(seeded_db):
    """DB should contain ooda_iterations record after trigger."""
    ws = _make_ws()
    fact_collector = FactCollector(ws)
    orient_engine = OrientEngine(ws)
    decision_engine = DecisionEngine()

    mock_caldera = MagicMock()
    mock_caldera.execute = AsyncMock(return_value=ExecutionResult(
        success=True, execution_id="mock-exec-2",
        output="Complete", facts=[], error=None,
    ))

    engine_router = EngineRouter(mock_caldera, None, fact_collector, ws)
    c5isr_mapper = C5ISRMapper(ws)
    controller = OODAController(
        fact_collector, orient_engine, decision_engine,
        engine_router, c5isr_mapper, ws,
    )

    await controller.trigger_cycle(seeded_db, "test-op-1")

    seeded_db.row_factory = aiosqlite.Row
    cursor = await seeded_db.execute(
        "SELECT * FROM ooda_iterations WHERE operation_id = 'test-op-1'"
    )
    rows = await cursor.fetchall()
    assert len(rows) >= 1
    assert rows[0]["observe_summary"] is not None


async def test_ooda_trigger_updates_operation_phase(seeded_db):
    """operation.current_ooda_phase should be updated after trigger_cycle."""
    ws = _make_ws()
    fact_collector = FactCollector(ws)
    orient_engine = OrientEngine(ws)
    decision_engine = DecisionEngine()

    mock_caldera = MagicMock()
    mock_caldera.execute = AsyncMock(return_value=ExecutionResult(
        success=True, execution_id="mock-exec-3",
        output="Complete", facts=[], error=None,
    ))

    engine_router = EngineRouter(mock_caldera, None, fact_collector, ws)
    c5isr_mapper = C5ISRMapper(ws)
    controller = OODAController(
        fact_collector, orient_engine, decision_engine,
        engine_router, c5isr_mapper, ws,
    )

    await controller.trigger_cycle(seeded_db, "test-op-1")

    seeded_db.row_factory = aiosqlite.Row
    cursor = await seeded_db.execute(
        "SELECT current_ooda_phase, ooda_iteration_count FROM operations WHERE id = 'test-op-1'"
    )
    op = await cursor.fetchone()
    # Phase should have progressed (act is the final phase)
    assert op["current_ooda_phase"] == "act"
    assert op["ooda_iteration_count"] == 1
