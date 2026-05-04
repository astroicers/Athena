# Content Audit — Slides 29-61

Audit of `03-operation.md` (slides 29-54) and `04-lessons-closing.md` (slides 55-61) against ground truth in `/tmp/harry-pptx/ppt/slides/slideN.xml`.

## Summary

- Total slides: 33
- BLOCKER issues: 2
- NICE-TO-FIX issues: 14

The conversion is, on the whole, faithful to the XML source for the high-stakes facts: every MITRE T-code, every hostname, every IP, every password, every command syntax, every Traditional-Chinese tagline that the XML carried through to the md verbatim or near-verbatim. The two BLOCKERs both concern fabricated content presented as demo evidence (a fake service-account password, and a hostname inconsistency with the chapter cover); the rest are dropped flavor text or minor casing/timing drift.

## Per-slide findings (only slides with issues)

### Slide 29 — Chapter cover · 真槍實彈

- [BLOCKER] [WRONG] XML says `WEB01 → DC-01 → ACCT-DB。` (no `01` suffix). md says `WEB01 → DC-01 → ACCT-DB01`. Every other slide in the deck (31, 50, 52, 53) uses `ACCT-DB01`, so the XML is the outlier — but the md silently rewrote what the cover slide actually shows. Either fix the cover slide back to `ACCT-DB` to match Harry's PPT, or annotate the change. As-is, md misrepresents what the cover says.

### Slide 31 — Mission targets

- [NICE-TO-FIX] [MISSING] XML labels WEB01 with sub-text `192.168.0.20 / IIS + ASP.NET / 入口` (three lines including `入口` flavor word). md drops `入口`. No factual loss but a flavor word disappeared.

### Slide 32 — 踩過的坑 (hidden in original PPT)

- [OK] Note in md correctly flags `hidden in original PPTX`. Race-condition SQL `SELECT pg_advisory_xact_lock(hash('access.local_admin'))` matches XML verbatim. T-codes T1003.001, T1003.003 match.

### Slide 35 — Stage 0 kickoff

- [OK] `MODE AUTO_FULL`, `INTERVAL 30 sec / loop`, `RISK medium`, `NOISE BUDGET 100`, `STATE → OBSERVE` all in XML and reproduced. Bottom bar `20:54:06 行動啟動 · OODA loop 開始` matches.
- [NICE-TO-FIX] [MISSING] XML's placeholder annotation `顯示行動剛啟動的狀態` and `AUTO_FULL · interval=30s` (under the war-room screenshot placeholder) is not surfaced as such in md (md replaces the placeholder with synthesized OPS LOG). This is in line with the OPS-LOG-synthesis instruction; flagging only because the agent stripped the original annotation entirely.

### Slide 36 — Stage 0 WEB01 · OBSERVE

- [NICE-TO-FIX] [HALLUCINATED] md adds two specific commands not in XML: `nmap -Pn -p- 192.168.0.20` (XML only says `nmap-scanner` tool name and the resulting open ports `80 / 5985 / 445`, never the `-Pn -p-` flags) and `curl http://192.168.0.20/ → debug.aspx 路徑可達` (no curl in XML). Both are plausible inferences but they are demo-style commands that didn't come from Harry's slide. Suggest converting to less prescriptive phrasing or marking as "we ran a port scan + path probe".
- [OK] Port mapping `80 IIS 8.5 / 5985 WinRM / 445 SMB` matches XML.

### Slide 39 — Stage 0 WEB01 · DONE

- [OK] Bottom bar `21:01:33 WEB01 Compromised · Δ +7m27s` faithfully transferred.
- [NICE-TO-FIX] [HALLUCINATED] OPS LOG adds intermediate timestamps (20:54:35, 20:54:42, 20:55:03, 20:58:14) not in XML — synthesized per task instructions, fine. md also adds `vector=T1190` to the alert-box facts line; XML alert-box doesn't have that text. Acceptable elaboration.

### Slide 40 — Stage 1 DC-01 · OBSERVE

