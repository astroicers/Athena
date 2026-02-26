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

"""Technique catalog and per-operation technique status endpoints."""

import json

from fastapi import APIRouter, Depends, HTTPException
import aiosqlite

from app.database import get_db
from app.models import Technique
from app.models.api_schemas import TechniqueWithStatus

router = APIRouter()


def _row_to_technique(row: aiosqlite.Row) -> Technique:
    platforms_raw = row["platforms"]
    platforms = json.loads(platforms_raw) if platforms_raw else []
    return Technique(
        id=row["id"],
        mitre_id=row["mitre_id"],
        name=row["name"],
        tactic=row["tactic"],
        tactic_id=row["tactic_id"],
        description=row["description"],
        kill_chain_stage=row["kill_chain_stage"],
        risk_level=row["risk_level"],
        caldera_ability_id=row["caldera_ability_id"],
        platforms=platforms,
    )


@router.get("/techniques", response_model=list[Technique])
async def list_techniques(db: aiosqlite.Connection = Depends(get_db)):
    """Return the full static technique catalog."""
    db.row_factory = aiosqlite.Row
    cursor = await db.execute("SELECT * FROM techniques ORDER BY mitre_id")
    rows = await cursor.fetchall()
    return [_row_to_technique(r) for r in rows]


@router.get(
    "/operations/{operation_id}/techniques",
    response_model=list[TechniqueWithStatus],
)
async def list_techniques_with_status(
    operation_id: str,
    db: aiosqlite.Connection = Depends(get_db),
):
    """Techniques enriched with the latest execution status for an operation."""
    db.row_factory = aiosqlite.Row

    # Verify operation exists
    cursor = await db.execute("SELECT id FROM operations WHERE id = ?", (operation_id,))
    if not await cursor.fetchone():
        raise HTTPException(status_code=404, detail="Operation not found")

    cursor = await db.execute(
        """
        SELECT t.*,
               te.status AS latest_status,
               te.id     AS latest_execution_id
        FROM techniques t
        LEFT JOIN (
            SELECT technique_id,
                   status,
                   id,
                   ROW_NUMBER() OVER (
                       PARTITION BY technique_id ORDER BY created_at DESC
                   ) AS rn
            FROM technique_executions
            WHERE operation_id = ?
        ) te ON te.technique_id = t.id AND te.rn = 1
        ORDER BY t.mitre_id
        """,
        (operation_id,),
    )
    rows = await cursor.fetchall()

    results = []
    for r in rows:
        platforms_raw = r["platforms"]
        platforms = json.loads(platforms_raw) if platforms_raw else []
        results.append(
            TechniqueWithStatus(
                id=r["id"],
                mitre_id=r["mitre_id"],
                name=r["name"],
                tactic=r["tactic"],
                tactic_id=r["tactic_id"],
                description=r["description"],
                kill_chain_stage=r["kill_chain_stage"],
                risk_level=r["risk_level"],
                caldera_ability_id=r["caldera_ability_id"],
                platforms=platforms,
                latest_status=r["latest_status"],
                latest_execution_id=r["latest_execution_id"],
            )
        )
    return results
