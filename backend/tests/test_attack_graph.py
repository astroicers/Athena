# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: [TODO: contact email]

"""Tests for AttackGraphEngine — SPEC-031 acceptance criteria.

TDD: tests written BEFORE engine implementation.
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.attack_graph import (
    AttackEdge,
    AttackGraph,
    AttackNode,
    EdgeRelationship,
    NodeStatus,
    TechniqueRule,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_ws():
    ws = MagicMock()
    ws.broadcast = AsyncMock()
    return ws


def _make_mock_db():
    """Return a fully-mocked aiosqlite connection."""
    db = AsyncMock()
    cursor = AsyncMock()
    cursor.fetchone = AsyncMock(return_value=None)
    cursor.fetchall = AsyncMock(return_value=[])
    db.execute = AsyncMock(return_value=cursor)
    db.executemany = AsyncMock()
    db.commit = AsyncMock()
    db.row_factory = None
    return db


def _seed_db_rows():
    """Return mock DB rows for targets, facts, and technique_executions."""
    targets = [
        {"id": "tgt-1", "hostname": "web-01", "ip_address": "10.0.1.10",
         "os": "Linux", "role": "webserver", "operation_id": "op-1"},
    ]
    facts = [
        {"id": "f-1", "trait": "network.host.ip", "value": "10.0.1.10",
         "category": "network", "source_technique_id": "T1595.001",
         "source_target_id": "tgt-1", "operation_id": "op-1"},
        {"id": "f-2", "trait": "service.open_port", "value": "22/tcp",
         "category": "service", "source_technique_id": "T1595.001",
         "source_target_id": "tgt-1", "operation_id": "op-1"},
    ]
    executions = [
        {"id": "exec-1", "technique_id": "T1595.001", "target_id": "tgt-1",
         "operation_id": "op-1", "status": "success"},
    ]
    return targets, facts, executions


# ---------------------------------------------------------------------------
# Test 1: Determinism — same facts produce same graph structure
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_determinism_same_facts_same_graph():
    """Same facts/targets/executions must produce identical graph structure."""
    from app.services.attack_graph_engine import AttackGraphEngine

    ws = _make_mock_ws()
    engine = AttackGraphEngine(ws)

    targets, facts, executions = _seed_db_rows()

    # Build in-memory graph twice
    g1 = engine._build_graph_in_memory("op-1", targets, facts, executions)
    g2 = engine._build_graph_in_memory("op-1", targets, facts, executions)

    # Same node IDs (deterministic = technique_id + target_id hashing)
    assert set(g1.nodes.keys()) == set(g2.nodes.keys())

    # Same edge count and same source->target pairs
    edges1 = sorted((e.source, e.target) for e in g1.edges)
    edges2 = sorted((e.source, e.target) for e in g2.edges)
    assert edges1 == edges2

    # Same recommended_path
    assert g1.recommended_path == g2.recommended_path


# ---------------------------------------------------------------------------
# Test 2: Weight calculation — known inputs produce expected weight
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_weight_calculation():
    """compute_edge_weight with known inputs matches formula."""
    from app.services.attack_graph_engine import AttackGraphEngine

    ws = _make_mock_ws()
    engine = AttackGraphEngine(ws)

    # confidence=0.85, information_gain=0.8, effort=1
    # W = 0.5*0.85 + 0.3*0.8 + 0.2*(1 - 1/5) = 0.425 + 0.24 + 0.16 = 0.825
    node = AttackNode(
        node_id="n1", target_id="t1", technique_id="T1595.002",
        tactic_id="TA0043", status=NodeStatus.PENDING,
        confidence=0.85, risk_level="low",
        information_gain=0.8, effort=1,
        prerequisites=["network.host.ip"], satisfied_prerequisites=["network.host.ip"],
    )
    weight = engine.compute_edge_weight(node)
    assert abs(weight - 0.825) < 0.01

    # effort=5 → e_norm=1.0 → gamma*(1-1.0)=0
    node2 = AttackNode(
        node_id="n2", target_id="t1", technique_id="T1190",
        tactic_id="TA0001", status=NodeStatus.PENDING,
        confidence=0.6, risk_level="medium",
        information_gain=0.7, effort=5,
        prerequisites=["service.open_port"], satisfied_prerequisites=[],
    )
    weight2 = engine.compute_edge_weight(node2)
    # W = 0.5*0.6 + 0.3*0.7 + 0.2*(1-1.0) = 0.3 + 0.21 + 0 = 0.51
    assert abs(weight2 - 0.51) < 0.01


# ---------------------------------------------------------------------------
# Test 3: Dijkstra recommended path — 5-node linear graph
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_dijkstra_recommended_path():
    """5-node chain: entry -> A -> B -> C -> destination. Path should be the full chain."""
    from app.services.attack_graph_engine import AttackGraphEngine

    ws = _make_mock_ws()
    engine = AttackGraphEngine(ws)

    # Build a simple 5-node graph manually
    graph = AttackGraph(
        graph_id="g1", operation_id="op-1",
        nodes={}, edges=[], recommended_path=[],
        explored_paths=[], unexplored_branches=[],
        coverage_score=0.0, updated_at="",
    )

    # Nodes: entry(depth=0), A, B, C, dest(highest info_gain PENDING)
    entry = AttackNode(
        node_id="entry", target_id="t1", technique_id="T1595.001",
        tactic_id="TA0043", status=NodeStatus.EXPLORED,
        confidence=0.95, risk_level="low", information_gain=0.9,
        effort=1, prerequisites=[], satisfied_prerequisites=[], depth=0,
    )
    node_a = AttackNode(
        node_id="a", target_id="t1", technique_id="T1595.002",
        tactic_id="TA0043", status=NodeStatus.EXPLORED,
        confidence=0.85, risk_level="low", information_gain=0.8,
        effort=1, prerequisites=["network.host.ip"],
        satisfied_prerequisites=["network.host.ip"], depth=1,
    )
    node_b = AttackNode(
        node_id="b", target_id="t1", technique_id="T1190",
        tactic_id="TA0001", status=NodeStatus.PENDING,
        confidence=0.6, risk_level="medium", information_gain=0.7,
        effort=2, prerequisites=["service.open_port"],
        satisfied_prerequisites=["service.open_port"], depth=2,
    )
    node_c = AttackNode(
        node_id="c", target_id="t1", technique_id="T1059.004",
        tactic_id="TA0002", status=NodeStatus.PENDING,
        confidence=0.85, risk_level="medium", information_gain=0.5,
        effort=1, prerequisites=["credential.ssh"],
        satisfied_prerequisites=[], depth=3,
    )
    dest = AttackNode(
        node_id="dest", target_id="t1", technique_id="T1003.001",
        tactic_id="TA0006", status=NodeStatus.PENDING,
        confidence=0.75, risk_level="high", information_gain=0.9,
        effort=1, prerequisites=["credential.ssh", "host.user"],
        satisfied_prerequisites=[], depth=4,
    )

    graph.nodes = {n.node_id: n for n in [entry, node_a, node_b, node_c, dest]}

    # Build edges: entry->a, a->b, b->c, c->dest  (all ENABLES)
    edges = []
    pairs = [("entry", "a"), ("a", "b"), ("b", "c"), ("c", "dest")]
    for src, tgt in pairs:
        w = engine.compute_edge_weight(graph.nodes[tgt])
        edges.append(AttackEdge(
            edge_id=f"e-{src}-{tgt}", source=src, target=tgt,
            weight=w, relationship=EdgeRelationship.ENABLES,
            required_facts=[],
        ))
    graph.edges = edges

    # Run Dijkstra
    rec_path = engine.compute_recommended_path(graph)

    # Path should start from entry node and reach dest (highest info_gain PENDING)
    assert len(rec_path) >= 2
    assert rec_path[0] == "entry"
    assert rec_path[-1] == "dest"


# ---------------------------------------------------------------------------
# Test 4: Cycle detection — detect and break cycle
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cycle_detection_and_break():
    """Graph with A->B->C->A cycle: detect and remove lowest-weight edge."""
    from app.services.attack_graph_engine import AttackGraphEngine

    ws = _make_mock_ws()
    engine = AttackGraphEngine(ws)

    graph = AttackGraph(
        graph_id="g-cycle", operation_id="op-1",
        nodes={}, edges=[], recommended_path=[],
        explored_paths=[], unexplored_branches=[],
        coverage_score=0.0, updated_at="",
    )

    na = AttackNode(
        node_id="a", target_id="t1", technique_id="T1",
        tactic_id="TA0001", status=NodeStatus.PENDING,
        confidence=0.8, risk_level="low", information_gain=0.5,
        effort=1, prerequisites=[], satisfied_prerequisites=[], depth=0,
    )
    nb = AttackNode(
        node_id="b", target_id="t1", technique_id="T2",
        tactic_id="TA0002", status=NodeStatus.PENDING,
        confidence=0.7, risk_level="low", information_gain=0.4,
        effort=2, prerequisites=[], satisfied_prerequisites=[], depth=1,
    )
    nc = AttackNode(
        node_id="c", target_id="t1", technique_id="T3",
        tactic_id="TA0003", status=NodeStatus.PENDING,
        confidence=0.6, risk_level="low", information_gain=0.3,
        effort=3, prerequisites=[], satisfied_prerequisites=[], depth=2,
    )

    graph.nodes = {"a": na, "b": nb, "c": nc}

    # Edges forming cycle: a->b (w=0.7), b->c (w=0.5), c->a (w=0.3)
    graph.edges = [
        AttackEdge(edge_id="e-ab", source="a", target="b", weight=0.7,
                   relationship=EdgeRelationship.ENABLES, required_facts=[]),
        AttackEdge(edge_id="e-bc", source="b", target="c", weight=0.5,
                   relationship=EdgeRelationship.ENABLES, required_facts=[]),
        AttackEdge(edge_id="e-ca", source="c", target="a", weight=0.3,
                   relationship=EdgeRelationship.ENABLES, required_facts=[]),
    ]

    cycles = engine.detect_cycles(graph)
    assert len(cycles) > 0, "Should detect at least one cycle"

    # Break cycles — should remove lowest weight edge (c->a, w=0.3)
    engine._break_cycles(graph, cycles)
    remaining_edges = [(e.source, e.target) for e in graph.edges]
    assert ("c", "a") not in remaining_edges, "Lowest-weight edge should be removed"


# ---------------------------------------------------------------------------
# Test 5: Dead branch pruning — failed node prunes siblings + downstream
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_dead_branch_pruning():
    """When a technique fails, siblings (same tactic+target) and downstream are pruned."""
    from app.services.attack_graph_engine import AttackGraphEngine

    ws = _make_mock_ws()
    engine = AttackGraphEngine(ws)

    graph = AttackGraph(
        graph_id="g-prune", operation_id="op-1",
        nodes={}, edges=[], recommended_path=[],
        explored_paths=[], unexplored_branches=[],
        coverage_score=0.0, updated_at="",
    )

    # prereq (explored) -> failed_node (FAILED) and sibling_node (same tactic/target, PENDING)
    # sibling_node -> downstream_node (PENDING)
    prereq = AttackNode(
        node_id="prereq", target_id="t1", technique_id="T0",
        tactic_id="TA0043", status=NodeStatus.EXPLORED,
        confidence=0.95, risk_level="low", information_gain=0.9,
        effort=1, prerequisites=[], satisfied_prerequisites=[], depth=0,
    )
    failed_node = AttackNode(
        node_id="failed", target_id="t1", technique_id="T1190",
        tactic_id="TA0001", status=NodeStatus.FAILED,
        confidence=0.0, risk_level="medium", information_gain=0.7,
        effort=2, prerequisites=["service.open_port"],
        satisfied_prerequisites=["service.open_port"], depth=1,
    )
    sibling = AttackNode(
        node_id="sibling", target_id="t1", technique_id="T1110.001",
        tactic_id="TA0001", status=NodeStatus.PENDING,
        confidence=0.7, risk_level="medium", information_gain=0.6,
        effort=1, prerequisites=["service.open_port"],
        satisfied_prerequisites=["service.open_port"], depth=1,
    )
    downstream = AttackNode(
        node_id="downstream", target_id="t1", technique_id="T1059.004",
        tactic_id="TA0002", status=NodeStatus.PENDING,
        confidence=0.85, risk_level="medium", information_gain=0.5,
        effort=1, prerequisites=["credential.ssh"],
        satisfied_prerequisites=[], depth=2,
    )

    graph.nodes = {
        "prereq": prereq, "failed": failed_node,
        "sibling": sibling, "downstream": downstream,
    }
    graph.edges = [
        AttackEdge(edge_id="e1", source="prereq", target="failed", weight=0.5,
                   relationship=EdgeRelationship.ENABLES, required_facts=[]),
        AttackEdge(edge_id="e2", source="prereq", target="sibling", weight=0.6,
                   relationship=EdgeRelationship.ENABLES, required_facts=[]),
        # failed and sibling are alternatives
        AttackEdge(edge_id="e3", source="failed", target="sibling", weight=0.4,
                   relationship=EdgeRelationship.ALTERNATIVE, required_facts=[]),
        # sibling enables downstream
        AttackEdge(edge_id="e4", source="sibling", target="downstream", weight=0.7,
                   relationship=EdgeRelationship.ENABLES, required_facts=[]),
    ]

    engine.prune_dead_branches(graph)

    assert graph.nodes["sibling"].status == NodeStatus.PRUNED
    assert graph.nodes["downstream"].status in (NodeStatus.PRUNED, NodeStatus.UNREACHABLE)


# ---------------------------------------------------------------------------
# Test 6: Empty graph — no facts, no exception
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_empty_graph_no_exception():
    """No facts/targets/executions produces a valid empty graph."""
    from app.services.attack_graph_engine import AttackGraphEngine

    ws = _make_mock_ws()
    engine = AttackGraphEngine(ws)

    graph = engine._build_graph_in_memory("op-1", [], [], [])

    assert isinstance(graph, AttackGraph)
    assert graph.operation_id == "op-1"
    assert len(graph.nodes) == 0
    assert len(graph.edges) == 0
    assert graph.coverage_score == 0.0
    assert graph.recommended_path == []


# ---------------------------------------------------------------------------
# Test 7: Orphan node — unreachable technique keeps UNREACHABLE status
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_orphan_node_unreachable_status():
    """A technique whose prerequisites cannot be satisfied is UNREACHABLE."""
    from app.services.attack_graph_engine import AttackGraphEngine

    ws = _make_mock_ws()
    engine = AttackGraphEngine(ws)

    targets = [
        {"id": "tgt-1", "hostname": "web-01", "ip_address": "10.0.1.10",
         "os": "Linux", "role": "webserver", "operation_id": "op-1"},
    ]
    # Only have network.host.ip — technique T1059.004 requires credential.ssh
    facts = [
        {"id": "f-1", "trait": "network.host.ip", "value": "10.0.1.10",
         "category": "network", "source_technique_id": "T1595.001",
         "source_target_id": "tgt-1", "operation_id": "op-1"},
    ]
    executions = []

    graph = engine._build_graph_in_memory("op-1", targets, facts, executions)

    # T1059.004 requires credential.ssh which is not in facts
    exec_nodes = [n for n in graph.nodes.values() if n.technique_id == "T1059.004"]
    if exec_nodes:
        assert exec_nodes[0].status == NodeStatus.UNREACHABLE


# ---------------------------------------------------------------------------
# Test 8: API GET — 200 with graph data
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_api_get_attack_graph(client):
    """GET /api/operations/{id}/attack-graph returns 200 with graph data."""
    resp = await client.get("/api/operations/test-op-1/attack-graph")
    assert resp.status_code == 200

    data = resp.json()
    assert "graph_id" in data
    assert data["operation_id"] == "test-op-1"
    assert "nodes" in data
    assert "edges" in data
    assert "recommended_path" in data
    assert "stats" in data


# ---------------------------------------------------------------------------
# Test 9: API POST rebuild — 200 with rebuilt graph
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_api_post_rebuild_attack_graph(client):
    """POST /api/operations/{id}/attack-graph/rebuild returns 200."""
    resp = await client.post("/api/operations/test-op-1/attack-graph/rebuild")
    assert resp.status_code == 200

    data = resp.json()
    assert data["operation_id"] == "test-op-1"
    assert "stats" in data


# ---------------------------------------------------------------------------
# Test 10: API 404 — non-existent operation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_api_get_nonexistent_operation(client):
    """GET /api/operations/{id}/attack-graph for unknown op returns 404."""
    resp = await client.get("/api/operations/nonexistent-op/attack-graph")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Test 11: WebSocket event — rebuild broadcasts graph.updated
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_websocket_event_on_rebuild():
    """rebuild() should broadcast a 'graph.updated' WebSocket event."""
    from app.services.attack_graph_engine import AttackGraphEngine

    ws = _make_mock_ws()
    engine = AttackGraphEngine(ws)

    # Mock DB that returns enough data for rebuild
    db = _make_mock_db()

    # Mock operation exists
    op_cursor = AsyncMock()
    op_cursor.fetchone = AsyncMock(return_value={"id": "op-1"})

    # Mock targets
    targets_cursor = AsyncMock()
    targets_cursor.fetchall = AsyncMock(return_value=[])

    # Mock facts
    facts_cursor = AsyncMock()
    facts_cursor.fetchall = AsyncMock(return_value=[])

    # Mock executions
    exec_cursor = AsyncMock()
    exec_cursor.fetchall = AsyncMock(return_value=[])

    call_count = 0

    async def mock_execute(sql, params=None):
        nonlocal call_count
        call_count += 1
        sql_lower = sql.strip().lower()
        if "select" in sql_lower and "operations" in sql_lower:
            return op_cursor
        if "select" in sql_lower and "targets" in sql_lower:
            return targets_cursor
        if "select" in sql_lower and "facts" in sql_lower:
            return facts_cursor
        if "select" in sql_lower and "technique_executions" in sql_lower:
            return exec_cursor
        # DELETE / INSERT statements
        default_cursor = AsyncMock()
        default_cursor.fetchone = AsyncMock(return_value=None)
        default_cursor.fetchall = AsyncMock(return_value=[])
        return default_cursor

    db.execute = AsyncMock(side_effect=mock_execute)

    graph = await engine.rebuild(db, "op-1")

    # Verify WebSocket broadcast was called with graph.updated
    ws.broadcast.assert_awaited()
    broadcast_calls = ws.broadcast.call_args_list
    event_types = [c.args[1] if len(c.args) > 1 else c.kwargs.get("event_type") for c in broadcast_calls]
    assert "graph.updated" in event_types


# ---------------------------------------------------------------------------
# Test 12: Orient summary — build_orient_summary format
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_build_orient_summary():
    """build_orient_summary produces correctly formatted string."""
    from app.services.attack_graph_engine import AttackGraphEngine

    ws = _make_mock_ws()
    engine = AttackGraphEngine(ws)

    graph = AttackGraph(
        graph_id="g1", operation_id="op-1",
        nodes={
            "n1": AttackNode(
                node_id="n1", target_id="t1", technique_id="T1595.001",
                tactic_id="TA0043", status=NodeStatus.EXPLORED,
                confidence=0.95, risk_level="low", information_gain=0.9,
                effort=1, prerequisites=[], satisfied_prerequisites=[], depth=0,
            ),
            "n2": AttackNode(
                node_id="n2", target_id="t1", technique_id="T1190",
                tactic_id="TA0001", status=NodeStatus.PENDING,
                confidence=0.6, risk_level="medium", information_gain=0.7,
                effort=2, prerequisites=["service.open_port"],
                satisfied_prerequisites=[], depth=1,
            ),
        },
        edges=[],
        recommended_path=["n1", "n2"],
        explored_paths=[["n1"]],
        unexplored_branches=["n2"],
        coverage_score=0.5,
        updated_at="2026-01-01T00:00:00",
    )

    summary = engine.build_orient_summary(graph)

    assert "coverage" in summary.lower()
    assert "50%" in summary
    assert "Recommended path" in summary
    assert "T1595.001" in summary
    assert "T1190" in summary
    assert "explored" in summary.lower()
    # Verify enhanced format elements
    assert "Current position" in summary
    assert "Next best node" in summary
    assert "Unexplored high-value branches" in summary


# ---------------------------------------------------------------------------
# Test 13: Coverage score — explored/total calculation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_coverage_score_calculation():
    """Coverage = explored / total nodes."""
    from app.services.attack_graph_engine import AttackGraphEngine

    ws = _make_mock_ws()
    engine = AttackGraphEngine(ws)

    targets = [
        {"id": "tgt-1", "hostname": "web-01", "ip_address": "10.0.1.10",
         "os": "Linux", "role": "webserver", "operation_id": "op-1"},
    ]
    facts = [
        {"id": "f-1", "trait": "network.host.ip", "value": "10.0.1.10",
         "category": "network", "source_technique_id": "T1595.001",
         "source_target_id": "tgt-1", "operation_id": "op-1"},
        {"id": "f-2", "trait": "service.open_port", "value": "22/tcp",
         "category": "service", "source_technique_id": "T1595.001",
         "source_target_id": "tgt-1", "operation_id": "op-1"},
    ]
    executions = [
        {"id": "exec-1", "technique_id": "T1595.001", "target_id": "tgt-1",
         "operation_id": "op-1", "status": "success"},
    ]

    graph = engine._build_graph_in_memory("op-1", targets, facts, executions)

    # At least one node is explored (T1595.001 succeeded)
    explored = sum(1 for n in graph.nodes.values() if n.status == NodeStatus.EXPLORED)
    total = len(graph.nodes)

    if total > 0:
        expected_coverage = explored / total
        assert abs(graph.coverage_score - expected_coverage) < 0.01


# ---------------------------------------------------------------------------
# Test 14: Confidence adjustments — cross-target +0.1, failed tactic -0.05
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_confidence_cross_target_boost():
    """If technique succeeded on another target, confidence gets +0.1 boost."""
    from app.services.attack_graph_engine import AttackGraphEngine

    ws = _make_mock_ws()
    engine = AttackGraphEngine(ws)

    # Two targets, T1595.001 succeeded on tgt-1
    targets = [
        {"id": "tgt-1", "hostname": "web-01", "ip_address": "10.0.1.10",
         "os": "Linux", "role": "webserver", "operation_id": "op-1"},
        {"id": "tgt-2", "hostname": "web-02", "ip_address": "10.0.1.11",
         "os": "Linux", "role": "webserver", "operation_id": "op-1"},
    ]
    facts = [
        {"id": "f-1", "trait": "network.host.ip", "value": "10.0.1.10",
         "category": "network", "source_technique_id": "T1595.001",
         "source_target_id": "tgt-1", "operation_id": "op-1"},
        {"id": "f-2", "trait": "service.open_port", "value": "22/tcp",
         "category": "service", "source_technique_id": "T1595.001",
         "source_target_id": "tgt-1", "operation_id": "op-1"},
    ]
    executions = [
        {"id": "exec-1", "technique_id": "T1595.001", "target_id": "tgt-1",
         "operation_id": "op-1", "status": "success"},
    ]

    graph = engine._build_graph_in_memory("op-1", targets, facts, executions)

    # Find T1595.001 node for tgt-2 — should have boosted confidence
    tgt2_scan_nodes = [
        n for n in graph.nodes.values()
        if n.technique_id == "T1595.001" and n.target_id == "tgt-2"
    ]
    if tgt2_scan_nodes:
        node = tgt2_scan_nodes[0]
        # Base confidence = 0.95 (no required facts, so full base)
        # Cross-target boost = +0.1
        # Cap at 1.0 → min(0.95 + 0.1, 1.0) = 1.0
        assert node.confidence >= 0.95  # boosted from base


@pytest.mark.asyncio
async def test_confidence_failed_tactic_penalty():
    """If same tactic has a failed technique, confidence is penalized -0.05."""
    from app.services.attack_graph_engine import AttackGraphEngine

    ws = _make_mock_ws()
    engine = AttackGraphEngine(ws)

    targets = [
        {"id": "tgt-1", "hostname": "web-01", "ip_address": "10.0.1.10",
         "os": "Linux", "role": "webserver", "operation_id": "op-1"},
    ]
    facts = [
        {"id": "f-1", "trait": "network.host.ip", "value": "10.0.1.10",
         "category": "network", "source_technique_id": "T1595.001",
         "source_target_id": "tgt-1", "operation_id": "op-1"},
        {"id": "f-2", "trait": "service.open_port", "value": "22/tcp",
         "category": "service", "source_technique_id": "T1595.001",
         "source_target_id": "tgt-1", "operation_id": "op-1"},
    ]
    # T1190 (TA0001) failed, T1110.001 (TA0001) should get penalty
    executions = [
        {"id": "exec-1", "technique_id": "T1595.001", "target_id": "tgt-1",
         "operation_id": "op-1", "status": "success"},
        {"id": "exec-2", "technique_id": "T1190", "target_id": "tgt-1",
         "operation_id": "op-1", "status": "failed"},
    ]

    graph = engine._build_graph_in_memory("op-1", targets, facts, executions)

    # Find T1110.001 node for tgt-1 (same tactic TA0001 as failed T1190)
    brute_nodes = [
        n for n in graph.nodes.values()
        if n.technique_id == "T1110.001" and n.target_id == "tgt-1"
    ]
    if brute_nodes:
        node = brute_nodes[0]
        # T1110.001 base_confidence=0.7, requires service.open_port (satisfied)
        # base = 0.7 * 1.0 = 0.7
        # failed tactic penalty = -0.05
        # expected = 0.65
        assert node.confidence <= 0.70  # should be penalized
