---
id: priv-009
title: "Windows Service Binary Replacement"
category: privilege_escalation
tags: [windows-privesc, service-binary, icacls, unquoted-service-path, sc]
platform: [windows]
commands:
  - "icacls \"C:\\Program Files\\VulnerableService\\service.exe\""
  - "sc qc VulnerableService"
  - "wmic service get name,displayname,pathname,startmode | findstr /i \"auto\" | findstr /i /v \"c:\\windows\\\\\""
  - "sc stop VulnerableService && sc start VulnerableService"
references:
  - "https://book.hacktricks.xyz/windows-hardening/windows-local-privilege-escalation#services"
  - "https://www.ired.team/offensive-security/privilege-escalation/weak-service-permissions"
---

Windows service binary replacement exploits weak file system permissions that allow a low-privileged user to overwrite or replace the executable that a Windows service runs as, typically a service configured to run as SYSTEM. Attackers use `icacls` to check write permissions on service binaries and `sc qc` or `wmic` to identify services with vulnerable paths, including unquoted service paths where spaces in directory names can be exploited by placing a malicious binary at an earlier path segment. After replacing the binary with a reverse shell or privilege escalation payload and restarting the service (or waiting for the next automatic start), the payload executes with SYSTEM privileges.
