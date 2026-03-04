# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: [TODO: contact email]

"""Admin endpoints — operation reset and maintenance utilities."""

from datetime import datetime, timezone

import aiosqlite
from fastapi import APIRouter, Depends, Response

from app.database import get_db
from app.routers._deps import ensure_operation
from app.ws_manager import ws_manager

router = APIRouter()


@router.post("/operations/{operation_id}/reset", status_code=204)
async def reset_operation(
    operation_id: str,
    db: aiosqlite.Connection = Depends(get_db),
):
    """Reset an operation to its initial planning state.

    Deletes all execution history (logs, recommendations, facts, technique
    executions, OODA iterations) and all operational data (targets, agents,
    mission steps).  Resets operation counters and C5ISR statuses back to
    their initial values.
    """
    await ensure_operation(db, operation_id)

    now = datetime.now(timezone.utc).isoformat()

    # ── DELETE execution history (FK-safe order) ─────────────────────────
    await db.execute(
        "DELETE FROM log_entries WHERE operation_id = ?", (operation_id,)
    )
    await db.execute(
        "DELETE FROM recommendations WHERE operation_id = ?", (operation_id,)
    )
    await db.execute(
        "DELETE FROM facts WHERE operation_id = ?", (operation_id,)
    )
    await db.execute(
        "DELETE FROM technique_executions WHERE operation_id = ?", (operation_id,)
    )
    await db.execute(
        "DELETE FROM ooda_iterations WHERE operation_id = ?", (operation_id,)
    )

    # ── DELETE operational data (FK-safe order) ──────────────────────────
    await db.execute(
        "DELETE FROM mission_steps WHERE operation_id = ?", (operation_id,)
    )
    await db.execute(
        "DELETE FROM recon_scans WHERE operation_id = ?", (operation_id,)
    )
    await db.execute(
        "DELETE FROM agents WHERE operation_id = ?", (operation_id,)
    )
    await db.execute(
        "DELETE FROM targets WHERE operation_id = ?", (operation_id,)
    )

    # ── RESET operation counters & C5ISR statuses ──────────────────────
    await db.execute(
        "UPDATE operations SET "
        "status = 'planning', "
        "current_ooda_phase = 'observe', "
        "ooda_iteration_count = 0, "
        "threat_level = 0.0, "
        "success_rate = 0.0, "
        "techniques_executed = 0, "
        "active_agents = 0, "
        "data_exfiltrated_bytes = 0, "
        "updated_at = ? "
        "WHERE id = ?",
        (now, operation_id),
    )
    await db.execute(
        "UPDATE c5isr_statuses SET "
        "status = 'offline', "
        "health_pct = 0.0, "
        "detail = 'Awaiting operation start', "
        "updated_at = ? "
        "WHERE operation_id = ?",
        (now, operation_id),
    )

    await db.commit()

    # ── Broadcast reset event via WebSocket ──────────────────────────────
    await ws_manager.broadcast(
        operation_id, "operation.reset", {"operation_id": operation_id}
    )

    return Response(status_code=204)
