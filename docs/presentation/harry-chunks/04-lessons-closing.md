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

<div class="bridge-bottom" style="margin-top: 1.6rem;">
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

<div class="alert-box" style="margin-top: 1.6rem;">
<strong>OODA 不是終點，是持續迭代的引擎。</strong> 每加一條前線，整個 doctrine 一起升級。
</div>

---
transition: fade
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

<div class="bridge-bottom" style="margin-top: 1.6rem;">
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
