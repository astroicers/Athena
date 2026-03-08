# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: [TODO: contact email]

"""Unit tests for ReconEngine — SPEC-018 Phase 12 acceptance criteria."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call

from app.services.recon_engine import ReconEngine


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_mock_db(ip_row=None):
    """Return a fully-mocked aiosqlite connection.

    ``ip_row`` is the value returned by the first ``cursor.fetchone()`` call
    (target IP lookup). Subsequent fetchone calls return ``None`` to simulate
    no engagement record existing (backward-compatible / unrestricted mode).

    If ``None`` is passed, ``fetchone`` returns ``None`` on all calls
    (target not found).
    """
    db = AsyncMock()
    # Assignment to row_factory must silently succeed
    db.row_factory = None

    cursor = AsyncMock()
    if ip_row is None:
        cursor.fetchone = AsyncMock(return_value=None)
    else:
        # First call → ip_row (target lookup), subsequent calls → None (no engagement)
        cursor.fetchone = AsyncMock(side_effect=[ip_row, None])

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
    """MOCK_C2_ENGINE=True → result.services has exactly 3 items."""
    row = make_ip_row("192.168.1.100")
    db = make_mock_db(ip_row=row)

    with patch("app.services.recon_engine.settings") as mock_settings, \
         patch("app.services.recon_engine.ws_manager.broadcast", new=AsyncMock()):

        mock_settings.MOCK_C2_ENGINE = True

        result = await ReconEngine().scan(db, "op-001", "tgt-001")

    assert len(result.services) == 3
    assert result.ip_address == "192.168.1.100"
    assert result.os_guess == "Linux_2.6.x"


# ---------------------------------------------------------------------------
# Test: scan in mock mode writes exactly 5 facts
# ---------------------------------------------------------------------------

async def test_scan_mock_writes_facts():
    """MOCK_C2_ENGINE=True → result.facts_written == 5 (3 services + 1 IP + 1 OS)."""
    row = make_ip_row("192.168.1.100")
    db = make_mock_db(ip_row=row)

    with patch("app.services.recon_engine.settings") as mock_settings, \
         patch("app.services.recon_engine.ws_manager.broadcast", new=AsyncMock()):

        mock_settings.MOCK_C2_ENGINE = True

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

        mock_settings.MOCK_C2_ENGINE = True

        with pytest.raises(ValueError, match="tgt-missing"):
            await ReconEngine().scan(db, "op-001", "tgt-missing")


# ---------------------------------------------------------------------------
# SPEC-036: facts_written field in scan results
# ---------------------------------------------------------------------------

async def test_scan_result_includes_facts_written():
    """SPEC-036: ReconResult from scan() contains a ``facts_written`` int field."""
    row = make_ip_row("192.168.1.100")
    db = make_mock_db(ip_row=row)

    with patch("app.services.recon_engine.settings") as mock_settings, \
         patch("app.services.recon_engine.ws_manager.broadcast", new=AsyncMock()):

        mock_settings.MOCK_C2_ENGINE = True

        result = await ReconEngine().scan(db, "op-001", "tgt-001")

    assert hasattr(result, "facts_written"), "ReconResult must expose facts_written"
    assert isinstance(result.facts_written, int)
    assert result.facts_written > 0


async def test_facts_written_default_zero():
    """SPEC-036: a scan with zero services & no OS yields facts_written == 1.

    Even with no services detected, ``_write_facts`` still writes the
    ``network.host.ip`` fact, so the minimum is 1.  If the implementation
    changes to truly produce 0 (e.g. no IP fact), adjust this assertion.
    """
    row = make_ip_row("10.0.0.1")
    db = make_mock_db(ip_row=row)

    # Patch _scan_via_mcp to return empty services, no OS, no XML
    empty_mcp = AsyncMock(return_value=([], None, None, 0.01))

    with patch("app.services.recon_engine.settings") as mock_settings, \
         patch("app.services.recon_engine.ws_manager.broadcast", new=AsyncMock()), \
         patch.object(ReconEngine, "_scan_via_mcp", empty_mcp):

        mock_settings.MOCK_C2_ENGINE = False
        mock_settings.MCP_ENABLED = True
        mock_settings.NMAP_SCAN_TIMEOUT_SEC = 30
        mock_settings.VULN_LOOKUP_ENABLED = False
        mock_settings.EXPLOIT_VALIDATION_ENABLED = False

        result = await ReconEngine().scan(db, "op-001", "tgt-001")

    # Only the network.host.ip fact is written when services list is empty
    assert result.facts_written == 1


# ---------------------------------------------------------------------------
# SPEC-036: empty nmap result produces warning log
# ---------------------------------------------------------------------------

async def test_empty_nmap_result_warning_log(caplog):
    """SPEC-036: when MCP nmap returns 0 services a WARNING is logged."""
    import logging

    row = make_ip_row("10.0.0.1")
    db = make_mock_db(ip_row=row)

    # _scan_via_mcp returns empty services with some raw XML
    empty_mcp = AsyncMock(return_value=([], None, "<nmap/>", 0.01))

    with patch("app.services.recon_engine.settings") as mock_settings, \
         patch("app.services.recon_engine.ws_manager.broadcast", new=AsyncMock()), \
         patch.object(ReconEngine, "_scan_via_mcp", empty_mcp):

        mock_settings.MOCK_C2_ENGINE = False
        mock_settings.MCP_ENABLED = True
        mock_settings.NMAP_SCAN_TIMEOUT_SEC = 30
        mock_settings.VULN_LOOKUP_ENABLED = False
        mock_settings.EXPLOIT_VALIDATION_ENABLED = False

        with caplog.at_level(logging.WARNING, logger="app.services.recon_engine"):
            result = await ReconEngine().scan(db, "op-001", "tgt-001")

    assert result.services == []
    # Verify the warning log was emitted
    warning_msgs = [r.message for r in caplog.records if r.levelno >= logging.WARNING]
    assert any("0 services" in msg for msg in warning_msgs), (
        f"Expected a warning about 0 services; got: {warning_msgs}"
    )
