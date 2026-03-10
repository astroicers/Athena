# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.

"""Seed data for PostgreSQL — converted from old SQLite database.py.

All INSERT OR IGNORE → INSERT ... ON CONFLICT DO NOTHING
All ? → $1, $2, ...
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING
from uuid import uuid4

if TYPE_CHECKING:
    from app.database.manager import DatabaseManager

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Technique playbook seeds (28 entries)
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
    {"mitre_id": "T1069.002", "platform": "windows",
     "command": "Get-ADGroupMember 'Domain Admins' -ErrorAction SilentlyContinue | Select-Object Name,SamAccountName",
     "output_parser": "first_line",
     "facts_traits": '["host.ad_group"]',
     "tags": '["discovery","ad","windows"]'},
    {"mitre_id": "T1558.003", "platform": "windows",
     "command": 'Get-ADUser -Filter {ServicePrincipalName -ne "$null"} -Properties ServicePrincipalName -ErrorAction SilentlyContinue | Select-Object SamAccountName,ServicePrincipalName',
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
# Tool registry seeds (10 entries)
# ---------------------------------------------------------------------------
TOOL_REGISTRY_SEEDS = [
    {"tool_id": "nmap", "name": "Nmap", "kind": "tool", "category": "reconnaissance",
     "description": "Network exploration and security auditing",
     "mitre_techniques": '["T1046","T1595.001","T1595.002"]', "risk_level": "medium",
     "output_traits": '["network.host.ip","service.port","service.banner","host.os"]',
     "config_json": '{"mcp_server":"nmap-scanner","mcp_tool":"nmap_scan"}'},
    {"tool_id": "subfinder", "name": "Subfinder", "kind": "tool", "category": "reconnaissance",
     "description": "Fast passive subdomain enumeration tool",
     "mitre_techniques": '["T1595.001","T1596"]', "risk_level": "low",
     "output_traits": '["network.host.hostname"]',
     "config_json": '{"mcp_server":"osint-recon","mcp_tool":"subfinder_query"}'},
    {"tool_id": "crtsh", "name": "crt.sh", "kind": "tool", "category": "reconnaissance",
     "description": "Certificate transparency log search",
     "mitre_techniques": '["T1596"]', "risk_level": "low",
     "output_traits": '["osint.subdomain","osint.certificate_san"]',
     "config_json": '{"mcp_server":"osint-recon","mcp_tool":"crtsh_query"}'},
    {"tool_id": "nvd_lookup", "name": "NVD Lookup", "kind": "tool", "category": "vulnerability_scanning",
     "description": "NIST NVD API for CVE lookup and enrichment",
     "mitre_techniques": '["T1595.002"]', "risk_level": "low",
     "output_traits": '["vuln.cve","vulnerability.cve"]',
     "config_json": '{"mcp_server":"vuln-lookup","mcp_tool":"nvd_cve_lookup"}'},
    {"tool_id": "ssh", "name": "Direct SSH", "kind": "engine", "category": "execution",
     "description": "Execute techniques via direct SSH",
     "mitre_techniques": '["T1021.004"]', "risk_level": "medium",
     "output_traits": "[]",
     "config_json": '{"mcp_server":"credential-checker"}'},
    {"tool_id": "persistent_ssh", "name": "Persistent SSH", "kind": "engine", "category": "execution",
     "description": "Pooled SSH sessions for faster execution",
     "mitre_techniques": '["T1021.004","T1059.004"]', "risk_level": "medium",
     "output_traits": "[]",
     "config_json": '{"mcp_server":"attack-executor"}'},
    {"tool_id": "metasploit", "name": "Metasploit", "kind": "engine", "category": "execution",
     "description": "Metasploit Framework RPC for exploit execution",
     "mitre_techniques": '["T1203","T1059","T1210"]', "risk_level": "critical",
     "output_traits": "[]",
     "config_json": '{"mcp_server":"msf-rpc"}'},
    {"tool_id": "winrm", "name": "WinRM", "kind": "engine", "category": "execution",
     "description": "Windows Remote Management",
     "mitre_techniques": '["T1021.006"]', "risk_level": "medium",
     "output_traits": "[]",
     "config_json": '{"mcp_server":"credential-checker"}'},
    {"tool_id": "mock", "name": "Mock Engine", "kind": "engine", "category": "execution",
     "description": "Mock execution engine for development",
     "mitre_techniques": "[]", "risk_level": "low",
     "output_traits": "[]"},
    {"tool_id": "credential_checker", "name": "Credential Checker", "kind": "tool", "category": "credential_access",
     "description": "SSH credential testing via MCP",
     "mitre_techniques": '["T1110.001","T1021.004"]', "risk_level": "high",
     "output_traits": '["credential.ssh"]',
     "config_json": '{"mcp_server":"credential-checker","mcp_tool":"ssh_credential_check"}'},
]

# ---------------------------------------------------------------------------
# Technique seeds (4 entries)
# ---------------------------------------------------------------------------
TECHNIQUE_SEEDS = [
    {"mitre_id": "T1069.002", "name": "Permission Groups Discovery: Domain Groups",
     "tactic": "Discovery", "tactic_id": "TA0007", "risk_level": "low", "platforms": '["windows"]',
     "noise_level": "low"},
    {"mitre_id": "T1558.003", "name": "Steal or Forge Kerberos Tickets: Kerberoasting",
     "tactic": "Credential Access", "tactic_id": "TA0006", "risk_level": "medium", "platforms": '["windows"]',
     "noise_level": "medium"},
    {"mitre_id": "T1003.003", "name": "OS Credential Dumping: NTDS",
     "tactic": "Credential Access", "tactic_id": "TA0006", "risk_level": "high", "platforms": '["windows"]',
     "noise_level": "medium"},
    {"mitre_id": "T1018", "name": "Remote System Discovery",
     "tactic": "Discovery", "tactic_id": "TA0007", "risk_level": "low", "platforms": '["windows","linux"]',
     "noise_level": "low"},
]

# ---------------------------------------------------------------------------
# MCP-discovered tool MITRE mappings
# ---------------------------------------------------------------------------
MCP_DISCOVERED_MITRE: dict[str, dict[str, str]] = {
    "osint-recon_dns_resolve":                    {"category": "reconnaissance",        "mitre": '["T1018","T1596.001"]'},
    "vuln-lookup_banner_to_cpe":                  {"category": "vulnerability_scanning", "mitre": '["T1592.002"]'},
    "credential-checker_rdp_credential_check":    {"category": "credential_access",     "mitre": '["T1110.001","T1021.001"]'},
    "credential-checker_winrm_credential_check":  {"category": "credential_access",     "mitre": '["T1110.001","T1021.006"]'},
    "attack-executor_execute_technique":          {"category": "execution",             "mitre": '["T1059.004"]'},
    "attack-executor_close_sessions":             {"category": "execution",             "mitre": '["T1059.004"]'},
    "web-scanner_web_http_probe":                 {"category": "reconnaissance",        "mitre": '["T1595.002"]'},
    "web-scanner_web_vuln_scan":                  {"category": "vulnerability_scanning", "mitre": '["T1595.002","T1190"]'},
    "web-scanner_web_dir_enum":                   {"category": "reconnaissance",        "mitre": '["T1595.003"]'},
    "web-scanner_web_screenshot":                 {"category": "reconnaissance",        "mitre": '["T1592.004"]'},
    "api-fuzzer_api_schema_detect":               {"category": "reconnaissance",        "mitre": '["T1595.002"]'},
    "api-fuzzer_api_endpoint_enum":               {"category": "reconnaissance",        "mitre": '["T1595.002"]'},
    "api-fuzzer_api_auth_test":                   {"category": "credential_access",     "mitre": '["T1110","T1550"]'},
    "api-fuzzer_api_param_fuzz":                  {"category": "vulnerability_scanning", "mitre": '["T1190"]'},
}


async def seed_if_empty(db_manager: DatabaseManager) -> None:
    """Seed technique playbooks, techniques, and tool registry if tables are empty."""
    async with db_manager.connection() as conn:
        # Seed technique_playbooks
        count = await conn.fetchval("SELECT COUNT(*) FROM technique_playbooks")
        if count == 0:
            for seed in TECHNIQUE_PLAYBOOK_SEEDS:
                await conn.execute(
                    """INSERT INTO technique_playbooks
                       (id, mitre_id, platform, command, output_parser, facts_traits, source, tags)
                       VALUES ($1, $2, $3, $4, $5, $6, 'seed', $7)
                       ON CONFLICT DO NOTHING""",
                    str(uuid4()), seed["mitre_id"], seed["platform"],
                    seed["command"], seed.get("output_parser"),
                    seed["facts_traits"], seed["tags"],
                )
            logger.info("Seeded %d technique playbooks", len(TECHNIQUE_PLAYBOOK_SEEDS))

        # Seed techniques
        for seed in TECHNIQUE_SEEDS:
            await conn.execute(
                """INSERT INTO techniques
                   (id, mitre_id, name, tactic, tactic_id, risk_level, platforms, noise_level)
                   VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                   ON CONFLICT (mitre_id) DO NOTHING""",
                str(uuid4()), seed["mitre_id"], seed["name"],
                seed["tactic"], seed["tactic_id"], seed["risk_level"], seed["platforms"],
                seed.get("noise_level", "medium"),
            )

        # Seed tool_registry
        count = await conn.fetchval("SELECT COUNT(*) FROM tool_registry")
        if count == 0:
            for seed in TOOL_REGISTRY_SEEDS:
                await conn.execute(
                    """INSERT INTO tool_registry
                       (id, tool_id, name, kind, category, description,
                        mitre_techniques, risk_level, output_traits, config_json, source)
                       VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, 'seed')
                       ON CONFLICT (tool_id) DO NOTHING""",
                    str(uuid4()), seed["tool_id"], seed["name"],
                    seed["kind"], seed["category"], seed["description"],
                    seed["mitre_techniques"], seed["risk_level"],
                    seed["output_traits"], seed.get("config_json", "{}"),
                )
            logger.info("Seeded %d tool registry entries", len(TOOL_REGISTRY_SEEDS))

        # Backfill MITRE techniques for tools
        for seed in TOOL_REGISTRY_SEEDS:
            mitre = seed["mitre_techniques"]
            if mitre and mitre != "[]":
                await conn.execute(
                    """UPDATE tool_registry
                       SET mitre_techniques = $1, updated_at = NOW()
                       WHERE tool_id = $2 AND (mitre_techniques IS NULL OR mitre_techniques = '[]')""",
                    mitre, seed["tool_id"],
                )
        for tool_id, meta in MCP_DISCOVERED_MITRE.items():
            await conn.execute(
                """UPDATE tool_registry
                   SET mitre_techniques = $1, category = $2, updated_at = NOW()
                   WHERE tool_id = $3 AND (mitre_techniques IS NULL OR mitre_techniques = '[]')""",
                meta["mitre"], meta["category"], tool_id,
            )
