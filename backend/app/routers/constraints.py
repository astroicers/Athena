# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.

"""Constraint override endpoints for C5ISR reverse influence."""

from __future__ import annotations

import json
from uuid import uuid4

import asyncpg
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.database import get_db
from app.routers._deps import ensure_operation
from app.services import constraint_engine

router = APIRouter()


class OverrideRequest(BaseModel):
    domain: str


@router.get("/operations/{operation_id}/constraints")
async def get_constraints(
    operation_id: str,
    db: asyncpg.Connection = Depends(get_db),
):
    """Return current operational constraints for the operation."""
    await ensure_operation(db, operation_id)
    # Get mission profile
    row = await db.fetchrow(
        "SELECT mission_profile FROM operations WHERE id = $1", operation_id,
    )
    mission_code = row["mission_profile"] if row and row["mission_profile"] else "SP"
    constraints = await constraint_engine.evaluate(db, operation_id, mission_code)
    return constraints.model_dump()


@router.post("/operations/{operation_id}/constraints/override")
async def override_constraint(
    operation_id: str,
    body: OverrideRequest,
    db: asyncpg.Connection = Depends(get_db),
):
    """Override a domain constraint for one OODA cycle.

    The override is recorded in event_store and expires after ~10 minutes
    (checked by constraint_engine on next evaluation).
    """
    await ensure_operation(db, operation_id)

    valid_domains = {"command", "control", "comms", "computers", "cyber", "isr"}
    if body.domain not in valid_domains:
        raise HTTPException(status_code=400, detail=f"Invalid domain: {body.domain}")

    event_id = str(uuid4())
    await db.execute(
        """INSERT INTO event_store (id, operation_id, event_type, payload, actor)
           VALUES ($1, $2, 'constraint.override', $3, 'commander')""",
        event_id, operation_id, json.dumps({"domain": body.domain}),
    )

    return {
        "status": "overridden",
        "domain": body.domain,
        "event_id": event_id,
        "note": "Override active for one OODA cycle (re-evaluated next cycle)",
    }
