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

"""Unit tests for InitialAccessEngine — SPEC-018 Phase 12 acceptance criteria."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call

from app.services.initial_access_engine import InitialAccessEngine


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_mock_db():
    """Return a fully-mocked aiosqlite connection."""
    db = AsyncMock()
    cursor = AsyncMock()
    cursor.fetchone = AsyncMock(return_value=None)
    db.execute = AsyncMock(return_value=cursor)
    db.commit = AsyncMock()
    return db


# ---------------------------------------------------------------------------
# Test 1: SSH in mock mode returns a successful result
# ---------------------------------------------------------------------------

async def test_ssh_mock_returns_success():
    """MOCK_CALDERA=True → success=True, method='ssh_credential', credential='msfadmin:msfadmin'."""
    db = make_mock_db()

    with patch("app.services.initial_access_engine.settings") as mock_settings, \
         patch("app.services.initial_access_engine.ws_manager.broadcast", new=AsyncMock()):

        mock_settings.MOCK_CALDERA = True

        result = await InitialAccessEngine().try_ssh_login(
            db, "op-001", "tgt-001", "192.168.1.100"
        )

    assert result.success is True
    assert result.method == "ssh_credential"
    assert result.credential == "msfadmin:msfadmin"
    assert result.agent_deployed is False


# ---------------------------------------------------------------------------
# Test 2: SSH in mock mode inserts a credential.ssh fact
# ---------------------------------------------------------------------------

async def test_ssh_mock_writes_credential_fact():
    """MOCK_CALDERA=True → db.execute is called with trait='credential.ssh'."""
    db = make_mock_db()
    captured_calls: list = []

    async def capture_execute(sql, params=None, /):
        captured_calls.append((sql, params))
        cursor = AsyncMock()
        return cursor

    db.execute = AsyncMock(side_effect=capture_execute)

    with patch("app.services.initial_access_engine.settings") as mock_settings, \
         patch("app.services.initial_access_engine.ws_manager.broadcast", new=AsyncMock()):

        mock_settings.MOCK_CALDERA = True

        await InitialAccessEngine().try_ssh_login(
            db, "op-001", "tgt-001", "192.168.1.100"
        )

    # At least one INSERT into facts should contain 'credential.ssh'
    insert_calls = [
        (sql, params)
        for sql, params in captured_calls
        if "INSERT INTO facts" in sql
    ]
    assert len(insert_calls) >= 1, "Expected at least one INSERT INTO facts call"

    # The params tuple must contain the trait value 'credential.ssh'
    _, params = insert_calls[0]
    assert "credential.ssh" in params, (
        f"'credential.ssh' not found in INSERT params: {params}"
    )


# ---------------------------------------------------------------------------
# Test 3: SSH in real mode — first credential succeeds
# ---------------------------------------------------------------------------

async def test_ssh_real_success():
    """MOCK_CALDERA=False, asyncssh.connect succeeds for msfadmin:msfadmin."""
    db = make_mock_db()

    # Build a mock asyncssh connection context manager
    mock_conn = AsyncMock()
    mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_conn.__aexit__ = AsyncMock(return_value=False)

    with patch("app.services.initial_access_engine.settings") as mock_settings, \
         patch("app.services.initial_access_engine.ws_manager.broadcast", new=AsyncMock()), \
         patch.dict("sys.modules", {"asyncssh": MagicMock()}):

        mock_settings.MOCK_CALDERA = False

        import sys
        mock_asyncssh = sys.modules["asyncssh"]
        mock_asyncssh.connect = AsyncMock(return_value=mock_conn)
        mock_asyncssh.Error = Exception

        result = await InitialAccessEngine().try_ssh_login(
            db, "op-001", "tgt-001", "192.168.1.100"
        )

    assert result.success is True
    # First credential attempted is now "vagrant:vagrant" (generic list sorted by likelihood)
    assert result.credential == "vagrant:vagrant"


# ---------------------------------------------------------------------------
# Test 4: SSH in real mode — all credentials fail
# ---------------------------------------------------------------------------

async def test_ssh_real_all_fail():
    """MOCK_CALDERA=False, asyncssh.connect always raises → success=False, method='none'."""
    db = make_mock_db()

    with patch("app.services.initial_access_engine.settings") as mock_settings, \
         patch("app.services.initial_access_engine.ws_manager.broadcast", new=AsyncMock()), \
         patch.dict("sys.modules", {"asyncssh": MagicMock()}):

        mock_settings.MOCK_CALDERA = False

        import sys
        mock_asyncssh = sys.modules["asyncssh"]

        # Make asyncssh.Error a real exception subclass so except clauses work
        class FakeAsyncSSHError(Exception):
            pass

        mock_asyncssh.Error = FakeAsyncSSHError
        mock_asyncssh.connect = AsyncMock(
            side_effect=FakeAsyncSSHError("Connection refused")
        )

        result = await InitialAccessEngine().try_ssh_login(
            db, "op-001", "tgt-001", "192.168.1.100"
        )

    assert result.success is False
    assert result.method == "none"
