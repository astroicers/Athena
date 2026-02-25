"""Shared dependencies for router modules."""

from fastapi import HTTPException
import aiosqlite


async def ensure_operation(db: aiosqlite.Connection, operation_id: str) -> None:
    """Raise 404 if *operation_id* does not exist."""
    cursor = await db.execute("SELECT id FROM operations WHERE id = ?", (operation_id,))
    if not await cursor.fetchone():
        raise HTTPException(status_code=404, detail="Operation not found")
