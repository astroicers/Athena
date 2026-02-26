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

from collections.abc import AsyncGenerator
from pathlib import Path

import aiosqlite

from app.config import settings

# ---------------------------------------------------------------------------
# Parse DB file path from settings.DATABASE_URL (strip "sqlite:///" prefix)
# Resolve relative paths against the project root (parent of backend/).
# ---------------------------------------------------------------------------
_raw_path: str = settings.DATABASE_URL.removeprefix("sqlite:///")
_PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent.parent  # …/Athena
_DB_FILE: str = str((_PROJECT_ROOT / _raw_path).resolve()) if not Path(_raw_path).is_absolute() else _raw_path

# ---------------------------------------------------------------------------
# 12 CREATE TABLE statements — exact copies from data-architecture.md Section 5
# ---------------------------------------------------------------------------
_CREATE_TABLES: list[str] = [
    """
    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        callsign TEXT NOT NULL,
        role TEXT DEFAULT 'Commander',
        created_at TEXT DEFAULT (datetime('now'))
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS operations (
        id TEXT PRIMARY KEY,
        code TEXT NOT NULL UNIQUE,
        name TEXT NOT NULL,
        codename TEXT NOT NULL,
        strategic_intent TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'planning',
        current_ooda_phase TEXT NOT NULL DEFAULT 'observe',
        ooda_iteration_count INTEGER DEFAULT 0,
        threat_level REAL DEFAULT 0.0,
        success_rate REAL DEFAULT 0.0,
        techniques_executed INTEGER DEFAULT 0,
        techniques_total INTEGER DEFAULT 0,
        active_agents INTEGER DEFAULT 0,
        data_exfiltrated_bytes INTEGER DEFAULT 0,
        automation_mode TEXT DEFAULT 'semi_auto',
        risk_threshold TEXT DEFAULT 'medium',
        operator_id TEXT REFERENCES users(id) ON DELETE SET NULL,
        created_at TEXT DEFAULT (datetime('now')),
        updated_at TEXT DEFAULT (datetime('now'))
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS targets (
        id TEXT PRIMARY KEY,
        hostname TEXT NOT NULL,
        ip_address TEXT NOT NULL,
        os TEXT,
        role TEXT NOT NULL,
        network_segment TEXT DEFAULT '10.0.1.0/24',
        is_compromised INTEGER DEFAULT 0,
        privilege_level TEXT,
        operation_id TEXT REFERENCES operations(id) ON DELETE CASCADE,
        created_at TEXT DEFAULT (datetime('now'))
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS agents (
        id TEXT PRIMARY KEY,
        paw TEXT NOT NULL,
        host_id TEXT REFERENCES targets(id) ON DELETE CASCADE,
        status TEXT DEFAULT 'pending',
        privilege TEXT DEFAULT 'User',
        last_beacon TEXT,
        beacon_interval_sec INTEGER DEFAULT 5,
        platform TEXT DEFAULT 'windows',
        operation_id TEXT REFERENCES operations(id) ON DELETE CASCADE,
        created_at TEXT DEFAULT (datetime('now'))
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS techniques (
        id TEXT PRIMARY KEY,
        mitre_id TEXT NOT NULL UNIQUE,
        name TEXT NOT NULL,
        tactic TEXT NOT NULL,
        tactic_id TEXT NOT NULL,
        description TEXT,
        kill_chain_stage TEXT DEFAULT 'exploit',
        risk_level TEXT DEFAULT 'medium',
        caldera_ability_id TEXT,
        platforms TEXT DEFAULT '["windows"]'
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS technique_executions (
        id TEXT PRIMARY KEY,
        technique_id TEXT NOT NULL,
        target_id TEXT REFERENCES targets(id) ON DELETE CASCADE,
        operation_id TEXT REFERENCES operations(id) ON DELETE CASCADE,
        ooda_iteration_id TEXT,
        engine TEXT DEFAULT 'caldera',
        status TEXT DEFAULT 'queued',
        result_summary TEXT,
        facts_collected_count INTEGER DEFAULT 0,
        started_at TEXT,
        completed_at TEXT,
        error_message TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS facts (
        id TEXT PRIMARY KEY,
        trait TEXT NOT NULL,
        value TEXT NOT NULL,
        category TEXT DEFAULT 'host',
        source_technique_id TEXT,
        source_target_id TEXT,
        operation_id TEXT REFERENCES operations(id) ON DELETE CASCADE,
        score INTEGER DEFAULT 1,
        collected_at TEXT DEFAULT (datetime('now'))
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS ooda_iterations (
        id TEXT PRIMARY KEY,
        operation_id TEXT REFERENCES operations(id) ON DELETE CASCADE,
        iteration_number INTEGER NOT NULL,
        phase TEXT DEFAULT 'observe',
        observe_summary TEXT,
        orient_summary TEXT,
        decide_summary TEXT,
        act_summary TEXT,
        recommendation_id TEXT,
        technique_execution_id TEXT,
        started_at TEXT DEFAULT (datetime('now')),
        completed_at TEXT
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS recommendations (
        id TEXT PRIMARY KEY,
        operation_id TEXT REFERENCES operations(id) ON DELETE CASCADE,
        ooda_iteration_id TEXT,
        situation_assessment TEXT NOT NULL,
        recommended_technique_id TEXT NOT NULL,
        confidence REAL NOT NULL,
        options TEXT NOT NULL,
        reasoning_text TEXT NOT NULL,
        accepted INTEGER,
        created_at TEXT DEFAULT (datetime('now'))
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS mission_steps (
        id TEXT PRIMARY KEY,
        operation_id TEXT REFERENCES operations(id) ON DELETE CASCADE,
        step_number INTEGER NOT NULL,
        technique_id TEXT NOT NULL,
        technique_name TEXT NOT NULL,
        target_id TEXT REFERENCES targets(id) ON DELETE CASCADE,
        target_label TEXT NOT NULL,
        engine TEXT DEFAULT 'caldera',
        status TEXT DEFAULT 'queued',
        created_at TEXT DEFAULT (datetime('now')),
        started_at TEXT,
        completed_at TEXT
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS c5isr_statuses (
        id TEXT PRIMARY KEY,
        operation_id TEXT REFERENCES operations(id) ON DELETE CASCADE,
        domain TEXT NOT NULL,
        status TEXT NOT NULL,
        health_pct REAL DEFAULT 100.0,
        detail TEXT DEFAULT '',
        updated_at TEXT DEFAULT (datetime('now')),
        UNIQUE(operation_id, domain)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS log_entries (
        id TEXT PRIMARY KEY,
        timestamp TEXT DEFAULT (datetime('now')),
        severity TEXT DEFAULT 'info',
        source TEXT NOT NULL,
        message TEXT NOT NULL,
        operation_id TEXT,
        technique_id TEXT,
        target_id TEXT
    );
    """,
]


async def init_db() -> None:
    """Create all 12 tables. Auto-creates the data directory if missing."""
    db_path = Path(_DB_FILE)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    async with aiosqlite.connect(str(db_path)) as db:
        await db.execute("PRAGMA foreign_keys = ON;")
        await db.execute("PRAGMA journal_mode = WAL;")
        for ddl in _CREATE_TABLES:
            await db.execute(ddl)
        await db.commit()


async def get_db() -> AsyncGenerator[aiosqlite.Connection, None]:
    """Async generator for FastAPI Depends injection."""
    db_path = Path(_DB_FILE)
    db = await aiosqlite.connect(str(db_path))
    await db.execute("PRAGMA foreign_keys = ON;")
    try:
        yield db
    finally:
        await db.close()
