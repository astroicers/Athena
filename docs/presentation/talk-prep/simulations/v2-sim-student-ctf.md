# v2 模擬聽眾回饋 — 資安系大四 / CTF 玩家

**版本：** v1 deck (2026-05-06)
**模擬日期：** 2026-05-06
**場景：** CYBERSEC Taiwan 2026 30-min Breakout Session

## Persona Profile

我是某私立大學資工系資安組大四生，22 歲，資安社副社長。HTB 學生會員，大概打到 Hacker rank（10 個 retired easy + 5 個 medium），玩過 PicoCTF / AIS3 EOF / HITCON CTF。同學七成在投 Google / 蝦皮的 SWE，我比較想做紅隊。自費學生票來 CYBERSEC，目標：找暑假實習、看業界在做什麼、蒐集 keyword 回去 google。

## 回饋表

| 項目 | 評分 | 說明 |
|------|------|------|
| **A. 整體印象** | 9/10 | 整場我又興奮又焦慮 — 興奮是因為 AS-REP / ADCS ESC1 我有 HTB 經驗，我看得懂；焦慮是因為這 18m57s 我自己手刻大概要 5 天起跳，差距太大。 |
| **B. 內容深度** | 8/10 | Harry 段對我這種程度剛好踩在「跟得上 + 有挑戰」的甜蜜點。Alex 段雲端那塊我學校沒教，但有 web 課的 SSRF 底，勉強跟得上。 |
| **C. 簡報節奏** | 7/10 | Slide 13-20 的 engine internals 太密，我抄筆記都來不及，有點跟丟。但 OPS LOG 的 timeline 設計超讚，我看得懂每一步在做什麼。 |
| **D. 實用性 / 可帶走** | 9/10 | 我會帶走一整本筆記。Athena 是不是 open source 是我今天最想知道的事。 |
| **E. 推薦給同學** | 強推 | 會推給我們資安社想做紅隊的學弟妹，但會警告：「OODA / C5ISR 那段聽不懂沒關係，先把 AS-REP / ADCS 看懂就有夠」。 |
| **F. 最讓我興奮的時刻** | — | Slide 41 AS-REP 原理 → Slide 45 ADCS ESC1 → Slide 48 da_alice 拿到 DA。這三張是我整場最有反應的時候 — 「這就是 HTB 上面的 Forest / Sauna 嘛！但他自動了！」 |
| **G. 跟丟的時刻** | — | Slide 17 composite confidence 那條 `(LLM × validation × history)^(1/3)` 的公式 + Brier score 0.31 → 0.12 那段。我有偷瞄旁邊的人 — 也在皺眉，稍微鬆一口氣 QQ。Slide 24 ORIENT 的「8 SECTIONS 輸入」我也跟丟了一點。 |
| **H. 跟資安社夥伴怎麼講** | — | 「靠這也太強，我看完想直接放棄手刻 nmap 腳本。Athena 把 HTB 那種 retired AD machine 整條 chain 自動跑完，從 RCE 一路到 secretsdump，20 分鐘。我們社團要不要 fork 來玩？」 |

## 詳細分析

### 我跟得上的比例（誠實估）

大概 **65%** 完全跟上、**25%** 硬撐、**10%** 直接放空。

**完全跟上的部分（我懂）：** Chapter 1 傳統 kill chain（slide 6-7，因為我 HTB 跑過）、Chapter 2 OODA 概念（slide 12，Boyd 我聽過名字）、Chapter 5 整段實戰 demo（slide 35-54，這就是我的舒適圈，AS-REP / ADCS / secretsdump 我都知道是什麼）、三條信條（slide 4, 58）、Alex 的 SSRF→IMDS（slide 56 的 `web_http_fetch`，這是 web 課教的）、Slide 65 vs PentestGPT 比較（這幾個工具我都聽過名字）。

**硬撐的部分（聽不太懂但用力跟）：** Slide 13-17 engine internals — 特別是 `composite confidence = (LLM × validation × history)^(1/3)` 跟 Laplace smoothing 那行 `(success+1)/(total+2)`。我知道這是貝氏統計，但我大三選修統計只記得貝氏定理長什麼樣，這套校正設計我想回去查 Brier score 是什麼。Slide 20 prompt injection via MCP description 我覺得超酷但需要再讀一次。

