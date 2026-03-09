---
title: Network Reconnaissance
category: reconnaissance
applicable_techniques:
  - T1595
  - T1595.001
  - T1046
mitre_tactics:
  - TA0043
max_token_estimate: 500
---

## Attack Methodology

1. **Host Discovery**: Identify live hosts on the network via ICMP, ARP, TCP SYN scanning.
2. **Port Scanning**: Enumerate open ports and running services on discovered hosts.
3. **Service Enumeration**: Determine service versions, OS fingerprinting, banner grabbing.
4. **Vulnerability Mapping**: Map discovered services to known vulnerabilities (CVE lookup).

## Scanning Strategies

- Stealth scan: TCP SYN (`-sS`), slow timing (`-T2`), randomize hosts
- Comprehensive: All ports (`-p-`), version detection (`-sV`), OS detection (`-O`), scripts (`-sC`)
- UDP: `nmap -sU --top-ports 100` — DNS(53), SNMP(161), TFTP(69), NTP(123)

## Tool Usage Tips

- Nmap: `nmap -sV -sC -O -p- target -oA output`
- Masscan: `masscan -p1-65535 target --rate 1000`
- Enum4linux: `enum4linux -a target` (SMB enumeration)
- SNMP: `snmpwalk -c public -v2c target`
