# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: azz093093.830330@gmail.com

"""Fact endpoints."""

import uuid
from datetime import datetime, timezone

import asyncpg
from fastapi import APIRouter, Depends

from app.database import get_db
from app.models import Fact
from app.models.api_schemas import FactCreate
from app.models.enums import FactCategory
from app.routers._deps import ensure_operation
from app.utils.enum_safety import safe_enum

router = APIRouter()


def _row_to_fact(row: asyncpg.Record) -> Fact:
    return Fact(
        id=row["id"],
        trait=row["trait"],
        value=row["value"],
        category=safe_enum(FactCategory, row["category"], log_name="FactCategory"),
        source_technique_id=row["source_technique_id"],
        source_target_id=row["source_target_id"],
        operation_id=row["operation_id"],
        score=row["score"],
        collected_at=row["collected_at"],
    )


@router.get("/operations/{operation_id}/facts", response_model=list[Fact])


async def list_facts(
    operation_id: str,
    target_id: str | None = None,
    db: asyncpg.Connection = Depends(get_db),
):
    await ensure_operation(db, operation_id)

    if target_id:
        rows = await db.fetch(
            "SELECT * FROM facts WHERE operation_id = $1 AND source_target_id = $2 "
            "ORDER BY collected_at DESC",
            operation_id, target_id,
        )
    else:
        rows = await db.fetch(
            "SELECT * FROM facts WHERE operation_id = $1 ORDER BY collected_at DESC",
            operation_id,
        )
    return [_row_to_fact(r) for r in rows]


@router.post("/operations/{operation_id}/facts", response_model=Fact, status_code=201)
async def create_fact(
    operation_id: str,
    body: FactCreate,
    db: asyncpg.Connection = Depends(get_db),
):
    """Manually inject an intelligence fact."""
    await ensure_operation(db, operation_id)
    fact_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    await db.execute(
        "INSERT INTO facts "
        "(id, trait, value, category, source_technique_id, "
        "source_target_id, operation_id, score, collected_at) "
        "VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)",
        fact_id, body.trait, body.value, body.category,
        body.source_technique_id, body.source_target_id,
        operation_id, body.score, now,
    )
    row = await db.fetchrow("SELECT * FROM facts WHERE id = $1", fact_id)
    return _row_to_fact(row)
