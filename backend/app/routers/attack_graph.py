# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: [TODO: contact email]

"""Attack graph REST endpoints — SPEC-031.

GET  /api/operations/{operation_id}/attack-graph         → load or auto-build
POST /api/operations/{operation_id}/attack-graph/rebuild  → force rebuild
"""

import logging

import aiosqlite
from fastapi import APIRouter, Depends, HTTPException

from app.database import get_db
from app.models.api_schemas import (
    AttackGraphEdge,
    AttackGraphNode,
    AttackGraphResponse,
    AttackGraphStats,
)
from app.models.attack_graph import AttackGraph, NodeStatus
from app.services.attack_graph_engine import AttackGraphEngine
from app.ws_manager import ws_manager

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/operations/{operation_id}",
    tags=["attack-graph"],
)


def _to_response(graph: AttackGraph) -> dict:
    """Convert AttackGraph dataclass to response dict with stats."""
    nodes = [
        AttackGraphNode(
            node_id=n.node_id,
            target_id=n.target_id,
            technique_id=n.technique_id,
            tactic_id=n.tactic_id,
            status=n.status.value,
            confidence=n.confidence,
            risk_level=n.risk_level,
            information_gain=n.information_gain,
            effort=n.effort,
            prerequisites=n.prerequisites,
            satisfied_prerequisites=n.satisfied_prerequisites,
            source=n.source,
            execution_id=n.execution_id,
            depth=n.depth,
        )
        for n in graph.nodes.values()
    ]

    edges = [
        AttackGraphEdge(
            edge_id=e.edge_id,
            source=e.source,
            target=e.target,
            weight=e.weight,
            relationship=e.relationship.value,
            required_facts=e.required_facts,
            source_type=e.source_type,
        )
        for e in graph.edges
    ]

    explored = sum(1 for n in graph.nodes.values() if n.status == NodeStatus.EXPLORED)
    pending = sum(1 for n in graph.nodes.values() if n.status == NodeStatus.PENDING)
    failed = sum(1 for n in graph.nodes.values() if n.status == NodeStatus.FAILED)
    pruned = sum(1 for n in graph.nodes.values() if n.status == NodeStatus.PRUNED)
    max_depth = max((n.depth for n in graph.nodes.values()), default=0)

    stats = AttackGraphStats(
        total_nodes=len(graph.nodes),
        explored_nodes=explored,
        pending_nodes=pending,
        failed_nodes=failed,
        pruned_nodes=pruned,
        total_edges=len(graph.edges),
        path_count=len(graph.explored_paths),
        max_depth=max_depth,
    )

    return AttackGraphResponse(
        graph_id=graph.graph_id,
        operation_id=graph.operation_id,
        nodes=nodes,
        edges=edges,
        recommended_path=graph.recommended_path,
        explored_paths=graph.explored_paths,
        unexplored_branches=graph.unexplored_branches,
        coverage_score=graph.coverage_score,
        updated_at=graph.updated_at,
        stats=stats,
    ).model_dump()


async def _verify_operation(db: aiosqlite.Connection, operation_id: str) -> None:
    """Raise 404 if operation does not exist."""
    cursor = await db.execute(
        "SELECT id FROM operations WHERE id = ?", (operation_id,)
    )
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Operation not found")


@router.get("/attack-graph", response_model=AttackGraphResponse)
async def get_attack_graph(
    operation_id: str,
    db: aiosqlite.Connection = Depends(get_db),
):
    """Load existing attack graph or auto-build if none exists."""
    db.row_factory = aiosqlite.Row
    await _verify_operation(db, operation_id)

    engine = AttackGraphEngine(ws_manager)

    # Try loading from DB first
    graph = await engine.get_graph(db, operation_id)
    if graph is None:
        # Auto-build
        graph = await engine.rebuild(db, operation_id)

    return _to_response(graph)


@router.post("/attack-graph/rebuild", response_model=AttackGraphResponse)
async def rebuild_attack_graph(
    operation_id: str,
    db: aiosqlite.Connection = Depends(get_db),
):
    """Force rebuild the attack graph."""
    db.row_factory = aiosqlite.Row
    await _verify_operation(db, operation_id)

    engine = AttackGraphEngine(ws_manager)
    graph = await engine.rebuild(db, operation_id)

    return _to_response(graph)
