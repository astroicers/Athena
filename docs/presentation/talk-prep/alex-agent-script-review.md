# Alex Agent Review — Script Part 1 + Slides 1-28

**版本：** v1 / 2026-05-06
**審稿人：** alex agent

## TL;DR

開場 OK、收尾 OK，中段 ARCHITECTURE+FRAMEWORK 是雙重交稅 — 我把 confidence 公式講了兩次、三道閥講了兩次、Communications 講了三次。28 張砍到 22 張剛好，30 分鐘要塞下這個量已經是壓著吐出來，不是合理節奏。Slide 17 是金，Slide 25 是金，Slide 26 該死，Slide 4 三條信條 + Slide 28 30× 收法穩。Voice 大致是我，但兩三段「停頓 / 掃視」開太多了像在演舞台劇 — Harry 比我會拍掌握場，我這場要更乾。一句 verdict：**結構性的 30% 重複必須砍，剩下的瑕疵是現場可吞的**。

---

## 講稿審查

### 整體聲音

像。但「假 Alex」最濃的地方是 Slide 11 跟 Slide 27。

Slide 11 收尾那句「軍事 80 年累積的 doctrine，我們花了大概 4 個月做出來——不是因為我們聰明，是因為他們已經把藍圖畫好了」— 不行。這聽起來像 TED 講者在演「謙遜」。我講話不會這樣鋪陳，我會說「四個月做完，不是我們快，是 C5ISR 把藍圖畫好了。我們做的是把它翻成 LLM 看得懂的 JSON」— 講完就走，不留情緒尾巴。

Slide 27 那句「兩條通道，閉環」後面又補一句「Act 不只是『下指令』。是把指揮官的決策、武器庫的能力、戰場的回報——接成一個閉環」— 同一件事講兩遍。我會講第一句，停一秒，下一張。第二句砍掉。

最像我的是 Slide 7 的「我不浪費你時間講教科書」、Slide 17 calibration clamp 那段「LLM 講大話沒關係，歷史紀錄會把它拉回來」、Slide 19 結尾「不用改一行 code」、Slide 20 結尾「schema 不只是介面，是攻擊面」。這四句保留，這是我寫得出來的句子。

Stage direction 整體偏多。`[停頓]` 出現 35 次以上，`[掃視]` 28 次以上。IaC v6 outline 裡 `[PAUSE]` 整場只給三個關鍵時刻，這場每張平均 2-3 個停頓 — 觀眾會疲乏。我建議：**全部刪除一半**，留下 Slide 1 開場、Slide 12 Boyd 故事的 10:1、Slide 17 第三因子、Slide 28 finale 那四個位置的停頓就好。其他位置的停頓寫進 punchline 自然會出現，不需要標。

### 逐張或分群審

**Slide 1 (開場 + 18m57s)** — 過。但 line 30「傳統紅隊做完這條鏈，大概一個禮拜」這句重複出現在 Slide 7 line 207「傳統紅隊做完這三段，大概一週」、Slide 28 line 1052「人類紅隊一天的工作量——我們 20 分鐘做完」。同一個對比講三次但用三個不同數字（一週 / 一週 / 一天），我自己看都覺得錯亂。**統一成「一週」**，Slide 28 改成「人類紅隊一週的工作量——我們 20 分鐘做完」。

**Slide 2 (Harry 自介)** — Line 56「我這邊講的是引擎，他等下講的是現場」OK。但 Harry 30 秒自介這個 timing 太緊，現場 Harry 可能講到 45-60 秒，這張的 transition 就會變鬆鬆的。建議改成「給 Harry 個 1 分鐘，他比我會講」— 預期值放寬，現場不會出戲。

**Slide 3 (我自介)** — line 72「那場聽過的朋友請舉個手讓我看一下？」這個技巧我用過，可以。但接下來「謝謝」這個收太快，**現場如果只有 5 隻手舉起來會冷場**。建議準備一個 fallback：「沒舉手沒關係，今年這場是獨立的」直接接下去，不要讓沉默卡住。

**Slide 4 (三條信條)** — 過，最強的一張。但 line 107「這句話我等下會再講三次，最後一張會引爆」— 預告自己要重複，反而讓重複看起來更刻意。**砍掉這句**，讓觀眾自己發現 refrain。

