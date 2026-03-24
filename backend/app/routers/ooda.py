# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: azz093093.830330@gmail.com

"""OODA loop endpoints."""

import asyncio
import functools
import json
import logging
import uuid

import asyncpg
from fastapi import APIRouter, Depends

from app.database import db_manager, get_db
from app.models import OODAIteration
from app.models.enums import OODAPhase
from app.models.ooda import OodaTriggerQueued, OODADirectiveCreate, OodaDashboardResponse
from app.models.api_schemas import OODATimelineEntry
from app.routers._deps import ensure_operation
from app.utils.enum_safety import safe_enum
from app.services.ooda_controller import OODAController
from app.ws_manager import ws_manager
from app.services.ooda_scheduler import start_auto_loop, stop_auto_loop, get_loop_status

logger = logging.getLogger(__name__)
router = APIRouter()

@functools.lru_cache(maxsize=1)
def _get_controller() -> OODAController:
    """Return singleton OODAController, built once and cached.

    Delegates to build_ooda_controller() which correctly wires MCP engine.
    """
    from app.services.ooda_controller import build_ooda_controller  # noqa: PLC0415
    return build_ooda_controller()


def _row_to_ooda(row: asyncpg.Record) -> OODAIteration:
    return OODAIteration(
        id=row["id"],
        operation_id=row["operation_id"],
        iteration_number=row["iteration_number"],
        phase=safe_enum(OODAPhase, row["phase"], log_name="OODAPhase"),
        observe_summary=row["observe_summary"],
        orient_summary=row["orient_summary"],
        decide_summary=row["decide_summary"],
        act_summary=row["act_summary"],
        recommendation_id=row["recommendation_id"],
        technique_execution_id=row["technique_execution_id"],
        started_at=row["started_at"],
        completed_at=row["completed_at"],
    )


@router.post("/operations/{operation_id}/ooda/trigger", status_code=202)


async def trigger_ooda(
    operation_id: str,
    db: asyncpg.Connection = Depends(get_db),
) -> OodaTriggerQueued:
    """Enqueue an OODA cycle -- returns 202 immediately, executes in background."""
    await ensure_operation(db, operation_id)

    iteration_id = str(uuid.uuid4())

    _task = asyncio.create_task(
        _run_ooda_background(iteration_id, operation_id)
    )
    _task.add_done_callback(
        lambda t: logger.warning(
            "OODA background task cancelled for iteration %s", iteration_id
        )
        if t.cancelled() else None
    )

    return OodaTriggerQueued(
        status="queued",
        operation_id=operation_id,
    )


async def _run_ooda_background(iteration_id: str, op_id: str) -> None:
    """Background task: run full OODA cycle with its own DB connection."""
    async with db_manager.connection() as db:
        try:
            controller = _get_controller()
            await controller.trigger_cycle(db, op_id)
        except Exception as exc:
            logger.exception(
                "Background OODA cycle %s failed: %s", iteration_id, exc
            )
            try:
                await db.execute(
                    "UPDATE ooda_iterations SET phase = 'failed' "
                    "WHERE id = $1 OR (operation_id = $2 AND completed_at IS NULL)",
                    iteration_id, op_id,
                )
            except Exception:
                logger.exception(
                    "Failed to update ooda_iteration status for %s", iteration_id
                )
            await ws_manager.broadcast(op_id, "ooda.failed", {
                "iteration_id": iteration_id,
                "error": str(exc),
            })


@router.get(
    "/operations/{operation_id}/ooda/dashboard",
    response_model=OodaDashboardResponse,
)
async def get_ooda_dashboard(
    operation_id: str,
    db: asyncpg.Connection = Depends(get_db),
):
    """Aggregated OODA dashboard data for the War Room."""
    await ensure_operation(db, operation_id)
    total = await db.fetchval(
        "SELECT COUNT(*) FROM ooda_iterations WHERE operation_id = $1",
        operation_id,
    )
    rows = await db.fetch(
        "SELECT * FROM ooda_iterations WHERE operation_id = $1 "
        "ORDER BY iteration_number DESC LIMIT 10",
        operation_id,
    )
    iterations = [_row_to_ooda(r) for r in rows]
    latest = iterations[0] if iterations else None
    return OodaDashboardResponse(
        current_phase=latest.phase if latest else "idle",
        iteration_count=total,
        latest_iteration=latest,
        recent_iterations=iterations,
    )


