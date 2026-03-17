# Copyright (c) 2025 Athena Red Team Platform
# Author: azz093093.830330@gmail.com
# Project: Athena
# License: MIT
#
# This file is part of the Athena Red Team Platform.
# Unauthorized copying or distribution is prohibited.

"""Integration tests for the Operations router."""

import pytest
from httpx import AsyncClient


async def test_list_operations(client: AsyncClient):
    """GET /api/operations returns a list that includes the seeded test-op-1."""
    resp = await client.get("/api/operations")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    ids = [op["id"] for op in data]
    assert "test-op-1" in ids


async def test_create_operation(client: AsyncClient):
    """POST /api/operations creates a new operation with status=planning."""
    resp = await client.post(
        "/api/operations",
        json={
            "code": "OP-NEW-001",
            "name": "New Operation",
            "codename": "SHADOW",
            "strategic_intent": "Test new operation creation",
            "mission_profile": "SP",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "planning"
    assert data["code"] == "OP-NEW-001"
    assert data["name"] == "New Operation"
    assert data["id"]


async def test_create_operation_with_mission_profile(client: AsyncClient):
    """POST /api/operations with mission_profile='CO' sets CO profile."""
    resp = await client.post(
        "/api/operations",
        json={
            "code": "OP-CO-001",
            "name": "Covert Operation",
            "codename": "GHOST",
            "strategic_intent": "Test covert mission profile",
            "mission_profile": "CO",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["mission_profile"] == "CO"


async def test_get_operation_by_id(client: AsyncClient):
    """GET /api/operations/test-op-1 returns the seeded operation."""
    resp = await client.get("/api/operations/test-op-1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == "test-op-1"
    assert data["status"] == "active"


async def test_get_operation_not_found(client: AsyncClient):
    """GET /api/operations/nonexistent returns 404."""
    resp = await client.get("/api/operations/nonexistent-op-id")
    assert resp.status_code == 404


async def test_update_operation_status(client: AsyncClient):
    """PATCH /api/operations/test-op-1 with status update returns 200 with updated status."""
    resp = await client.patch(
        "/api/operations/test-op-1",
        json={"status": "active"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == "test-op-1"
    assert data["status"] == "active"


async def test_update_operation_no_changes(client: AsyncClient):
    """PATCH /api/operations/test-op-1 with empty body returns current operation state."""
    resp = await client.patch(
        "/api/operations/test-op-1",
        json={},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == "test-op-1"


async def test_get_operation_summary(client: AsyncClient):
    """GET /api/operations/test-op-1/summary returns 200 with operation summary."""
    resp = await client.get("/api/operations/test-op-1/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert "operation" in data
    assert data["operation"]["id"] == "test-op-1"
    assert "c5isr" in data
    assert "latest_recommendation" in data


async def test_get_operation_summary_not_found(client: AsyncClient):
    """GET /api/operations/nonexistent/summary returns 404."""
    resp = await client.get("/api/operations/nonexistent-op-id/summary")
    assert resp.status_code == 404


async def test_list_mission_profiles(client: AsyncClient):
    """GET /api/mission-profiles returns a dict of mission profile definitions."""
    resp = await client.get("/api/mission-profiles")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, dict)
    # Should include at least SR, CO, SP, FA
    assert len(data) >= 4


async def test_get_mission_profile_by_code(client: AsyncClient):
    """GET /api/mission-profiles/SP returns SP profile data."""
    resp = await client.get("/api/mission-profiles/SP")
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == "SP"
