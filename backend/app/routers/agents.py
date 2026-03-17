# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: azz093093.830330@gmail.com

"""Agent endpoints."""

import asyncio
import logging
import uuid
from datetime import datetime, timezone

import asyncpg
from fastapi import APIRouter, Depends

from app.config import settings
from app.database import db_manager, get_db
from app.models import Agent
from app.routers._deps import ensure_operation
from app.ws_manager import ws_manager

logger = logging.getLogger(__name__)

router = APIRouter()


def _row_to_agent(row: asyncpg.Record) -> Agent:
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
    db: asyncpg.Connection = Depends(get_db),
):
    await ensure_operation(db, operation_id)

    rows = await db.fetch(
        "SELECT * FROM agents WHERE operation_id = $1 ORDER BY paw",
        operation_id,
    )
    return [_row_to_agent(r) for r in rows]


@router.post("/operations/{operation_id}/agents/sync", status_code=202)


async def sync_agents(
    operation_id: str,
    db: asyncpg.Connection = Depends(get_db),
):
    """Sync agents from C2 engine -- returns 202 immediately, executes in background."""
    await ensure_operation(db, operation_id)

    _task = asyncio.create_task(_sync_agents_background(operation_id))
    _task.add_done_callback(
        lambda t: logger.warning("agents/sync task cancelled for op %s", operation_id)
        if t.cancelled() else None
    )
    return {"status": "sync_started", "operation_id": operation_id}


async def _sync_agents_background(operation_id: str) -> None:
    """Background: sync agents from C2, upsert into DB, broadcast result."""
    try:
        if settings.MOCK_C2_ENGINE:
            logger.info("agents/sync mock mode for op %s -- no-op", operation_id)
            await ws_manager.broadcast(
                operation_id, "agents.synced",
                {"operation_id": operation_id, "synced": 0, "skipped": 0},
            )
            return

        from app.clients.c2_client import C2EngineClient
        client = C2EngineClient(settings.C2_ENGINE_URL, settings.C2_ENGINE_API_KEY)
        c2_agents = await client.sync_agents(operation_id)
        await client.aclose()

        async with db_manager.connection() as db:

            target_rows = await db.fetch(
                "SELECT id, hostname, ip_address FROM targets WHERE operation_id = $1",
                operation_id,
            )
            target_by_host: dict[str, str] = {}
            for t in target_rows:
                if t["hostname"]:
                    target_by_host[t["hostname"].lower()] = t["id"]
                if t["ip_address"]:
                    target_by_host[t["ip_address"]] = t["id"]

            synced = 0
            skipped = 0
            for agent in c2_agents:
                agent_host = agent.get("host", "")
                host_id = (
                    target_by_host.get(agent_host.lower())
                    or target_by_host.get(agent_host)
                )
                if not host_id:
                    logger.warning(
                        "C2 agent paw=%s host=%s -- no matching target in op %s, skipping",
                        agent.get("paw"), agent_host, operation_id,
                    )
                    skipped += 1
                    continue

                paw = agent.get("paw", "")
                now = datetime.now(timezone.utc)

                existing = await db.fetchrow(
                    "SELECT id FROM agents WHERE paw = $1 AND operation_id = $2",
                    paw, operation_id,
                )

                if existing:
                    await db.execute(
                        "UPDATE agents SET host_id = $1, status = $2, privilege = $3, "
                        "last_beacon = $4, platform = $5 WHERE id = $6",
                        host_id,
                        agent.get("status", "alive"),
                        agent.get("privilege", "User"),
                        now,
                        agent.get("platform", "unknown"),
                        existing["id"],
                    )
                else:
                    agent_id = str(uuid.uuid4())
                    await db.execute(
                        "INSERT INTO agents "
                        "(id, paw, host_id, status, privilege, last_beacon, "
                        "beacon_interval_sec, platform, operation_id) "
                        "VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)",
                        agent_id, paw, host_id,
                        agent.get("status", "alive"),
                        agent.get("privilege", "User"),
                        now, 60,
                        agent.get("platform", "unknown"),
                        operation_id,
                    )
                synced += 1

        logger.info(
            "Synced %d agents from C2 engine for op %s (%d skipped -- no matching target)",
            synced, operation_id, skipped,
        )
        await ws_manager.broadcast(
            operation_id, "agents.synced",
            {"operation_id": operation_id, "synced": synced, "skipped": skipped},
        )
    except Exception as exc:
        logger.exception("agents/sync background failed for op %s: %s", operation_id, exc)
        await ws_manager.broadcast(
            operation_id, "agents.sync_failed",
            {"operation_id": operation_id, "error": str(exc)},
        )
