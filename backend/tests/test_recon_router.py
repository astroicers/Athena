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

"""Router tests for POST /operations/{op_id}/recon/scan — async 202 pattern."""

from unittest.mock import AsyncMock, patch

import pytest


# ---------------------------------------------------------------------------
# POST /operations/{op_id}/recon/scan → 202 Accepted (async / queued)
# ---------------------------------------------------------------------------

async def test_recon_scan_returns_202_queued(client):
    """POST recon/scan returns 202 with status='queued' immediately."""
    with patch("app.routers.recon.asyncio.create_task") as mock_create_task, \
         patch("app.routers.recon.ReconEngine"), \
         patch("app.routers.recon.InitialAccessEngine"):
        # create_task must not raise; background work is irrelevant for this test
        mock_create_task.return_value = None

        resp = await client.post(
            "/api/operations/test-op-1/recon/scan",
            json={"target_id": "test-target-1", "enable_initial_access": False},
        )

    assert resp.status_code == 202
    data = resp.json()
    assert data["status"] == "queued"
    assert data["target_id"] == "test-target-1"
    assert data["operation_id"] == "test-op-1"
    assert "scan_id" in data


async def test_recon_scan_enqueues_background_task(client):
    """POST recon/scan calls asyncio.create_task exactly once."""
    with patch("app.routers.recon.asyncio.create_task") as mock_create_task, \
         patch("app.routers.recon.ReconEngine"), \
         patch("app.routers.recon.InitialAccessEngine"):
        mock_create_task.return_value = None

        resp = await client.post(
            "/api/operations/test-op-1/recon/scan",
            json={"target_id": "test-target-1", "enable_initial_access": False},
        )

    assert resp.status_code == 202
    mock_create_task.assert_called_once()


async def test_recon_scan_inserts_queued_row(client, seeded_db):
    """POST recon/scan inserts a recon_scans row with status='queued'."""
    with patch("app.routers.recon.asyncio.create_task") as mock_create_task:
        mock_create_task.return_value = None

        resp = await client.post(
            "/api/operations/test-op-1/recon/scan",
            json={"target_id": "test-target-1", "enable_initial_access": False},
        )

    assert resp.status_code == 202
    scan_id = resp.json()["scan_id"]

    seeded_db.row_factory = __import__("aiosqlite").Row
    cursor = await seeded_db.execute(
        "SELECT status FROM recon_scans WHERE id = ?", (scan_id,)
    )
    row = await cursor.fetchone()
    assert row is not None
    # Row may have been updated to 'running'/'completed' by background if it ran,
    # but since create_task is mocked, it should remain 'queued'.
    assert row["status"] == "queued"


async def test_recon_scan_target_not_found_returns_404(client):
    """POST recon/scan with unknown target_id → 404, no background task."""
    with patch("app.routers.recon.asyncio.create_task") as mock_create_task:
        mock_create_task.return_value = None

        resp = await client.post(
            "/api/operations/test-op-1/recon/scan",
            json={"target_id": "nonexistent-target", "enable_initial_access": False},
        )

    assert resp.status_code == 404
    mock_create_task.assert_not_called()


