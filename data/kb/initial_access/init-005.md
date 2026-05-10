---
id: init-005
title: "Exploiting Exposed Services"
category: initial_access
tags: [nmap, nse, metasploit, service-exploitation, vulnerability-scanning]
platform: [linux, windows]
commands:
  - "nmap -sV --script vuln -p- <target-ip>"
  - "nmap -sV --script=exploit <target-ip> -p 21,22,23,80,443,445,3389"
  - "msfconsole -q -x 'use auxiliary/scanner/smb/smb_ms17_010; set RHOSTS <target-subnet>/24; run'"
  - "searchsploit <service-name> <version>"
references:
  - "https://nmap.org/nsedoc/categories/exploit.html"
  - "https://book.hacktricks.xyz/generic-methodologies-and-resources/external-recon-methodology"
---

Exploiting exposed network services involves identifying publicly accessible services (FTP, SSH, Telnet, SMB, HTTP, databases, industrial control protocols) with known vulnerabilities by combining version detection with vulnerability databases such as CVE, ExploitDB, and Metasploit's module library. Nmap NSE scripts in the `vuln` and `exploit` categories can automatically detect and sometimes exploit vulnerabilities during scanning, while Metasploit provides battle-tested exploit modules for common service vulnerabilities. The methodology begins with broad port scanning, narrows down to version fingerprinting, and cross-references findings with `searchsploit` to identify applicable exploits before attempting controlled exploitation.
