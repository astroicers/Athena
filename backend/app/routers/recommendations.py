# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: [TODO: contact email]

"""AI recommendation endpoints."""

import json
from datetime import datetime, timezone

import aiosqlite
from fastapi import APIRouter, Depends, HTTPException, Query

from app.database import get_db
from app.models import OrientRecommendation
from app.models.recommendation import TacticalOption
from app.routers._deps import ensure_operation

router = APIRouter()


def _row_to_recommendation(row: aiosqlite.Row) -> OrientRecommendation:
    options_raw = json.loads(row["options"]) if row["options"] else []
    return OrientRecommendation(
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


@router.get(
    "/operations/{operation_id}/recommendations/latest",
    response_model=OrientRecommendation | None,
)


async def get_latest_recommendation(
    operation_id: str,
    db: aiosqlite.Connection = Depends(get_db),
):
    await ensure_operation(db, operation_id)

    cursor = await db.execute(
        "SELECT * FROM recommendations WHERE operation_id = ? "
        "ORDER BY created_at DESC LIMIT 1",
        (operation_id,),
    )
    row = await cursor.fetchone()
    if not row:
        return None
    return _row_to_recommendation(row)


@router.get(
    "/operations/{operation_id}/recommendations",
    response_model=list[OrientRecommendation],
)


async def list_recommendations(
    operation_id: str,
    limit: int = Query(20, ge=1, le=100),
    db: aiosqlite.Connection = Depends(get_db),
):
    """List all past recommendations for an operation, newest first."""
    await ensure_operation(db, operation_id)

    cursor = await db.execute(
        "SELECT * FROM recommendations WHERE operation_id = ? "
        "ORDER BY created_at DESC LIMIT ?",
        (operation_id, limit),
    )
    rows = await cursor.fetchall()
    return [_row_to_recommendation(r) for r in rows]


@router.post(
    "/operations/{operation_id}/recommendations/{recommendation_id}/accept",
    response_model=OrientRecommendation,
)


async def accept_recommendation(
    operation_id: str,
    recommendation_id: str,
    db: aiosqlite.Connection = Depends(get_db),
):
    await ensure_operation(db, operation_id)

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
