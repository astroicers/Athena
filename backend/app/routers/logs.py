# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: [TODO: contact email]

"""Log entry endpoints (paginated)."""

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Query

from app.database import get_db
from app.models import LogEntry
from app.models.api_schemas import PaginatedLogs

router = APIRouter()


def _row_to_log(row: asyncpg.Record) -> LogEntry:
    return LogEntry(
        id=row["id"],
        timestamp=row["timestamp"],
        severity=row["severity"],
        source=row["source"],
        message=row["message"],
        operation_id=row["operation_id"],
        technique_id=row["technique_id"],
    )


@router.get(
    "/operations/{operation_id}/logs",
    response_model=PaginatedLogs,
)


async def list_logs(
    operation_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: asyncpg.Connection = Depends(get_db),
):

    # Verify operation
    row = await db.fetchrow("SELECT id FROM operations WHERE id = $1", operation_id)
    if not row:
        raise HTTPException(status_code=404, detail="Operation not found")

    # Total count
    total = await db.fetchval(
        "SELECT COUNT(*) FROM log_entries WHERE operation_id = $1",
        operation_id,
    )

    # Paginated results
    offset = (page - 1) * page_size
    rows = await db.fetch(
        "SELECT * FROM log_entries WHERE operation_id = $1 "
        "ORDER BY timestamp DESC LIMIT $2 OFFSET $3",
        operation_id, page_size, offset,
    )

    return PaginatedLogs(
        items=[_row_to_log(r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
    )