**Slide 5 (Mission Briefing)** — 過。但 line 138「網路上 GitHub 都看得到」這句語感不對，我會說「GitHub 自己 clone 一份就有」— 主動，而不是被動。

**Slide 6 + Slide 7** — 重複。Slide 6 講「偵察→突破→立足→橫向→收割」5 個節點，Slide 7 講「掃描→建 C2→拿 DC」3 段。**內容是同一個 kill chain 拆兩次**。建議合併成一張：保留 Slide 6 的 5 節點 visual + Slide 7 的 hostname 標注（WEB01 / DC-01 / ACCT-DB01），講稿用 Slide 7 的版本但壓到 1 分鐘內。**省一張、省 90 秒**。

**Slide 8 (二戰 → C5ISR)** — 過。line 240「這跟紅隊有什麼關係？」+ line 245「光靠人類用 keyboard 串，做不到那個速度」這個轉折好。

**Slide 9 (DOCTRINE 章節分隔)** — **砍**。整張就是預告下三張要講什麼。line 268「C5ISR 是組織骨架、OODA 是節拍器、Tempo 是勝負手」— 這三句已經在 Slide 4 講過、會在 Slide 28 再講第三次。章節分隔頁對 30 分鐘 talk 是 luxury，**不要**。同理 Slide 14、Slide 21 都該砍。

**Slide 10 (C5ISR 8 字母)** — 過。但 line 297「四個 C：Command、Control、Communications、Computers」+ line 301「第五個 C 是 Cyber」+ line 303「ISR：Intelligence、Surveillance、Reconnaissance」 — **8 個字母用 30 秒念完**，否則這張會拖。現在的 speaker notes 寫法估計 1 分 15 秒，太久。

**Slide 11 (C5ISR → Athena 對應)** — 過，但要快。一對一對應 8 條太細，建議 speaker notes 改成「C5ISR 八個字母 → Athena 八個元件，一對一。我不一條一條念，請拍照。重點是 Reconnaissance / Intelligence / Cyber 這三條 — 偵察工具、Facts DB、實際火力 — 等下會反覆出現」。**省 60 秒**。

**Slide 12 (Boyd OODA)** — Line 369「F-86 贏了 10:1 的交換比」這個數字 [紅隊 lead persona] 已經抗議過「資安圈被引用 200 次了」。但這場 audience mix 是半專業半商務，講一次 OK。維持原狀，只把 line 384「OODA 不是流程圖，是節拍器」這句**加重**，這是這張唯一新的 takeaway，現在被「快一點點」那段稀釋了。

**Slide 13 (Athena 跑 OODA)** — 過。line 423「整個 loop——30 秒一輪」是 setup，line 430「這就是 TEMPO 的物理基礎」是 callback，這個結構好。

**Slide 14 (ARCHITECTURE 章節分隔)** — **砍**，理由同 Slide 9。

**Slide 15 (Orient JSON)** — 過。Line 478「LLM 沒有亂講話。它的根據在上面 situation_assessment 那行」這句語感正確。但 line 491「LLM 直接給『我建議 AS-REP Roast』這種自然語言句子，是垃圾」— 我講話會用這個語氣，但「垃圾」會讓現場部分商務型聽眾皺眉，建議改成「LLM 直接給自然語言句子是用不上的」— 一樣強硬，少一個情緒詞。

**Slide 16 + Slide 17** — Slide 16 講三道閥（composite confidence / risk matrix / noise budget）+ Slide 17 拆 composite confidence 公式。**Slide 26 又把這三道閥重講一次**。也就是說 audience 會聽到：第一次 Slide 16 三道閥 → 第二次 Slide 17 拆第一道閥 → 第三次 Slide 26 同三道閥但綁 C5ISR Control。

我看完反應：**砍 Slide 26**。Slide 16 + 17 的版本資訊密度更高、講者語氣更熟練（「LLM 講大話沒關係，歷史會把它拉回來」），Slide 26 那個「指揮官不靠感覺下令，靠量化評估」是 Slide 16 的弱化版本。Slide 26 的 C5ISR Control 對應只是換一個 label，不增加任何 content。

**Slide 17 (0.87 拆解)** — 全場最強的一張（除了 finale）。維持原狀。Line 567「LLM 喊 0.95、但歷史只有 0.4——複合信心值會被拉到 0.5 上下」這個具體計算讓 [紅隊 persona] 唯一抄筆記，這就是要保。

