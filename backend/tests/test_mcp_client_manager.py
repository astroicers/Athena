# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: [TODO: contact email]

"""Unit tests for MCPClientManager."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.mcp_client_manager import MCPClientManager, MCPServerConfig, MCPToolInfo


async def test_startup_no_config_file():
    """startup() with missing config file logs warning and returns."""
    manager = MCPClientManager()
    with patch("app.services.mcp_client_manager.Path") as MockPath:
        mock_instance = MagicMock()
        MockPath.return_value = mock_instance
        mock_instance.is_absolute.return_value = True
        mock_instance.exists.return_value = False
        await manager.startup()
    assert len(manager._configs) == 0


async def test_startup_loads_disabled_server():
    """startup() parses config but skips disabled servers."""
    config_data = {
        "servers": {
            "test-server": {
                "transport": "stdio",
                "command": "python",
                "args": ["-m", "test_server"],
                "enabled": False,
            }
        }
    }
    manager = MCPClientManager()
    with patch("app.services.mcp_client_manager.Path") as MockPath:
        mock_instance = MagicMock()
        MockPath.return_value = mock_instance
        mock_instance.is_absolute.return_value = True
        mock_instance.exists.return_value = True
        mock_instance.read_text.return_value = json.dumps(config_data)
        await manager.startup()

    assert "test-server" in manager._configs
    assert manager._configs["test-server"].transport == "stdio"
    assert manager._configs["test-server"].enabled is False
    # Disabled server should NOT be connected
    assert "test-server" not in manager._sessions


async def test_call_tool_not_connected():
    """call_tool() raises ConnectionError when server not connected."""
    manager = MCPClientManager()
    with pytest.raises(ConnectionError, match="not connected"):
        await manager.call_tool("nonexistent", "some_tool", {})


async def test_call_tool_success():
    """call_tool() invokes session.call_tool and normalizes result."""
    manager = MCPClientManager()
    mock_session = AsyncMock()
    mock_content_block = MagicMock()
    mock_content_block.type = "text"
    mock_content_block.text = '{"facts": [{"trait": "host.os", "value": "Linux"}]}'
    mock_result = MagicMock()
    mock_result.content = [mock_content_block]
    mock_result.isError = False
    mock_session.call_tool.return_value = mock_result

    manager._sessions["test"] = mock_session

    result = await manager.call_tool("test", "scan", {"target": "10.0.0.1"})
    assert result["is_error"] is False
    assert len(result["content"]) == 1
    assert "facts" in result["content"][0]["text"]
    mock_session.call_tool.assert_awaited_once_with("scan", {"target": "10.0.0.1"})


async def test_health_check_connected():
    """health_check() returns True when list_tools succeeds."""
    manager = MCPClientManager()
    mock_session = AsyncMock()
    mock_session.list_tools.return_value = MagicMock(tools=[])
    manager._sessions["test"] = mock_session
    assert await manager.health_check("test") is True


async def test_health_check_not_connected():
    """health_check() returns False for unknown server."""
    manager = MCPClientManager()
    assert await manager.health_check("unknown") is False


async def test_list_servers():
    """list_servers() returns configured servers with connection status."""
    manager = MCPClientManager()
    manager._configs["s1"] = MCPServerConfig(
        name="s1", transport="stdio", enabled=True
    )
    manager._sessions["s1"] = AsyncMock()
    manager._tools["s1"] = [
        MCPToolInfo(server_name="s1", tool_name="t1", description="", input_schema={})
    ]

    servers = manager.list_servers()
    assert len(servers) == 1
    assert servers[0]["name"] == "s1"
    assert servers[0]["connected"] is True
    assert servers[0]["tool_count"] == 1


async def test_get_server_for_tool():
    """get_server_for_tool() reverse-looks up server by tool name."""
    manager = MCPClientManager()
    info = MCPToolInfo(
        server_name="recon-server",
        tool_name="nmap_scan",
        description="",
        input_schema={},
    )
    manager._tool_index["recon-server:nmap_scan"] = info

    assert manager.get_server_for_tool("nmap_scan") == "recon-server"
    assert manager.get_server_for_tool("nonexistent") is None
