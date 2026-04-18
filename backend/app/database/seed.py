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

# ===========================================================================
# Technique playbook seeds — organised by ATT&CK tactic
# ===========================================================================

# --- TA0043: Reconnaissance ---------------------------------------------------
_RECON_SEEDS = [
    # --- Linux ---
    {"mitre_id": "T1592", "platform": "linux",
     "command": "uname -a && id && cat /etc/os-release",
     "facts_traits": '["host.os", "host.user"]',
     "tags": '["reconnaissance"]'},
    {"mitre_id": "T1595.001", "platform": "linux",
     "command": "nmap -sV -Pn --top-ports 25 {target_ip} 2>/dev/null || echo 'NMAP_UNAVAILABLE'",
     "facts_traits": '["network.host.ip"]',
     "tags": '["reconnaissance"]'},
    {"mitre_id": "T1595.002", "platform": "linux",
     "command": "nmap --script vuln -Pn {target_ip} 2>/dev/null || echo 'NMAP_UNAVAILABLE'",
     "facts_traits": '["vuln.cve"]',
     "tags": '["reconnaissance"]'},
    {"mitre_id": "T1592.004", "platform": "linux",
     "command": "curl -sI http://{target_ip}/ 2>/dev/null | head -10 || echo 'HTTP_UNAVAILABLE'",
     "facts_traits": '["service.web"]',
     "tags": '["reconnaissance","http"]'},
    {"mitre_id": "T1596", "platform": "linux",
     "command": "dig ANY {target_ip} 2>/dev/null || nslookup {target_ip} 2>/dev/null || echo 'DNS_UNAVAILABLE'",
     "facts_traits": '["network.dns.record"]',
     "tags": '["reconnaissance","dns"]'},
    # --- Windows ---
    {"mitre_id": "T1592", "platform": "windows",
     "command": "systeminfo | Select-String 'OS Name','OS Version','System Type'",
     "output_parser": "first_line",
     "facts_traits": '["host.os"]',
     "tags": '["reconnaissance","windows"]'},
    {"mitre_id": "T1595.001", "platform": "windows",
     "command": "Test-NetConnection -ComputerName {target_ip} -Port 445 -ErrorAction SilentlyContinue | Select-Object ComputerName,RemotePort,TcpTestSucceeded",
     "output_parser": "first_line",
     "facts_traits": '["network.host.ip","service.port"]',
     "tags": '["reconnaissance","windows"]'},
    {"mitre_id": "T1596", "platform": "windows",
     "command": "Resolve-DnsName {target_ip} -ErrorAction SilentlyContinue | Select-Object Name,Type,IPAddress",
     "output_parser": "first_line",
     "facts_traits": '["network.dns.record"]',
     "tags": '["reconnaissance","dns","windows"]'},
]

# --- TA0001: Initial Access ---------------------------------------------------
_INITIAL_ACCESS_SEEDS = [
    # --- Linux ---
    {"mitre_id": "T1190", "platform": "linux",
     "command": "curl -sI http://localhost/ 2>/dev/null | head -5",
     "facts_traits": '["service.web"]',
     "tags": '["initial_access"]'},
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
    {"mitre_id": "T1133", "platform": "linux",
     "command": "ss -tlnp 2>/dev/null | grep -E ':(22|3389|5900|5985)' || echo 'NO_REMOTE_SERVICES'",
     "facts_traits": '["service.port"]',
     "tags": '["initial_access","remote_service"]'},
    # --- Windows ---
    {"mitre_id": "T1078.001", "platform": "windows",
     "command": "Get-LocalUser | Where-Object { $_.Enabled -eq $true } | Select-Object Name,LastLogon",
     "output_parser": "first_line",
     "facts_traits": '["host.user"]',
     "tags": '["initial_access","windows"]'},
    {"mitre_id": "T1133", "platform": "windows",
     "command": "Get-ItemProperty 'HKLM:\\SYSTEM\\CurrentControlSet\\Control\\Terminal Server' -Name fDenyTSConnections -ErrorAction SilentlyContinue | Select-Object fDenyTSConnections",
     "output_parser": "first_line",
     "facts_traits": '["service.rdp"]',
     "tags": '["initial_access","rdp","windows"]'},
    {"mitre_id": "T1190", "platform": "windows",
     "command": "Get-WebSite -ErrorAction SilentlyContinue | Select-Object Name,State,PhysicalPath | Format-Table -AutoSize",
     "output_parser": "first_line",
     "facts_traits": '["service.web"]',
     "tags": '["initial_access","iis","windows"]'},
]