**Slide 18 (17 個 MCP)** — 過。但 speaker notes line 596-599 把 4 群名單念完，其實看 visual 就有了。**改成「分四群、每群 3-4 個工具，我不念了，自己看」**，把省下來的 20 秒留給 line 612「DOCTRINE BEATS TOOLS」那段 callback。

**Slide 19 (hardcoded → LLM 動態路由)** — 過。Line 656「不用改一行 code」這個收法乾淨。但 [紅隊 persona] 抓到一個破口：「LLM 選錯怎麼辦？」這個問題你 Slide 20 才回答，中間有 3 秒空檔。建議在 line 658 transition 加一句「但 LLM 選錯怎麼辦——下一張」直接 set up，不要讓質疑卡在心裡。

**Slide 20 (Schema 是 sandbox)** — 過。Prompt injection via MCP description 是這張 unique value，[紅隊 persona] 都覺得 thoughtful。**保留 line 685-700 那段 "schema 不只是介面，是攻擊面"**，這是這張的支點。

**Slide 21 (FRAMEWORK 章節分隔)** — **砍**。

**Slide 22 (為什麼接 OODA + C5ISR)** — Saved by line 762「OODA 給你節奏，C5ISR 給你體系。一個告訴你怎麼跑、一個告訴你跑什麼」。這句保留。但前面 line 743「很多人看 OODA 跟 C5ISR，覺得是同一件事。不是」這個開場太教科書、太「我來糾正你」。改成「OODA 跟 C5ISR 不是同一件事，但放一起才完整」— 直接給結論，不要設稻草人。

**Slide 23-27** — 這 5 張是 OBSERVE / ORIENT (×2) / DECIDE / ACT 對應 C5ISR。這是這場最弱的結構。

問題：Slide 13 已經講過 OODA 四步了。Slide 11 已經講過 C5ISR 八個字母對應 Athena 元件了。Slide 23-27 在做的事是「再 cross 一次」— 把兩個已經講過的東西 zip 起來。每個 OODA 步驟對應 1-2 個 C5ISR 字母，每張 1 分鐘 = 5 分鐘。

我的判斷：**全砍掉合成 1-2 張**。具體做法：
- 砍 Slide 22, 23, 24, 26, 27（5 張全砍）
- 保留 Slide 25（Orient 失敗記憶 + cooldown）— [紅隊 persona] 唯一另一張抄筆記的，這個 doctrine 是 unique
- 新做一張「OODA × C5ISR Crosswalk」單表 — 4 列（O/O/D/A）× 2 欄（C5ISR 對應 + Athena 元件 + 失敗模式 + 自我修復），1 分鐘帶過
- **5 張壓成 2 張，省 3 分鐘**

如果這個太激進、不想動結構，**至少砍 Slide 26**（理由如上，整張是 Slide 16 的 rerun）。

**Slide 28 (TEMPO 30×)** — 全場最強的一張。維持原狀。但 line 1062-1068 三條信條 callback 太長，改成「我給你的三條信條 — FACT-DRIVEN、DOCTRINE BEATS TOOLS、TEMPO IS THE WEAPON — 等下 Harry 的 demo 會把這三條印一次給你看。Harry，換你」。**省 30 秒**，handover 更乾脆。

### 必修 punchlines

| Slide | 現在的 punchline | 問題 | 改法 |
|-------|----------------|------|------|
| 4 | 「這句話我等下會再講三次，最後一張會引爆」(line 107) | 預告 refrain 反而破壞 refrain | 砍掉這句 |
| 11 | 「不是因為我們聰明，是因為他們已經把藍圖畫好了」(line 344) | 假謙遜、TED 味 | 「四個月做完，不是我們快，是 C5ISR 把藍圖畫好了。我們做的是把它翻成 JSON」 |
| 15 | 「是垃圾」(line 491) | 商務 audience 會皺眉 | 「是用不上的」 |
| 22 | 「很多人看 OODA 跟 C5ISR，覺得是同一件事。不是」(line 743) | 設稻草人 | 直接給結論「OODA 跟 C5ISR 不是同一件事，但放一起才完整」 |
| 25 | 「LLM 在這件事上——比人類精準」(line 899) | 過於肯定，會被 [紅隊 persona] 抓「真實環境驗證了？」 | 「LLM 在這件事上——不會像人類一樣忘記」(改 quality 不改 quantity) |
| 26 | 「指揮官不靠感覺下令，靠量化評估」(line 942) | 整張砍掉 | N/A |
| 27 | 「Act 不只是『下指令』。是把指揮官的決策...接成一個閉環」(line 991) | 跟前一句「兩條通道，閉環」(line 989) 重複 | 砍後一句 |

