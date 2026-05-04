---
layout: cover
class: 'text-center'
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

<div class="bridge-bottom" style="margin-top: 1.4rem; font-style: italic;">
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

<div class="bridge-bottom" style="margin-top: 1.4rem;">
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

<div class="alert-box" style="margin-top: 1.4rem;">
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

<div class="bridge-bottom" style="margin-top: 1.6rem; text-align: center;">
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

<div class="bridge-bottom" style="margin-top: 1.6rem;">
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

<div class="bridge-bottom" style="margin-top: 1.4rem; font-style: italic;">
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

<div class="bridge-bottom" style="margin-top: 1.4rem; font-style: italic;">
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
<span style="color: var(--fg-dim);">• MiG 性能更好</span><br/>
<span style="color: var(--accent-green);">• F-86 卻贏 10:1</span><br/><br/>
Boyd 把 F-86 的勝利拆出三件事：<br/>
<strong>觀察 — 判斷 — 決定 — 行動</strong>
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

<div class="bridge-bottom" style="margin-top: 1.6rem; font-style: italic;">
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
---

<!-- Slide 15 from Harry's PPT — Orient JSON output -->

<div class="op-header">
<span>// OPERATION ATHENA-ORIENT</span>
<span class="classified">:: CLASSIFIED</span>
</div>

<div class="op-layout">
<div class="op-content">

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

<div class="alert-box" style="margin-top: 0.8rem;">
看到那個 <span class="status elevated">0.87</span> 了嗎？ — 下一張告訴你它怎麼算出來的 →
</div>

</div>

<div class="ops-log">
<div class="ops-header">// OPS LOG · ORIENT</div>

```bash {1|2|3|4|5|6|all}
[14:02:11] ● FACTS LOADED  n=42
[14:02:12] ● LLM CALL      claude-opus
[14:02:14] ● JSON PARSED   ok
[14:02:14] ● TECH PICKED   T1558.004
[14:02:14] ● CONFIDENCE    0.87
[14:02:14] ● ROUTE READY   asrep_roast
[14:02:14] ● HANDOFF       → DECIDE
```

</div>
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

<div class="bridge-bottom" style="margin-top: 1.4rem; font-style: italic;">
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

<div class="alert-box" style="margin-top: 1.2rem;">
校正後 Brier score 從 <strong>0.31 降到 0.12</strong>（demo 環境 200 輪樣本）。
</div>

---
transition: fade
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

<div class="bridge-bottom" style="margin-top: 1.4rem; font-style: italic;">
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

<div class="bridge-bottom" style="margin-top: 1.4rem; font-style: italic;">
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

<div class="bridge-bottom" style="margin-top: 1.4rem; font-style: italic;">
架構講完了 — 接下來把它跑成五個動作循環 →
</div>
