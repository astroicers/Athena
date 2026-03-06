# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: [TODO: contact email]

"""Target and topology endpoints."""

import json
import uuid
from datetime import datetime, timezone

import aiosqlite
from fastapi import APIRouter, Depends, HTTPException
from starlette.responses import Response

from app.database import get_db
from app.models import Target
from app.models.api_schemas import (
    BatchImportResult,
    NodeSummaryResponse,
    TargetBatchCreate,
    TargetCreate,
    TargetSetActive,
    TopologyData,
    TopologyEdge,
    TopologyNode,
)
from app.routers._deps import ensure_operation
from app.services.node_summarizer import get_node_summary

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


@router.get(
    "/operations/{operation_id}/targets/{target_id}/summary",
    response_model=NodeSummaryResponse,
)


async def get_target_summary(
    operation_id: str,
    target_id: str,
    force_refresh: bool = False,
    db: aiosqlite.Connection = Depends(get_db),
):
    """Generate AI tactical intelligence summary for a target node."""
    await ensure_operation(db, operation_id)

    result = await get_node_summary(db, operation_id, target_id, force_refresh)
    if result is None:
        raise HTTPException(status_code=404, detail="Target not found")
    return result


@router.get("/operations/{operation_id}/topology", response_model=TopologyData)


async def get_topology(
    operation_id: str,
    db: aiosqlite.Connection = Depends(get_db),
):
    """Build topology graph: Athena C2 centre + target hosts + state-aware edges."""
    await ensure_operation(db, operation_id)

    # ── Athena C2 centre node ──
    nodes: list[TopologyNode] = [
        TopologyNode(
            id="athena-c2",
            label="ATHENA",
            type="c2",
            data={"role": "c2", "is_compromised": False, "is_active": True},
        )
    ]

    # ── Targets → host nodes (deduplicate by ip_address) ──
    cursor = await db.execute(
        "SELECT * FROM targets WHERE operation_id = ?", (operation_id,)
    )
    target_rows = await cursor.fetchall()

    seen_ips: set[str] = set()
    target_ids: list[str] = []  # track for phase lookup
    for t in target_rows:
        ip = t["ip_address"]
        if ip in seen_ips:
            continue
        seen_ips.add(ip)
        target_ids.append(t["id"])
        nodes.append(
            TopologyNode(
                id=t["id"],
                label=f"{t['hostname']} ({ip})",
                type="host",
                data={
                    "hostname": t["hostname"],
                    "ip_address": ip,
                    "os": t["os"],
                    "role": t["role"],
                    "is_compromised": bool(t["is_compromised"]),
                    "is_active": bool(t["is_active"]),
                    "privilege_level": t["privilege_level"],
                },
            )
        )

    # ── Compute attack_phase + per-node stats and build Athena→host edges ──
    edges: list[TopologyEdge] = []

    for tid in target_ids:
        # Agent status (highest priority)
        cur = await db.execute(
            "SELECT paw, status, privilege FROM agents "
            "WHERE host_id = ? AND operation_id = ? ORDER BY last_beacon DESC LIMIT 1",
            (tid, operation_id),
        )
        agent = await cur.fetchone()

        # Technique execution status
        cur = await db.execute(
            "SELECT status FROM technique_executions "
            "WHERE target_id = ? AND operation_id = ? ORDER BY created_at DESC LIMIT 1",
            (tid, operation_id),
        )
        exec_row = await cur.fetchone()

        # Recon scan status
        cur = await db.execute(
            "SELECT status FROM recon_scans "
            "WHERE target_id = ? AND operation_id = ? ORDER BY started_at DESC LIMIT 1",
            (tid, operation_id),
        )
        scan_row = await cur.fetchone()

        # Per-node gamification stats
        stats_cur = await db.execute(
            """
            SELECT
                (SELECT COUNT(*) FROM recon_scans
                 WHERE target_id = ? AND operation_id = ?) AS scan_count,
                (SELECT COUNT(*) FROM facts
                 WHERE source_target_id = ? AND operation_id = ?) AS fact_count,
                (SELECT COUNT(*) FROM facts
                 WHERE source_target_id = ? AND operation_id = ?
                   AND trait LIKE 'credential.%') AS credential_count
            """,
            (tid, operation_id, tid, operation_id, tid, operation_id),
        )
        stats_row = await stats_cur.fetchone()
        scan_count = stats_row["scan_count"] if stats_row else 0
        fact_count = stats_row["fact_count"] if stats_row else 0
        credential_count = stats_row["credential_count"] if stats_row else 0

        # Open port count from latest completed scan
        port_cur = await db.execute(
            "SELECT open_ports FROM recon_scans "
            "WHERE target_id = ? AND operation_id = ? AND status = 'completed' "
            "ORDER BY completed_at DESC LIMIT 1",
            (tid, operation_id),
        )
        port_row = await port_cur.fetchone()
        open_port_count = 0
        if port_row and port_row["open_ports"]:
            try:
                open_port_count = len(json.loads(port_row["open_ports"]))
            except (ValueError, TypeError):
                pass

        # Persistence fact count
        persist_cur = await db.execute(
            "SELECT COUNT(*) AS cnt FROM facts "
            "WHERE source_target_id = ? AND operation_id = ? "
            "AND trait = 'host.persistence'",
            (tid, operation_id),
        )
        persist_row = await persist_cur.fetchone()
        persistence_count = persist_row["cnt"] if persist_row else 0

        # Determine phase (priority: session > attacking > scanning > attempted > idle)
        phase = "idle"
        edge_label = None

        if agent and agent["status"] == "alive":
            phase = "session"
            priv = agent["privilege"] or "user"
            edge_label = f"SSH ({priv})"
        elif exec_row and exec_row["status"] == "running":
            phase = "attacking"
            edge_label = "Attacking..."
        elif scan_row and scan_row["status"] == "running":
            phase = "scanning"
            edge_label = "Scanning..."
        elif exec_row or scan_row:
            phase = "attempted"
            edge_label = "Attempted"

        # Store phase + stats in the host node data
        for n in nodes:
            if n.id == tid:
                n.data["attack_phase"] = phase
                n.data["scanCount"] = scan_count
                n.data["factCount"] = fact_count
                n.data["credentialCount"] = credential_count
                n.data["openPortCount"] = open_port_count
                n.data["persistenceCount"] = persistence_count
                break

        # Build edge from Athena → host (only if not idle)
        if phase != "idle":
            edges.append(
                TopologyEdge(
                    source="athena-c2",
                    target=tid,
                    label=edge_label,
                    data={"phase": phase},
                )
            )

    # ── Lateral movement edges (host→host) ──────────────────────────────────
    lat_cursor = await db.execute(
        "SELECT DISTINCT f.source_target_id, a.host_id AS dest_tid "
        "FROM facts f "
        "JOIN agents a ON a.operation_id = f.operation_id "
        "  AND a.host_id != f.source_target_id AND a.status = 'alive' "
        "WHERE f.operation_id = ? "
        "  AND f.trait IN ('credential.ssh','credential.rdp','credential.winrm') "
        "  AND f.source_target_id IS NOT NULL",
        (operation_id,),
    )
    target_id_set = set(target_ids)
    for row in await lat_cursor.fetchall():
        src, dst = row["source_target_id"], row["dest_tid"]
        if src in target_id_set and dst in target_id_set:
            edges.append(
                TopologyEdge(
                    source=src, target=dst,
                    label="Lateral",
                    data={"phase": "lateral"},
                )
            )

    return TopologyData(nodes=nodes, edges=edges)
