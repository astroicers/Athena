# Copyright (c) 2025 Athena Red Team Platform
# Author: azz093093.830330@gmail.com
# Project: Athena
# License: MIT
#
# This file is part of the Athena Red Team Platform.
# Unauthorized copying or distribution is prohibited.

"""Router tests for agent endpoints:
    GET  /api/operations/{op_id}/agents
    POST /api/operations/{op_id}/agents/sync
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# GET /api/operations/{op_id}/agents -> 200
# ---------------------------------------------------------------------------


async def test_list_agents(client):
    """GET /api/operations/test-op-1/agents returns 200 with a list."""
    resp = await client.get("/api/operations/test-op-1/agents")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    ids = [a["id"] for a in data]
    assert "test-agent-1" in ids


async def test_list_agents_returns_correct_fields(client):
    """GET agents list items contain paw, host_id, and status fields."""
    resp = await client.get("/api/operations/test-op-1/agents")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    agent = next(a for a in data if a["id"] == "test-agent-1")
    assert agent["paw"] == "abc123"
    assert "host_id" in agent
    assert "status" in agent


async def test_list_agents_unknown_op_returns_404(client):
    """GET /api/operations/nonexistent/agents returns 404."""
    resp = await client.get("/api/operations/nonexistent/agents")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /api/operations/{op_id}/agents/sync -> 202
# ---------------------------------------------------------------------------


async def test_sync_agents_returns_202(client):
    """POST /api/operations/test-op-1/agents/sync returns 202 immediately."""
    with patch("app.routers.agents.asyncio.create_task") as mock_task:
        mock_task.return_value = MagicMock()

        resp = await client.post("/api/operations/test-op-1/agents/sync")

    assert resp.status_code == 202
    data = resp.json()
    assert data["status"] == "sync_started"
    assert data["operation_id"] == "test-op-1"
    mock_task.assert_called_once()


async def test_sync_agents_unknown_op_returns_404(client):
    """POST /api/operations/nonexistent/agents/sync returns 404."""
    with patch("app.routers.agents.asyncio.create_task") as mock_task:
        mock_task.return_value = MagicMock()

        resp = await client.post("/api/operations/nonexistent/agents/sync")

    assert resp.status_code == 404
    mock_task.assert_not_called()
