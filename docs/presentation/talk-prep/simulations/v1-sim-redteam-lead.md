# v1 模擬聽眾回饋 — 資深紅隊隊長

**版本：** v1 (2026-05-06 deck)
**模擬日期：** 2026-05-06
**場景：** CYBERSEC Taiwan 2026 30-min Breakout Session

## Persona Profile

8 年 AD 滲透測試，現職紅隊組長，BloodHound + impacket + certipy + Mythic + Cobalt Strike 是日常工具，AS-REP roasting + ADCS ESC1 + secretsdump 串過幾十次。讀過 PentestGPT (Lin et al. 2024)、Nebula、AutoAttacker 論文，對 LLM-driven offensive AI 的論述強度有底。今天進來找兩件事：(1) 真的新東西、(2) 可以拿去客戶 engagement 包裝用的 framing。對 AI auto-pwn demo 天生懷疑，預設這場是 marketing 不是 research。

## 回饋表

| 項目 | 評分 / 回答 |
|------|-------------|
| A. 整體滿意度 | **3/5** |
| B. 學到新東西 | **2/5** |
| C. 跟我有關 | **3.5/5** |
| D. 回去會行動 | **2.5/5** |
| E. 一句話回饋 | "AS-REP + ESC1 我已經串過五十次，你串得快不重要 — 但 composite confidence 那條公式跟 dead_end fact 寫回 history 那段 framing 我會抄。剩下九成是給非紅隊的人聽的。" |
| F. 最記得的一件事 | **Slide 17（0.87 怎麼算）+ Slide 25（cooldown=30min）合起來。** 整場我唯一停下來抄筆記的地方。`composite = (LLM × validation × history)^(1/3)` 這條幾何平均不是新數學，但把它跟「Brier score 0.31 → 0.12」綁在一起講，是這場第一次讓我覺得 Athena 不是 prompt loop wrapper。Slide 25 的「失敗 fact 寫進 prompt + cooldown=30min」更狠 — 我 engagement 平常用 Notion 自己記 EDR 擋什麼、什麼 OPSEC 走不通，講者把這個變成系統的一部分而且還會自動解禁。這個架構我下次跟客戶 debrief 的時候會直接拿來解釋「AI 紅隊跟 prompt 紅隊差在哪」。但我必須說 — Brier score 200 輪樣本在 demo 環境，這個數字基本上是 marketing，真實環境跨 EDR、跨 AD 規模、跨 cooldown 時間窗 我絕對不信 0.12。所以這句是 framing 抄走，數字當沒看到。 |
| G. 最想滑手機時刻 | **Slide 41–48 整段（AS-REP roasting → hashcat → ESC1 → certipy auth）。** 7 張投影片講我冷啟動 30 秒就能畫白板的東西。Slide 41 的 KRB_AS_REQ padata 解剖、Slide 47 的 ESC1 三條件（Enrollee Supplies Subject + Client Auth EKU + low-priv enroll）— 這是 SpecterOps 2021 Will Schroeder 那篇白皮書的內容，我帶過三個 junior 都是用同一套教材。講者花了 8 分鐘鋪陳協議細節，這時間應該拿去講 AI 怎麼決定要走 ESC1 而不是 ESC4/ESC8、走錯路怎麼回頭。我滑了三次手機，旁邊那個藍隊朋友還在抄 Slide 47，我替他開心，但這段不是給我的。 |
| H. 同事問怎說 | "AD 那段你閉著眼睛都會。但有兩個東西可以抄：第一，他們把 LLM_confidence × validation × history_success_rate 取幾何平均叫 composite confidence，然後把 history Laplace smoothing 過。下次客戶問你『你怎麼知道 AI 不會幻覺』，這個 framing 比 prompt engineering 那套乾淨十倍。第二，他們把 attempt.failed 寫回 facts DB 還加 cooldown=30min，這是把紅隊的 lesson learned 系統化。Demo 本身是 lab 靶機加 5 個故意設定錯誤，沒啥好看的。但 Slide 65 跟 PentestGPT/Nebula/AutoAttacker 的對比表蠻誠實，他們承認那三個是 prompt loop 跟 RAG，自己是 OODA × C5ISR × MCP。你要寫客戶簡報抄這張就好。其他 50 分鐘可以跳過。" |