# --- TA0002: Execution --------------------------------------------------------
_EXECUTION_SEEDS = [
    # --- Linux ---
    {"mitre_id": "T1059.004", "platform": "linux",
     "command": "bash -c 'id && whoami && hostname'",
     "facts_traits": '["host.process"]',
     "tags": '["execution"]'},
    {"mitre_id": "T1059.006", "platform": "linux",
     "command": "python3 -c 'import os,platform; print(os.getlogin(), platform.node())' 2>/dev/null || echo 'PYTHON_UNAVAILABLE'",
     "facts_traits": '["host.user","host.os"]',
     "tags": '["execution","python"]'},
    {"mitre_id": "T1059.003", "platform": "linux",
     "command": "sh -c 'id && uname -a' 2>/dev/null",
     "facts_traits": '["host.process"]',
     "tags": '["execution","posix_shell"]'},
    {"mitre_id": "T1053.003_exec", "platform": "linux",
     "command": "crontab -l 2>/dev/null || echo 'NO_CRONTAB'",
     "output_parser": "first_line",
     "facts_traits": '["host.persistence"]',
     "tags": '["execution","cron"]'},
    {"mitre_id": "T1059.009", "platform": "linux",
     "command": "which cloud-init aws gcloud az 2>/dev/null | head -5 || echo 'NO_CLOUD_CLI'",
     "output_parser": "first_line",
     "facts_traits": '["host.binary"]',
     "tags": '["execution","cloud"]'},
    # --- Windows ---
    {"mitre_id": "T1059.001", "platform": "windows",
     "command": "whoami; $env:COMPUTERNAME; Get-Process | Select-Object -First 5 Name,Id",
     "output_parser": "first_line",
     "facts_traits": '["host.os"]',
     "tags": '["execution","powershell","windows"]'},
    {"mitre_id": "T1059.003", "platform": "windows",
     "command": "cmd /c 'whoami && hostname && ver'",
     "output_parser": "first_line",
     "facts_traits": '["host.os"]',
     "tags": '["execution","cmd","windows"]'},
    {"mitre_id": "T1047", "platform": "windows",
     "command": "Get-WmiObject Win32_OperatingSystem -ErrorAction SilentlyContinue | Select-Object Caption,Version,OSArchitecture",
     "output_parser": "first_line",
     "facts_traits": '["host.os"]',
     "tags": '["execution","wmi","windows"]'},
    {"mitre_id": "T1059.006", "platform": "windows",
     "command": "python -c \"import os,platform; print(os.getlogin(), platform.node())\" 2>$null; if (-not $?) { 'PYTHON_UNAVAILABLE' }",
     "output_parser": "first_line",
     "facts_traits": '["host.user"]',
     "tags": '["execution","python","windows"]'},
    {"mitre_id": "T1569.002", "platform": "windows",
     "command": "Get-Service | Where-Object { $_.Status -eq 'Running' } | Select-Object -First 10 Name,DisplayName",
     "output_parser": "first_line",
     "facts_traits": '["host.service"]',
     "tags": '["execution","service","windows"]'},
]

# --- TA0003: Persistence ------------------------------------------------------
_PERSISTENCE_SEEDS = [
    # --- Linux ---
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
    {"mitre_id": "T1547.006", "platform": "linux",
     "command": "cat /etc/modules 2>/dev/null; lsmod | head -10",
     "output_parser": "first_line",
     "facts_traits": '["host.persistence"]',
     "tags": '["persistence","kernel_module","linux"]'},
    {"mitre_id": "T1546.004", "platform": "linux",
     "command": "cat ~/.bashrc ~/.bash_profile ~/.profile 2>/dev/null | grep -E 'alias|export|eval' | head -10",
     "output_parser": "first_line",
     "facts_traits": '["host.persistence"]',
     "tags": '["persistence","shell_profile","linux"]'},
    {"mitre_id": "T1037.004", "platform": "linux",
     "command": "cat /etc/rc.local 2>/dev/null || ls /etc/init.d/ 2>/dev/null | head -10",
     "output_parser": "first_line",
     "facts_traits": '["host.persistence"]',
     "tags": '["persistence","rc_scripts","linux"]'},
    # --- Windows ---
    {"mitre_id": "T1053.005", "platform": "windows",
     "command": "schtasks /query /fo CSV /nh 2>$null | Select-Object -First 10",
     "output_parser": "first_line",
     "facts_traits": '["host.persistence"]',
     "tags": '["persistence","scheduled_task","windows"]'},
    {"mitre_id": "T1547.001", "platform": "windows",
     "command": "Get-ItemProperty 'HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run' -ErrorAction SilentlyContinue",
     "output_parser": "first_line",
     "facts_traits": '["host.persistence"]',
     "tags": '["persistence","registry_run","windows"]'},
    {"mitre_id": "T1543.003", "platform": "windows",
     "command": "Get-WmiObject Win32_Service | Where-Object { $_.StartMode -eq 'Auto' -and $_.State -eq 'Running' } | Select-Object -First 10 Name,PathName",
     "output_parser": "first_line",
     "facts_traits": '["host.service"]',
     "tags": '["persistence","windows_service","windows"]'},
    {"mitre_id": "T1136.001", "platform": "windows",
     "command": "Get-LocalUser | Select-Object Name,Enabled,LastLogon,PasswordLastSet",
     "output_parser": "first_line",
     "facts_traits": '["host.user"]',
     "tags": '["persistence","account_creation","windows"]'},
    {"mitre_id": "T1546.003", "platform": "windows",
     "command": "Get-WmiObject -Class __EventFilter -Namespace root\\subscription -ErrorAction SilentlyContinue | Select-Object Name,Query",
     "output_parser": "first_line",
     "facts_traits": '["host.persistence"]',
     "tags": '["persistence","wmi_event","windows"]'},
    {"mitre_id": "T1547.009", "platform": "windows",
     "command": "reg query 'HKLM\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\Winlogon' /v Userinit 2>$null",
     "output_parser": "first_line",
     "facts_traits": '["host.persistence"]',
     "tags": '["persistence","winlogon","windows"]'},
]

