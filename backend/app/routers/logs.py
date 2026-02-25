"""Log entry endpoints (paginated)."""

from fastapi import APIRouter, Depends, HTTPException, Query
import aiosqlite

from app.database import get_db
from app.models import LogEntry
from app.models.api_schemas import PaginatedLogs

router = APIRouter()


def _row_to_log(row: aiosqlite.Row) -> LogEntry:
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
    db: aiosqlite.Connection = Depends(get_db),
):
    db.row_factory = aiosqlite.Row

    # Verify operation
    cursor = await db.execute("SELECT id FROM operations WHERE id = ?", (operation_id,))
    if not await cursor.fetchone():
        raise HTTPException(status_code=404, detail="Operation not found")

    # Total count
    cursor = await db.execute(
        "SELECT COUNT(*) AS cnt FROM log_entries WHERE operation_id = ?",
        (operation_id,),
    )
    total = (await cursor.fetchone())["cnt"]

    # Paginated results
    offset = (page - 1) * page_size
    cursor = await db.execute(
        "SELECT * FROM log_entries WHERE operation_id = ? "
        "ORDER BY timestamp DESC LIMIT ? OFFSET ?",
        (operation_id, page_size, offset),
    )
    rows = await cursor.fetchall()

    return PaginatedLogs(
        items=[_row_to_log(r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
    )
