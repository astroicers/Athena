# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: [TODO: contact email]

"""Tool registry CRUD endpoints."""
import json
import logging
import uuid
from datetime import datetime, timezone

import aiosqlite
from fastapi import APIRouter, Depends, HTTPException, Request

from app.database import get_db
from app.models.tool_registry import (
    ToolRegistryCreate,
    ToolRegistryEntry,
    ToolRegistryUpdate,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/tools", tags=["Tools"])


def _row_to_tool(row: aiosqlite.Row) -> dict:
    return {
        "id": row["id"],
        "tool_id": row["tool_id"],
        "name": row["name"],
        "description": row["description"],
        "kind": row["kind"],
        "category": row["category"],
        "version": row["version"],
        "enabled": bool(row["enabled"]),
        "source": row["source"],
        "config_json": json.loads(row["config_json"] or "{}"),
        "mitre_techniques": json.loads(row["mitre_techniques"] or "[]"),
        "risk_level": row["risk_level"],
        "output_traits": json.loads(row["output_traits"] or "[]"),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


@router.get("", response_model=list[ToolRegistryEntry])
async def list_tools(
    kind: str | None = None,
    category: str | None = None,
    enabled: bool | None = None,
    db: aiosqlite.Connection = Depends(get_db),
):
    """List all tools with optional filtering by kind, category, enabled."""
    db.row_factory = aiosqlite.Row
    query = "SELECT * FROM tool_registry WHERE 1=1"
    params: list = []
    if kind:
        query += " AND kind = ?"
        params.append(kind)
    if category:
        query += " AND category = ?"
        params.append(category)
    if enabled is not None:
        query += " AND enabled = ?"
        params.append(int(enabled))
    query += " ORDER BY created_at ASC"
    cursor = await db.execute(query, params)
    rows = await cursor.fetchall()
    return [_row_to_tool(r) for r in rows]


@router.get("/{tool_id}", response_model=ToolRegistryEntry)
async def get_tool(
    tool_id: str,
    db: aiosqlite.Connection = Depends(get_db),
):
    """Get a specific tool by tool_id slug (NOT uuid)."""
    db.row_factory = aiosqlite.Row
    cursor = await db.execute(
        "SELECT * FROM tool_registry WHERE tool_id = ?", (tool_id,)
    )
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Tool not found")
    return _row_to_tool(row)


@router.post("", response_model=ToolRegistryEntry, status_code=201)
async def create_tool(
    body: ToolRegistryCreate,
    db: aiosqlite.Connection = Depends(get_db),
):
    """Create a new tool (source='user')."""
    db.row_factory = aiosqlite.Row

    # Check for duplicate tool_id
    cursor = await db.execute(
        "SELECT id FROM tool_registry WHERE tool_id = ?", (body.tool_id,)
    )
    if await cursor.fetchone():
        raise HTTPException(
            status_code=409, detail=f"Tool with tool_id '{body.tool_id}' already exists"
        )

    row_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    await db.execute(
        """INSERT INTO tool_registry
           (id, tool_id, name, description, kind, category, version,
            enabled, source, config_json, mitre_techniques, risk_level,
            output_traits, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'user', ?, ?, ?, ?, ?, ?)""",
        (
            row_id,
            body.tool_id,
            body.name,
            body.description,
            body.kind,
            body.category,
            body.version,
            int(body.enabled),
            json.dumps(body.config_json),
            json.dumps(body.mitre_techniques),
            body.risk_level,
            json.dumps(body.output_traits),
            now,
            now,
        ),
    )
    await db.commit()
    cursor = await db.execute(
        "SELECT * FROM tool_registry WHERE id = ?", (row_id,)
    )
    return _row_to_tool(await cursor.fetchone())


@router.patch("/{tool_id}", response_model=ToolRegistryEntry)
async def update_tool(
    tool_id: str,
    body: ToolRegistryUpdate,
    db: aiosqlite.Connection = Depends(get_db),
):
    """Update an existing tool. Cannot change tool_id, kind, or source."""
    db.row_factory = aiosqlite.Row
    cursor = await db.execute(
        "SELECT * FROM tool_registry WHERE tool_id = ?", (tool_id,)
    )
    existing = await cursor.fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Tool not found")

    updates: dict = {}
    for field, value in body.model_dump(exclude_unset=True).items():
        if field == "config_json":
            updates["config_json"] = json.dumps(value) if value is not None else "{}"
        elif field == "mitre_techniques":
            updates["mitre_techniques"] = json.dumps(value) if value is not None else "[]"
        elif field == "output_traits":
            updates["output_traits"] = json.dumps(value) if value is not None else "[]"
        elif field == "enabled":
            updates["enabled"] = int(value) if value is not None else 1
        else:
            updates[field] = value

    if updates:
        updates["updated_at"] = datetime.now(timezone.utc).isoformat()
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        await db.execute(  # noqa: S608
            f"UPDATE tool_registry SET {set_clause} WHERE tool_id = ?",
            (*updates.values(), tool_id),
        )
        await db.commit()

    cursor = await db.execute(
        "SELECT * FROM tool_registry WHERE tool_id = ?", (tool_id,)
    )
    return _row_to_tool(await cursor.fetchone())


@router.delete("/{tool_id}", status_code=204)
async def delete_tool(
    tool_id: str,
    db: aiosqlite.Connection = Depends(get_db),
):
    """Delete a user-created tool. Seed tools cannot be deleted (403)."""
    db.row_factory = aiosqlite.Row
    cursor = await db.execute(
        "SELECT source FROM tool_registry WHERE tool_id = ?", (tool_id,)
    )
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Tool not found")
    if row["source"] == "seed":
        raise HTTPException(status_code=403, detail="Cannot delete seed tools")
    await db.execute(
        "DELETE FROM tool_registry WHERE tool_id = ?", (tool_id,)
    )
    await db.commit()


@router.post("/{tool_id}/check")
async def check_tool(
    tool_id: str,
    request: Request,
    db: aiosqlite.Connection = Depends(get_db),
):
    """Health check — returns availability status for a tool.

    For MCP-backed tools (config_json.mcp_server), pings the MCP server.
    """
    db.row_factory = aiosqlite.Row
    cursor = await db.execute(
        "SELECT tool_id, name, enabled, config_json FROM tool_registry WHERE tool_id = ?",
        (tool_id,),
    )
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Tool not found")

    config = json.loads(row["config_json"] or "{}")
    mcp_server = config.get("mcp_server")

    if mcp_server and hasattr(request.app.state, "mcp_manager"):
        manager = request.app.state.mcp_manager
        is_healthy = await manager.health_check(mcp_server)
        return {
            "tool_id": row["tool_id"],
            "available": is_healthy,
            "detail": (
                f"{row['name']} MCP server '{mcp_server}' is "
                f"{'available' if is_healthy else 'unavailable'}"
            ),
        }

    return {
        "tool_id": row["tool_id"],
        "available": bool(row["enabled"]),
        "detail": f"{row['name']} is {'available' if row['enabled'] else 'disabled'}",
    }
