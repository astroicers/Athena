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

"""Unit tests for ReconEngine — SPEC-018 Phase 12 acceptance criteria."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call

from app.services.recon_engine import ReconEngine


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_mock_db(ip_row=None):
    """Return a fully-mocked aiosqlite connection.

    ``ip_row`` is the value returned by ``cursor.fetchone()``.
    If ``None`` is passed, ``fetchone`` returns ``None`` (target not found).
    """
    db = AsyncMock()
    # Assignment to row_factory must silently succeed
    db.row_factory = None

    cursor = AsyncMock()
    cursor.fetchone = AsyncMock(return_value=ip_row)

    db.execute = AsyncMock(return_value=cursor)
    db.commit = AsyncMock()
    return db


def make_ip_row(ip: str = "192.168.1.100"):
    """Return a MagicMock that behaves like an aiosqlite.Row for ip_address."""
    row = MagicMock()
    row.__getitem__ = lambda self, k: ip if k == "ip_address" else None
    return row


# ---------------------------------------------------------------------------
# Test: scan in mock mode returns three services
# ---------------------------------------------------------------------------

async def test_scan_mock_returns_three_services():
    """MOCK_CALDERA=True → result.services has exactly 3 items."""
    row = make_ip_row("192.168.1.100")
    db = make_mock_db(ip_row=row)

    with patch("app.services.recon_engine.settings") as mock_settings, \
         patch("app.services.recon_engine.ws_manager.broadcast", new=AsyncMock()):

        mock_settings.MOCK_CALDERA = True

        result = await ReconEngine().scan(db, "op-001", "tgt-001")

    assert len(result.services) == 3
    assert result.ip_address == "192.168.1.100"
    assert result.os_guess == "Linux_2.6.x"


# ---------------------------------------------------------------------------
# Test: scan in mock mode writes exactly 5 facts
# ---------------------------------------------------------------------------

async def test_scan_mock_writes_facts():
    """MOCK_CALDERA=True → result.facts_written == 5 (3 services + 1 IP + 1 OS)."""
    row = make_ip_row("192.168.1.100")
    db = make_mock_db(ip_row=row)

    with patch("app.services.recon_engine.settings") as mock_settings, \
         patch("app.services.recon_engine.ws_manager.broadcast", new=AsyncMock()):

        mock_settings.MOCK_CALDERA = True

        result = await ReconEngine().scan(db, "op-001", "tgt-001")

    # 3 service facts + 1 network.host.ip fact + 1 host.os fact
    assert result.facts_written == 5


# ---------------------------------------------------------------------------
# Test: scan raises ValueError when target is not found
# ---------------------------------------------------------------------------

async def test_scan_target_not_found_raises():
    """fetchone() returning None → ValueError is raised."""
    db = make_mock_db(ip_row=None)

    with patch("app.services.recon_engine.settings") as mock_settings, \
         patch("app.services.recon_engine.ws_manager.broadcast", new=AsyncMock()):

        mock_settings.MOCK_CALDERA = True

        with pytest.raises(ValueError, match="tgt-missing"):
            await ReconEngine().scan(db, "op-001", "tgt-missing")
