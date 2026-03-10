# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.

"""Dashboard aggregate API — single endpoint for all operation metrics."""

from __future__ import annotations

import asyncpg
from fastapi import APIRouter, Depends, Query

from app.database import get_db
from app.routers._deps import ensure_operation

router = APIRouter()


@router.get("/operations/{operation_id}/dashboard")
async def get_dashboard(
    operation_id: str,
    db: asyncpg.Connection = Depends(get_db),
):
    """Aggregated dashboard data: OODA state, threat_level, mission progress,
    C5ISR summary, OPSEC summary."""
    await ensure_operation(db, operation_id)

    # Operation basics
    op = await db.fetchrow(
        """SELECT id, code, name, codename, status, current_ooda_phase,
                  ooda_iteration_count, threat_level, success_rate,
                  techniques_executed, mission_profile
           FROM operations WHERE id = $1""",
        operation_id,
    )

    # C5ISR summary
    c5isr_rows = await db.fetch(
        "SELECT domain, health_pct, status FROM c5isr_statuses WHERE operation_id = $1",
        operation_id,
    )

    # Target summary
    target_stats = await db.fetchrow(
        """SELECT COUNT(*) AS total,
                  COUNT(*) FILTER (WHERE access_status = 'active') AS compromised,
                  COUNT(*) FILTER (WHERE role IN ('Domain Controller', 'DC', 'Database', 'File Server')) AS hvt_total,
                  COUNT(*) FILTER (WHERE access_status = 'active' AND role IN ('Domain Controller', 'DC', 'Database', 'File Server')) AS hvt_compromised
           FROM targets WHERE operation_id = $1""",
        operation_id,
    )

    # Recent technique executions
    recent_execs = await db.fetch(
        """SELECT te.technique_id, t.name AS technique_name, te.status, te.engine, te.completed_at
           FROM technique_executions te
           LEFT JOIN techniques t ON t.mitre_id = te.technique_id
           WHERE te.operation_id = $1
           ORDER BY te.completed_at DESC NULLS LAST LIMIT 5""",
        operation_id,
    )

    # OPSEC quick summary
    opsec_row = await db.fetchrow(
        """SELECT COALESCE(SUM(noise_points), 0) AS noise_10min,
                  COUNT(*) AS event_count
           FROM opsec_events
           WHERE operation_id = $1 AND created_at > NOW() - INTERVAL '10 minutes'""",
        operation_id,
    )

    # Objective progress
    obj_row = await db.fetchrow(
        """SELECT COUNT(*) AS total,
                  COUNT(*) FILTER (WHERE status = 'achieved') AS achieved,
                  COUNT(*) FILTER (WHERE status = 'in_progress') AS in_progress
           FROM mission_objectives WHERE operation_id = $1""",
        operation_id,
    )

    return {
        "operation": dict(op) if op else {},
        "c5isr": [dict(r) for r in c5isr_rows],
        "targets": dict(target_stats) if target_stats else {},
        "recent_executions": [dict(r) for r in recent_execs],
        "opsec": {
            "noise_10min": int(opsec_row["noise_10min"]) if opsec_row else 0,
            "event_count": int(opsec_row["event_count"]) if opsec_row else 0,
        },
        "objectives": dict(obj_row) if obj_row else {"total": 0, "achieved": 0, "in_progress": 0},
    }


@router.get("/operations/{operation_id}/targets/{target_id}/kill-chain")
async def get_kill_chain(
    operation_id: str,
    target_id: str,
    db: asyncpg.Connection = Depends(get_db),
):
    """Per-target MITRE tactic progress (kill chain)."""
    await ensure_operation(db, operation_id)
    rows = await db.fetch(
        """SELECT tactic_id, status, confidence
           FROM attack_graph_nodes
           WHERE operation_id = $1 AND target_id = $2
           ORDER BY tactic_id""",
        operation_id, target_id,
    )
    return [dict(r) for r in rows]


