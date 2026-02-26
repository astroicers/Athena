# Copyright 2026 Athena Contributors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Athena backend test fixtures.

Key design decisions:
    - In-memory SQLite (``:memory:``) for full test isolation.
    - ``_CREATE_TABLES`` imported from ``app.database`` so the test schema
      always matches production.
    - FastAPI ``get_db`` dependency is overridden to inject the test DB.
    - ``httpx.AsyncClient`` with ``ASGITransport`` for realistic API tests.
    - ``ws_manager`` is replaced with a ``MagicMock`` so broadcast calls
      can be asserted without real WebSocket connections.
    - Environment variables ``MOCK_LLM`` and ``MOCK_CALDERA`` are set to
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
os.environ.setdefault("MOCK_CALDERA", "true")

from app.database import _CREATE_TABLES, get_db  # noqa: E402
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
    INSERT INTO c5isr_statuses (id, operation_id, domain, status, health_pct)
    VALUES
        ('c5-cmd',   'test-op-1', 'command',   'operational', 95.0),
        ('c5-ctrl',  'test-op-1', 'control',   'active',      88.0),
        ('c5-comms', 'test-op-1', 'comms',     'nominal',     78.0),
        ('c5-comp',  'test-op-1', 'computers', 'engaged',     70.0),
        ('c5-cyber', 'test-op-1', 'cyber',     'scanning',    55.0),
        ('c5-isr',   'test-op-1', 'isr',       'degraded',    40.0);
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
    return manager
