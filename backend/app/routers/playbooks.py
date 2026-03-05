# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: [TODO: contact email]

"""Technique playbook knowledge base CRUD endpoints."""
import json
import logging
import uuid
from datetime import datetime, timezone

import aiosqlite
from fastapi import APIRouter, Depends, HTTPException

from app.database import get_db
from app.models.playbook import Playbook, PlaybookCreate, PlaybookUpdate

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/playbooks", tags=["playbooks"])


def _row_to_playbook(row: aiosqlite.Row) -> dict:
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
    db: aiosqlite.Connection = Depends(get_db),
):
    """List all playbooks with optional filtering."""
    query = "SELECT * FROM technique_playbooks WHERE 1=1"
    params: list = []
    if mitre_id:
        query += " AND mitre_id = ?"
        params.append(mitre_id)
    if platform:
        query += " AND platform = ?"
        params.append(platform)
    query += " ORDER BY created_at ASC"
    cursor = await db.execute(query, params)
    rows = await cursor.fetchall()
    return [_row_to_playbook(r) for r in rows]


@router.post("", response_model=Playbook, status_code=201)


async def create_playbook(
    body: PlaybookCreate,
    db: aiosqlite.Connection = Depends(get_db),
):
    """Create a new playbook."""
    pb_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    await db.execute(
        """INSERT INTO technique_playbooks
           (id, mitre_id, platform, command, output_parser, facts_traits, source, tags, created_at)
           VALUES (?, ?, ?, ?, ?, ?, 'user', ?, ?)""",
        (
            pb_id,
            body.mitre_id,
            body.platform,
            body.command,
            body.output_parser,
            json.dumps(body.facts_traits),
            json.dumps(body.tags),
            now,
        ),
    )
    await db.commit()
    cursor = await db.execute(
        "SELECT * FROM technique_playbooks WHERE id = ?", (pb_id,)
    )
    return _row_to_playbook(await cursor.fetchone())


@router.get("/{playbook_id}", response_model=Playbook)


async def get_playbook(
    playbook_id: str,
    db: aiosqlite.Connection = Depends(get_db),
):
    """Get a specific playbook by ID."""
    cursor = await db.execute(
        "SELECT * FROM technique_playbooks WHERE id = ?", (playbook_id,)
    )
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Playbook not found")
    return _row_to_playbook(row)


@router.patch("/{playbook_id}", response_model=Playbook)


async def update_playbook(
    playbook_id: str,
    body: PlaybookUpdate,
    db: aiosqlite.Connection = Depends(get_db),
):
    """Update an existing playbook."""
    cursor = await db.execute(
        "SELECT * FROM technique_playbooks WHERE id = ?", (playbook_id,)
    )
    if not await cursor.fetchone():
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
            updates[field] = value  # 允許 None 通過（清空 output_parser 等欄位）

    if updates:
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        await db.execute(  # noqa: S608
            f"UPDATE technique_playbooks SET {set_clause} WHERE id = ?",
            (*updates.values(), playbook_id),
        )
        await db.commit()

    cursor = await db.execute(
        "SELECT * FROM technique_playbooks WHERE id = ?", (playbook_id,)
    )
    return _row_to_playbook(await cursor.fetchone())


@router.delete("/{playbook_id}", status_code=204)


async def delete_playbook(
    playbook_id: str,
    db: aiosqlite.Connection = Depends(get_db),
):
    """Delete a user-created playbook. Seed playbooks cannot be deleted."""
    cursor = await db.execute(
        "SELECT source FROM technique_playbooks WHERE id = ?", (playbook_id,)
    )
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Playbook not found")
    if row["source"] == "seed":
        raise HTTPException(status_code=403, detail="Cannot delete seed playbooks")
    await db.execute(
        "DELETE FROM technique_playbooks WHERE id = ?", (playbook_id,)
    )
    await db.commit()
