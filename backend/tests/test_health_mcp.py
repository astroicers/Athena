# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: [TODO: contact email]

"""Tests for MCP status in health endpoint."""

from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_health_includes_mcp_servers(client):
    """When MCP_ENABLED, health response includes mcp_servers."""
    mock_mgr = MagicMock()
    mock_mgr.list_servers.return_value = [
        {"name": "nmap-scanner", "connected": True, "tool_count": 1}
    ]
    with patch("app.routers.health.settings") as s, patch(
        "app.routers.health.get_mcp_manager", return_value=mock_mgr, create=True
    ):
        s.MOCK_C2_ENGINE = True
        s.MOCK_LLM = True
        s.MCP_ENABLED = True
        s.ANTHROPIC_API_KEY = ""
        s.ANTHROPIC_AUTH_TOKEN = ""
        s.LLM_BACKEND = "auto"
        s.OPENAI_API_KEY = ""
        resp = await client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "mcp_servers" in data["services"]


@pytest.mark.asyncio
async def test_health_no_mcp_when_disabled(client):
    """When MCP_ENABLED=False, health response has no mcp_servers."""
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "mcp_servers" not in data["services"]
