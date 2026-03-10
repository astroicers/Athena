# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.

"""Tests for Dashboard aggregate API endpoints — SPEC-049."""

from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# GET /operations/{id}/dashboard
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_dashboard_aggregate(client):
    """GET /operations/{id}/dashboard returns aggregated data."""
    resp = await client.get("/api/operations/test-op-1/dashboard")
    assert resp.status_code == 200
    data = resp.json()
    assert "operation" in data
    assert data["operation"]["id"] == "test-op-1"
    assert "c5isr" in data
    assert isinstance(data["c5isr"], list)
    assert "targets" in data
    assert "recent_executions" in data
    assert "opsec" in data
    assert "objectives" in data


@pytest.mark.asyncio
async def test_dashboard_404(client):
    resp = await client.get("/api/operations/nonexistent/dashboard")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_dashboard_c5isr_populated(client):
    """Dashboard should include seeded C5ISR domains."""
    resp = await client.get("/api/operations/test-op-1/dashboard")
    data = resp.json()
    domains = {r["domain"] for r in data["c5isr"]}
    assert "command" in domains
    assert "cyber" in domains


@pytest.mark.asyncio
async def test_dashboard_targets_stats(client):
    """Dashboard target stats should show at least 1 target."""
    resp = await client.get("/api/operations/test-op-1/dashboard")
    data = resp.json()
    assert data["targets"]["total"] >= 1


# ---------------------------------------------------------------------------
# GET /operations/{id}/targets/{tid}/kill-chain
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_kill_chain(client):
    """GET kill-chain returns attack graph nodes for the target."""
    resp = await client.get("/api/operations/test-op-1/targets/test-target-1/kill-chain")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    # Seeded data has attack_graph_nodes for test-target-1
    assert len(data) >= 1
    assert "tactic_id" in data[0]


@pytest.mark.asyncio
async def test_kill_chain_404_op(client):
    resp = await client.get("/api/operations/nonexistent/targets/test-target-1/kill-chain")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /operations/{id}/attack-surface
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_attack_surface(client):
    """GET attack-surface returns per-target vuln distribution."""
    resp = await client.get("/api/operations/test-op-1/attack-surface")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    # At least 1 target
    assert len(data) >= 1
    assert "hostname" in data[0]
    assert "vuln_count" in data[0]


# ---------------------------------------------------------------------------
# GET /operations/{id}/metrics/time-series
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_time_series_c5isr(client):
    """GET time-series with metric=c5isr returns list."""
    resp = await client.get("/api/operations/test-op-1/metrics/time-series?metric=c5isr")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_time_series_opsec(client):
    resp = await client.get("/api/operations/test-op-1/metrics/time-series?metric=opsec")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_time_series_executions(client):
    resp = await client.get("/api/operations/test-op-1/metrics/time-series?metric=executions")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_time_series_unknown_metric(client):
    resp = await client.get("/api/operations/test-op-1/metrics/time-series?metric=bogus")
    assert resp.status_code == 200
    data = resp.json()
    assert "error" in data


@pytest.mark.asyncio
async def test_time_series_404(client):
    resp = await client.get("/api/operations/nonexistent/metrics/time-series?metric=c5isr")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /operations/{id}/credential-graph
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_credential_graph_empty(client):
    """GET credential-graph with no credentials returns empty graph."""
    resp = await client.get("/api/operations/test-op-1/credential-graph")
    assert resp.status_code == 200
    data = resp.json()
    assert data["operation_id"] == "test-op-1"
    assert "nodes" in data
    assert "edges" in data


@pytest.mark.asyncio
async def test_credential_graph_with_data(client, seeded_db):
    """GET credential-graph with seeded credentials returns nodes and edges."""
    import json
    await seeded_db.execute(
        """INSERT INTO credentials (id, operation_id, username, secret_type, secret_value,
               domain, source_target_id, tested_targets)
           VALUES ($1, $2, $3, $4, $5, $6, $7, $8)""",
        "cred-1", "test-op-1", "admin", "ntlm_hash", "aad3b435...",
        "CORP", "test-target-1", json.dumps([{"target_id": "test-target-1", "result": "success"}]),
    )
    resp = await client.get("/api/operations/test-op-1/credential-graph")
    data = resp.json()
    assert len(data["nodes"]) >= 2  # credential + target
    assert len(data["edges"]) >= 1
