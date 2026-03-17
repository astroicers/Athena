# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: azz093093.830330@gmail.com

"""AgentSwarm — bounded-concurrency parallel task executor for OODA Act phase."""

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

import asyncpg

from app.config import settings
from app.services.engine_router import EngineRouter
from app.ws_manager import WebSocketManager

logger = logging.getLogger(__name__)


@dataclass
class SwarmTask:
    """Single unit of parallel execution within the Act phase."""
    task_id: str
    technique_id: str
    target_id: str
    engine: str
    status: str = "pending"
    result: dict | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error: str | None = None


@dataclass
class SwarmResult:
    """Aggregated result of all parallel tasks in one Act phase."""
    ooda_iteration_id: str
    total: int
    completed: int = 0
    failed: int = 0
    timed_out: int = 0
    tasks: list[SwarmTask] = field(default_factory=list)

    @property
    def all_failed(self) -> bool:
        return self.total > 0 and self.completed == 0

    @property
    def partial_success(self) -> bool:
        return 0 < self.completed < self.total

    @property
    def act_summary(self) -> str:
        return (
            f"Swarm: {self.completed}/{self.total} succeeded, "
            f"{self.failed} failed, {self.timed_out} timed out"
        )


class SwarmExecutor:
    """Bounded-concurrency parallel executor for the OODA Act phase."""

    def __init__(self, engine_router: EngineRouter, ws_manager: WebSocketManager):
        self._router = engine_router
        self._ws = ws_manager
        self._semaphore = asyncio.Semaphore(settings.MAX_PARALLEL_TASKS)

    async def execute_swarm(
        self,
        pool: asyncpg.Pool,
        operation_id: str,
        ooda_iteration_id: str,
        parallel_tasks: list[dict],
    ) -> SwarmResult:
        """Execute multiple tasks in parallel with bounded concurrency.

        Each parallel coroutine acquires its own connection from *pool* so that
        concurrent tasks never share a single asyncpg.Connection (which is not
        safe for concurrent coroutines).
        """
        swarm_result = SwarmResult(
            ooda_iteration_id=ooda_iteration_id,
            total=len(parallel_tasks),
        )

        if not parallel_tasks:
            return swarm_result

        swarm_tasks: list[SwarmTask] = []
        for task_spec in parallel_tasks:
            st = SwarmTask(
                task_id=str(uuid.uuid4()),
                technique_id=task_spec["technique_id"],
                target_id=task_spec["target_id"],
                engine=task_spec.get("engine", "ssh"),
            )
            swarm_tasks.append(st)

        # Insert into DB — sequential, use a single acquired connection
        now = datetime.now(timezone.utc)
        async with pool.acquire() as db:
            for st in swarm_tasks:
                await db.execute(
                    "INSERT INTO swarm_tasks "
                    "(id, ooda_iteration_id, operation_id, technique_id, target_id, "
                    "engine, status, created_at) "
                    "VALUES ($1, $2, $3, $4, $5, $6, 'pending', $7)",
                    st.task_id, ooda_iteration_id, operation_id,
                    st.technique_id, st.target_id, st.engine, now,
                )

        # Broadcast initial state
        await self._broadcast_batch(operation_id, swarm_tasks)

        # Execute all tasks concurrently with bounded semaphore.
        # Each _execute_single acquires its own connection from the pool so
        # concurrent coroutines never share a single asyncpg.Connection.
        # Using asyncio.gather with return_exceptions=True for Python 3.10 compat
        # (_execute_single handles its own exceptions, so leaked ones are logged)
        results = await asyncio.gather(
            *(
                self._execute_single(pool, operation_id, ooda_iteration_id, st)
                for st in swarm_tasks
            ),
            return_exceptions=True,
        )
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(
                    "SwarmExecutor: unhandled task exception: %s",
                    result, exc_info=result,
                )

        # Aggregate results
        for st in swarm_tasks:
            swarm_result.tasks.append(st)
            if st.status == "completed":
                swarm_result.completed += 1
            elif st.status == "timeout":
                swarm_result.timed_out += 1
            elif st.status == "failed":
                swarm_result.failed += 1

        # Update DB records — sequential, use a single acquired connection
        async with pool.acquire() as db:
            for st in swarm_tasks:
                await db.execute(
                    "UPDATE swarm_tasks SET status = $1, error = $2, "
                    "started_at = $3, completed_at = $4 WHERE id = $5",
                    st.status, st.error,
                    st.started_at if st.started_at else None,
                    st.completed_at if st.completed_at else None,
                    st.task_id,
                )

        # Broadcast final state
        await self._broadcast_batch(operation_id, swarm_tasks)

        return swarm_result

    async def _execute_single(
        self, pool: asyncpg.Pool, operation_id: str, ooda_iteration_id: str, task: SwarmTask,
    ) -> None:
        """Execute a single task with semaphore guard and per-task timeout.

        Acquires its own connection from *pool* so that concurrent invocations
        do not share a single asyncpg.Connection.
        """
        async with self._semaphore:
            task.status = "running"
            task.started_at = datetime.now(timezone.utc)

            try:
                async with pool.acquire() as db:
                    result = await asyncio.wait_for(
                        self._router.execute(
                            db,
                            technique_id=task.technique_id,
                            target_id=task.target_id,
                            engine=task.engine,
                            operation_id=operation_id,
                            ooda_iteration_id=ooda_iteration_id,
                        ),
                        timeout=settings.PARALLEL_TASK_TIMEOUT_SEC,
                    )
                task.result = result
                task.status = "completed" if result.get("status") == "success" else "failed"
                if result.get("error"):
                    task.error = result["error"]
            except asyncio.TimeoutError:
                task.status = "timeout"
                task.error = f"Task timed out after {settings.PARALLEL_TASK_TIMEOUT_SEC}s"
                logger.warning("SwarmTask %s timed out: %s on %s", task.task_id, task.technique_id, task.target_id)
            except Exception as exc:
                task.status = "failed"
                task.error = f"{type(exc).__name__}: {exc}"
                logger.error("SwarmTask %s failed: %s", task.task_id, exc, exc_info=True)
            finally:
                task.completed_at = datetime.now(timezone.utc)

    async def _broadcast_batch(self, operation_id: str, tasks: list[SwarmTask]) -> None:
        """Broadcast execution.batch_update WebSocket event."""
        try:
            await self._ws.broadcast(
                operation_id, "execution.batch_update",
                {"tasks": [
                    {"task_id": t.task_id, "technique_id": t.technique_id,
                     "target_id": t.target_id, "engine": t.engine,
                     "status": t.status, "error": t.error}
                    for t in tasks
                ]},
            )
        except Exception:
            pass  # fire-and-forget
