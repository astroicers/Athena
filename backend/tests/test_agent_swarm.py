# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: azz093093.830330@gmail.com

"""Unit tests for AgentSwarm — SPEC-030 bounded-parallel task executor."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio


# ---------------------------------------------------------------------------
# Helper: seed the minimal rows that swarm_tasks FK references need.
# ---------------------------------------------------------------------------

async def _seed_swarm_rows(db) -> None:
    """Insert op-1, tgt-1, ooda-1 so swarm_tasks FK constraints pass."""
    await db.execute(
        "INSERT INTO operations (id, code, name, codename, strategic_intent) "
        "VALUES ('op-1', 'OP-1', 'SwarmTest', 'SWARM', 'test') "
        "ON CONFLICT DO NOTHING"
    )
    for i in range(5):
        tgt_id = f"tgt-{i}"
        await db.execute(
            "INSERT INTO targets (id, hostname, ip_address, role, operation_id) "
            f"VALUES ('{tgt_id}', 'swarm-{tgt_id}', '10.0.0.{i}', 'target', 'op-1') "
            "ON CONFLICT DO NOTHING"
        )
    await db.execute(
        "INSERT INTO ooda_iterations (id, operation_id, iteration_number) "
        "VALUES ('ooda-1', 'op-1', 1) "
        "ON CONFLICT DO NOTHING"
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_ws():
    """Return a mock WebSocketManager."""
    ws = MagicMock()
    ws.broadcast = AsyncMock()
    return ws


def _make_mock_router(side_effect=None, return_value=None):
    """Return a mock EngineRouter."""
    router = MagicMock()
    if side_effect is not None:
        router.execute = AsyncMock(side_effect=side_effect)
    elif return_value is not None:
        router.execute = AsyncMock(return_value=return_value)
    else:
        router.execute = AsyncMock(return_value={"status": "success"})
    return router


# ---------------------------------------------------------------------------
# SwarmResult property tests
# ---------------------------------------------------------------------------

class TestSwarmResultProperties:
    """Test SwarmResult dataclass properties."""

    def test_all_failed_when_none_completed(self):
        from app.services.agent_swarm import SwarmResult
        r = SwarmResult(ooda_iteration_id="ooda-1", total=3, completed=0, failed=3)
        assert r.all_failed is True

    def test_all_failed_false_when_some_completed(self):
        from app.services.agent_swarm import SwarmResult
        r = SwarmResult(ooda_iteration_id="ooda-1", total=3, completed=1, failed=2)
        assert r.all_failed is False

    def test_all_failed_false_when_total_is_zero(self):
        from app.services.agent_swarm import SwarmResult
        r = SwarmResult(ooda_iteration_id="ooda-1", total=0, completed=0)
        assert r.all_failed is False

    def test_partial_success_when_some_completed(self):
        from app.services.agent_swarm import SwarmResult
        r = SwarmResult(ooda_iteration_id="ooda-1", total=3, completed=2, failed=1)
        assert r.partial_success is True

    def test_partial_success_false_when_all_completed(self):
        from app.services.agent_swarm import SwarmResult
        r = SwarmResult(ooda_iteration_id="ooda-1", total=3, completed=3)
        assert r.partial_success is False

    def test_partial_success_false_when_none_completed(self):
        from app.services.agent_swarm import SwarmResult
        r = SwarmResult(ooda_iteration_id="ooda-1", total=3, completed=0, failed=3)
        assert r.partial_success is False

    def test_act_summary_format(self):
        from app.services.agent_swarm import SwarmResult
        r = SwarmResult(
            ooda_iteration_id="ooda-1", total=5, completed=3, failed=1, timed_out=1
        )
        expected = "Swarm: 3/5 succeeded, 1 failed, 1 timed out"
        assert r.act_summary == expected


# ---------------------------------------------------------------------------
# SwarmExecutor tests
# ---------------------------------------------------------------------------

class TestSwarmExecutorEmptyTasks:
    """Test empty parallel_tasks list."""

    async def test_empty_parallel_tasks(self, pg_pool):
        from app.services.agent_swarm import SwarmExecutor

        ws = _make_mock_ws()
        router = _make_mock_router()
        executor = SwarmExecutor(engine_router=router, ws_manager=ws)

        result = await executor.execute_swarm(
            pg_pool, "op-1", "ooda-1", []
        )
        assert result.total == 0
        assert result.completed == 0
        assert result.failed == 0
        assert result.timed_out == 0
        assert result.tasks == []


class TestSwarmExecutorSingleTask:
    """Test single task execution."""

    async def test_single_task_executes(self, pg_pool, tmp_db):
        await _seed_swarm_rows(tmp_db)
        from app.services.agent_swarm import SwarmExecutor

        ws = _make_mock_ws()
        router = _make_mock_router(return_value={"status": "success"})

        with patch("app.services.agent_swarm.settings") as mock_settings:
            mock_settings.MAX_PARALLEL_TASKS = 5
            mock_settings.PARALLEL_TASK_TIMEOUT_SEC = 120

            executor = SwarmExecutor(engine_router=router, ws_manager=ws)

            tasks = [
                {
                    "technique_id": "T1059.004",
                    "target_id": "tgt-1",
                    "engine": "ssh",
                }
            ]
            result = await executor.execute_swarm(pg_pool, "op-1", "ooda-1", tasks)
            assert result.total == 1
            assert result.completed == 1
            assert result.failed == 0
            assert len(result.tasks) == 1
            assert result.tasks[0].status == "completed"
            router.execute.assert_awaited_once()


class TestSwarmExecutorMultipleTasks:
    """Test multiple parallel task execution."""

    async def test_multiple_tasks_parallel(self, pg_pool, tmp_db):
        await _seed_swarm_rows(tmp_db)
        from app.services.agent_swarm import SwarmExecutor

        ws = _make_mock_ws()
        router = _make_mock_router(return_value={"status": "success"})

        with patch("app.services.agent_swarm.settings") as mock_settings:
            mock_settings.MAX_PARALLEL_TASKS = 5
            mock_settings.PARALLEL_TASK_TIMEOUT_SEC = 120

            executor = SwarmExecutor(engine_router=router, ws_manager=ws)

            tasks = [
                {"technique_id": "T1059.004", "target_id": "tgt-1", "engine": "ssh"},
                {"technique_id": "T1087", "target_id": "tgt-2", "engine": "ssh"},
                {"technique_id": "T1083", "target_id": "tgt-3", "engine": "ssh"},
            ]
            result = await executor.execute_swarm(pg_pool, "op-1", "ooda-1", tasks)
            assert result.total == 3
            assert result.completed == 3
            assert result.failed == 0
            assert len(result.tasks) == 3
            assert router.execute.await_count == 3


class TestSwarmExecutorSemaphore:
    """Test semaphore bounds concurrency."""

    async def test_semaphore_bounds_concurrency(self, pg_pool, tmp_db):
        await _seed_swarm_rows(tmp_db)
        from app.services.agent_swarm import SwarmExecutor

        ws = _make_mock_ws()
        max_concurrent = 0
        current_concurrent = 0
        lock = asyncio.Lock()

        async def _counting_execute(*args, **kwargs):
            nonlocal max_concurrent, current_concurrent
            async with lock:
                current_concurrent += 1
                if current_concurrent > max_concurrent:
                    max_concurrent = current_concurrent
            await asyncio.sleep(0.05)  # simulate work
            async with lock:
                current_concurrent -= 1
            return {"status": "success"}

        router = MagicMock()
        router.execute = AsyncMock(side_effect=_counting_execute)

        with patch("app.services.agent_swarm.settings") as mock_settings:
            mock_settings.MAX_PARALLEL_TASKS = 2
            mock_settings.PARALLEL_TASK_TIMEOUT_SEC = 120

            executor = SwarmExecutor(engine_router=router, ws_manager=ws)

            tasks = [
                {"technique_id": f"T{i}", "target_id": f"tgt-{i}", "engine": "ssh"}
                for i in range(4)
            ]
            result = await executor.execute_swarm(pg_pool, "op-1", "ooda-1", tasks)
            assert result.total == 4
            assert result.completed == 4
            # The semaphore should limit concurrency to 2
            assert max_concurrent <= 2


class TestSwarmExecutorTimeoutIsolation:
    """Test that one task timing out does not affect others."""

    async def test_task_timeout_isolation(self, pg_pool, tmp_db):
        await _seed_swarm_rows(tmp_db)
        from app.services.agent_swarm import SwarmExecutor

        ws = _make_mock_ws()
        call_count = 0

        async def _mixed_execute(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            technique_id = kwargs.get("technique_id", "")
            if technique_id == "T_TIMEOUT":
                await asyncio.sleep(10)  # will timeout
                return {"status": "success"}
            return {"status": "success"}

        router = MagicMock()
        router.execute = AsyncMock(side_effect=_mixed_execute)

        with patch("app.services.agent_swarm.settings") as mock_settings:
            mock_settings.MAX_PARALLEL_TASKS = 5
            mock_settings.PARALLEL_TASK_TIMEOUT_SEC = 1  # 1 second timeout

            executor = SwarmExecutor(engine_router=router, ws_manager=ws)

            tasks = [
                {"technique_id": "T_OK1", "target_id": "tgt-1", "engine": "ssh"},
                {"technique_id": "T_TIMEOUT", "target_id": "tgt-2", "engine": "ssh"},
                {"technique_id": "T_OK2", "target_id": "tgt-3", "engine": "ssh"},
            ]
            result = await executor.execute_swarm(pg_pool, "op-1", "ooda-1", tasks)
            assert result.total == 3
            assert result.completed == 2
            assert result.timed_out == 1

            # Find the timed-out task
            timeout_tasks = [t for t in result.tasks if t.status == "timeout"]
            assert len(timeout_tasks) == 1
            assert timeout_tasks[0].technique_id == "T_TIMEOUT"


class TestSwarmExecutorExceptionIsolation:
    """Test that one task raising an exception does not affect others."""

    async def test_task_exception_isolation(self, pg_pool, tmp_db):
        await _seed_swarm_rows(tmp_db)
        from app.services.agent_swarm import SwarmExecutor

        ws = _make_mock_ws()

        async def _mixed_execute(*args, **kwargs):
            technique_id = kwargs.get("technique_id", "")
            if technique_id == "T_FAIL":
                raise RuntimeError("Simulated engine failure")
            return {"status": "success"}

        router = MagicMock()
        router.execute = AsyncMock(side_effect=_mixed_execute)

        with patch("app.services.agent_swarm.settings") as mock_settings:
            mock_settings.MAX_PARALLEL_TASKS = 5
            mock_settings.PARALLEL_TASK_TIMEOUT_SEC = 120

            executor = SwarmExecutor(engine_router=router, ws_manager=ws)

            tasks = [
                {"technique_id": "T_OK1", "target_id": "tgt-1", "engine": "ssh"},
                {"technique_id": "T_FAIL", "target_id": "tgt-2", "engine": "ssh"},
                {"technique_id": "T_OK2", "target_id": "tgt-3", "engine": "ssh"},
            ]
            result = await executor.execute_swarm(pg_pool, "op-1", "ooda-1", tasks)
            assert result.total == 3
            assert result.completed == 2
            assert result.failed == 1

            # Find the failed task
            failed_tasks = [t for t in result.tasks if t.status == "failed"]
            assert len(failed_tasks) == 1
            assert "RuntimeError" in failed_tasks[0].error


class TestSwarmExecutorAllFail:
    """Test all tasks failing."""

    async def test_all_tasks_fail(self, pg_pool, tmp_db):
        await _seed_swarm_rows(tmp_db)
        from app.services.agent_swarm import SwarmExecutor

        ws = _make_mock_ws()
        router = _make_mock_router(return_value={"status": "failed", "error": "nope"})

        with patch("app.services.agent_swarm.settings") as mock_settings:
            mock_settings.MAX_PARALLEL_TASKS = 5
            mock_settings.PARALLEL_TASK_TIMEOUT_SEC = 120

            executor = SwarmExecutor(engine_router=router, ws_manager=ws)

            tasks = [
                {"technique_id": "T1", "target_id": "tgt-1", "engine": "ssh"},
                {"technique_id": "T2", "target_id": "tgt-2", "engine": "ssh"},
                {"technique_id": "T3", "target_id": "tgt-3", "engine": "ssh"},
            ]
            result = await executor.execute_swarm(pg_pool, "op-1", "ooda-1", tasks)
            assert result.total == 3
            assert result.completed == 0
            assert result.failed == 3
            assert result.all_failed is True


class TestSwarmExecutorPartialSuccess:
    """Test partial success."""

    async def test_partial_success(self, pg_pool, tmp_db):
        await _seed_swarm_rows(tmp_db)
        from app.services.agent_swarm import SwarmExecutor

        ws = _make_mock_ws()
        call_idx = 0

        async def _alternating_execute(*args, **kwargs):
            nonlocal call_idx
            call_idx += 1
            if call_idx == 2:
                return {"status": "failed", "error": "oops"}
            return {"status": "success"}

        router = MagicMock()
        router.execute = AsyncMock(side_effect=_alternating_execute)

        with patch("app.services.agent_swarm.settings") as mock_settings:
            mock_settings.MAX_PARALLEL_TASKS = 5
            mock_settings.PARALLEL_TASK_TIMEOUT_SEC = 120

            executor = SwarmExecutor(engine_router=router, ws_manager=ws)

            tasks = [
                {"technique_id": "T1", "target_id": "tgt-1", "engine": "ssh"},
                {"technique_id": "T2", "target_id": "tgt-2", "engine": "ssh"},
                {"technique_id": "T3", "target_id": "tgt-3", "engine": "ssh"},
            ]
            result = await executor.execute_swarm(pg_pool, "op-1", "ooda-1", tasks)
            assert result.total == 3
            assert result.completed == 2
            assert result.failed == 1
            assert result.partial_success is True


class TestSwarmExecutorDBPersistence:
    """Test that task records are persisted to the database."""

    async def test_db_records_created(self, pg_pool, tmp_db):
        await _seed_swarm_rows(tmp_db)
        from app.services.agent_swarm import SwarmExecutor

        ws = _make_mock_ws()
        router = _make_mock_router(return_value={"status": "success"})

        with patch("app.services.agent_swarm.settings") as mock_settings:
            mock_settings.MAX_PARALLEL_TASKS = 5
            mock_settings.PARALLEL_TASK_TIMEOUT_SEC = 120

            executor = SwarmExecutor(engine_router=router, ws_manager=ws)

            tasks = [
                {"technique_id": "T1", "target_id": "tgt-1", "engine": "ssh"},
                {"technique_id": "T2", "target_id": "tgt-2", "engine": "ssh"},
            ]
            # pg_pool used so each parallel task gets its own connection
            result = await executor.execute_swarm(pg_pool, "op-1", "ooda-1", tasks)

            # Verify via tmp_db (same underlying test database, tables already truncated)
            count = await tmp_db.fetchval(
                "SELECT COUNT(*) FROM swarm_tasks WHERE ooda_iteration_id = 'ooda-1'"
            )
            assert count == 2

            # Check records have completed status
            rows = await tmp_db.fetch(
                "SELECT status FROM swarm_tasks WHERE ooda_iteration_id = 'ooda-1'"
            )
            for r in rows:
                assert r["status"] == "completed"


# ---------------------------------------------------------------------------
# DecisionEngine parallel_tasks tests
# ---------------------------------------------------------------------------

class TestDecisionEngineParallelTasks:
    """Test that DecisionEngine.evaluate() produces parallel_tasks."""

    async def _setup_db(self, db):
        """Setup DB with operation, targets, and completed Kill Chain stages.

        SPEC-040: Composite confidence includes Kill Chain penalty.  Seed
        prior-stage execution data so the penalty does not push confidence
        below the 0.5 gate for these parallel-task tests.
        """
        await db.execute(
            "INSERT INTO operations (id, code, name, codename, strategic_intent, "
            "automation_mode, risk_threshold) "
            "VALUES ('op-1', 'OP-1', 'Test', 'TEST', 'test intent', 'semi_auto', 'medium')"
        )
        await db.execute(
            "INSERT INTO targets (id, hostname, ip_address, os, role, operation_id, is_active) "
            "VALUES ('tgt-1', 'host1', '10.0.0.1', 'Linux', 'server', 'op-1', TRUE)"
        )
        # Seed completed Kill Chain stages (TA0043 Recon, TA0001 Initial Access)
        await db.execute(
            "INSERT INTO attack_graph_nodes (id, operation_id, target_id, technique_id, tactic_id, status, confidence) "
            "VALUES ('agn-1', 'op-1', 'tgt-1', 'T1595.001', 'TA0043', 'explored', 0.9), "
            "       ('agn-2', 'op-1', 'tgt-1', 'T1190', 'TA0001', 'explored', 0.8)"
        )
        await db.execute(
            "INSERT INTO technique_executions (id, technique_id, target_id, operation_id, engine, status, started_at, completed_at) "
            "VALUES ('te-1', 'T1595.001', 'tgt-1', 'op-1', 'mcp_ssh', 'success', NOW(), NOW()), "
            "       ('te-2', 'T1190', 'tgt-1', 'op-1', 'mcp_ssh', 'success', NOW(), NOW())"
        )

    async def test_evaluate_produces_parallel_tasks(self, tmp_db):
        from app.services.decision_engine import DecisionEngine

        await self._setup_db(tmp_db)

        engine = DecisionEngine()
        recommendation = {
            "recommended_technique_id": "T1059.004",
            "confidence": 0.8,
            "options": [
                {
                    "technique_id": "T1059.004",
                    "risk_level": "low",
                    "recommended_engine": "ssh",
                    "target_id": "tgt-1",
                },
                {
                    "technique_id": "T1087",
                    "risk_level": "low",
                    "recommended_engine": "ssh",
                    "target_id": "tgt-1",
                },
            ],
        }
        result = await engine.evaluate(tmp_db, "op-1", recommendation)
        assert "parallel_tasks" in result
        assert len(result["parallel_tasks"]) == 2
        assert result["parallel_tasks"][0]["technique_id"] == "T1059.004"
        assert result["parallel_tasks"][1]["technique_id"] == "T1087"

    async def test_manual_mode_no_parallel_tasks(self, tmp_db):
        from app.services.decision_engine import DecisionEngine

        await tmp_db.execute(
            "INSERT INTO operations (id, code, name, codename, strategic_intent, "
            "automation_mode, risk_threshold) "
            "VALUES ('op-m', 'OP-M', 'Manual', 'MANUAL', 'test', 'manual', 'medium')"
        )
        await tmp_db.execute(
            "INSERT INTO targets (id, hostname, ip_address, os, role, operation_id) "
            "VALUES ('tgt-m', 'host-m', '10.0.0.2', 'Linux', 'server', 'op-m')"
        )

        engine = DecisionEngine()
        recommendation = {
            "recommended_technique_id": "T1059.004",
            "confidence": 0.8,
            "options": [
                {
                    "technique_id": "T1059.004",
                    "risk_level": "low",
                    "recommended_engine": "ssh",
                    "target_id": "tgt-m",
                },
            ],
        }
        result = await engine.evaluate(tmp_db, "op-m", recommendation)
        assert "parallel_tasks" in result
        assert result["parallel_tasks"] == []

    async def test_high_risk_excluded_from_parallel_tasks(self, tmp_db):
        from app.services.decision_engine import DecisionEngine

        await self._setup_db(tmp_db)

        engine = DecisionEngine()
        recommendation = {
            "recommended_technique_id": "T1059.004",
            "confidence": 0.8,
            "options": [
                {
                    "technique_id": "T1059.004",
                    "risk_level": "low",
                    "recommended_engine": "ssh",
                    "target_id": "tgt-1",
                },
                {
                    "technique_id": "T1003.001",
                    "risk_level": "high",
                    "recommended_engine": "ssh",
                    "target_id": "tgt-1",
                },
                {
                    "technique_id": "T_CRITICAL",
                    "risk_level": "critical",
                    "recommended_engine": "ssh",
                    "target_id": "tgt-1",
                },
            ],
        }
        result = await engine.evaluate(tmp_db, "op-1", recommendation)
        assert "parallel_tasks" in result
        # Only the low-risk technique should be in parallel_tasks
        technique_ids = [t["technique_id"] for t in result["parallel_tasks"]]
        assert "T1059.004" in technique_ids
        assert "T1003.001" not in technique_ids
        assert "T_CRITICAL" not in technique_ids

    async def test_parallel_tasks_dedup(self, tmp_db):
        from app.services.decision_engine import DecisionEngine

        await self._setup_db(tmp_db)

        engine = DecisionEngine()
        recommendation = {
            "recommended_technique_id": "T1059.004",
            "confidence": 0.8,
            "options": [
                {
                    "technique_id": "T1059.004",
                    "risk_level": "low",
                    "recommended_engine": "ssh",
                    "target_id": "tgt-1",
                },
                {
                    "technique_id": "T1059.004",
                    "risk_level": "low",
                    "recommended_engine": "ssh",
                    "target_id": "tgt-1",
                },
                {
                    "technique_id": "T1087",
                    "risk_level": "medium",
                    "recommended_engine": "ssh",
                    "target_id": "tgt-1",
                },
            ],
        }
        result = await engine.evaluate(tmp_db, "op-1", recommendation)
        assert "parallel_tasks" in result
        # T1059.004 should appear only once
        technique_ids = [t["technique_id"] for t in result["parallel_tasks"]]
        assert technique_ids.count("T1059.004") == 1
