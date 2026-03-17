# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: azz093093.830330@gmail.com

"""Tests for MCP runtime robustness."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_config_has_reconnect_settings():
    from app.config import Settings

    s = Settings()
    assert hasattr(s, "MCP_RECONNECT_INTERVAL_SEC")
    assert hasattr(s, "MCP_MAX_RETRIES")
    assert s.MCP_RECONNECT_INTERVAL_SEC == 5
    assert s.MCP_MAX_RETRIES == 3


@pytest.mark.asyncio
async def test_config_has_transport_mode():
    from app.config import Settings

    s = Settings()
    assert hasattr(s, "MCP_TRANSPORT_MODE")
    assert s.MCP_TRANSPORT_MODE in ("stdio", "http", "auto")


@pytest.mark.asyncio
async def test_call_tool_respects_timeout():
    """call_tool() wraps session.call_tool in asyncio.wait_for."""
    from app.services.mcp_client_manager import MCPClientManager

    manager = MCPClientManager()
    mock_session = MagicMock()

    async def slow_call(*a, **kw):
        await asyncio.sleep(999)

    mock_session.call_tool = slow_call
    manager._sessions["srv"] = mock_session

    with patch("app.services.mcp_client_manager.settings") as s:
        s.MCP_TOOL_TIMEOUT_SEC = 0.05
        s.MCP_MAX_RETRIES = 3
        s.MCP_RECONNECT_INTERVAL_SEC = 5
        with pytest.raises(asyncio.TimeoutError):
            await manager.call_tool("srv", "tool", {})


@pytest.mark.asyncio
async def test_auto_reconnect_on_disconnected_session():
    """call_tool() reconnects if session is missing but config exists."""
    from app.services.mcp_client_manager import MCPClientManager, MCPServerConfig

    manager = MCPClientManager()
    config = MCPServerConfig(
        name="srv", transport="stdio", command="python", args=["-m", "server"]
    )
    manager._configs["srv"] = config

    async def mock_connect(cfg):
        mock_session = AsyncMock()
        mock_result = MagicMock(content=[], isError=False)
        mock_session.call_tool.return_value = mock_result
        manager._sessions["srv"] = mock_session

    manager._connect = mock_connect

    with patch("app.services.mcp_client_manager.settings") as s:
        s.MCP_TOOL_TIMEOUT_SEC = 30
        s.MCP_MAX_RETRIES = 3
        s.MCP_RECONNECT_INTERVAL_SEC = 5
        result = await manager.call_tool("srv", "tool", {})

    assert result["is_error"] is False


@pytest.mark.asyncio
async def test_http_transport_config_available():
    """mcp_servers.json has http_url entries for auto transport mode."""
    import json
    from pathlib import Path

    config_path = Path(__file__).resolve().parent.parent.parent / "mcp_servers.json"
    raw = json.loads(config_path.read_text())
    http_url_servers = {
        k: v for k, v in raw["servers"].items() if v.get("http_url")
    }
    # At least nmap-scanner, osint-recon, vuln-lookup have http_url
    assert len(http_url_servers) >= 3


@pytest.mark.asyncio
async def test_broadcast_global_sends_to_all_operations():
    from app.ws_manager import WebSocketManager

    ws_mgr = WebSocketManager()
    assert hasattr(ws_mgr, "broadcast_global")

    mock_ws1 = AsyncMock()
    mock_ws2 = AsyncMock()
    ws_mgr._connections["op1"] = {mock_ws1}
    ws_mgr._connections["op2"] = {mock_ws2}

    await ws_mgr.broadcast_global(
        "mcp.server.status", {"server": "s", "connected": True}
    )

    mock_ws1.send_text.assert_awaited_once()
    mock_ws2.send_text.assert_awaited_once()


@pytest.mark.asyncio
async def test_circuit_breaker_state_transitions():
    """Circuit breaker transitions: CLOSED → OPEN → HALF_OPEN → CLOSED."""
    from app.services.mcp_client_manager import CircuitBreakerState, CircuitState

    breaker = CircuitBreakerState()
    assert breaker.state == CircuitState.CLOSED

    # Record 3 failures → should transition to OPEN
    breaker.record_failure(max_retries=3)
    assert breaker.state == CircuitState.CLOSED  # only 1 failure
    breaker.record_failure(max_retries=3)
    assert breaker.state == CircuitState.CLOSED  # only 2 failures
    breaker.record_failure(max_retries=3)
    assert breaker.state == CircuitState.OPEN  # 3 failures → OPEN

    # OPEN → should not allow requests immediately
    assert not breaker.should_allow_request(base_interval=9999)

    # Simulate cooldown elapsed
    breaker.last_failure_time = 0  # far in the past
    assert breaker.should_allow_request(base_interval=1)
    assert breaker.state == CircuitState.HALF_OPEN

    # Success → back to CLOSED
    breaker.record_success()
    assert breaker.state == CircuitState.CLOSED
    assert breaker.failure_count == 0
