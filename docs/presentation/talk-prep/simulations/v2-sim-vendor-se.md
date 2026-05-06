# v2 模擬聽眾回饋 — Vendor Solution Engineer（EDR/SIEM 廠商）

**版本：** v1 deck (2026-05-06)
**模擬日期：** 2026-05-06
**場景：** CYBERSEC Taiwan 2026 30-min Breakout Session

## Persona Profile

35 歲男，跨國 EDR/XDR/SIEM 廠商台灣分公司 SE 五年，前 SOC analyst 三年。每週跑 5–8 場 demo / PoC，金融、政府、製造、半導體都做。公司今年 KPI 是 AI 主題的 new logo，老闆塞了三張 ticket 來 CYBERSEC：(1) 撈 sales ammo、(2) 看客戶 pain points、(3) 偵察競品 framing。Athena 這場是我這天圈起來必聽的 — 30 分鐘 / AI agent / 軍事 doctrine / Kill chain demo，題目本身就是下季 sales deck 的 raw material。

## 回饋表

| 項目 | 評分 / 回答 |
|------|----------|
| A. 整體滿意度 | **4.5/5** |
| B. 學到新東西 | **3/5**（技術不是新東西，但 framing 整套換掉我的 pitch 結構） |
| C. 跟我有關 | **5/5**（這就是下季 sales deck 的 raw material） |
| D. 回去會行動 | **5/5**（明天回 office 就改 battlecard + briefing） |
| E. 一句話回饋 | 「TEMPO 30× 跟『doctrine beats tools』下週開始進我的每一場 client briefing。Athena 的存在剛好幫我把『為什麼要買 AI-powered EDR』的故事說完。」 |
| F. 我會抄走的 framing | (1) 三條信條（fact-driven / doctrine beats tools / tempo is the weapon）— 直接套到我家的 marketing。(2) 「20 分鐘 / 3 of 3 / 0 人工介入」這個 metric tile 結構，跟我家 MTTD/MTTR 對打。(3) Slide 65 的 Athena vs PentestGPT/Nebula 對比表 — 這個 framework 我自己 battlecard 也會抄，把「framework / state / auto」三欄拿來比競品。(4) Slide 5 攻擊路徑 6 chapter agenda 那種「Mission Briefing」軍事 framing — CISO 喜歡這味。(5) Alex slide 61 三個 defender 提問 — 客戶教育素材直接拿走。 |
| G. 最想滑手機時刻 | Slide 17 composite confidence 數學公式 + Brier score。客戶不會問這個，講者花了一張 slide 講 Laplace smoothing 我幾乎要把手機拿出來。Slide 19/20 engine_router 跟 schema sandbox 那兩張我也是 zone out — 對銷售沒幫助，我不需要懂 LLM 怎麼選工具。Slide 45–47 ADCS ESC1 三條件那組我也是放空 — 我家 product detection 早就 cover ESC1 family，不需要再上一次課。 |
| H. 我下個月怎麼用這場 | (1) **Battlecard 改寫**：把 Athena 放進「next-gen offensive AI」象限，定位它是 attacker side 的 reference point，凸顯我家 defender side 為什麼是必需品。(2) **CISO briefing slide 套版**：把「AI 紅隊把 1 天壓成 20 分鐘」當 hook，接上「我家 AI detection 把 dwell time 從 X 天壓到 30 秒」做對戰公式。(3) **三個 Storm-0558 / Midnight Blizzard / Volt Typhoon** 的 case study 直接抄進我家 quarterly threat briefing — 這幾個 case 我家 marketing 文件目前散在各報告，第一次看到有人 30 秒講完三個。(4) **RFP response template** 加新題：客戶問「你家偵測得到 AS-REP roasting / ADCS ESC1 / SSRF→IMDS pivot 嗎」我得備好 demo + screenshot。 |

## 詳細分析

### 我會 screenshot 的 5 張投影片 + 為什麼

