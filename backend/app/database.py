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
from uuid import uuid4

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
# 13 CREATE TABLE statements — exact copies from data-architecture.md Section 5
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
        max_iterations INTEGER DEFAULT 0,
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
    """
    CREATE TABLE IF NOT EXISTS recon_scans (
        id TEXT PRIMARY KEY,
        operation_id TEXT REFERENCES operations(id) ON DELETE CASCADE,
        target_id TEXT REFERENCES targets(id) ON DELETE CASCADE,
        status TEXT DEFAULT 'pending',
        nmap_result TEXT,
        open_ports TEXT,
        os_guess TEXT,
        initial_access_method TEXT,
        credential_found TEXT,
        agent_deployed INTEGER DEFAULT 0,
        started_at TEXT,
        completed_at TEXT
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS engagements (
        id TEXT PRIMARY KEY,
        operation_id TEXT REFERENCES operations(id) ON DELETE CASCADE,
        client_name TEXT NOT NULL,
        contact_email TEXT NOT NULL,
        roe_document_path TEXT,
        roe_signed_at TEXT,
        scope_type TEXT DEFAULT 'whitelist',
        in_scope TEXT NOT NULL DEFAULT '[]',
        out_of_scope TEXT DEFAULT '[]',
        start_time TEXT,
        end_time TEXT,
        emergency_contact TEXT,
        status TEXT DEFAULT 'draft',
        created_at TEXT DEFAULT (datetime('now'))
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS vuln_cache (
        id TEXT PRIMARY KEY,
        cpe_string TEXT NOT NULL,
        cve_id TEXT NOT NULL,
        cvss_score REAL,
        severity TEXT,
        description TEXT,
        exploit_available INTEGER DEFAULT 0,
        cached_at TEXT DEFAULT (datetime('now')),
        UNIQUE(cpe_string, cve_id)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS technique_playbooks (
        id TEXT PRIMARY KEY,
        mitre_id TEXT NOT NULL,
        platform TEXT NOT NULL DEFAULT 'linux',
        command TEXT NOT NULL,
        output_parser TEXT,
        facts_traits TEXT NOT NULL DEFAULT '[]',
        source TEXT DEFAULT 'seed',
        tags TEXT DEFAULT '[]',
        created_at TEXT DEFAULT (datetime('now'))
    );
    """,
]

