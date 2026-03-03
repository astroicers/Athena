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
    assert "iteration_id" in data
    # iteration_id must be a non-empty UUID-like string
    assert len(data["iteration_id"]) == 36


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
