# Copyright 2026 Athena Contributors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Router tests for POST /operations/{op_id}/ooda/trigger — async 202 pattern."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# POST /operations/{op_id}/ooda/trigger → 202 Accepted (async / queued)
# ---------------------------------------------------------------------------


async def test_ooda_trigger_returns_202_queued(client):
    """POST ooda/trigger returns 202 with status='queued' immediately."""
    with patch("app.routers.ooda.asyncio.create_task") as mock_create_task:
        mock_task = MagicMock()
        mock_task.add_done_callback = MagicMock()
        mock_create_task.return_value = mock_task

        resp = await client.post("/api/operations/test-op-1/ooda/trigger")

    assert resp.status_code == 202
    data = resp.json()
    assert data["status"] == "queued"
    assert data["operation_id"] == "test-op-1"
    # iteration_id is internal only — must NOT be exposed in the response
    assert "iteration_id" not in data


async def test_ooda_trigger_enqueues_background_task(client):
    """POST ooda/trigger calls asyncio.create_task exactly once."""
    with patch("app.routers.ooda.asyncio.create_task") as mock_create_task:
        mock_task = MagicMock()
        mock_task.add_done_callback = MagicMock()
        mock_create_task.return_value = mock_task

        resp = await client.post("/api/operations/test-op-1/ooda/trigger")

    assert resp.status_code == 202
    mock_create_task.assert_called_once()


async def test_ooda_trigger_op_not_found_returns_404(client):
    """POST ooda/trigger with unknown op_id returns 404."""
    with patch("app.routers.ooda.asyncio.create_task") as mock_create_task:
        mock_task = MagicMock()
        mock_task.add_done_callback = MagicMock()
        mock_create_task.return_value = mock_task

        resp = await client.post("/api/operations/nonexistent-op/ooda/trigger")

    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Background function: _run_ooda_background
# ---------------------------------------------------------------------------


async def test_run_ooda_background_broadcasts_failed_on_exception():
    """_run_ooda_background: broadcasts ooda.failed when controller.trigger_cycle raises."""
    from app.routers.ooda import _run_ooda_background

    with patch("app.routers.ooda._get_controller") as mock_get_ctrl, \
         patch("aiosqlite.connect") as mock_connect, \
         patch("app.routers.ooda.ws_manager") as mock_ws:

        # Simulate controller.trigger_cycle raising an exception
        mock_ctrl = MagicMock()
        mock_ctrl.trigger_cycle = AsyncMock(side_effect=RuntimeError("OODA cycle exploded"))
        mock_get_ctrl.return_value = mock_ctrl

        # Make aiosqlite.connect behave as an async context manager
        mock_db = AsyncMock()
        mock_connect.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_connect.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_ws.broadcast = AsyncMock()

        iteration_id = "test-iter-uuid-1234"
        await _run_ooda_background(iteration_id, "op-fail-1")

    # ws_manager.broadcast must have been called with "ooda.failed"
    mock_ws.broadcast.assert_called_once()
    call_args = mock_ws.broadcast.call_args
    # positional args: (op_id, event_type, payload)
    assert call_args.args[1] == "ooda.failed"
    payload = call_args.args[2]
    assert "iteration_id" in payload
    assert payload["iteration_id"] == iteration_id
    assert "error" in payload
    assert "OODA cycle exploded" in payload["error"]
