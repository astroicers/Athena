# Copyright (c) 2025 Athena Red Team Platform
# Author: azz093093.830330@gmail.com
# Project: Athena
# License: MIT
#
# This file is part of the Athena Red Team Platform.
# Unauthorized copying or distribution is prohibited.

"""Integration tests for the health router (/api/health, /api/mcp/status)."""

from httpx import AsyncClient


async def test_health_check_returns_ok(client: AsyncClient):
    """GET /api/health returns 200 with status='ok'."""
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["version"]


async def test_health_check_has_service_statuses(client: AsyncClient):
    """GET /api/health response contains database key with 'connected' status."""
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    services = data["services"]
    assert "database" in services
    # The test DB is live so it should be reachable
    assert services["database"] == "connected"


async def test_mcp_status_disabled(client: AsyncClient):
    """GET /api/mcp/status returns 200 even when MCP_ENABLED is false."""
    resp = await client.get("/api/mcp/status")
    assert resp.status_code == 200
    data = resp.json()
    # MCP_ENABLED defaults to false in test env → enabled key must be present
    assert "enabled" in data


async def test_mcp_status_structure(client: AsyncClient):
    """GET /api/mcp/status response has required top-level keys."""
    resp = await client.get("/api/mcp/status")
    assert resp.status_code == 200
    data = resp.json()
    # Whether enabled or not the shape is always {enabled, servers, tool_count}
    assert "enabled" in data
    assert "servers" in data
    assert "tool_count" in data
    assert isinstance(data["servers"], list)
    assert isinstance(data["tool_count"], int)
