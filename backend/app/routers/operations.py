# Copyright 2026 Athena Contributors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Operations CRUD endpoints."""

import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
import aiosqlite

from app.database import get_db
from app.models import Operation, C5ISRStatus, PentestGPTRecommendation
from app.models.api_schemas import (
    OperationCreate,
    OperationSummary,
    OperationUpdate,
)
from app.models.recommendation import TacticalOption

router = APIRouter()


def _row_to_operation(row: aiosqlite.Row) -> Operation:
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
        operator_id=row["operator_id"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


@router.get("/operations", response_model=list[Operation])
async def list_operations(db: aiosqlite.Connection = Depends(get_db)):
    db.row_factory = aiosqlite.Row
    cursor = await db.execute("SELECT * FROM operations ORDER BY created_at DESC")
    rows = await cursor.fetchall()
    return [_row_to_operation(r) for r in rows]


@router.post("/operations", response_model=Operation, status_code=201)
async def create_operation(
    body: OperationCreate,
    db: aiosqlite.Connection = Depends(get_db),
):
    op_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    await db.execute(
        "INSERT INTO operations "
        "(id, code, name, codename, strategic_intent, status, "
        "current_ooda_phase, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, 'planning', 'observe', ?, ?)",
        (op_id, body.code, body.name, body.codename, body.strategic_intent, now, now),
    )
    await db.commit()

    db.row_factory = aiosqlite.Row
    cursor = await db.execute("SELECT * FROM operations WHERE id = ?", (op_id,))
    row = await cursor.fetchone()
    return _row_to_operation(row)


@router.get("/operations/{operation_id}", response_model=Operation)
async def get_operation(
    operation_id: str,
    db: aiosqlite.Connection = Depends(get_db),
):
    db.row_factory = aiosqlite.Row
    cursor = await db.execute("SELECT * FROM operations WHERE id = ?", (operation_id,))
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Operation not found")
    return _row_to_operation(row)


@router.patch("/operations/{operation_id}", response_model=Operation)
async def update_operation(
    operation_id: str,
    body: OperationUpdate,
    db: aiosqlite.Connection = Depends(get_db),
):
    # Verify existence
    db.row_factory = aiosqlite.Row
    cursor = await db.execute("SELECT id FROM operations WHERE id = ?", (operation_id,))
    if not await cursor.fetchone():
        raise HTTPException(status_code=404, detail="Operation not found")

    updates = body.model_dump(exclude_none=True)
    if not updates:
        # Nothing to update, just return current
        cursor = await db.execute("SELECT * FROM operations WHERE id = ?", (operation_id,))
        row = await cursor.fetchone()
        return _row_to_operation(row)

    now = datetime.now(timezone.utc).isoformat()
    updates["updated_at"] = now

    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = [v.value if hasattr(v, "value") else v for v in updates.values()]
    values.append(operation_id)

    await db.execute(
        f"UPDATE operations SET {set_clause} WHERE id = ?",
        values,
    )
    await db.commit()

    cursor = await db.execute("SELECT * FROM operations WHERE id = ?", (operation_id,))
    row = await cursor.fetchone()
    return _row_to_operation(row)


@router.get("/operations/{operation_id}/summary", response_model=OperationSummary)
async def get_operation_summary(
    operation_id: str,
    db: aiosqlite.Connection = Depends(get_db),
):
    db.row_factory = aiosqlite.Row

    # Operation
    cursor = await db.execute("SELECT * FROM operations WHERE id = ?", (operation_id,))
    op_row = await cursor.fetchone()
    if not op_row:
        raise HTTPException(status_code=404, detail="Operation not found")
    operation = _row_to_operation(op_row)

    # C5ISR statuses
    cursor = await db.execute(
        "SELECT * FROM c5isr_statuses WHERE operation_id = ?", (operation_id,)
    )
    c5_rows = await cursor.fetchall()
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
    cursor = await db.execute(
        "SELECT * FROM recommendations WHERE operation_id = ? "
        "ORDER BY created_at DESC LIMIT 1",
        (operation_id,),
    )
    rec_row = await cursor.fetchone()
    latest_rec = None
    if rec_row:
        options_raw = json.loads(rec_row["options"]) if rec_row["options"] else []
        latest_rec = PentestGPTRecommendation(
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
