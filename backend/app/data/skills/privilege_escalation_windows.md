---
title: Windows Privilege Escalation
category: post_exploitation
applicable_techniques:
  - T1068
  - T1548.002
mitre_tactics:
  - TA0004
max_token_estimate: 800
---

## Attack Methodology

1. **Enumeration**: `systeminfo`, `whoami /priv`, `net user`, `net localgroup administrators`, `wmic service list brief`
2. **Token Privileges**: SeImpersonatePrivilege → Potato exploits (JuicyPotato, PrintSpoofer, GodPotato).
3. **Service Misconfig**: Unquoted service paths, weak service permissions, writable service binaries.
4. **UAC Bypass**: fodhelper.exe, eventvwr.exe registry hijack, CMSTPLUA COM object.
5. **AlwaysInstallElevated**: Check `reg query HKLM\SOFTWARE\Policies\Microsoft\Windows\Installer /v AlwaysInstallElevated`
6. **Scheduled Tasks**: writable task scripts, DLL hijacking in task binaries.

## Bypass Techniques

- AMSI bypass: `[Ref].Assembly.GetType('System.Management.Automation.AmsiUtils').GetField('amsiInitFailed','NonPublic,Static').SetValue($null,$true)`
- AppLocker bypass: trusted paths (`C:\Windows\Temp`), LOLBAS binaries
- Defender evasion: obfuscation, in-memory execution, reflective DLL loading

## Tool Usage Tips

- WinPEAS: `winpeas.exe`
- PowerUp: `Invoke-AllChecks`
- SharpUp: `SharpUp.exe audit`
