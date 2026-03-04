# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: [TODO: contact email]

"""Integration tests for ReconEngine MCP branch."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def mock_mcp_manager():
    """Create a mock MCPClientManager."""
    manager = MagicMock()
    manager.is_connected.return_value = True
    manager.call_tool = AsyncMock()
    return manager


@pytest.fixture
def nmap_mcp_result():
    """Mock MCP call_tool result from nmap-scanner."""
    facts = [
        {"trait": "service.open_port", "value": "22/tcp/ssh/OpenSSH_7.4"},
        {"trait": "service.open_port", "value": "80/tcp/http/Apache_2.4.6"},
        {"trait": "network.host.ip", "value": "10.0.1.5"},
        {"trait": "host.os", "value": "Linux_2.6.x"},
    ]
    return {
        "content": [
            {
                "type": "text",
                "text": json.dumps({
                    "facts": facts,
                    "raw_output": "<nmap output>",
                }),
            }
        ],
        "is_error": False,
    }


async def test_scan_via_mcp_returns_services(mock_mcp_manager, nmap_mcp_result):
    """_scan_via_mcp should parse MCP result into ServiceInfo objects."""
    mock_mcp_manager.call_tool.return_value = nmap_mcp_result

    with patch("app.services.mcp_client_manager.get_mcp_manager", return_value=mock_mcp_manager):
        from app.services.recon_engine import ReconEngine

        engine = ReconEngine()
        services, os_guess, raw_xml, duration = await engine._scan_via_mcp("10.0.1.5")

    assert len(services) == 2
    assert services[0].port == 22
    assert services[0].service == "ssh"
    assert services[0].version == "OpenSSH 7.4"  # underscore→space
    assert services[1].port == 80
    assert os_guess == "Linux_2.6.x"
    assert raw_xml == "<nmap output>"
    assert duration > 0

    mock_mcp_manager.call_tool.assert_called_once_with(
        "nmap-scanner", "nmap_scan", {"target": "10.0.1.5"}
    )


async def test_scan_via_mcp_not_connected():
    """_scan_via_mcp should raise ConnectionError when server not connected."""
    manager = MagicMock()
    manager.is_connected.return_value = False

    with patch("app.services.mcp_client_manager.get_mcp_manager", return_value=manager):
        from app.services.recon_engine import ReconEngine

        engine = ReconEngine()
        with pytest.raises(ConnectionError):
            await engine._scan_via_mcp("10.0.1.5")


async def test_scan_via_mcp_no_manager():
    """_scan_via_mcp should raise ConnectionError when manager is None."""
    with patch("app.services.mcp_client_manager.get_mcp_manager", return_value=None):
        from app.services.recon_engine import ReconEngine

        engine = ReconEngine()
        with pytest.raises(ConnectionError):
            await engine._scan_via_mcp("10.0.1.5")


async def test_scan_via_mcp_empty_result(mock_mcp_manager):
    """_scan_via_mcp should handle empty scan results."""
    mock_mcp_manager.call_tool.return_value = {
        "content": [
            {
                "type": "text",
                "text": json.dumps({
                    "facts": [{"trait": "network.host.ip", "value": "10.0.1.5"}],
                    "raw_output": "",
                }),
            }
        ],
        "is_error": False,
    }

    with patch("app.services.mcp_client_manager.get_mcp_manager", return_value=mock_mcp_manager):
        from app.services.recon_engine import ReconEngine

        engine = ReconEngine()
        services, os_guess, raw_xml, duration = await engine._scan_via_mcp("10.0.1.5")

    assert len(services) == 0
    assert os_guess is None
