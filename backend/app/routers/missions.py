"""Mission planning endpoints."""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
import aiosqlite

from app.database import get_db
from app.models import MissionStep
from app.models.api_schemas import MissionStepCreate, MissionStepUpdate
from app.routers._deps import ensure_operation

router = APIRouter()


def _row_to_step(row: aiosqlite.Row) -> MissionStep:
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
    db: aiosqlite.Connection = Depends(get_db),
):
    db.row_factory = aiosqlite.Row
    await ensure_operation(db, operation_id)

    cursor = await db.execute(
        "SELECT * FROM mission_steps WHERE operation_id = ? ORDER BY step_number",
        (operation_id,),
    )
    rows = await cursor.fetchall()
    return [_row_to_step(r) for r in rows]


@router.post(
    "/operations/{operation_id}/mission/steps",
    response_model=MissionStep,
    status_code=201,
)
async def create_mission_step(
    operation_id: str,
    body: MissionStepCreate,
    db: aiosqlite.Connection = Depends(get_db),
):
    db.row_factory = aiosqlite.Row
    await ensure_operation(db, operation_id)

    step_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    await db.execute(
        "INSERT INTO mission_steps "
        "(id, operation_id, step_number, technique_id, technique_name, "
        "target_id, target_label, engine, status, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'queued', ?)",
        (
            step_id,
            operation_id,
            body.step_number,
            body.technique_id,
            body.technique_name,
            body.target_id,
            body.target_label,
            body.engine.value,
            now,
        ),
    )
    await db.commit()

    cursor = await db.execute("SELECT * FROM mission_steps WHERE id = ?", (step_id,))
    row = await cursor.fetchone()
    return _row_to_step(row)


@router.patch(
    "/operations/{operation_id}/mission/steps/{step_id}",
    response_model=MissionStep,
)
async def update_mission_step(
    operation_id: str,
    step_id: str,
    body: MissionStepUpdate,
    db: aiosqlite.Connection = Depends(get_db),
):
    db.row_factory = aiosqlite.Row
    await ensure_operation(db, operation_id)

    cursor = await db.execute(
        "SELECT * FROM mission_steps WHERE id = ? AND operation_id = ?",
        (step_id, operation_id),
    )
    if not await cursor.fetchone():
        raise HTTPException(status_code=404, detail="Mission step not found")

    updates = body.model_dump(exclude_none=True)
    if not updates:
        cursor = await db.execute("SELECT * FROM mission_steps WHERE id = ?", (step_id,))
        row = await cursor.fetchone()
        return _row_to_step(row)

    # Handle started_at / completed_at timestamps based on status transitions
    now = datetime.now(timezone.utc).isoformat()
    if "status" in updates:
        status_val = updates["status"]
        if hasattr(status_val, "value"):
            status_val = status_val.value
            updates["status"] = status_val
        if status_val == "running":
            updates["started_at"] = now
        elif status_val in ("completed", "failed", "skipped"):
            updates["completed_at"] = now

    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values())
    values.append(step_id)

    await db.execute(
        f"UPDATE mission_steps SET {set_clause} WHERE id = ?",
        values,
    )
    await db.commit()

    cursor = await db.execute("SELECT * FROM mission_steps WHERE id = ?", (step_id,))
    row = await cursor.fetchone()
    return _row_to_step(row)


@router.post("/operations/{operation_id}/mission/execute")
async def execute_mission(
    operation_id: str,
    db: aiosqlite.Connection = Depends(get_db),
):
    """STUB — Queue all mission steps for execution."""
    db.row_factory = aiosqlite.Row
    await ensure_operation(db, operation_id)

    cursor = await db.execute(
        "SELECT COUNT(*) AS cnt FROM mission_steps WHERE operation_id = ?",
        (operation_id,),
    )
    row = await cursor.fetchone()
    return {"message": "Execution queued", "steps_count": row["cnt"]}
