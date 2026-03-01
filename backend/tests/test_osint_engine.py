# Copyright 2026 Athena Contributors
# Licensed under the Apache License, Version 2.0

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
    db.execute = AsyncMock(return_value=cursor)
    db.commit = AsyncMock()
    db.row_factory = None
    return db


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

async def test_mock_mode_returns_result():
    """MOCK_CALDERA=True → returns mock OSINTResult without network I/O."""
    db = make_mock_db()

    with patch("app.services.osint_engine.settings") as mock_settings, \
         patch("app.services.osint_engine.ws_manager.broadcast", new=AsyncMock()):
        mock_settings.MOCK_CALDERA = True
        mock_settings.OSINT_MAX_SUBDOMAINS = 500

        result = await OSINTEngine().discover(db, "op-001", "example.com")

    assert result.subdomains_found == len(_MOCK_SUBDOMAINS)
    assert result.domain == "example.com"
    assert result.operation_id == "op-001"
    assert "mock" in result.sources_used


async def test_mock_mode_writes_facts():
    """MOCK_CALDERA=True → db.execute called for INSERT INTO facts."""
    db = make_mock_db()
    captured: list = []

    async def capture_execute(sql, params=None, /):
        captured.append((sql, params))
        cursor = AsyncMock()
        cursor.fetchone = AsyncMock(return_value=None)
        return cursor

    db.execute = AsyncMock(side_effect=capture_execute)

    with patch("app.services.osint_engine.settings") as mock_settings, \
         patch("app.services.osint_engine.ws_manager.broadcast", new=AsyncMock()):
        mock_settings.MOCK_CALDERA = True
        mock_settings.OSINT_MAX_SUBDOMAINS = 500

        await OSINTEngine().discover(db, "op-001", "example.com")

    insert_calls = [c for c in captured if "INSERT INTO facts" in str(c[0])]
    assert len(insert_calls) >= 1

    # All inserts should have osint category
    for _, params in insert_calls:
        if params:
            assert "osint" in params, f"Expected 'osint' category in params: {params}"


async def test_crtsh_query_parsing():
    """_crtsh_query correctly parses subdomains from crt.sh JSON response."""
    engine = OSINTEngine()
    mock_response_data = [
        {"name_value": "mail.example.com\nwww.example.com"},
        {"name_value": "*.example.com"},  # wildcard — should be excluded
        {"name_value": "api.example.com"},
    ]

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_response_data
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        with patch("app.services.osint_engine.settings") as mock_settings:
            mock_settings.OSINT_REQUEST_TIMEOUT_SEC = 30
            subs = await engine._crtsh_query("example.com")

    # Should include subdomain entries, not wildcards, not apex
    assert "mail.example.com" in subs
    assert "www.example.com" in subs
    assert "api.example.com" in subs
    # Wildcard entries should be filtered out
    assert not any(s.startswith("*") for s in subs)


async def test_subfinder_graceful_degradation():
    """When subfinder binary is not found, returns empty list without error."""
    engine = OSINTEngine()

    with patch("asyncio.create_subprocess_exec", side_effect=FileNotFoundError("subfinder not found")):
        result = await engine._subfinder_query("example.com")

    assert result == []


async def test_create_target_if_missing_deduplicates():
    """_create_target_if_missing returns False when IP already exists for this operation."""
    db = make_mock_db()

    # First call: target doesn't exist (fetchone returns None)
    cursor_miss = AsyncMock()
    cursor_miss.fetchone = AsyncMock(return_value=None)

    # Second call: target already exists (fetchone returns a row)
    cursor_hit = AsyncMock()
    cursor_hit.fetchone = AsyncMock(return_value={"id": "existing-target-id"})

    call_count = 0

    async def side_effect(sql, params=None, /):
        nonlocal call_count
        call_count += 1
        if "SELECT id FROM targets" in sql:
            if call_count == 1:
                return cursor_miss
            else:
                return cursor_hit
        cursor = AsyncMock()
        cursor.fetchone = AsyncMock(return_value=None)
        return cursor

    db.execute = AsyncMock(side_effect=side_effect)

    engine = OSINTEngine()

    # First call should create the target
    created1 = await engine._create_target_if_missing(db, "op-001", "www.test.com", "10.0.0.1")
    # Second call with same IP should not create
    created2 = await engine._create_target_if_missing(db, "op-001", "mail.test.com", "10.0.0.1")

    assert created1 is True
    assert created2 is False
