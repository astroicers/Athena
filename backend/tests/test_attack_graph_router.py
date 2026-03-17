# Copyright (c) 2025 Athena Red Team Platform
# Author: azz093093.830330@gmail.com
# Project: Athena
# License: MIT
#
# This file is part of the Athena Red Team Platform.
# Unauthorized copying or distribution is prohibited.

"""Integration tests for the Attack Graph router (SPEC-031)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_graph() -> MagicMock:
    """Return a MagicMock that satisfies AttackGraph's interface for _to_response()."""
    mock_graph = MagicMock()
    mock_graph.nodes = {}
    mock_graph.edges = []
    mock_graph.explored_paths = []
    mock_graph.unexplored_branches = []
    mock_graph.recommended_path = []
    mock_graph.coverage_score = 0.0
    mock_graph.graph_id = "fake-graph-id"
    mock_graph.operation_id = "test-op-1"
    mock_graph.updated_at = MagicMock(isoformat=MagicMock(return_value="2025-01-01T00:00:00"))
    return mock_graph


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

async def test_get_attack_graph(client: AsyncClient):
    """GET /api/operations/test-op-1/attack-graph -> 200 with engine mocked."""
    mock_graph = _make_mock_graph()

    with patch("app.routers.attack_graph.AttackGraphEngine") as MockEngine:
        instance = MagicMock()
        MockEngine.return_value = instance
        instance.get_graph = AsyncMock(return_value=mock_graph)

        resp = await client.get("/api/operations/test-op-1/attack-graph")

    assert resp.status_code == 200
    body = resp.json()
    assert "nodes" in body
    assert "edges" in body
    assert "stats" in body


async def test_get_attack_graph_builds_when_empty(client: AsyncClient, seeded_db):
    """When engine.get_graph returns None, engine.rebuild is called automatically."""
    mock_graph = _make_mock_graph()

    with patch("app.routers.attack_graph.AttackGraphEngine") as MockEngine:
        instance = MagicMock()
        MockEngine.return_value = instance
        instance.get_graph = AsyncMock(return_value=None)
        instance.rebuild = AsyncMock(return_value=mock_graph)

        resp = await client.get("/api/operations/test-op-1/attack-graph")

    assert resp.status_code == 200
    instance.get_graph.assert_awaited_once()
    instance.rebuild.assert_awaited_once()


async def test_get_attack_graph_unknown_op(client: AsyncClient):
    """GET /api/operations/nonexistent/attack-graph -> 404."""
    resp = await client.get("/api/operations/nonexistent/attack-graph")
    assert resp.status_code == 404


async def test_rebuild_attack_graph(client: AsyncClient):
    """POST /api/operations/test-op-1/attack-graph/rebuild -> 200."""
    mock_graph = _make_mock_graph()

    with patch("app.routers.attack_graph.AttackGraphEngine") as MockEngine:
        instance = MagicMock()
        MockEngine.return_value = instance
        instance.rebuild = AsyncMock(return_value=mock_graph)

        resp = await client.post("/api/operations/test-op-1/attack-graph/rebuild")

    assert resp.status_code == 200
    body = resp.json()
    assert "nodes" in body
    assert "stats" in body
    instance.rebuild.assert_awaited_once()


async def test_rebuild_attack_graph_unknown_op(client: AsyncClient):
    """POST /api/operations/nonexistent/attack-graph/rebuild -> 404."""
    resp = await client.post("/api/operations/nonexistent/attack-graph/rebuild")
    assert resp.status_code == 404