@router.get("/operations/{operation_id}/attack-surface")
async def get_attack_surface(
    operation_id: str,
    db: asyncpg.Connection = Depends(get_db),
):
    """Per-target/service vulnerability distribution."""
    await ensure_operation(db, operation_id)
    rows = await db.fetch(
        """SELECT t.id AS target_id, t.hostname, t.ip_address,
                  COUNT(v.id) AS vuln_count,
                  COUNT(*) FILTER (WHERE v.severity = 'critical') AS critical,
                  COUNT(*) FILTER (WHERE v.severity = 'high') AS high
           FROM targets t
           LEFT JOIN vulnerabilities v ON v.target_id = t.id
           WHERE t.operation_id = $1
           GROUP BY t.id, t.hostname, t.ip_address
           ORDER BY vuln_count DESC""",
        operation_id,
    )
    return [dict(r) for r in rows]


@router.get("/operations/{operation_id}/metrics/time-series")
async def get_time_series(
    operation_id: str,
    metric: str = Query("c5isr", description="Metric type: c5isr, opsec, executions"),
    granularity: str = Query("5min", description="Aggregation: 1min, 5min, 15min, 1h"),
    db: asyncpg.Connection = Depends(get_db),
):
    """Historical time-series data for various metrics."""
    await ensure_operation(db, operation_id)

    interval_map = {"1min": "1 minute", "5min": "5 minutes", "15min": "15 minutes", "1h": "1 hour"}
    interval = interval_map.get(granularity, "5 minutes")

    if metric == "c5isr":
        rows = await db.fetch(
            f"""SELECT domain,
                       date_trunc('minute', recorded_at) AS ts,
                       AVG(health_pct) AS avg_health
                FROM c5isr_status_history
                WHERE operation_id = $1
                GROUP BY domain, date_trunc('minute', recorded_at)
                ORDER BY ts""",
            operation_id,
        )
    elif metric == "opsec":
        rows = await db.fetch(
            f"""SELECT date_trunc('minute', created_at) AS ts,
                       SUM(noise_points) AS total_noise,
                       COUNT(*) AS event_count
                FROM opsec_events
                WHERE operation_id = $1
                GROUP BY date_trunc('minute', created_at)
                ORDER BY ts""",
            operation_id,
        )
    elif metric == "executions":
        rows = await db.fetch(
            f"""SELECT date_trunc('minute', completed_at) AS ts,
                       COUNT(*) AS total,
                       COUNT(*) FILTER (WHERE status = 'success') AS success,
                       COUNT(*) FILTER (WHERE status = 'failed') AS failed
                FROM technique_executions
                WHERE operation_id = $1 AND completed_at IS NOT NULL
                GROUP BY date_trunc('minute', completed_at)
                ORDER BY ts""",
            operation_id,
        )
    else:
        return {"error": f"Unknown metric: {metric}"}

    return [dict(r) for r in rows]


@router.get("/operations/{operation_id}/credential-graph")
async def get_credential_graph(
    operation_id: str,
    db: asyncpg.Connection = Depends(get_db),
):
    """Credential reuse graph (nodes + edges)."""
    await ensure_operation(db, operation_id)
    creds = await db.fetch(
        """SELECT id, username, secret_type, domain, source_target_id, tested_targets
           FROM credentials WHERE operation_id = $1""",
        operation_id,
    )

    nodes = []
    edges = []
    seen_targets = set()

    for c in creds:
        cred_id = c["id"]
        label = f"{c['username'] or 'unknown'}@{c['domain'] or 'local'}"
        nodes.append({"id": cred_id, "label": label, "type": "credential",
                       "metadata": {"secret_type": c["secret_type"]}})

        if c["source_target_id"]:
            tid = c["source_target_id"]
            if tid not in seen_targets:
                seen_targets.add(tid)
                nodes.append({"id": tid, "label": tid, "type": "target", "metadata": {}})
            edges.append({"source": tid, "target": cred_id, "relation": "harvested_from"})

        import json
        tested = json.loads(c["tested_targets"]) if isinstance(c["tested_targets"], str) else (c["tested_targets"] or [])
        for entry in tested:
            tid = entry.get("target_id", "")
            if tid and tid not in seen_targets:
                seen_targets.add(tid)
                nodes.append({"id": tid, "label": tid, "type": "target", "metadata": {}})
            if tid:
                edges.append({"source": cred_id, "target": tid,
                               "relation": "valid_on" if entry.get("result") == "success" else "tested_on"})

    return {"operation_id": operation_id, "nodes": nodes, "edges": edges}