# --- TA0004: Privilege Escalation ---------------------------------------------
_PRIVESC_SEEDS = [
    # --- Linux ---
    {"mitre_id": "T1548.001", "platform": "linux",
     "command": "find / -perm -4000 -type f 2>/dev/null | head -20",
     "facts_traits": '["host.file","host.privilege"]',
     "tags": '["privilege_escalation","suid"]'},
    {"mitre_id": "T1548.003", "platform": "linux",
     "command": "cat /etc/sudoers 2>/dev/null; sudo -l 2>/dev/null || echo 'SUDO_DENIED'",
     "facts_traits": '["host.privilege"]',
     "tags": '["privilege_escalation","sudo"]'},
    {"mitre_id": "T1068", "platform": "linux",
     "command": "uname -r && cat /proc/version",
     "output_parser": "first_line",
     "facts_traits": '["host.os"]',
     "tags": '["privilege_escalation","kernel"]'},
    {"mitre_id": "T1574.006", "platform": "linux",
     "command": "echo $LD_PRELOAD; cat /etc/ld.so.preload 2>/dev/null; ldconfig -p 2>/dev/null | head -10",
     "facts_traits": '["host.privilege"]',
     "tags": '["privilege_escalation","ld_preload"]'},
    {"mitre_id": "T1055", "platform": "linux",
     "command": "cat /proc/sys/kernel/yama/ptrace_scope 2>/dev/null; ls -la /proc/self/maps 2>/dev/null | head -5",
     "output_parser": "first_line",
     "facts_traits": '["host.privilege"]',
     "tags": '["privilege_escalation","process_injection"]'},
    {"mitre_id": "T1021.004_priv", "platform": "linux",
     "command": "sudo -l 2>/dev/null && sudo -n id 2>/dev/null",
     "output_parser": "first_line",
     "facts_traits": '["host.privilege"]',
     "tags": '["lateral_move","privilege_escalation","ssh"]'},
    {"mitre_id": "T1548.004", "platform": "linux",
     "command": "getcap -r / 2>/dev/null | head -20",
     "facts_traits": '["host.privilege","host.file"]',
     "tags": '["privilege_escalation","capabilities"]'},
    {"mitre_id": "T1134.002", "platform": "linux",
     "command": "cat /proc/self/status | grep -E 'Uid|Gid|Cap' 2>/dev/null",
     "output_parser": "first_line",
     "facts_traits": '["host.privilege"]',
     "tags": '["privilege_escalation","token"]'},
    # --- Windows ---
    {"mitre_id": "T1548.002", "platform": "windows",
     "command": "Get-ItemProperty 'HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System' -ErrorAction SilentlyContinue | Select-Object EnableLUA,ConsentPromptBehaviorAdmin",
     "output_parser": "first_line",
     "facts_traits": '["host.privilege"]',
     "tags": '["privilege_escalation","uac","windows"]'},
    {"mitre_id": "T1134.001", "platform": "windows",
     "command": "whoami /priv",
     "output_parser": "first_line",
     "facts_traits": '["host.privilege"]',
     "tags": '["privilege_escalation","token","windows"]'},
    {"mitre_id": "T1574.001", "platform": "windows",
     "command": "$env:PATH -split ';' | ForEach-Object { if (Test-Path $_) { Get-Acl $_ -ErrorAction SilentlyContinue | Select-Object Path,Owner } } | Select-Object -First 10",
     "output_parser": "first_line",
     "facts_traits": '["host.privilege"]',
     "tags": '["privilege_escalation","dll_hijack","windows"]'},
    {"mitre_id": "T1055", "platform": "windows",
     "command": "Get-Process | Where-Object { $_.SessionId -eq (Get-Process -Id $PID).SessionId } | Select-Object -First 15 Id,ProcessName,Path",
     "output_parser": "first_line",
     "facts_traits": '["host.process"]',
     "tags": '["privilege_escalation","process_injection","windows"]'},
    {"mitre_id": "T1068", "platform": "windows",
     "command": "[System.Environment]::OSVersion | Select-Object VersionString; (Get-WmiObject Win32_OperatingSystem).Version",
     "output_parser": "first_line",
     "facts_traits": '["host.os"]',
     "tags": '["privilege_escalation","kernel","windows"]'},
    {"mitre_id": "T1134.002", "platform": "windows",
     "command": "whoami /groups | Select-String 'S-1-5'",
     "output_parser": "first_line",
     "facts_traits": '["host.privilege"]',
     "tags": '["privilege_escalation","token","windows"]'},
    {"mitre_id": "T1574.002", "platform": "windows",
     "command": "Get-ChildItem 'C:\\Program Files','C:\\Program Files (x86)' -ErrorAction SilentlyContinue | Where-Object { $_.Name -match ' ' } | Select-Object -First 10 FullName",
     "output_parser": "first_line",
     "facts_traits": '["host.file","host.privilege"]',
     "tags": '["privilege_escalation","unquoted_service_path","windows"]'},
    {"mitre_id": "T1543.003_priv", "platform": "windows",
     "command": "Get-WmiObject Win32_Service | Where-Object { $_.PathName -notmatch 'svchost' -and $_.StartMode -eq 'Auto' } | Select-Object -First 10 Name,PathName,StartName",
     "output_parser": "first_line",
     "facts_traits": '["host.service","host.privilege"]',
     "tags": '["privilege_escalation","service_misconfig","windows"]'},
]

