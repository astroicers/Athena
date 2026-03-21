# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: azz093093.830330@gmail.com

"""Integration tests for the Dashboard router."""

import json

from httpx import AsyncClient


# ---------------------------------------------------------------------------
# GET /api/operations/{id}/dashboard
# ---------------------------------------------------------------------------

async def test_get_dashboard(client: AsyncClient, seeded_db):
    """GET /api/operations/{op_id}/dashboard returns 200 with aggregated data."""
    resp = await client.get("/api/operations/test-op-1/dashboard")
    assert resp.status_code == 200
    data = resp.json()
    assert "operation" in data
    assert data["operation"]["id"] == "test-op-1"
    assert "c5isr" in data
    assert "targets" in data
    assert "opsec" in data
    assert "objectives" in data
    assert "recent_executions" in data


async def test_get_dashboard_not_found(client: AsyncClient):
    """GET /api/operations/{bad_id}/dashboard returns 404."""
    resp = await client.get("/api/operations/nonexistent-op-id/dashboard")
    assert resp.status_code == 404


async def test_dashboard_c5isr_sections(client: AsyncClient, seeded_db):
    """Dashboard c5isr contains seeded domain data."""
    resp = await client.get("/api/operations/test-op-1/dashboard")
    data = resp.json()
    assert isinstance(data["c5isr"], list)
    domains = {r["domain"] for r in data["c5isr"]}
    assert "command" in domains
    assert "control" in domains
    assert "cyber" in domains
    assert "isr" in domains


async def test_dashboard_targets_section(client: AsyncClient, seeded_db):
    """Dashboard targets section has correct structure."""
    resp = await client.get("/api/operations/test-op-1/dashboard")
    data = resp.json()
    targets = data["targets"]
    assert "total" in targets
    assert targets["total"] >= 1
    assert "compromised" in targets
    assert "hvt_total" in targets
    assert "hvt_compromised" in targets


async def test_dashboard_opsec_section(client: AsyncClient, seeded_db):
    """Dashboard opsec section has noise_10min and event_count."""
    resp = await client.get("/api/operations/test-op-1/dashboard")
    data = resp.json()
    opsec = data["opsec"]
    assert "noise_10min" in opsec
    assert "event_count" in opsec
    assert isinstance(opsec["noise_10min"], int)
    assert isinstance(opsec["event_count"], int)


async def test_dashboard_objectives_section(client: AsyncClient, seeded_db):
    """Dashboard objectives section has total/achieved/in_progress."""
    resp = await client.get("/api/operations/test-op-1/dashboard")
    data = resp.json()
    objectives = data["objectives"]
    assert "total" in objectives
    assert "achieved" in objectives
    assert "in_progress" in objectives


async def test_dashboard_recent_executions(client: AsyncClient, seeded_db):
    """Dashboard includes recent technique executions from seed data."""
    resp = await client.get("/api/operations/test-op-1/dashboard")
    data = resp.json()
    execs = data["recent_executions"]
    assert isinstance(execs, list)
    # Seeded data has 4 technique executions
    assert len(execs) >= 1
    assert "technique_id" in execs[0]
    assert "status" in execs[0]


# ---------------------------------------------------------------------------
# GET /api/operations/{id}/targets/{target_id}/kill-chain
# ---------------------------------------------------------------------------

