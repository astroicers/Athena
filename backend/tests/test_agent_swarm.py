# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: [TODO: contact email]

"""Unit tests for AgentSwarm — SPEC-030 bounded-parallel task executor."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import aiosqlite

from app.database import _CREATE_TABLES

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _make_in_memory_db() -> aiosqlite.Connection:
    """Create an in-memory SQLite database with the full Athena schema.

    Foreign keys are disabled to allow inserting swarm_tasks without
    requiring parent rows in operations/ooda_iterations/targets.
    """
    db = await aiosqlite.connect(":memory:")
    db.row_factory = aiosqlite.Row
    # Disable FK for swarm tests — we test executor logic, not DB integrity
    await db.execute("PRAGMA foreign_keys = OFF;")
    for ddl in _CREATE_TABLES:
        await db.execute(ddl)
    await db.commit()
    return db


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

    async def test_empty_parallel_tasks(self):
        from app.services.agent_swarm import SwarmExecutor

        ws = _make_mock_ws()
        router = _make_mock_router()
        executor = SwarmExecutor(engine_router=router, ws_manager=ws)

        db = await _make_in_memory_db()
        try:
            result = await executor.execute_swarm(
                db, "op-1", "ooda-1", []
            )
            assert result.total == 0
            assert result.completed == 0
            assert result.failed == 0
            assert result.timed_out == 0
            assert result.tasks == []
        finally:
            await db.close()


class TestSwarmExecutorSingleTask:
    """Test single task execution."""

    async def test_single_task_executes(self):
        from app.services.agent_swarm import SwarmExecutor

        ws = _make_mock_ws()
        router = _make_mock_router(return_value={"status": "success"})

        with patch("app.services.agent_swarm.settings") as mock_settings:
            mock_settings.MAX_PARALLEL_TASKS = 5
            mock_settings.PARALLEL_TASK_TIMEOUT_SEC = 120

            executor = SwarmExecutor(engine_router=router, ws_manager=ws)

            db = await _make_in_memory_db()
            try:
                tasks = [
                    {
                        "technique_id": "T1059.004",
                        "target_id": "tgt-1",
                        "engine": "ssh",
                    }
                ]
                result = await executor.execute_swarm(db, "op-1", "ooda-1", tasks)
                assert result.total == 1
                assert result.completed == 1
                assert result.failed == 0
                assert len(result.tasks) == 1
                assert result.tasks[0].status == "completed"
                router.execute.assert_awaited_once()
            finally:
                await db.close()


class TestSwarmExecutorMultipleTasks:
    """Test multiple parallel task execution."""

    async def test_multiple_tasks_parallel(self):
        from app.services.agent_swarm import SwarmExecutor

        ws = _make_mock_ws()
        router = _make_mock_router(return_value={"status": "success"})

        with patch("app.services.agent_swarm.settings") as mock_settings:
            mock_settings.MAX_PARALLEL_TASKS = 5
            mock_settings.PARALLEL_TASK_TIMEOUT_SEC = 120

            executor = SwarmExecutor(engine_router=router, ws_manager=ws)

            db = await _make_in_memory_db()
            try:
                tasks = [
                    {"technique_id": "T1059.004", "target_id": "tgt-1", "engine": "ssh"},
                    {"technique_id": "T1087", "target_id": "tgt-2", "engine": "ssh"},
                    {"technique_id": "T1083", "target_id": "tgt-3", "engine": "ssh"},
                ]
                result = await executor.execute_swarm(db, "op-1", "ooda-1", tasks)
                assert result.total == 3
                assert result.completed == 3
                assert result.failed == 0
                assert len(result.tasks) == 3
                assert router.execute.await_count == 3
            finally:
                await db.close()


class TestSwarmExecutorSemaphore:
    """Test semaphore bounds concurrency."""

    async def test_semaphore_bounds_concurrency(self):
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

            db = await _make_in_memory_db()
            try:
                tasks = [
                    {"technique_id": f"T{i}", "target_id": f"tgt-{i}", "engine": "ssh"}
                    for i in range(4)
                ]
                result = await executor.execute_swarm(db, "op-1", "ooda-1", tasks)
                assert result.total == 4
                assert result.completed == 4
                # The semaphore should limit concurrency to 2
                assert max_concurrent <= 2
            finally:
                await db.close()


class TestSwarmExecutorTimeoutIsolation:
    """Test that one task timing out does not affect others."""

    async def test_task_timeout_isolation(self):
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

            db = await _make_in_memory_db()
            try:
                tasks = [
                    {"technique_id": "T_OK1", "target_id": "tgt-1", "engine": "ssh"},
                    {"technique_id": "T_TIMEOUT", "target_id": "tgt-2", "engine": "ssh"},
                    {"technique_id": "T_OK2", "target_id": "tgt-3", "engine": "ssh"},
                ]
                result = await executor.execute_swarm(db, "op-1", "ooda-1", tasks)
                assert result.total == 3
                assert result.completed == 2
                assert result.timed_out == 1

                # Find the timed-out task
                timeout_tasks = [t for t in result.tasks if t.status == "timeout"]
                assert len(timeout_tasks) == 1
                assert timeout_tasks[0].technique_id == "T_TIMEOUT"
            finally:
                await db.close()


class TestSwarmExecutorExceptionIsolation:
    """Test that one task raising an exception does not affect others."""

    async def test_task_exception_isolation(self):
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

            db = await _make_in_memory_db()
            try:
                tasks = [
                    {"technique_id": "T_OK1", "target_id": "tgt-1", "engine": "ssh"},
                    {"technique_id": "T_FAIL", "target_id": "tgt-2", "engine": "ssh"},
                    {"technique_id": "T_OK2", "target_id": "tgt-3", "engine": "ssh"},
                ]
                result = await executor.execute_swarm(db, "op-1", "ooda-1", tasks)
                assert result.total == 3
                assert result.completed == 2
                assert result.failed == 1

                # Find the failed task
                failed_tasks = [t for t in result.tasks if t.status == "failed"]
                assert len(failed_tasks) == 1
                assert "RuntimeError" in failed_tasks[0].error
            finally:
                await db.close()


class TestSwarmExecutorAllFail:
    """Test all tasks failing."""

    async def test_all_tasks_fail(self):
        from app.services.agent_swarm import SwarmExecutor

        ws = _make_mock_ws()
        router = _make_mock_router(return_value={"status": "failed", "error": "nope"})

        with patch("app.services.agent_swarm.settings") as mock_settings:
            mock_settings.MAX_PARALLEL_TASKS = 5
            mock_settings.PARALLEL_TASK_TIMEOUT_SEC = 120

            executor = SwarmExecutor(engine_router=router, ws_manager=ws)

            db = await _make_in_memory_db()
            try:
                tasks = [
                    {"technique_id": "T1", "target_id": "tgt-1", "engine": "ssh"},
                    {"technique_id": "T2", "target_id": "tgt-2", "engine": "ssh"},
                    {"technique_id": "T3", "target_id": "tgt-3", "engine": "ssh"},
                ]
                result = await executor.execute_swarm(db, "op-1", "ooda-1", tasks)
                assert result.total == 3
                assert result.completed == 0
                assert result.failed == 3
                assert result.all_failed is True
            finally:
                await db.close()


class TestSwarmExecutorPartialSuccess:
    """Test partial success."""

    async def test_partial_success(self):
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

            db = await _make_in_memory_db()
            try:
                tasks = [
                    {"technique_id": "T1", "target_id": "tgt-1", "engine": "ssh"},
                    {"technique_id": "T2", "target_id": "tgt-2", "engine": "ssh"},
                    {"technique_id": "T3", "target_id": "tgt-3", "engine": "ssh"},
                ]
                result = await executor.execute_swarm(db, "op-1", "ooda-1", tasks)
                assert result.total == 3
                assert result.completed == 2
                assert result.failed == 1
                assert result.partial_success is True
            finally:
                await db.close()


class TestSwarmExecutorDBPersistence:
    """Test that task records are persisted to the database."""

    async def test_db_records_created(self):
        from app.services.agent_swarm import SwarmExecutor

        ws = _make_mock_ws()
        router = _make_mock_router(return_value={"status": "success"})

        with patch("app.services.agent_swarm.settings") as mock_settings:
            mock_settings.MAX_PARALLEL_TASKS = 5
            mock_settings.PARALLEL_TASK_TIMEOUT_SEC = 120

            executor = SwarmExecutor(engine_router=router, ws_manager=ws)

            db = await _make_in_memory_db()
            try:
                tasks = [
                    {"technique_id": "T1", "target_id": "tgt-1", "engine": "ssh"},
                    {"technique_id": "T2", "target_id": "tgt-2", "engine": "ssh"},
                ]
                result = await executor.execute_swarm(db, "op-1", "ooda-1", tasks)

                # Check DB records
                cursor = await db.execute(
                    "SELECT COUNT(*) FROM swarm_tasks WHERE ooda_iteration_id = 'ooda-1'"
                )
                row = await cursor.fetchone()
                assert row[0] == 2

                # Check records have completed status
                cursor = await db.execute(
                    "SELECT status FROM swarm_tasks WHERE ooda_iteration_id = 'ooda-1'"
                )
                rows = await cursor.fetchall()
                for r in rows:
                    assert r[0] == "completed"
            finally:
                await db.close()


# ---------------------------------------------------------------------------
# DecisionEngine parallel_tasks tests
# ---------------------------------------------------------------------------

class TestDecisionEngineParallelTasks:
    """Test that DecisionEngine.evaluate() produces parallel_tasks."""

    async def _setup_db(self):
        """Setup DB with operation and targets."""
        db = await _make_in_memory_db()
        await db.execute(
            "INSERT INTO operations (id, code, name, codename, strategic_intent, "
            "automation_mode, risk_threshold) "
            "VALUES ('op-1', 'OP-1', 'Test', 'TEST', 'test intent', 'semi_auto', 'medium')"
        )
        await db.execute(
            "INSERT INTO targets (id, hostname, ip_address, os, role, operation_id, is_active) "
            "VALUES ('tgt-1', 'host1', '10.0.0.1', 'Linux', 'server', 'op-1', 1)"
        )
        await db.commit()
        return db

    async def test_evaluate_produces_parallel_tasks(self):
        from app.services.decision_engine import DecisionEngine

        db = await self._setup_db()
        try:
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
            result = await engine.evaluate(db, "op-1", recommendation)
            assert "parallel_tasks" in result
            assert len(result["parallel_tasks"]) == 2
            assert result["parallel_tasks"][0]["technique_id"] == "T1059.004"
            assert result["parallel_tasks"][1]["technique_id"] == "T1087"
        finally:
            await db.close()

    async def test_manual_mode_no_parallel_tasks(self):
        from app.services.decision_engine import DecisionEngine

        db = await _make_in_memory_db()
        try:
            await db.execute(
                "INSERT INTO operations (id, code, name, codename, strategic_intent, "
                "automation_mode, risk_threshold) "
                "VALUES ('op-m', 'OP-M', 'Manual', 'MANUAL', 'test', 'manual', 'medium')"
            )
            await db.execute(
                "INSERT INTO targets (id, hostname, ip_address, os, role, operation_id) "
                "VALUES ('tgt-m', 'host-m', '10.0.0.2', 'Linux', 'server', 'op-m')"
            )
            await db.commit()

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
            result = await engine.evaluate(db, "op-m", recommendation)
            assert "parallel_tasks" in result
            assert result["parallel_tasks"] == []
        finally:
            await db.close()

    async def test_high_risk_excluded_from_parallel_tasks(self):
        from app.services.decision_engine import DecisionEngine

        db = await self._setup_db()
        try:
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
            result = await engine.evaluate(db, "op-1", recommendation)
            assert "parallel_tasks" in result
            # Only the low-risk technique should be in parallel_tasks
            technique_ids = [t["technique_id"] for t in result["parallel_tasks"]]
            assert "T1059.004" in technique_ids
            assert "T1003.001" not in technique_ids
            assert "T_CRITICAL" not in technique_ids
        finally:
            await db.close()

    async def test_parallel_tasks_dedup(self):
        from app.services.decision_engine import DecisionEngine

        db = await self._setup_db()
        try:
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
            result = await engine.evaluate(db, "op-1", recommendation)
            assert "parallel_tasks" in result
            # T1059.004 should appear only once
            technique_ids = [t["technique_id"] for t in result["parallel_tasks"]]
            assert technique_ids.count("T1059.004") == 1
        finally:
            await db.close()
