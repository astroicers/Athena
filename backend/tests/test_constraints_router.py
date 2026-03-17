# Copyright (c) 2025 Athena Red Team Platform
# Author: azz093093.830330@gmail.com
# Project: Athena
# License: MIT
#
# This file is part of the Athena Red Team Platform.
# Unauthorized copying or distribution is prohibited.

"""Integration tests for the constraints router (/api/operations/{op_id}/constraints)."""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


async def test_get_constraints(client: AsyncClient):
    """GET /api/operations/test-op-1/constraints returns 200 with constraint fields.

    Note: constraint_engine.evaluate() is NOT mocked here because it has no external
    dependencies — it reads from the DB (which is provided by the test fixture) and
    returns an OperationalConstraints object with default safe values when no
    violations exist. MOCK_LLM/MOCK_C2_ENGINE=true (set in conftest) ensures no
    external calls are made.
    """
    resp = await client.get("/api/operations/test-op-1/constraints")
    assert resp.status_code == 200
    data = resp.json()
    # OperationalConstraints model_dump() always includes these keys
    assert "warnings" in data
    assert "hard_limits" in data
    assert "orient_max_options" in data
    assert "noise_budget_remaining" in data
    assert isinstance(data["warnings"], list)
    assert isinstance(data["hard_limits"], list)


async def test_get_constraints_unknown_op(client: AsyncClient):
    """GET /api/operations/nonexistent/constraints returns 404."""
    resp = await client.get("/api/operations/nonexistent-op-xyz/constraints")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


async def test_override_constraint(client: AsyncClient):
    """POST /api/operations/test-op-1/constraints/override with valid domain returns 200."""
    resp = await client.post(
        "/api/operations/test-op-1/constraints/override",
        json={"domain": "command"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "overridden"
    assert data["domain"] == "command"
    assert "event_id" in data
    assert data["event_id"]  # non-empty UUID string


async def test_override_constraint_invalid_domain(client: AsyncClient):
    """POST /api/operations/test-op-1/constraints/override with invalid domain returns 400."""
    resp = await client.post(
        "/api/operations/test-op-1/constraints/override",
        json={"domain": "invalid_domain_xyz"},
    )
    assert resp.status_code == 400
    assert "invalid domain" in resp.json()["detail"].lower()


async def test_override_constraint_unknown_op(client: AsyncClient):
    """POST /api/operations/nonexistent/constraints/override returns 404."""
    resp = await client.post(
        "/api/operations/nonexistent-op-xyz/constraints/override",
        json={"domain": "cyber"},
    )
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()
