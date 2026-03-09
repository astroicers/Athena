# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: [TODO: contact email]

"""Tests for Engine Fallback Chain — SPEC-040 Component B."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.engine_router import (
    EngineRouter,
    _is_terminal_error,
    _FALLBACK_CHAIN,
    _TERMINAL_ERRORS,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_router():
    """Create EngineRouter with mocked dependencies."""
    c2 = MagicMock()
    fact_collector = MagicMock()
    ws = MagicMock()
    ws.broadcast = AsyncMock()
    mcp = MagicMock()
    return EngineRouter(c2, fact_collector, ws, mcp)


def _success_result(engine="mcp_ssh", exec_id="exec-1"):
    return {
        "execution_id": exec_id,
        "technique_id": "T1059.004",
        "target_id": "tgt-1",
        "engine": engine,
        "status": "success",
        "result_summary": "ok",
        "facts_collected_count": 1,
        "error": None,
    }


def _failed_result(engine="mcp_ssh", error="connection timed out", exec_id="exec-1"):
    return {
        "execution_id": exec_id,
        "technique_id": "T1059.004",
        "target_id": "tgt-1",
        "engine": engine,
        "status": "failed",
        "result_summary": None,
        "facts_collected_count": 0,
        "error": error,
    }


# ---------------------------------------------------------------------------
# TC-B1: Primary success -> no fallback
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_primary_success_no_fallback():
    """Primary engine succeeds -> return directly, no fallback attempted."""
    router = _make_router()

    with patch.object(router, "_execute_single", new_callable=AsyncMock,
                      return_value=_success_result("mcp_ssh")):
        db = AsyncMock()
        result = await router.execute(
            db, "T1059.004", "tgt-1", "mcp_ssh", "op-1"
        )

    assert result["status"] == "success"
    assert result["fallback_history"] == []
    assert result["final_engine"] == "mcp_ssh"


# ---------------------------------------------------------------------------
# TC-B2: Primary fails -> fallback succeeds
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_fallback_success():
    """mcp_ssh fails (non-terminal) -> metasploit succeeds."""
    router = _make_router()

    async def side_effect(db, tech, tgt, engine, op, ooda=None):
        if engine == "mcp_ssh":
            return _failed_result("mcp_ssh", "connection timed out")
        return _success_result("metasploit")

    with patch.object(router, "_execute_single", new_callable=AsyncMock,
                      side_effect=side_effect):
        db = AsyncMock()
        result = await router.execute(
            db, "T1059.004", "tgt-1", "mcp_ssh", "op-1"
        )

    assert result["status"] == "success"
    assert result["final_engine"] == "metasploit"
    assert len(result["fallback_history"]) == 1
    assert result["fallback_history"][0]["engine"] == "mcp_ssh"
    assert result["fallback_history"][0]["error"] == "connection timed out"


# ---------------------------------------------------------------------------
# TC-B3: Terminal error -> no fallback
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_terminal_error_no_fallback():
    """Primary returns terminal error -> no fallback attempted."""
    router = _make_router()

    with patch.object(router, "_execute_single", new_callable=AsyncMock,
                      return_value=_failed_result(
                          "mcp_ssh",
                          "scope violation — target outside authorized range"
                      )):
        db = AsyncMock()
        result = await router.execute(
            db, "T1059.004", "tgt-1", "mcp_ssh", "op-1"
        )

    assert result["status"] == "failed"
    assert result["fallback_history"] == []
    assert "scope violation" in result["error"]


# ---------------------------------------------------------------------------
# TC-B4: All engines fail
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_all_engines_fail():
    """mcp_ssh -> metasploit -> c2 all fail."""
    router = _make_router()
    call_count = 0

    async def side_effect(db, tech, tgt, engine, op, ooda=None):
        nonlocal call_count
        call_count += 1
        return _failed_result(engine, f"error from {engine}")

    with patch.object(router, "_execute_single", new_callable=AsyncMock,
                      side_effect=side_effect):
        db = AsyncMock()
        result = await router.execute(
            db, "T1059.004", "tgt-1", "mcp_ssh", "op-1"
        )

    assert result["status"] == "failed"
    # Primary (mcp_ssh) + 2 fallbacks (metasploit, c2) = 3 calls
    assert call_count == 3
    # fallback_history has all three failures (primary + both fallbacks)
    assert len(result["fallback_history"]) == 3
    assert result["fallback_history"][0]["engine"] == "mcp_ssh"
    assert result["fallback_history"][1]["engine"] == "metasploit"
    assert result["fallback_history"][2]["engine"] == "c2"
    assert result["final_engine"] == "c2"


# ---------------------------------------------------------------------------
# TC-B5: Fallback terminal error stops chain
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_fallback_terminal_error_stops_chain():
    """mcp_ssh fails (non-terminal) -> metasploit returns terminal error -> c2 not tried."""
    router = _make_router()
    engines_tried = []

    async def side_effect(db, tech, tgt, engine, op, ooda=None):
        engines_tried.append(engine)
        if engine == "mcp_ssh":
            return _failed_result("mcp_ssh", "connection timed out")
        if engine == "metasploit":
            return _failed_result("metasploit", "platform mismatch: Windows required")
        return _success_result(engine)

    with patch.object(router, "_execute_single", new_callable=AsyncMock,
                      side_effect=side_effect):
        db = AsyncMock()
        result = await router.execute(
            db, "T1059.004", "tgt-1", "mcp_ssh", "op-1"
        )

    assert "c2" not in engines_tried
    assert len(result["fallback_history"]) == 1  # only mcp_ssh failure recorded
    assert result["final_engine"] == "metasploit"


# ---------------------------------------------------------------------------
# TC-B6: WebSocket event verification
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_fallback_websocket_event():
    """Verify broadcast is called with execution.fallback event."""
    router = _make_router()

    async def side_effect(db, tech, tgt, engine, op, ooda=None):
        if engine == "mcp_ssh":
            return _failed_result("mcp_ssh", "connection timed out")
        return _success_result("metasploit")

    with patch.object(router, "_execute_single", new_callable=AsyncMock,
                      side_effect=side_effect):
        db = AsyncMock()
        result = await router.execute(
            db, "T1059.004", "tgt-1", "mcp_ssh", "op-1"
        )

    # Verify broadcast was called
    router._ws.broadcast.assert_called_once()
    call_args = router._ws.broadcast.call_args
    assert call_args[0][0] == "op-1"
    assert call_args[0][1] == "execution.fallback"

    payload = call_args[0][2]
    assert payload["failed_engine"] == "mcp_ssh"
    assert payload["fallback_engine"] == "metasploit"
    assert payload["failed_error"] == "connection timed out"
    assert payload["attempt"] == 1
    assert payload["max_attempts"] == 2  # mcp_ssh has 2 fallbacks


# ---------------------------------------------------------------------------
# TC-B7: Unknown engine -> no fallback
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_unknown_engine_no_fallback():
    """engine='mcp' not in _FALLBACK_CHAIN -> no fallback, return directly."""
    router = _make_router()

    with patch.object(router, "_execute_single", new_callable=AsyncMock,
                      return_value=_failed_result("mcp", "some error")):
        db = AsyncMock()
        result = await router.execute(
            db, "T1059.004", "tgt-1", "mcp", "op-1"
        )

    assert result["status"] == "failed"
    # Primary failure is recorded but no fallback engines
    assert len(result["fallback_history"]) == 1
    assert result["fallback_history"][0]["engine"] == "mcp"
    assert result["final_engine"] == "mcp"


# ---------------------------------------------------------------------------
# TC-B8: _is_terminal_error function tests
# ---------------------------------------------------------------------------

class TestIsTerminalError:
    def test_scope_violation(self):
        assert _is_terminal_error("scope violation — target outside range") is True

    def test_platform_mismatch(self):
        assert _is_terminal_error("Platform Mismatch: Windows required") is True

    def test_blocked_by_roe(self):
        assert _is_terminal_error("blocked by rules of engagement") is True

    def test_connection_timeout_not_terminal(self):
        assert _is_terminal_error("connection timed out") is False

    def test_auth_failed_not_terminal(self):
        assert _is_terminal_error("authentication failed") is False

    def test_none_not_terminal(self):
        assert _is_terminal_error(None) is False

    def test_empty_not_terminal(self):
        assert _is_terminal_error("") is False
