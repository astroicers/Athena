# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: [TODO: contact email]

"""Tests for target management features — active target, batch import, delete."""


# ---------------------------------------------------------------------------
# 1. Active Target
# ---------------------------------------------------------------------------


async def test_set_active_target(client):
    """PATCH /targets/active sets is_active=1 on the specified target."""
    resp = await client.patch(
        "/api/operations/test-op-1/targets/active",
        json={"target_id": "test-target-1"},
    )
    assert resp.status_code == 200
    targets = resp.json()
    active = [t for t in targets if t["is_active"]]
    assert len(active) == 1
    assert active[0]["id"] == "test-target-1"


async def test_set_active_target_clears_previous(client):
    """Setting a new active target deactivates the previous one."""
    # First, create a second target
    await client.post("/api/operations/test-op-1/targets", json={
        "hostname": "WS-01",
        "ip_address": "10.0.1.20",
        "role": "Workstation",
    })
    # Set first as active
    await client.patch(
        "/api/operations/test-op-1/targets/active",
        json={"target_id": "test-target-1"},
    )
    # Get list to find the second target's ID
    list_resp = await client.get("/api/operations/test-op-1/targets")
    second = [t for t in list_resp.json() if t["id"] != "test-target-1"][0]
    # Set second as active
    resp = await client.patch(
        "/api/operations/test-op-1/targets/active",
        json={"target_id": second["id"]},
    )
    assert resp.status_code == 200
    targets = resp.json()
    active = [t for t in targets if t["is_active"]]
    assert len(active) == 1
    assert active[0]["id"] == second["id"]


async def test_deselect_active_target(client):
    """Empty target_id deselects all active targets."""
    await client.patch(
        "/api/operations/test-op-1/targets/active",
        json={"target_id": "test-target-1"},
    )
    resp = await client.patch(
        "/api/operations/test-op-1/targets/active",
        json={"target_id": ""},
    )
    assert resp.status_code == 200
    active = [t for t in resp.json() if t["is_active"]]
    assert len(active) == 0


async def test_set_active_target_not_found(client):
    """Setting a non-existent target as active returns 404."""
    resp = await client.patch(
        "/api/operations/test-op-1/targets/active",
        json={"target_id": "nonexistent"},
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 2. Batch Import
# ---------------------------------------------------------------------------


async def test_batch_import_plain_ips(client):
    """Batch import creates targets for each entry."""
    resp = await client.post("/api/operations/test-op-1/targets/batch", json={
        "entries": [
            {"hostname": "host-a", "ip_address": "192.168.1.1"},
            {"hostname": "host-b", "ip_address": "192.168.1.2"},
        ],
        "role": "target",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["total_created"] == 2
    assert data["total_requested"] == 2
    assert len(data["skipped_duplicates"]) == 0


async def test_batch_import_skips_duplicates(client):
    """Batch import skips IPs that already exist in the operation."""
    # 10.0.1.5 already exists (test-target-1)
    resp = await client.post("/api/operations/test-op-1/targets/batch", json={
        "entries": [
            {"hostname": "DC-01", "ip_address": "10.0.1.5"},
            {"hostname": "new-host", "ip_address": "10.0.1.100"},
        ],
        "role": "target",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["total_created"] == 1
    assert data["skipped_duplicates"] == ["10.0.1.5"]


async def test_batch_import_max_entries(client):
    """Batch import rejects more than 512 entries."""
    entries = [
        {"hostname": f"h-{i}", "ip_address": f"10.{i // 256}.{i % 256}.1"}
        for i in range(513)
    ]
    resp = await client.post("/api/operations/test-op-1/targets/batch", json={
        "entries": entries,
        "role": "target",
    })
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# 3. Delete Target
# ---------------------------------------------------------------------------


async def test_delete_active_target_blocked(client):
    """DELETE on active target returns 409."""
    await client.patch(
        "/api/operations/test-op-1/targets/active",
        json={"target_id": "test-target-1"},
    )
    resp = await client.delete(
        "/api/operations/test-op-1/targets/test-target-1",
    )
    assert resp.status_code == 409
    assert "active target" in resp.json()["detail"].lower()


async def test_delete_non_active_target(client):
    """DELETE on non-active target returns 204."""
    # Create a second target to delete (don't delete the seeded one which has FK deps)
    create_resp = await client.post("/api/operations/test-op-1/targets", json={
        "hostname": "delete-me",
        "ip_address": "10.99.99.99",
        "role": "target",
    })
    target_id = create_resp.json()["id"]
    resp = await client.delete(
        f"/api/operations/test-op-1/targets/{target_id}",
    )
    assert resp.status_code == 204
    # Verify it's gone
    list_resp = await client.get("/api/operations/test-op-1/targets")
    assert all(t["id"] != target_id for t in list_resp.json())


# ---------------------------------------------------------------------------
# 4. Topology includes is_active
# ---------------------------------------------------------------------------


async def test_topology_includes_is_active(client):
    """GET /topology includes is_active in node data."""
    resp = await client.get("/api/operations/test-op-1/topology")
    assert resp.status_code == 200
    nodes = resp.json()["nodes"]
    host_nodes = [n for n in nodes if n["type"] == "host"]
    assert len(host_nodes) >= 1
    for node in host_nodes:
        assert "is_active" in node["data"]


# ---------------------------------------------------------------------------
# 5. Target list includes is_active
# ---------------------------------------------------------------------------


async def test_list_targets_includes_is_active(client):
    """GET /targets includes is_active field."""
    resp = await client.get("/api/operations/test-op-1/targets")
    assert resp.status_code == 200
    targets = resp.json()
    for tgt in targets:
        assert "is_active" in tgt
        assert isinstance(tgt["is_active"], bool)