@router.get("/operations/{operation_id}/ooda/current", response_model=OODAIteration | None)


async def get_current_ooda(
    operation_id: str,
    db: asyncpg.Connection = Depends(get_db),
):
    await ensure_operation(db, operation_id)

    row = await db.fetchrow(
        "SELECT * FROM ooda_iterations WHERE operation_id = $1 "
        "ORDER BY iteration_number DESC LIMIT 1",
        operation_id,
    )
    if not row:
        return None
    return _row_to_ooda(row)


@router.get("/operations/{operation_id}/ooda/history", response_model=list[OODAIteration])


async def get_ooda_history(
    operation_id: str,
    db: asyncpg.Connection = Depends(get_db),
):
    await ensure_operation(db, operation_id)

    rows = await db.fetch(
        "SELECT * FROM ooda_iterations WHERE operation_id = $1 "
        "ORDER BY iteration_number ASC",
        operation_id,
    )
    return [_row_to_ooda(r) for r in rows]


@router.get(
    "/operations/{operation_id}/ooda/timeline",
    response_model=list[OODATimelineEntry],
)


async def get_ooda_timeline(
    operation_id: str,
    db: asyncpg.Connection = Depends(get_db),
):
    """Flatten iterations into per-phase timeline entries."""
    await ensure_operation(db, operation_id)

    rows = await db.fetch(
        "SELECT * FROM ooda_iterations WHERE operation_id = $1 "
        "ORDER BY iteration_number ASC",
        operation_id,
    )

    entries: list[OODATimelineEntry] = []
    phase_map = [
        ("observe", "observe_summary"),
        ("orient", "orient_summary"),
        ("decide", "decide_summary"),
        ("act", "act_summary"),
    ]
    for row in rows:
        # Resolve target info via technique_executions for this iteration
        exec_target = await db.fetchrow(
            "SELECT te.target_id, t.hostname, t.ip_address "
            "FROM technique_executions te "
            "JOIN targets t ON te.target_id = t.id "
            "WHERE te.ooda_iteration_id = $1 LIMIT 1",
            row["id"],
        )
        target_id = exec_target["target_id"] if exec_target else None
        target_hostname = exec_target["hostname"] if exec_target else None
        target_ip = exec_target["ip_address"] if exec_target else None

        for phase_name, summary_col in phase_map:
            summary = row[summary_col]
            if summary:
                detail = None

                if phase_name == "observe":
                    facts = await db.fetch(
                        "SELECT trait, value, category FROM facts "
                        "WHERE operation_id = $1 ORDER BY collected_at DESC LIMIT 50",
                        operation_id,
                    )
                    detail = {
                        "facts_count": len(facts),
                        "facts": [dict(f) for f in facts],
                        "raw_summary": row["observe_summary"] or "",
                    }

                elif phase_name == "orient" and row["recommendation_id"]:
                    rec = await db.fetchrow(
                        "SELECT situation_assessment, recommended_technique_id, confidence, "
                        "reasoning_text, options FROM recommendations WHERE id = $1",
                        row["recommendation_id"],
                    )
                    if rec:
                        detail = {
                            "situation_assessment": rec["situation_assessment"],
                            "recommended_technique_id": rec["recommended_technique_id"],
                            "confidence": float(rec["confidence"]) if rec["confidence"] else 0,
                            "reasoning_text": rec["reasoning_text"],
                            "options": json.loads(rec["options"]) if rec["options"] else [],
                        }

                elif phase_name == "decide":
                    detail = {
                        "reason": row["decide_summary"] or "",
                    }

                elif phase_name == "act" and row["technique_execution_id"]:
                    act_exec = await db.fetchrow(
                        "SELECT technique_id, engine, status, result_summary, error_message, "
                        "facts_collected_count FROM technique_executions WHERE id = $1",
                        row["technique_execution_id"],
                    )
                    if act_exec:
                        detail = {
                            "technique_id": act_exec["technique_id"],
                            "engine": act_exec["engine"],
                            "status": act_exec["status"],
                            "result_summary": act_exec["result_summary"],
                            "error_message": act_exec["error_message"],
                            "facts_collected_count": act_exec["facts_collected_count"] or 0,
                        }

                entries.append(
                    OODATimelineEntry(
                        iteration_number=row["iteration_number"],
                        phase=phase_name,
                        summary=summary,
                        timestamp=str(row["started_at"] or ""),
                        target_id=target_id,
                        target_hostname=target_hostname,
                        target_ip=target_ip,
                        detail=detail,
                    )
                )
    # -- Also include completed recon scans as timeline entries --
    recon_rows = await db.fetch(
        """
        SELECT rs.target_id, rs.open_ports, rs.os_guess,
               rs.initial_access_method, rs.credential_found,
               rs.completed_at, rs.ip_address AS scan_ip,
               t.hostname, t.ip_address
        FROM recon_scans rs
        LEFT JOIN targets t ON t.id = rs.target_id
        WHERE rs.operation_id = $1 AND rs.status = 'completed'
        ORDER BY rs.completed_at ASC
        """,
        operation_id,
    )

    for row in recon_rows:
        ports = json.loads(row["open_ports"] or "[]")
        host = row["hostname"] or row["ip_address"] or row["scan_ip"] or "unknown"
        parts = [f"Target: {host}"]
        if ports:
            port_list = ", ".join(
                f"{p['port']}/{p.get('service', '?')}" for p in ports
            )
            parts.append(f"Ports: {port_list}")
        if row["os_guess"]:
            parts.append(f"OS: {row['os_guess']}")
        if row["credential_found"]:
            parts.append(f"Credential: {row['credential_found']}")
        elif row["initial_access_method"] and row["initial_access_method"] != "none":
            parts.append(f"Access: {row['initial_access_method']}")

        entries.append(
            OODATimelineEntry(
                iteration_number=0,
                phase="recon",
                summary=" · ".join(parts),
                timestamp=str(row["completed_at"] or ""),
            )
        )

    return entries


