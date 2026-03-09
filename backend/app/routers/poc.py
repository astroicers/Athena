"""PoC report API endpoint."""
import json
from fastapi import APIRouter, Depends, HTTPException
from app.database import get_db

router = APIRouter(tags=["PoC"])


@router.get("/api/operations/{operation_id}/poc")
async def get_poc_records(operation_id: str, db=Depends(get_db)):
    """Get all PoC records for an operation."""
    cursor = await db.execute(
        "SELECT id FROM operations WHERE id = ?", (operation_id,)
    )
    if not await cursor.fetchone():
        raise HTTPException(status_code=404, detail="Operation not found")

    cursor = await db.execute(
        "SELECT trait, value, source_target_id, collected_at "
        "FROM facts WHERE operation_id = ? AND trait LIKE 'poc.%' "
        "ORDER BY collected_at DESC",
        (operation_id,),
    )
    rows = await cursor.fetchall()

    poc_records = []
    for row in rows:
        try:
            val = row["value"] if isinstance(row, dict) else row[1]
            record = json.loads(val)
            poc_records.append(record)
        except (json.JSONDecodeError, IndexError):
            continue

    return {
        "operation_id": operation_id,
        "poc_records": poc_records,
        "total": len(poc_records),
    }
