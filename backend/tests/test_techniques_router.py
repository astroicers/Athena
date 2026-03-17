# Copyright (c) 2025 Athena Red Team Platform
# Author: azz093093.830330@gmail.com
# Project: Athena
# License: MIT
#
# This file is part of the Athena Red Team Platform.
# Unauthorized copying or distribution is prohibited.

"""Router tests for /api/techniques and /api/operations/{op_id}/techniques endpoints."""

import uuid
from unittest.mock import MagicMock, patch

import pytest_asyncio


# ---------------------------------------------------------------------------
# Module-scoped fixture: complete seed including a technique_execution that
# references test-tech-1 by id so the attack-path JOIN always returns data.
#
# All tests in this module share one DB setup + one long-lived connection,
# avoiding the pg_pool early-teardown issue in pytest-asyncio 1.3.0 that
# occurs when both function-scoped (client) and module-scoped fixtures try
# to acquire pg_pool in the same session.
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(scope="module")
async def tc(pg_pool):
    """Module-scoped client fixture for techniques tests.

    Yields a dict with:
      - "client": httpx.AsyncClient
      - "exec_id": str — pre-inserted technique_execution id
    """
    import asyncpg
    import os
    from httpx import ASGITransport, AsyncClient

    os.environ.setdefault("MOCK_LLM", "true")
    os.environ.setdefault("MOCK_C2_ENGINE", "true")
    os.environ.setdefault("MOCK_METASPLOIT", "true")

    from app.database import get_db
    from app.main import app
    from app.database.seed import TECHNIQUE_PLAYBOOK_SEEDS

    _DEFAULT_TEST_DSN = "postgresql://athena:athena_secret@localhost:55432/athena_test"
    TEST_DATABASE_URL: str = os.environ.get("TEST_DATABASE_URL", _DEFAULT_TEST_DSN)

    _ALL_TABLES = [
        "mission_objectives", "credentials", "opsec_events", "event_store",
        "c5isr_status_history",
        "vulnerabilities", "swarm_tasks", "attack_graph_edges", "attack_graph_nodes",
        "tool_registry", "technique_playbooks", "vuln_cache", "engagements",
        "recon_scans", "log_entries", "c5isr_statuses", "mission_steps",
        "recommendations", "ooda_directives", "ooda_iterations", "facts",
        "technique_executions", "techniques", "agents", "targets",
        "operations", "users",
    ]

    conn = await asyncpg.connect(TEST_DATABASE_URL)
    try:
        await conn.execute("SET session_replication_role = replica")
        table_list = ", ".join(_ALL_TABLES)
        await conn.execute(f"TRUNCATE {table_list} CASCADE")

        # Seed core rows
        await conn.execute("""
            INSERT INTO operations (id, code, name, codename, strategic_intent, status, current_ooda_phase)
            VALUES ('test-op-1', 'OP-TEST-001', 'Test Operation', 'PHANTOM-TEST',
                    'Test strategic intent', 'active', 'observe')
        """)
        await conn.execute("""
            INSERT INTO targets (id, hostname, ip_address, os, role, operation_id)
            VALUES ('test-target-1', 'DC-01', '10.0.1.5', 'Windows Server 2022',
                    'Domain Controller', 'test-op-1')
        """)
        await conn.execute("""
            INSERT INTO agents (id, paw, host_id, status, operation_id)
            VALUES ('test-agent-1', 'abc123', 'test-target-1', 'alive', 'test-op-1')
        """)
        await conn.execute("""
            INSERT INTO techniques (id, mitre_id, name, tactic, tactic_id, risk_level)
            VALUES ('test-tech-1', 'T1003.001', 'LSASS Memory', 'Credential Access',
                    'TA0006', 'medium')
        """)

        # Seed technique_playbooks
        for seed in TECHNIQUE_PLAYBOOK_SEEDS:
            await conn.execute(
                """INSERT INTO technique_playbooks
                   (id, mitre_id, platform, command, output_parser, facts_traits, source, tags)
                   VALUES ($1, $2, $3, $4, $5, $6, 'seed', $7)
                   ON CONFLICT DO NOTHING""",
                str(uuid.uuid4()), seed["mitre_id"], seed["platform"],
                seed["command"], seed.get("output_parser"),
                seed["facts_traits"], seed["tags"],
            )

        # Pre-insert one technique_execution that references test-tech-1 by ID
        # so the attack-path JOIN (te.technique_id = t.id) succeeds.
        exec_id = str(uuid.uuid4())
        await conn.execute(
            """INSERT INTO technique_executions
                   (id, technique_id, target_id, operation_id, engine, status)
               VALUES ($1, 'test-tech-1', 'test-target-1', 'test-op-1', 'mcp_ssh', 'success')""",
            exec_id,
        )
    finally:
        try:
            await conn.execute("SET session_replication_role = DEFAULT")
        except Exception:
            pass
        await conn.close()

    # Long-lived connection for get_db dependency override
    db_conn = await asyncpg.connect(TEST_DATABASE_URL)

    async def _override_get_db():
        yield db_conn

    app.dependency_overrides[get_db] = _override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield {"client": ac, "exec_id": exec_id}

    app.dependency_overrides.pop(get_db, None)
    await db_conn.close()


