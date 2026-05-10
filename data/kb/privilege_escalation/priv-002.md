---
id: priv-002
title: "Sudo Misconfiguration"
category: privilege_escalation
tags: [sudo, misconfiguration, linux-privesc, nopasswd]
platform: [linux]
commands:
  - "sudo -l"
  - "sudo -u root /bin/bash"
  - "sudo vim -c ':!/bin/bash'"
  - "sudo awk 'BEGIN {system(\"/bin/bash\")}'"
references:
  - "https://gtfobins.github.io/gtfobins/vim/#sudo"
  - "https://book.hacktricks.xyz/linux-hardening/privilege-escalation#sudo-and-suid"
---

Sudo misconfigurations allow low-privileged users to execute commands as root without a password, most commonly when `/etc/sudoers` contains `ALL=(ALL) NOPASSWD: ALL` or grants sudo rights to applications that support shell escapes. Running `sudo -l` reveals which commands the current user can execute with elevated privileges, and GTFOBins documents shell escape sequences for editors, interpreters, and utilities that can be abused when run under sudo. Even restricted sudo rules (e.g., `sudo /usr/bin/vim`) can be bypassed if the allowed binary supports spawning subshells or executing arbitrary commands.