async def test_recon_scan_op_not_found_returns_404(client):
    """POST recon/scan with unknown op_id → 404."""
    resp = await client.post(
        "/api/operations/nonexistent-op/recon/scan",
        json={"target_id": "test-target-1", "enable_initial_access": False},
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Background function: _run_scan_background
# ---------------------------------------------------------------------------

async def test_run_scan_background_marks_completed(tmp_db):
    """_run_scan_background happy path: DB row ends as 'completed'."""
    import aiosqlite
    from app.database import _CREATE_TABLES
    from app.models.recon import ReconResult, ServiceInfo
    from app.routers.recon import _run_scan_background, ReconScanRequest

    # Seed minimal data into tmp_db
    for ddl in _CREATE_TABLES:
        await tmp_db.execute(ddl)
    await tmp_db.execute(
        "INSERT INTO operations (id, code, name, codename, strategic_intent) "
        "VALUES ('op-bg-1', 'OP-BG', 'BG Test', 'BG', 'test')"
    )
    await tmp_db.execute(
        "INSERT INTO targets (id, hostname, ip_address, os, role, operation_id) "
        "VALUES ('tgt-bg-1', 'host-bg', '10.0.0.99', 'Linux', 'web', 'op-bg-1')"
    )
    await tmp_db.execute(
        "INSERT INTO recon_scans (id, operation_id, target_id, status, started_at) "
        "VALUES ('scan-bg-1', 'op-bg-1', 'tgt-bg-1', 'queued', '2026-01-01T00:00:00')"
    )
    await tmp_db.commit()

    mock_recon_result = ReconResult(
        target_id="tgt-bg-1",
        operation_id="op-bg-1",
        ip_address="10.0.0.99",
        os_guess="Linux_2.6.x",
        services=[
            ServiceInfo(port=22, protocol="tcp", service="ssh", version="OpenSSH 8.9", state="open")
        ],
        facts_written=3,
        scan_duration_sec=0.1,
        raw_xml=None,
    )

    body = ReconScanRequest(
        target_id="tgt-bg-1",
        enable_initial_access=False,
    )

    db_path = ":memory:"  # we patch connect to return tmp_db

    # ws_manager is imported inside _run_scan_background via local import,
    # so we must patch it on the app.ws_manager module.
    with patch("app.routers.recon._DB_FILE", db_path), \
         patch("aiosqlite.connect") as mock_connect, \
         patch("app.routers.recon.ReconEngine") as MockReconEngine, \
         patch("app.ws_manager.ws_manager") as mock_ws:

        # Make aiosqlite.connect return tmp_db as an async context manager
        mock_connect.return_value.__aenter__ = AsyncMock(return_value=tmp_db)
        mock_connect.return_value.__aexit__ = AsyncMock(return_value=False)

        MockReconEngine.return_value.scan = AsyncMock(return_value=mock_recon_result)
        mock_ws.broadcast = AsyncMock()

        await _run_scan_background(
            "scan-bg-1", "op-bg-1", "tgt-bg-1", "10.0.0.99", body
        )

    tmp_db.row_factory = aiosqlite.Row
    cursor = await tmp_db.execute(
        "SELECT status FROM recon_scans WHERE id = 'scan-bg-1'"
    )
    row = await cursor.fetchone()
    assert row is not None
    assert row["status"] == "completed"

    # Verify recon.completed was broadcast
    calls = [str(c) for c in mock_ws.broadcast.call_args_list]
    assert any("recon.completed" in c for c in calls), "recon.completed was not broadcast"


async def test_run_scan_background_marks_failed_on_exception(tmp_db):
    """_run_scan_background: DB row ends as 'failed' when ReconEngine raises."""
    import aiosqlite
    from app.database import _CREATE_TABLES
    from app.routers.recon import _run_scan_background, ReconScanRequest

    for ddl in _CREATE_TABLES:
        await tmp_db.execute(ddl)
    await tmp_db.execute(
        "INSERT INTO operations (id, code, name, codename, strategic_intent) "
        "VALUES ('op-bg-2', 'OP-BG2', 'BG Test 2', 'BG2', 'test')"
    )
    await tmp_db.execute(
        "INSERT INTO targets (id, hostname, ip_address, os, role, operation_id) "
        "VALUES ('tgt-bg-2', 'host-bg2', '10.0.0.98', 'Linux', 'web', 'op-bg-2')"
    )
    await tmp_db.execute(
        "INSERT INTO recon_scans (id, operation_id, target_id, status, started_at) "
        "VALUES ('scan-bg-2', 'op-bg-2', 'tgt-bg-2', 'queued', '2026-01-01T00:00:00')"
    )
    await tmp_db.commit()

    body = ReconScanRequest(
        target_id="tgt-bg-2",
        enable_initial_access=False,
    )

    # ws_manager is imported inside _run_scan_background via local import,
    # so we must patch it on the app.ws_manager module.
    with patch("app.routers.recon._DB_FILE", ":memory:"), \
         patch("aiosqlite.connect") as mock_connect, \
         patch("app.routers.recon.ReconEngine") as MockReconEngine, \
         patch("app.ws_manager.ws_manager") as mock_ws:

        mock_connect.return_value.__aenter__ = AsyncMock(return_value=tmp_db)
        mock_connect.return_value.__aexit__ = AsyncMock(return_value=False)

        MockReconEngine.return_value.scan = AsyncMock(
            side_effect=RuntimeError("nmap timeout")
        )
        mock_ws.broadcast = AsyncMock()

        await _run_scan_background(
            "scan-bg-2", "op-bg-2", "tgt-bg-2", "10.0.0.98", body
        )

    tmp_db.row_factory = aiosqlite.Row
    cursor = await tmp_db.execute(
        "SELECT status FROM recon_scans WHERE id = 'scan-bg-2'"
    )
    row = await cursor.fetchone()
    assert row is not None
    assert row["status"] == "failed"

    # ws_manager.broadcast should have been called with "recon.failed"
    calls = [str(c) for c in mock_ws.broadcast.call_args_list]
    assert any("recon.failed" in c for c in calls)
