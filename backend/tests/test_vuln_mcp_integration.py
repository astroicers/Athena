# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: azz093093.830330@gmail.com

"""Integration tests for VulnLookupService MCP branch."""

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


async def test_query_nvd_via_mcp_returns_results(mock_mcp_manager):
    """_query_nvd_via_mcp should parse vuln.cve facts into result dicts."""
    facts = [
        {
            "trait": "vuln.cve",
            "value": "CVE-2023-1234:cvss=7.5:severity=high:exploit=true:desc=A vuln in OpenSSH",
        },
        {
            "trait": "vuln.cve",
            "value": "CVE-2023-5678:cvss=4.0:severity=medium:exploit=false:desc=Another vuln",
        },
    ]
    mock_mcp_manager.call_tool.return_value = _mcp_result(facts)

    with patch("app.services.mcp_client_manager.get_mcp_manager", return_value=mock_mcp_manager):
        from app.services.vuln_lookup import VulnLookupService

        service = VulnLookupService()
        results = await service._query_nvd_via_mcp("cpe:/a:openbsd:openssh:7.4")

    assert len(results) == 2
    assert results[0]["cve_id"] == "CVE-2023-1234"
    assert results[0]["cvss_score"] == 7.5
    assert results[0]["exploit_available"] is True
    assert "OpenSSH" in results[0]["description"]
    assert results[1]["cve_id"] == "CVE-2023-5678"
    assert results[1]["exploit_available"] is False

    mock_mcp_manager.call_tool.assert_called_once_with(
        "vuln-lookup", "nvd_cve_lookup", {"cpe": "cpe:/a:openbsd:openssh:7.4"}
    )


async def test_query_nvd_via_mcp_empty_result(mock_mcp_manager):
    """_query_nvd_via_mcp should return empty list when no CVEs found."""
    mock_mcp_manager.call_tool.return_value = _mcp_result([])

    with patch("app.services.mcp_client_manager.get_mcp_manager", return_value=mock_mcp_manager):
        from app.services.vuln_lookup import VulnLookupService

        service = VulnLookupService()
        results = await service._query_nvd_via_mcp("cpe:/a:unknown:unknown:1.0")

    assert results == []


async def test_query_nvd_via_mcp_not_connected():
    """_query_nvd_via_mcp should raise ConnectionError."""
    manager = MagicMock()
    manager.is_connected.return_value = False

    with patch("app.services.mcp_client_manager.get_mcp_manager", return_value=manager):
        from app.services.vuln_lookup import VulnLookupService

        service = VulnLookupService()
        with pytest.raises(ConnectionError):
            await service._query_nvd_via_mcp("cpe:/a:openbsd:openssh:7.4")


async def test_query_nvd_via_mcp_no_manager():
    """_query_nvd_via_mcp should raise ConnectionError when manager is None."""
    with patch("app.services.mcp_client_manager.get_mcp_manager", return_value=None):
        from app.services.vuln_lookup import VulnLookupService

        service = VulnLookupService()
        with pytest.raises(ConnectionError):
            await service._query_nvd_via_mcp("cpe:/a:openbsd:openssh:7.4")


async def test_query_nvd_via_mcp_non_json_response(mock_mcp_manager):
    """_query_nvd_via_mcp should handle non-JSON gracefully."""
    mock_mcp_manager.call_tool.return_value = {
        "content": [{"type": "text", "text": "not json"}],
        "is_error": False,
    }

    with patch("app.services.mcp_client_manager.get_mcp_manager", return_value=mock_mcp_manager):
        from app.services.vuln_lookup import VulnLookupService

        service = VulnLookupService()
        results = await service._query_nvd_via_mcp("cpe:/a:openbsd:openssh:7.4")

    assert results == []
