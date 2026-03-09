# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: [TODO: contact email]

"""Athena backend test fixtures.

Key design decisions:
    - In-memory SQLite (``:memory:``) for full test isolation.
    - ``_CREATE_TABLES`` imported from ``app.database`` so the test schema
      always matches production.
    - FastAPI ``get_db`` dependency is overridden to inject the test DB.
    - ``httpx.AsyncClient`` with ``ASGITransport`` for realistic API tests.
    - ``ws_manager`` is replaced with a ``MagicMock`` so broadcast calls
      can be asserted without real WebSocket connections.
    - Environment variables ``MOCK_LLM`` and ``MOCK_C2_ENGINE`` are set to
      ``true`` so no external services are contacted during tests.
"""

import os
from unittest.mock import AsyncMock, MagicMock

import aiosqlite
import pytest
from httpx import ASGITransport, AsyncClient

# ---------------------------------------------------------------------------
# Environment — ensure mocks are active before any app module is imported
# ---------------------------------------------------------------------------
os.environ.setdefault("MOCK_LLM", "true")
os.environ.setdefault("MOCK_C2_ENGINE", "true")
os.environ.setdefault("MOCK_METASPLOIT", "true")

from app.database import _CREATE_TABLES, _seed_technique_playbooks, get_db  # noqa: E402
from app.main import app  # noqa: E402


# ---------------------------------------------------------------------------
# Fixture: tmp_db — bare in-memory database with schema only
# ---------------------------------------------------------------------------
@pytest.fixture
async def tmp_db():
    """Create an in-memory SQLite database with the full Athena schema.

    Yields an open ``aiosqlite.Connection`` and closes it after the test.
    Note: WAL mode is **not** enabled because it is incompatible with
    ``:memory:`` databases.
    """
    db = await aiosqlite.connect(":memory:")
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA foreign_keys = ON;")
    for ddl in _CREATE_TABLES:
        await db.execute(ddl)
    await db.commit()
    yield db
    await db.close()


# ---------------------------------------------------------------------------
# Seed SQL — minimal data for a single operation
# ---------------------------------------------------------------------------
_SEED_STATEMENTS: list[str] = [
    """
    INSERT INTO operations (id, code, name, codename, strategic_intent, status, current_ooda_phase)
    VALUES ('test-op-1', 'OP-TEST-001', 'Test Operation', 'PHANTOM-TEST',
            'Test strategic intent', 'active', 'observe');
    """,
    """
    INSERT INTO targets (id, hostname, ip_address, os, role, operation_id)
    VALUES ('test-target-1', 'DC-01', '10.0.1.5', 'Windows Server 2022',
            'Domain Controller', 'test-op-1');
    """,
    """
    INSERT INTO agents (id, paw, host_id, status, operation_id)
    VALUES ('test-agent-1', 'abc123', 'test-target-1', 'alive', 'test-op-1');
    """,
    """
    INSERT INTO techniques (id, mitre_id, name, tactic, tactic_id, risk_level)
    VALUES ('test-tech-1', 'T1003.001', 'LSASS Memory', 'Credential Access',
            'TA0006', 'medium');
    """,
    """
    INSERT INTO c5isr_statuses (id, operation_id, domain, status, health_pct, numerator, denominator, metric_label)
    VALUES
        ('c5-cmd',   'test-op-1', 'command',   'operational', 95.0, 3,    NULL, 'OODA iterations'),
        ('c5-ctrl',  'test-op-1', 'control',   'active',      88.0, 1,    1,    'agents alive'),
        ('c5-comms', 'test-op-1', 'comms',     'nominal',     78.0, NULL, NULL, 'C2 channel'),
        ('c5-comp',  'test-op-1', 'computers', 'engaged',     70.0, 3,    5,    'targets pwned'),
        ('c5-cyber', 'test-op-1', 'cyber',     'scanning',    55.0, 4,    6,    'attacks succeeded'),
        ('c5-isr',   'test-op-1', 'isr',       'degraded',    40.0, 40,   100,  'confidence');
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
        ('agn-seed-5', 'test-op-1', 'test-target-1', 'T1003.001', 'TA0006', 'pending',  0.7);
    """,
    """
    INSERT INTO technique_executions (id, technique_id, target_id, operation_id, engine, status, started_at, completed_at)
    VALUES
        ('te-seed-1', 'T1595.001', 'test-target-1', 'test-op-1', 'mcp_ssh', 'success', datetime('now','-4 hours'), datetime('now','-4 hours')),
        ('te-seed-2', 'T1190',     'test-target-1', 'test-op-1', 'mcp_ssh', 'success', datetime('now','-3 hours'), datetime('now','-3 hours')),
        ('te-seed-3', 'T1059.001', 'test-target-1', 'test-op-1', 'mcp_ssh', 'success', datetime('now','-2 hours'), datetime('now','-2 hours')),
        ('te-seed-4', 'T1548.002', 'test-target-1', 'test-op-1', 'mcp_ssh', 'success', datetime('now','-1 hours'), datetime('now','-1 hours'));
    """,
]


# ---------------------------------------------------------------------------
# Fixture: seeded_db — in-memory database with schema + minimal seed data
# ---------------------------------------------------------------------------
@pytest.fixture
async def seeded_db(tmp_db: aiosqlite.Connection):
    """Extend ``tmp_db`` with a minimal set of seed rows.

    Provides: 1 operation, 1 target, 1 agent, 1 technique, 6 C5ISR statuses.
    """
    for stmt in _SEED_STATEMENTS:
        await tmp_db.execute(stmt)
    await tmp_db.commit()
    yield tmp_db


# ---------------------------------------------------------------------------
# Fixture: client — httpx.AsyncClient wired to the FastAPI app
# ---------------------------------------------------------------------------
@pytest.fixture
async def client(seeded_db: aiosqlite.Connection):
    """Async HTTP client for API integration tests.

    * Overrides the ``get_db`` dependency so every request receives the
      seeded in-memory database.
    * Uses ``ASGITransport`` so requests never leave the process.
    * Dependency override is removed after the test to avoid leaking
      state into other tests.
    """

    # Seed technique_playbooks for playbook API tests
    await _seed_technique_playbooks(seeded_db)
    await seeded_db.commit()

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
