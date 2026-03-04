# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: [TODO: contact email]

"""Engagement (Rules of Engagement) endpoints."""

import json
import logging
import uuid
from datetime import datetime, timezone

import aiosqlite
from fastapi import APIRouter, Depends, HTTPException

from app.database import get_db
from app.models.api_schemas import EngagementCreate
from app.models.engagement import Engagement
from app.routers._deps import ensure_operation

logger = logging.getLogger(__name__)
router = APIRouter()


def _row_to_engagement(row: aiosqlite.Row) -> Engagement:
    d = dict(row)
    d["in_scope"] = json.loads(d.get("in_scope") or "[]")
    d["out_of_scope"] = json.loads(d.get("out_of_scope") or "[]")
    return Engagement(**d)


@router.post(
    "/operations/{op_id}/engagement",
    response_model=Engagement,
    status_code=201,
)
async def create_engagement(
    op_id: str,
    body: EngagementCreate,
    db: aiosqlite.Connection = Depends(get_db),
) -> Engagement:
    """Create a Rules of Engagement record for an operation."""
    db.row_factory = aiosqlite.Row
    await ensure_operation(db, op_id)

    # Only one engagement per operation
    cursor = await db.execute(
        "SELECT id FROM engagements WHERE operation_id = ?", (op_id,)
    )
    if await cursor.fetchone():
        raise HTTPException(
            status_code=409,
            detail=f"An engagement already exists for operation '{op_id}'. Use PATCH to update.",
        )

    eng_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    await db.execute(
        """
        INSERT INTO engagements
            (id, operation_id, client_name, contact_email,
             in_scope, out_of_scope, start_time, end_time,
             emergency_contact, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'draft', ?)
        """,
        (
            eng_id, op_id,
            body.client_name, body.contact_email,
            json.dumps(body.in_scope),
            json.dumps(body.out_of_scope),
            body.start_time, body.end_time,
            body.emergency_contact,
            now,
        ),
    )
    await db.commit()

    cursor = await db.execute("SELECT * FROM engagements WHERE id = ?", (eng_id,))
    row = await cursor.fetchone()
    return _row_to_engagement(row)


@router.get("/operations/{op_id}/engagement", response_model=Engagement)
async def get_engagement(
    op_id: str,
    db: aiosqlite.Connection = Depends(get_db),
) -> Engagement:
    """Get the engagement/ROE for an operation."""
    db.row_factory = aiosqlite.Row
    await ensure_operation(db, op_id)

    cursor = await db.execute(
        "SELECT * FROM engagements WHERE operation_id = ? ORDER BY created_at DESC LIMIT 1",
        (op_id,),
    )
    row = await cursor.fetchone()
    if row is None:
        raise HTTPException(
            status_code=404,
            detail=f"No engagement found for operation '{op_id}'",
        )
    return _row_to_engagement(row)


@router.patch("/operations/{op_id}/engagement/activate", response_model=Engagement)
async def activate_engagement(
    op_id: str,
    db: aiosqlite.Connection = Depends(get_db),
) -> Engagement:
    """Activate an engagement (draft -> active). Enables scope enforcement."""
    db.row_factory = aiosqlite.Row
    await ensure_operation(db, op_id)

    cursor = await db.execute(
        "SELECT * FROM engagements WHERE operation_id = ? ORDER BY created_at DESC LIMIT 1",
        (op_id,),
    )
    row = await cursor.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail=f"No engagement for operation '{op_id}'")

    if row["status"] == "active":
        return _row_to_engagement(row)

    await db.execute(
        "UPDATE engagements SET status = 'active' WHERE id = ?",
        (row["id"],),
    )
    await db.commit()

    cursor = await db.execute("SELECT * FROM engagements WHERE id = ?", (row["id"],))
    return _row_to_engagement(await cursor.fetchone())


@router.patch("/operations/{op_id}/engagement/suspend", response_model=Engagement)
async def suspend_engagement(
    op_id: str,
    db: aiosqlite.Connection = Depends(get_db),
) -> Engagement:
    """Suspend an active engagement (emergency stop)."""
    db.row_factory = aiosqlite.Row
    await ensure_operation(db, op_id)

    cursor = await db.execute(
        "SELECT * FROM engagements WHERE operation_id = ? ORDER BY created_at DESC LIMIT 1",
        (op_id,),
    )
    row = await cursor.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail=f"No engagement for operation '{op_id}'")

    await db.execute(
        "UPDATE engagements SET status = 'suspended' WHERE id = ?",
        (row["id"],),
    )
    await db.commit()

    cursor = await db.execute("SELECT * FROM engagements WHERE id = ?", (row["id"],))
    return _row_to_engagement(await cursor.fetchone())