## 詳細分析

### 為什麼 A 是 3 不是 4

兩個原因。第一，30 分鐘塞 69 張投影片這個密度太高，Slide 4 三條信條 → Slide 28 TEMPO IS THE WEAPON → Slide 58 三條信條 refrain，整場「rhetorical framing」的比例壓過「technical novelty」。Doctrine 講三遍我就煩了。第二，全場唯一可被外部驗證的數據是 Slide 17 的 Brier 0.31→0.12 跟 Slide 4 的 30× 速度 — 但兩個都沒有 baseline。30× vs 什麼？人類紅隊？Cobalt Strike 自動化？PentestGPT？沒給。Brier 200 輪是哪 200 輪、跨幾個靶機、是不是同樣 5 個誤設定重複跑？沒給。這對紅隊隊長是致命傷 — 你要說自己是 fact-driven，自己的 marketing 數字就先要 fact-driven。

### 為什麼 B 是 2 不是 3

新的東西只有兩個半：(1) composite confidence 取幾何平均的構想（半個新，數學是老的，application 角度是新的），(2) attempt.failed + cooldown 機制（半個新，紅隊內部都有人類版本，systematize 是新的），(3) Slide 20 提到 MCP description 的 prompt injection allowlist（這個倒是真的 thoughtful，紅隊圈很少有人從 attacker-side 提這個防禦面）。其他都是已知的：OODA loop 大家都在用、C5ISR 是 framing 包裝、17 個 MCP 工具是 wrapper、AS-REP + ESC1 + secretsdump 是教科書 chain。Slide 19 hardcoded → LLM 動態路由的對比，10 行 code vs 3 行 code 那張對工程師有梗，對紅隊我內心翻白眼 — 這是 Anthropic MCP spec 的功能，Athena 不是發明者，講得像是自己的 doctrine breakthrough。

### 為什麼 C / D 是 3.5 / 2.5

C 給 3.5，因為 framing 跟我有關（客戶 briefing、紅隊招人面試題目、解釋 AI 紅隊跟 prompt 紅隊差別）— 但攻擊技術沒有跟我有關的東西。D 只給 2.5，因為我帶走的「行動」基本上只有兩件：(1) 下次客戶 briefing PPT 抄 Slide 65 對比表，把我們的 TTP 跟 Athena 對比；(2) 跟團隊 review 我們自己的 attempt.failed Notion 文件，看能不能 systematize。但這兩個都不是這場 talk 推動的，是這場 talk 提醒了我。真正的「我要回去做」沒有 — 沒有客戶風險面我可以馬上提示、沒有新工具我可以加進工具箱、沒有新偵測 bypass 我會試。

### Harry 段（slides 1–54 + 63–69）我的感受

**前 28 張（理論）：** Slide 4 三信條開場 OK 但太長，Slide 8（C2 → C5ISR）軍事類比講給董事長聽很好，講給紅隊聽是浪費。Slide 12 Boyd OODA 我大學就讀過，10:1 交換比這個 anecdote 在資安圈被引用過 200 次了。Slide 15（Orient JSON 樣本）這張我精神回來一下 — 真實 JSON 結構、`recommended_technique_id` + `confidence` + `options[3]` 的 schema 設計是合理的，看得出來不是隨便寫的。但 Slide 16 三道閥（composite confidence + risk_threshold matrix + noise_budget）裡面 noise_budget 那個機制我懷疑 — 紅隊真的能量化 noise_cost 嗎？Defender 偵測曲線是非線性的，每個 EDR 不一樣，noise_cost = 2 是怎麼定的？沒解釋。

