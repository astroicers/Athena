# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: azz093093.830330@gmail.com

"""Technique catalog and per-operation technique status endpoints."""

import asyncio
import json
import logging
import uuid

import asyncpg
from fastapi import APIRouter, Depends, HTTPException

from app.config import settings
from app.database import db_manager, get_db
from app.models import Technique
from app.models.api_schemas import AttackPathEntry, AttackPathResponse, TechniqueCreate, TechniqueWithStatus
from app.ws_manager import ws_manager

logger = logging.getLogger(__name__)

router = APIRouter()


def _row_to_technique(row: asyncpg.Record) -> Technique:
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
        c2_ability_id=row["c2_ability_id"],
        platforms=platforms,
    )


@router.get("/techniques", response_model=list[Technique])


async def list_techniques(db: asyncpg.Connection = Depends(get_db)):
    """Return the full static technique catalog."""
    rows = await db.fetch("SELECT * FROM techniques ORDER BY mitre_id")
    return [_row_to_technique(r) for r in rows]


@router.post("/techniques", status_code=201)


async def create_technique(
    body: TechniqueCreate,
    db: asyncpg.Connection = Depends(get_db),
):
    """Add a new MITRE ATT&CK technique."""
    tech_id = str(uuid.uuid4())
    await db.execute(
        "INSERT INTO techniques "
        "(id, mitre_id, name, tactic, tactic_id, description, "
        "kill_chain_stage, risk_level, c2_ability_id, platforms) "
        "VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)",
        tech_id,
        body.mitre_id,
        body.name,
        body.tactic,
        body.tactic_id,
        body.description,
        body.kill_chain_stage,
        body.risk_level,
        body.c2_ability_id,
        json.dumps(body.platforms),
    )
    row = await db.fetchrow("SELECT * FROM techniques WHERE id = $1", tech_id)
    return dict(row)


@router.post("/techniques/sync-c2", status_code=202)


async def sync_c2_abilities(
    db: asyncpg.Connection = Depends(get_db),  # noqa: ARG001  kept for DI consistency
):
    """Sync c2_ability_id from C2 engine's ability catalog -- returns 202 immediately."""
    _task = asyncio.create_task(_sync_techniques_background())
    _task.add_done_callback(
        lambda t: logger.warning("techniques/sync-c2 task cancelled")
        if t.cancelled() else None
    )
    return {"status": "sync_started"}


async def _sync_techniques_background() -> None:
    """Background: fetch C2 abilities, update technique c2_ability_id."""
    try:
        if settings.MOCK_C2_ENGINE:
            logger.info("techniques/sync-c2 mock mode -- no-op")
            return

        from app.clients.c2_client import C2EngineClient

        client = C2EngineClient(settings.C2_ENGINE_URL, settings.C2_ENGINE_API_KEY)
        abilities = await client.list_abilities()
        await client.aclose()

        if not abilities:
            logger.info("techniques/sync-c2: no abilities returned from C2 engine")
            return

        # Build mitre_id -> ability_id mapping
        mapping: dict[str, str] = {}
        for ab in abilities:
            tech_id = ab.get("technique_id") or ab.get("technique", {}).get(
                "attack_id", ""
            )
            ab_id = ab.get("ability_id") or ab.get("id", "")
            if tech_id and ab_id:
                mapping.setdefault(tech_id, ab_id)

        synced = 0
        async with db_manager.connection() as db:
            for mitre_id, ability_id in mapping.items():
                result = await db.execute(
                    "UPDATE techniques SET c2_ability_id = $1 "
                    "WHERE mitre_id = $2 AND (c2_ability_id IS NULL OR c2_ability_id = '')",
                    ability_id, mitre_id,
                )
                # asyncpg returns 'UPDATE N' string
                if result and result.split()[-1] != '0':
                    synced += 1

        logger.info(
            "techniques/sync-c2: synced=%d total_abilities=%d mapped=%d",
            synced, len(abilities), len(mapping),
        )
        # techniques/sync-c2 is a global endpoint (no op_id) --
        # WS broadcast requires an operation_id, so we log only.
    except Exception as exc:
        logger.exception("techniques/sync-c2 background failed: %s", exc)


@router.get(
    "/operations/{operation_id}/techniques",
    response_model=list[TechniqueWithStatus],
)


