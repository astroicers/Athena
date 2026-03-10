# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: [TODO: contact email]

"""C5ISR domain status endpoints."""

from datetime import datetime, timezone

import asyncpg
from fastapi import APIRouter, Depends, HTTPException

from app.database import get_db
from app.models import C5ISRStatus
from app.models.api_schemas import C5ISRUpdate
from app.models.enums import C5ISRDomain
from app.routers._deps import ensure_operation

router = APIRouter()


def _row_to_c5isr(row: asyncpg.Record) -> C5ISRStatus:
    keys = row.keys()
    return C5ISRStatus(
        id=row["id"],
        operation_id=row["operation_id"],
        domain=row["domain"],
        status=row["status"],
        health_pct=row["health_pct"],
        detail=row["detail"],
        numerator=row["numerator"] if "numerator" in keys else None,
        denominator=row["denominator"] if "denominator" in keys else None,
        metric_label=row["metric_label"] if "metric_label" in keys else "",
    )


@router.get(
    "/operations/{operation_id}/c5isr",
    response_model=list[C5ISRStatus],
)


async def list_c5isr(
    operation_id: str,
    db: asyncpg.Connection = Depends(get_db),
):
    await ensure_operation(db, operation_id)

    rows = await db.fetch(
        "SELECT * FROM c5isr_statuses WHERE operation_id = $1", operation_id
    )
    return [_row_to_c5isr(r) for r in rows]


@router.patch(
    "/operations/{operation_id}/c5isr/{domain}",
    response_model=C5ISRStatus,
)


async def update_c5isr(
    operation_id: str,
    domain: str,
    body: C5ISRUpdate,
    db: asyncpg.Connection = Depends(get_db),
):
    await ensure_operation(db, operation_id)

    # Validate domain
    valid_domains = {d.value for d in C5ISRDomain}
    if domain not in valid_domains:
        raise HTTPException(status_code=400, detail="Invalid domain")

    row = await db.fetchrow(
        "SELECT * FROM c5isr_statuses WHERE operation_id = $1 AND domain = $2",
        operation_id, domain,
    )
    if not row:
        raise HTTPException(status_code=404, detail="C5ISR status not found for domain")

    updates = body.model_dump(exclude_none=True)
    if not updates:
        return _row_to_c5isr(row)

    now = datetime.now(timezone.utc)
    updates["updated_at"] = now

    # Serialize enum values
    set_clause = ", ".join(f"{k} = ${i+1}" for i, k in enumerate(updates))
    values = [v.value if hasattr(v, "value") else v for v in updates.values()]
    values.extend([operation_id, domain])

    n = len(updates)
    await db.execute(
        f"UPDATE c5isr_statuses SET {set_clause} "
        f"WHERE operation_id = ${n+1} AND domain = ${n+2}",
        *values,
    )

    row = await db.fetchrow(
        "SELECT * FROM c5isr_statuses WHERE operation_id = $1 AND domain = $2",
        operation_id, domain,
    )
    return _row_to_c5isr(row)