**Slide 17（0.87 拆解）：** 這是 Harry 段唯一讓我抄筆記的一張。Laplace smoothing 寫成 `(success+1)/(total+2)` Beta(1,1) 是教科書貝氏，但用 `composite = (LLM × validation × history)^(1/3)` 把幾何平均當 calibration clamp 是合理的工程選擇 — 算術平均會被高分項拉走，幾何平均對 0 敏感，三項任一偏低會把整體拉下來。Brier 0.31→0.12 有給數字算誠意，但前面講過數字 baseline 不夠透明。

**Slide 19（hardcoded → LLM 動態路由）：** 我會在心裡翻白眼但不會講出來。10 行 dict 變 3 行 LLM dispatch 不是 doctrine，是把工程責任丟給 LLM。當 LLM 選錯 tool 怎麼辦？Slide 20 講了 fallback（連續 2 次失敗 → 標 dead_end），這個答案 OK 但不夠 — 真實環境一個 dead_end 可能是因為 EDR 暫時性偵測，不是這個 technique 本身不行。30min cooldown 機制至少回應了我這個質疑，OK 算過關。

**Slide 32（踩過的坑）：** 這張救了 Harry 段的 credibility。三個 failure mode（EDR 擋 LSASS dump、BloodHound 超時 partial facts、平行 race condition + advisory lock）每個都具體。第三個 PostgreSQL advisory lock 那個解法我覺得寫過 production system 的人才會這樣解，這張不是 marketing 是工程紀錄。但只有一張太短，我希望看到 5–6 個 failure mode + recovery strategy 對照，那會把這場 talk 整體 credibility 拉上來。

**Slide 33–54（demo 主體 + AS-REP + ESC1 + secretsdump）：** 這 22 張我大部分時間在等 Alex 段。Demo 環境 5 個誤設定（Slide 33）寫得很白：ASP.NET 注入 + DoesNotRequirePreAuth + ESC1 + 無約束委派 + xp_cmdshell — 這是 lab 靶機，不是企業環境。20 分鐘打穿不是 AI 厲害，是靶機故意做給你打。我在心裡狂翻白眼是因為 Slide 31 的 mission brief 說「全強密碼，純靠 AD 設定錯誤」 — 對啊，5 個故意 misconfig 我用 BloodHound + 自己的腳本也是 20 分鐘。30× 速度的 baseline 又一次沒給。Slide 53（War Room timeline）的 OODA #26 看起來蠻舒服，但所有 demo 都長這樣 — 沒有人會在 talk 上放失敗的 OODA #1, #5, #14, #22 的 timeline，只放成功的 #26。

**收尾（Slide 55–58 + 65）：** Slide 55 三個心得（強密碼不夠、ADCS 是後門、AI 1 天 → 20 分鐘）— 第一條我十年前就在講、第二條 Will Schroeder 2021 就講完了、第三條沒 baseline。Slide 65 對比 PentestGPT / Nebula / AutoAttacker 是收尾最強的一張，承認自己跟學術專案的差別在 stateful + dynamic routing + composite confidence，比通篇講 doctrine 強多了。但問題是這張只給 30 秒，應該擴成 2 張，把 Athena 在 AutoAttacker (Xu et al. 2024) 用的 attack graph 表示法上改了什麼、跟 PentestGPT 的 prompt loop 差別具體在哪講清楚。對讀過論文的人這是最有價值的一段，被埋掉太可惜。

### Alex 段（slides 55–62）我的感受

Alex 段 10 分鐘內塞 8 張，密度比 Harry 段更高，但我反而覺得這 10 分鐘 ROI 比 Harry 那 20 分鐘高。原因：

