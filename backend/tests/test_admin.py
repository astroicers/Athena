# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: [TODO: contact email]

"""Admin API tests — SPEC-018 tech-debt clearance."""

from unittest.mock import AsyncMock, patch


async def test_reset_returns_204(client):
    """POST /api/operations/test-op-1/reset → 204."""
    with patch("app.routers.admin.ws_manager") as mock_ws:
        mock_ws.broadcast = AsyncMock()
        resp = await client.post("/api/operations/test-op-1/reset")
        assert resp.status_code == 204


async def test_reset_broadcasts_event(client):
    """Reset broadcasts operation.reset via WebSocket."""
    with patch("app.routers.admin.ws_manager") as mock_ws:
        mock_ws.broadcast = AsyncMock()
        await client.post("/api/operations/test-op-1/reset")
        mock_ws.broadcast.assert_awaited_once_with(
            "test-op-1", "operation.reset", {"operation_id": "test-op-1"}
        )


async def test_reset_clears_execution_history(client, seeded_db):
    """After inserting execution data then resetting, tables are empty."""
    await seeded_db.execute(
        "INSERT INTO log_entries (id, operation_id, timestamp, severity, source, message) "
        "VALUES ('log-1', 'test-op-1', '2026-01-01', 'info', 'test', 'msg')"
    )
    await seeded_db.execute(
        "INSERT INTO facts (id, operation_id, trait, value, score) "
        "VALUES ('fact-1', 'test-op-1', 'host.os', 'Windows', 0.9)"
    )
    with patch("app.routers.admin.ws_manager") as mock_ws:
        mock_ws.broadcast = AsyncMock()
        await client.post("/api/operations/test-op-1/reset")
    # Verify via report endpoint
    data = (await client.get("/api/operations/test-op-1/report")).json()
    assert len(data["logs"]) == 0
    assert len(data["facts"]) == 0


async def test_reset_resets_operation_state(client, seeded_db):
    """After reset, operation status='planning', counters=0."""
    with patch("app.routers.admin.ws_manager") as mock_ws:
        mock_ws.broadcast = AsyncMock()
        await client.post("/api/operations/test-op-1/reset")
    data = (await client.get("/api/operations/test-op-1/report")).json()
    assert data["operation"]["status"] == "planning"
    assert data["operation"]["ooda_iteration_count"] == 0
    assert data["operation"]["techniques_executed"] == 0
    assert data["operation"]["active_agents"] == 0


async def test_reset_deletes_targets_agents_steps(client, seeded_db):
    """After reset, targets/agents/mission_steps are fully deleted (not just reset)."""
    with patch("app.routers.admin.ws_manager") as mock_ws:
        mock_ws.broadcast = AsyncMock()
        await client.post("/api/operations/test-op-1/reset")

    data = (await client.get("/api/operations/test-op-1/report")).json()
    assert data["targets"] == []
    assert data["agents"] == []
    assert data["mission_steps"] == []


async def test_reset_nonexistent_operation(client):
    """POST /api/operations/no-such-op/reset → 404."""
    with patch("app.routers.admin.ws_manager") as mock_ws:
        mock_ws.broadcast = AsyncMock()
        resp = await client.post("/api/operations/no-such-op/reset")
        assert resp.status_code == 404
