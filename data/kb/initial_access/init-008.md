---
id: init-008
title: "VPN and RDP Brute Force"
category: initial_access
tags: [vpn, rdp, brute-force, crowbar, ncrack, credential-attack]
platform: [linux, windows]
commands:
  - "crowbar -b rdp -s <target-ip>/32 -u administrator -C /usr/share/wordlists/rockyou.txt"
  - "ncrack -u administrator -P passwords.txt rdp://<target-ip>"
  - "crowbar -b openvpn -s <target-ip>/32 -u vpn_user -C common-vpn-passwords.txt -k client.ovpn"
  - "hydra -L users.txt -P passwords.txt rdp://<target-ip> -t 1 -w 30"
references:
  - "https://github.com/galkan/crowbar"
  - "https://attack.mitre.org/techniques/T1110/001/"
---

VPN and RDP endpoints are high-value brute-force targets because successful authentication provides direct network access to internal infrastructure, bypassing perimeter defenses. Crowbar is specifically designed for protocols that are poorly handled by generic tools like Hydra, including OpenVPN (using client certificates with credential authentication), RDP, SSH with key authentication, and OpenVPN, while `ncrack` provides multi-protocol support with controllable connection rates. Attackers typically prioritize credential lists from prior data breaches using services like `dehashed`, combine them with company-specific password patterns, and target VPN portals identified through Shodan searches for products like Pulse Secure, Fortinet, Citrix, and GlobalProtect that have had authentication bypass vulnerabilities.