async def test_get_kill_chain(client: AsyncClient, seeded_db):
    """GET /api/operations/{op_id}/targets/{target_id}/kill-chain returns 200."""
    resp = await client.get(
        "/api/operations/test-op-1/targets/test-target-1/kill-chain"
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    # Seeded data has 5 attack_graph_nodes for test-target-1
    assert len(data) >= 1
    assert "tactic_id" in data[0]
    assert "status" in data[0]
    assert "confidence" in data[0]


async def test_get_kill_chain_bad_operation(client: AsyncClient):
    """GET kill-chain with nonexistent operation returns 404."""
    resp = await client.get(
        "/api/operations/nonexistent-op-id/targets/test-target-1/kill-chain"
    )
    assert resp.status_code == 404


async def test_get_kill_chain_no_target_data(client: AsyncClient, seeded_db):
    """GET kill-chain for target with no graph nodes returns empty list."""
    resp = await client.get(
        "/api/operations/test-op-1/targets/nonexistent-target/kill-chain"
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data == []


# ---------------------------------------------------------------------------
# GET /api/operations/{id}/attack-surface
# ---------------------------------------------------------------------------

async def test_get_attack_surface(client: AsyncClient, seeded_db):
    """GET /api/operations/{op_id}/attack-surface returns 200 with target data."""
    resp = await client.get("/api/operations/test-op-1/attack-surface")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert "hostname" in data[0]
    assert "ip_address" in data[0]
    assert "vuln_count" in data[0]
    assert "critical" in data[0]
    assert "high" in data[0]


async def test_get_attack_surface_not_found(client: AsyncClient):
    """GET attack-surface with bad operation returns 404."""
    resp = await client.get("/api/operations/nonexistent-op-id/attack-surface")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /api/operations/{id}/metrics/time-series
# ---------------------------------------------------------------------------

async def test_time_series_c5isr(client: AsyncClient, seeded_db):
    """GET time-series with metric=c5isr returns a list."""
    resp = await client.get(
        "/api/operations/test-op-1/metrics/time-series?metric=c5isr"
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


async def test_time_series_opsec(client: AsyncClient, seeded_db):
    """GET time-series with metric=opsec returns a list."""
    resp = await client.get(
        "/api/operations/test-op-1/metrics/time-series?metric=opsec"
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


async def test_time_series_executions(client: AsyncClient, seeded_db):
    """GET time-series with metric=executions returns a list."""
    resp = await client.get(
        "/api/operations/test-op-1/metrics/time-series?metric=executions"
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


async def test_time_series_unknown_metric(client: AsyncClient, seeded_db):
    """GET time-series with unknown metric returns error dict."""
    resp = await client.get(
        "/api/operations/test-op-1/metrics/time-series?metric=bogus"
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "error" in data


async def test_time_series_granularity(client: AsyncClient, seeded_db):
    """GET time-series accepts granularity parameter."""
    resp = await client.get(
        "/api/operations/test-op-1/metrics/time-series?metric=c5isr&granularity=1h"
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


async def test_time_series_not_found(client: AsyncClient):
    """GET time-series with bad operation returns 404."""
    resp = await client.get(
        "/api/operations/nonexistent-op-id/metrics/time-series?metric=c5isr"
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /api/operations/{id}/credential-graph
# ---------------------------------------------------------------------------

async def test_credential_graph_empty(client: AsyncClient, seeded_db):
    """GET credential-graph with no credentials returns empty graph."""
    resp = await client.get("/api/operations/test-op-1/credential-graph")
    assert resp.status_code == 200
    data = resp.json()
    assert data["operation_id"] == "test-op-1"
    assert "nodes" in data
    assert "edges" in data
    assert isinstance(data["nodes"], list)
    assert isinstance(data["edges"], list)


async def test_credential_graph_with_data(client: AsyncClient, seeded_db):
    """GET credential-graph with seeded credential returns nodes and edges."""
    await seeded_db.execute(
        """INSERT INTO credentials (id, operation_id, username, secret_type, secret_value,
               domain, source_target_id, tested_targets)
           VALUES ($1, $2, $3, $4, $5, $6, $7, $8)""",
        "cred-router-1", "test-op-1", "admin", "ntlm_hash", "aad3b435...",
        "CORP", "test-target-1",
        json.dumps([{"target_id": "test-target-1", "result": "success"}]),
    )
    resp = await client.get("/api/operations/test-op-1/credential-graph")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["nodes"]) >= 2
    assert len(data["edges"]) >= 1


async def test_credential_graph_not_found(client: AsyncClient):
    """GET credential-graph with bad operation returns 404."""
    resp = await client.get("/api/operations/nonexistent-op-id/credential-graph")
    assert resp.status_code == 404
