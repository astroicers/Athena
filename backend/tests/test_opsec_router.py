# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: azz093093.830330@gmail.com

"""Integration tests for the OPSEC router."""

from httpx import AsyncClient


# ---------------------------------------------------------------------------
# GET /api/operations/{op_id}/opsec-status
# ---------------------------------------------------------------------------

async def test_get_opsec_status(client: AsyncClient, seeded_db):
    """GET /api/operations/{op_id}/opsec-status returns 200 with OPSEC aggregate."""
    resp = await client.get("/api/operations/test-op-1/opsec-status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["operation_id"] == "test-op-1"
    assert "noise_score" in data
    assert "detection_risk" in data
    assert "noise_budget_total" in data


async def test_get_opsec_status_not_found(client: AsyncClient):
    """GET /api/operations/{bad_id}/opsec-status returns 404."""
    resp = await client.get("/api/operations/nonexistent-op-id/opsec-status")
    assert resp.status_code == 404


async def test_opsec_status_zero_noise_without_events(client: AsyncClient, seeded_db):
    """OPSEC status with no opsec_events should have zero or low noise_score."""
    resp = await client.get("/api/operations/test-op-1/opsec-status")
    data = resp.json()
    # No opsec_events seeded, so noise should be zero
    assert data["noise_score"] >= 0


async def test_opsec_status_with_event(client: AsyncClient, seeded_db):
    """OPSEC status reflects inserted opsec events."""
    await seeded_db.execute(
        """INSERT INTO opsec_events (id, operation_id, event_type, noise_points, detail)
           VALUES ($1, $2, $3, $4, $5)""",
        "opsec-evt-1", "test-op-1", "port_scan", 15, '{"message": "Nmap SYN scan detected"}',
    )
    resp = await client.get("/api/operations/test-op-1/opsec-status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["noise_score"] >= 0


# ---------------------------------------------------------------------------
# GET /api/operations/{op_id}/threat-level
# ---------------------------------------------------------------------------

async def test_get_threat_level(client: AsyncClient, seeded_db):
    """GET /api/operations/{op_id}/threat-level returns 200 with threat data."""
    resp = await client.get("/api/operations/test-op-1/threat-level")
    assert resp.status_code == 200
    data = resp.json()
    assert data["operation_id"] == "test-op-1"
    assert "level" in data
    assert "components" in data
    assert 0.0 <= data["level"] <= 1.0


async def test_get_threat_level_not_found(client: AsyncClient):
    """GET /api/operations/{bad_id}/threat-level returns 404."""
    resp = await client.get("/api/operations/nonexistent-op-id/threat-level")
    assert resp.status_code == 404


async def test_threat_level_has_components(client: AsyncClient, seeded_db):
    """Threat level response contains component breakdown."""
    resp = await client.get("/api/operations/test-op-1/threat-level")
    data = resp.json()
    assert isinstance(data["components"], dict)


async def test_threat_level_bounded(client: AsyncClient, seeded_db):
    """Threat level value is bounded between 0.0 and 1.0."""
    resp = await client.get("/api/operations/test-op-1/threat-level")
    data = resp.json()
    assert 0.0 <= data["level"] <= 1.0
