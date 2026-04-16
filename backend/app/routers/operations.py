# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: azz093093.830330@gmail.com

"""Operations CRUD endpoints."""

import json
import uuid
from datetime import datetime, timezone

import asyncpg
from fastapi import APIRouter, Depends, HTTPException

from app.database import get_db
from app.models import C5ISRStatus, Operation, OrientRecommendation
from app.models.api_schemas import (
    OperationCreate,
    OperationSummary,
    OperationUpdate,
)
from app.models.recommendation import TacticalOption
from app.config import settings
from app.services.mission_profile_loader import get_all_profiles, get_profile

router = APIRouter()


def _row_to_operation(row: asyncpg.Record) -> Operation:
    """Convert a DB row to an Operation model."""
    return Operation(
        id=row["id"],
        code=row["code"],
        name=row["name"],
        codename=row["codename"],
        strategic_intent=row["strategic_intent"],
        status=row["status"],
        current_ooda_phase=row["current_ooda_phase"],
        ooda_iteration_count=row["ooda_iteration_count"],
        threat_level=row["threat_level"],
        success_rate=row["success_rate"],
        techniques_executed=row["techniques_executed"],
        techniques_total=row["techniques_total"],
        active_agents=row["active_agents"],
        data_exfiltrated_bytes=row["data_exfiltrated_bytes"],
        automation_mode=row["automation_mode"],
        risk_threshold=row["risk_threshold"],
        mission_profile=row.get("mission_profile", "SP") or "SP",
        operator_id=row["operator_id"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


@router.get("/operations", response_model=list[Operation])


async def list_operations(db: asyncpg.Connection = Depends(get_db)):
    rows = await db.fetch("SELECT * FROM operations ORDER BY created_at DESC")
    return [_row_to_operation(r) for r in rows]


@router.post("/operations", response_model=Operation, status_code=201)


async def create_operation(
    body: OperationCreate,
    db: asyncpg.Connection = Depends(get_db),
):
    op_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    await db.execute(
        "INSERT INTO operations "
        "(id, code, name, codename, strategic_intent, mission_profile, "
        "risk_threshold, status, current_ooda_phase, created_at, updated_at) "
        "VALUES ($1, $2, $3, $4, $5, $6, $7, 'planning', 'observe', $8, $9)",
        op_id, body.code, body.name, body.codename, body.strategic_intent,
        body.mission_profile.value, settings.RISK_THRESHOLD, now, now,
    )

    row = await db.fetchrow("SELECT * FROM operations WHERE id = $1", op_id)
    return _row_to_operation(row)


@router.get("/operations/{operation_id}", response_model=Operation)


async def get_operation(
    operation_id: str,
    db: asyncpg.Connection = Depends(get_db),
):
    row = await db.fetchrow("SELECT * FROM operations WHERE id = $1", operation_id)
    if not row:
        raise HTTPException(status_code=404, detail="Operation not found")
    return _row_to_operation(row)


@router.patch("/operations/{operation_id}", response_model=Operation)


async def update_operation(
    operation_id: str,
    body: OperationUpdate,
    db: asyncpg.Connection = Depends(get_db),
):
    # Verify existence
    row = await db.fetchrow("SELECT id FROM operations WHERE id = $1", operation_id)
    if not row:
        raise HTTPException(status_code=404, detail="Operation not found")

    updates = body.model_dump(exclude_none=True)
    if not updates:
        # Nothing to update, just return current
        row = await db.fetchrow("SELECT * FROM operations WHERE id = $1", operation_id)
        return _row_to_operation(row)

    now = datetime.now(timezone.utc)
    updates["updated_at"] = now

    set_clause = ", ".join(f"{k} = ${i+1}" for i, k in enumerate(updates))
    values = [v.value if hasattr(v, "value") else v for v in updates.values()]
    values.append(operation_id)

    await db.execute(
        f"UPDATE operations SET {set_clause} WHERE id = ${len(values)}",
        *values,
    )

    row = await db.fetchrow("SELECT * FROM operations WHERE id = $1", operation_id)
    return _row_to_operation(row)


@router.get("/operations/{operation_id}/summary", response_model=OperationSummary)


async def get_operation_summary(
    operation_id: str,
    db: asyncpg.Connection = Depends(get_db),
):

    # Operation
    op_row = await db.fetchrow("SELECT * FROM operations WHERE id = $1", operation_id)
    if not op_row:
        raise HTTPException(status_code=404, detail="Operation not found")
    operation = _row_to_operation(op_row)

    # C5ISR statuses
    c5_rows = await db.fetch(
        "SELECT * FROM c5isr_statuses WHERE operation_id = $1", operation_id
    )
    c5isr = [
        C5ISRStatus(
            id=r["id"],
            operation_id=r["operation_id"],
            domain=r["domain"],
            status=r["status"],
            health_pct=r["health_pct"],
            detail=r["detail"],
        )
        for r in c5_rows
    ]

    # Latest recommendation
    rec_row = await db.fetchrow(
        "SELECT * FROM recommendations WHERE operation_id = $1 "
        "ORDER BY created_at DESC LIMIT 1",
        operation_id,
    )
    latest_rec = None
    if rec_row:
        options_raw = json.loads(rec_row["options"]) if rec_row["options"] else []
        latest_rec = OrientRecommendation(
            id=rec_row["id"],
            operation_id=rec_row["operation_id"],
            ooda_iteration_id=rec_row["ooda_iteration_id"],
            situation_assessment=rec_row["situation_assessment"],
            recommended_technique_id=rec_row["recommended_technique_id"],
            confidence=rec_row["confidence"],
            options=[TacticalOption(**o) for o in options_raw],
            reasoning_text=rec_row["reasoning_text"],
            accepted=bool(rec_row["accepted"]) if rec_row["accepted"] is not None else None,
            created_at=rec_row["created_at"],
        )

    return OperationSummary(
        operation=operation,
        c5isr=c5isr,
        latest_recommendation=latest_rec,
    )


@router.get("/mission-profiles")


async def list_mission_profiles():
    """Return all available mission profile definitions (SR/CO/SP/FA)."""
    return get_all_profiles()


@router.get("/mission-profiles/{code}")


async def get_mission_profile(code: str):
    """Return a single mission profile by code."""
    profile = get_profile(code)
    return {"code": code, **profile}
