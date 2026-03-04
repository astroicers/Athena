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

"""Target and topology endpoints."""

import uuid
from datetime import datetime, timezone

import aiosqlite
from fastapi import APIRouter, Depends, HTTPException
from starlette.responses import Response

from app.database import get_db
from app.models import Target
from app.models.api_schemas import (
    BatchImportResult,
    TargetBatchCreate,
    TargetCreate,
    TargetSetActive,
    TopologyData,
    TopologyEdge,
    TopologyNode,
)
from app.routers._deps import ensure_operation

router = APIRouter()


def _row_to_target(row: aiosqlite.Row) -> Target:
    return Target(
        id=row["id"],
        hostname=row["hostname"],
        ip_address=row["ip_address"],
        os=row["os"],
        role=row["role"],
        network_segment=row["network_segment"],
        is_compromised=bool(row["is_compromised"]),
        is_active=bool(row["is_active"]),
        privilege_level=row["privilege_level"],
        operation_id=row["operation_id"],
    )


@router.get("/operations/{operation_id}/targets", response_model=list[Target])
async def list_targets(
    operation_id: str,
    db: aiosqlite.Connection = Depends(get_db),
):
    db.row_factory = aiosqlite.Row
    await ensure_operation(db, operation_id)

    cursor = await db.execute(
        "SELECT * FROM targets WHERE operation_id = ? ORDER BY hostname",
        (operation_id,),
    )
    rows = await cursor.fetchall()
    return [_row_to_target(r) for r in rows]


@router.post("/operations/{operation_id}/targets", response_model=Target, status_code=201)
async def create_target(
    operation_id: str,
    body: TargetCreate,
    db: aiosqlite.Connection = Depends(get_db),
):
    """Add a target host to an operation."""
    db.row_factory = aiosqlite.Row
    await ensure_operation(db, operation_id)

    # Prevent duplicate IP within the same operation
    dup = await db.execute(
        "SELECT id FROM targets WHERE ip_address = ? AND operation_id = ?",
        (body.ip_address, operation_id),
    )
    if await dup.fetchone():
        raise HTTPException(
            status_code=409,
            detail=f"Target with IP {body.ip_address!r} already exists in this operation",
        )

    target_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    await db.execute(
        "INSERT INTO targets (id, hostname, ip_address, os, role, "
        "network_segment, is_compromised, privilege_level, operation_id, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, 0, NULL, ?, ?)",
        (target_id, body.hostname, body.ip_address, body.os, body.role,
         body.network_segment, operation_id, now),
    )
    await db.commit()
    cursor = await db.execute("SELECT * FROM targets WHERE id = ?", (target_id,))
    row = await cursor.fetchone()
    return _row_to_target(row)


@router.patch("/operations/{operation_id}/targets/active", response_model=list[Target])
async def set_active_target(
    operation_id: str,
    body: TargetSetActive,
    db: aiosqlite.Connection = Depends(get_db),
):
    """Set (or clear) the active target for an operation."""
    db.row_factory = aiosqlite.Row
    await ensure_operation(db, operation_id)

    # Clear all active flags for this operation
    await db.execute(
        "UPDATE targets SET is_active = 0 WHERE operation_id = ?",
        (operation_id,),
    )

    if body.target_id:
        # Verify target exists in this operation
        cursor = await db.execute(
            "SELECT id FROM targets WHERE id = ? AND operation_id = ?",
            (body.target_id, operation_id),
        )
        if not await cursor.fetchone():
            raise HTTPException(status_code=404, detail="Target not found")
        await db.execute(
            "UPDATE targets SET is_active = 1 WHERE id = ?",
            (body.target_id,),
        )

    await db.commit()

    # Return updated list
    cursor = await db.execute(
        "SELECT * FROM targets WHERE operation_id = ? ORDER BY hostname",
        (operation_id,),
    )
    rows = await cursor.fetchall()
    return [_row_to_target(r) for r in rows]


