# v1 模擬聽眾回饋 — 資安顧問

**版本：** v1 (2026-05-06 deck)
**模擬日期：** 2026-05-06
**場景：** CYBERSEC Taiwan 2026 30-min Breakout Session

## Persona Profile

12 年資安顧問經驗，台北本土資安顧問公司資深顧問。客戶橫跨金融、製造、政府、新創。產出形式是**報告**——客戶簡報用的 deliverable，不是技術交付。會議室裡用的是董事會語言，不是 BloodHound graph。來 CYBERSEC 是為了找下季 sales pitch 的 punchline、收集威脅建模素材、評估自己的 pentest 服務要不要升級成「AI-augmented」、看別人怎麼包裝。

## 回饋表

| 項目 | 評分/回答 |
|------|----------|
| A. 整體滿意度 | 4/5 |
| B. 學到新東西 | 3/5 |
| C. 跟我有關 | 4.5/5 |
| D. 回去會採取行動 | 4.5/5 |
| E. 一句話回饋 | 「中間引擎那段我放空了快五分鐘，但 Slide 4、Slide 28、Slide 54、Slide 60 這四張我下個月給金控董事會的 briefing 直接抄。三條信條當開頭、30× 當衝擊、Mission Complete tile 當 closer、Volt Typhoon 當 threat case。一場 talk 我帶走四張可以直接放進 sales deck 的素材，CP 值很高。」 |
| F. 最記得的一件事 | Slide 28 那個 30× 的瞬間。整張投影片只有一個數字、一句英文 punchline「TEMPO IS THE WEAPON」、一句中文註解。我馬上拿手機拍照，因為這就是董事會語言——數字大、訊息單一、不用解釋技術。我每次跟金控 CISO 簡報「為什麼我們現在的 IR retainer 不夠用」最缺的就是這種一張投影片講完一個 punchline 的設計。Harry 設計這張的時候顯然是給「會場最後一排在滑手機的 CTO」看的，而那剛好就是我每次提案要面對的對象。第二個記得的時刻是 Slide 54 的 Mission Complete tile：「20 min / 3 of 3 / 0 manual / 100%」四個格子。這四個數字是任何銷售簡報的黃金結構——時間、成功率、自動化、可解釋性。我已經在腦中把它改成「我們的 AI-augmented pentest：3 天 / 100% target coverage / 60% manual reduction / 100% report-ready」的版型。Harry 不知道他在幫我做 sales template，但他做了。 |
| G. 最想滑手機時刻 | 三段。最痛的是 Slide 17（0.87 怎麼算的）那段——composite confidence、Brier score 從 0.31 降到 0.12、Laplace smoothing、幾何平均。客戶不會看這個、不會問這個、我也不會在報告裡寫這個。那 90 秒我直接在筆記本上寫「跳過」。第二是 Slide 14-20 整段引擎內部（Orient JSON、Decision Engine 三道閥、動態路由、Schema sandbox）——對我來說這就是「CDK bootstrap version 那種等級的技術段落」，我知道它存在、知道它重要，但跟我下次去金控提案的對話沒有關係。第三段是 Slide 41-47 的 AS-REP + ESC1 連續七張投影片——AS-REP 一張原理 + 一張 hash 取得 + 一張 OPSEC + 一張 hashcat = 四張；ESC1 一張原理 + 一張 certipy req + 一張三條件 = 三張。我在心裡狂想：「拆 1-2 張就好，何必七張？」我的初級顧問會看這些細節，我不會。 |
| H. 同事問怎麼回答 | 「兩個講者、30 分鐘、地端 AD 加雲端 SSRF。Harry 的部分是把軍事 doctrine（OODA、C5ISR）包裝成 AI 紅隊的 framework，配 17 個 MCP 工具、跑了一場 20 分鐘全自動 demo。Alex 的部分把 Domain Admin 接到 hybrid identity，講 SSRF→IMDS 怎麼跨進雲端。三條信條叫 FACT-DRIVEN、DOCTRINE BEATS TOOLS、TEMPO IS THE WEAPON——這三句口號客戶簡報會很好用。最有商業價值的不是技術內容，是它的包裝：大字、軍事比喻、War Room dashboard、Mission Complete tile。如果你要給董事會 brief『AI 紅隊在 2026 已經到什麼程度』，就直接抄 Slide 28 的 30×、Slide 54 的四個數字、Slide 60 三個 APT 案例（Storm-0558 / Midnight Blizzard / Volt Typhoon）。中間 doctrine 拆解的 6-7 張我跳過，那是給寫 code 的人看的，不是給董事會看的。」 |

