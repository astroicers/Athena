---
id: priv-006
title: "Kernel Exploit"
category: privilege_escalation
tags: [kernel-exploit, dirtycow, linux-privesc, cve, local-exploit]
platform: [linux]
commands:
  - "uname -a && cat /etc/os-release"
  - "python3 linux-exploit-suggester.py --uname \"$(uname -a)\""
  - "gcc -pthread dirty.c -o dirty -lcrypt && ./dirty password123"
  - "searchsploit linux kernel $(uname -r | cut -d. -f1-2)"
references:
  - "https://github.com/mzet-/linux-exploit-suggester"
  - "https://dirtycow.ninja/"
---

Kernel exploits target vulnerabilities in the Linux kernel itself to achieve privilege escalation from any user to root, bypassing all userland security controls. The first step is fingerprinting the exact kernel version with `uname -a` and then running tools like Linux Exploit Suggester to match against known CVEs such as DirtyCow (CVE-2016-5195), Dirty Pipe (CVE-2022-0847), or various privilege escalation vulnerabilities in the eBPF subsystem. Exploit code is typically compiled on the target (or a matching system) and executed locally; since kernel exploits can crash the system, they should be used as a last resort after other escalation paths have been exhausted.
