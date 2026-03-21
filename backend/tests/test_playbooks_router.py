# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: azz093093.830330@gmail.com

"""Integration tests for the Playbooks router."""

from httpx import AsyncClient


# ---------------------------------------------------------------------------
# GET /api/playbooks — List
# ---------------------------------------------------------------------------

async def test_list_playbooks(client: AsyncClient):
    """GET /api/playbooks returns 200 with a list of playbooks."""
    resp = await client.get("/api/playbooks")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    # Seed data should populate at least 100 playbooks
    assert len(data) >= 100


async def test_list_playbooks_filter_by_mitre_id(client: AsyncClient):
    """GET /api/playbooks?mitre_id=... filters by MITRE technique ID."""
    # Create a playbook with a unique mitre_id
    await client.post(
        "/api/playbooks",
        json={
            "mitre_id": "T9990",
            "platform": "linux",
            "command": "test-filter",
            "facts_traits": [],
        },
    )
    resp = await client.get("/api/playbooks?mitre_id=T9990")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    assert all(p["mitre_id"] == "T9990" for p in data)


async def test_list_playbooks_filter_by_platform(client: AsyncClient):
    """GET /api/playbooks?platform=... filters by platform."""
    await client.post(
        "/api/playbooks",
        json={
            "mitre_id": "T9991",
            "platform": "darwin",
            "command": "sw_vers",
            "facts_traits": [],
        },
    )
    resp = await client.get("/api/playbooks?platform=darwin")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    assert all(p["platform"] == "darwin" for p in data)


# ---------------------------------------------------------------------------
# GET /api/playbooks/{id} — Detail
# ---------------------------------------------------------------------------