1. **Slide 4（三條信條 prologue）+ Slide 58（refrain）** — 同一組 punchline 開場 + 結尾各打一次，把整場 talk 結構鎖死。我下季 sales deck 三章節結構也要這樣搞：page 2 開三句、最後一張回三句。CISO 級的 audience 吃這套。
2. **Slide 28（TEMPO 30× 大字）** — 直接 screenshot 進 client briefing 第一頁。「速度差 30 倍不是更快，是換了一個維度」這句話本身就是 selling line — 客戶下季預算 review 時老闆問「為什麼要花這個錢」，這張 slide 比我寫一頁 RFP 有效。
3. **Slide 54（Mission Complete tile：20 min / 3 of 3 / 0 / 100%）** — 這個 4-tile metric layout 是我的 sales 視覺武器。客戶問「你家擋得住這 20 分鐘嗎」我要立刻拿出對應的 4-tile：dwell time、coverage、auto-response、explainability。對打公式直接成形。
4. **Slide 60（三個 APT cases — Storm-0558 / Midnight Blizzard / Volt Typhoon）** — AI 威脅 case study。我家公司 marketing 的 quarterly threat report 之前一張 slide 塞五個 incident 模糊不清，這個 3-column 結構（年份 + 受害 + 攻擊手法）我直接抄。Volt Typhoon 那句「CISA 評估與台海衝突相關」對台灣金融客戶是 cold sweat moment — 我會放第一頁。
5. **Slide 65（Athena vs PentestGPT vs Nebula 對比）** — 對我來說這是 battlecard 教學示範。三欄：framework / state / auto。我家對抗 CrowdStrike / Microsoft Defender 的 battlecard 之前是亂寫一通，這個 3-row × 3-col + 一行 code-style 標註的格式，我下週 battlecard refresh 直接套。

### 我會抄進 sales deck 的 framing

1. **「Doctrine beats tools」** — 這是我見過最好的 anti-feature-checklist 攻擊。客戶最常 RFP 比 feature checkbox，但我們家其實工具沒比 CrowdStrike 多，輸的是視野不夠高。把「doctrine beats tools」翻譯成我家 pitch 就是「detection rules beat tool count」— 客戶不該比 EDR 工具數量，該比 detection doctrine 完整度。明天上去就改我的 elevator pitch。
2. **「30× 速度差不是更快，是維度差」** — 這句話我會抄成 mirror version：「我家偵測從天到秒不是更快，是治理維度的轉換」。配上 MTTD 數字直接打 PO。
3. **「Fact-driven, not vibe-driven」** — Slide 59 closing 那段三行排比結構。我家 detection rule 很多客戶覺得「不就是 SIEM signature 嗎」，我可以借這個 framing 講「我家 detection 是 fact-driven correlation，不是 vibe-driven keyword match」。
4. **Mission briefing 軍事語氣全套** — eyebrow tag「// OPERATION ATHENA-XXX」+「:: CLASSIFIED」+ 倒數時間 stamp。我家下季的 incident response demo 我會偷這個視覺風格 — 一樣是看 log，包成 SOC War Room 戰情室就比較好賣，CISO 聽得進去。

### 我家產品的 sales angle 因為這場 talk 變成什麼

聽完這場 talk 我下季 pitch 重組成兩段：**「攻擊端的 tempo 已經被 AI 拉到 30×（用 Athena 當 reference）」→「你家 detection / response 的 tempo 跟得上嗎？」**。這是一個從攻擊面焦慮反推防守面 PO 的標準 sales motion，但 Athena 這場 talk 把攻擊端的故事第一次講得這麼乾淨 — 之前我用 Mandiant M-Trends 報告講 dwell time，太抽象。現在我有一個 20 分鐘的具體 number，搭配 AS-REP roasting / ADCS ESC1 / SSRF→IMDS 三個 attack vector 客戶聽得懂的故事。

我家對抗 Athena 這種威脅的 selling point 我會這樣包：(1) **AD telemetry depth**：AS-REP roasting / ADCS ESC1 / Kerberos abuse 我家有 detection rule 全 cover，demo 時我會直接放 alert 截圖；(2) **identity correlation**：Slide 60–62 Alex 講混合身分那段是我家最強的 differentiator — 我家 XDR 把 AD + Entra ID + M365 + cloud 拉成一張 graph，這就是 Alex 第二個 defender 提問的答案；(3) **MDR auto-response**：Athena 30s OODA loop 對我家就是「auto-isolation < 30s」的 mirror — 我家有 auto-isolate 動作，賣 SLA 我直接打 Athena 的時間軸。

但 talk 也讓我警覺一件事 — Athena 如果開源（沒查到 license），紅隊客戶 PoC 會大量採用，這會壓低我家 red team simulation module 的價值。我得回去問 product team Athena 的 release plan，如果是商業化 SaaS 那是合作機會（我家可以做 detection content for Athena），如果是 open source 那 marketing 要重新定位。

