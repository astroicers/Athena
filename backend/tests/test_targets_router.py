# Copyright (c) 2025 Athena Red Team Platform
# Author: azz093093.830330@gmail.com
# Project: Athena
# License: MIT
#
# This file is part of the Athena Red Team Platform.
# Unauthorized copying or distribution is prohibited.

"""Integration tests for the Targets router."""

import asyncpg
import pytest
from httpx import AsyncClient


async def test_list_targets(client: AsyncClient):
    """GET /api/operations/test-op-1/targets -> 200, includes test-target-1."""
    resp = await client.get("/api/operations/test-op-1/targets")
    assert resp.status_code == 200
    targets = resp.json()
    assert isinstance(targets, list)
    ids = [t["id"] for t in targets]
    assert "test-target-1" in ids


async def test_list_targets_unknown_op(client: AsyncClient):
    """GET /api/operations/nonexistent/targets -> 404."""
    resp = await client.get("/api/operations/nonexistent-op/targets")
    assert resp.status_code == 404


async def test_create_target(client: AsyncClient):
    """POST /api/operations/test-op-1/targets -> 201."""
    resp = await client.post(
        "/api/operations/test-op-1/targets",
        json={
            "hostname": "web-01",
            "ip_address": "10.0.2.1",
            "os": "Ubuntu 22.04",
            "role": "Web Server",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["hostname"] == "web-01"
    assert body["ip_address"] == "10.0.2.1"
    assert body["id"]


async def test_create_target_duplicate_ip_returns_409(client: AsyncClient, seeded_db: asyncpg.Connection):
    """POST with existing IP 10.0.1.5 -> 409 Conflict."""
    resp = await client.post(
        "/api/operations/test-op-1/targets",
        json={
            "hostname": "dc-duplicate",
            "ip_address": "10.0.1.5",  # already seeded
            "os": "Windows Server 2022",
        },
    )
    assert resp.status_code == 409
    assert "already exists" in resp.json()["detail"]


async def test_set_active_target(client: AsyncClient, seeded_db: asyncpg.Connection):
    """PATCH /api/operations/test-op-1/targets/active -> 200, target marked active."""
    resp = await client.patch(
        "/api/operations/test-op-1/targets/active",
        json={"target_id": "test-target-1"},
    )
    assert resp.status_code == 200
    targets = resp.json()
    active = [t for t in targets if t["id"] == "test-target-1"]
    assert len(active) == 1
    assert active[0]["is_active"] is True


async def test_set_active_target_not_found(client: AsyncClient):
    """PATCH with unknown target_id -> 404."""
    resp = await client.patch(
        "/api/operations/test-op-1/targets/active",
        json={"target_id": "nonexistent-target-xyz"},
    )
    assert resp.status_code == 404


async def test_batch_create_targets(client: AsyncClient):
    """POST /api/operations/test-op-1/targets/batch -> 201 with created list."""
    resp = await client.post(
        "/api/operations/test-op-1/targets/batch",
        json={
            "entries": [
                {"hostname": "srv-01", "ip_address": "10.0.3.1"},
                {"hostname": "srv-02", "ip_address": "10.0.3.2"},
            ],
            "role": "Server",
            "os": "Linux",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["total_requested"] == 2
    assert body["total_created"] == 2
    assert len(body["created"]) == 2
    assert body["skipped_duplicates"] == []


async def test_batch_create_skips_duplicates(client: AsyncClient, seeded_db: asyncpg.Connection):
    """Batch create with an existing IP -> that entry is skipped."""
    resp = await client.post(
        "/api/operations/test-op-1/targets/batch",
        json={
            "entries": [
                {"hostname": "dc-01-dup", "ip_address": "10.0.1.5"},  # duplicate
                {"hostname": "new-host", "ip_address": "10.0.4.1"},
            ],
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["total_requested"] == 2
    assert body["total_created"] == 1
    assert "10.0.1.5" in body["skipped_duplicates"]


async def test_delete_target(client: AsyncClient, seeded_db: asyncpg.Connection):
    """DELETE /api/operations/test-op-1/targets/test-target-1 -> 204 (not active)."""
    # Ensure target is NOT active before deleting
    await seeded_db.execute(
        "UPDATE targets SET is_active = FALSE WHERE id = 'test-target-1'"
    )
    resp = await client.delete("/api/operations/test-op-1/targets/test-target-1")
    assert resp.status_code == 204


async def test_delete_target_not_found(client: AsyncClient):
    """DELETE unknown target -> 404."""
    resp = await client.delete("/api/operations/test-op-1/targets/nonexistent-target-xyz")
    assert resp.status_code == 404


async def test_delete_active_target_blocked(client: AsyncClient, seeded_db: asyncpg.Connection):
    """Set target active then DELETE -> 409 (cannot delete active target)."""
    # First set the target as active
    await seeded_db.execute(
        "UPDATE targets SET is_active = TRUE WHERE id = 'test-target-1'"
    )
    resp = await client.delete("/api/operations/test-op-1/targets/test-target-1")
    assert resp.status_code == 409
    assert "active" in resp.json()["detail"].lower()


async def test_get_topology(client: AsyncClient):
    """GET /api/operations/test-op-1/topology -> 200 with nodes and edges."""
    resp = await client.get("/api/operations/test-op-1/topology")
    assert resp.status_code == 200
    body = resp.json()
    assert "nodes" in body
    assert "edges" in body
    assert isinstance(body["nodes"], list)
    assert isinstance(body["edges"], list)
    # Must have at least the Athena C2 node
    node_ids = [n["id"] for n in body["nodes"]]
    assert "athena-c2" in node_ids


async def test_get_target_summary(client: AsyncClient, seeded_db: asyncpg.Connection):
    """GET /api/operations/test-op-1/targets/test-target-1/summary -> 200."""
    resp = await client.get(
        "/api/operations/test-op-1/targets/test-target-1/summary"
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "summary" in body
    assert "fact_count" in body
    assert "cached" in body
    assert "generated_at" in body
    assert "model" in body
