# Copyright (c) 2025 Athena Red Team Platform
# Author: azz093093.830330@gmail.com
# Project: Athena
# License: MIT
#
# This file is part of the Athena Red Team Platform.
# Unauthorized copying or distribution is prohibited.

"""Router tests for /api/operations/{op_id}/vulnerabilities endpoints.

Note: The vulnerabilities router registers itself with prefix="/api" internally,
and the app mounts it without an additional prefix, so the effective URL path
is /api/operations/{op_id}/vulnerabilities (no double-prefix).
"""

import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio


# ---------------------------------------------------------------------------
# Module-scoped fixture: insert vulnerabilities once for this module.
# Using module scope avoids the seeded_db/client double-fixture conflict that
# causes UniqueViolationErrors when function-scoped seeded_db is requested
# twice in the same test (once by client, once explicitly).
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(scope="module")
async def client_with_vulns(pg_pool):
    """Async HTTP client whose DB has both seed data and two vulnerability rows.

    Shares the session-scoped pg_pool; truncates and re-seeds once per module.
    Provides two vulnerabilities:
      - vuln_discovered: status='discovered'  (can transition to confirmed)
      - vuln_reported:   status='reported'    (terminal — no valid transitions)
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

        # Seed core data
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

        # Insert the two vulnerabilities this module needs
        now = datetime.now(timezone.utc)
        vuln_discovered_id = str(uuid.uuid4())
        vuln_reported_id = str(uuid.uuid4())

        await conn.execute(
            """INSERT INTO vulnerabilities
                   (id, operation_id, cve_id, target_id, severity, status,
                    cvss_score, description, source_fact_id, discovered_at)
               VALUES ($1, 'test-op-1', 'CVE-2024-1111', 'test-target-1',
                       'high', 'discovered', 8.5, 'Discovered vuln', NULL, $2)""",
            vuln_discovered_id, now,
        )
        await conn.execute(
            """INSERT INTO vulnerabilities
                   (id, operation_id, cve_id, target_id, severity, status,
                    cvss_score, description, source_fact_id, discovered_at)
               VALUES ($1, 'test-op-1', 'CVE-2024-2222', 'test-target-1',
                       'critical', 'reported', 9.8, 'Reported terminal vuln', NULL, $2)""",
            vuln_reported_id, now,
        )
    finally:
        try:
            await conn.execute("SET session_replication_role = DEFAULT")
        except Exception:
            pass
        await conn.close()

    # Build a fresh connection for get_db override
    db_conn = await asyncpg.connect(TEST_DATABASE_URL)

    async def _override_get_db():
        yield db_conn

    app.dependency_overrides[get_db] = _override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac, vuln_discovered_id, vuln_reported_id

    app.dependency_overrides.pop(get_db, None)
    await db_conn.close()


# ---------------------------------------------------------------------------
# GET /api/operations/{op_id}/vulnerabilities
# ---------------------------------------------------------------------------


async def test_list_vulnerabilities(client_with_vulns):
    """GET /api/operations/test-op-1/vulnerabilities returns 200 with expected shape."""
    ac, _disc, _rep = client_with_vulns
    resp = await ac.get("/api/operations/test-op-1/vulnerabilities")
    assert resp.status_code == 200
    data = resp.json()
    assert "vulnerabilities" in data
    assert "summary" in data
    assert isinstance(data["vulnerabilities"], list)
    assert len(data["vulnerabilities"]) >= 2


async def test_list_vulnerabilities_unknown_op(client_with_vulns):
    """GET /api/operations/nonexistent/vulnerabilities returns 404."""
    ac, _disc, _rep = client_with_vulns
    resp = await ac.get("/api/operations/nonexistent/vulnerabilities")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# PUT /api/operations/{op_id}/vulnerabilities/{vuln_id}/status
# ---------------------------------------------------------------------------


async def test_update_vulnerability_status(client_with_vulns):
    """PUT status transitions a vulnerability from 'discovered' to 'confirmed' → 200."""
    ac, vuln_id, _rep = client_with_vulns
    resp = await ac.put(
        f"/api/operations/test-op-1/vulnerabilities/{vuln_id}/status",
        json={"status": "confirmed"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "confirmed"
    assert data["id"] == vuln_id


async def test_update_vulnerability_status_invalid(client_with_vulns):
    """PUT with an invalid / disallowed status transition returns 400."""
    ac, _disc, vuln_reported_id = client_with_vulns
    resp = await ac.put(
        f"/api/operations/test-op-1/vulnerabilities/{vuln_reported_id}/status",
        json={"status": "confirmed"},
    )
    # 'reported' is a terminal state — no transitions allowed → 400
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# GET /api/operations/{op_id}/vulnerabilities/summary
# ---------------------------------------------------------------------------


async def test_get_vulnerability_summary(client_with_vulns):
    """GET /api/operations/test-op-1/vulnerabilities/summary returns 200 with aggregate shape."""
    ac, _disc, _rep = client_with_vulns
    resp = await ac.get("/api/operations/test-op-1/vulnerabilities/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert "total" in data
    assert "by_severity" in data
    assert "by_status" in data
    # by_severity must contain all 5 severity levels
    for sev in ("critical", "high", "medium", "low", "info"):
        assert sev in data["by_severity"]


async def test_get_vulnerability_summary_unknown_op(client_with_vulns):
    """GET /api/operations/nonexistent/vulnerabilities/summary returns 404."""
    ac, _disc, _rep = client_with_vulns
    resp = await ac.get("/api/operations/nonexistent/vulnerabilities/summary")
    assert resp.status_code == 404
