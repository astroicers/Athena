# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: [TODO: contact email]

"""Fact endpoints."""

import aiosqlite
from fastapi import APIRouter, Depends

from app.database import get_db
from app.models import Fact
from app.routers._deps import ensure_operation

router = APIRouter()


def _row_to_fact(row: aiosqlite.Row) -> Fact:
    return Fact(
        id=row["id"],
        trait=row["trait"],
        value=row["value"],
        category=row["category"],
        source_technique_id=row["source_technique_id"],
        source_target_id=row["source_target_id"],
        operation_id=row["operation_id"],
        score=row["score"],
        collected_at=row["collected_at"],
    )


@router.get("/operations/{operation_id}/facts", response_model=list[Fact])
async def list_facts(
    operation_id: str,
    db: aiosqlite.Connection = Depends(get_db),
):
    db.row_factory = aiosqlite.Row
    await ensure_operation(db, operation_id)

    cursor = await db.execute(
        "SELECT * FROM facts WHERE operation_id = ? ORDER BY collected_at DESC",
        (operation_id,),
    )
    rows = await cursor.fetchall()
    return [_row_to_fact(r) for r in rows]
