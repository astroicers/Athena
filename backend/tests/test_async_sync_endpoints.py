# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: [TODO: contact email]

"""Tests for async 202 pattern on POST /agents/sync and POST /techniques/sync-c2.

Covers Task 5 of the async refactor plan:
  - Endpoint returns 202 immediately with {"status": "sync_started"}
  - asyncio.create_task is called exactly once
  - Background function broadcasts completion event on success
  - Background function logs (and for agents: broadcasts failure event) on exception
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# POST /operations/{op_id}/agents/sync → 202 Accepted
# ---------------------------------------------------------------------------


async def test_agents_sync_returns_202(client):
    """POST agents/sync returns 202 with status='sync_started' immediately."""
    with patch("app.routers.agents.asyncio.create_task") as mock_create_task:
        mock_task = MagicMock()
        mock_task.add_done_callback = MagicMock()
        mock_create_task.return_value = mock_task

        resp = await client.post("/api/operations/test-op-1/agents/sync")

    assert resp.status_code == 202
    data = resp.json()
    assert data["status"] == "sync_started"
    assert data["operation_id"] == "test-op-1"


async def test_agents_sync_enqueues_background_task(client):
    """POST agents/sync calls asyncio.create_task exactly once."""
    with patch("app.routers.agents.asyncio.create_task") as mock_create_task:
        mock_task = MagicMock()
        mock_task.add_done_callback = MagicMock()
        mock_create_task.return_value = mock_task

        await client.post("/api/operations/test-op-1/agents/sync")

    mock_create_task.assert_called_once()


async def test_agents_sync_op_not_found_returns_404(client):
    """POST agents/sync with unknown op_id returns 404 before spawning a task."""
    with patch("app.routers.agents.asyncio.create_task") as mock_create_task:
        mock_task = MagicMock()
        mock_task.add_done_callback = MagicMock()
        mock_create_task.return_value = mock_task

        resp = await client.post("/api/operations/nonexistent-op/agents/sync")

    assert resp.status_code == 404
    mock_create_task.assert_not_called()


# ---------------------------------------------------------------------------
# _sync_agents_background — success path (mock mode)
# ---------------------------------------------------------------------------


async def test_sync_agents_background_broadcasts_synced_on_mock_mode():
    """_sync_agents_background broadcasts agents.synced in MOCK_C2_ENGINE mode."""
    from app.routers.agents import _sync_agents_background

    with patch("app.routers.agents.settings") as mock_settings, \
         patch("app.routers.agents.ws_manager") as mock_ws:

        mock_settings.MOCK_C2_ENGINE = True
        mock_ws.broadcast = AsyncMock()

        await _sync_agents_background("op-test-1")

    mock_ws.broadcast.assert_awaited_once()
    call_args = mock_ws.broadcast.call_args
    assert call_args.args[0] == "op-test-1"
    assert call_args.args[1] == "agents.synced"
    payload = call_args.args[2]
    assert payload["operation_id"] == "op-test-1"
    assert "synced" in payload


# ---------------------------------------------------------------------------
# _sync_agents_background — failure path
# ---------------------------------------------------------------------------


async def test_sync_agents_background_broadcasts_sync_failed_on_exception():
    """_sync_agents_background broadcasts agents.sync_failed when C2 client raises."""
    from app.routers.agents import _sync_agents_background

    with patch("app.routers.agents.settings") as mock_settings, \
         patch("app.routers.agents.ws_manager") as mock_ws, \
         patch("app.routers.agents.C2EngineClient", create=True) as mock_c2_cls:

        mock_settings.MOCK_C2_ENGINE = False
        mock_settings.C2_ENGINE_URL = "http://fake-c2"
        mock_settings.C2_ENGINE_API_KEY = "fake-key"
        mock_ws.broadcast = AsyncMock()

        # Make the C2 client raise on sync_agents
        mock_client = AsyncMock()
        mock_client.sync_agents = AsyncMock(side_effect=RuntimeError("C2 unreachable"))
        mock_c2_cls.return_value = mock_client

        # Patch the import inside the function
        with patch.dict("sys.modules", {"app.clients.c2_client": MagicMock(
            C2EngineClient=mock_c2_cls
        )}):
            await _sync_agents_background("op-fail-1")

    mock_ws.broadcast.assert_awaited_once()
    call_args = mock_ws.broadcast.call_args
    assert call_args.args[1] == "agents.sync_failed"
    payload = call_args.args[2]
    assert "error" in payload
    assert "C2 unreachable" in payload["error"]


# ---------------------------------------------------------------------------
# POST /techniques/sync-c2 → 202 Accepted
# ---------------------------------------------------------------------------


async def test_techniques_sync_c2_returns_202(client):
    """POST techniques/sync-c2 returns 202 with status='sync_started'."""
    with patch("app.routers.techniques.asyncio.create_task") as mock_create_task:
        mock_task = MagicMock()
        mock_task.add_done_callback = MagicMock()
        mock_create_task.return_value = mock_task

        resp = await client.post("/api/techniques/sync-c2")

    assert resp.status_code == 202
    data = resp.json()
    assert data["status"] == "sync_started"


async def test_techniques_sync_c2_enqueues_background_task(client):
    """POST techniques/sync-c2 calls asyncio.create_task exactly once."""
    with patch("app.routers.techniques.asyncio.create_task") as mock_create_task:
        mock_task = MagicMock()
        mock_task.add_done_callback = MagicMock()
        mock_create_task.return_value = mock_task

        await client.post("/api/techniques/sync-c2")

    mock_create_task.assert_called_once()


# ---------------------------------------------------------------------------
# _sync_techniques_background — mock mode (no-op, no exception)
# ---------------------------------------------------------------------------


async def test_sync_techniques_background_mock_mode_noop():
    """_sync_techniques_background exits silently in MOCK_C2_ENGINE mode."""
    from app.routers.techniques import _sync_techniques_background

    with patch("app.routers.techniques.settings") as mock_settings, \
         patch("app.routers.techniques.ws_manager") as mock_ws:

        mock_settings.MOCK_C2_ENGINE = True
        mock_ws.broadcast = AsyncMock()

        # Should complete without error and without calling ws_manager
        await _sync_techniques_background()

    mock_ws.broadcast.assert_not_awaited()


# ---------------------------------------------------------------------------
# _sync_techniques_background — exception path (logs only, no WS broadcast)
# ---------------------------------------------------------------------------


async def test_sync_techniques_background_logs_on_exception(caplog):
    """_sync_techniques_background logs the exception and does not re-raise."""
    import logging
    from app.routers.techniques import _sync_techniques_background

    with patch("app.routers.techniques.settings") as mock_settings, \
         patch("app.routers.techniques.ws_manager") as mock_ws, \
         patch.dict("sys.modules", {"app.clients.c2_client": MagicMock(
             C2EngineClient=MagicMock(
                 return_value=MagicMock(
                     list_abilities=AsyncMock(side_effect=RuntimeError("C2 engine down")),
                     aclose=AsyncMock(),
                 )
             )
         )}):

        mock_settings.MOCK_C2_ENGINE = False
        mock_settings.C2_ENGINE_URL = "http://fake"
        mock_settings.C2_ENGINE_API_KEY = "key"
        mock_ws.broadcast = AsyncMock()

        with caplog.at_level(logging.ERROR, logger="app.routers.techniques"):
            await _sync_techniques_background()

    # Must not have called ws_manager.broadcast (no op_id available)
    mock_ws.broadcast.assert_not_awaited()
    # Must have logged the failure
    assert any("C2 engine down" in r.message or "background failed" in r.message
               for r in caplog.records)
