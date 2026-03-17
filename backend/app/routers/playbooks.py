# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: azz093093.830330@gmail.com

"""Technique playbook knowledge base CRUD endpoints."""
import json
import logging
import uuid
from datetime import datetime, timezone

import asyncpg
from fastapi import APIRouter, Depends, HTTPException

from app.database import get_db
from app.models.playbook import (
    Playbook,
    PlaybookBulkCreate,
    PlaybookBulkResult,
    PlaybookCreate,
    PlaybookUpdate,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/playbooks", tags=["playbooks"])


def _row_to_playbook(row: asyncpg.Record) -> dict:
    return {
        "id": row["id"],
        "mitre_id": row["mitre_id"],
        "platform": row["platform"],
        "command": row["command"],
        "output_parser": row["output_parser"],
        "facts_traits": json.loads(row["facts_traits"] or "[]"),
        "source": row["source"],
        "tags": json.loads(row["tags"] or "[]"),
        "created_at": row["created_at"],
    }


@router.get("", response_model=list[Playbook])


async def list_playbooks(
    mitre_id: str | None = None,
    platform: str | None = None,
    db: asyncpg.Connection = Depends(get_db),
):
    """List all playbooks with optional filtering."""
    query = "SELECT * FROM technique_playbooks WHERE 1=1"
    params: list = []
    idx = 1
    if mitre_id:
        query += f" AND mitre_id = ${idx}"
        params.append(mitre_id)
        idx += 1
    if platform:
        query += f" AND platform = ${idx}"
        params.append(platform)
        idx += 1
    query += " ORDER BY created_at ASC"
    rows = await db.fetch(query, *params)
    return [_row_to_playbook(r) for r in rows]


@router.post("", response_model=Playbook, status_code=201)


async def create_playbook(
    body: PlaybookCreate,
    db: asyncpg.Connection = Depends(get_db),
):
    """Create a new playbook."""
    pb_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    await db.execute(
        """INSERT INTO technique_playbooks
           (id, mitre_id, platform, command, output_parser, facts_traits, source, tags, created_at)
           VALUES ($1, $2, $3, $4, $5, $6, 'user', $7, $8)""",
        pb_id,
        body.mitre_id,
        body.platform,
        body.command,
        body.output_parser,
        json.dumps(body.facts_traits),
        json.dumps(body.tags),
        now,
    )
    row = await db.fetchrow(
        "SELECT * FROM technique_playbooks WHERE id = $1", pb_id
    )
    return _row_to_playbook(row)


@router.post("/bulk", response_model=PlaybookBulkResult, status_code=200)


async def bulk_create_playbooks(
    body: PlaybookBulkCreate,
    db: asyncpg.Connection = Depends(get_db),
):
    """Bulk-import playbooks. Skips entries where (mitre_id, platform) already exists."""
    created = 0
    skipped = 0
    errors: list[str] = []

    for idx, pb in enumerate(body.playbooks):
        try:
            existing = await db.fetchrow(
                "SELECT id FROM technique_playbooks WHERE mitre_id = $1 AND platform = $2",
                pb.mitre_id, pb.platform,
            )
            if existing:
                skipped += 1
                continue
            pb_id = str(uuid.uuid4())
            now = datetime.now(timezone.utc)
            await db.execute(
                """INSERT INTO technique_playbooks
                   (id, mitre_id, platform, command, output_parser, facts_traits, source, tags, created_at)
                   VALUES ($1, $2, $3, $4, $5, $6, 'user', $7, $8)""",
                pb_id, pb.mitre_id, pb.platform, pb.command,
                pb.output_parser, json.dumps(pb.facts_traits),
                json.dumps(pb.tags), now,
            )
            created += 1
        except Exception as exc:
            errors.append(f"[{idx}] {pb.mitre_id}/{pb.platform}: {exc}")

    logger.info("Bulk import: created=%d skipped=%d errors=%d", created, skipped, len(errors))
    return PlaybookBulkResult(created=created, skipped=skipped, errors=errors)


@router.get("/{playbook_id}", response_model=Playbook)


async def get_playbook(
    playbook_id: str,
    db: asyncpg.Connection = Depends(get_db),
):
    """Get a specific playbook by ID."""
    row = await db.fetchrow(
        "SELECT * FROM technique_playbooks WHERE id = $1", playbook_id
    )
    if not row:
        raise HTTPException(status_code=404, detail="Playbook not found")
    return _row_to_playbook(row)


@router.patch("/{playbook_id}", response_model=Playbook)


async def update_playbook(
    playbook_id: str,
    body: PlaybookUpdate,
    db: asyncpg.Connection = Depends(get_db),
):
    """Update an existing playbook."""
    existing = await db.fetchrow(
        "SELECT * FROM technique_playbooks WHERE id = $1", playbook_id
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Playbook not found")

    updates: dict = {}
    for field, value in body.model_dump(exclude_unset=True).items():
        if field == "command" and value is None:
            # command is NOT NULL in DB — silently skip null values
            continue
        if field == "facts_traits":
            updates["facts_traits"] = json.dumps(value) if value is not None else "[]"
        elif field == "tags":
            updates["tags"] = json.dumps(value) if value is not None else "[]"
        else:
            updates[field] = value  # allow None through (clear output_parser etc.)

    if updates:
        set_clause = ", ".join(f"{k} = ${i+1}" for i, k in enumerate(updates))
        values = list(updates.values())
        values.append(playbook_id)
        await db.execute(  # noqa: S608
            f"UPDATE technique_playbooks SET {set_clause} WHERE id = ${len(values)}",
            *values,
        )

    row = await db.fetchrow(
        "SELECT * FROM technique_playbooks WHERE id = $1", playbook_id
    )
    return _row_to_playbook(row)


@router.delete("/{playbook_id}", status_code=204)


async def delete_playbook(
    playbook_id: str,
    db: asyncpg.Connection = Depends(get_db),
):
    """Delete a user-created playbook. Seed playbooks cannot be deleted."""
    row = await db.fetchrow(
        "SELECT source FROM technique_playbooks WHERE id = $1", playbook_id
    )
    if not row:
        raise HTTPException(status_code=404, detail="Playbook not found")
    if row["source"] == "seed":
        raise HTTPException(status_code=403, detail="Cannot delete seed playbooks")
    await db.execute(
        "DELETE FROM technique_playbooks WHERE id = $1", playbook_id
    )