# --- TA0005: Defense Evasion --------------------------------------------------
_DEFENSE_EVASION_SEEDS = [
    # --- Linux ---
    {"mitre_id": "T1070.003", "platform": "linux",
     "command": "wc -l ~/.bash_history 2>/dev/null; ls -la ~/.bash_history 2>/dev/null || echo 'NO_HISTORY'",
     "output_parser": "first_line",
     "facts_traits": '["host.file"]',
     "tags": '["defense_evasion","history"]'},
    {"mitre_id": "T1070.001", "platform": "linux",
     "command": "ls -la /var/log/ 2>/dev/null | head -10; wc -l /var/log/auth.log 2>/dev/null",
     "facts_traits": '["host.file"]',
     "tags": '["defense_evasion","log_check"]'},
    {"mitre_id": "T1562.001", "platform": "linux",
     "command": "systemctl status apparmor 2>/dev/null; sestatus 2>/dev/null; systemctl status auditd 2>/dev/null || echo 'NO_SECURITY_TOOLS'",
     "facts_traits": '["host.service"]',
     "tags": '["defense_evasion","security_tools"]'},
    {"mitre_id": "T1036.005", "platform": "linux",
     "command": "ps aux | awk '{print $11}' | sort | uniq -c | sort -rn | head -15",
     "output_parser": "first_line",
     "facts_traits": '["host.process"]',
     "tags": '["defense_evasion","masquerading"]'},
    # --- Windows ---
    {"mitre_id": "T1562.001", "platform": "windows",
     "command": "Get-MpComputerStatus -ErrorAction SilentlyContinue | Select-Object AntivirusEnabled,RealTimeProtectionEnabled,AntivirusSignatureLastUpdated",
     "output_parser": "first_line",
     "facts_traits": '["host.service"]',
     "tags": '["defense_evasion","av_status","windows"]'},
    {"mitre_id": "T1070.001", "platform": "windows",
     "command": "Get-EventLog -List -ErrorAction SilentlyContinue | Select-Object Log,MaximumKilobytes,Entries",
     "output_parser": "first_line",
     "facts_traits": '["host.file"]',
     "tags": '["defense_evasion","event_log","windows"]'},
    {"mitre_id": "T1562.004", "platform": "windows",
     "command": "Get-NetFirewallProfile -ErrorAction SilentlyContinue | Select-Object Name,Enabled",
     "output_parser": "first_line",
     "facts_traits": '["host.service"]',
     "tags": '["defense_evasion","firewall","windows"]'},
    {"mitre_id": "T1070.006", "platform": "windows",
     "command": "Get-ChildItem C:\\Windows\\Temp -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 10 Name,LastWriteTime,Length",
     "output_parser": "first_line",
     "facts_traits": '["host.file"]',
     "tags": '["defense_evasion","timestomp","windows"]'},
    {"mitre_id": "T1036.005", "platform": "windows",
     "command": "Get-Process | Where-Object { $_.Path -and $_.Path -notmatch 'Windows|Program Files' } | Select-Object -First 10 Name,Path",
     "output_parser": "first_line",
     "facts_traits": '["host.process"]',
     "tags": '["defense_evasion","masquerading","windows"]'},
]

