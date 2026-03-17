# Copyright (c) 2025 Athena Red Team Platform
# Author: azz093093.830330@gmail.com
# Project: Athena
# License: MIT
#
# This file is part of the Athena Red Team Platform.
# Unauthorized copying or distribution is prohibited.

"""Integration tests for the Mission Steps router."""

from httpx import AsyncClient

_BASE = "/api/operations/test-op-1/mission/steps"
_STEP_PAYLOAD = {
    "step_number": 1,
    "technique_id": "T1003.001",
    "technique_name": "LSASS Memory",
    "target_id": "test-target-1",
    "target_label": "DC-01",
    "engine": "ssh",
}


async def test_list_mission_steps_empty(client: AsyncClient):
    """GET mission/steps on a fresh operation returns an empty list."""
    resp = await client.get(_BASE)
    assert resp.status_code == 200
    assert resp.json() == []


async def test_create_mission_step(client: AsyncClient, seeded_db):
    """POST mission/steps creates a step and returns the correct fields."""
    resp = await client.post(_BASE, json=_STEP_PAYLOAD)
    assert resp.status_code == 201

    body = resp.json()
    assert body["operation_id"] == "test-op-1"
    assert body["step_number"] == 1
    assert body["technique_id"] == "T1003.001"
    assert body["technique_name"] == "LSASS Memory"
    assert body["target_id"] == "test-target-1"
    assert body["target_label"] == "DC-01"
    assert body["engine"] == "ssh"
    assert body["status"] == "queued"
    assert body["id"]


async def test_create_two_steps_order_preserved(client: AsyncClient, seeded_db):
    """POST two steps then GET returns them ordered by step_number."""
    payload1 = dict(_STEP_PAYLOAD, step_number=1, technique_name="Step One")
    payload2 = dict(_STEP_PAYLOAD, step_number=2, technique_name="Step Two")

    await client.post(_BASE, json=payload1)
    await client.post(_BASE, json=payload2)

    resp = await client.get(_BASE)
    assert resp.status_code == 200

    items = resp.json()
    assert len(items) == 2
    assert items[0]["step_number"] == 1
    assert items[0]["technique_name"] == "Step One"
    assert items[1]["step_number"] == 2
    assert items[1]["technique_name"] == "Step Two"


async def test_update_mission_step_status_running(client: AsyncClient, seeded_db):
    """PATCH status=running sets started_at on the step row in the DB."""
    create_resp = await client.post(_BASE, json=_STEP_PAYLOAD)
    assert create_resp.status_code == 201
    step_id = create_resp.json()["id"]

    patch_resp = await client.patch(
        f"{_BASE}/{step_id}",
        json={"status": "running"},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["status"] == "running"

    # Verify started_at was written to the database
    row = await seeded_db.fetchrow(
        "SELECT started_at FROM mission_steps WHERE id = $1", step_id
    )
    assert row["started_at"] is not None


async def test_update_mission_step_completed(client: AsyncClient, seeded_db):
    """PATCH status=completed sets completed_at on the step row in the DB."""
    create_resp = await client.post(_BASE, json=_STEP_PAYLOAD)
    assert create_resp.status_code == 201
    step_id = create_resp.json()["id"]

    patch_resp = await client.patch(
        f"{_BASE}/{step_id}",
        json={"status": "completed"},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["status"] == "completed"

    row = await seeded_db.fetchrow(
        "SELECT completed_at FROM mission_steps WHERE id = $1", step_id
    )
    assert row["completed_at"] is not None


async def test_update_mission_step_not_found(client: AsyncClient):
    """PATCH a non-existent step_id returns 404."""
    resp = await client.patch(
        f"{_BASE}/nonexistent-step-id",
        json={"status": "running"},
    )
    assert resp.status_code == 404


async def test_create_mission_step_unknown_op_returns_404(client: AsyncClient):
    """POST to an unknown operation_id returns 404."""
    resp = await client.post(
        "/api/operations/unknown-op-xyz/mission/steps",
        json=_STEP_PAYLOAD,
    )
    assert resp.status_code == 404
