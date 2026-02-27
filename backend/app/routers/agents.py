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

import aiosqlite
from fastapi import APIRouter, Depends

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

    # Load targets for this operation to match Caldera agents by host/IP
    cursor = await db.execute(
        "SELECT id, hostname, ip_address FROM targets WHERE operation_id = ?",
        (operation_id,),
    )
    target_rows = await cursor.fetchall()
    # Build lookup: hostname→target_id, ip→target_id
    target_by_host: dict[str, str] = {}
    for t in target_rows:
        if t["hostname"]:
            target_by_host[t["hostname"].lower()] = t["id"]
        if t["ip_address"]:
            target_by_host[t["ip_address"]] = t["id"]

    synced = 0
    skipped = 0
    for agent in caldera_agents:
        caldera_host = agent.get("host", "")
        # Match to Athena target by hostname or IP
        host_id = target_by_host.get(caldera_host.lower()) or target_by_host.get(caldera_host)
        if not host_id:
            logger.warning(
                "Caldera agent paw=%s host=%s — no matching target in operation %s, skipping",
                agent.get("paw"), caldera_host, operation_id,
            )
            skipped += 1
            continue

        paw = agent.get("paw", "")
        now = datetime.now(timezone.utc).isoformat()

        # Upsert by paw: check if agent with this paw already exists
        cursor = await db.execute(
            "SELECT id FROM agents WHERE paw = ? AND operation_id = ?",
            (paw, operation_id),
        )
        existing = await cursor.fetchone()

        if existing:
            await db.execute(
                "UPDATE agents SET host_id = ?, status = ?, privilege = ?, "
                "last_beacon = ?, platform = ? WHERE id = ?",
                (
                    host_id,
                    agent.get("status", "alive"),
                    agent.get("privilege", "User"),
                    now,
                    agent.get("platform", "unknown"),
                    existing["id"],
                ),
            )
        else:
            agent_id = str(uuid.uuid4())
            await db.execute(
                "INSERT INTO agents "
                "(id, paw, host_id, status, privilege, last_beacon, "
                "beacon_interval_sec, platform, operation_id) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    agent_id, paw, host_id,
                    agent.get("status", "alive"),
                    agent.get("privilege", "User"),
                    now, 60,
                    agent.get("platform", "unknown"),
                    operation_id,
                ),
            )
        synced += 1

    await db.commit()
    logger.info(
        "Synced %d agents from Caldera for operation %s (%d skipped — no matching target)",
        synced, operation_id, skipped,
    )
    return {"synced": synced, "skipped": skipped}
