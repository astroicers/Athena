# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: [TODO: contact email]

"""Unit tests for MCPEngineClient."""

from unittest.mock import AsyncMock, MagicMock

from app.clients.mcp_engine_client import MCPEngineClient
from app.services.mcp_client_manager import MCPToolInfo


async def test_execute_success():
    """execute() with successful MCP call returns ExecutionResult with facts."""
    mock_manager = MagicMock()
    mock_manager.get_server_for_tool.return_value = "test-server"
    mock_manager.call_tool = AsyncMock(
        return_value={
            "content": [
                {
                    "type": "text",
                    "text": '{"facts": [{"trait": "host.os", "value": "Linux"}]}',
                }
            ],
            "is_error": False,
        }
    )

    client = MCPEngineClient(manager=mock_manager)
    result = await client.execute("nmap_scan", "10.0.0.1")

    assert result.success is True
    assert result.execution_id
    assert len(result.facts) == 1
    assert result.facts[0]["trait"] == "host.os"
    assert result.error is None


async def test_execute_qualified_name():
    """execute() with 'server:tool' ability_id routes correctly."""
    mock_manager = MagicMock()
    mock_manager.call_tool = AsyncMock(
        return_value={
            "content": [{"type": "text", "text": "plain output"}],
            "is_error": False,
        }
    )

    client = MCPEngineClient(manager=mock_manager)
    result = await client.execute("recon-server:nmap_scan", "10.0.0.1")

    assert result.success is True
    mock_manager.call_tool.assert_awaited_once_with(
        "recon-server", "nmap_scan", {"target": "10.0.0.1"}
    )


async def test_execute_no_server_found():
    """execute() with unknown tool name returns failure."""
    mock_manager = MagicMock()
    mock_manager.get_server_for_tool.return_value = None

    client = MCPEngineClient(manager=mock_manager)
    result = await client.execute("unknown_tool", "10.0.0.1")

    assert result.success is False
    assert "No MCP server found" in result.error


async def test_execute_connection_error():
    """execute() handles ConnectionError gracefully."""
    mock_manager = MagicMock()
    mock_manager.get_server_for_tool.return_value = "server"
    mock_manager.call_tool = AsyncMock(
        side_effect=ConnectionError("server not connected")
    )

    client = MCPEngineClient(manager=mock_manager)
    result = await client.execute("tool", "10.0.0.1")

    assert result.success is False
    assert "not connected" in result.error


async def test_execute_mcp_error():
    """execute() when MCP returns is_error=True."""
    mock_manager = MagicMock()
    mock_manager.get_server_for_tool.return_value = "server"
    mock_manager.call_tool = AsyncMock(
        return_value={
            "content": [{"type": "text", "text": "Tool failed: timeout"}],
            "is_error": True,
        }
    )

    client = MCPEngineClient(manager=mock_manager)
    result = await client.execute("tool", "10.0.0.1")

    assert result.success is False
    assert "timeout" in result.error


async def test_list_abilities():
    """list_abilities() returns all discovered MCP tools."""
    mock_manager = MagicMock()
    mock_manager.list_all_tools.return_value = [
        MCPToolInfo(server_name="s1", tool_name="t1", description="D1", input_schema={}),
        MCPToolInfo(server_name="s2", tool_name="t2", description="D2", input_schema={}),
    ]

    client = MCPEngineClient(manager=mock_manager)
    abilities = await client.list_abilities()

    assert len(abilities) == 2
    assert abilities[0]["ability_id"] == "s1:t1"
    assert abilities[1]["name"] == "t2"


async def test_is_available_true():
    """is_available() True when at least one server is connected."""
    mock_manager = MagicMock()
    mock_manager.list_servers.return_value = [{"name": "s1", "connected": True}]

    client = MCPEngineClient(manager=mock_manager)
    assert await client.is_available() is True


async def test_is_available_false():
    """is_available() False when no servers are connected."""
    mock_manager = MagicMock()
    mock_manager.list_servers.return_value = [{"name": "s1", "connected": False}]

    client = MCPEngineClient(manager=mock_manager)
    assert await client.is_available() is False
