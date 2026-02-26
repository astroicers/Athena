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

"""Agent endpoints."""

import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
import aiosqlite

from app.config import settings
from app.database import get_db
from app.models import Agent
from app.routers._deps import ensure_operation

logger = logging.getLogger(__name__)

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
    """Sync agents from Caldera into Athena's database."""
    db.row_factory = aiosqlite.Row
    await ensure_operation(db, operation_id)

    if settings.MOCK_CALDERA:
        return {"message": "Mock mode — using seed agents", "synced": 0}

    try:
        from app.clients.caldera_client import CalderaClient
        client = CalderaClient(settings.CALDERA_URL, settings.CALDERA_API_KEY)
        caldera_agents = await client.sync_agents(operation_id)
        await client.aclose()
    except Exception as e:
        logger.error("Failed to sync agents from Caldera: %s", e)
        return {"message": f"Caldera sync failed: {e}", "synced": 0}

    synced = 0
    for agent in caldera_agents:
        agent_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        await db.execute(
            """INSERT OR REPLACE INTO agents
               (id, paw, host_id, status, privilege, last_beacon,
                beacon_interval_sec, platform, operation_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                agent_id,
                agent.get("paw", ""),
                agent.get("host", "unknown"),
                agent.get("status", "alive"),
                agent.get("privilege", "User"),
                now,
                60,
                agent.get("platform", "unknown"),
                operation_id,
            ),
        )
        synced += 1

    await db.commit()
    logger.info("Synced %d agents from Caldera for operation %s", synced, operation_id)
    return {"synced": synced}
