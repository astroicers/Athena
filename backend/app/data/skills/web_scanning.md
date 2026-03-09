---
title: Web Application Scanning
category: reconnaissance
applicable_techniques:
  - T1595
  - T1595.002
mitre_tactics:
  - TA0043
max_token_estimate: 500
---

## Attack Methodology

1. **Discovery**: Identify web technologies, frameworks, CMS versions via response headers, HTML source, and error pages.
2. **Directory Enumeration**: Brute-force directories and files to find hidden endpoints, admin panels, backup files.
3. **Vulnerability Scanning**: Test for known CVEs, misconfigurations, default credentials.
4. **API Discovery**: Find API endpoints via Swagger/OpenAPI docs, JavaScript source analysis.

## Key Checks

- Server headers: `Server`, `X-Powered-By`, `X-AspNet-Version`
- Default files: `robots.txt`, `sitemap.xml`, `.env`, `web.config`, `.git/config`
- Common admin paths: `/admin`, `/wp-admin`, `/phpmyadmin`, `/manager`

## Tool Usage Tips

- Nikto: `nikto -h target -C all`
- Gobuster: `gobuster dir -u http://target -w /usr/share/wordlists/dirb/common.txt`
- WhatWeb: `whatweb target`
- Nuclei: `nuclei -u target -t cves/`