**Slide 4（flAWS.cloud Orient JSON）：** 這是全場第二好的一張（第一是 Slide 17）。`rec_id 00e38a61` + 真實 timestamp `2026-04-16T16:11:11.286Z` + `evidence_refs: ["web.vuln.ssrf", "cloud.aws.imds_role"]` — 這是真的 production log 撈出來的，不是手寫 demo JSON。`situation_assessment` 那段「Per Rule #10, SSRF→IMDS pivot required」直接引用內部 rule 編號，這種細節是裝不出來的。三個 confidence（0.95 / 0.75 / 0.65）的 spread 也比 Harry 段那個都 0.87 看起來真實。「不是更快，是更聰明」這句 punchline 我會抄。

**Slide 5（blast radius 跨 hybrid identity）：** 對紅隊隊長價值中等。AD → Entra Connect → Azure → M365 → Key Vault → 跨雲供應鏈這條鏈我自己跑過，不是新知識。但「傳統 CVSS 算不出來這種當量」這句對我接下來寫客戶 executive summary 是金句，會抄。

**Slide 6（Storm-0558 / Midnight Blizzard / Volt Typhoon）：** Storm-0558 (2023) MSA 簽章金鑰外洩、Midnight Blizzard (2024) Microsoft 內部信箱、Volt Typhoon LOTL — 這三個 case 我都讀過 CISA + Microsoft 的 IR 報告。但把它們放在一起當作「混合身分攻擊已經在發生」的 evidence 是好的 framing，比 Harry 段全部 lab demo 有說服力。「差別只在於攻擊者用 Python 還是 AI，而那個差距正在縮小」這句結論我也覺得 OK，雖然「差距正在縮小」沒有 quantitative evidence。

**Slide 7（防禦方三問）：** 紅隊 vs 雲端地端、SOC 是否把憑證 token 路徑當同一張圖、IR 跟得上 AI 速度 — 這三問是給 CISO 跟 SOC manager 的，不是給我。但下次面試 candidate 可以拿來當問題。

**整體：** Alex 段最大的優點是有 3 個外部可驗證的 anchor 點（真實 Orient log、3 個真實 IR case、明確的雲端 attack surface 列表），credibility 比 Harry 段純 lab demo 高。但 10 分鐘容量本來就有限，我希望 Slide 4 那個 Orient JSON 能擴成 2 張 — 加一張展示「同樣 SSRF 在另一個環境（Azure 而非 AWS）AI 怎麼選擇不同 technique」，把「決策依環境變」這件事 demo 給看。

### 如果我能改一件事

**砍掉 Slide 41–48（AS-REP 7 張詳細協議解剖），合併成 2 張，把省下的 5 張時間給 Slide 17 + 32 + 65 擴展。**

具體：
- Slide 41 (AS-REP 原理) + Slide 43 (OPSEC) → 合併成 1 張，留協議圖跟 noise_cost=2 那行就好。AD 圈的人都知道 padata empty 的意義。
- Slide 45 (ESC1 原理) + Slide 47 (三條件) → 合併成 1 張。`certipy find -vulnerable` 一行 demo 然後三條件清單就好。
- 省下 5 張：(a) 一張擴 Slide 17 的 calibration，加 baseline（人類紅隊的 confidence calibration 是什麼）— 把 Brier 0.31→0.12 變得可信。(b) 兩張擴 Slide 32 從 3 個 failure mode 到 6–8 個 + recovery strategy 矩陣 — 這對紅隊聽眾是 credibility 殺手鐧。(c) 兩張擴 Slide 65 對比，把 PentestGPT (Lin 2024) 的 prompt loop limitation、Nebula 的 RAG miss、AutoAttacker 的 attack graph 跟 Athena 具體比，引一兩條原文 quote。

這樣改完，紅隊聽眾的 B（學新東西）至少從 2 拉到 3.5，A 從 3 拉到 3.5。代價是非紅隊聽眾失去 ESC1 + AS-REP 的 protocol detail — 但說真的，30 分鐘 talk 不是教學，那些 detail 應該在 GitHub README 跟 backup slide。