可保留（不要動）的金句：
- 「武器庫人人有，差別在 doctrine」(Slide 4)
- 「我不浪費你時間講教科書」(Slide 7)
- 「LLM 講大話沒關係，歷史紀錄會把它拉回來」(Slide 17)
- 「不用改一行 code」(Slide 19)
- 「schema 不只是介面，是攻擊面」(Slide 20)
- 「30 倍不是更快——是換了一個維度」(Slide 28)

---

## Slide 順序 / 結構審查

### 該砍的

| Slide # | 理由 |
|---------|------|
| **9** (DOCTRINE 章節分隔) | 純 transition page，內容已在 Slide 4 預告、Slide 10-13 會展開。30 分鐘 talk 沒空間放 luxury。**省 30 秒**。 |
| **14** (ARCHITECTURE 章節分隔) | 同上。「給你看 code」這個 setup line 移到 Slide 15 開頭講就好。**省 30 秒**。 |
| **21** (FRAMEWORK 章節分隔) | 同上。**省 30 秒**。 |
| **26** (Decide ↔ Control) | 整張是 Slide 16 三道閥的 rerun，只多一個 C5ISR Control label。Audience 會聽到「composite confidence × risk matrix × noise budget」這三個詞**第三次**。**省 1 分 15 秒**。 |
| **22 + 23 + 24 + 27 (考慮一起砍)** | 見「該合併的」 |

最起碼必砍：9, 14, 21, 26 — **省 2 分 45 秒**。

### 該合併的

| 合併哪幾張 | 理由 | 做法 |
|-----------|------|------|
| **Slide 6 + 7** | 同一條 kill chain 拆兩次 | 5 節點 visual + hostname 標注合併到一張，speaker notes 用 Slide 7 的 3 段版本但 1 分鐘內帶完。省 1 張、~90 秒。 |
| **Slide 22 + 23 + 24 + 27** (FRAMEWORK 4-grid) | OODA 四步逐張對應 C5ISR — 每張 1 分鐘 = 4 分鐘 | 合成一張「OODA × C5ISR Crosswalk」單表，4 列 × 4 欄。1 分 30 秒帶完。省 2 分 30 秒。 |

如果這兩個合併都做：**4 張砍成 2 張、省 4 分鐘**。

### 該換位置的

**Slide 18 (17 個 MCP 工具)** 現在在 ARCHITECTURE 章 (15-20)，但這張其實是 weapon inventory，跟 Slide 27 (Act ↔ Cyber) 講的是同一件事。建議移到 Slide 27 旁邊（如果 Slide 27 沒砍）或者乾脆併進 Slide 19 的左半 — 「我們有 17 個工具，但路由不靠 dict 靠 LLM」一張帶過。

**Slide 25 (Orient cooldown)** 現在在 FRAMEWORK 章 (Slide 24 之後)，但這個機制是 ARCHITECTURE 細節，本質上跟 Slide 17 (composite confidence) 同一個 family — 都是「LLM doesn't get final say」的具體實作。建議移到 Slide 17 之後 (新 Slide 18)，跟 confidence 公式綁在一起當「FACT-DRIVEN 怎麼落地」的雙證。

### 整體 28 張對 30 分鐘

**偏多**。

簡單算：30 分鐘 - 開場+自介 (3 張，~3 分鐘) - 收尾 finale (1 張，~2 分鐘) = **24 張要塞在 25 分鐘**，平均每張 1 分鐘。對技術張 (Slide 15 / 17 / 20) 來說 1 分鐘剛好；對章節分隔頁 (9 / 14 / 21) 是浪費；對 FRAMEWORK 重述章 (22-27) 是稅。

更糟的是：**這只是 Alex 段**。Harry 後面還有 30+ 張。如果這 28 張我講超時 5 分鐘，Harry 的 demo 會被腰斬。