# --- TA0006: Credential Access ------------------------------------------------
_CREDENTIAL_ACCESS_SEEDS = [
    # --- Linux ---
    {"mitre_id": "T1003.001", "platform": "linux",
     "command": "cat /etc/shadow 2>/dev/null || echo 'NO_SHADOW_ACCESS'",
     "facts_traits": '["credential.hash"]',
     "tags": '["credential_access"]'},
    {"mitre_id": "T1552.001", "platform": "linux",
     "command": "grep -rli 'password\\|passwd\\|secret\\|api_key' /etc/ /opt/ /var/www/ 2>/dev/null | head -15",
     "facts_traits": '["credential.file","host.file"]',
     "tags": '["credential_access","creds_in_files"]'},
    {"mitre_id": "T1552.004", "platform": "linux",
     "command": "find / -name 'id_rsa' -o -name 'id_ed25519' -o -name '*.pem' -o -name '*.key' 2>/dev/null | head -15",
     "facts_traits": '["credential.certificate"]',
     "tags": '["credential_access","private_keys"]'},
    {"mitre_id": "T1555.003", "platform": "linux",
     "command": "find /home /root -path '*/.mozilla/firefox/*/logins.json' -o -path '*/.config/google-chrome/*/Login Data' 2>/dev/null | head -10",
     "facts_traits": '["credential.file"]',
     "tags": '["credential_access","browser_creds"]'},
    {"mitre_id": "T1003.008", "platform": "linux",
     "command": "cat /etc/passwd | cut -d: -f1,3,7 && cat /etc/shadow 2>/dev/null | cut -d: -f1,2 | head -10",
     "facts_traits": '["credential.hash","host.user"]',
     "tags": '["credential_access","passwd_shadow"]'},
    {"mitre_id": "T1552.003", "platform": "linux",
     "command": "history 2>/dev/null | grep -iE 'pass|secret|key|token' | tail -10 || echo 'NO_HISTORY_CREDS'",
     "output_parser": "first_line",
     "facts_traits": '["credential.file"]',
     "tags": '["credential_access","bash_history"]'},
    # --- Windows ---
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
    {"mitre_id": "T1558.003", "platform": "windows",
     "command": 'Get-ADUser -Filter {ServicePrincipalName -ne "$null"} -Properties ServicePrincipalName -ErrorAction SilentlyContinue | Select-Object SamAccountName,ServicePrincipalName',
     "output_parser": "first_line",
     "facts_traits": '["credential.spn"]',
     "tags": '["credential_access","kerberoasting","ad","windows"]'},
    {"mitre_id": "T1552.001", "platform": "windows",
     "command": "Get-ChildItem C:\\Users -Recurse -Include *.xml,*.txt,*.ini,*.config -ErrorAction SilentlyContinue | Select-String -Pattern 'password|credential|secret' -List | Select-Object -First 10 Path",
     "output_parser": "first_line",
     "facts_traits": '["credential.file"]',
     "tags": '["credential_access","creds_in_files","windows"]'},
    {"mitre_id": "T1552.002", "platform": "windows",
     "command": "reg query 'HKLM\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\Winlogon' /v DefaultPassword 2>$null; reg query 'HKLM\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\Winlogon' /v AutoAdminLogon 2>$null",
     "output_parser": "first_line",
     "facts_traits": '["credential.password"]',
     "tags": '["credential_access","registry_creds","windows"]'},
    {"mitre_id": "T1555.003", "platform": "windows",
     "command": "Get-ChildItem \"$env:LOCALAPPDATA\\Google\\Chrome\\User Data\\Default\\Login Data\" -ErrorAction SilentlyContinue; Get-ChildItem \"$env:APPDATA\\Mozilla\\Firefox\\Profiles\\*\\logins.json\" -ErrorAction SilentlyContinue",
     "output_parser": "first_line",
     "facts_traits": '["credential.file"]',
     "tags": '["credential_access","browser_creds","windows"]'},
    {"mitre_id": "T1003.004", "platform": "windows",
     "command": "reg query 'HKLM\\SECURITY' 2>$null; if ($?) { 'LSA_SECRETS_ACCESSIBLE' } else { 'LSA_SECRETS_DENIED' }",
     "output_parser": "first_line",
     "facts_traits": '["credential.hash"]',
     "tags": '["credential_access","lsa_secrets","windows"]'},
    {"mitre_id": "T1552.006", "platform": "windows",
     "command": "cmdkey /list 2>$null",
     "output_parser": "first_line",
     "facts_traits": '["credential.password"]',
     "tags": '["credential_access","stored_creds","windows"]'},
]

