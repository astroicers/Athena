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

# Technique Executions
TEXEC_01 = "texec-0001"

# Facts
FACT_01 = "fact-0001"
FACT_02 = "fact-0002"

# OODA Iterations
OODA_01 = "ooda-0001"

# Recommendations
REC_01 = "rec-0001"

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

# Log Entries
LOG_01 = "log-0001"
LOG_02 = "log-0002"
LOG_03 = "log-0003"

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
                "active",
                "decide",
                1,
                7.4,
                73.0,
                47,
                156,
                12,
                2516582,
                "semi_auto",
                "medium",
                USR_VIPER,
                TS_BASE,
                TS_NOW,
            ),
        )

        # ==================================================================
        # 3. targets (5 records)
        # ==================================================================
        targets = [
            (TGT_DC01, "DC-01", "10.0.1.5", "Windows Server 2019",
             "Domain Controller", "10.0.1.0/24", 1, "SYSTEM",
             OP_PHANTOM, TS_BASE),
            (TGT_WSPC01, "WS-PC01", "10.0.1.20", "Windows 10",
             "Workstation", "10.0.1.0/24", 1, "Admin",
             OP_PHANTOM, TS_BASE),
            (TGT_WSPC02, "WS-PC02", "10.0.1.21", "Windows 10",
             "Workstation", "10.0.1.0/24", 0, None,
             OP_PHANTOM, TS_BASE),
            (TGT_DB01, "DB-01", "10.0.1.30", "Windows Server 2019",
             "Database Server", "10.0.1.0/24", 0, None,
             OP_PHANTOM, TS_BASE),
            (TGT_FS01, "FS-01", "10.0.1.40", "Windows Server 2016",
             "File Server", "10.0.1.0/24", 1, "SYSTEM",
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
            (AGT_7F3A, "AGENT-7F3A", TGT_DC01, "alive", "SYSTEM",
             TS_BEACON, 5, "windows", OP_PHANTOM, TS_BASE),
            (AGT_2B1C, "AGENT-2B1C", TGT_WSPC01, "alive", "Admin",
             TS_BEACON, 5, "windows", OP_PHANTOM, TS_BASE),
            (AGT_9E4D, "AGENT-9E4D", TGT_WSPC02, "pending", "User",
             None, 5, "windows", OP_PHANTOM, TS_BASE),
            (AGT_5A7B, "AGENT-5A7B", TGT_FS01, "alive", "SYSTEM",
             TS_BEACON, 5, "windows", OP_PHANTOM, TS_BASE),
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
        ]
        await db.executemany(
            "INSERT OR IGNORE INTO techniques "
            "(id, mitre_id, name, tactic, tactic_id, description, "
            "kill_chain_stage, risk_level, caldera_ability_id, platforms) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            techniques,
        )

        # ==================================================================
        # 6. technique_executions (1 record)
        # ==================================================================
        await db.execute(
            "INSERT OR IGNORE INTO technique_executions "
            "(id, technique_id, target_id, operation_id, "
            "ooda_iteration_id, engine, status, result_summary, "
            "facts_collected_count, started_at, completed_at, "
            "error_message, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                TEXEC_01,
                TECH_T1003,
                TGT_DC01,
                OP_PHANTOM,
                OODA_01,
                "caldera",
                "success",
                "Extracted 10 NTLM hashes from LSASS memory on DC-01",
                2,
                TS_EXEC_START,
                "2024-11-15T08:35:00",
                None,
                TS_EXEC_START,
            ),
        )

        # ==================================================================
        # 7. facts (2 records)
        # ==================================================================
        facts = [
            (FACT_01, "host.user.password_hash",
             "aad3b435b51404eeaad3b435b51404ee:"
             "fc525c9683e8fe067095ba2ddc971889",
             "credential", TECH_T1003, TGT_DC01, OP_PHANTOM,
             1, "2024-11-15T08:35:00"),
            (FACT_02, "host.os.version",
             "Windows Server 2019 Build 17763",
             "host", TECH_T1595, TGT_DC01, OP_PHANTOM,
             1, TS_SCAN_END),
        ]
        await db.executemany(
            "INSERT OR IGNORE INTO facts "
            "(id, trait, value, category, source_technique_id, "
            "source_target_id, operation_id, score, collected_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            facts,
        )

        # ==================================================================
        # 8. ooda_iterations (1 record)
        # ==================================================================
        await db.execute(
            "INSERT OR IGNORE INTO ooda_iterations "
            "(id, operation_id, iteration_number, phase, "
            "observe_summary, orient_summary, decide_summary, "
            "act_summary, recommendation_id, technique_execution_id, "
            "started_at, completed_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                OODA_01,
                OP_PHANTOM,
                1,
                "decide",
                "Network scan completed. 5 hosts discovered in "
                "10.0.1.0/24. DC-01 identified as primary target.",
                "PentestGPT analysis: DC-01 running Windows Server 2019 "
                "with SeDebugPrivilege available. LSASS credential "
                "extraction recommended with 87% confidence.",
                "Commander approved T1003.001 execution on DC-01 via "
                "Caldera engine. Risk level: medium.",
                None,
                REC_01,
                TEXEC_01,
                TS_SCAN_START,
                None,
            ),
        )

        # ==================================================================
        # 9. recommendations (1 record — options as JSON TEXT)
        # ==================================================================
        options = json.dumps([
            {
                "technique_id": TECH_T1003,
                "technique_name": "OS Credential Dumping: LSASS Memory",
                "reasoning": (
                    "Target DC-01 runs Windows Server 2019 with "
                    "SeDebugPrivilege available. LSASS process memory "
                    "contains NTLM hashes for domain accounts. High "
                    "probability of obtaining domain-wide credentials "
                    "for lateral movement."
                ),
                "risk_level": "medium",
                "recommended_engine": "caldera",
                "confidence": 0.87,
                "prerequisites": [
                    "SeDebugPrivilege (available)",
                    "Local Admin (confirmed)",
                ],
            }
        ])

        await db.execute(
            "INSERT OR IGNORE INTO recommendations "
            "(id, operation_id, ooda_iteration_id, "
            "situation_assessment, recommended_technique_id, "
            "confidence, options, reasoning_text, accepted, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                REC_01,
                OP_PHANTOM,
                OODA_01,
                "Current position: Domain Controller DC-01 compromised "
                "with SYSTEM privileges. SeDebugPrivilege confirmed "
                "available. LSASS process accessible for credential "
                "extraction. High probability of obtaining domain-wide "
                "NTLM hashes for lateral movement.",
                TECH_T1003,
                0.87,
                options,
                "Target DC-01 runs Windows Server 2019 with "
                "SeDebugPrivilege available. LSASS process memory "
                "contains NTLM hashes for lateral movement.",
                None,
                TS_EXEC_START,
            ),
        )

        # ==================================================================
        # 10. mission_steps (4 records)
        # ==================================================================
        mission_steps = [
            (MS_01, OP_PHANTOM, 1, TECH_T1595,
             "Active Scanning: IP Blocks", TGT_DC01,
             "10.0.1.0/24", "caldera", "completed",
             TS_BASE, TS_SCAN_START, TS_SCAN_END),
            (MS_02, OP_PHANTOM, 2, TECH_T1003,
             "OS Credential Dumping: LSASS Memory", TGT_DC01,
             "DC-01", "caldera", "running",
             TS_BASE, TS_EXEC_START, None),
            (MS_03, OP_PHANTOM, 3, TECH_T1021,
             "Remote Services: SMB/Windows Admin Shares", TGT_WSPC01,
             "WS-PC01", "caldera", "queued",
             TS_BASE, None, None),
            (MS_04, OP_PHANTOM, 4, TECH_T1059,
             "Command and Scripting Interpreter: PowerShell", TGT_WSPC02,
             "WS-PC02", "shannon", "queued",
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
            (C5_CMD, OP_PHANTOM, "command", "operational", 100.0,
             "Full command authority established", TS_NOW),
            (C5_CTL, OP_PHANTOM, "control", "active", 90.0,
             "Operation control active, monitoring all agents", TS_NOW),
            (C5_COM, OP_PHANTOM, "comms", "degraded", 60.0,
             "Intermittent connectivity to 2 agents", TS_NOW),
            (C5_CMP, OP_PHANTOM, "computers", "nominal", 93.0,
             "4/5 target hosts enumerated", TS_NOW),
            (C5_CYB, OP_PHANTOM, "cyber", "engaged", 73.0,
             "Active credential harvesting in progress", TS_NOW),
            (C5_ISR, OP_PHANTOM, "isr", "scanning", 67.0,
             "Passive reconnaissance ongoing", TS_NOW),
        ]
        await db.executemany(
            "INSERT OR IGNORE INTO c5isr_statuses "
            "(id, operation_id, domain, status, health_pct, detail, "
            "updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            c5isr,
        )

        # ==================================================================
        # 12. log_entries (3 records)
        # ==================================================================
        logs = [
            (LOG_01, TS_SCAN_START, "info", "ooda-observe",
             "[OBSERVE] Scanning target network 10.0.1.0/24",
             OP_PHANTOM, TECH_T1595, None),
            (LOG_02, TS_EXEC_START, "warning", "ooda-orient",
             "[ORIENT] PentestGPT recommends T1003.001 "
             "(confidence: 87%)",
             OP_PHANTOM, TECH_T1003, TGT_DC01),
            (LOG_03, "2024-11-15T08:35:00", "success", "ooda-act",
             "[SUCCESS] Domain Admin acquired — "
             "Mission OP-2024-017 complete",
             OP_PHANTOM, TECH_T1003, TGT_DC01),
        ]
        await db.executemany(
            "INSERT OR IGNORE INTO log_entries "
            "(id, timestamp, severity, source, message, "
            "operation_id, technique_id, target_id) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            logs,
        )

        await db.commit()

    print("Seed data inserted successfully for OP-2024-017 PHANTOM-EYE.")


if __name__ == "__main__":
    asyncio.run(seed())