# ---------------------------------------------------------------------------
# Seed data for technique_playbooks — 13 Linux techniques
# Uses INSERT OR IGNORE so restarts are safe (no duplicate key errors).
# ---------------------------------------------------------------------------
TECHNIQUE_PLAYBOOK_SEEDS = [
    {"mitre_id": "T1592", "platform": "linux",
     "command": "uname -a && id && cat /etc/os-release",
     "facts_traits": '["host.os", "host.user"]',
     "tags": '["reconnaissance"]'},
    {"mitre_id": "T1046", "platform": "linux",
     "command": "netstat -tulnp 2>/dev/null || ss -tulnp 2>/dev/null",
     "facts_traits": '["service.open_port"]',
     "tags": '["discovery"]'},
    {"mitre_id": "T1059.004", "platform": "linux",
     "command": "bash -c 'id && whoami && hostname'",
     "facts_traits": '["host.process"]',
     "tags": '["execution"]'},
    {"mitre_id": "T1003.001", "platform": "linux",
     "command": "cat /etc/shadow 2>/dev/null || echo 'NO_SHADOW_ACCESS'",
     "facts_traits": '["credential.hash"]',
     "tags": '["credential_access"]'},
    {"mitre_id": "T1087", "platform": "linux",
     "command": "cat /etc/passwd | cut -d: -f1,3,7",
     "facts_traits": '["host.user"]',
     "tags": '["discovery"]'},
    {"mitre_id": "T1083", "platform": "linux",
     "command": "find / -name '*.conf' -readable 2>/dev/null | head -20",
     "facts_traits": '["host.file"]',
     "tags": '["discovery"]'},
    {"mitre_id": "T1190", "platform": "linux",
     "command": "curl -sI http://localhost/ 2>/dev/null | head -5",
     "facts_traits": '["service.web"]',
     "tags": '["initial_access"]'},
    {"mitre_id": "T1595.001", "platform": "linux",
     "command": "nmap -sV -Pn --top-ports 25 {target_ip} 2>/dev/null || echo 'NMAP_UNAVAILABLE'",
     "facts_traits": '["network.host.ip"]',
     "tags": '["reconnaissance"]'},
    {"mitre_id": "T1595.002", "platform": "linux",
     "command": "nmap --script vuln -Pn {target_ip} 2>/dev/null || echo 'NMAP_UNAVAILABLE'",
     "facts_traits": '["vuln.cve"]',
     "tags": '["reconnaissance"]'},
    {"mitre_id": "T1021.004", "platform": "linux",
     "command": "ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 {target_ip} id 2>/dev/null || echo 'SSH_LATERAL_UNAVAILABLE'",
     "facts_traits": '["host.session"]',
     "tags": '["lateral_movement"]'},
    {"mitre_id": "T1078.001", "platform": "linux",
     "command": "id && cat /etc/passwd | grep -v nologin | grep -v false",
     "facts_traits": '["credential.ssh"]',
     "tags": '["initial_access"]'},
    {"mitre_id": "T1110.001", "platform": "linux",
     "command": "echo 'SSH_BRUTEFORCE_HANDLED_BY_INITIAL_ACCESS_ENGINE'",
     "facts_traits": '["credential.ssh"]',
     "tags": '["initial_access"]'},
    {"mitre_id": "T1110.003", "platform": "linux",
     "command": "echo 'CREDENTIAL_SPRAY_HANDLED_BY_INITIAL_ACCESS_ENGINE'",
     "facts_traits": '["credential.ssh"]',
     "tags": '["initial_access"]'},
    {"mitre_id": "T1021.004_priv", "platform": "linux",
     "command": "sudo -l 2>/dev/null && sudo -n id 2>/dev/null",
     "output_parser": "first_line",
     "facts_traits": '["host.privilege"]',
     "tags": '["lateral_move","privilege_escalation","ssh"]'},
    {"mitre_id": "T1021.004_recon", "platform": "linux",
     "command": "id && hostname && ip addr show && cat /etc/hosts",
     "output_parser": "first_line",
     "facts_traits": '["host.os","host.network"]',
     "tags": '["lateral_move","discovery","ssh"]'},
    {"mitre_id": "T1560.001", "platform": "linux",
     "command": "tar czf /tmp/.bundle.tgz /etc/passwd /etc/shadow 2>/dev/null && echo BUNDLED",
     "output_parser": "first_line",
     "facts_traits": '["host.file"]',
     "tags": '["collection","staging","linux"]'},
    {"mitre_id": "T1105", "platform": "linux",
     "command": "which curl wget python3 nc 2>/dev/null | head -5",
     "output_parser": "first_line",
     "facts_traits": '["host.binary"]',
     "tags": '["transfer","c2","linux"]'},
    {"mitre_id": "T1053.003", "platform": "linux",
     "command": "ls -la /etc/cron.d/ 2>/dev/null | head -5",
     "output_parser": "first_line",
     "facts_traits": '["host.persistence"]',
     "tags": '["persistence","cron","linux"]'},
    {"mitre_id": "T1543.002", "platform": "linux",
     "command": "systemctl list-units --type=service --state=running 2>/dev/null | head -10",
     "output_parser": "first_line",
     "facts_traits": '["host.service"]',
     "tags": '["persistence","systemd","linux"]'},
    {"mitre_id": "T1136.001", "platform": "linux",
     "command": "id; getent passwd | cut -d: -f1,3,7 | head -10",
     "output_parser": "first_line",
     "facts_traits": '["host.user"]',
     "tags": '["persistence","account_creation","linux"]'},
    {"mitre_id": "T1021.001", "platform": "windows",
     "command": "whoami; hostname; ipconfig /all | Select-String 'IPv4'",
     "output_parser": "first_line",
     "facts_traits": '["host.os","host.network"]',
     "tags": '["lateral_move","winrm","windows"]'},
    {"mitre_id": "T1053.005", "platform": "windows",
     "command": "schtasks /query /fo CSV /nh 2>$null | Select-Object -First 10",
     "output_parser": "first_line",
     "facts_traits": '["host.persistence"]',
     "tags": '["persistence","scheduled_task","windows"]'},
    {"mitre_id": "T1059.001", "platform": "windows",
     "command": "whoami; $env:COMPUTERNAME; Get-Process | Select-Object -First 5 Name,Id",
     "output_parser": "first_line",
     "facts_traits": '["host.os"]',
     "tags": '["execution","powershell","windows"]'},
]


async def _seed_technique_playbooks(db: aiosqlite.Connection) -> None:
    """Insert seed playbooks only when the table is empty (idempotent)."""
    async with db.execute("SELECT COUNT(*) FROM technique_playbooks") as cursor:
        row = await cursor.fetchone()
        count = row[0] if row else 0

    if count > 0:
        return  # Already seeded — skip

    for seed in TECHNIQUE_PLAYBOOK_SEEDS:
        await db.execute(
            """
            INSERT OR IGNORE INTO technique_playbooks
                (id, mitre_id, platform, command, facts_traits, source, tags)
            VALUES (?, ?, ?, ?, ?, 'seed', ?)
            """,
            (
                str(uuid4()),
                seed["mitre_id"],
                seed["platform"],
                seed["command"],
                seed["facts_traits"],
                seed["tags"],
            ),
        )


async def init_db() -> None:
    """Create all tables and seed initial data. Auto-creates the data directory if missing."""
    db_path = Path(_DB_FILE)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    async with aiosqlite.connect(str(db_path)) as db:
        await db.execute("PRAGMA foreign_keys = ON;")
        await db.execute("PRAGMA journal_mode = WAL;")
        for ddl in _CREATE_TABLES:
            await db.execute(ddl)
        await _seed_technique_playbooks(db)
        # Migration: add max_iterations column if not present
        try:
            await db.execute("ALTER TABLE operations ADD COLUMN max_iterations INTEGER DEFAULT 0")
            await db.commit()
        except Exception:
            pass  # column already exists
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