### 客戶聽完會問我什麼

1. 「你家 EDR 偵測得到 AS-REP roasting 嗎？Kerberoast 呢？」— 我得備好 detection rule + Sigma signature + alert screenshot 三件組。
2. 「ADCS ESC1〜ESC11 你家 cover 哪幾條？」— 這題我得回去抓 product team 的 ADCS detection coverage matrix，比照 Athena slide 47 三條件做對應。
3. 「Athena 是不是開源？我們紅隊能不能拿來做 internal pentest？」— 這題答不好客戶會問「那我為什麼要買你家紅隊模組」。我得備好 Athena vs 我家 BAS（Breach and Attack Simulation）的差異化說法。
4. 「30 秒 OODA loop 我家 SOC 跟得上嗎？我家 alert 一天 2000 條，30 秒一個攻擊步驟我們根本看不過來」— 這是 MDR 的 PO 入口，我得把對應的 auto-response SLA 拉出來。
5. 「混合身分這段 Alex 講的 Storm-0558，我們也是 hybrid identity，要怎麼防？」— 這是 identity-centric SOC 的 pitch 機會，我得把 Entra ID + AD 雙向 correlation 的 demo 路徑備好。

### 為什麼 A / B / C / D 是這個分數

**A. 4.5/5** — 對 SE 來說這是上半年最有 ROI 的 30 分鐘。三條 punchline、四個 metric tile、一個競品對比表 + 三個 APT case study — 我帶走的素材夠我做一整季 client briefing。扣 0.5 是因為中間 engine 內部三張（confidence 數學 / engine_router / schema sandbox）對我太深，我意識到這不是給我聽的就放空了，但講者沒在那邊停太久 — 算過得去。

**B. 3/5** — 技術上我沒學到新東西。AS-REP roasting / ADCS ESC1 / SSRF→IMDS / secretsdump 這些我做 SOC analyst 時就 alert 過很多次。LLM + MCP 那套我大概知道是 wrapper 邏輯。但 framing 給我的價值遠大於技術 — 把這些技術重新包裝成「軍事 doctrine + tempo」這個故事，這就是新東西，所以給 3 不是 2。

**C. 5/5** — 這就是我來 CYBERSEC 的目的。下季 sales deck、客戶教育材料、battlecard、RFP response 全部都會用到這場 talk 的素材。對 vendor SE 來說 100% 直接 actionable。

**D. 5/5** — 明天回 office 第一件事：抄 battlecard 結構、改 elevator pitch（doctrine beats tools 角度）、把三個 APT case 進 quarterly briefing、把 Athena 加進競品掃描清單。下週要跟金融客戶 CISO 開會，三條信條的開場我已經想好怎麼套。

### Harry 段 / Alex 段對我的商業價值對比

對 sales 角度兩段價值很不一樣。**Harry 那 20 分鐘對我的 sales motion 價值最高 — slide 4、28、54、58、65** 是我整場最重的 5 張，全部來自他。三條信條、TEMPO 30×、Mission Complete metric tile、競品對比表 — 這幾張就是我下季 deck 的骨架。Harry 講的故事是「攻擊端發生了什麼」，這是 sales 鋪 PO 的前 10 分鐘必備內容。20 min / 3 of 3 / 0 人工 這組數字本身就是一個完整的 sales hook。

但 **Alex 那 10 分鐘對我的「PO closing」階段價值更高**。Slide 60 的三個 APT cases、slide 64 的 cross-cloud blast radius、slide 67 的三個 defender 提問 — 這些是把客戶從「焦慮」推到「該買什麼」的 closing material。Alex 那段「DA 不是終點，是入場券」+「混合身分」是 identity-centric SOC sales 最直接的入口 — 我家 XDR 賣 identity correlation 之前一直靠 Microsoft 自己的文件，這場有了第三方視角的攻擊路徑，sales motion 就完整了。

Bottom line — Harry 段給我「sales hook + 視覺武器 + battlecard 框架」，Alex 段給我「PO closing + APT 真實案例 + 客戶教育問題」。兩段加起來才是完整的 sales journey。如果 only 30 分鐘只能聽一段，我會挑 Harry，因為 hook 沒鋪好客戶不會聽到後面 — 但 Alex 那 10 分鐘的 actionable closing material 對 RFP 階段 vendor 的轉換率比 hook 還關鍵。