async def test_get_playbook_by_id(client: AsyncClient):
    """GET /api/playbooks/{id} returns 200 with playbook details."""
    create_resp = await client.post(
        "/api/playbooks",
        json={
            "mitre_id": "T8880",
            "platform": "linux",
            "command": "id",
            "facts_traits": ["host.user"],
            "tags": ["discovery"],
        },
    )
    pb_id = create_resp.json()["id"]

    resp = await client.get(f"/api/playbooks/{pb_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == pb_id
    assert data["mitre_id"] == "T8880"
    assert data["platform"] == "linux"
    assert data["command"] == "id"
    assert data["source"] == "user"
    assert "facts_traits" in data
    assert "tags" in data
    assert "created_at" in data


async def test_get_playbook_not_found(client: AsyncClient):
    """GET /api/playbooks/{nonexistent} returns 404."""
    resp = await client.get("/api/playbooks/nonexistent-playbook-id")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /api/playbooks — Create
# ---------------------------------------------------------------------------

async def test_create_playbook(client: AsyncClient):
    """POST /api/playbooks returns 201 with the created playbook."""
    resp = await client.post(
        "/api/playbooks",
        json={
            "mitre_id": "T9992",
            "platform": "linux",
            "command": "whoami",
            "output_parser": "first_line",
            "facts_traits": ["host.user"],
            "tags": ["test"],
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["mitre_id"] == "T9992"
    assert data["platform"] == "linux"
    assert data["command"] == "whoami"
    assert data["output_parser"] == "first_line"
    assert data["source"] == "user"
    assert data["id"]


async def test_create_playbook_minimal(client: AsyncClient):
    """POST with only required fields succeeds."""
    resp = await client.post(
        "/api/playbooks",
        json={
            "mitre_id": "T9993",
            "platform": "linux",
            "command": "uname -a",
            "facts_traits": [],
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["mitre_id"] == "T9993"


async def test_create_playbook_invalid_data(client: AsyncClient):
    """POST with missing required fields returns 422."""
    resp = await client.post(
        "/api/playbooks",
        json={"mitre_id": "T0000"},
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# PATCH /api/playbooks/{id} — Update
# ---------------------------------------------------------------------------

async def test_update_playbook_command(client: AsyncClient):
    """PATCH /api/playbooks/{id} updates the command field."""
    create_resp = await client.post(
        "/api/playbooks",
        json={
            "mitre_id": "T7770",
            "platform": "linux",
            "command": "old_cmd",
            "facts_traits": [],
        },
    )
    pb_id = create_resp.json()["id"]

    resp = await client.patch(
        f"/api/playbooks/{pb_id}", json={"command": "new_cmd"}
    )
    assert resp.status_code == 200
    assert resp.json()["command"] == "new_cmd"


async def test_update_playbook_tags(client: AsyncClient):
    """PATCH can update tags."""
    create_resp = await client.post(
        "/api/playbooks",
        json={
            "mitre_id": "T7771",
            "platform": "linux",
            "command": "ls",
            "facts_traits": [],
            "tags": [],
        },
    )
    pb_id = create_resp.json()["id"]

    resp = await client.patch(
        f"/api/playbooks/{pb_id}", json={"tags": ["updated", "new-tag"]}
    )
    assert resp.status_code == 200
    assert "updated" in resp.json()["tags"]


async def test_update_playbook_not_found(client: AsyncClient):
    """PATCH nonexistent playbook returns 404."""
    resp = await client.patch(
        "/api/playbooks/nonexistent-id",
        json={"command": "test"},
    )
    assert resp.status_code == 404


async def test_update_playbook_clear_output_parser(client: AsyncClient):
    """PATCH with output_parser=null clears the field."""
    create_resp = await client.post(
        "/api/playbooks",
        json={
            "mitre_id": "T5550",
            "platform": "linux",
            "command": "cmd",
            "facts_traits": [],
            "output_parser": "json",
        },
    )
    pb_id = create_resp.json()["id"]

    resp = await client.patch(
        f"/api/playbooks/{pb_id}", json={"output_parser": None}
    )
    assert resp.status_code == 200
    assert resp.json()["output_parser"] is None


# ---------------------------------------------------------------------------
# DELETE /api/playbooks/{id}
# ---------------------------------------------------------------------------

async def test_delete_playbook(client: AsyncClient):
    """DELETE /api/playbooks/{id} removes a user-created playbook."""
    create_resp = await client.post(
        "/api/playbooks",
        json={
            "mitre_id": "T6660",
            "platform": "linux",
            "command": "rm_test",
            "facts_traits": [],
        },
    )
    pb_id = create_resp.json()["id"]

    del_resp = await client.delete(f"/api/playbooks/{pb_id}")
    assert del_resp.status_code == 204

    # Verify it's gone
    get_resp = await client.get(f"/api/playbooks/{pb_id}")
    assert get_resp.status_code == 404


async def test_delete_playbook_not_found(client: AsyncClient):
    """DELETE nonexistent playbook returns 404."""
    resp = await client.delete("/api/playbooks/nonexistent-id")
    assert resp.status_code == 404


async def test_delete_seed_playbook_forbidden(client: AsyncClient):
    """DELETE seed playbook returns 403."""
    all_pb = (await client.get("/api/playbooks")).json()
    seed = next(p for p in all_pb if p.get("source") == "seed")
    resp = await client.delete(f"/api/playbooks/{seed['id']}")
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# POST /api/playbooks/bulk — Bulk create
# ---------------------------------------------------------------------------

async def test_bulk_create_playbooks(client: AsyncClient):
    """POST /api/playbooks/bulk creates multiple playbooks."""
    resp = await client.post(
        "/api/playbooks/bulk",
        json={
            "playbooks": [
                {
                    "mitre_id": "T9800",
                    "platform": "linux",
                    "command": "bulk_cmd_1",
                    "facts_traits": [],
                },
                {
                    "mitre_id": "T9801",
                    "platform": "linux",
                    "command": "bulk_cmd_2",
                    "facts_traits": [],
                },
            ]
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["created"] == 2
    assert data["skipped"] == 0
    assert data["errors"] == []


async def test_bulk_create_skips_duplicates(client: AsyncClient):
    """POST /api/playbooks/bulk skips existing mitre_id+platform combos."""
    payload = {
        "playbooks": [
            {
                "mitre_id": "T9810",
                "platform": "linux",
                "command": "dup_cmd",
                "facts_traits": [],
            },
        ]
    }
    # First call creates
    resp1 = await client.post("/api/playbooks/bulk", json=payload)
    assert resp1.json()["created"] == 1

    # Second call skips
    resp2 = await client.post("/api/playbooks/bulk", json=payload)
    assert resp2.json()["created"] == 0
    assert resp2.json()["skipped"] == 1
