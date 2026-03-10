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

import asyncpg
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


def _row_to_target(row: asyncpg.Record) -> Target:
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
    db: asyncpg.Connection = Depends(get_db),
):
    await ensure_operation(db, operation_id)

    rows = await db.fetch(
        "SELECT * FROM targets WHERE operation_id = $1 ORDER BY hostname",
        operation_id,
    )
    return [_row_to_target(r) for r in rows]


@router.post("/operations/{operation_id}/targets", response_model=Target, status_code=201)


async def create_target(
    operation_id: str,
    body: TargetCreate,
    db: asyncpg.Connection = Depends(get_db),
):
    """Add a target host to an operation."""
    await ensure_operation(db, operation_id)

    # Prevent duplicate IP within the same operation
    dup = await db.fetchrow(
        "SELECT id FROM targets WHERE ip_address = $1 AND operation_id = $2",
        body.ip_address, operation_id,
    )
    if dup:
        raise HTTPException(
            status_code=409,
            detail=f"Target with IP {body.ip_address!r} already exists in this operation",
        )

    target_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    await db.execute(
        "INSERT INTO targets (id, hostname, ip_address, os, role, "
        "network_segment, is_compromised, privilege_level, operation_id, created_at) "
        "VALUES ($1, $2, $3, $4, $5, $6, FALSE, NULL, $7, $8)",
        target_id, body.hostname, body.ip_address, body.os, body.role,
        body.network_segment, operation_id, now,
    )
    row = await db.fetchrow("SELECT * FROM targets WHERE id = $1", target_id)
    return _row_to_target(row)


@router.patch("/operations/{operation_id}/targets/active", response_model=list[Target])


async def set_active_target(
    operation_id: str,
    body: TargetSetActive,
    db: asyncpg.Connection = Depends(get_db),
):
    """Set (or clear) the active target for an operation."""
    await ensure_operation(db, operation_id)

    # Clear all active flags for this operation
    await db.execute(
        "UPDATE targets SET is_active = FALSE WHERE operation_id = $1",
        operation_id,
    )

    if body.target_id:
        # Verify target exists in this operation
        row = await db.fetchrow(
            "SELECT id FROM targets WHERE id = $1 AND operation_id = $2",
            body.target_id, operation_id,
        )
        if not row:
            raise HTTPException(status_code=404, detail="Target not found")
        await db.execute(
            "UPDATE targets SET is_active = TRUE WHERE id = $1",
            body.target_id,
        )

    # Return updated list
    rows = await db.fetch(
        "SELECT * FROM targets WHERE operation_id = $1 ORDER BY hostname",
        operation_id,
    )
    return [_row_to_target(r) for r in rows]


@router.post(
    "/operations/{operation_id}/targets/batch",
    response_model=BatchImportResult,
    status_code=201,
)


