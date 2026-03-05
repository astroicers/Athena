# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: [TODO: contact email]

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
        is_active INTEGER DEFAULT 0,
        privilege_level TEXT,
        operation_id TEXT REFERENCES operations(id) ON DELETE CASCADE,
        created_at TEXT DEFAULT (datetime('now')),
        UNIQUE(ip_address, operation_id)
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
        created_at TEXT DEFAULT (datetime('now')),
        UNIQUE(paw, operation_id)
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
        c2_ability_id TEXT,
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
        engine TEXT DEFAULT 'ssh',
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
    CREATE TABLE IF NOT EXISTS ooda_directives (
        id TEXT PRIMARY KEY,
        operation_id TEXT NOT NULL REFERENCES operations(id) ON DELETE CASCADE,
        directive TEXT NOT NULL,
        scope TEXT DEFAULT 'next_cycle',
        created_at TEXT DEFAULT (datetime('now')),
        consumed_at TEXT
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
        engine TEXT DEFAULT 'ssh',
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
        ip_address TEXT,
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
    """
    CREATE TABLE IF NOT EXISTS tool_registry (
        id TEXT PRIMARY KEY,
        tool_id TEXT NOT NULL UNIQUE,
        name TEXT NOT NULL,
        description TEXT,
        kind TEXT NOT NULL DEFAULT 'tool',
        category TEXT NOT NULL DEFAULT 'reconnaissance',
        version TEXT,
        enabled INTEGER NOT NULL DEFAULT 1,
        source TEXT NOT NULL DEFAULT 'seed',
        config_json TEXT DEFAULT '{}',
        mitre_techniques TEXT DEFAULT '[]',
        risk_level TEXT DEFAULT 'low',
        output_traits TEXT DEFAULT '[]',
        created_at TEXT DEFAULT (datetime('now')),
        updated_at TEXT DEFAULT (datetime('now'))
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
     "facts_traits": '["host.user"]',
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
    # --- Windows AD techniques (Week 2) ---
    {"mitre_id": "T1069.002", "platform": "windows",
     "command": "Get-ADGroupMember 'Domain Admins' -ErrorAction SilentlyContinue | Select-Object Name,SamAccountName",
     "output_parser": "first_line",
     "facts_traits": '["host.ad_group"]',
     "tags": '["discovery","ad","windows"]'},
    {"mitre_id": "T1558.003", "platform": "windows",
     "command": "Get-ADUser -Filter {ServicePrincipalName -ne \"$null\"} -Properties ServicePrincipalName -ErrorAction SilentlyContinue | Select-Object SamAccountName,ServicePrincipalName",
     "output_parser": "first_line",
     "facts_traits": '["credential.spn"]',
     "tags": '["credential_access","kerberoasting","ad","windows"]'},
    {"mitre_id": "T1003.001", "platform": "windows",
     "command": "[Security.Principal.WindowsIdentity]::GetCurrent().Groups | ForEach-Object { $_.Translate([Security.Principal.NTAccount]).Value } | Select-Object -First 10",
     "output_parser": "first_line",
     "facts_traits": '["host.privilege"]',
     "tags": '["credential_access","privilege_check","windows"]'},
    {"mitre_id": "T1003.003", "platform": "windows",
     "command": "reg query 'HKLM\\SAM' 2>$null; if ($?) { 'SAM_ACCESSIBLE' } else { 'SAM_DENIED' }",
     "output_parser": "first_line",
     "facts_traits": '["credential.sam_status"]',
     "tags": '["credential_access","sam","windows"]'},
    {"mitre_id": "T1018", "platform": "windows",
     "command": "Get-ADComputer -Filter * -Properties Name,OperatingSystem -ErrorAction SilentlyContinue | Select-Object -First 20 Name,OperatingSystem",
     "output_parser": "first_line",
     "facts_traits": '["host.ad_computer"]',
     "tags": '["discovery","ad","windows"]'},
]


# ---------------------------------------------------------------------------
# Seed data for tool_registry — 10 tools/engines
# Uses INSERT OR IGNORE so restarts are safe (no duplicate key errors).
# ---------------------------------------------------------------------------
TOOL_REGISTRY_SEEDS = [
    {
        "tool_id": "nmap",
        "name": "Nmap",
        "kind": "tool",
        "category": "reconnaissance",
        "description": "Network exploration and security auditing",
        "mitre_techniques": '["T1046","T1595.001","T1595.002"]',
        "risk_level": "medium",
        "output_traits": '["network.host.ip","service.port","service.banner","host.os"]',
        "config_json": '{"mcp_server":"nmap-scanner","mcp_tool":"nmap_scan"}',
    },
    {
        "tool_id": "subfinder",
        "name": "Subfinder",
        "kind": "tool",
        "category": "reconnaissance",
        "description": "Fast passive subdomain enumeration tool",
        "mitre_techniques": '["T1595.001","T1596"]',
        "risk_level": "low",
        "output_traits": '["network.host.hostname"]',
        "config_json": '{"mcp_server":"osint-recon","mcp_tool":"subfinder_query"}',
    },
    {
        "tool_id": "crtsh",
        "name": "crt.sh",
        "kind": "tool",
        "category": "reconnaissance",
        "description": "Certificate transparency log search",
        "mitre_techniques": '["T1596"]',
        "risk_level": "low",
        "output_traits": '["osint.subdomain","osint.certificate_san"]',
        "config_json": '{"mcp_server":"osint-recon","mcp_tool":"crtsh_query"}',
    },
    {
        "tool_id": "nvd_lookup",
        "name": "NVD Lookup",
        "kind": "tool",
        "category": "vulnerability_scanning",
        "description": "NIST NVD API for CVE lookup and enrichment",
        "mitre_techniques": '["T1595.002"]',
        "risk_level": "low",
        "output_traits": '["vuln.cve","vulnerability.cve"]',
        "config_json": '{"mcp_server":"vuln-lookup","mcp_tool":"nvd_cve_lookup"}',
    },
    {
        "tool_id": "ssh",
        "name": "Direct SSH",
        "kind": "engine",
        "category": "execution",
        "description": "Execute techniques via direct SSH",
        "mitre_techniques": "[]",
        "risk_level": "medium",
        "output_traits": "[]",
        "config_json": '{"mcp_server":"credential-checker"}',
    },
    {
        "tool_id": "persistent_ssh",
        "name": "Persistent SSH",
        "kind": "engine",
        "category": "execution",
        "description": "Pooled SSH sessions for faster execution",
        "mitre_techniques": "[]",
        "risk_level": "medium",
        "output_traits": "[]",
        "config_json": '{"mcp_server":"attack-executor"}',
    },
    {
        "tool_id": "metasploit",
        "name": "Metasploit",
        "kind": "engine",
        "category": "execution",
        "description": "Metasploit Framework RPC for exploit execution",
        "mitre_techniques": "[]",
        "risk_level": "critical",
        "output_traits": "[]",
        "config_json": '{"mcp_server":"msf-rpc"}',
    },
    {
        "tool_id": "winrm",
        "name": "WinRM",
        "kind": "engine",
        "category": "execution",
        "description": "Windows Remote Management",
        "mitre_techniques": "[]",
        "risk_level": "medium",
        "output_traits": "[]",
        "config_json": '{"mcp_server":"credential-checker"}',
    },
    {
        "tool_id": "mock",
        "name": "Mock Engine",
        "kind": "engine",
        "category": "execution",
        "description": "Mock execution engine for development",
        "mitre_techniques": "[]",
        "risk_level": "low",
        "output_traits": "[]",
    },
    {
        "tool_id": "credential_checker",
        "name": "Credential Checker",
        "kind": "tool",
        "category": "credential_access",
        "description": "SSH credential testing via MCP",
        "mitre_techniques": '["T1110.001","T1021.004"]',
        "risk_level": "high",
        "output_traits": '["credential.ssh"]',
        "config_json": '{"mcp_server":"credential-checker","mcp_tool":"ssh_credential_check"}',
    },
]


async def _seed_tool_registry(db: aiosqlite.Connection) -> None:
    """Insert seed tool registry entries only when the table is empty (idempotent)."""
    async with db.execute("SELECT COUNT(*) FROM tool_registry") as cursor:
        row = await cursor.fetchone()
        count = row[0] if row else 0

    if count > 0:
        return  # Already seeded — skip

    for seed in TOOL_REGISTRY_SEEDS:
        await db.execute(
            """
            INSERT OR IGNORE INTO tool_registry
                (id, tool_id, name, kind, category, description,
                 mitre_techniques, risk_level, output_traits, config_json, source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'seed')
            """,
            (
                str(uuid4()),
                seed["tool_id"],
                seed["name"],
                seed["kind"],
                seed["category"],
                seed["description"],
                seed["mitre_techniques"],
                seed["risk_level"],
                seed["output_traits"],
                seed.get("config_json", "{}"),
            ),
        )


# ---------------------------------------------------------------------------
# Seed data for techniques table — ensures orient engine can resolve tactic/kill-chain
# ---------------------------------------------------------------------------
TECHNIQUE_SEEDS = [
    {"mitre_id": "T1069.002", "name": "Permission Groups Discovery: Domain Groups",
     "tactic": "Discovery", "tactic_id": "TA0007", "risk_level": "low", "platforms": '["windows"]'},
    {"mitre_id": "T1558.003", "name": "Steal or Forge Kerberos Tickets: Kerberoasting",
     "tactic": "Credential Access", "tactic_id": "TA0006", "risk_level": "medium", "platforms": '["windows"]'},
    {"mitre_id": "T1003.003", "name": "OS Credential Dumping: NTDS",
     "tactic": "Credential Access", "tactic_id": "TA0006", "risk_level": "high", "platforms": '["windows"]'},
    {"mitre_id": "T1018", "name": "Remote System Discovery",
     "tactic": "Discovery", "tactic_id": "TA0007", "risk_level": "low", "platforms": '["windows","linux"]'},
]


async def _seed_techniques(db: aiosqlite.Connection) -> None:
    """Insert seed technique definitions (INSERT OR IGNORE — idempotent)."""
    import uuid as _uuid

    # Fix legacy rows that were inserted without an id
    await db.execute(
        "UPDATE techniques SET id = lower(hex(randomblob(4)) || '-' || hex(randomblob(2)) || '-4' || substr(hex(randomblob(2)),2) || '-' || substr('89ab',abs(random())%4+1,1) || substr(hex(randomblob(2)),2) || '-' || hex(randomblob(6))) WHERE id IS NULL"
    )

    for seed in TECHNIQUE_SEEDS:
        await db.execute(
            """
            INSERT OR IGNORE INTO techniques
                (id, mitre_id, name, tactic, tactic_id, risk_level, platforms)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(_uuid.uuid4()),
                seed["mitre_id"],
                seed["name"],
                seed["tactic"],
                seed["tactic_id"],
                seed["risk_level"],
                seed["platforms"],
            ),
        )


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
                (id, mitre_id, platform, command, output_parser, facts_traits, source, tags)
            VALUES (?, ?, ?, ?, ?, ?, 'seed', ?)
            """,
            (
                str(uuid4()),
                seed["mitre_id"],
                seed["platform"],
                seed["command"],
                seed.get("output_parser"),
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
        await _seed_techniques(db)
        await _seed_tool_registry(db)
        # Migration: add max_iterations column if not present
        try:
            await db.execute("ALTER TABLE operations ADD COLUMN max_iterations INTEGER DEFAULT 0")
            await db.commit()
        except Exception:
            pass  # column already exists
        # Migration: rename caldera_ability_id → c2_ability_id
        try:
            await db.execute("ALTER TABLE techniques RENAME COLUMN caldera_ability_id TO c2_ability_id")
            await db.commit()
        except Exception:
            pass
        # Migration: update engine values 'caldera' → 'c2'
        try:
            await db.execute("UPDATE technique_executions SET engine = 'c2' WHERE engine = 'caldera'")
            await db.execute("UPDATE mission_steps SET engine = 'c2' WHERE engine = 'caldera'")
            await db.commit()
        except Exception:
            pass
        # Migration: debrand C2 (Caldera) → C2 Engine (ADR-019)
        try:
            await db.execute(
                "UPDATE tool_registry SET name = 'C2 Engine',"
                " description = 'C2 framework integration for technique execution'"
                " WHERE tool_id = 'c2' AND name = 'C2 (Caldera)'"
            )
            await db.commit()
        except Exception:
            pass
        # Migration: add is_active column to targets
        try:
            await db.execute("ALTER TABLE targets ADD COLUMN is_active INTEGER DEFAULT 0")
            await db.commit()
        except Exception:
            pass
        # Migration: fix poisoned credential.ssh facts from T1078.001 id output
        try:
            await db.execute(
                "UPDATE facts SET trait = 'host.user' "
                "WHERE trait = 'credential.ssh' AND value LIKE 'uid=%'"
            )
            await db.commit()
        except Exception:
            pass
        # Migration: add ip_address column to recon_scans
        try:
            await db.execute("ALTER TABLE recon_scans ADD COLUMN ip_address TEXT")
            await db.commit()
        except Exception:
            pass  # column already exists
        # Migration: deduplicate targets and agents, then add unique indexes
        try:
            # Remove duplicate targets (keep the earliest row per ip+operation)
            await db.execute("""
                DELETE FROM targets WHERE rowid NOT IN (
                    SELECT MIN(rowid) FROM targets GROUP BY ip_address, operation_id
                )
            """)
            await db.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_targets_ip_op "
                "ON targets(ip_address, operation_id)"
            )
            # Remove duplicate agents (keep the earliest row per paw+operation)
            await db.execute("""
                DELETE FROM agents WHERE rowid NOT IN (
                    SELECT MIN(rowid) FROM agents GROUP BY paw, operation_id
                )
            """)
            await db.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_agents_paw_op "
                "ON agents(paw, operation_id)"
            )
            await db.commit()
        except Exception:
            pass  # indexes already exist or table was freshly created with UNIQUE
        # Migration: deprecate C2 (Caldera) tool, set mcp_server on seed tools
        try:
            await db.execute("DELETE FROM tool_registry WHERE tool_id = 'c2'")
            _mcp_mappings = {
                "ssh": "credential-checker",
                "persistent_ssh": "attack-executor",
                "winrm": "credential-checker",
                "metasploit": "msf-rpc",
            }
            for tid, srv in _mcp_mappings.items():
                await db.execute(
                    "UPDATE tool_registry SET config_json = ? "
                    "WHERE tool_id = ? AND (config_json IS NULL OR config_json = '{}')",
                    (f'{{"mcp_server":"{srv}"}}', tid),
                )
            await db.commit()
        except Exception:
            pass
        await db.commit()


async def get_db() -> AsyncGenerator[aiosqlite.Connection, None]:
    """Async generator for FastAPI Depends injection."""
    db_path = Path(_DB_FILE)
    db = await aiosqlite.connect(str(db_path))
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA foreign_keys = ON;")
    try:
        yield db
    finally:
        await db.close()
