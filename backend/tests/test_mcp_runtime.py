# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: [TODO: contact email]

"""Tests for MCP runtime robustness (Phase 3)."""

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
        result = await manager.call_tool("srv", "tool", {})

    assert result["is_error"] is False


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
