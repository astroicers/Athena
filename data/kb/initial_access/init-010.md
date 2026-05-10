---
id: init-010
title: "API Key in Public Repository"
category: initial_access
tags: [api-key-exposure, trufflehog, gitrob, secret-scanning, github-recon]
platform: [linux, windows]
commands:
  - "trufflehog git https://github.com/target-org/repo.git --only-verified"
  - "trufflehog github --org=target-org --only-verified"
  - "gitleaks detect --source /path/to/repo --report-path gitleaks-report.json"
  - "gitrob --github-access-token <token> target-org"
references:
  - "https://github.com/trufflesecurity/trufflehog"
  - "https://attack.mitre.org/techniques/T1552/004/"
---

Exposed API keys, OAuth tokens, database credentials, and private keys inadvertently committed to public (or accessible private) Git repositories grant attackers direct access to cloud infrastructure, internal services, and third-party platforms without any exploitation required. TruffleHog scans repository history (not just the current HEAD) using entropy analysis and regex patterns to identify high-confidence secrets, while GitLeaks provides similar functionality with customizable rule sets for CI/CD pipeline integration. Discovered credentials should be tested against their associated service immediately, as organizations rarely rotate secrets after accidental exposure unless specifically alerted, and valid cloud provider credentials (AWS, GCP, Azure) can provide a direct pivot into production infrastructure.
