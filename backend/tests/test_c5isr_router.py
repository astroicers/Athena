# Copyright (c) 2025 Athena Red Team Platform
# Author: azz093093.830330@gmail.com
# Project: Athena
# License: MIT
#
# This file is part of the Athena Red Team Platform.
# Unauthorized copying or distribution is prohibited.

"""Integration tests for the C5ISR router."""

import pytest
from httpx import AsyncClient


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

async def test_list_c5isr(client: AsyncClient):
    """GET /api/operations/test-op-1/c5isr -> 200, returns 6 seeded domains."""
    resp = await client.get("/api/operations/test-op-1/c5isr")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 6


async def test_list_c5isr_unknown_op(client: AsyncClient):
    """GET /api/operations/nonexistent/c5isr -> 404."""
    resp = await client.get("/api/operations/nonexistent/c5isr")
    assert resp.status_code == 404


async def test_update_c5isr_health(client: AsyncClient, seeded_db):
    """PATCH /api/operations/test-op-1/c5isr/command {health_pct: 75} -> 200."""
    resp = await client.patch(
        "/api/operations/test-op-1/c5isr/command",
        json={"health_pct": 75},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["domain"] == "command"
    assert body["health_pct"] == 75.0


async def test_update_c5isr_invalid_domain(client: AsyncClient):
    """PATCH with an unrecognised domain -> 400."""
    resp = await client.patch(
        "/api/operations/test-op-1/c5isr/invalidomain",
        json={"health_pct": 50},
    )
    assert resp.status_code in (400, 404)


async def test_update_c5isr_empty_body(client: AsyncClient):
    """PATCH with empty body {} -> 200, existing row unchanged."""
    resp = await client.patch(
        "/api/operations/test-op-1/c5isr/command",
        json={},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["domain"] == "command"
    # Original seeded health_pct for 'command' is 95.0
    assert body["health_pct"] == 95.0


async def test_get_c5isr_report(client: AsyncClient):
    """GET /api/operations/test-op-1/c5isr/command/report -> 200."""
    resp = await client.get("/api/operations/test-op-1/c5isr/command/report")
    assert resp.status_code == 200
    body = resp.json()
    assert body["domain"] == "command"
    assert body["operation_id"] == "test-op-1"


async def test_get_c5isr_report_invalid_domain(client: AsyncClient):
    """GET report for an unrecognised domain -> 400 or 404."""
    resp = await client.get("/api/operations/test-op-1/c5isr/invalid/report")
    assert resp.status_code in (400, 404)
