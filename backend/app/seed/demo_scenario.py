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

"""
Seed script for the OP-2024-017 "PHANTOM-EYE" demo scenario.

Populates all 12 tables with reproducible, fixed-ID data.
Idempotent: uses INSERT OR IGNORE so re-running is safe.

Usage (from backend/ directory):
    python -m app.seed.demo_scenario
"""

import asyncio
import json

import aiosqlite

from app.database import _DB_FILE, init_db

# ---------------------------------------------------------------------------
# Fixed IDs for reproducibility
# ---------------------------------------------------------------------------

# User
USR_VIPER = "usr-0001"

# Operation
OP_PHANTOM = "op-0001"

# Targets
TGT_DC01 = "tgt-0001"
TGT_WSPC01 = "tgt-0002"
TGT_WSPC02 = "tgt-0003"
TGT_DB01 = "tgt-0004"
TGT_FS01 = "tgt-0005"

# Agents
AGT_7F3A = "agt-0001"
AGT_2B1C = "agt-0002"
AGT_9E4D = "agt-0003"
AGT_5A7B = "agt-0004"

# Techniques (static catalog)
TECH_T1595 = "tech-0001"
TECH_T1003 = "tech-0002"
TECH_T1021 = "tech-0003"
TECH_T1059 = "tech-0004"
TECH_T1059_004 = "tech-t1059-004"
TECH_T1078_001 = "tech-t1078-001"
TECH_T1021_004 = "tech-t1021-004"
TECH_T1110_001 = "tech-t1110-001"
TECH_T1190 = "tech-t1190"
TECH_T1046 = "tech-t1046"

# Mission Steps
MS_01 = "ms-0001"
MS_02 = "ms-0002"
MS_03 = "ms-0003"
MS_04 = "ms-0004"

# C5ISR Statuses
C5_CMD = "c5-0001"
C5_CTL = "c5-0002"
C5_COM = "c5-0003"
C5_CMP = "c5-0004"
C5_CYB = "c5-0005"
C5_ISR = "c5-0006"

# ---------------------------------------------------------------------------
# Timestamps (explicit ISO format)
# ---------------------------------------------------------------------------
TS_BASE = "2024-11-15T08:00:00"
TS_SCAN_START = "2024-11-15T08:05:00"
TS_SCAN_END = "2024-11-15T08:12:00"
TS_EXEC_START = "2024-11-15T08:30:00"
TS_BEACON = "2024-11-15T09:00:00"
TS_NOW = "2024-11-15T09:15:00"


