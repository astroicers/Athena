# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: [TODO: contact email]

"""Mission planning endpoints."""

import uuid
from datetime import datetime, timezone

import asyncpg
from fastapi import APIRouter, Depends, HTTPException

from app.database import get_db
from app.models import MissionStep
from app.models.api_schemas import MissionStepCreate, MissionStepUpdate
from app.routers._deps import ensure_operation

router = APIRouter()


def _row_to_step(row: asyncpg.Record) -> MissionStep:
    return MissionStep(
        id=row["id"],
        operation_id=row["operation_id"],
        step_number=row["step_number"],
        technique_id=row["technique_id"],
        technique_name=row["technique_name"],
        target_id=row["target_id"],
        target_label=row["target_label"],
        engine=row["engine"],
        status=row["status"],
    )


@router.get(
    "/operations/{operation_id}/mission/steps",
    response_model=list[MissionStep],
)


async def list_mission_steps(
    operation_id: str,
    db: asyncpg.Connection = Depends(get_db),
):
    await ensure_operation(db, operation_id)

    rows = await db.fetch(
        "SELECT * FROM mission_steps WHERE operation_id = $1 ORDER BY step_number",
        operation_id,
    )
    return [_row_to_step(r) for r in rows]


@router.post(
    "/operations/{operation_id}/mission/steps",
    response_model=MissionStep,
    status_code=201,
)


async def create_mission_step(
    operation_id: str,
    body: MissionStepCreate,
    db: asyncpg.Connection = Depends(get_db),
):
    await ensure_operation(db, operation_id)

    step_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    await db.execute(
        "INSERT INTO mission_steps "
        "(id, operation_id, step_number, technique_id, technique_name, "
        "target_id, target_label, engine, status, created_at) "
        "VALUES ($1, $2, $3, $4, $5, $6, $7, $8, 'queued', $9)",
        step_id,
        operation_id,
        body.step_number,
        body.technique_id,
        body.technique_name,
        body.target_id,
        body.target_label,
        body.engine.value,
        now,
    )

    row = await db.fetchrow("SELECT * FROM mission_steps WHERE id = $1", step_id)
    return _row_to_step(row)


@router.patch(
    "/operations/{operation_id}/mission/steps/{step_id}",
    response_model=MissionStep,
)


async def update_mission_step(
    operation_id: str,
    step_id: str,
    body: MissionStepUpdate,
    db: asyncpg.Connection = Depends(get_db),
):
    await ensure_operation(db, operation_id)

    row = await db.fetchrow(
        "SELECT * FROM mission_steps WHERE id = $1 AND operation_id = $2",
        step_id, operation_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Mission step not found")

    updates = body.model_dump(exclude_none=True)
    if not updates:
        row = await db.fetchrow("SELECT * FROM mission_steps WHERE id = $1", step_id)
        return _row_to_step(row)

    # Handle started_at / completed_at timestamps based on status transitions
    now = datetime.now(timezone.utc)
    if "status" in updates:
        status_val = updates["status"]
        if hasattr(status_val, "value"):
            status_val = status_val.value
            updates["status"] = status_val
        if status_val == "running":
            updates["started_at"] = now
        elif status_val in ("completed", "failed", "skipped"):
            updates["completed_at"] = now

    set_clause = ", ".join(f"{k} = ${i+1}" for i, k in enumerate(updates))
    values = list(updates.values())
    values.append(step_id)

    await db.execute(
        f"UPDATE mission_steps SET {set_clause} WHERE id = ${len(values)}",
        *values,
    )

    row = await db.fetchrow("SELECT * FROM mission_steps WHERE id = $1", step_id)
    return _row_to_step(row)
