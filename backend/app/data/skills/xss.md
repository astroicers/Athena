---
title: Cross-Site Scripting (XSS)
category: web_application
applicable_techniques:
  - T1190
  - T1059.007
mitre_tactics:
  - TA0001
  - TA0002
max_token_estimate: 600
---

## Attack Methodology

1. **Discovery**: Test all input reflection points — URL parameters, form fields, HTTP headers (Referer, User-Agent), JSON/XML bodies.
2. **Classification**: Determine XSS type — Reflected (URL-based), Stored (persistent in DB), DOM-based (client-side JS manipulation).
3. **Exploitation**: Inject JavaScript payloads to steal cookies, session tokens, or perform actions as the victim user.

## Bypass Techniques

- Filter bypass: event handlers (`onerror`, `onload`, `onfocus`), tag alternatives (`<svg>`, `<img>`, `<details>`)
- Encoding bypass: HTML entities (`&#x3C;script&#x3E;`), Unicode escapes, URL encoding
- CSP bypass: JSONP endpoints, `unsafe-inline`, `base-uri` manipulation
- Polyglot payloads: `jaVasCript:/*-/*\`/*\'/*"/**/(/* */oNcliCk=alert() )//`

## Tool Usage Tips

- XSStrike: `xsstrike -u "URL" --crawl`
- Manual: `<script>alert(1)</script>`, `"><img src=x onerror=alert(1)>`
- DOM-based: Check `document.location`, `document.URL`, `document.referrer` sinks
