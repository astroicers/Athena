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

"""C5ISR domain status endpoints."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
import aiosqlite

from app.database import get_db
from app.models import C5ISRStatus
from app.models.api_schemas import C5ISRUpdate
from app.models.enums import C5ISRDomain
from app.routers._deps import ensure_operation

router = APIRouter()


def _row_to_c5isr(row: aiosqlite.Row) -> C5ISRStatus:
    return C5ISRStatus(
        id=row["id"],
        operation_id=row["operation_id"],
        domain=row["domain"],
        status=row["status"],
        health_pct=row["health_pct"],
        detail=row["detail"],
    )


@router.get(
    "/operations/{operation_id}/c5isr",
    response_model=list[C5ISRStatus],
)
async def list_c5isr(
    operation_id: str,
    db: aiosqlite.Connection = Depends(get_db),
):
    db.row_factory = aiosqlite.Row
    await ensure_operation(db, operation_id)

    cursor = await db.execute(
        "SELECT * FROM c5isr_statuses WHERE operation_id = ?", (operation_id,)
    )
    rows = await cursor.fetchall()
    return [_row_to_c5isr(r) for r in rows]


@router.patch(
    "/operations/{operation_id}/c5isr/{domain}",
    response_model=C5ISRStatus,
)
async def update_c5isr(
    operation_id: str,
    domain: str,
    body: C5ISRUpdate,
    db: aiosqlite.Connection = Depends(get_db),
):
    db.row_factory = aiosqlite.Row
    await ensure_operation(db, operation_id)

    # Validate domain
    valid_domains = {d.value for d in C5ISRDomain}
    if domain not in valid_domains:
        raise HTTPException(status_code=400, detail="Invalid domain")

    cursor = await db.execute(
        "SELECT * FROM c5isr_statuses WHERE operation_id = ? AND domain = ?",
        (operation_id, domain),
    )
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="C5ISR status not found for domain")

    updates = body.model_dump(exclude_none=True)
    if not updates:
        return _row_to_c5isr(row)

    now = datetime.now(timezone.utc).isoformat()
    updates["updated_at"] = now

    # Serialize enum values
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = [v.value if hasattr(v, "value") else v for v in updates.values()]
    values.extend([operation_id, domain])

    await db.execute(
        f"UPDATE c5isr_statuses SET {set_clause} "
        "WHERE operation_id = ? AND domain = ?",
        values,
    )
    await db.commit()

    cursor = await db.execute(
        "SELECT * FROM c5isr_statuses WHERE operation_id = ? AND domain = ?",
        (operation_id, domain),
    )
    row = await cursor.fetchone()
    return _row_to_c5isr(row)
