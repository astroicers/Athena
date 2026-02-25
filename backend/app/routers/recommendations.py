"""PentestGPT recommendation endpoints."""

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
import aiosqlite

from app.database import get_db
from app.models import PentestGPTRecommendation
from app.models.recommendation import TacticalOption

router = APIRouter()


def _row_to_recommendation(row: aiosqlite.Row) -> PentestGPTRecommendation:
    options_raw = json.loads(row["options"]) if row["options"] else []
    return PentestGPTRecommendation(
        id=row["id"],
        operation_id=row["operation_id"],
        ooda_iteration_id=row["ooda_iteration_id"],
        situation_assessment=row["situation_assessment"],
        recommended_technique_id=row["recommended_technique_id"],
        confidence=row["confidence"],
        options=[TacticalOption(**o) for o in options_raw],
        reasoning_text=row["reasoning_text"],
        accepted=bool(row["accepted"]) if row["accepted"] is not None else None,
        created_at=row["created_at"],
    )


async def _ensure_operation(db: aiosqlite.Connection, operation_id: str):
    cursor = await db.execute("SELECT id FROM operations WHERE id = ?", (operation_id,))
    if not await cursor.fetchone():
        raise HTTPException(status_code=404, detail="Operation not found")


@router.get(
    "/operations/{operation_id}/recommendations/latest",
    response_model=PentestGPTRecommendation | None,
)
async def get_latest_recommendation(
    operation_id: str,
    db: aiosqlite.Connection = Depends(get_db),
):
    db.row_factory = aiosqlite.Row
    await _ensure_operation(db, operation_id)

    cursor = await db.execute(
        "SELECT * FROM recommendations WHERE operation_id = ? "
        "ORDER BY created_at DESC LIMIT 1",
        (operation_id,),
    )
    row = await cursor.fetchone()
    if not row:
        return None
    return _row_to_recommendation(row)


@router.post(
    "/operations/{operation_id}/recommendations/{recommendation_id}/accept",
    response_model=PentestGPTRecommendation,
)
async def accept_recommendation(
    operation_id: str,
    recommendation_id: str,
    db: aiosqlite.Connection = Depends(get_db),
):
    db.row_factory = aiosqlite.Row
    await _ensure_operation(db, operation_id)

    cursor = await db.execute(
        "SELECT * FROM recommendations WHERE id = ? AND operation_id = ?",
        (recommendation_id, operation_id),
    )
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Recommendation not found")

    await db.execute(
        "UPDATE recommendations SET accepted = 1 WHERE id = ?",
        (recommendation_id,),
    )
    await db.commit()

    cursor = await db.execute(
        "SELECT * FROM recommendations WHERE id = ?", (recommendation_id,)
    )
    row = await cursor.fetchone()
    return _row_to_recommendation(row)