**直接放空的部分：** Slide 32 失敗模式（advisory lock 那個 trade-off 我不在意，我又不會去 deploy 這套）、Alex slide 6 的 Storm-0558 / Midnight Blizzard / Volt Typhoon（我有聽過名字但完整脈絡不熟，APT 不是學校會教的）、Alex slide 7 給 SOC 的三問題（我又不是 CISO，這跟我關係不大）。

### 我會回去 Google 的 keywords（學習筆記）

整場我筆記本寫滿，回去要查的 keyword：

1. **MCP (Model Context Protocol)** — 17 個 server 那個協定到底是什麼，跟 LSP 一樣嗎？這是核心。
2. **OODA loop（軍事原版）** — Boyd 的原始論文，韓戰 F-86 vs MiG-15 真的 10:1 嗎？
3. **C5ISR** — 軍事 doctrine，我想知道為什麼這個能套到 LLM。
4. **Brier score / Laplace smoothing** — slide 17 那條公式，我大三統計沒教。
5. **composite confidence calibration** — LLM 校正方法，畢業專題可能用得到。
6. **AS-REP Roasting + `DoesNotRequirePreAuth=True`** — HTB 打過但不是非常熟，要回去重做 Forest。
7. **ADCS ESC1〜ESC11** — slide 45-47 講的 `Enrollee Supplies Subject` + `Client Authentication EKU`，這個我只聽過 ESC1，原來還有 ESC11。
8. **certipy（工具）** — 我之前都用 mimikatz / impacket，certipy 是新的我要裝起來。
9. **PKINIT** — slide 48 用 PFX 換 TGT 的協定，Kerberos 進階內容。
10. **Hybrid Identity / Entra Connect / AD FS / PTA** — slide 56 講的雲端介接層，學校沒教，要補。
11. **IMDS SSRF (cloud.aws.imds_role)** — Alex slide 4 的真實 log，我要去 flAWS.cloud 跑跑看。
12. **PentestGPT / Nebula / AutoAttacker** — slide 65 提到的同類產品，找 paper 來讀。

### 我會問講者的 3 個問題

**Q1：Athena 是 open source 嗎？學生 / 個人能 fork 來玩嗎？**
我看到 GitHub 上的 Athena log JSON（slide 56 那個 `rec_id 00e38a61`）— 想知道這套是不是公開的，可不可以拿去學校 lab 跑。如果不是 OSS，有沒有授權給學生 / 學術研究的方案？

**Q2：學生想入門 AI 紅隊，prerequisite 是什麼？怎麼學？**
我現在 HTB Hacker rank、會基本 AD pentest，但 OODA + LLM + MCP 這套技術棧我完全沒碰過。建議的學習路徑是什麼？要先學 LangChain / agent framework 嗎？還是先把 Kerberos / ADCS 內功打深？

**Q3：Cheehoo Labs / 網路中文資訊有徵實習嗎？我能投嗎？**
（這個其實是想去問 Alex 老師的，我想下台之後找他）

### 為什麼 A / B / C / D 是這個分數

**A 整體印象 9/10** — 整場節奏 demo 段超抓得住我，三條信條（slide 4）那種 doctrine framing 直接擊中我這種愛玩 framework 的學生。扣 1 分是因為 slide 17 composite confidence 那段我跟丟，會讓我懷疑自己是不是程度不夠。

**B 內容深度 8/10** — 我這種大四已修過滲透測試 + 有 HTB 底子的程度，剛好可以跟 Harry 段，又有 Alex 段拓展視野。對我同學那種純前後端的會太硬，但對我剛剛好。扣分是因為某些段落（engine internals）對我這個程度還是太深。

**C 簡報節奏 7/10** — OPS LOG 設計超強，每一張投影片右邊都有 timestamp，我看得到「20:54:08 → 21:14:02」整個攻擊鏈的時間線，這個視覺敘事我整場都跟得上。但 slide 13-20 那 8 張 architecture 太密、太多新名詞（MCP、Orient JSON、engine_router、advisory lock），我抄筆記抄到手痠還是有跟丟感。

**D 實用性 9/10** — 我會帶走一整本筆記。AS-REP / ADCS / certipy 這些可以直接拿去 HTB 實作。Athena 三條信條我會記到畢業專題去。

