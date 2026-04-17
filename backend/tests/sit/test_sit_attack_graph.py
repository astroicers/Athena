"""SIT: AttackGraphEngine integration — rebuild + orient summary."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from app.services.attack_graph_engine import AttackGraphEngine

pytestmark = pytest.mark.asyncio


# -- G.1 rebuild produces nodes and edges ------------------------------------
async def test_rebuild_produces_nodes_and_edges(sit_services):
    """AttackGraphEngine.rebuild() creates rows in attack_graph_nodes and edges."""
    db = sit_services.db
    engine = AttackGraphEngine(sit_services.ws)

    graph = await engine.rebuild(db, "test-op-1")

    node_count = await db.fetchval(
        "SELECT COUNT(*) FROM attack_graph_nodes WHERE operation_id = $1",
        "test-op-1",
    )
    edge_count = await db.fetchval(
        "SELECT COUNT(*) FROM attack_graph_edges WHERE operation_id = $1",
        "test-op-1",
    )

    assert node_count > 0, "rebuild should produce attack_graph_nodes rows"
    assert edge_count > 0, "rebuild should produce attack_graph_edges rows"
    # In-memory graph should match persisted counts
    assert len(graph.nodes) == node_count
    assert len(graph.edges) >= 1


# -- G.2 rebuild is idempotent (no duplication) ------------------------------
async def test_rebuild_idempotent(sit_services):
    """Two consecutive rebuilds produce the same node count (no duplication)."""
    db = sit_services.db
    engine = AttackGraphEngine(sit_services.ws)

    await engine.rebuild(db, "test-op-1")
    count_first = await db.fetchval(
        "SELECT COUNT(*) FROM attack_graph_nodes WHERE operation_id = $1",
        "test-op-1",
    )

    await engine.rebuild(db, "test-op-1")
    count_second = await db.fetchval(
        "SELECT COUNT(*) FROM attack_graph_nodes WHERE operation_id = $1",
        "test-op-1",
    )

    assert count_first == count_second, (
        f"rebuild should be idempotent: {count_first} != {count_second}"
    )


# -- G.3 explored node from execution ----------------------------------------
async def test_explored_node_from_execution(sit_seeded_with_execution, sit_ws_manager):
    """Node for T1003.001 shows status='explored' after a successful execution."""
    db = sit_seeded_with_execution
    engine = AttackGraphEngine(sit_ws_manager)

    await engine.rebuild(db, "test-op-1")

    row = await db.fetchrow(
        "SELECT status FROM attack_graph_nodes "
        "WHERE operation_id = $1 AND technique_id = 'T1003.001'",
        "test-op-1",
    )
    assert row is not None, "T1003.001 node should exist in attack_graph_nodes"
    assert row["status"] == "explored", (
        f"T1003.001 should be 'explored' after success execution, got '{row['status']}'"
    )


# -- G.4 build_orient_summary format -----------------------------------------
async def test_build_orient_summary_format(sit_services):
    """build_orient_summary() returns text containing 'coverage' and 'position'."""
    db = sit_services.db
    engine = AttackGraphEngine(sit_services.ws)

    graph = await engine.rebuild(db, "test-op-1")
    summary = engine.build_orient_summary(graph)

    assert isinstance(summary, str)
    summary_lower = summary.lower()
    assert "coverage" in summary_lower, (
        f"Orient summary should mention 'coverage', got: {summary[:200]}"
    )
    # 'position' appears when there are explored nodes (seed has 4 explored)
    assert "position" in summary_lower, (
        f"Orient summary should mention 'position', got: {summary[:200]}"
    )


# -- G.5 rebuild broadcasts ws event -----------------------------------------
async def test_rebuild_broadcasts_ws_event(sit_services):
    """rebuild() broadcasts a 'graph.updated' WebSocket event."""
    db = sit_services.db
    engine = AttackGraphEngine(sit_services.ws)

    # Clear previous calls
    sit_services.ws._calls.clear()

    await engine.rebuild(db, "test-op-1")

    event_types = [c[1] for c in sit_services.ws._calls]
    assert "graph.updated" in event_types, (
        f"Expected 'graph.updated' in WS events, got: {event_types}"
    )