**目標：壓到 22 張、25 分鐘以內，留 5 分鐘 buffer 給 Harry 跟 Q&A**。

壓法：
1. 砍章節分隔 9, 14, 21 → 25 張 / -1.5 分鐘
2. 合併 Slide 6+7 → 24 張 / -1.5 分鐘
3. 砍 Slide 26 → 23 張 / -1.5 分鐘
4. 合併 Slide 22+23+24+27 → 19 張 / -2.5 分鐘 (新增 1 張 crosswalk)

這樣：**22 張、~22-23 分鐘、Harry 接 demo 還有時間**。

如果不想動結構（無法接受砍 22-27），最低限度：**砍 9, 14, 21, 26 + 合併 6+7 = 22 張 / 省 4 分鐘**。但這版本 FRAMEWORK 章還是會讓技術 audience 跑神。

---

## 三件最該動的事

### 1. 砍 Slide 26 + 處理 FRAMEWORK 章 (22-27) 的 redundancy

**ROI 最高**。這是觀眾體感「為什麼還在重講」的最大來源。Slide 26 是 Slide 16 的 rerun（三道閥又講一次），Slide 22-24 + 27 是把 OODA 四步跟 C5ISR 字母 zip 起來但這個 zip 在 Slide 11 + 13 已經做過。

最低成本動作：**砍 Slide 26**。
完整動作：**5 張壓成 2 張**（保留 Slide 25 + 新做 1 張 crosswalk）。

### 2. 砍三張章節分隔頁 (9, 14, 21) + 合併 Slide 6+7

**省 3 分鐘 buffer**。30 分鐘 talk 不能養章節分隔頁這種 luxury。Slide 6+7 講同一條 kill chain 拆兩次，合併不損失內容。

### 3. 修 punchline 真實感

**前兩條改完才有 oxygen 處理 voice 問題**。具體 7 條改寫見上方表格 — 重點是 Slide 11 結尾、Slide 22 開場、Slide 26 (整張砍)、Slide 27 結尾這四個位置的「假 Alex」味道最重。

Stage direction 砍一半：保留 Slide 1 / 12 / 17 / 28 四個關鍵停頓，其他 `[停頓]` `[掃視]` 全部刪。讓現場節奏自己出現，不要用標記預設情緒。

---

## 通過的部分

- **Slide 1 開場 18m57s 的 framing** — line 31 「在我講完這 28 張之前，AI 已經把一個完整的 AD 環境拿下來了」這個 setup 是這場開場的支點，跟 Harry 的 live demo 形成回響。維持。
- **Slide 4 三條信條** — 三條都是 punchline 級的 framing，現場 [CISO persona] 已經確認會抄走當 board narrative，不要動。
- **Slide 12 Boyd 故事** — 韓戰 10:1 雖然被引用過 200 次，但對半專業半商務 audience 第一次聽，OK。「快一點點」這個 phrasing 我自己會講。
- **Slide 17 confidence 公式拆解** — 全場最強，[紅隊 persona] 抄筆記就是這張。Laplace smoothing + 幾何平均 calibration clamp 的 framing 不要動，這是區分 "AI 紅隊" vs "prompt 紅隊" 的支點。
- **Slide 19 hardcoded → 動態路由的 before/after code** — 視覺對比有梗、結尾「不用改一行 code」乾脆。
- **Slide 20 Prompt injection via MCP description** — 這是現場唯一能「教」紅隊 lead 的東西，[紅隊 persona] 都認 thoughtful。維持。
- **Slide 25 Orient cooldown 機制** — [紅隊 persona] 第二張抄筆記的，「比 Notion 筆記精準」的 framing 對紅隊有直接共鳴。建議從 FRAMEWORK 章移到 ARCHITECTURE 章跟 Slide 17 綁在一起，但不要砍。
- **Slide 28 TEMPO 30× finale** — 結構正確（30× → 30 倍是換維度 → 三條信條 callback → handover Harry）。只需要把三條信條那段壓短一點。
- **整體三條信條的 setup（Slide 4）→ payoff（Slide 28）** — 這是這場 talk 的 spine，沒有問題。問題在中間 24 張怎麼撐。

方向是對的。要做的是壓重量，不是改地圖。
