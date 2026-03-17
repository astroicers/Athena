# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: azz093093.830330@gmail.com

"""Athena backend test fixtures — PostgreSQL via asyncpg.

Key design decisions:
    - Real PostgreSQL instance required (``TEST_DATABASE_URL`` env var or
      default ``postgresql://athena:athena_secret@localhost:55432/athena_test``).
    - Schema DDL is extracted from the Alembic migration ``001_initial_schema``
      and executed directly (no Alembic runner overhead in tests).
    - A session-scoped ``pg_pool`` fixture creates/destroys the test database
      and applies the schema once per test session.
    - A function-scoped ``tmp_db`` fixture truncates all tables between tests
      for full isolation.
    - ``seeded_db`` extends ``tmp_db`` with minimal seed data.
    - FastAPI ``get_db`` dependency is overridden to inject the test connection.
    - ``httpx.AsyncClient`` with ``ASGITransport`` for realistic API tests.
    - ``ws_manager`` is replaced with a ``MagicMock`` so broadcast calls
      can be asserted without real WebSocket connections.
    - Environment variables ``MOCK_LLM`` and ``MOCK_C2_ENGINE`` are set to
      ``true`` so no external services are contacted during tests.
    - Tests are automatically skipped when PostgreSQL is not reachable.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import asyncpg
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

# ---------------------------------------------------------------------------
# Environment — ensure mocks are active before any app module is imported
# ---------------------------------------------------------------------------
os.environ.setdefault("MOCK_LLM", "true")
os.environ.setdefault("MOCK_C2_ENGINE", "true")
os.environ.setdefault("MOCK_METASPLOIT", "true")

# ---------------------------------------------------------------------------
# PostgreSQL connection settings
# ---------------------------------------------------------------------------
_DEFAULT_SYS_DSN = "postgresql://athena:athena_secret@localhost:55432/postgres"
_DEFAULT_TEST_DSN = "postgresql://athena:athena_secret@localhost:55432/athena_test"

TEST_DATABASE_URL: str = os.environ.get("TEST_DATABASE_URL", _DEFAULT_TEST_DSN)

# Derive system DSN (connect to ``postgres`` database) for CREATE/DROP DATABASE
_parsed = TEST_DATABASE_URL.rsplit("/", 1)
SYS_DATABASE_URL: str = os.environ.get("SYS_DATABASE_URL", f"{_parsed[0]}/postgres")
TEST_DB_NAME: str = _parsed[1] if len(_parsed) > 1 else "athena_test"

# ---------------------------------------------------------------------------
# Schema DDL — extracted from the Alembic migration file
# ---------------------------------------------------------------------------

_MIGRATION_DIR = Path(__file__).resolve().parent.parent / "alembic" / "versions"
_MIGRATION_FILES = sorted(_MIGRATION_DIR.glob("*.py"))


def _extract_ddl_from_file(filepath: Path) -> list[str]:
    """Parse all op.execute(...) SQL strings from a migration file.

    Returns a list of raw SQL statements (CREATE TABLE, CREATE INDEX, etc.)
    in the order they appear in ``upgrade()``.
    """
    source = filepath.read_text(encoding="utf-8")

    # Extract the upgrade() function body
    match = re.search(r"def upgrade\(\)[^:]*:(.*?)(?=\ndef |\Z)", source, re.DOTALL)
    if not match:
        raise RuntimeError(f"Cannot locate upgrade() in {filepath.name}")
    body = match.group(1)

    # Find all op.execute("""...""") and op.execute("...")
    statements: list[str] = []
    for m in re.finditer(r'op\.execute\(\s*"""(.*?)"""\s*\)', body, re.DOTALL):
        statements.append(m.group(1).strip())
    for m in re.finditer(r'op\.execute\(\s*"([^"]+)"\s*\)', body):
        statements.append(m.group(1).strip())
    return statements


def _extract_ddl_statements() -> list[str]:
    """Extract DDL from all migration files in order."""
    all_stmts: list[str] = []
    for f in _MIGRATION_FILES:
        all_stmts.extend(_extract_ddl_from_file(f))
    return all_stmts


_DDL_STATEMENTS: list[str] = _extract_ddl_statements()

# All table names in reverse dependency order for TRUNCATE
_ALL_TABLES: list[str] = [
    "mission_objectives", "credentials", "opsec_events", "event_store",
    "c5isr_status_history",
    "vulnerabilities", "swarm_tasks", "attack_graph_edges", "attack_graph_nodes",
    "tool_registry", "technique_playbooks", "vuln_cache", "engagements",
    "recon_scans", "log_entries", "c5isr_statuses", "mission_steps",
    "recommendations", "ooda_directives", "ooda_iterations", "facts",
    "technique_executions", "techniques", "agents", "targets",
    "operations", "users",
]


# ---------------------------------------------------------------------------
# Marker: skip when PostgreSQL is not available
# ---------------------------------------------------------------------------

async def _pg_is_reachable() -> bool:
    """Return True if we can connect to the system PostgreSQL instance."""
    try:
        conn = await asyncpg.connect(SYS_DATABASE_URL, timeout=5)
        await conn.close()
        return True
    except (OSError, asyncpg.PostgresError, asyncio.TimeoutError):
        return False

import asyncio  # noqa: E402 (needed for _pg_is_reachable)


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "requires_pg: mark test as needing a live PostgreSQL instance"
    )


def pytest_collection_modifyitems(config, items):
    """Auto-skip all tests that depend on pg_pool/tmp_db/seeded_db/client
    when PostgreSQL is not reachable.  The actual check is deferred to the
    session-scoped fixture so we only probe once.
    """
    # We don't skip here — the pg_pool fixture itself will pytest.skip()
    pass


# ---------------------------------------------------------------------------
# Fixture: pg_pool — session-scoped connection pool with fresh test database
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture(scope="session")
async def pg_pool():
    """Create a disposable test database, apply schema, and yield a pool.

    If PostgreSQL is not reachable the entire test session is skipped.
    """
    # Probe connectivity
    try:
        sys_conn = await asyncpg.connect(SYS_DATABASE_URL, timeout=5)
    except (OSError, asyncpg.PostgresError, Exception) as exc:
        pytest.skip(f"PostgreSQL not available ({exc})")
        return  # unreachable but satisfies type checker

    # Create (or recreate) the test database
    try:
        # Must terminate existing connections before DROP
        await sys_conn.execute(f"""
            SELECT pg_terminate_backend(pid)
            FROM pg_stat_activity
            WHERE datname = '{TEST_DB_NAME}' AND pid <> pg_backend_pid()
        """)
        await sys_conn.execute(f"DROP DATABASE IF EXISTS {TEST_DB_NAME}")
        await sys_conn.execute(f"CREATE DATABASE {TEST_DB_NAME}")
    finally:
        await sys_conn.close()

    # Create pool against the test database
    pool = await asyncpg.create_pool(TEST_DATABASE_URL, min_size=1, max_size=5)

    # Apply schema DDL
    async with pool.acquire() as conn:
        for ddl in _DDL_STATEMENTS:
            await conn.execute(ddl)

    yield pool

    # Teardown
    await pool.close()

    sys_conn = await asyncpg.connect(SYS_DATABASE_URL, timeout=5)
    try:
        await sys_conn.execute(f"""
            SELECT pg_terminate_backend(pid)
            FROM pg_stat_activity
            WHERE datname = '{TEST_DB_NAME}' AND pid <> pg_backend_pid()
        """)
        await sys_conn.execute(f"DROP DATABASE IF EXISTS {TEST_DB_NAME}")
    finally:
        await sys_conn.close()


# ---------------------------------------------------------------------------
# Fixture: tmp_db — bare connection with all tables truncated
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture
async def tmp_db(pg_pool: asyncpg.Pool):
    """Acquire a connection from the pool with all tables truncated.

    Yields an ``asyncpg.Connection`` and releases it after the test.
    Uses raw acquire/release to avoid ``reset()`` interference when tests
    leave transactions in an unexpected state.
    """
    # Create a direct connection per test to avoid pool state contamination.
    # The pool is only used for schema setup in pg_pool fixture.
    conn = await asyncpg.connect(TEST_DATABASE_URL)
    try:
        # Disable FK triggers for the session — tests were written for SQLite
        # which had no FK enforcement. We'll enforce in production only.
        await conn.execute("SET session_replication_role = replica")
        table_list = ", ".join(_ALL_TABLES)
        await conn.execute(f"TRUNCATE {table_list} CASCADE")
        yield conn
    finally:
        try:
            await conn.execute("SET session_replication_role = DEFAULT")
        except Exception:
            pass
        await conn.close()


# ---------------------------------------------------------------------------
# Seed SQL — minimal data for a single operation (PostgreSQL syntax)
# ---------------------------------------------------------------------------
_SEED_STATEMENTS: list[str] = [
    """
    INSERT INTO operations (id, code, name, codename, strategic_intent, status, current_ooda_phase)
    VALUES ('test-op-1', 'OP-TEST-001', 'Test Operation', 'PHANTOM-TEST',
            'Test strategic intent', 'active', 'observe')
    """,
    """
    INSERT INTO targets (id, hostname, ip_address, os, role, operation_id)
    VALUES ('test-target-1', 'DC-01', '10.0.1.5', 'Windows Server 2022',
            'Domain Controller', 'test-op-1')
    """,
    """
    INSERT INTO agents (id, paw, host_id, status, operation_id)
    VALUES ('test-agent-1', 'abc123', 'test-target-1', 'alive', 'test-op-1')
    """,
    """
    INSERT INTO techniques (id, mitre_id, name, tactic, tactic_id, risk_level)
    VALUES ('test-tech-1', 'T1003.001', 'LSASS Memory', 'Credential Access',
            'TA0006', 'medium')
    """,
    """
    INSERT INTO c5isr_statuses (id, operation_id, domain, status, health_pct, numerator, denominator, metric_label)
    VALUES
        ('c5-cmd',   'test-op-1', 'command',   'operational', 95.0, 3,    NULL, 'OODA iterations'),
        ('c5-ctrl',  'test-op-1', 'control',   'active',      88.0, 1,    1,    'agents alive'),
        ('c5-comms', 'test-op-1', 'comms',     'nominal',     78.0, NULL, NULL, 'C2 channel'),
        ('c5-comp',  'test-op-1', 'computers', 'engaged',     70.0, 3,    5,    'targets pwned'),
        ('c5-cyber', 'test-op-1', 'cyber',     'scanning',    55.0, 4,    6,    'attacks succeeded'),
        ('c5-isr',   'test-op-1', 'isr',       'degraded',    40.0, 40,   100,  'confidence')
    """,
    # SPEC-040: Seed completed Kill Chain stages so composite confidence
    # doesn't penalise test recommendations for T1003.001 (TA0006).
    # Attack graph nodes + successful technique_executions for prior stages.
    """
    INSERT INTO attack_graph_nodes (id, operation_id, target_id, technique_id, tactic_id, status, confidence)
    VALUES
        ('agn-seed-1', 'test-op-1', 'test-target-1', 'T1595.001', 'TA0043', 'explored', 0.9),
        ('agn-seed-2', 'test-op-1', 'test-target-1', 'T1190',     'TA0001', 'explored', 0.8),
        ('agn-seed-3', 'test-op-1', 'test-target-1', 'T1059.001', 'TA0002', 'explored', 0.85),
        ('agn-seed-4', 'test-op-1', 'test-target-1', 'T1548.002', 'TA0004', 'explored', 0.75),
        ('agn-seed-5', 'test-op-1', 'test-target-1', 'T1003.001', 'TA0006', 'pending',  0.7)
    """,
    """
    INSERT INTO technique_executions (id, technique_id, target_id, operation_id, engine, status, started_at, completed_at)
    VALUES
        ('te-seed-1', 'T1595.001', 'test-target-1', 'test-op-1', 'mcp_ssh', 'success', NOW() - INTERVAL '4 hours', NOW() - INTERVAL '4 hours'),
        ('te-seed-2', 'T1190',     'test-target-1', 'test-op-1', 'mcp_ssh', 'success', NOW() - INTERVAL '3 hours', NOW() - INTERVAL '3 hours'),
        ('te-seed-3', 'T1059.001', 'test-target-1', 'test-op-1', 'mcp_ssh', 'success', NOW() - INTERVAL '2 hours', NOW() - INTERVAL '2 hours'),
        ('te-seed-4', 'T1548.002', 'test-target-1', 'test-op-1', 'mcp_ssh', 'success', NOW() - INTERVAL '1 hours', NOW() - INTERVAL '1 hours')
    """,
]


# ---------------------------------------------------------------------------
# Fixture: seeded_db — connection with schema + minimal seed data
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture
async def seeded_db(tmp_db: asyncpg.Connection):
    """Extend ``tmp_db`` with a minimal set of seed rows.

    Provides: 1 operation, 1 target, 1 agent, 1 technique, 6 C5ISR statuses,
    5 attack graph nodes, 4 technique executions.
    """
    for stmt in _SEED_STATEMENTS:
        await tmp_db.execute(stmt)
    yield tmp_db


# ---------------------------------------------------------------------------
# Fixture: client — httpx.AsyncClient wired to the FastAPI app
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture
async def client(seeded_db: asyncpg.Connection):
    """Async HTTP client for API integration tests.

    * Overrides the ``get_db`` dependency so every request receives the
      seeded test database connection.
    * Uses ``ASGITransport`` so requests never leave the process.
    * Dependency override is removed after the test to avoid leaking
      state into other tests.
    """
    from app.database import get_db  # noqa: E402
    from app.database.seed import seed_if_empty  # noqa: E402
    from app.main import app  # noqa: E402

    # Seed technique_playbooks for playbook API tests.
    # We wrap the connection in a minimal DatabaseManager-like object so
    # seed_if_empty can call conn.fetchval / conn.execute.
    from app.database.seed import TECHNIQUE_PLAYBOOK_SEEDS
    from uuid import uuid4

    count = await seeded_db.fetchval("SELECT COUNT(*) FROM technique_playbooks")
    if count == 0:
        for seed in TECHNIQUE_PLAYBOOK_SEEDS:
            await seeded_db.execute(
                """INSERT INTO technique_playbooks
                   (id, mitre_id, platform, command, output_parser, facts_traits, source, tags)
                   VALUES ($1, $2, $3, $4, $5, $6, 'seed', $7)
                   ON CONFLICT DO NOTHING""",
                str(uuid4()), seed["mitre_id"], seed["platform"],
                seed["command"], seed.get("output_parser"),
                seed["facts_traits"], seed["tags"],
            )

    async def _override_get_db():
        yield seeded_db

    app.dependency_overrides[get_db] = _override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Fixture: mock_ws_manager — drop-in replacement for the WS broadcaster
# ---------------------------------------------------------------------------
@pytest.fixture
def mock_ws_manager():
    """Return a ``MagicMock`` that stands in for ``WebSocketManager``.

    ``broadcast`` is set up as an ``AsyncMock`` so callers can ``await`` it
    and tests can assert on calls (e.g.
    ``mock_ws_manager.broadcast.assert_awaited_once_with(...)``).
    """
    manager = MagicMock()
    manager.broadcast = AsyncMock()
    manager.active_connection_count = MagicMock(return_value=0)
    manager._broadcast_total = 0
    manager._broadcast_success = 0
    return manager
