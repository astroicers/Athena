# Copyright (c) 2025 Athena Red Team Platform
# Author: azz093093.830330@gmail.com
# Project: Athena
# License: MIT
#
# This file is part of the Athena Red Team Platform.
# Unauthorized copying or distribution is prohibited.

"""Integration tests for the facts router (/api/operations/{op_id}/facts)."""

import asyncpg
from httpx import AsyncClient


async def test_list_facts_empty(client: AsyncClient):
    """GET /api/operations/test-op-1/facts returns 200 with an empty list
    when no facts have been inserted."""
    resp = await client.get("/api/operations/test-op-1/facts")
    assert resp.status_code == 200
    assert resp.json() == []


async def test_list_facts_with_data(client: AsyncClient, seeded_db: asyncpg.Connection):
    """GET /api/operations/test-op-1/facts returns the inserted fact."""
    await seeded_db.execute(
        "INSERT INTO facts "
        "(id, operation_id, source_target_id, trait, value, category, score) "
        "VALUES ('fact-1', 'test-op-1', 'test-target-1', 'network.open_port', '80', 'network', 90)"
    )

    resp = await client.get("/api/operations/test-op-1/facts")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["id"] == "fact-1"
    assert data[0]["trait"] == "network.open_port"
    assert data[0]["value"] == "80"


async def test_list_facts_filter_by_target_id(
    client: AsyncClient, seeded_db: asyncpg.Connection
):
    """GET /api/operations/test-op-1/facts?target_id=test-target-1 returns only
    facts whose source_target_id matches the query parameter."""
    # Insert a second target so we can test the filter
    await seeded_db.execute(
        "INSERT INTO targets (id, hostname, ip_address, os, role, operation_id) "
        "VALUES ('test-target-2', 'WEB-01', '10.0.1.6', 'Linux', 'Web Server', 'test-op-1')"
    )

    # Fact for target-1
    await seeded_db.execute(
        "INSERT INTO facts "
        "(id, operation_id, source_target_id, trait, value, category, score) "
        "VALUES ('fact-t1', 'test-op-1', 'test-target-1', 'host.user', 'admin', 'host', 80)"
    )
    # Fact for target-2
    await seeded_db.execute(
        "INSERT INTO facts "
        "(id, operation_id, source_target_id, trait, value, category, score) "
        "VALUES ('fact-t2', 'test-op-1', 'test-target-2', 'host.user', 'www-data', 'host', 70)"
    )

    resp = await client.get(
        "/api/operations/test-op-1/facts?target_id=test-target-1"
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["id"] == "fact-t1"
    assert data[0]["source_target_id"] == "test-target-1"


async def test_list_facts_unknown_op_returns_404(client: AsyncClient):
    """GET /api/operations/nonexistent/facts returns 404 when the operation
    does not exist."""
    resp = await client.get("/api/operations/nonexistent/facts")
    assert resp.status_code == 404
