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
    db.row_factory = aiosqlite.Row
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
    db.row_factory = aiosqlite.Row
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
    db.row_factory = aiosqlite.Row
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
    db.row_factory = aiosqlite.Row
    cursor = await db.execute(
        "SELECT * FROM technique_playbooks WHERE id = ?", (playbook_id,)
    )
    if not await cursor.fetchone():
        raise HTTPException(status_code=404, detail="Playbook not found")

    updates: dict = {}
    if body.command is not None:
        updates["command"] = body.command
    if body.output_parser is not None:
        updates["output_parser"] = body.output_parser
    if body.facts_traits is not None:
        updates["facts_traits"] = json.dumps(body.facts_traits)
    if body.tags is not None:
        updates["tags"] = json.dumps(body.tags)

    if updates:
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        await db.execute(
            f"UPDATE technique_playbooks SET {set_clause} WHERE id = ?",  # noqa: S608
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
    db.row_factory = aiosqlite.Row
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