- [NICE-TO-FIX] [HALLUCINATED] md adds two specific commands: `nmap -Pn -p 88,389,445 192.168.0.16` and `bloodhound-collector -d corp.athena.lab`. XML only lists `bloodhound-collector` as tool name (in OPS LOG) and `收集 AD 屬性` annotation, no nmap port list, no `-d corp.athena.lab` flag. Plausible but not from XML.
- [OK] Detection of `legacy_kev: DoesNotRequirePreAuth = True` matches XML.

### Slide 42 — Stage 1 AS-REP Hash 取得

- [OK] Command `impacket-GetNPUsers corp.athena.lab/ -no-pass -usersfile users.txt` matches XML verbatim.
- [OK] AS_REP output `$krb5asrep$23$legacy_kev@CORP.ATHENA.LAB:3a7f8c2d4e1b5a9f6c3d8e2b7a1f4c9d... (558 chars)` matches.
- [NICE-TO-FIX] [HALLUCINATED] alert-box `etype=23 (rc4-hmac) · hashcat -m 18200 直接吃` — XML for slide 42 does not contain this annotation (it appears on slide 43); md duplicates it onto slide 42's alert-box. Not factually wrong, just placement drift.

### Slide 44 — hashcat 破解

- [OK] Command `hashcat -m 18200 asrep.hash rockyou.txt`, status output, and recovered password `M0nk3y!B@n4n4#99` all match XML.
- [NICE-TO-FIX] [MISSING] XML's online-attack panel shows only `+ 鎖定政策` and `5 次失敗 → 帳號鎖定`. md reorders the bullets and adds `速度受限於網路 + 鎖定政策` as one combined line — semantic match but rewording.

### Slide 45 — ADCS ESC1 原理

- [NICE-TO-FIX] [MISSING] XML node 2 says `申請 VulnTemplate1 / 填 da_alice@corp.athena.lab` (no explicit "UPN" prefix). md adds `UPN 填 da_alice@corp.athena.lab`. Adding "UPN" is technically correct (the certipy `-upn` flag confirms it on slide 46) but it's an editorial annotation, not what the slide shows.

### Slide 46 — certipy req → da_alice.pfx

- [OK] Full command including `-u legacy_kev@corp.athena.lab -p 'M0nk3y!B@n4n4#99' -ca CORP-CA -template VulnTemplate1 -upn da_alice@corp.athena.lab` matches XML byte-for-byte.

### Slide 50 — Stage 2 ACCT-DB01 · OBSERVE

- [NICE-TO-FIX] [HALLUCINATED] md adds command `nmap -Pn -p 1433,445 192.168.0.23`. XML doesn't show this command (only the resulting open ports `1433 MSSQL / 445 SMB` in the OPS LOG and the conclusion `→ 直接走 admin_share 取 hash`). Plausible inference but not from slide.
- [OK] OPS LOG `OODA / PORT 1433 MSSQL / PORT 445 SMB / ADMIN PATH ✓ DA in 手 / ✓ SMB on 445 / → secretsdump` matches XML semantically.

### Slide 52 — secretsdump 輸出

