"""PoC report API endpoint."""
import json
from fastapi import APIRouter, Depends, HTTPException
from app.database import get_db

router = APIRouter(tags=["PoC"])


@router.get("/api/operations/{operation_id}/poc")
async def get_poc_records(operation_id: str, db=Depends(get_db)):
    """Get all PoC records for an operation."""
    row = await db.fetchrow(
        "SELECT id FROM operations WHERE id = $1", operation_id
    )
    if not row:
        raise HTTPException(status_code=404, detail="Operation not found")

    rows = await db.fetch(
        "SELECT trait, value, source_target_id, collected_at "
        "FROM facts WHERE operation_id = $1 AND trait LIKE 'poc.%' "
        "ORDER BY collected_at DESC",
        operation_id,
    )

    poc_records = []
    for r in rows:
        try:
            val = r["value"]
            record = json.loads(val)
            poc_records.append(record)
        except (json.JSONDecodeError, IndexError):
            continue

    # Enrich with technique_name and engine from related tables
    technique_ids = {r.get("technique_id") for r in poc_records if r.get("technique_id")}
    technique_names: dict[str, str] = {}
    technique_engines: dict[str, str] = {}
    if technique_ids:
        placeholders = ", ".join(f"${i+1}" for i in range(len(technique_ids)))
        tid_list = list(technique_ids)
        name_rows = await db.fetch(
            f"SELECT mitre_id, name FROM techniques WHERE mitre_id IN ({placeholders})",
            *tid_list,
        )
        technique_names = {r["mitre_id"]: r["name"] for r in name_rows}
        engine_rows = await db.fetch(
            f"SELECT DISTINCT ON (technique_id) technique_id, engine "
            f"FROM technique_executions WHERE technique_id IN ({placeholders}) "
            f"AND operation_id = ${len(tid_list)+1} "
            f"ORDER BY technique_id, started_at DESC",
            *tid_list, operation_id,
        )
        technique_engines = {r["technique_id"]: r["engine"] for r in engine_rows}

    for record in poc_records:
        tid = record.get("technique_id", "")
        if "technique_name" not in record:
            record["technique_name"] = technique_names.get(tid, tid)
        if "engine" not in record:
            record["engine"] = technique_engines.get(tid, "unknown")

    return {
        "operation_id": operation_id,
        "poc_records": poc_records,
        "total": len(poc_records),
    }