## 詳細分析

### 我會拍照的 5 張投影片 + 為什麼

1. **Slide 4（三條信條 Prologue）+ Slide 58（Refrain）** — 同一張內容開場 + 收尾兩次出現，DOCTRINE BEATS TOOLS / TEMPO IS THE WEAPON / FACT-DRIVEN，三句英文口號加中文註解。我下季 pentest 服務升級的 sales pitch 開場直接用「武器庫人人有，差別在 doctrine」這句——把客戶的「你們不就是換個工具？」這個常見反駁直接堵住。
2. **Slide 28（TEMPO 30× 大字）** — 一張投影片只有一個數字。董事會 briefing 的標準範本，我會把這張的版型偷走——下次「我們的 AI-augmented pentest 把 6 週壓到 6 天」也要這樣做一張。
3. **Slide 54（Mission Complete 四格 tile）** — 20min / 3of3 / 0 manual / 100%。這就是 sales deck 第一頁。直接 screenshot 進我的金融客戶提案。「AI 紅隊不是 lab demo，是 20 分鐘真實 kill chain」——這句話我幫客戶威脅建模時可以直接用。
4. **Slide 60（三個 APT 案例 Storm-0558 / Midnight Blizzard / Volt Typhoon）** — 三個並列卡片、年份、一句話描述。我下個月金控董事會的 briefing 第二頁直接抄這個版型，把它換成台灣相關的 APT 案例。Volt Typhoon 那句「CISA 評估與台海衝突相關」客戶會買單。
5. **Slide 65（Athena vs PentestGPT/Nebula）** — 競品定位三段式：framework / state / auto。我自己服務升級時也要做一張類似的——「傳統 pentest vs AI-augmented pentest」對比表，讓客戶看到差異。

### 我下個月客戶簡報會抄的 framing

- **「Doctrine beats tools」**——這句話直接解決我每次被客戶問「你們的工具跟別家有什麼不同？」的尷尬。下次回答：「工具差不多，差別在 doctrine——我們有測試方法論、決策框架、量化的風險矩陣。」客戶不會反駁這個。
- **「30 倍速度不是更快，是換了一個維度」**——這是個好用的 frame。下次跟 CFO 解釋「為什麼 IR retainer 要漲價」的時候：「攻擊者已經從每天 5 步驟變成每分鐘 5 步驟，你的 SOC 還在用人類 tempo。30 倍不是優化問題，是維度問題。」
- **「DA 不是終點，是入場券」**（Slide 56）——這句話我可以拿來重新包裝我的雲端安全 review 服務。傳統客戶覺得「我地端有 IR、雲端有 IR，分開做就好」，這句話打破那個假設。

### 為什麼 A / B / C / D 是這個分數

**A = 4：** 整體流暢、視覺一流、敘事清楚，但中段 6-7 張引擎內部對我這種顧問來說是 dead weight。如果 Harry 把 Slide 14-20 拆成兩張高層次 + 一張延伸閱讀 QR code，我會給 5。

**B = 3：** 老實說 AS-REP Roasting / ADCS ESC1 / secretsdump 我都聽過——這就是過去 5 年中型企業滲透測試的標準教材。我的初級顧問每週都在跑這些。新東西其實只有一件：**把 OODA + C5ISR 兩個軍事 framework 接到 AI 紅隊的 framing**——這個 framing 我之前沒看過，扣 2 分是因為核心 attack technique 沒有新意。

**C = 4.5：** 雖然技術細節跟我距離遠，但**敘事框架直接命中我的工作**。三條信條、Mission Complete tile、APT 案例對比、競品定位——每一個都對映到我的 sales deck 結構。差 0.5 的原因是 Harry 沒有給我「顧問語言」的版本——他給的是工程師語言+董事會 punchline，中間少了一塊「給諮詢業務用的話術」。

**D = 4.5：** 走出去時我手上有四張可以直接抄的投影片版型、三個 framing phrase、一個「升級 pentest 服務成 AI-augmented」的 internal 提案動機。下週的客戶 review meeting 我可以直接用「你的紅隊能同時看到雲端 + 地端嗎？」（Slide 67）這個問題——這比我自己想的問法精準多了。

### Harry 段我的感受

**有用的部分：** Slide 4（三條信條）、Slide 7（每階段做什麼）、Slide 28（30×）、Slide 32（踩過的坑）、Slide 54（Mission Complete）。這五張是整段的精華。Slide 7 那張我特別喜歡——「偵察→突破 / 立足→橫向移動 / 收割資料」三段，客戶問「滲透測試到底在做什麼？」我以前都要講十分鐘，現在這張投影片三句話講完。我會直接抄進我的 onboarding 簡報。

