"""OODA loop endpoints."""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
import aiosqlite

from app.database import get_db
from app.models import OODAIteration
from app.models.api_schemas import OODATimelineEntry

router = APIRouter()


def _row_to_ooda(row: aiosqlite.Row) -> OODAIteration:
    return OODAIteration(
        id=row["id"],
        operation_id=row["operation_id"],
        iteration_number=row["iteration_number"],
        phase=row["phase"],
        observe_summary=row["observe_summary"],
        orient_summary=row["orient_summary"],
        decide_summary=row["decide_summary"],
        act_summary=row["act_summary"],
        recommendation_id=row["recommendation_id"],
        technique_execution_id=row["technique_execution_id"],
        started_at=row["started_at"],
        completed_at=row["completed_at"],
    )


async def _ensure_operation(db: aiosqlite.Connection, operation_id: str):
    cursor = await db.execute("SELECT id FROM operations WHERE id = ?", (operation_id,))
    if not await cursor.fetchone():
        raise HTTPException(status_code=404, detail="Operation not found")


@router.post("/operations/{operation_id}/ooda/trigger", response_model=OODAIteration)
async def trigger_ooda(
    operation_id: str,
    db: aiosqlite.Connection = Depends(get_db),
):
    """STUB — Create a new OODA iteration in observe phase."""
    db.row_factory = aiosqlite.Row
    await _ensure_operation(db, operation_id)

    # Determine next iteration number
    cursor = await db.execute(
        "SELECT COALESCE(MAX(iteration_number), 0) + 1 AS next_num "
        "FROM ooda_iterations WHERE operation_id = ?",
        (operation_id,),
    )
    row = await cursor.fetchone()
    next_num = row["next_num"]

    ooda_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    await db.execute(
        "INSERT INTO ooda_iterations "
        "(id, operation_id, iteration_number, phase, started_at) "
        "VALUES (?, ?, ?, 'observe', ?)",
        (ooda_id, operation_id, next_num, now),
    )
    await db.commit()

    cursor = await db.execute(
        "SELECT * FROM ooda_iterations WHERE id = ?", (ooda_id,)
    )
    row = await cursor.fetchone()
    return _row_to_ooda(row)


@router.get("/operations/{operation_id}/ooda/current", response_model=OODAIteration | None)
async def get_current_ooda(
    operation_id: str,
    db: aiosqlite.Connection = Depends(get_db),
):
    db.row_factory = aiosqlite.Row
    await _ensure_operation(db, operation_id)

    cursor = await db.execute(
        "SELECT * FROM ooda_iterations WHERE operation_id = ? "
        "ORDER BY iteration_number DESC LIMIT 1",
        (operation_id,),
    )
    row = await cursor.fetchone()
    if not row:
        return None
    return _row_to_ooda(row)


@router.get("/operations/{operation_id}/ooda/history", response_model=list[OODAIteration])
async def get_ooda_history(
    operation_id: str,
    db: aiosqlite.Connection = Depends(get_db),
):
    db.row_factory = aiosqlite.Row
    await _ensure_operation(db, operation_id)

    cursor = await db.execute(
        "SELECT * FROM ooda_iterations WHERE operation_id = ? "
        "ORDER BY iteration_number ASC",
        (operation_id,),
    )
    rows = await cursor.fetchall()
    return [_row_to_ooda(r) for r in rows]


@router.get(
    "/operations/{operation_id}/ooda/timeline",
    response_model=list[OODATimelineEntry],
)
async def get_ooda_timeline(
    operation_id: str,
    db: aiosqlite.Connection = Depends(get_db),
):
    """Flatten iterations into per-phase timeline entries."""
    db.row_factory = aiosqlite.Row
    await _ensure_operation(db, operation_id)

    cursor = await db.execute(
        "SELECT * FROM ooda_iterations WHERE operation_id = ? "
        "ORDER BY iteration_number ASC",
        (operation_id,),
    )
    rows = await cursor.fetchall()

    entries: list[OODATimelineEntry] = []
    phase_map = [
        ("observe", "observe_summary"),
        ("orient", "orient_summary"),
        ("decide", "decide_summary"),
        ("act", "act_summary"),
    ]
    for row in rows:
        for phase_name, summary_col in phase_map:
            summary = row[summary_col]
            if summary:
                entries.append(
                    OODATimelineEntry(
                        iteration_number=row["iteration_number"],
                        phase=phase_name,
                        summary=summary,
                        timestamp=row["started_at"] or "",
                    )
                )
    return entries