# --- TA0007: Discovery --------------------------------------------------------
_DISCOVERY_SEEDS = [
    # --- Linux ---
    {"mitre_id": "T1046", "platform": "linux",
     "command": "netstat -tulnp 2>/dev/null || ss -tulnp 2>/dev/null",
     "facts_traits": '["service.open_port"]',
     "tags": '["discovery"]'},
    {"mitre_id": "T1087", "platform": "linux",
     "command": "cat /etc/passwd | cut -d: -f1,3,7",
     "facts_traits": '["host.user"]',
     "tags": '["discovery"]'},
    {"mitre_id": "T1083", "platform": "linux",
     "command": "find / -name '*.conf' -readable 2>/dev/null | head -20",
     "facts_traits": '["host.file"]',
     "tags": '["discovery"]'},
    {"mitre_id": "T1033", "platform": "linux",
     "command": "whoami && id && w 2>/dev/null",
     "output_parser": "first_line",
     "facts_traits": '["host.user"]',
     "tags": '["discovery","system_owner"]'},
    {"mitre_id": "T1057", "platform": "linux",
     "command": "ps auxf 2>/dev/null | head -30 || ps aux | head -30",
     "facts_traits": '["host.process"]',
     "tags": '["discovery","process"]'},
    {"mitre_id": "T1082", "platform": "linux",
     "command": "cat /proc/cpuinfo 2>/dev/null | head -5; free -h 2>/dev/null; df -h 2>/dev/null | head -10",
     "facts_traits": '["host.os"]',
     "tags": '["discovery","system_info"]'},
    {"mitre_id": "T1016", "platform": "linux",
     "command": "ip addr show 2>/dev/null; ip route 2>/dev/null; cat /etc/resolv.conf 2>/dev/null",
     "facts_traits": '["host.network","network.subnet"]',
     "tags": '["discovery","network_config"]'},
    {"mitre_id": "T1049", "platform": "linux",
     "command": "ss -tunap 2>/dev/null | head -20 || netstat -tunap 2>/dev/null | head -20",
     "facts_traits": '["service.port","network.host.ip"]',
     "tags": '["discovery","network_connections"]'},
    {"mitre_id": "T1007", "platform": "linux",
     "command": "systemctl list-units --type=service --state=running 2>/dev/null | head -20 || service --status-all 2>/dev/null | head -20",
     "facts_traits": '["host.service"]',
     "tags": '["discovery","service"]'},
    {"mitre_id": "T1518", "platform": "linux",
     "command": "dpkg -l 2>/dev/null | head -20 || rpm -qa 2>/dev/null | head -20",
     "facts_traits": '["host.software"]',
     "tags": '["discovery","software"]'},
    # --- Windows ---
    {"mitre_id": "T1069.002", "platform": "windows",
     "command": "Get-ADGroupMember 'Domain Admins' -ErrorAction SilentlyContinue | Select-Object Name,SamAccountName",
     "output_parser": "first_line",
     "facts_traits": '["host.ad_group"]',
     "tags": '["discovery","ad","windows"]'},
    {"mitre_id": "T1018", "platform": "windows",
     "command": "Get-ADComputer -Filter * -Properties Name,OperatingSystem -ErrorAction SilentlyContinue | Select-Object -First 20 Name,OperatingSystem",
     "output_parser": "first_line",
     "facts_traits": '["host.ad_computer"]',
     "tags": '["discovery","ad","windows"]'},
    {"mitre_id": "T1033", "platform": "windows",
     "command": "whoami /all | Select-Object -First 20",
     "output_parser": "first_line",
     "facts_traits": '["host.user"]',
     "tags": '["discovery","system_owner","windows"]'},
    {"mitre_id": "T1057", "platform": "windows",
     "command": "Get-Process | Select-Object -First 20 Id,ProcessName,Path",
     "output_parser": "first_line",
     "facts_traits": '["host.process"]',
     "tags": '["discovery","process","windows"]'},
    {"mitre_id": "T1082", "platform": "windows",
     "command": "Get-ComputerInfo -ErrorAction SilentlyContinue | Select-Object CsName,WindowsVersion,OsArchitecture,CsTotalPhysicalMemory",
     "output_parser": "first_line",
     "facts_traits": '["host.os"]',
     "tags": '["discovery","system_info","windows"]'},
    {"mitre_id": "T1016", "platform": "windows",
     "command": "Get-NetIPAddress -ErrorAction SilentlyContinue | Select-Object IPAddress,InterfaceAlias,PrefixLength",
     "output_parser": "first_line",
     "facts_traits": '["host.network"]',
     "tags": '["discovery","network_config","windows"]'},
    {"mitre_id": "T1049", "platform": "windows",
     "command": "Get-NetTCPConnection -State Established -ErrorAction SilentlyContinue | Select-Object -First 15 LocalAddress,LocalPort,RemoteAddress,RemotePort,OwningProcess",
     "output_parser": "first_line",
     "facts_traits": '["service.port","network.host.ip"]',
     "tags": '["discovery","network_connections","windows"]'},
    {"mitre_id": "T1135", "platform": "windows",
     "command": "Get-SmbShare -ErrorAction SilentlyContinue | Select-Object Name,Path,Description",
     "output_parser": "first_line",
     "facts_traits": '["host.file"]',
     "tags": '["discovery","network_share","windows"]'},
    {"mitre_id": "T1087.001", "platform": "windows",
     "command": "Get-LocalUser | Select-Object Name,Enabled,LastLogon",
     "output_parser": "first_line",
     "facts_traits": '["host.user"]',
     "tags": '["discovery","local_account","windows"]'},
    {"mitre_id": "T1518", "platform": "windows",
     "command": "Get-WmiObject Win32_Product -ErrorAction SilentlyContinue | Select-Object -First 15 Name,Version",
     "output_parser": "first_line",
     "facts_traits": '["host.software"]',
     "tags": '["discovery","software","windows"]'},
]

# --- TA0008: Lateral Movement -------------------------------------------------
_LATERAL_MOVEMENT_SEEDS = [
    # --- Linux ---
    {"mitre_id": "T1021.004", "platform": "linux",
     "command": "ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 {target_ip} id 2>/dev/null || echo 'SSH_LATERAL_UNAVAILABLE'",
     "facts_traits": '["host.session"]',
     "tags": '["lateral_movement"]'},
    {"mitre_id": "T1021.004_recon", "platform": "linux",
     "command": "id && hostname && ip addr show && cat /etc/hosts",
     "output_parser": "first_line",
     "facts_traits": '["host.os","host.network"]',
     "tags": '["lateral_move","discovery","ssh"]'},
    {"mitre_id": "T1570", "platform": "linux",
     "command": "which scp rsync nc 2>/dev/null; ls -la /tmp/ 2>/dev/null | head -5",
     "output_parser": "first_line",
     "facts_traits": '["host.binary"]',
     "tags": '["lateral_movement","file_transfer"]'},
    {"mitre_id": "T1563.001", "platform": "linux",
     "command": "who 2>/dev/null; screen -ls 2>/dev/null; tmux ls 2>/dev/null || echo 'NO_SESSIONS'",
     "output_parser": "first_line",
     "facts_traits": '["host.session"]',
     "tags": '["lateral_movement","session_hijack"]'},
    # --- Windows ---
    {"mitre_id": "T1021.001", "platform": "windows",
     "command": "whoami; hostname; ipconfig /all | Select-String 'IPv4'",
     "output_parser": "first_line",
     "facts_traits": '["host.os","host.network"]',
     "tags": '["lateral_move","winrm","windows"]'},
    {"mitre_id": "T1021.002", "platform": "windows",
     "command": "Get-SmbMapping -ErrorAction SilentlyContinue; net use 2>$null",
     "output_parser": "first_line",
     "facts_traits": '["host.session"]',
     "tags": '["lateral_movement","smb","windows"]'},
    {"mitre_id": "T1021.003", "platform": "windows",
     "command": "Get-WmiObject Win32_Process -ErrorAction SilentlyContinue | Where-Object { $_.Name -eq 'mstsc.exe' } | Select-Object Name,ProcessId",
     "output_parser": "first_line",
     "facts_traits": '["host.session"]',
     "tags": '["lateral_movement","dcom","windows"]'},
    {"mitre_id": "T1570", "platform": "windows",
     "command": "Get-SmbShare -ErrorAction SilentlyContinue | Where-Object { $_.Name -notmatch '\\$' } | Select-Object Name,Path",
     "output_parser": "first_line",
     "facts_traits": '["host.file"]',
     "tags": '["lateral_movement","file_transfer","windows"]'},
]