- [BLOCKER] [HALLUCINATED] md's command-output code block contains a fabricated password: `mssql_svc:Sup3rS3cret!2026   ← 服務帳號明文`. The XML for slide 52 has only the placeholder `[ 待貼：secretsdump 終端輸出 ] / SAM:Administrator hash / + MSSQL service password` — no real terminal output, no concrete password. Inventing `Sup3rS3cret!2026` and presenting it as if it were the actual secretsdump line risks audience confusion ("what is the actual MSSQL service password?") and weakens authenticity. Either replace with `<redacted>`, use clearly-fake `<service_password>`, or get the real value from Harry. Same applies to the `Administrator:500:aad3b...:8846f7eaee...` line — these specific hash bytes also aren't in XML.
- [OK] OPS LOG `TOOL impacket-ad:secretsdump / PROTO SMB / 445 / DUMPED SAM hashes / LSA secrets / service.mssql_pass / fact saved access.local_admin` matches XML.
- [OK] `secretsdump.py corp/da_alice@192.168.0.23 -k` invocation is reasonable (XML doesn't specify the exact command but the tool name + protocol match).

### Slide 53 — Stage 2 ACCT-DB01 · DONE

- [OK] Bottom bar `21:14:02 ACCT-DB01 Compromised · 全程 < 20 分鐘` matches XML.
- [OK] OPS LOG `TARGET ACCT-DB01 / GAINED local admin / mssql sa / 財務資料 / MISSION COMPLETE 3 / 3 targets / 全自動執行` matches XML.
- [NICE-TO-FIX] [HALLUCINATED] alert-box says `WEB01 (Δ+7m27s) → DC-01 (Δ+8m14s) → ACCT-DB01 (Δ+4m21s)`. The first two come from XML (slides 39 and 49). The third (`Δ +4m21s`) is computed by md and is slightly wrong: from stage-2 OBSERVE start at 21:09:50 to compromise at 21:14:02 = 4m12s, not 4m21s. Minor synthesized-timing arithmetic error.

### Slide 54 — Mission Complete

- [OK] Kill chain `T1190 (RCE) → T1558.004 (AS-REP) → T1110.002 (offline crack) → T1649 (ADCS ESC1) → T1003.003 (secretsdump)` matches XML verbatim.
- [OK] Stats 20 min / 3 of 3 / 0 / 100% match.
- [OK] `完全靠 AD 設定錯誤 + AI 自動串接` matches the bottom callout in XML.

### Slide 56 — Roadmap (hidden in original PPT)

- [NICE-TO-FIX] [META] XML has `show="0"` on this slide (i.e. hidden in the original deck), but the md does NOT include the `(hidden in original PPTX)` annotation that slide 32 received. Either drop slide 56 from the chunk, or annotate it.
- [NICE-TO-FIX] [MISSING] XML Persistence card body lists four items: `站穩後不離場 / golden ticket / DSRM / skeleton key / 跨重啟存活` (5 lines actually). md compresses to `站穩後不離場 / golden ticket · DSRM / 跨重啟存活` and drops `skeleton key`. Drops one persistence technique.

### Slide 60 — Q&A

- [NICE-TO-FIX] [HALLUCINATED] md adds two contact blocks:
  ```
  Harry Chen / <!-- TODO: contact -->
  Alex Chih  / <!-- TODO: contact -->
  ```
  XML for slide 60 has only `?`, `Questions & Answers`, `歡迎挑戰任何架構假設、攻擊細節、武器化路徑。`, `// AWAITING INPUT _`. The contact placeholders are an md-side template addition. Probably intentional, but worth confirming with Harry whether he wants speaker contact info on the Q&A slide.

### Slide 61 — Thanks

- [NICE-TO-FIX] [WRONG] md says `CYBERSEC 2026` (all caps); XML says `Cybersec 2026` (mixed case). Cosmetic. Pick one and apply consistently.

## Slides verified clean (no findings)

30, 33, 34, 37, 38, 41, 43, 47, 48, 49, 51, 55, 57, 58, 59. These reproduce XML faithfully — including all MITRE T-codes (T1190, T1558.004, T1110.002, T1649, T1003.003, T1059.001, T1003.001, T1187), hostnames (WEB01, DC-01, ACCT-DB01), IPs (192.168.0.10/16/20/23), passwords (M0nk3y!B@n4n4#99, W!nt3rC0m!ng#DA2026$, X9k#mP2!vL@qR7$), and Traditional-Chinese phrasing.

## Triage summary

| Severity   | Count | Examples |
|------------|-------|----------|
| BLOCKER    | 2     | slide 29 (`ACCT-DB` vs `ACCT-DB01`), slide 52 (fake password `Sup3rS3cret!2026`) |
| NICE-TO-FIX | 14   | mostly: synthesized commands not in XML (36, 40, 50), dropped flavor words (31, 35, 56), timestamp arithmetic drift (53), casing (61), placement drift (42, 45) |
| OK         | 33 slides covered; 15 fully clean |

Highest-priority fixes for Harry's review:

1. Slide 29 — confirm whether the cover slide should say `ACCT-DB` (matching XML) or `ACCT-DB01` (matching the rest of the deck).
2. Slide 52 — replace fabricated `Sup3rS3cret!2026` with redaction or real value.
3. Slide 56 — annotate as hidden, or remove.
4. Slide 53 — fix `Δ +4m21s` to `Δ +4m12s` (or recompute from intended start).
