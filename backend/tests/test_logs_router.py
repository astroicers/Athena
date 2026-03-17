# Copyright (c) 2025 Athena Red Team Platform
# Author: azz093093.830330@gmail.com
# Project: Athena
# License: MIT
#
# This file is part of the Athena Red Team Platform.
# Unauthorized copying or distribution is prohibited.

"""Integration tests for the logs router (/api/operations/{op_id}/logs)."""

import asyncpg
from httpx import AsyncClient


async def test_list_logs_empty(client: AsyncClient):
    """GET /api/operations/test-op-1/logs returns 200 with items=[] and total=0
    when no log entries have been inserted."""
    resp = await client.get("/api/operations/test-op-1/logs")
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0


async def test_list_logs_with_entries(
    client: AsyncClient, seeded_db: asyncpg.Connection
):
    """GET /api/operations/test-op-1/logs returns inserted log entries."""
    await seeded_db.execute(
        "INSERT INTO log_entries (id, operation_id, severity, source, message) "
        "VALUES ('log-1', 'test-op-1', 'info', 'nmap', 'Scan completed')"
    )
    await seeded_db.execute(
        "INSERT INTO log_entries (id, operation_id, severity, source, message) "
        "VALUES ('log-2', 'test-op-1', 'warning', 'engine', 'Retry attempted')"
    )

    resp = await client.get("/api/operations/test-op-1/logs")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    ids = {entry["id"] for entry in data["items"]}
    assert {"log-1", "log-2"} == ids


async def test_list_logs_pagination(
    client: AsyncClient, seeded_db: asyncpg.Connection
):
    """GET /api/operations/test-op-1/logs?page=1&page_size=2 returns 2 items
    and reports total=5."""
    for i in range(1, 6):
        await seeded_db.execute(
            "INSERT INTO log_entries (id, operation_id, severity, source, message) "
            f"VALUES ('log-page-{i}', 'test-op-1', 'info', 'test', 'Message {i}')"
        )

    resp = await client.get("/api/operations/test-op-1/logs?page=1&page_size=2")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 5
    assert len(data["items"]) == 2
    assert data["page"] == 1
    assert data["page_size"] == 2


async def test_list_logs_page_2(
    client: AsyncClient, seeded_db: asyncpg.Connection
):
    """GET /api/operations/test-op-1/logs?page=2&page_size=2 returns the next
    2 items (different from page 1)."""
    for i in range(1, 6):
        await seeded_db.execute(
            "INSERT INTO log_entries (id, operation_id, severity, source, message) "
            f"VALUES ('log-p2-{i}', 'test-op-1', 'info', 'test', 'Message {i}')"
        )

    resp_p1 = await client.get("/api/operations/test-op-1/logs?page=1&page_size=2")
    resp_p2 = await client.get("/api/operations/test-op-1/logs?page=2&page_size=2")

    assert resp_p1.status_code == 200
    assert resp_p2.status_code == 200

    p1_ids = {entry["id"] for entry in resp_p1.json()["items"]}
    p2_ids = {entry["id"] for entry in resp_p2.json()["items"]}

    # Pages must not overlap
    assert p1_ids.isdisjoint(p2_ids)
    # Both pages return exactly 2 items
    assert len(p1_ids) == 2
    assert len(p2_ids) == 2
    # Total is consistent
    assert resp_p2.json()["total"] == 5
    assert resp_p2.json()["page"] == 2


async def test_list_logs_unknown_op_returns_404(client: AsyncClient):
    """GET /api/operations/nonexistent/logs returns 404 when the operation
    does not exist."""
    resp = await client.get("/api/operations/nonexistent/logs")
    assert resp.status_code == 404
