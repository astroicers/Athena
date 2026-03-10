# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.

"""Tests for Mission Objectives CRUD endpoints — SPEC-049."""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_list_objectives_empty(client):
    """GET /operations/{id}/objectives returns empty list initially."""
    resp = await client.get("/api/operations/test-op-1/objectives")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_create_objective(client):
    """POST /operations/{id}/objectives creates a new objective."""
    resp = await client.post(
        "/api/operations/test-op-1/objectives",
        json={"objective": "Compromise Domain Controller", "category": "strategic", "priority": 1},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "id" in data
    assert data["status"] == "pending"


@pytest.mark.asyncio
async def test_create_and_list(client):
    """Created objectives appear in list."""
    await client.post(
        "/api/operations/test-op-1/objectives",
        json={"objective": "Exfiltrate sensitive data", "category": "tactical"},
    )
    resp = await client.get("/api/operations/test-op-1/objectives")
    data = resp.json()
    assert len(data) == 1
    assert data[0]["objective"] == "Exfiltrate sensitive data"


@pytest.mark.asyncio
async def test_update_objective_status(client):
    """PATCH /operations/{id}/objectives/{oid} updates status."""
    create_resp = await client.post(
        "/api/operations/test-op-1/objectives",
        json={"objective": "Get initial foothold"},
    )
    obj_id = create_resp.json()["id"]

    patch_resp = await client.patch(
        f"/api/operations/test-op-1/objectives/{obj_id}",
        json={"status": "achieved"},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["updated"] is True

    # Verify achieved_at is set
    list_resp = await client.get("/api/operations/test-op-1/objectives")
    obj = [o for o in list_resp.json() if o["id"] == obj_id][0]
    assert obj["status"] == "achieved"
    assert obj["achieved_at"] is not None


@pytest.mark.asyncio
async def test_update_objective_evidence(client):
    """PATCH can update evidence field."""
    create_resp = await client.post(
        "/api/operations/test-op-1/objectives",
        json={"objective": "Map internal network"},
    )
    obj_id = create_resp.json()["id"]

    patch_resp = await client.patch(
        f"/api/operations/test-op-1/objectives/{obj_id}",
        json={"evidence": {"subnets": ["10.0.1.0/24", "10.0.2.0/24"]}},
    )
    assert patch_resp.status_code == 200


@pytest.mark.asyncio
async def test_update_objective_not_found(client):
    """PATCH with bad objective ID returns 404."""
    resp = await client.patch(
        "/api/operations/test-op-1/objectives/nonexistent",
        json={"status": "achieved"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_objective_no_fields(client):
    """PATCH with empty body returns 400."""
    create_resp = await client.post(
        "/api/operations/test-op-1/objectives",
        json={"objective": "Test obj"},
    )
    obj_id = create_resp.json()["id"]
    resp = await client.patch(
        f"/api/operations/test-op-1/objectives/{obj_id}",
        json={},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_objectives_404_op(client):
    """Objectives endpoints return 404 for bad operation."""
    resp = await client.get("/api/operations/nonexistent/objectives")
    assert resp.status_code == 404