# ---------------------------------------------------------------------------
# GET /api/techniques
# ---------------------------------------------------------------------------


async def test_list_techniques(tc):
    """GET /api/techniques returns 200 and includes the seeded test-tech-1."""
    resp = await tc["client"].get("/api/techniques")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    ids = [t["id"] for t in data]
    assert "test-tech-1" in ids


# ---------------------------------------------------------------------------
# POST /api/techniques
# ---------------------------------------------------------------------------


async def test_create_technique(tc):
    """POST /api/techniques creates a new technique and returns 201."""
    payload = {
        "mitre_id": "T9999.001",
        "name": "Test Credential Dump",
        "tactic": "Credential Access",
        "tactic_id": "TA0006",
        "description": "A test technique",
        "kill_chain_stage": "exploit",
        "risk_level": "high",
        "platforms": ["windows"],
    }
    resp = await tc["client"].post("/api/techniques", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["mitre_id"] == "T9999.001"
    assert data["name"] == "Test Credential Dump"


# ---------------------------------------------------------------------------
# POST /api/techniques/sync-c2 → 202 Accepted (async background task)
# ---------------------------------------------------------------------------


async def test_sync_c2_abilities_returns_202(tc):
    """POST /api/techniques/sync-c2 enqueues a background task and returns 202."""
    with patch("app.routers.techniques.asyncio.create_task") as mock_task:
        mock_task.return_value = MagicMock()
        resp = await tc["client"].post("/api/techniques/sync-c2")

    assert resp.status_code == 202
    mock_task.assert_called_once()
    data = resp.json()
    assert data["status"] == "sync_started"


# ---------------------------------------------------------------------------
# GET /api/operations/{op_id}/techniques
# ---------------------------------------------------------------------------


async def test_list_techniques_with_status(tc):
    """GET /api/operations/test-op-1/techniques returns 200 with status-enriched techniques."""
    resp = await tc["client"].get("/api/operations/test-op-1/techniques")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    # seeded technique test-tech-1 (T1003.001) must be present
    ids = [t["id"] for t in data]
    assert "test-tech-1" in ids
    # Each item should carry the status fields
    entry = next(t for t in data if t["id"] == "test-tech-1")
    assert "latest_status" in entry
    assert "latest_execution_id" in entry


async def test_list_techniques_with_status_unknown_op(tc):
    """GET /api/operations/nonexistent/techniques returns 404."""
    resp = await tc["client"].get("/api/operations/nonexistent/techniques")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /api/operations/{op_id}/attack-path
# ---------------------------------------------------------------------------


async def test_get_attack_path(tc):
    """GET /api/operations/test-op-1/attack-path returns 200 with expected structure."""
    resp = await tc["client"].get("/api/operations/test-op-1/attack-path")
    assert resp.status_code == 200
    data = resp.json()
    assert data["operation_id"] == "test-op-1"
    assert "entries" in data
    assert "highest_tactic_idx" in data
    assert "tactic_coverage" in data


async def test_get_attack_path_unknown_op(tc):
    """GET /api/operations/nonexistent/attack-path returns 404."""
    resp = await tc["client"].get("/api/operations/nonexistent/attack-path")
    assert resp.status_code == 404


async def test_get_attack_path_has_entries(tc):
    """GET /api/operations/test-op-1/attack-path returns entries for the pre-seeded
    technique_execution whose technique_id = test-tech-1 (id, not mitre_id).
    """
    exec_id = tc["exec_id"]
    resp = await tc["client"].get("/api/operations/test-op-1/attack-path")
    assert resp.status_code == 200
    data = resp.json()
    # At least the one execution we pre-seeded should appear
    assert len(data["entries"]) >= 1
    exec_ids = {e["execution_id"] for e in data["entries"]}
    assert exec_id in exec_ids
    # The technique fields should be filled from the joined row
    entry = next(e for e in data["entries"] if e["execution_id"] == exec_id)
    assert entry["mitre_id"] == "T1003.001"
    assert entry["technique_name"] == "LSASS Memory"