# --- TA0009: Collection -------------------------------------------------------
_COLLECTION_SEEDS = [
    # --- Linux ---
    {"mitre_id": "T1560.001", "platform": "linux",
     "command": "tar czf /tmp/.bundle.tgz /etc/passwd /etc/shadow 2>/dev/null && echo BUNDLED",
     "output_parser": "first_line",
     "facts_traits": '["host.file"]',
     "tags": '["collection","staging","linux"]'},
    {"mitre_id": "T1005", "platform": "linux",
     "command": "find /home /root /var/www /opt -name '*.sql' -o -name '*.db' -o -name '*.sqlite' -o -name '*.bak' 2>/dev/null | head -15",
     "facts_traits": '["host.file"]',
     "tags": '["collection","local_data"]'},
    {"mitre_id": "T1119", "platform": "linux",
     "command": "find /home /tmp -newer /etc/hostname -name '*.txt' -o -name '*.csv' -o -name '*.json' 2>/dev/null | head -10",
     "output_parser": "first_line",
     "facts_traits": '["host.file"]',
     "tags": '["collection","automated"]'},
    # --- Windows ---
    {"mitre_id": "T1560.001", "platform": "windows",
     "command": "Compress-Archive -Path $env:USERPROFILE\\Documents -DestinationPath $env:TEMP\\docs.zip -Force -ErrorAction SilentlyContinue; if (Test-Path $env:TEMP\\docs.zip) { 'ARCHIVED' } else { 'ARCHIVE_FAILED' }",
     "output_parser": "first_line",
     "facts_traits": '["host.file"]',
     "tags": '["collection","staging","windows"]'},
    {"mitre_id": "T1005", "platform": "windows",
     "command": "Get-ChildItem C:\\Users -Recurse -Include *.docx,*.xlsx,*.pdf,*.sql,*.bak -ErrorAction SilentlyContinue | Select-Object -First 15 FullName,Length,LastWriteTime",
     "output_parser": "first_line",
     "facts_traits": '["host.file"]',
     "tags": '["collection","local_data","windows"]'},
    {"mitre_id": "T1119", "platform": "windows",
     "command": "Get-ChildItem $env:USERPROFILE -Recurse -Include *.txt,*.csv,*.json -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 10 FullName,Length",
     "output_parser": "first_line",
     "facts_traits": '["host.file"]',
     "tags": '["collection","automated","windows"]'},
]

# --- TA0011: Command and Control ----------------------------------------------
_C2_SEEDS = [
    # --- Linux ---
    {"mitre_id": "T1105", "platform": "linux",
     "command": "which curl wget python3 nc 2>/dev/null | head -5",
     "output_parser": "first_line",
     "facts_traits": '["host.binary"]',
     "tags": '["transfer","c2","linux"]'},
    {"mitre_id": "T1071.001", "platform": "linux",
     "command": "curl -sI https://ifconfig.me 2>/dev/null | head -5; wget -qO- https://ifconfig.me 2>/dev/null || echo 'NO_HTTP_EGRESS'",
     "output_parser": "first_line",
     "facts_traits": '["network.host.ip"]',
     "tags": '["c2","http_egress"]'},
    {"mitre_id": "T1572", "platform": "linux",
     "command": "which ssh socat chisel 2>/dev/null; ss -tlnp 2>/dev/null | grep -E ':(1080|8080|3128)' || echo 'NO_PROXY_TUNNEL'",
     "output_parser": "first_line",
     "facts_traits": '["host.binary","service.port"]',
     "tags": '["c2","tunnel"]'},
    # --- Windows ---
    {"mitre_id": "T1105", "platform": "windows",
     "command": "Get-Command curl,wget,Invoke-WebRequest,certutil -ErrorAction SilentlyContinue | Select-Object Name,Source",
     "output_parser": "first_line",
     "facts_traits": '["host.binary"]',
     "tags": '["c2","transfer","windows"]'},
    {"mitre_id": "T1071.001", "platform": "windows",
     "command": "Invoke-WebRequest -Uri 'https://ifconfig.me' -UseBasicParsing -TimeoutSec 5 -ErrorAction SilentlyContinue | Select-Object StatusCode,Content",
     "output_parser": "first_line",
     "facts_traits": '["network.host.ip"]',
     "tags": '["c2","http_egress","windows"]'},
    {"mitre_id": "T1572", "platform": "windows",
     "command": "netsh interface portproxy show all 2>$null; Get-ItemProperty 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Internet Settings' -ErrorAction SilentlyContinue | Select-Object ProxyServer,ProxyEnable",
     "output_parser": "first_line",
     "facts_traits": '["host.network"]',
     "tags": '["c2","tunnel","proxy","windows"]'},
]

