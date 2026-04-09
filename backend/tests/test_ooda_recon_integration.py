# Copyright 2026 Athena Contributors
# SPEC-052: OODA-Native Recon and Initial Access — TDD tests (recon integration)
# Tests written BEFORE implementation per ASP TDD protocol.

"""Tests for OODA-native recon integration (SPEC-052).

Validates:
1. Target creation auto-triggers OODA cycle
2. Observe phase auto-recon for zero-fact targets
3. Noise budget enforcement for auto-recon
4. Mission profile-aware fact thresholds
5. No iterationNumber === 0 sentinel records
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_ws() -> MagicMock:
    ws = MagicMock()
    ws.broadcast = AsyncMock()
    ws.send_personal = AsyncMock()
    return ws


def _make_recon_result(services: int = 3) -> MagicMock:
    """Create a mock ReconResult with N services."""
    result = MagicMock()
    result.services = [MagicMock() for _ in range(services)]
    return result


# ---------------------------------------------------------------------------
# Test 1: Target creation auto-triggers OODA
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_target_creation_auto_triggers_ooda(client):
    """POST /operations/{op}/targets should schedule auto_trigger_ooda."""

    with patch("app.routers.targets.auto_trigger_ooda", new_callable=AsyncMock) as mock_trigger:
        resp = await client.post(
            "/operations/test-op-1/targets",
            json={
                "hostname": "WEB-01",
                "ip_address": "10.0.1.20",
                "os": "Ubuntu 22.04",
                "role": "web-server",
            },
        )
        assert resp.status_code == 201

        # auto_trigger_ooda should have been called (possibly via asyncio.create_task)
        # We patch at the import site in the router module
        mock_trigger.assert_called_once()
        call_args = mock_trigger.call_args
        assert call_args[0][0] == "test-op-1"  # operation_id
        assert "target.added" in call_args[1].get("reason", call_args[0][1] if len(call_args[0]) > 1 else "")


# ---------------------------------------------------------------------------
# Test 2: Observe phase auto-recon for zero-fact targets
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_observe_auto_recon_zero_facts(seeded_db):
    """OODA Observe phase should auto-scan targets with 0 facts."""

    from app.services.c5isr_mapper import C5ISRMapper
    from app.services.decision_engine import DecisionEngine
    from app.services.engine_router import EngineRouter
    from app.services.fact_collector import FactCollector
    from app.services.ooda_controller import OODAController
    from app.services.orient_engine import OrientEngine

    ws = _make_ws()

    # Create a new target with zero facts
    await seeded_db.execute(
        "INSERT INTO targets (id, hostname, ip_address, os, role, operation_id, is_active) "
        "VALUES ('target-zero-facts', 'ZERO-01', '10.0.1.99', 'Linux', 'test', 'test-op-1', TRUE)"
    )

    # Verify it has 0 facts
    fact_count = await seeded_db.fetchval(
        "SELECT COUNT(*) FROM facts WHERE source_target_id = 'target-zero-facts'"
    )
    assert fact_count == 0

    # Mock ReconEngine to verify it gets called
    mock_recon_result = _make_recon_result(services=5)
    with patch("app.services.ooda_controller.ReconEngine") as MockReconClass:
        mock_recon = MagicMock()
        mock_recon.scan = AsyncMock(return_value=mock_recon_result)
        MockReconClass.return_value = mock_recon

        # Build controller with mocked services
        fc = FactCollector(ws)
        orient = OrientEngine(ws)
        decision = DecisionEngine()
        c2_mock = MagicMock()
        c2_mock.execute = AsyncMock()
        router = EngineRouter(c2_mock, fc, ws)
        c5isr = C5ISRMapper(ws)
        controller = OODAController(fc, orient, decision, router, c5isr, ws)

        # Trigger one OODA cycle
        await controller.trigger_cycle(seeded_db, "test-op-1")

        # ReconEngine.scan() should have been called for the zero-fact target
        mock_recon.scan.assert_called()
        # Verify scan was called with the zero-fact target
        scan_calls = mock_recon.scan.call_args_list
        target_ids_scanned = [
            call.args[2] if len(call.args) > 2 else call.kwargs.get("target_id")
            for call in scan_calls
        ]
        assert "target-zero-facts" in target_ids_scanned


# ---------------------------------------------------------------------------
# Test 3: Auto-recon respects noise budget
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_observe_auto_recon_respects_noise_budget(seeded_db):
    """SR mode with insufficient noise budget should skip auto-recon."""

    from app.services.c5isr_mapper import C5ISRMapper
    from app.services.decision_engine import DecisionEngine
    from app.services.engine_router import EngineRouter
    from app.services.fact_collector import FactCollector
    from app.services.ooda_controller import OODAController
    from app.services.orient_engine import OrientEngine

    ws = _make_ws()

    # Set operation to SR mode (strictest noise budget)
    await seeded_db.execute(
        "UPDATE operations SET mission_profile = 'SR' WHERE id = 'test-op-1'"
    )

    # Create target with 0 facts
    await seeded_db.execute(
        "INSERT INTO targets (id, hostname, ip_address, os, role, operation_id, is_active) "
        "VALUES ('target-sr-nobudget', 'SR-01', '10.0.1.98', 'Linux', 'test', 'test-op-1', TRUE)"
    )

    # Mock constraint engine to return exhausted noise budget
    mock_constraints = MagicMock()
    mock_constraints.noise_budget_remaining = 0  # No budget left
    mock_constraints.warnings = []
    mock_constraints.hard_limits = []
    mock_constraints.blocked_targets = []
    mock_constraints.forced_mode = None
    mock_constraints.orient_max_options = 3
    mock_constraints.min_confidence_override = None
    mock_constraints.max_parallel_override = None
    mock_constraints.active_overrides = []

    with patch("app.services.ooda_controller.ReconEngine") as MockReconClass, \
         patch("app.services.constraint_engine.evaluate", new_callable=AsyncMock, return_value=mock_constraints):
        mock_recon = MagicMock()
        mock_recon.scan = AsyncMock(return_value=_make_recon_result())
        MockReconClass.return_value = mock_recon

        fc = FactCollector(ws)
        orient = OrientEngine(ws)
        decision = DecisionEngine()
        c2_mock = MagicMock()
        c2_mock.execute = AsyncMock()
        router = EngineRouter(c2_mock, fc, ws)
        c5isr = C5ISRMapper(ws)
        controller = OODAController(fc, orient, decision, router, c5isr, ws)

        await controller.trigger_cycle(seeded_db, "test-op-1")

        # With noise budget exhausted, auto-recon should NOT be called
        # (This test will fail until implementation adds noise budget check)
        mock_recon.scan.assert_not_called()


# ---------------------------------------------------------------------------
# Test 4: Mission profile-aware fact thresholds
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@pytest.mark.parametrize("profile,threshold", [
    ("SR", 0),   # SR: only scan if literally 0 facts
    ("CO", 2),   # CO: scan if < 2 facts
    ("SP", 3),   # SP: scan if < 3 facts (current default)
    ("FA", 5),   # FA: scan if < 5 facts
])
async def test_observe_auto_recon_mission_profile_threshold(seeded_db, profile, threshold):
    """Auto-recon threshold should vary by mission profile."""

    from app.services.c5isr_mapper import C5ISRMapper
    from app.services.decision_engine import DecisionEngine
    from app.services.engine_router import EngineRouter
    from app.services.fact_collector import FactCollector
    from app.services.ooda_controller import OODAController
    from app.services.orient_engine import OrientEngine

    ws = _make_ws()

    # Set mission profile
    await seeded_db.execute(
        "UPDATE operations SET mission_profile = $1 WHERE id = 'test-op-1'",
        profile,
    )

    # Create target with exactly `threshold` facts (should NOT trigger scan)
    target_id = f"target-{profile}-threshold"
    await seeded_db.execute(
        "INSERT INTO targets (id, hostname, ip_address, os, role, operation_id, is_active) "
        "VALUES ($1, $2, $3, 'Linux', 'test', 'test-op-1', TRUE)",
        target_id, f"{profile}-01", f"10.0.{ord(profile[0])}.1",
    )

    # Insert exactly `threshold` facts for this target
    for i in range(threshold):
        await seeded_db.execute(
            "INSERT INTO facts (id, trait, value, category, operation_id, source_target_id) "
            "VALUES ($1, $2, $3, 'service', 'test-op-1', $4)",
            f"fact-{profile}-{i}", f"service.port.{i}", str(8000 + i), target_id,
        )

    with patch("app.services.ooda_controller.ReconEngine") as MockReconClass:
        mock_recon = MagicMock()
        mock_recon.scan = AsyncMock(return_value=_make_recon_result())
        MockReconClass.return_value = mock_recon

        fc = FactCollector(ws)
        orient = OrientEngine(ws)
        decision = DecisionEngine()
        c2_mock = MagicMock()
        c2_mock.execute = AsyncMock()
        router = EngineRouter(c2_mock, fc, ws)
        c5isr = C5ISRMapper(ws)
        controller = OODAController(fc, orient, decision, router, c5isr, ws)

        await controller.trigger_cycle(seeded_db, "test-op-1")

        # Target has exactly `threshold` facts → should NOT trigger scan
        # (This validates the profile-specific threshold is applied)
        scan_calls = mock_recon.scan.call_args_list
        target_ids_scanned = [
            call.args[2] if len(call.args) > 2 else call.kwargs.get("target_id", "")
            for call in scan_calls
        ]
        assert target_id not in target_ids_scanned, \
            f"{profile} profile: target with {threshold} facts should NOT be scanned"


# ---------------------------------------------------------------------------
# Test 5: No iterationNumber === 0 sentinel records
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_no_iteration_zero_sentinel(seeded_db):
    """After OODA cycle with auto-recon, no iteration_number=0 records should exist."""

    from app.services.c5isr_mapper import C5ISRMapper
    from app.services.decision_engine import DecisionEngine
    from app.services.engine_router import EngineRouter
    from app.services.fact_collector import FactCollector
    from app.services.ooda_controller import OODAController
    from app.services.orient_engine import OrientEngine

    ws = _make_ws()

    with patch("app.services.ooda_controller.ReconEngine") as MockReconClass:
        mock_recon = MagicMock()
        mock_recon.scan = AsyncMock(return_value=_make_recon_result())
        MockReconClass.return_value = mock_recon

        fc = FactCollector(ws)
        orient = OrientEngine(ws)
        decision = DecisionEngine()
        c2_mock = MagicMock()
        c2_mock.execute = AsyncMock()
        router = EngineRouter(c2_mock, fc, ws)
        c5isr = C5ISRMapper(ws)
        controller = OODAController(fc, orient, decision, router, c5isr, ws)

        # Run a full OODA cycle
        await controller.trigger_cycle(seeded_db, "test-op-1")

    # Verify no sentinel records
    sentinel_count = await seeded_db.fetchval(
        "SELECT COUNT(*) FROM ooda_iterations "
        "WHERE operation_id = 'test-op-1' AND iteration_number = 0"
    )
    assert sentinel_count == 0, "No iterationNumber=0 sentinel records should exist"

    # Verify normal iterations start at 1
    min_iter = await seeded_db.fetchval(
        "SELECT MIN(iteration_number) FROM ooda_iterations "
        "WHERE operation_id = 'test-op-1'"
    )
    assert min_iter is None or min_iter >= 1