**Slide 32 踩過的坑那張救了整段的可信度。** EDR 擋下 LSASS dump、Bloodhound 超時 partial facts、平行 race condition——這三個 failure mode 讓整場 demo 從「marketing 影片」變成「真的有人在跑這套」。我會在客戶 briefing 引用這張，因為它告訴董事會：「AI 紅隊不是 silver bullet，是會踩坑的真實系統。」這比 Mission Complete 的成功展示更有說服力，因為它證明這個系統不是 cherry-picked。

**dead weight 段：** Slide 14-20 引擎內部（Orient JSON / Decision Engine / 動態路由 / Schema sandbox）整整七張我都放空。Slide 17 那個 composite confidence 數學式（LLM × validation × history）^(1/3) + Brier score 從 0.31 降到 0.12——客戶不會問這個，我也用不到。這段在我看來是「給寫 code 的工程師看的炫技」，不是給聽眾看的價值。如果是給 CTO 聽的場我會說「這段 ok」，但 30 分鐘場合給混合聽眾，這 7 分鐘是奢侈品。

**Stage 1 的 AS-REP+ESC1 七張連發太重。** 我懂 Harry 想完整呈現 kill chain，但對顧問聽眾來說，AS-REP 一張原理 + 一張結果 = 兩張就夠了，ESC1 同理。現在四張+三張=七張，我大概第五張就在心裡 fast-forward。

### Alex 段我的感受

**Cloud pivot 這 10 分鐘對我的顧問業務超有價值。** 過去兩年我在金融客戶端最常被問的就是「我們地端 IR 做完了，雲端怎麼辦？」——這個問題我以前要分兩次提案、兩份報告、兩個 retainer。Alex 的核心 framing「DA 不是終點，是入場券」直接把這個拆解打掉，變成一個 unified threat narrative。**這個 framing 我下季提案直接用。**

**Slide 60（三個 APT 案例）是整段最商業化價值的一張。** Storm-0558（2023）、Midnight Blizzard（2024）、Volt Typhoon（2024-25）——三個都是公開可查的 APT，三個都跨地端+雲端，三個都用混合身分當跳板。我下個月給金控董事會的 briefing 第二頁直接抄這個版型，因為金控董事會就吃這套：「這不是學術，是真實事件。」Volt Typhoon 那句「CISA 評估與台海衝突相關」對台灣金融客戶特別有共鳴——他們最近被金管會問這個問了不下十次。

**Slide 67（三個防禦問題）是「給管理階層用的問題」。** 「你的紅隊能同時看到雲端 + 地端嗎？」「你的 SOC 是否把憑證與 token 路徑當作同一張圖？」「AI 攻擊者的速度——你的事件應變跟得上嗎？」這三個問題用的是 governance 語言，不是技術語言。我會把這三個問題直接帶進下週金控的 SOC 評估會議。

**遺憾：Slide 64（flAWS.cloud Orient JSON）那段我放空了。** Alex 顯然把這個 JSON 當成「全場唯一可 fact-check 的真實證據」，但對我來說，rec_id / ooda_iteration_id / evidence_refs / 0.95 confidence 全部是工程師細節。我不會 fact-check 這個——客戶也不會。這張投影片如果改成「我們在公開的 lab 環境跑了一次，全程 X 分鐘，全程零人工」配合一張 Athena dashboard 截圖，對顧問聽眾的衝擊會更強。

### 一個我希望這場 talk 多花時間的 — 一個我覺得太多時間的

**多花時間：Slide 32（踩過的坑）。** 現在只有三個 failure mode 各 80 字。我希望多花 1-2 分鐘展開——客戶最常問的就是「but what if it fails?」如果 Harry 多給 2-3 個失敗案例（例如「客戶環境有 SIEM 把我們的 nmap 全部擋下」「AI 推薦了一個過時的 CVE」），這場 talk 對顧問業務的可信度會再上一個量級。failure stories 是顧問的硬通貨，現在這場 talk 給太少。

**太多時間：Slide 14-20（引擎內部 7 張）。** 整整 7 張投影片講 Orient JSON 結構、Decision Engine 三道閥、composite confidence 數學、動態路由、Schema sandbox、prompt injection 防禦——這些放成 4 張 high-level + 一個 GitHub link 就夠。剩下 3-4 分鐘可以給更多 demo footage、更多 failure stories、更多 APT 案例延伸。對混合聽眾，這 7 張是奢侈品；對全工程師場合也許 ok，但 CYBERSEC 不是。