@router.post("/operations/{operation_id}/ooda/directive", status_code=201)
async def create_directive(
    operation_id: str,
    body: OODADirectiveCreate,
    db: asyncpg.Connection = Depends(get_db),
):
    """Store a human operator directive to influence the next OODA orient phase."""
    await ensure_operation(db, operation_id)
    directive_id = str(uuid.uuid4())
    await db.execute(
        "INSERT INTO ooda_directives (id, operation_id, directive, scope) VALUES ($1, $2, $3, $4)",
        directive_id, operation_id, body.directive, body.scope,
    )
    return {"id": directive_id, "status": "stored"}


@router.get("/operations/{operation_id}/ooda/directive/latest")
async def get_latest_directive(
    operation_id: str,
    db: asyncpg.Connection = Depends(get_db),
):
    """Get the most recent directive for this operation."""
    await ensure_operation(db, operation_id)
    row = await db.fetchrow(
        "SELECT * FROM ooda_directives WHERE operation_id = $1 ORDER BY created_at DESC LIMIT 1",
        operation_id,
    )
    if not row:
        return None
    return dict(row)


@router.post("/operations/{operation_id}/ooda/auto-start")


async def start_ooda_auto_loop(
    operation_id: str,
    interval_sec: int = 30,
    max_iterations: int = 0,
    db: asyncpg.Connection = Depends(get_db),
):
    """Start automated OODA loop (APScheduler). Runs every interval_sec until max_iterations or stopped."""
    await ensure_operation(db, operation_id)  # raises 404 if not found
    return await start_auto_loop(
        operation_id=operation_id,
        interval_sec=interval_sec,
        max_iterations=max_iterations,
    )


@router.delete("/operations/{operation_id}/ooda/auto-stop")


async def stop_ooda_auto_loop(
    operation_id: str,
    db: asyncpg.Connection = Depends(get_db),
):
    """Stop automated OODA loop for this operation."""
    await ensure_operation(db, operation_id)  # raises 404 if not found
    return await stop_auto_loop(operation_id)


@router.get("/operations/{operation_id}/ooda/auto-status")


async def get_ooda_auto_status(operation_id: str):
    """Get auto loop status for this operation (purely in-memory, no DB check needed)."""
    return get_loop_status(operation_id)
