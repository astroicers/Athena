# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: azz093093.830330@gmail.com

"""Integration tests for the Objectives router."""

from httpx import AsyncClient


# ---------------------------------------------------------------------------
# POST /api/operations/{op_id}/objectives — Create
# ---------------------------------------------------------------------------

async def test_create_objective(client: AsyncClient):
    """POST /api/operations/{op_id}/objectives returns 201 with id and status."""
    resp = await client.post(
        "/api/operations/test-op-1/objectives",
        json={
            "objective": "Compromise Domain Controller",
            "category": "strategic",
            "priority": 1,
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "id" in data
    assert data["status"] == "pending"


async def test_create_objective_defaults(client: AsyncClient):
    """POST with minimal body uses default category and priority."""
    resp = await client.post(
        "/api/operations/test-op-1/objectives",
        json={"objective": "Minimal objective"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "id" in data
    assert data["status"] == "pending"


async def test_create_objective_bad_operation(client: AsyncClient):
    """POST with nonexistent operation returns 404."""
    resp = await client.post(
        "/api/operations/nonexistent-op-id/objectives",
        json={"objective": "Should fail"},
    )
    assert resp.status_code == 404


async def test_create_objective_invalid_data(client: AsyncClient):
    """POST with missing required field returns 422."""
    resp = await client.post(
        "/api/operations/test-op-1/objectives",
        json={},
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET /api/operations/{op_id}/objectives — List
# ---------------------------------------------------------------------------

async def test_list_objectives_empty(client: AsyncClient):
    """GET /api/operations/{op_id}/objectives returns empty list initially."""
    resp = await client.get("/api/operations/test-op-1/objectives")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert data == []


async def test_list_objectives_after_create(client: AsyncClient):
    """GET returns created objectives."""
    await client.post(
        "/api/operations/test-op-1/objectives",
        json={"objective": "Exfiltrate sensitive data", "category": "tactical"},
    )
    resp = await client.get("/api/operations/test-op-1/objectives")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["objective"] == "Exfiltrate sensitive data"
    assert "id" in data[0]
    assert "category" in data[0]
    assert "priority" in data[0]
    assert "status" in data[0]
    assert "created_at" in data[0]


async def test_list_objectives_bad_operation(client: AsyncClient):
    """GET with nonexistent operation returns 404."""
    resp = await client.get("/api/operations/nonexistent-op-id/objectives")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# PATCH /api/operations/{op_id}/objectives/{id} — Update
# ---------------------------------------------------------------------------

async def test_update_objective_status(client: AsyncClient):
    """PATCH updates objective status to achieved and sets achieved_at."""
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

    # Verify achieved_at is set via list
    list_resp = await client.get("/api/operations/test-op-1/objectives")
    obj = [o for o in list_resp.json() if o["id"] == obj_id][0]
    assert obj["status"] == "achieved"
    assert obj["achieved_at"] is not None


async def test_update_objective_evidence(client: AsyncClient):
    """PATCH can update the evidence field with a JSON object."""
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
    assert patch_resp.json()["updated"] is True


async def test_update_objective_not_found(client: AsyncClient):
    """PATCH with nonexistent objective returns 404."""
    resp = await client.patch(
        "/api/operations/test-op-1/objectives/nonexistent-obj-id",
        json={"status": "achieved"},
    )
    assert resp.status_code == 404


async def test_update_objective_no_fields(client: AsyncClient):
    """PATCH with empty body returns 400 (no fields to update)."""
    create_resp = await client.post(
        "/api/operations/test-op-1/objectives",
        json={"objective": "Test objective"},
    )
    obj_id = create_resp.json()["id"]

    resp = await client.patch(
        f"/api/operations/test-op-1/objectives/{obj_id}",
        json={},
    )
    assert resp.status_code == 400


async def test_update_objective_bad_operation(client: AsyncClient):
    """PATCH with nonexistent operation returns 404."""
    resp = await client.patch(
        "/api/operations/nonexistent-op-id/objectives/some-id",
        json={"status": "in_progress"},
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Full CRUD flow
# ---------------------------------------------------------------------------

async def test_create_list_update_flow(client: AsyncClient):
    """Full flow: create -> list -> update status -> verify."""
    # Create two objectives
    resp1 = await client.post(
        "/api/operations/test-op-1/objectives",
        json={"objective": "First objective", "priority": 2},
    )
    resp2 = await client.post(
        "/api/operations/test-op-1/objectives",
        json={"objective": "Second objective", "priority": 1},
    )
    assert resp1.status_code == 201
    assert resp2.status_code == 201

    # List should return both, ordered by priority then created_at
    list_resp = await client.get("/api/operations/test-op-1/objectives")
    data = list_resp.json()
    assert len(data) == 2
    # Priority 1 should come first
    assert data[0]["priority"] <= data[1]["priority"]

    # Update first to in_progress
    obj_id = resp1.json()["id"]
    await client.patch(
        f"/api/operations/test-op-1/objectives/{obj_id}",
        json={"status": "in_progress"},
    )

    # Verify via list
    list_resp = await client.get("/api/operations/test-op-1/objectives")
    updated = [o for o in list_resp.json() if o["id"] == obj_id][0]
    assert updated["status"] == "in_progress"
