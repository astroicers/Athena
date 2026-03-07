# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: [TODO: contact email]

"""Unit tests for OSINTEngine — A.2 acceptance criteria."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.osint_engine import OSINTEngine, _MOCK_SUBDOMAINS


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_mock_db():
    db = AsyncMock()
    cursor = AsyncMock()
    cursor.fetchone = AsyncMock(return_value=None)
    cursor.rowcount = 1
    db.execute = AsyncMock(return_value=cursor)
    db.commit = AsyncMock()
    db.row_factory = None
    return db


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

async def test_mock_mode_returns_result():
    """MOCK_C2_ENGINE=True → returns mock OSINTResult without network I/O."""
    db = make_mock_db()

    with patch("app.services.osint_engine.settings") as mock_settings, \
         patch("app.services.osint_engine.ws_manager.broadcast", new=AsyncMock()):
        mock_settings.MOCK_C2_ENGINE = True
        mock_settings.OSINT_MAX_SUBDOMAINS = 500

        result = await OSINTEngine().discover(db, "op-001", "example.com")

    assert result.subdomains_found == len(_MOCK_SUBDOMAINS)
    assert result.domain == "example.com"
    assert result.operation_id == "op-001"
    assert "mock" in result.sources_used


async def test_mock_mode_writes_facts():
    """MOCK_C2_ENGINE=True → db.execute called for INSERT INTO facts."""
    db = make_mock_db()
    captured: list = []

    async def capture_execute(sql, params=None, /):
        captured.append((sql, params))
        cursor = AsyncMock()
        cursor.fetchone = AsyncMock(return_value=None)
        cursor.rowcount = 1
        return cursor

    db.execute = AsyncMock(side_effect=capture_execute)

    with patch("app.services.osint_engine.settings") as mock_settings, \
         patch("app.services.osint_engine.ws_manager.broadcast", new=AsyncMock()):
        mock_settings.MOCK_C2_ENGINE = True
        mock_settings.OSINT_MAX_SUBDOMAINS = 500

        await OSINTEngine().discover(db, "op-001", "example.com")

    insert_calls = [c for c in captured if "INTO facts" in str(c[0])]
    assert len(insert_calls) >= 1

    # All inserts should have osint category
    for _, params in insert_calls:
        if params:
            assert "osint" in params, f"Expected 'osint' category in params: {params}"


async def test_mcp_required_when_not_mock():
    """When MOCK_C2_ENGINE=False and MCP_ENABLED=False, discover raises ConnectionError."""
    db = make_mock_db()

    with patch("app.services.osint_engine.settings") as mock_settings, \
         patch("app.services.osint_engine.ws_manager.broadcast", new=AsyncMock()):
        mock_settings.MOCK_C2_ENGINE = False
        mock_settings.MCP_ENABLED = False
        mock_settings.OSINT_MAX_SUBDOMAINS = 500

        with pytest.raises(ConnectionError, match="MCP is required"):
            await OSINTEngine().discover(db, "op-001", "example.com")


async def test_parse_mcp_subdomains():
    """_parse_mcp_subdomains correctly parses osint.subdomain facts from MCP result."""
    engine = OSINTEngine()
    import json
    mcp_result = {
        "content": [{
            "type": "text",
            "text": json.dumps({
                "facts": [
                    {"trait": "osint.subdomain", "value": "www.example.com"},
                    {"trait": "osint.subdomain", "value": "api.example.com"},
                    {"trait": "other.trait", "value": "ignored"},
                ]
            }),
        }],
    }

    subs = engine._parse_mcp_subdomains(mcp_result)
    assert "www.example.com" in subs
    assert "api.example.com" in subs
    assert len(subs) == 2


async def test_create_target_if_missing_deduplicates():
    """_create_target_if_missing returns False when IP already exists (INSERT OR IGNORE)."""
    db = make_mock_db()

    call_count = 0

    async def side_effect(sql, params=None, /):
        nonlocal call_count
        call_count += 1
        cursor = AsyncMock()
        if "INSERT OR IGNORE" in sql:
            # First insert succeeds (rowcount=1), second is ignored (rowcount=0)
            cursor.rowcount = 1 if call_count == 1 else 0
        return cursor

    db.execute = AsyncMock(side_effect=side_effect)

    engine = OSINTEngine()

    # First call should create the target
    created1 = await engine._create_target_if_missing(db, "op-001", "www.test.com", "10.0.0.1")
    # Second call with same IP should not create (INSERT OR IGNORE → rowcount=0)
    created2 = await engine._create_target_if_missing(db, "op-001", "mail.test.com", "10.0.0.1")

    assert created1 is True
    assert created2 is False