async def list_techniques_with_status(
    operation_id: str,
    db: asyncpg.Connection = Depends(get_db),
):
    """Techniques enriched with the latest execution status for an operation."""

    # Verify operation exists
    row = await db.fetchrow("SELECT id FROM operations WHERE id = $1", operation_id)
    if not row:
        raise HTTPException(status_code=404, detail="Operation not found")

    rows = await db.fetch(
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
            WHERE operation_id = $1
        ) te ON te.technique_id = t.id AND te.rn = 1
        ORDER BY t.mitre_id
        """,
        operation_id,
    )

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
                c2_ability_id=r["c2_ability_id"],
                platforms=platforms,
                latest_status=r["latest_status"],
                latest_execution_id=r["latest_execution_id"],
            )
        )
    return results


@router.get("/operations/{operation_id}/attack-path", response_model=AttackPathResponse)


async def get_attack_path(
    operation_id: str,
    db: asyncpg.Connection = Depends(get_db),
) -> AttackPathResponse:
    """Return full execution history for attack path timeline visualization."""
    from app.routers._deps import ensure_operation
    await ensure_operation(db, operation_id)

    rows = await db.fetch(
        """
        SELECT te.id           AS execution_id,
               te.status,
               te.engine,
               te.started_at,
               te.completed_at,
               te.result_summary,
               te.error_message,
               te.facts_collected_count,
               t.mitre_id,
               t.name          AS technique_name,
               t.tactic,
               t.tactic_id,
               t.kill_chain_stage,
               t.risk_level,
               tg.hostname     AS target_hostname,
               tg.ip_address   AS target_ip
        FROM technique_executions te
        JOIN techniques t  ON te.technique_id = t.id
        LEFT JOIN targets tg ON te.target_id = tg.id
        WHERE te.operation_id = $1
        ORDER BY te.started_at ASC NULLS LAST, te.created_at ASC
        """,
        operation_id,
    )

    # TACTIC_ORDER defines the 14 ATT&CK tactics left-to-right
    TACTIC_ORDER_IDS = [
        "TA0043", "TA0042", "TA0001", "TA0002", "TA0003", "TA0004", "TA0005",
        "TA0006", "TA0007", "TA0008", "TA0009", "TA0011", "TA0010", "TA0040",
    ]
    tactic_idx_map = {tid: i for i, tid in enumerate(TACTIC_ORDER_IDS)}

    entries = []
    highest_idx = -1
    tactic_coverage: dict[str, int] = {}

    for row in rows:
        r = dict(row)
        # compute duration
        duration_sec = None
        if r.get("started_at") and r.get("completed_at"):
            try:
                from datetime import datetime
                fmt = "%Y-%m-%dT%H:%M:%S.%f" if "." in r["started_at"] else "%Y-%m-%dT%H:%M:%S"
                t_start = (r["started_at"] if isinstance(r["started_at"], datetime) else datetime.fromisoformat(r["started_at"]))
                t_end = (r["completed_at"] if isinstance(r["completed_at"], datetime) else datetime.fromisoformat(r["completed_at"]))
                duration_sec = (t_end - t_start).total_seconds()
            except Exception:
                pass

        entry = AttackPathEntry(
            execution_id=r["execution_id"],
            mitre_id=r["mitre_id"] or "",
            technique_name=r["technique_name"] or "",
            tactic=r["tactic"] or "",
            tactic_id=r["tactic_id"] or "",
            kill_chain_stage=r["kill_chain_stage"] or "",
            risk_level=r["risk_level"] or "",
            status=r["status"] or "queued",
            engine=r["engine"] or "",
            started_at=r["started_at"].isoformat() if hasattr(r["started_at"], "isoformat") else r["started_at"],
            completed_at=r["completed_at"].isoformat() if hasattr(r["completed_at"], "isoformat") else r["completed_at"],
            duration_sec=duration_sec,
            result_summary=r["result_summary"],
            error_message=r["error_message"],
            facts_collected_count=r["facts_collected_count"] or 0,
            target_hostname=r["target_hostname"],
            target_ip=r["target_ip"],
        )
        entries.append(entry)

        # track highest tactic reached (any non-queued status)
        tid = r.get("tactic_id") or ""
        if r["status"] != "queued" and tid in tactic_idx_map:
            idx = tactic_idx_map[tid]
            if idx > highest_idx:
                highest_idx = idx

        # count successes per tactic
        if r["status"] == "success" and tid:
            tactic_coverage[tid] = tactic_coverage.get(tid, 0) + 1

    return AttackPathResponse(
        operation_id=operation_id,
        entries=entries,
        highest_tactic_idx=highest_idx,
        tactic_coverage=tactic_coverage,
    )