async def batch_create_targets(
    operation_id: str,
    body: TargetBatchCreate,
    db: asyncpg.Connection = Depends(get_db),
):
    """Batch-import targets into an operation, skipping duplicates."""
    await ensure_operation(db, operation_id)

    if len(body.entries) > 512:
        raise HTTPException(status_code=400, detail="Maximum 512 entries per batch")

    created: list[str] = []
    skipped_duplicates: list[str] = []

    for entry in body.entries:
        # Check duplicate IP within this operation
        dup = await db.fetchrow(
            "SELECT id FROM targets WHERE ip_address = $1 AND operation_id = $2",
            entry.ip_address, operation_id,
        )
        if dup:
            skipped_duplicates.append(entry.ip_address)
            continue

        target_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        await db.execute(
            "INSERT INTO targets (id, hostname, ip_address, os, role, "
            "network_segment, is_compromised, privilege_level, operation_id, created_at) "
            "VALUES ($1, $2, $3, $4, $5, $6, FALSE, NULL, $7, $8)",
            target_id,
            entry.hostname,
            entry.ip_address,
            entry.os or body.os,
            entry.role or body.role,
            entry.network_segment or body.network_segment,
            operation_id,
            now,
        )
        created.append(target_id)

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
    db: asyncpg.Connection = Depends(get_db),
):
    """Remove a target from an operation."""
    await ensure_operation(db, operation_id)
    row = await db.fetchrow(
        "SELECT id, is_active FROM targets WHERE id = $1 AND operation_id = $2",
        target_id, operation_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Target not found")
    if row["is_active"]:
        raise HTTPException(
            status_code=409,
            detail="Cannot delete the active target. Deselect it first.",
        )
    # FK CASCADE will handle agents referencing this target
    await db.execute("DELETE FROM targets WHERE id = $1", target_id)
    return Response(status_code=204)


@router.get(
    "/operations/{operation_id}/targets/{target_id}/summary",
    response_model=NodeSummaryResponse,
)


async def get_target_summary(
    operation_id: str,
    target_id: str,
    force_refresh: bool = False,
    db: asyncpg.Connection = Depends(get_db),
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
    db: asyncpg.Connection = Depends(get_db),
):
    """Build topology graph: Athena C2 centre + target hosts + state-aware edges."""
    await ensure_operation(db, operation_id)

    # -- Athena C2 centre node --
    nodes: list[TopologyNode] = [
        TopologyNode(
            id="athena-c2",
            label="ATHENA",
            type="c2",
            data={"role": "c2", "is_compromised": False, "is_active": True},
        )
    ]

    # -- Targets -> host nodes (deduplicate by ip_address) --
    target_rows = await db.fetch(
        "SELECT * FROM targets WHERE operation_id = $1", operation_id
    )

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
                    "network_segment": t["network_segment"],  # SPEC-042
                    "is_compromised": bool(t["is_compromised"]),
                    "is_active": bool(t["is_active"]),
                    "privilege_level": t["privilege_level"],
                },
            )
        )

    # -- Compute attack_phase + per-node stats and build Athena->host edges --
    edges: list[TopologyEdge] = []

    for tid in target_ids:
        # Agent status (highest priority)
        agent = await db.fetchrow(
            "SELECT paw, status, privilege FROM agents "
            "WHERE host_id = $1 AND operation_id = $2 ORDER BY last_beacon DESC LIMIT 1",
            tid, operation_id,
        )

        # Technique execution status
        exec_row = await db.fetchrow(
            "SELECT status FROM technique_executions "
            "WHERE target_id = $1 AND operation_id = $2 ORDER BY created_at DESC LIMIT 1",
            tid, operation_id,
        )

        # Recon scan status
        scan_row = await db.fetchrow(
            "SELECT status FROM recon_scans "
            "WHERE target_id = $1 AND operation_id = $2 ORDER BY started_at DESC LIMIT 1",
            tid, operation_id,
        )

        # Per-node gamification stats
        stats_row = await db.fetchrow(
            """
            SELECT
                (SELECT COUNT(*) FROM recon_scans
                 WHERE target_id = $1 AND operation_id = $2) AS scan_count,
                (SELECT COUNT(*) FROM facts
                 WHERE source_target_id = $3 AND operation_id = $4) AS fact_count,
                (SELECT COUNT(*) FROM facts
                 WHERE source_target_id = $5 AND operation_id = $6
                   AND trait LIKE 'credential.%') AS credential_count
            """,
            tid, operation_id, tid, operation_id, tid, operation_id,
        )
        scan_count = stats_row["scan_count"] if stats_row else 0
        fact_count = stats_row["fact_count"] if stats_row else 0
        credential_count = stats_row["credential_count"] if stats_row else 0

        # Open port count from latest completed scan
        port_row = await db.fetchrow(
            "SELECT open_ports FROM recon_scans "
            "WHERE target_id = $1 AND operation_id = $2 AND status = 'completed' "
            "ORDER BY completed_at DESC LIMIT 1",
            tid, operation_id,
        )
        open_port_count = 0
        if port_row and port_row["open_ports"]:
            try:
                open_port_count = len(json.loads(port_row["open_ports"]))
            except (ValueError, TypeError):
                pass

        # Persistence fact count
        persist_row = await db.fetchrow(
            "SELECT COUNT(*) AS cnt FROM facts "
            "WHERE source_target_id = $1 AND operation_id = $2 "
            "AND trait = 'host.persistence'",
            tid, operation_id,
        )
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

        # Build edge from Athena -> host (only if not idle)
        if phase != "idle":
            edges.append(
                TopologyEdge(
                    source="athena-c2",
                    target=tid,
                    label=edge_label,
                    data={"phase": phase},
                )
            )

    # -- Lateral movement edges (host->host) --
    lat_rows = await db.fetch(
        "SELECT DISTINCT f.source_target_id, a.host_id AS dest_tid "
        "FROM facts f "
        "JOIN agents a ON a.operation_id = f.operation_id "
        "  AND a.host_id != f.source_target_id AND a.status = 'alive' "
        "WHERE f.operation_id = $1 "
        "  AND f.trait IN ('credential.ssh','credential.rdp','credential.winrm') "
        "  AND f.source_target_id IS NOT NULL",
        operation_id,
    )
    target_id_set = set(target_ids)
    for row in lat_rows:
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
