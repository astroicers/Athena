# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: [TODO: contact email]

"""Integration tests for OSINTEngine MCP branch."""

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


def _mcp_result(facts, raw_output=""):
    """Helper to build MCP call_tool result dict."""
    return {
        "content": [
            {
                "type": "text",
                "text": json.dumps({"facts": facts, "raw_output": raw_output}),
            }
        ],
        "is_error": False,
    }


async def test_discover_via_mcp_basic(mock_mcp_manager):
    """_discover_via_mcp should aggregate crtsh + resolve results."""
    # crtsh returns 2 subdomains
    crtsh_facts = [
        {"trait": "osint.subdomain", "value": "www.example.com"},
        {"trait": "osint.subdomain", "value": "api.example.com"},
    ]
    # resolve returns IPs
    resolve_facts = [
        {"trait": "osint.resolved_ip", "value": "api.example.com:1.2.3.4"},
        {"trait": "osint.resolved_ip", "value": "www.example.com:5.6.7.8"},
    ]

    mock_mcp_manager.call_tool.side_effect = [
        _mcp_result(crtsh_facts),    # crtsh_query
        _mcp_result(resolve_facts),  # dns_resolve
    ]

    with (
        patch("app.services.mcp_client_manager.get_mcp_manager", return_value=mock_mcp_manager),
        patch("app.services.osint_engine.settings") as mock_settings,
    ):
        mock_settings.MCP_ENABLED = True
        mock_settings.SUBFINDER_ENABLED = False

        from app.services.osint_engine import OSINTEngine

        engine = OSINTEngine()
        infos, sources = await engine._discover_via_mcp("example.com", 100)

    assert len(infos) == 2
    assert "crtsh" in sources
    assert infos[0].subdomain == "api.example.com"
    assert infos[0].resolved_ips == ["1.2.3.4"]


async def test_discover_via_mcp_with_subfinder(mock_mcp_manager):
    """_discover_via_mcp should include subfinder when enabled."""
    crtsh_facts = [
        {"trait": "osint.subdomain", "value": "www.example.com"},
    ]
    subfinder_facts = [
        {"trait": "osint.subdomain", "value": "dev.example.com"},
    ]
    resolve_facts = [
        {"trait": "osint.resolved_ip", "value": "www.example.com:1.1.1.1"},
        {"trait": "osint.resolved_ip", "value": "dev.example.com:2.2.2.2"},
    ]

    mock_mcp_manager.call_tool.side_effect = [
        _mcp_result(crtsh_facts),
        _mcp_result(subfinder_facts),
        _mcp_result(resolve_facts),
    ]

    with (
        patch("app.services.mcp_client_manager.get_mcp_manager", return_value=mock_mcp_manager),
        patch("app.services.osint_engine.settings") as mock_settings,
    ):
        mock_settings.MCP_ENABLED = True
        mock_settings.SUBFINDER_ENABLED = True

        from app.services.osint_engine import OSINTEngine

        engine = OSINTEngine()
        infos, sources = await engine._discover_via_mcp("example.com", 100)

    assert len(infos) == 2
    assert "crtsh" in sources
    assert "subfinder" in sources


async def test_discover_via_mcp_not_connected():
    """_discover_via_mcp should raise ConnectionError when not connected."""
    manager = MagicMock()
    manager.is_connected.return_value = False

    with patch("app.services.mcp_client_manager.get_mcp_manager", return_value=manager):
        from app.services.osint_engine import OSINTEngine

        engine = OSINTEngine()
        with pytest.raises(ConnectionError):
            await engine._discover_via_mcp("example.com", 100)


async def test_parse_mcp_subdomains():
    """_parse_mcp_subdomains should extract subdomain values from MCP result."""
    from app.services.osint_engine import OSINTEngine

    result = _mcp_result([
        {"trait": "osint.subdomain", "value": "a.example.com"},
        {"trait": "osint.subdomain", "value": "b.example.com"},
        {"trait": "other.trait", "value": "ignored"},
    ])
    subs = OSINTEngine._parse_mcp_subdomains(result)
    assert subs == ["a.example.com", "b.example.com"]


async def test_parse_mcp_resolved_ips():
    """_parse_mcp_resolved_ips should build {subdomain: [ip]} dict."""
    from app.services.osint_engine import OSINTEngine

    result = _mcp_result([
        {"trait": "osint.resolved_ip", "value": "a.example.com:1.1.1.1"},
        {"trait": "osint.resolved_ip", "value": "a.example.com:2.2.2.2"},
        {"trait": "osint.resolved_ip", "value": "b.example.com:3.3.3.3"},
    ])
    resolved = OSINTEngine._parse_mcp_resolved_ips(result)
    assert resolved["a.example.com"] == ["1.1.1.1", "2.2.2.2"]
    assert resolved["b.example.com"] == ["3.3.3.3"]