### Harry 段我的感受

**興奮的部分（我懂！）：** slide 41 AS-REP Roasting 出來的時候我直接坐挺起來 — 這就是我在 HTB 打 Forest / Sauna 那種感覺！`DoesNotRequirePreAuth=True` → `impacket-GetNPUsers -no-pass` → `hashcat -m 18200`，我連指令都背得出來。然後 slide 45 ADCS ESC1 的「Enrollee Supplies Subject + Client Authentication EKU + Low-priv enroll」三條件 AND 邏輯，我以前只聽過 ESC1 名字沒實戰過，這次看完原理超清楚，回去要在我的 lab AD 環境試一次。slide 48 拿到 da_alice TGT 那一瞬間我心裡 OS：「這就是城堡鑰匙啊」。

**跟得上但用力的部分：** Chapter 4 framework 的 OODA × C5ISR 對映表（slide 22-27）我覺得設計很美，但我會懷疑這是不是有點過度包裝？OODA 我懂、C5ISR 我懂概念，但兩個 framework 強行對映有沒有比直接寫成 pipeline 好？這個我內心打了問號但沒辦法在現場驗證。

**直接跟丟的部分：** slide 17 composite confidence 拆解。`validation_score = 0.5 × exit_ok + 0.5 × (new_facts > 0)` 我懂，但 `(LLM × validation × history)^(1/3)` 我反應慢半拍 — 為什麼是幾何平均不是加權算術？我抬頭看了一下右邊那位學長，他也在皺眉，鬆一口氣（不是只有我）。Brier score 0.31 → 0.12 我直接記下來回去 google。

承認啦，整段 Harry 我大概懂 60-70%。

### Alex 段我的感受

**Alex slide 1（Domain Admin → ?）我嚇一跳。** Harry 剛剛才講完拿到 DA，slide 1 直接打臉「DA 不是終點，是入場券」— 這個轉場好戲劇性，我心裡 OS：「對欸，HTB 我每次拿到 DA 就 submit flag 走人，但真實企業才剛開始。」這個敘事 hook 我會記得。

**SSRF→IMDS（slide 4）對我比較陌生但有底。** 我修過雲端安全選修，知道 IMDS 是 EC2 metadata service，知道拿到 169.254.169.254 那條 URL 就能撈 IAM credentials。但完整 SSRF→IMDS chain 加上真實 Orient JSON 那段（`evidence_refs: ["web.vuln.ssrf", "cloud.aws.imds_role"]` + confidence 0.95）我看到的瞬間真的覺得：「靠這是真的 log 不是 demo」。我會去 GitHub 找 Athena 是不是 open source 就是因為這張投影片。

**hybrid identity / Storm-0558（slide 6）放空。** Storm-0558 / Midnight Blizzard / Volt Typhoon 我都聽過名字（Volt Typhoon 是 CISA 那個跟台海相關的對吧），但完整事件脈絡 + Entra Connect / AD FS / PTA 那些雲端介接層我學校沒教過，這段我邊聽邊打開手機 google「Volt Typhoon LOTL」。Alex slide 7 給 SOC 的三個問題我覺得很好但跟我無關 — 我不是 SOC manager，我只是個學生。

### 給未來自己的話 / 對講者的感謝

回去後我要做三件事：(1) 把今天 12 個 keyword 全部 google 一輪；(2) 在我的 lab AD 環境完整跑一次 AS-REP → certipy → secretsdump 鏈；(3) 想辦法找到 Athena 的 GitHub repo 看能不能 fork。

對 Harry 的感謝 — 你讓我看到「我會的東西」（HTB 那些 AD 招式）原來可以被 AI 自動串成 18m57s 的 kill chain，這同時是震撼跟啟發 — 紅隊不會被取代，但要學會跟 AI 工作。對 Alex 的感謝 — 你那張「Domain Admin → ?」直接逼我意識到我在 HTB 學的東西在企業只是入場券，學校沒教的雲端 / 混合身分才是真正的戰場，謝謝你打開這個視野。

下台後我會去找 Alex 老師問實習。如果沒有也沒關係 — 至少我帶走一張地圖，知道接下來這 1 年要往哪走。
