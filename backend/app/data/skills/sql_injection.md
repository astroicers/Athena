---
title: SQL Injection
category: web_application
applicable_techniques:
  - T1190
  - T1059.007
mitre_tactics:
  - TA0001
  - TA0002
max_token_estimate: 800
---

## Attack Methodology

1. **Discovery**: Identify injection points via parameter fuzzing — test single quotes, double quotes, semicolons, and comment sequences in all user inputs (GET/POST params, headers, cookies).
2. **Classification**: Determine injection type — UNION-based (visible output), blind boolean-based (true/false responses), blind time-based (response delay), error-based (DB errors in response), or out-of-band (DNS/HTTP exfiltration).
3. **Exploitation**: Extract data using appropriate technique — UNION SELECT for direct extraction, conditional responses for blind, SLEEP/BENCHMARK for time-based.
4. **Post-Exploitation**: Dump database schema (`information_schema`), extract credentials, attempt OS command execution via `xp_cmdshell` (MSSQL) or `LOAD_FILE`/`INTO OUTFILE` (MySQL).

## Bypass Techniques

- WAF bypass: inline comments (`/*!50000 UNION*/`), case alternation (`uNiOn SeLeCt`), URL encoding, double encoding
- Prepared statement detection: use stacked queries where supported (`;DROP TABLE`)
- Character encoding: UTF-8 overlong encoding, hex encoding (`0x41424344`)
- Whitespace alternatives: `/**/`, `%0a`, `%09`, `+` instead of spaces

## Tool Usage Tips

- sqlmap: `sqlmap -u "URL" --batch --level=5 --risk=3 --tamper=space2comment`
- Manual testing: `' OR 1=1--`, `' UNION SELECT NULL,NULL,NULL--`
- Error-based: `' AND extractvalue(1, concat(0x7e, version()))--`
