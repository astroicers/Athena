# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.

"""Mission objectives CRUD endpoints."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4

import asyncpg
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.database import get_db
from app.routers._deps import ensure_operation

router = APIRouter()


class ObjectiveCreate(BaseModel):
    objective: str
    category: str = "tactical"
    priority: int = 1


class ObjectiveUpdate(BaseModel):
    status: str | None = None
    evidence: dict | None = None


@router.get("/operations/{operation_id}/objectives")
async def list_objectives(
    operation_id: str,
    db: asyncpg.Connection = Depends(get_db),
):
    await ensure_operation(db, operation_id)
    rows = await db.fetch(
        """SELECT id, objective, category, priority, status, evidence, created_at, achieved_at
           FROM mission_objectives
           WHERE operation_id = $1
           ORDER BY priority, created_at""",
        operation_id,
    )
    return [dict(r) for r in rows]


@router.post("/operations/{operation_id}/objectives", status_code=201)
async def create_objective(
    operation_id: str,
    body: ObjectiveCreate,
    db: asyncpg.Connection = Depends(get_db),
):
    await ensure_operation(db, operation_id)
    obj_id = str(uuid4())
    await db.execute(
        """INSERT INTO mission_objectives (id, operation_id, objective, category, priority)
           VALUES ($1, $2, $3, $4, $5)""",
        obj_id, operation_id, body.objective, body.category, body.priority,
    )
    return {"id": obj_id, "status": "pending"}


@router.patch("/operations/{operation_id}/objectives/{objective_id}")
async def update_objective(
    operation_id: str,
    objective_id: str,
    body: ObjectiveUpdate,
    db: asyncpg.Connection = Depends(get_db),
):
    await ensure_operation(db, operation_id)
    row = await db.fetchrow(
        "SELECT id FROM mission_objectives WHERE id = $1 AND operation_id = $2",
        objective_id, operation_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Objective not found")

    updates = []
    params = []
    idx = 1

    if body.status is not None:
        idx += 1
        updates.append(f"status = ${idx}")
        params.append(body.status)
        if body.status == "achieved":
            idx += 1
            updates.append(f"achieved_at = ${idx}")
            params.append(datetime.now(timezone.utc))

    if body.evidence is not None:
        idx += 1
        updates.append(f"evidence = ${idx}")
        params.append(json.dumps(body.evidence))

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    sql = f"UPDATE mission_objectives SET {', '.join(updates)} WHERE id = $1"
    await db.execute(sql, objective_id, *params)

    return {"id": objective_id, "updated": True}
