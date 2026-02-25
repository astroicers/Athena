"""Agent endpoints."""

from fastapi import APIRouter, Depends
import aiosqlite

from app.database import get_db
from app.models import Agent
from app.routers._deps import ensure_operation

router = APIRouter()


def _row_to_agent(row: aiosqlite.Row) -> Agent:
    return Agent(
        id=row["id"],
        paw=row["paw"],
        host_id=row["host_id"],
        status=row["status"],
        privilege=row["privilege"],
        last_beacon=row["last_beacon"],
        beacon_interval_sec=row["beacon_interval_sec"],
        platform=row["platform"],
        operation_id=row["operation_id"],
    )


@router.get("/operations/{operation_id}/agents", response_model=list[Agent])
async def list_agents(
    operation_id: str,
    db: aiosqlite.Connection = Depends(get_db),
):
    db.row_factory = aiosqlite.Row
    await ensure_operation(db, operation_id)

    cursor = await db.execute(
        "SELECT * FROM agents WHERE operation_id = ? ORDER BY paw",
        (operation_id,),
    )
    rows = await cursor.fetchall()
    return [_row_to_agent(r) for r in rows]


@router.post("/operations/{operation_id}/agents/sync")
async def sync_agents(
    operation_id: str,
    db: aiosqlite.Connection = Depends(get_db),
):
    """STUB — Sync agents from Caldera (not implemented in POC)."""
    db.row_factory = aiosqlite.Row
    await ensure_operation(db, operation_id)

    return {"message": "Sync not implemented (POC stub)", "synced": 0}
