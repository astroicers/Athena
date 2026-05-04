---
theme: default
title: 'AI as Commander — Cloud Front'
info: |
  CYBERSEC 2026 — Cloud path (10 min · closing)
  Alex Chih · Cheehoo Labs
class: 'text-white'
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
<div class="desc">The real castle is hybrid identity.</div>
</div>
</div>

</div>

<div class="cover-footer">
<div class="speaker">Alex Chih · Cheehoo Labs · CYBERSEC 2026</div>
<div class="tagline">DA is the trigger. Hybrid identity is the payload.</div>
</div>

</div>

---
transition: fade
---

<!--
Slide 2 — Terrain Shift | 1:00 (0:45 - 1:45)

讓觀眾意識到：DA 在 2026 年現代企業 = 跨進雲端的入場券。
台灣 80%+ 企業是 hybrid。Entra Connect 是雙向通道。
-->

<div class="slide-eyebrow">Section A · Terrain Shift</div>
<div class="slide-h1">DA is not the summit — it's the bridge</div>
<div class="slide-sub">85% of Taiwan mid-size enterprises run hybrid identity in 2026.</div>

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
<strong>Entra Connect 是雙向通道</strong> — 你拿到 DA，就拿到通往雲端的橋。
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
<td>IAM Role · Resource ARN · Tenant ID</td>
</tr>
<tr>
<td><strong>Comms</strong></td>
<td>SSH · SMB · Kerberos · LDAP</td>
<td>OAuth Token · PRT · SAS Token · API key</td>
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
---

<!--
Slide 4 — Cloud OODA Tested | 2:00 (3:15 - 5:15) ⭐ 核心 1

替換為真實 SSRF demo recap。flAWS.cloud Level 5 跑通的 log。
這是全場唯一「跑過的真實證據」— 必須用真截圖 + 真 Orient JSON。

TODO（演講前要補的素材）：
- 在 Orient JSON 區塊上方加 War Room timeline 截圖
- 確認 Orient JSON 是 log 撈出來的真實內容（不是改寫的）
-->

<div class="slide-eyebrow">From the Lab · flAWS.cloud</div>
<div class="slide-h1">AI's first cloud decision</div>
<div class="slide-sub">Real Orient log from a lab run. Not a slide mock-up.</div>

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
  "situation_assessment": "Web app exposes /proxy/ endpoint with
    IMDS canary confirmed. SSH is key-only — brute force will fail.
    Cloud pivot offers higher strategic value.",
  "recommended_technique": "T1190",
  "reasoning": "Rule #10 (SSRF→IMDS) triggered.
    SSH dead-branched via Rule #2.",
  "confidence": 0.87
}
```

<div class="alert-box" style="margin-top: 1rem;">
小兵看到 SSH:22 就 brute force。指揮官看到 SSH 是 key-only — 自動跳過，選擇 SSRF。<strong>不是更快，是更聰明。</strong>
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
一個邊界漏洞的 blast radius 跨 <strong>5 個域 · 2 朵雲</strong>。傳統 CVSS 算不出來這種當量。
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
<div class="body">Test tenant → Microsoft corporate + customer tenants. Full scope still undisclosed today.</div>
</div>

<div class="side red-border">
<div class="head">Volt Typhoon<br/><span style="font-size: 0.78rem; color: var(--fg-dim); font-weight: 400;">2024–25</span></div>
<div class="body">On-prem persistence + cloud lateral. Critical infrastructure (incl. Taiwan power, telco).</div>
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
<div class="body">Does your SOC know <strong>on-prem credentials can pivot to cloud</strong>? And vice versa?</div>
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
From toolbox to nuclear weapon —<br/>
the distance isn't <span style="color: var(--fg-dim);">tool progress</span>.
</div>

<div style="font-size: 2.6rem; font-weight: 700; line-height: 1.4; margin-top: 1.6rem; color: var(--accent-red);">
是視野的擴張。
</div>

<div style="margin-top: 3rem; color: var(--fg-dim); font-size: 1rem;">
Alex Chih · Cheehoo Labs · CYBERSEC 2026
</div>

</div>