@router.post(
    "/operations/{operation_id}/targets/batch",
    response_model=BatchImportResult,
    status_code=201,
)
async def batch_create_targets(
    operation_id: str,
    body: TargetBatchCreate,
    db: aiosqlite.Connection = Depends(get_db),
):
    """Batch-import targets into an operation, skipping duplicates."""
    db.row_factory = aiosqlite.Row
    await ensure_operation(db, operation_id)

    if len(body.entries) > 512:
        raise HTTPException(status_code=400, detail="Maximum 512 entries per batch")

    created: list[str] = []
    skipped_duplicates: list[str] = []

    for entry in body.entries:
        # Check duplicate IP within this operation
        dup = await db.execute(
            "SELECT id FROM targets WHERE ip_address = ? AND operation_id = ?",
            (entry.ip_address, operation_id),
        )
        if await dup.fetchone():
            skipped_duplicates.append(entry.ip_address)
            continue

        target_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        await db.execute(
            "INSERT INTO targets (id, hostname, ip_address, os, role, "
            "network_segment, is_compromised, privilege_level, operation_id, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, 0, NULL, ?, ?)",
            (
                target_id,
                entry.hostname,
                entry.ip_address,
                entry.os or body.os,
                entry.role or body.role,
                entry.network_segment or body.network_segment,
                operation_id,
                now,
            ),
        )
        created.append(target_id)

    await db.commit()

    return BatchImportResult(
        created=created,
        skipped_duplicates=skipped_duplicates,
        total_requested=len(body.entries),
        total_created=len(created),
    )


@router.delete("/operations/{operation_id}/targets/{target_id}", status_code=204)
async def delete_target(
    operation_id: str,
    target_id: str,
    db: aiosqlite.Connection = Depends(get_db),
):
    """Remove a target from an operation."""
    db.row_factory = aiosqlite.Row
    await ensure_operation(db, operation_id)
    cursor = await db.execute(
        "SELECT id, is_active FROM targets WHERE id = ? AND operation_id = ?",
        (target_id, operation_id),
    )
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Target not found")
    if row["is_active"]:
        raise HTTPException(
            status_code=409,
            detail="Cannot delete the active target. Deselect it first.",
        )
    # FK CASCADE will handle agents referencing this target
    await db.execute("DELETE FROM targets WHERE id = ?", (target_id,))
    await db.commit()
    return Response(status_code=204)


@router.get("/operations/{operation_id}/topology", response_model=TopologyData)
async def get_topology(
    operation_id: str,
    db: aiosqlite.Connection = Depends(get_db),
):
    """Build topology graph from targets and agents."""
    db.row_factory = aiosqlite.Row
    await ensure_operation(db, operation_id)

    # Targets → host nodes
    cursor = await db.execute(
        "SELECT * FROM targets WHERE operation_id = ?", (operation_id,)
    )
    target_rows = await cursor.fetchall()

    nodes: list[TopologyNode] = []
    for t in target_rows:
        nodes.append(
            TopologyNode(
                id=t["id"],
                label=f"{t['hostname']} ({t['ip_address']})",
                type="host",
                data={
                    "hostname": t["hostname"],
                    "ip_address": t["ip_address"],
                    "os": t["os"],
                    "role": t["role"],
                    "is_compromised": bool(t["is_compromised"]),
                    "is_active": bool(t["is_active"]),
                    "privilege_level": t["privilege_level"],
                },
            )
        )

    # Agents → agent nodes + edges to their host
    cursor = await db.execute(
        "SELECT * FROM agents WHERE operation_id = ?", (operation_id,)
    )
    agent_rows = await cursor.fetchall()

    edges: list[TopologyEdge] = []
    for a in agent_rows:
        nodes.append(
            TopologyNode(
                id=a["id"],
                label=a["paw"],
                type="agent",
                data={
                    "paw": a["paw"],
                    "status": a["status"],
                    "privilege": a["privilege"],
                    "platform": a["platform"],
                },
            )
        )
        edges.append(
            TopologyEdge(
                source=a["id"],
                target=a["host_id"],
                label=f"beacon ({a['status']})",
            )
        )

    return TopologyData(nodes=nodes, edges=edges)
