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

<div class="bridge-bottom" style="margin-top: 1.2rem;">
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

<div class="bridge-bottom" style="margin-top: 1.2rem;">
<strong>Recon</strong> 出工去找新東西、<strong>Surveillance</strong> 把找到的東西收成資產 — 一次出擊變成累積戰力。
</div>

---
transition: fade
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

<div class="bridge-bottom" style="margin-top: 1.2rem;">
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

<div class="alert-box" style="margin-top: 1rem; font-style: italic; color: var(--accent-green, #3FB950); border-left-color: var(--accent-green, #3FB950); background: rgba(63,185,80,0.08);">
失敗記憶 + cooldown — 比人類紅隊的 Notion 筆記還精準
</div>

---
transition: fade
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

<div class="bridge-bottom" style="margin-top: 1.2rem;">
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

<div class="bridge-bottom" style="margin-top: 1.2rem;">
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