# --- TA0010: Exfiltration -----------------------------------------------------
_EXFILTRATION_SEEDS = [
    # --- Linux ---
    {"mitre_id": "T1041", "platform": "linux",
     "command": "which curl wget nc socat 2>/dev/null; iptables -L OUTPUT 2>/dev/null | head -5 || echo 'IPTABLES_DENIED'",
     "output_parser": "first_line",
     "facts_traits": '["host.binary"]',
     "tags": '["exfiltration","c2_channel"]'},
    {"mitre_id": "T1048.003", "platform": "linux",
     "command": "cat /etc/resolv.conf 2>/dev/null; dig TXT test.example.com 2>/dev/null | head -3 || echo 'DNS_EXFIL_CHECK'",
     "output_parser": "first_line",
     "facts_traits": '["network.dns.record"]',
     "tags": '["exfiltration","dns"]'},
    # --- Windows ---
    {"mitre_id": "T1041", "platform": "windows",
     "command": "Get-NetFirewallRule -Direction Outbound -Enabled True -ErrorAction SilentlyContinue | Select-Object -First 10 DisplayName,Action",
     "output_parser": "first_line",
     "facts_traits": '["host.service"]',
     "tags": '["exfiltration","c2_channel","windows"]'},
    {"mitre_id": "T1048.003", "platform": "windows",
     "command": "Resolve-DnsName -Type TXT test.example.com -ErrorAction SilentlyContinue; Get-DnsClientServerAddress -ErrorAction SilentlyContinue | Select-Object InterfaceAlias,ServerAddresses",
     "output_parser": "first_line",
     "facts_traits": '["network.dns.record"]',
     "tags": '["exfiltration","dns","windows"]'},
]

# --- TA0040: Impact -----------------------------------------------------------
_IMPACT_SEEDS = [
    # --- Linux ---
    {"mitre_id": "T1489", "platform": "linux",
     "command": "systemctl list-units --type=service --state=running 2>/dev/null | grep -E 'mysql|postgres|nginx|apache|docker' | head -10 || echo 'NO_CRITICAL_SERVICES'",
     "output_parser": "first_line",
     "facts_traits": '["host.service"]',
     "tags": '["impact","service_stop"]'},
    # --- Windows ---
    {"mitre_id": "T1489", "platform": "windows",
     "command": "Get-Service | Where-Object { $_.Status -eq 'Running' -and $_.DisplayName -match 'SQL|IIS|Exchange|DNS|DHCP' } | Select-Object Name,DisplayName,Status",
     "output_parser": "first_line",
     "facts_traits": '["host.service"]',
     "tags": '["impact","service_stop","windows"]'},
    {"mitre_id": "T1531", "platform": "windows",
     "command": "Get-LocalUser | Select-Object Name,Enabled,PasswordExpires,LastLogon",
     "output_parser": "first_line",
     "facts_traits": '["host.user"]',
     "tags": '["impact","account_manipulation","windows"]'},
]

# ---------------------------------------------------------------------------
# Combined playbook seeds list
# ---------------------------------------------------------------------------
TECHNIQUE_PLAYBOOK_SEEDS = (
    _RECON_SEEDS
    + _INITIAL_ACCESS_SEEDS
    + _EXECUTION_SEEDS
    + _PERSISTENCE_SEEDS
    + _PRIVESC_SEEDS
    + _DEFENSE_EVASION_SEEDS
    + _CREDENTIAL_ACCESS_SEEDS
    + _DISCOVERY_SEEDS
    + _LATERAL_MOVEMENT_SEEDS
    + _COLLECTION_SEEDS
    + _C2_SEEDS
    + _EXFILTRATION_SEEDS
    + _IMPACT_SEEDS
)

# ---------------------------------------------------------------------------
# Tool registry seeds (13 entries)
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
    {"tool_id": "privesc_scanner", "name": "Privilege Escalation Scanner", "kind": "tool",
     "category": "execution",
     "description": "Linux/Windows privilege escalation vector detection",
     "mitre_techniques": '["T1548.001","T1548.002","T1548.003","T1574.006","T1068"]',
     "risk_level": "high",
     "output_traits": '["privesc.suid_binary","privesc.sudo_rule","privesc.kernel_vuln","privesc.token_privilege","privesc.uac_level","privesc.writable_path"]',
     "config_json": '{"mcp_server":"privesc-scanner","mcp_tool":"linux_privesc_scan"}'},
    {"tool_id": "credential_dumper", "name": "Credential Dumper", "kind": "tool",
     "category": "credential_access",
     "description": "Impacket-based SAM/NTDS/DCSync/Kerberoasting credential extraction",
     "mitre_techniques": '["T1003.001","T1003.002","T1003.003","T1003.006","T1558.003"]',
     "risk_level": "critical",
     "output_traits": '["credential.hash","credential.domain_user","credential.kerberos_hash","credential.spn_account","credential.cached","credential.dpapi_key"]',
     "config_json": '{"mcp_server":"credential-dumper","mcp_tool":"dump_sam_hashes"}'},
    {"tool_id": "lateral_mover", "name": "Lateral Movement Suite", "kind": "tool",
     "category": "credential_access",
     "description": "PsExec/WMIExec/SMB lateral movement with Pass-the-Hash support",
     "mitre_techniques": '["T1021.002","T1021.003","T1047","T1550.002","T1570"]',
     "risk_level": "critical",
     "output_traits": '["lateral.session","lateral.smb_share","lateral.readable_share","credential.shell"]',
     "config_json": '{"mcp_server":"lateral-mover","mcp_tool":"psexec_lateral"}'},
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
