# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: azz093093.830330@gmail.com

"""APScheduler-based OODA loop automation service."""

import logging
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import settings
from app.services.ooda_controller import build_ooda_controller

logger = logging.getLogger(__name__)

_scheduler = AsyncIOScheduler(timezone="UTC")
_active_loops: dict[str, dict[str, Any]] = {}


def get_scheduler() -> AsyncIOScheduler:
    return _scheduler


def start_scheduler() -> None:
    if not _scheduler.running:
        _scheduler.start()
        logger.info("OODA APScheduler started")


def stop_scheduler() -> None:
    if _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("OODA APScheduler stopped")


async def start_auto_loop(
    operation_id: str,
    interval_sec: int = settings.OODA_LOOP_INTERVAL_SEC,
    max_iterations: int = 0,
) -> dict:
    """Start automated OODA loop for an operation."""
    if operation_id in _active_loops:
        return {"status": "already_running", "operation_id": operation_id}

    controller = build_ooda_controller()

    _active_loops[operation_id] = {
        "interval_sec": interval_sec,
        "max_iterations": max_iterations,
        "iteration_count": 0,
        "job_id": f"ooda_{operation_id}",
    }

    async def _run_cycle():
        from app.database import db_manager

        meta = _active_loops.get(operation_id)
        if not meta:
            return
        if meta["max_iterations"] > 0 and meta["iteration_count"] >= meta["max_iterations"]:
            logger.info(
                "Operation %s reached max_iterations=%d, stopping",
                operation_id,
                meta["max_iterations"],
            )
            await stop_auto_loop(operation_id)
            return
        meta["iteration_count"] += 1
        logger.info("OODA auto-cycle %d for operation %s", meta["iteration_count"], operation_id)
        try:
            async with db_manager.connection() as db:
                await controller.trigger_cycle(db, operation_id)
        except Exception:
            logger.exception("OODA auto-cycle failed for operation %s", operation_id)

    _scheduler.add_job(
        _run_cycle,
        trigger="interval",
        seconds=interval_sec,
        id=f"ooda_{operation_id}",
        replace_existing=True,
        max_instances=1,
    )
    return {
        "status": "started",
        "operation_id": operation_id,
        "interval_sec": interval_sec,
        "max_iterations": max_iterations,
    }


async def stop_auto_loop(operation_id: str) -> dict:
    """Stop automated OODA loop."""
    job_id = f"ooda_{operation_id}"
    if _scheduler.get_job(job_id):
        _scheduler.remove_job(job_id)
    meta = _active_loops.pop(operation_id, None)
    iterations_completed = meta["iteration_count"] if meta else 0
    return {
        "status": "stopped",
        "operation_id": operation_id,
        "iterations_completed": iterations_completed,
    }


def get_loop_status(operation_id: str) -> dict:
    """Return current auto-loop status for an operation.

    Includes a boolean ``running`` field so frontend consumers can
    straightforwardly read ``autoStatus.running`` without having to
    interpret the ``status`` enum string. ``status`` is kept for
    backward compatibility with log/audit consumers.
    """
    from app.config import settings as _settings  # noqa: PLC0415

    relay_available = bool(getattr(_settings, "RELAY_IP", "") or "")
    meta = _active_loops.get(operation_id)
    if not meta:
        return {
            "running": False,
            "status": "idle",
            "operation_id": operation_id,
            "relay_available": relay_available,
        }
    return {
        "running": True,
        "status": "running",
        "operation_id": operation_id,
        "interval_sec": meta["interval_sec"],
        "max_iterations": meta["max_iterations"],
        "iteration_count": meta["iteration_count"],
        "relay_available": relay_available,
    }
