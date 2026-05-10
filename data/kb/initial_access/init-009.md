---
id: init-009
title: "Subdomain Takeover"
category: initial_access
tags: [subdomain-takeover, dns, cname, amass, subjack, recon]
platform: [linux, windows]
commands:
  - "amass enum -d target.example.com -o subdomains.txt"
  - "subjack -w subdomains.txt -t 100 -timeout 30 -ssl -c /opt/subjack/fingerprints.json -v"
  - "nuclei -t dns/subdomain-takeover.yaml -l subdomains.txt"
  - "dig CNAME vulnerable.target.example.com"
references:
  - "https://github.com/EdOverflow/can-i-take-over-xyz"
  - "https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/02-Configuration_and_Deployment_Management_Testing/10-Test_for_Subdomain_Takeover"
---

Subdomain takeover occurs when a DNS CNAME record points to a third-party service (GitHub Pages, Heroku, AWS S3, Azure, Netlify, etc.) that has been deprovisioned or deleted, allowing an attacker to register the same resource and serve malicious content under the victim's legitimate domain. The attack begins with broad subdomain enumeration using tools like `amass` or `subfinder`, followed by identifying dangling CNAME records using `subjack` or `nuclei` templates that check for service-specific indicators of unclaimed resources. A successful takeover enables cookie theft (if the subdomain shares the parent domain's cookies), phishing using a trusted domain, bypassing Content Security Policy, and serving malware from a legitimate-looking URL.
