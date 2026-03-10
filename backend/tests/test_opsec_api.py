# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.

"""API tests for OPSEC endpoints — SPEC-048."""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_get_opsec_status(client):
    """GET /operations/{id}/opsec-status returns OPSEC aggregate."""
    resp = await client.get("/api/operations/test-op-1/opsec-status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["operation_id"] == "test-op-1"
    assert "noise_score" in data
    assert "detection_risk" in data
    assert "noise_budget_total" in data


@pytest.mark.asyncio
async def test_get_opsec_status_404(client):
    """GET /operations/{id}/opsec-status with bad op returns 404."""
    resp = await client.get("/api/operations/nonexistent/opsec-status")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_threat_level(client):
    """GET /operations/{id}/threat-level returns threat level."""
    resp = await client.get("/api/operations/test-op-1/threat-level")
    assert resp.status_code == 200
    data = resp.json()
    assert data["operation_id"] == "test-op-1"
    assert "level" in data
    assert "components" in data
    assert 0.0 <= data["level"] <= 1.0


@pytest.mark.asyncio
async def test_get_threat_level_404(client):
    """GET /operations/{id}/threat-level with bad op returns 404."""
    resp = await client.get("/api/operations/nonexistent/threat-level")
    assert resp.status_code == 404
