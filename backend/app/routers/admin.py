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
    executions, OODA iterations) and resets config data (operation counters,
    targets, agents, mission steps, C5ISR statuses) back to their initial
    values.
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

    # ── UPDATE config data back to initial state ─────────────────────────
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
        "UPDATE targets SET "
        "is_compromised = 0, "
        "privilege_level = NULL "
        "WHERE operation_id = ?",
        (operation_id,),
    )
    await db.execute(
        "UPDATE agents SET "
        "status = 'pending', "
        "privilege = 'User', "
        "last_beacon = NULL "
        "WHERE operation_id = ?",
        (operation_id,),
    )
    await db.execute(
        "UPDATE mission_steps SET "
        "status = 'queued', "
        "started_at = NULL, "
        "completed_at = NULL "
        "WHERE operation_id = ?",
        (operation_id,),
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
