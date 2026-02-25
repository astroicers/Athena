"""C5ISR domain status endpoints."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import aiosqlite

from app.database import get_db
from app.models import C5ISRStatus
from app.models.enums import C5ISRDomain, C5ISRDomainStatus

router = APIRouter()


class C5ISRUpdate(BaseModel):
    status: C5ISRDomainStatus | None = None
    health_pct: float | None = None
    detail: str | None = None


def _row_to_c5isr(row: aiosqlite.Row) -> C5ISRStatus:
    return C5ISRStatus(
        id=row["id"],
        operation_id=row["operation_id"],
        domain=row["domain"],
        status=row["status"],
        health_pct=row["health_pct"],
        detail=row["detail"],
    )


async def _ensure_operation(db: aiosqlite.Connection, operation_id: str):
    cursor = await db.execute("SELECT id FROM operations WHERE id = ?", (operation_id,))
    if not await cursor.fetchone():
        raise HTTPException(status_code=404, detail="Operation not found")


@router.get(
    "/operations/{operation_id}/c5isr",
    response_model=list[C5ISRStatus],
)
async def list_c5isr(
    operation_id: str,
    db: aiosqlite.Connection = Depends(get_db),
):
    db.row_factory = aiosqlite.Row
    await _ensure_operation(db, operation_id)

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
    await _ensure_operation(db, operation_id)

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
