# Speaker Notes Audit — 69-slide deck

> Audit of `<!-- ... -->` HTML comment blocks immediately after each slide separator (`---`).
> Quality bar: a GOOD note specifies (a) time budget, (b) the ONE beat to land, (c) transition cue.
> Source file: `/Users/alexchih/Documents/Projects/Alex/Athena/docs/presentation/slides.md` (3353 lines, 69 slides)

## Speaker map (deck-index)
- Slides 1–54: Harry Chen (~20 min on-prem demo + framework)
- Slides 55–62: Alex Chih (~10 min cloud SSRF→IMDS demo)
- Slides 63–69: Harry Chen (lessons + roadmap + closing + Q&A + thanks)

## Summary
- **GOOD: 8** (all Alex's slides 55-62 — already have time-budgeted, beat-driven, transition-aware notes)
- **WEAK: 60** (Harry's 53 demo/framework slides + 7 closing slides — comments are topic tags, not delivery guidance)
- **MISSING: 1** (Slide 3 — Alex profile placeholder, bio not yet drafted)

> Note: Harry's slides do contain in-slide transition language (`bridge-bottom` div) and demo OPS LOG sidebars,
> so the speaker has visible cues on screen — but the `<!-- -->` comment itself does not include a time budget,
> beat, or speaker direction. Per the audit's GOOD criteria, those count as WEAK.

---

## WEAK / MISSING slides

### Slide 1 — Cover · OPERATION ATHENA-433FC2 (Harry)
**Status**: WEAK
**Existing**: `Slide 1 from Harry's PPT — Cover · OPERATION ATHENA-433FC2`
**Suggest**:
> 30 sec — slow, eye contact. 標題念出口：「AI 從小兵變指揮官」+「18m57s 全自動全滅」。
> 重點：把右下角的 18m57s 種進觀眾腦袋——這個數字會在第 54 張收尾時對上。
> Bridge: 「我跟 Alex 今天 50 分鐘要證明這件事」→ 進講者頁。

---

### Slide 2 — Speaker · Harry Chen
**Status**: WEAK
**Existing**: `Slide 2 from Harry's PPT — Speaker · Harry Chen`
**Suggest**:
> 30 sec. 自我介紹但不背履歷——挑一條：「前政府機關紅隊組長，數十次實戰滲透。」
> 重點：建立「我打過真環境，不是只會跑工具」可信度。
> Bridge: 「等等的 Alex 是雲端那條線的人」→ 進 Alex profile。

---

### Slide 3 — Speaker · Alex Chih (TODO placeholder)
**Status**: MISSING
**Existing**: `Slide 3 from Harry's PPT — Speaker · Alex Chih (TODO placeholder)` plus three inline `TODO: Alex profile` markers
**Suggest**:
> TODO placeholder — speaker bio not yet drafted. 待補：姓名 / 職稱 / 三點經歷 / 專長領域。
> 演講前必須補：照片、姓名、Cheehoo Labs 職稱、雲端紅隊／hybrid identity 經歷。
> 30 sec. Harry 帶過介紹（「我搭檔 Alex 等等 10 分鐘上場」），不要 Alex 走上台只為這頁。
> Bridge: 「他等下處理雲端那段，現在先回來看為什麼要做這套」。

---

### Slide 4 — Three Doctrines (Prologue) (Harry)
**Status**: WEAK
**Existing**: `Slide 4 from Harry's PPT — Three Doctrines (Prologue)`
**Suggest**:
> 1 min — 慢、重、像下軍令。三條信條一條念出聲：FACT-DRIVEN / DOCTRINE BEATS TOOLS / TEMPO IS THE WEAPON。
> 重點：種鼓點。整場 50 張每一頁都會回來敲這三條，第 65 張 refrain 收尾。
> Bridge: 「接下來 50 張，每一頁都在敲這三個鼓點」（slide 內文已寫，照念即可）。

---

### Slide 5 — Mission Briefing · Agenda (Harry)
**Status**: WEAK
**Existing**: `Slide 5 from Harry's PPT — Mission Briefing · Agenda`
**Suggest**:
> 45 sec. 不要逐章念——指 OPERATION 那行說「重點是第 5 章 24 張的 demo」。
> 重點：管理觀眾的注意力預算，告訴他們長 demo 在後段。
> Bridge: 「先看為什麼傳統紅隊長這樣已經不夠」→ Ch1。

---

### Slide 6 — Traditional Kill Chain (Harry)
**Status**: WEAK
**Existing**: `Slide 6 from Harry's PPT — Chapter 1 · Traditional Kill Chain`
**Suggest**:
> 30 sec. 五個節點念過去：偵察 → 突破 → 立足 → 橫向 → 收割。
> 重點：底下那行 OODA × 4 是埋梗——每一段都有 OODA loop。
> Bridge: 「傳統紅隊一週的工作量，AI 在 20 分鐘內全程自走」（內文已寫）。

---

### Slide 7 — 每一階段在做什麼 (Harry)
**Status**: WEAK
**Existing**: `Slide 7 from Harry's PPT — 每一階段在做什麼`
**Suggest**:
> 45 sec. 三條快過——01 偵察突破、02 立足橫向、03 收割。提一下 WEB01 / DC-01 / ACCT-DB01 是等下 demo 的三台機器。
> 重點：先讓觀眾記三台主機名，等下 demo 才不會迷路。
> Bridge: 「軍事作戰其實遇過同樣的問題」→ Ch1 第三張類比。

---

### Slide 8 — 軍事作戰遇到過同樣的問題 (Harry)
**Status**: WEAK
**Existing**: `Slide 8 from Harry's PPT — 軍事作戰遇到過同樣的問題`
**Suggest**:
> 1 min. 二戰前各兵種各自為政 → 戰後 C2 → C5ISR。重點是這不是新發明，是借舊智慧。
> 重點：建立「軍事八十年的學費，紅隊直接收」的權威感。
> Bridge: 「軍事先解決了這個問題，我們直接借用」（slide 已寫）→ Ch2 chapter cover。

---

### Slide 9 — Chapter 02 cover · DOCTRINE (Harry)
**Status**: WEAK
**Existing**: `Slide 9 from Harry's PPT — Chapter 02 cover · DOCTRINE`
**Suggest**:
> 15 sec — 章節分頁，停頓即可。「從天上的空戰到鍵盤上的紅隊」念一次。
> 重點：節奏轉換點，給觀眾喘口氣。不要解釋細節，留給後三張。
> Bridge: 「先看 C5ISR 是哪八個字」→ slide 10。

---

### Slide 10 — C5ISR 是什麼 (8-grid) (Harry)
**Status**: WEAK
**Existing**: `Slide 10 from Harry's PPT — C5ISR 是什麼 (8-grid)`
**Suggest**:
> 1 min 30 sec. 八個 C 不要全部念——挑 Command / Cyber / Intelligence 三個說過去，其他指過去帶過。
> 重點：先讓觀眾接受八個字是「設計藍圖」，下一張對到 Athena。
> Bridge: 「這八個字就是 Athena 的設計藍圖」（內文已寫）。

---

### Slide 11 — C5ISR → Athena 對應表 (Harry)
**Status**: WEAK
**Existing**: `Slide 11 from Harry's PPT — C5ISR → Athena 對應表`
**Suggest**:
> 1 min. 不要逐條念——挑 Recon=nmap / Intelligence=Facts DB / Cyber=certipy 三條對到具體工具。
> 重點：把抽象軍事 doctrine 落地成 17 個 MCP 工具，這是 Athena 的工程實踐。
> Bridge: 「C5ISR 對應完了，下一張看節奏：Boyd 的 OODA」（內文已寫）。

---

### Slide 12 — Boyd's OODA Loop (Harry)
**Status**: WEAK
**Existing**: `Slide 12 from Harry's PPT — Boyd's OODA Loop`
**Suggest**:
> 1 min. 講故事——韓戰 F-86 vs MiG-15、性能差但 10:1 勝。
> 重點：OODA 不是流程圖，是節拍器。誰轉得快誰贏。
> Bridge: 「Boyd 在天上證明過了，看它在 LLM 裡長什麼樣」（內文已寫）。

---

### Slide 13 — Athena 怎麼跑 OODA (Harry)
**Status**: WEAK
**Existing**: `Slide 13 from Harry's PPT — Athena 怎麼跑 OODA`
**Suggest**:
> 45 sec. 四步骨架：Observe（MCP 寫 facts）→ Orient（LLM 讀 facts 推 ATT&CK）→ Decide（門檻）→ Act（router 派工）。
> 重點：先給輪廓，下一章每步拆細節。
> Bridge: 「理論結束了，給你看 code」→ Ch3 cover。

---

### Slide 14 — Chapter 03 cover · ARCHITECTURE (Harry)
**Status**: WEAK
**Existing**: `Slide 14 from Harry's PPT — Chapter 03 cover · ARCHITECTURE`
**Suggest**:
> 15 sec — 章節分頁。「下面七張是引擎室」這句念出來。
> 重點：預告這章會看 confidence 0.87 怎麼算的（內文已寫，照唸）。
> Bridge: 直接進 Orient JSON。

---

### Slide 15 — Orient JSON output (Harry)
**Status**: WEAK
**Existing**: `Slide 15 from Harry's PPT — Orient JSON output`
**Suggest**:
> 1 min 30 sec. JSON 不要逐欄念——指 `recommended_technique_id` + `confidence: 0.87` + `options: 3 條`。
> 點 1/2/3 揭露 OPS LOG（FACTS LOADED → LLM CALL → ROUTE READY）。
> 重點：LLM 不是吐文字，是吐結構化判斷。每個 confidence 對得起一條 fact。
> Bridge: 「那個 0.87 怎麼算的？下一張」（內文已寫）。

---

### Slide 16 — Decision Engine 三道閥 (Harry)
**Status**: WEAK
**Existing**: `Slide 16 from Harry's PPT — Decision Engine 三道閥`
**Suggest**:
> 1 min. 三道閥：composite confidence × risk_threshold matrix × noise_budget。
> 重點：Decide 不是黑盒，是三個量化閘門。LLM 過度自信會被歷史校正打回。
> Bridge: 「下一張拆開 confidence 的三個來源」（內文已寫）。

---

### Slide 17 — 0.87 怎麼算的 (Harry)
**Status**: WEAK
**Existing**: `Slide 17 from Harry's PPT — 0.87 怎麼算的（confidence 拆解）`
**Suggest**:
> 1 min 30 sec. 三因子幾何平均：LLM × validation × history。
> 重點：底下那行 alert-box——Brier score 從 0.31 降到 0.12。這是唯一一個「校正後比 LLM 直覺更準」的證據，請念出來。
> Bridge: 「校正講完了，看武器庫」→ MCP 工具表。

---

### Slide 18 — 17 個 MCP 工具 (Harry)
**Status**: WEAK
**Existing**: `Slide 18 from Harry's PPT — 17 個 MCP 工具`
**Suggest**:
> 45 sec. 不要逐個念——指 RECON / EXPLOIT / AD ATTACK / POST-EX 四群。提一句 17 個 MCP server 各自是 sandbox process。
> 重點：工具是肌肉、不是大腦（呼應信條 ②）。
> Bridge: 「17 個工具今天好用，明天新環境怎辦？」（內文已寫）→ 動態路由。

---

### Slide 19 — hardcoded dict → 動態路由 (Harry)
**Status**: WEAK
**Existing**: `Slide 19 from Harry's PPT — 從 hardcoded dict 到動態路由`
**Suggest**:
> 1 min. 左右並列：舊 10 行 dict（每加新工具改 code 重 deploy）vs 新 3 行（LLM 自己挑）。
> 重點：這是 Athena 的工程關鍵——新 MCP server 上線即可被 LLM 自動發現。
> Bridge: 「LLM 怎麼知道用哪個工具？」→ schema 那張。

---

### Slide 20 — Schema 是介面，也是 sandbox (Harry)
**Status**: WEAK
**Existing**: `Slide 20 from Harry's PPT — Schema 是介面，也是 sandbox`
**Suggest**:
> 1 min. 三點：tools/list 給 metadata、選錯 fallback、prompt injection allowlist（純 ASCII / 無祈使句 / ≤200 字元）。
> 重點：MCP description 是攻擊面——Athena 對所有 description 做白名單過濾。資安觀眾會 care 這條。
> Bridge: 「架構講完了，下一章把它跑成五個動作循環」（內文已寫）→ Ch4。

---

### Slide 21 — Ch4 Framework chapter divider (Harry)
**Status**: WEAK
**Existing**: `Slide 21 from Harry's PPT — Ch4 Framework · Chapter divider (作戰準則 — 五個動作循環)`
**Suggest**:
> 15 sec — 章節分頁。「OODA × C5ISR 接成一張表，最後落到 TEMPO」念一次。
> 重點：預告本章收尾在 30× 那張。
> Bridge: 直接進「為什麼把兩個框架接在一起」。

---

### Slide 22 — Why fuse OODA + C5ISR (Harry)
**Status**: WEAK
**Existing**: `Slide 22 from Harry's PPT — Ch4 Framework · Why fuse OODA + C5ISR`
**Suggest**:
> 1 min. OODA 給節奏（轉得多快），C5ISR 給體系（具備什麼能力）——兩個各自缺對方那塊。
> 重點：兩個框架軍事都用過，沒人融合。Athena 的設計就是把 OODA 四步當骨架、C5ISR 八能力填進去。
> Bridge: 「接下來四頁逐項拆 Observe / Orient / Decide / Act」（內文已寫）。

---

### Slide 23 — Observe ↔ Recon + Surveillance (Harry)
**Status**: WEAK
**Existing**: `Slide 23 from Harry's PPT — Ch4 Framework · Observe ↔ Recon + Surveillance`
**Suggest**:
> 1 min. 三欄：Recon 一次性出工 / Surveillance 持續累積 / Fact schema 標準化。
> 重點：Recon 出去找新東西、Surveillance 把找到的收成資產（內文已寫）。
> Bridge: 「Orient 看著 fact 但會不會死循環？」→ slide 25。

---

### Slide 24 — Orient ↔ Intelligence + Command (Harry)
**Status**: WEAK
**Existing**: `Slide 24 from Harry's PPT — Ch4 Framework · Orient ↔ Intelligence + Command`
**Suggest**:
> 1 min 30 sec. 三欄：8 個 input sections / JSON output / 四原則（kill chain 位置 / fact 驅動 / 失敗記憶 / 憑證優先）。
> 重點：Orient 是 OODA 靈魂、也是 C5ISR Intelligence 核心——兩個框架在同一個地方說同一件事。
> Bridge: 「Orient 怎麼避免重推已敗技術？」（內文已寫）→ slide 25。

---

### Slide 25 — Avoid retrying failed techniques (Harry)
**Status**: WEAK
**Existing**: `Slide 25 from Harry's PPT — Ch4 Framework · Avoid retrying failed techniques`
**Suggest**:
> 1 min. 三步：失敗寫 attempt.failed / Orient prompt 注入 blocked_techniques / 30 min cooldown 解禁。
> 重點：失敗記憶 + cooldown——比人類紅隊的 Notion 筆記還精準（slide 內文已寫）。
> Bridge: 「Orient 講完，下一張 Decide」→ slide 26。

---

### Slide 26 — Decide ↔ Control (Harry)
**Status**: WEAK
**Existing**: `Slide 26 from Harry's PPT — Ch4 Framework · Decide ↔ Control`
**Suggest**:
> 1 min 30 sec. 三欄：composite confidence / risk matrix / noise budget。
> 重點：指揮官不靠感覺下令，靠量化作戰評估——這是 Decide vs LLM 直覺最大差別（內文已寫）。
> Bridge: 「Decide 算完了，下一張 Act」（內文已寫）。

---

### Slide 27 — Act ↔ Computers + Cyber + Comms (Harry)
**Status**: WEAK
**Existing**: `Slide 27 from Harry's PPT — Ch4 Framework · Act ↔ Computers + Cyber + Comms`
**Suggest**:
> 1 min. 三欄：engine_router 派工 / 17 個 MCP 武器庫 / Facts DB + WebSocket 雙通道。
> 重點：Act 不只是「下指令」，是把決策—武器—回報接成閉環（內文已寫）。
> Bridge: 「四個動作講完，最後一張：tempo 才是勝負手」（內文已寫）→ slide 28。

---

### Slide 28 — TEMPO IS THE WEAPON 30× (Harry)
**Status**: WEAK
**Existing**: `Slide 28 from Harry's PPT — Ch4 Framework · TEMPO IS THE WEAPON (30× punchline)`
**Suggest**:
> 30 sec — 慢，重音。「30 倍」念兩次，停頓 2 秒。「TEMPO IS THE WEAPON」用英文唸出。
> 重點：信條 ③ 收尾。30 秒一個 OODA loop、失敗變便宜、速度本身就是維度。
> Bridge: 「理論講完了，真槍實彈」→ Ch5 demo cover。

---

### Slide 29 — Ch5 Operation chapter cover (Harry)
**Status**: WEAK
**Existing**: `Slide 29 from Harry's PPT — Ch5 Operation · CHAPTER COVER · 真槍實彈`
**Suggest**:
> 20 sec — 章節分頁，提氣。「三個 stage、不到 20 分鐘、零人工介入：WEB01 → DC-01 → ACCT-DB01」念一次。
> 重點：宣告 demo 開始。建議深呼吸一次再進下一張。
> Bridge: 直接進系統架構圖。

---

### Slide 30 — Athena 系統架構 (Harry)
**Status**: WEAK
**Existing**: `Slide 30 from Harry's PPT — Ch5 Operation · ARCHITECTURE · Athena 系統架構`
**Suggest**:
> 30 sec. 四層由上而下：War Room UI / OODA Engine / Decision + Facts DB / MCP Tool Layer。
> 重點：每層可獨立替換——Anthropic / OpenAI / 在地 LLM 都跑得起來（slide 內文已寫）。資安觀眾在意「不綁定 Anthropic」這條。
> Bridge: 「demo 從哪個角度看？」→ 今天的目標。

---

### Slide 31 — 今天的目標 (Harry)
**Status**: WEAK
**Existing**: `Slide 31 from Harry's PPT — Ch5 Operation · MISSION · 今天的目標`
**Suggest**:
> 30 sec. 四個節點圖：Attacker → WEB01 → DC-01 → ACCT-DB01，IP 念一次。
> 重點：三台靶機、全強密碼、純靠 AD 設定錯誤、預期 < 20 分鐘（內文已寫）。最後那句強調觀眾會看到 AI 跳過密碼這條路。
> Bridge: 「demo 不是一次就順的——下一張先談踩過的坑」→ slide 32。

---

### Slide 32 — 踩過的坑 (edge cases) (Harry)
**Status**: WEAK
**Existing**: `Slide 32 from Harry's PPT — Ch5 Operation · EDGE-CASES · 踩過的坑（hidden in original PPTX）`
**Suggest**:
> 1 min. 三條 failure mode：EDR 擋 LSASS / Bloodhound 超時 streaming / 平行 race condition。
> 重點：示範「200+ 次 demo」的真實感，不是只跑成功的那次。資安觀眾尤其吃這條（誠實）。
> Bridge: 「坑談完了，看靶機 AD 設定錯誤」→ slide 33。

---

### Slide 33 — 靶機 AD 設定錯誤全景 (Harry)
**Status**: WEAK
**Existing**: `Slide 33 from Harry's PPT — Ch5 Operation · INTEL · 靶機 AD 設定錯誤全景`
**Suggest**:
> 30 sec. 五條設定錯誤、右欄全部「無關」（密碼強度）。
> 重點：punchline 那行——「五條，沒有一條跟密碼有關」。觀眾要意識到 AI 走的是設定錯誤這條路。
> Bridge: 「但密碼是強密碼嗎？」→ slide 34 印證。

---

### Slide 34 — 密碼強度全部強密碼 (Harry)
**Status**: WEAK
**Existing**: `Slide 34 from Harry's PPT — Ch5 Operation · INTEL · 密碼強度全部強密碼`
**Suggest**:
> 30 sec. 三組密碼念出來——`M0nk3y!B@n4n4#99` 等，重音「全部強密碼」。
> 重點：danger box 那句——「密碼噴灑全部失敗。AI 選擇了另一條路」。這是 demo 第一個轉折。
> Bridge: 「現在進入 demo——OODA loop 啟動」→ slide 35 Stage 0 kickoff。

---

### Slide 35 — Stage 0 kickoff (Harry)
**Status**: WEAK
**Existing**: `Slide 35 from Harry's PPT — Ch5 Operation · STAGE 0 · 行動啟動（kickoff · OODA loop start）`
**Suggest**:
> 30 sec. AUTO_FULL · interval=30s · noise_budget=100。點 1/2/3/4/5/6 揭露 OPS LOG 一行行（MODE / INTERVAL / RISK / NOISE / STATE / 行動啟動）。
> 重點：標記「人類從這刻開始不再介入」的時間錨。
> Bridge: 「OBSERVE 從 WEB01 開始」→ slide 36。

---

### Slide 36 — WEB01 OBSERVE recon (Harry)
**Status**: WEAK
**Existing**: `Slide 36 from Harry's PPT — Ch5 Operation · STAGE 0 · WEB01 OBSERVE recon`
**Suggest**:
> 45 sec. 點 1/2/3/4/5/6/7 揭露 OPS LOG 一行行（OBSERVE → nmap → port 80/5985/445 → /debug.aspx → ORIENT）。
> 重點：第一個 OODA loop 的 OBSERVE 階段，nmap 找到 debug.aspx 是接下來 RCE 的入口。
> Bridge: 「facts 寫完，等 LLM 判斷」→ slide 37 ORIENT。

---

### Slide 37 — WEB01 ORIENT (T1190 LLM decision) (Harry)
**Status**: WEAK
**Existing**: `Slide 37 from Harry's PPT — Ch5 Operation · STAGE 0 · WEB01 ORIENT (LLM decision T1190)`
**Suggest**:
> 1 min. 左欄 situation assessment、右欄 T1190 / confidence 0.75 / web_rce_execute / auto_approved=True。
> 重點：「LLM 自己決定要用 web_rce_execute，不是我們寫死的」（slide 已寫）——強調動態路由。
> Bridge: 「auto_approved 了，下一張 ACT」→ slide 38。

---

### Slide 38 — WEB01 ACT debug.aspx RCE (Harry)
**Status**: WEAK
**Existing**: `Slide 38 from Harry's PPT — Ch5 Operation · STAGE 0 · WEB01 ACT (debug.aspx RCE)`
**Suggest**:
> 45 sec. 上方 HTTP request `?cmd=whoami` → `iis apppool\defaultapppool`。下方 C# 漏洞 code 指出 `cmdArg` 零過濾。
> 重點：danger box——LLM 看到原始碼推 RCE 信心 0.75 直接 fire。
> Bridge: 「攻陷了」→ slide 39 DONE。

---

### Slide 39 — WEB01 DONE compromised (Harry)
**Status**: WEAK
**Existing**: `Slide 39 from Harry's PPT — Ch5 Operation · STAGE 0 · WEB01 DONE (compromised)`
**Suggest**:
> 30 sec. 點 1/2/3/4/5/6/7 揭露 OPS LOG（TARGET / VECTOR / PAYLOAD / SHELL / COMPROMISED / NEXT / fact saved）。
> 重點：Δ +7m27s 念出來——這是第一台。寫入 `access.web_shell` 進 Facts DB，下輪 OODA 就能讀。
> Bridge: 「下一台 DC-01」→ slide 40 Stage 1。

---

### Slide 40 — DC-01 OBSERVE AS-REP ready (Harry)
**Status**: WEAK
**Existing**: `Slide 40 from Harry's PPT — Ch5 Operation · STAGE 1 · DC-01 OBSERVE (AS-REP ready)`
**Suggest**:
> 45 sec. 點 1/2/3/4/5/6/7 揭露 OPS LOG（OBSERVE → bloodhound → port 88/389/445 → ad.user_no_preauth → AS-REP READY）。
> 重點：bloodhound 找到 `legacy_kev: DoesNotRequirePreAuth = True`——這條 fact 觸發接下來整段 AS-REP roasting。
> Bridge: 「AS-REP roasting 是什麼原理？」→ slide 41。

---

### Slide 41 — AS-REP Roasting 原理 (Harry)
**Status**: WEAK
**Existing**: `Slide 41 from Harry's PPT — Ch5 Operation · STAGE 1 · AS-REP Roasting 原理`
**Suggest**:
> 1 min. 三步圖：攻擊者請 AS-REP（零憑證）→ KDC 因 DoesNotRequirePreAuth=True 直接吐 → 攻擊者離線爆破。
> 重點：danger box——「DoesNotRequirePreAuth=True 把 pre-authentication 關掉了，KDC 對任何人都吐 AS-REP」。
> Bridge: 「實際指令長這樣」→ slide 42 ACT。

---

### Slide 42 — AS-REP Hash 取得 (impacket-GetNPUsers) (Harry)
**Status**: WEAK
**Existing**: `Slide 42 from Harry's PPT — Ch5 Operation · STAGE 1 · AS-REP Hash 取得 (impacket-GetNPUsers · image6 secretsdump)`
**Suggest**:
> 30 sec. 指 `impacket-GetNPUsers -no-pass -usersfile users.txt` 那行——`-no-pass` 是關鍵。
> 重點：「零憑證，只需要知道帳號名稱」（slide 已寫）。寫入 `access.kerberos.as_rep.legacy_kev`。
> Bridge: 「下一張看 AS-REP 在 wire 上長什麼樣」→ slide 43。

---

### Slide 43 — AS-REP Roasting OPSEC (Harry)
**Status**: WEAK
**Existing**: `Slide 43 from Harry's PPT — Ch5 Operation · STAGE 1 · AS-REP Roasting OPSEC`
**Suggest**:
> 45 sec. 三點：KRB_AS_REQ 沒 PA-ENC-TIMESTAMP / KRB_AS_REP enc-part 直接吐 / OPSEC 為何難抓。
> 重點：noise_cost=2、看起來就是合法 Kerberos 流量、不留登入失敗紀錄。
> Bridge: 「拿到 hash 了，要破解」→ slide 44 hashcat。

---

### Slide 44 — hashcat 破解 (Harry)
**Status**: WEAK
**Existing**: `Slide 44 from Harry's PPT — Ch5 Operation · STAGE 1 · hashcat 破解`
**Suggest**:
> 30 sec. 指 hashcat -m 18200 那行——`Cracked 1/1` + 密碼 `M0nk3y!B@n4n4#99`。
> 重點：強密碼也擋不住離線爆破——關鍵在於不該讓 hash 流出（slide 已寫）。對比表線上 vs 離線。
> Bridge: 「拿到密碼後下一招——ADCS ESC1」→ slide 45。

---

### Slide 45 — ADCS ESC1 原理 (Harry)
**Status**: WEAK
**Existing**: `Slide 45 from Harry's PPT — Ch5 Operation · STAGE 1 · ADCS ESC1 原理`
**Suggest**:
> 1 min. ENROLLEE_SUPPLIES_SUBJECT 那段念出來——「申請者自填 SAN，CA 不驗證」。
> 重點：三步圖——legacy_kev 登入 → 申請 VulnTemplate1 UPN 填 da_alice → CA 直接簽。整段合法走 ADCS API。
> Bridge: 「實際指令」→ slide 46。

---

### Slide 46 — certipy req → da_alice.pfx (Harry)
**Status**: WEAK
**Existing**: `Slide 46 from Harry's PPT — Ch5 Operation · STAGE 1 · certipy req → da_alice.pfx`
**Suggest**:
> 30 sec. 指 `-template VulnTemplate1 -upn da_alice@corp.athena.lab` 兩行。
> 重點：「整個過程合法走 ADCS API，CA 自己蓋章的」（slide 已寫）。
> Bridge: 「但我們真找到 ESC1 嗎？下一張證明」（內文已寫）→ slide 47。

---

### Slide 47 — ESC1 三條件 (Harry)
**Status**: WEAK
**Existing**: `Slide 47 from Harry's PPT — Ch5 Operation · STAGE 1 · ESC1 三條件`
**Suggest**:
> 45 sec. 三條件 AND：Enrollee Supplies Subject / Client Auth EKU / Low-priv enroll 權限。
> 重點：`certipy find -vulnerable` 自動標出。三條件每條都是「設計選項，不是 bug」——這是 ADCS 攻擊面難治的原因。
> Bridge: 「拿到 pfx，下一步換 TGT」→ slide 48。

---

### Slide 48 — certipy auth → da_alice TGT (Harry)
**Status**: WEAK
**Existing**: `Slide 48 from Harry's PPT — Ch5 Operation · STAGE 1 · certipy auth → da_alice TGT (DA reached)`
**Suggest**:
> 30 sec. 點 1/2/3/4/5/6/7 揭露 OPS LOG（PFX → TGT / certipy auth / TICKET / ★ DOMAIN ADMIN）。
> 重點：★ DOMAIN ADMIN 那行重音——這是整個 demo 第一個高潮。寫入 `access.kerberos_ticket.da_alice`。
> Bridge: 「DC-01 攻陷 summary」→ slide 49。

---

### Slide 49 — DC-01 攻陷 (DA achieved) (Harry)
**Status**: WEAK
**Existing**: `Slide 49 from Harry's PPT — Ch5 Operation · STAGE 1 · DC-01 攻陷 (DA achieved)`
**Suggest**:
> 30 sec. Kill chain `T1558.004 → T1110.002 → T1649` 念一次——三段全自動串接無人類批准。
> 重點：Δ +8m14s 念出來。已經兩台。
> Bridge: 「下一台 ACCT-DB01」→ slide 50 Stage 2。

---

### Slide 50 — ACCT-DB01 OBSERVE (Harry)
**Status**: WEAK
**Existing**: `Slide 50 from Harry's PPT — Ch5 Operation · STAGE 2 · ACCT-DB01 OBSERVE`
**Suggest**:
> 30 sec. 點 1/2/3/4/5/6 揭露 OPS LOG（OBSERVE → port 1433/445 → ADMIN PATH ✓ DA ✓ SMB → secretsdump）。
> 重點：DA 已在手，直接走 admin_share——這是 LLM 自己選的最短路徑。
> Bridge: 「secretsdump 原理」→ slide 51。

---

### Slide 51 — secretsdump 原理 (Harry)
**Status**: WEAK
**Existing**: `Slide 51 from Harry's PPT — Ch5 Operation · STAGE 2 · secretsdump 原理`
**Suggest**:
> 45 sec. 三步：ACCESS（DA 走 SMB ADMIN$+IPC$）→ EXTRACT（SAM hive + LSA secrets + DPAPI）→ RESULT（hash + 服務帳號明文）。
> 重點：danger box——SMB 445 走，Windows 當日常檔案分享流量，防火牆無感。
> Bridge: 「實際輸出」→ slide 52。

---

### Slide 52 — secretsdump 輸出 (Harry)
**Status**: WEAK
**Existing**: `Slide 52 from Harry's PPT — Ch5 Operation · STAGE 2 · secretsdump 輸出`
**Suggest**:
> 30 sec. 指 `mssql_svc:Sup3rS3cret!2026   ← 服務帳號明文`——重音明文兩字。
> 重點：服務帳號明文密碼也一起噴出來（slide 已寫）。寫入 `access.local_admin · service.mssql_pass`。
> Bridge: 「ACCT-DB01 也下了」→ slide 53。

---

### Slide 53 — ACCT-DB01 攻陷 Mission Complete (Harry)
**Status**: WEAK
**Existing**: `Slide 53 from Harry's PPT — Ch5 Operation · STAGE 2 · ACCT-DB01 攻陷 (Mission Complete · War Room image2)`
**Suggest**:
> 45 sec. War Room timeline 截圖指過——WEB01 (+7m27s) → DC-01 (+8m14s) → ACCT-DB01 (+4m21s)。
> 重點：點 1-7 揭露 OPS LOG「★ MISSION COMPLETE · 3/3 targets · 全自動執行」。OODA #26 全程可重播可審計。
> Bridge: 「整段收尾」→ slide 54。

---

### Slide 54 — Mission Complete summary (hand-off setup) (Harry)
**Status**: WEAK
**Existing**: `Slide 54 from Harry's PPT — Ch5 Operation · MISSION COMPLETE · 完全靠 AD 設定錯誤 + AI 自動串接`
**Suggest**:
> 1 min — 慢，承上啟下。四個 metric 念過去：20 min / 3-3 / 0 人工 / 100% 信心可解釋。
> 重點：Kill chain 五個 ATT&CK ID 念一次。「完全靠 AD 設定錯誤 + AI 自動串接」（slide 已寫）。
> Bridge: **這是 hand-off 點。** 收：「我把 Domain Admin 拿到了——但 DA 在 2026 是什麼意思？」交給 Alex。Alex 走上台。

---

### Slide 55 — Hook · Domain Admin → ? (Alex, hand-off entry)
**Status**: GOOD
**Existing**: Slide 1 — Hook / 接手 | 0:45 (0:00 - 0:45) — 接續另一位講者「拿到 Domain Admin」的結尾，反轉敘事：DA 不是終點，是入場券。clicks 1: 「Domain Admin」變紅；2: 「→ ?」浮現橘色。

---

### Slide 56 — Terrain Shift (Alex)
**Status**: GOOD
**Existing**: Slide 2 — Terrain Shift | 1:00 (0:45 - 1:45) — 讓觀眾意識到：DA 在 2026 年現代企業 = 跨進雲端的入場券。台灣 80%+ 企業是 hybrid。Entra Connect 是雙向通道。

---

### Slide 57 — C5ISR Extended (Alex)
**Status**: GOOD
**Existing**: Slide 3 — C5ISR Extended | 1:30 (1:45 - 3:15) — 延伸前段講者建立的 C5ISR 框架到雲端。同一套指揮架構，戰場從機房延伸到雲端。

---

### Slide 58 — Cloud OODA Tested · flAWS demo (Alex) ⭐ 核心 1
**Status**: GOOD
**Existing**: Slide 4 — Cloud OODA Tested | 2:00 (3:15 - 5:15) ⭐ 核心 1 — 替換為真實 SSRF demo recap。flAWS.cloud Level 5 跑通的 log。這是全場唯一「跑過的真實證據」— 必須用真截圖 + 真 Orient JSON。TODO（演講前要補的素材）：在 Orient JSON 區塊上方加 War Room timeline 截圖；確認 Orient JSON 是 log 撈出來的真實內容（不是改寫的）。

---

### Slide 59 — Blast Radius (Alex) ⭐ 核心 2
**Status**: GOOD
**Existing**: Slide 5 — Blast Radius | 1:30 (5:15 - 6:45) ⭐ 核心 2 — 從一個入口到全戰場 — 視覺化「核彈」當量。

---

### Slide 60 — In the Wild (Alex)
**Status**: GOOD
**Existing**: Slide 6 — In the Wild | 1:00 (6:45 - 7:45) — 證明這不是 lab 演練，是 2023-2025 真實發生的事。

---

### Slide 61 — Three Questions (Alex)
**Status**: GOOD
**Existing**: Slide 7 — Three Questions | 1:30 (7:45 - 9:15) — 給防禦方三個 takeaway，呼應演講主題的戰略高度。

---

### Slide 62 — Closing (Alex, hand-back)
**Status**: GOOD
**Existing**: Slide 8 — Closing | 0:45 (9:15 - 10:00) — 英文 setup + 中文 kicker，最後一擊。
**Note**: 此頁是 Alex 的 closing。需要 Alex/Harry 確認是 Alex 直接收場交回給 Harry 講 lessons，或 Harry 上台後接 slide 63。建議：Alex 念完「是視野的擴張」後簡短說「現在交回 Harry 收尾整場心得」。

---

### Slide 63 — Lessons Learned (Harry, post-handback)
**Status**: WEAK
**Existing**: `Slide 55 from Harry's PPT — Ch6 · Lessons Learned (三個戰場心得)`
**Suggest**:
> 1 min 30 sec. Harry 上台接回。三條：強密碼不夠 / ADCS 是 AD 後門 / AI 把 1 天壓成 20 分鐘。
> 重點：呼應 Alex 剛才「視野的擴張」——把心得從「on-prem demo」延伸到「攻防不對稱已經改變」。
> Bridge: 「下一步往哪走？」（內文已寫）→ slide 64 roadmap。

---

### Slide 64 — Roadmap (Harry)
**Status**: WEAK
**Existing**: `Slide 56 from Harry's PPT — Ch6 · Roadmap (下一步 Roadmap)`
**Suggest**:
> 1 min. 四個前線：Multi-domain / Stealth tier / Persistence / Federated LLM。
> 重點：alert-box——「OODA 不是終點，是持續迭代的引擎」（slide 已寫）。提一句 Federated LLM 是給企業內部部署用的（敏感案件不出網域）。
> Bridge: 「跟現有 offensive AI 比怎麼樣？」→ slide 65。

---

### Slide 65 — Positioning · Athena vs Offensive AI (Harry)
**Status**: WEAK
**Existing**: `Slide 57 from Harry's PPT — Ch6 · Positioning (Athena vs 現有 Offensive AI)`
**Suggest**:
> 1 min 30 sec. 三條：PentestGPT 是 prompt loop / Nebula 是 RAG + 固定工具 / Athena 是 OODA×C5ISR + PostgreSQL state + AUTO_FULL。
> 重點：bridge——差別不在「用 LLM」，在於把軍事 doctrine 變成可執行系統（內文已寫）。
> Bridge: 「最後三條鼓點再敲一次」→ slide 66 refrain。

---

### Slide 66 — Refrain · Three Doctrines (Harry)
**Status**: WEAK
**Existing**: `Slide 58 from Harry's PPT — Ch6 · Refrain (三條信條 · 整場簡報的鼓點)`
**Suggest**:
> 45 sec — 慢，重音。同 slide 4，但這次是 callback：FACT-DRIVEN / DOCTRINE BEATS TOOLS / TEMPO IS THE WEAPON。
> 重點：「你已經聽完整場——但記得的應該只有這三條」（slide 已寫）。三條信條第三次出現（Prologue / 第 28 張 30× / 這裡）。
> Bridge: 進 closing。

---

### Slide 67 — Closing · AI 不會取代紅隊 (Harry)
**Status**: WEAK
**Existing**: `Slide 59 from Harry's PPT — Ch6 · Closing (AI 不會取代紅隊)`
**Suggest**:
> 45 sec — 慢，眼神接觀眾。「AI 不會取代紅隊」停頓兩秒、「AI 會把紅隊速度乘上 30 倍」念重。
> 重點：三條 callback：doctrine beats tools / fact-driven, not vibe-driven / tempo is the weapon。整場最高潮收尾。
> Bridge: 「Q&A」→ slide 68。

---

### Slide 68 — Q&A (Harry + Alex)
**Status**: WEAK
**Existing**: `Slide 60 from Harry's PPT — Q&A`
**Note**: TODO contact info for both speakers (placeholder in slide).
**Suggest**:
> ~5-8 min for actual Q&A. 開場 10 sec 提示——「歡迎挑戰任何架構假設、攻擊細節、武器化路徑」（slide 已寫）。
> 重點：Harry 處理 on-prem / OODA / MCP 問題，Alex 處理雲端 / hybrid identity / SSRF 問題。事先講清誰接哪類。
> 演講前必補：兩人 contact（email / GitHub / Twitter 擇一），避免空白被觀眾發現。

---

### Slide 69 — Thanks (Harry + Alex)
**Status**: WEAK
**Existing**: `Slide 61 from Harry's PPT — Thanks`
**Suggest**:
> 15 sec. 大字 THANK YOU + 謝謝大家，雙人站定鞠躬。
> 重點：不要再加新內容——讓觀眾鼓掌，下台前最後一個畫面是兩個人的合影。
> Bridge: end of deck.

---

## Quick wins for演講前

1. **Slide 3** — Alex 的 bio 三點 + 照片 + Cheehoo Labs 職稱（MISSING，必補）。
2. **Slide 58** — 確認 War Room timeline 截圖 + Orient JSON 是 log 真實撈出來的（Alex 已標 TODO）。
3. **Slide 68** — 兩位講者 contact 資訊（兩處 TODO placeholder）。
4. **Hand-off rehearsal** — Slide 54→55 與 62→63 的兩個 hand-off 點建議走過至少兩次，確保講者銜接無冷場。

## 各章節時間分配對照（self-check）

| 章節 | Slide 範圍 | 估計時長（總和上面建議） | Agenda 預設 |
|------|-----------|-------------------|---------|
| Cover + Speakers + Prologue | 1-4 | ~3 min | (含在 ch1) |
| Ch1 Tradition | 5-8 | ~3 min | 5 min |
| Ch2 Doctrine | 9-13 | ~5 min | 6 min |
| Ch3 Architecture | 14-20 | ~7 min | 10 min |
| Ch4 Framework | 21-28 | ~8 min | 8 min |
| Ch5 Operation | 29-54 | ~16 min | 15 min |
| Alex cloud demo | 55-62 | 10 min（Alex 已分配） | (Alex's section) |
| Ch6 After Action + Q&A + Thanks | 63-69 | ~10 min | 6 min |
| **總計** | | **~62 min** | ~50 min |

> 估計總長超過 agenda 約 12 分鐘——演講前需要修剪。建議：
> - Ch3 architecture（slide 14-20）每張砍 15-20 sec → 省 ~2 min
> - Ch4 framework（slide 21-28）每張砍 15 sec → 省 ~2 min
> - Ch5 demo 中性的 OPS LOG 揭示頁（slide 36/40/50）每張砍至 30 sec → 省 ~2 min
> - Q&A 預留 5 min（slide 68）而非 8 min → 省 ~3 min
> - 上述合計可省 ~9 min，落到 ~53 min，貼近 agenda 50 min 預設。