async def seed() -> None:
    """Insert all demo data into the database (idempotent)."""
    await init_db()

    async with aiosqlite.connect(_DB_FILE) as db:
        await db.execute("PRAGMA foreign_keys = ON;")

        # ==================================================================
        # 1. users (1 record)
        # ==================================================================
        await db.execute(
            "INSERT OR IGNORE INTO users (id, callsign, role, created_at) "
            "VALUES (?, ?, ?, ?)",
            (USR_VIPER, "VIPER-1", "Commander", TS_BASE),
        )

        # ==================================================================
        # 2. operations (1 record)
        # ==================================================================
        await db.execute(
            "INSERT OR IGNORE INTO operations "
            "(id, code, name, codename, strategic_intent, status, "
            "current_ooda_phase, ooda_iteration_count, threat_level, "
            "success_rate, techniques_executed, techniques_total, "
            "active_agents, data_exfiltrated_bytes, automation_mode, "
            "risk_threshold, operator_id, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                OP_PHANTOM,
                "OP-2024-017",
                "Obtain Domain Admin",
                "PHANTOM-EYE",
                "Obtain Domain Admin access via credential harvesting "
                "and lateral movement",
                "planning",
                "observe",
                0,
                0.0,
                0.0,
                0,
                4,
                0,
                0,
                "semi_auto",
                "medium",
                USR_VIPER,
                TS_BASE,
                TS_BASE,
            ),
        )

        # ==================================================================
        # 3. targets (5 records)
        # ==================================================================
        targets = [
            (TGT_DC01, "DC-01", "10.0.1.5", "Windows Server 2019",
             "Domain Controller", "10.0.1.0/24", 0, None,
             OP_PHANTOM, TS_BASE),
            (TGT_WSPC01, "WS-PC01", "10.0.1.20", "Windows 10",
             "Workstation", "10.0.1.0/24", 0, None,
             OP_PHANTOM, TS_BASE),
            (TGT_WSPC02, "WS-PC02", "10.0.1.21", "Windows 10",
             "Workstation", "10.0.1.0/24", 0, None,
             OP_PHANTOM, TS_BASE),
            (TGT_DB01, "DB-01", "10.0.1.30", "Windows Server 2019",
             "Database Server", "10.0.1.0/24", 0, None,
             OP_PHANTOM, TS_BASE),
            (TGT_FS01, "FS-01", "10.0.1.40", "Windows Server 2016",
             "File Server", "10.0.1.0/24", 0, None,
             OP_PHANTOM, TS_BASE),
        ]
        await db.executemany(
            "INSERT OR IGNORE INTO targets "
            "(id, hostname, ip_address, os, role, network_segment, "
            "is_compromised, privilege_level, operation_id, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            targets,
        )

        # ==================================================================
        # 4. agents (4 records)
        # ==================================================================
        agents = [
            (AGT_7F3A, "AGENT-7F3A", TGT_DC01, "pending", "User",
             None, 5, "windows", OP_PHANTOM, TS_BASE),
            (AGT_2B1C, "AGENT-2B1C", TGT_WSPC01, "pending", "User",
             None, 5, "windows", OP_PHANTOM, TS_BASE),
            (AGT_9E4D, "AGENT-9E4D", TGT_WSPC02, "pending", "User",
             None, 5, "windows", OP_PHANTOM, TS_BASE),
            (AGT_5A7B, "AGENT-5A7B", TGT_FS01, "pending", "User",
             None, 5, "windows", OP_PHANTOM, TS_BASE),
        ]
        await db.executemany(
            "INSERT OR IGNORE INTO agents "
            "(id, paw, host_id, status, privilege, last_beacon, "
            "beacon_interval_sec, platform, operation_id, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            agents,
        )

        # ==================================================================
        # 5. techniques (4 records — static catalog, no operation_id)
        # ==================================================================
        techniques = [
            (TECH_T1595, "T1595.001",
             "Active Scanning: IP Blocks",
             "Reconnaissance", "TA0043",
             "Scan IP blocks to gather victim network information.",
             "recon", "low", None,
             json.dumps(["windows"])),
            (TECH_T1003, "T1003.001",
             "OS Credential Dumping: LSASS Memory",
             "Credential Access", "TA0006",
             "Dump credentials from LSASS process memory.",
             "exploit", "medium", None,
             json.dumps(["windows"])),
            (TECH_T1021, "T1021.002",
             "Remote Services: SMB/Windows Admin Shares",
             "Lateral Movement", "TA0008",
             "Use SMB/Windows Admin Shares for lateral movement.",
             "c2", "high", None,
             json.dumps(["windows"])),
            (TECH_T1059, "T1059.001",
             "Command and Scripting Interpreter: PowerShell",
             "Execution", "TA0002",
             "Execute commands via PowerShell.",
             "exploit", "medium", None,
             json.dumps(["windows"])),
            # Linux techniques for Metasploitable
            (TECH_T1059_004, "T1059.004",
             "Command and Scripting Interpreter: Unix Shell",
             "Execution", "TA0002",
             "Execute commands via Unix shell (bash/sh).",
             "exploit", "medium", None,
             json.dumps(["linux"])),
            (TECH_T1078_001, "T1078.001",
             "Valid Accounts: Default Accounts",
             "Initial Access", "TA0001",
             "Use default credentials to gain access to systems.",
             "recon", "low", None,
             json.dumps(["linux", "windows"])),
            (TECH_T1021_004, "T1021.004",
             "Remote Services: SSH",
             "Lateral Movement", "TA0008",
             "Use SSH for remote access and lateral movement.",
             "c2", "medium", None,
             json.dumps(["linux"])),
            (TECH_T1110_001, "T1110.001",
             "Brute Force: Password Guessing",
             "Credential Access", "TA0006",
             "Attempt to guess passwords for user accounts.",
             "exploit", "medium", None,
             json.dumps(["linux", "windows"])),
            (TECH_T1190, "T1190",
             "Exploit Public-Facing Application",
             "Initial Access", "TA0001",
             "Exploit vulnerabilities in public-facing applications.",
             "exploit", "medium", None,
             json.dumps(["linux", "windows"])),
            (TECH_T1046, "T1046",
             "Network Service Discovery",
             "Discovery", "TA0007",
             "Enumerate services running on remote hosts.",
             "recon", "low", None,
             json.dumps(["linux", "windows"])),
            # Recon techniques (Phase 12)
            ("tech-t1592",     "T1592",     "Gather Victim Host Information",
             "Reconnaissance",    "TA0043", None, "recon",   "low",    None,
             '["linux","windows"]'),
            ("tech-t1595-002", "T1595.002", "Active Scanning: Vulnerability Scan",
             "Reconnaissance",    "TA0043", None, "recon",   "low",    None,
             '["linux","windows"]'),
            ("tech-t1110-003", "T1110.003", "Brute Force: Password Spraying",
             "Credential Access", "TA0006", None, "exploit", "medium", None,
             '["linux","windows"]'),
        ]
        await db.executemany(
            "INSERT OR IGNORE INTO techniques "
            "(id, mitre_id, name, tactic, tactic_id, description, "
            "kill_chain_stage, risk_level, caldera_ability_id, platforms) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            techniques,
        )

        # ==================================================================
        # 6. mission_steps (4 records — all queued, awaiting OODA)
        # ==================================================================
        mission_steps = [
            (MS_01, OP_PHANTOM, 1, TECH_T1595,
             "Active Scanning: IP Blocks", TGT_DC01,
             "10.0.1.0/24", "caldera", "queued",
             TS_BASE, None, None),
            (MS_02, OP_PHANTOM, 2, TECH_T1003,
             "OS Credential Dumping: LSASS Memory", TGT_DC01,
             "DC-01", "caldera", "queued",
             TS_BASE, None, None),
            (MS_03, OP_PHANTOM, 3, TECH_T1021,
             "Remote Services: SMB/Windows Admin Shares", TGT_WSPC01,
             "WS-PC01", "caldera", "queued",
             TS_BASE, None, None),
            (MS_04, OP_PHANTOM, 4, TECH_T1059,
             "Command and Scripting Interpreter: PowerShell", TGT_WSPC02,
             "WS-PC02", "caldera", "queued",
             TS_BASE, None, None),
        ]
        await db.executemany(
            "INSERT OR IGNORE INTO mission_steps "
            "(id, operation_id, step_number, technique_id, "
            "technique_name, target_id, target_label, engine, "
            "status, created_at, started_at, completed_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            mission_steps,
        )

        # ==================================================================
        # 11. c5isr_statuses (6 records)
        # ==================================================================
        c5isr = [
            (C5_CMD, OP_PHANTOM, "command", "offline", 0.0,
             "Awaiting operation start", TS_BASE),
            (C5_CTL, OP_PHANTOM, "control", "offline", 0.0,
             "Awaiting operation start", TS_BASE),
            (C5_COM, OP_PHANTOM, "comms", "offline", 0.0,
             "Awaiting operation start", TS_BASE),
            (C5_CMP, OP_PHANTOM, "computers", "offline", 0.0,
             "Awaiting operation start", TS_BASE),
            (C5_CYB, OP_PHANTOM, "cyber", "offline", 0.0,
             "Awaiting operation start", TS_BASE),
            (C5_ISR, OP_PHANTOM, "isr", "offline", 0.0,
             "Awaiting operation start", TS_BASE),
        ]
        await db.executemany(
            "INSERT OR IGNORE INTO c5isr_statuses "
            "(id, operation_id, domain, status, health_pct, detail, "
            "updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            c5isr,
        )

        await db.commit()

    print("Seed data inserted successfully for OP-2024-017 PHANTOM-EYE.")


if __name__ == "__main__":
    asyncio.run(seed())
