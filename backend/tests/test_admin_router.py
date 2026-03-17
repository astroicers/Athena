# Copyright (c) 2025 Athena Red Team Platform
# Author: azz093093.830330@gmail.com
# Project: Athena
# License: MIT
#
# This file is part of the Athena Red Team Platform.
# Unauthorized copying or distribution is prohibited.

"""Router tests for admin endpoints:
    POST /api/admin/rules/reload
    POST /api/operations/{op_id}/reset
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# POST /api/admin/rules/reload -> 200
# ---------------------------------------------------------------------------


async def test_reload_rules(client):
    """POST /api/admin/rules/reload returns 200 with status='ok'."""
    # reload_rules is lazily imported inside the handler so we patch it
    # at its definition site in the attack_graph_engine module.
    with patch("app.services.attack_graph_engine.reload_rules") as mock_reload, \
         patch("app.routers.admin.ws_manager") as mock_ws:
        mock_ws.broadcast = AsyncMock()

        resp = await client.post("/api/admin/rules/reload")

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    mock_reload.assert_called_once()


# ---------------------------------------------------------------------------
# POST /api/operations/{op_id}/reset -> 204
# ---------------------------------------------------------------------------


async def test_reset_operation(client, seeded_db):
    """POST /api/operations/test-op-1/reset returns 204 No Content."""
    with patch("app.routers.admin.ws_manager") as mock_ws:
        mock_ws.broadcast = AsyncMock()

        resp = await client.post("/api/operations/test-op-1/reset")

    assert resp.status_code == 204
    mock_ws.broadcast.assert_awaited_once()
    call_args = mock_ws.broadcast.call_args
    assert call_args.args[0] == "test-op-1"
    assert call_args.args[1] == "operation.reset"


async def test_reset_operation_clears_attack_graph(client, seeded_db):
    """POST reset deletes all attack_graph_nodes for the operation."""
    # Verify seed data exists first
    count_before = await seeded_db.fetchval(
        "SELECT COUNT(*) FROM attack_graph_nodes WHERE operation_id = 'test-op-1'"
    )
    assert count_before > 0, "Seed data must include attack_graph_nodes"

    with patch("app.routers.admin.ws_manager") as mock_ws:
        mock_ws.broadcast = AsyncMock()
        resp = await client.post("/api/operations/test-op-1/reset")

    assert resp.status_code == 204

    count_after = await seeded_db.fetchval(
        "SELECT COUNT(*) FROM attack_graph_nodes WHERE operation_id = 'test-op-1'"
    )
    assert count_after == 0


async def test_reset_operation_not_found(client):
    """POST /api/operations/nonexistent/reset returns 404."""
    resp = await client.post("/api/operations/nonexistent/reset")
    assert resp.status_code == 404
