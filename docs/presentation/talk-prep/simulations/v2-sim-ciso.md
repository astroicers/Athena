# v2 模擬聽眾回饋 — CISO / 資安長(金控業)

**版本：** v1 deck (2026-05-06)
**模擬日期：** 2026-05-06
**場景：** CYBERSEC Taiwan 2026 30-min Breakout Session
**Scoring scale：** 1-5(1 = 浪費時間,5 = 今年最值得我親自坐下來聽的一場)

## Persona Profile

52 歲,台灣某中大型金控 CISO,任職 7 年。團隊 50 人(SOC、紅隊、GRC、AppSec、IR 五個 stack),年度資安預算 8 位數新台幣,直接 report 至 CFO,跟董事會半年一次資安治理委員會。已 8 年沒寫過 production code,今天來 CYBERSEC 不是學技術 — 是收 framing、收數字、收 peer benchmark,下半年董事會議我要 pitch「AI 攻擊時代的資安投資再平衡」這一案。我會用 board lens、ROI lens、vendor management lens 來聽這場 talk。

## 回饋表

| 項目 | 評分 / 回答 |
|------|----------|
| A. 整體滿意度 | 4.5/5 |
| B. 學到新東西 | 3.5/5 |
| C. 跟我有關 | 4.5/5 |
| D. 回去會採取行動 | 5/5 |
| E. 一句話回饋 | 「這場 talk 給我的不是新威脅情報 — 是新的 board narrative。三條信條、20 分鐘對 1 天、Mission Complete tile,我下個月會議直接搬 5 張投影片。中間引擎那段我完全放空,但兩位講者很誠實地告訴我『這段你不用聽』,光這份分寸就值我來這一趟。」 |
| F. 最重要的時刻 | Slide 28 那張「30×」大字 + Slide 54 的「20 min / 3-of-3 / 0 manual / 100% explainable」四格儀表板。這對 board 有衝擊力的原因不是數字本身,是這兩張投影片把「攻擊速度」從工程術語翻譯成董事會語言。董事會聽不懂 OODA、聽不懂 MCP、聽不懂 ESC1,但他們聽得懂「攻擊者已經 30 倍快、我們的事件應變速度沒有跟上」。我手機拿起來拍了至少 4 次,Slide 28 我拍了兩次怕角度沒對好。第二個關鍵時刻是 Alex 的 Slide 56(DA 不是終點,是入場券)— 這是我整年聽過最精準的 cloud risk framing,因為我家的 hybrid identity(Entra Connect + AD FS)就是他講的那個架構,而我們 board 一直把 cloud security 當成「IT 在管的事」,沒人意識到地端 DA 直接接到雲端控制面。 |
| G. 最想滑手機的時刻 | 三段。(1)Slide 13-20 引擎內部那 7 張 — Orient JSON、composite confidence 公式、schema sandbox、dynamic routing。我看了第一張就知道「不是給我聽的」,後面 6 張我在算明年紅隊 budget 的 baseline。(2)Slide 41-49 的 AS-REP / ADCS / certipy 細節 — 這些我團隊紅隊 lead 會看,我不需要懂 etype 23 是 RC4-HMAC。(3)Slide 51 的 secretsdump 原理 — 同上。但這三段加起來大概只有 6-7 分鐘,而且講者很誠實地用「下一張回到節奏」的橋接句帶過,所以我沒有失望,只是進入「策略思考模式」,把這時間拿來想 Q&A 我要問什麼。 |
| H. 我下個 board meeting 怎麼用這場 talk | 我下半年董事會「AI 威脅 25 分鐘簡報」直接搬 5 張投影片(見下方詳細分析)。三條信條變我的開場 framing,Mission Complete 變我的「為什麼今年要加紅隊預算」的 punchline,Alex 的真實 APT 三例(Storm-0558 / Midnight Blizzard / Volt Typhoon)變我的「不是假設、是 in the wild」段落。Athena 是不是商業產品我會私下找講者問,但即使不能採購,這套 narrative 我已經拿到了。Risk-adjusted ROI 的計算方式我也想清楚了:「攻擊者 cycle time 縮短 30 倍 → 我的偵測 / 應變 cycle time 必須相應縮短 → MDR 換約 + SOAR 投資 + 紅隊 AI 武裝化」這是三個 budget line item。 |

## 詳細分析

### 我下個 board meeting 會用的 5 張投影片 + 用法

1. **Slide 4(三條信條)** — 我的開場 framing。直接照搬「FACT-DRIVEN / DOCTRINE BEATS TOOLS / TEMPO IS THE WEAPON」的三段結構,只把標題換成防守視角:「FACTS BEAT FEELINGS / FRAMEWORK BEATS POINT TOOLS / SPEED IS SURVIVAL」。董事會喜歡這種三柱式 framework,看得懂、記得住、會在後續會議引用。

2. **Slide 28(30× 大字)** — 我的 emotional anchor。Board 的注意力曲線在第 8-10 分鐘會掉,需要一個視覺衝擊把他們拉回來。30× 三個字佔滿整張投影片,沒有任何附註,就是最強的單點衝擊。我會搭配一句話:「攻擊者一晚做完我們紅隊一週的工作。」

3. **Slide 54(Mission Complete 四格儀表板)** — 我的「為什麼明年要加預算」的 closer。20 min / 3-of-3 / 0 manual / 100% explainable 這四個數字是最完美的 board-friendly 證據格式。不需要解釋技術細節,光看這四格,任何 board director 都能感受到衝擊。

4. **Alex Slide 60(Storm-0558 / Midnight Blizzard / Volt Typhoon)** — 我的「這不是假設」段落。Board 最怕的就是被 Auditor 或媒體質疑「你說的威脅是不是廠商在炒作」。這三個 named APT 都是 CISA 出公告、上過 Wall Street Journal 的事件,引用這三個就是最強的可信度錨點。Volt Typhoon 對我特別重要 — 因為提到台海情境,我家董事會有兩位是退役將領,這條線他們會接得很快。

5. **Alex Slide 56(DA 不是終點,是入場券)** — 我的 cloud security 升級議題的核心 framing。我家過去三年一直在 push cloud security budget,但 board 的反應一直是「我們有 Microsoft E5、有 Defender、有 Sentinel,夠了吧」。這張投影片把「地端 AD」跟「雲端 blast radius」串成一張連續圖,直接打掉那個錯誤前提。

### 我會抄走的 4 個 framings

1. **「不是工具,是指揮系統」(Slide 8 + Slide 57)** — 這對 board 有效,因為它把「資安投資」從「買更多 vendor 的東西」重新定義成「建立指揮架構」。Board 永遠願意付錢給「architecture」,但不喜歡看到 vendor SKU 一條一條疊上去。我會把這個 frame 用來解釋為什麼 SOC + 紅隊 + IR + GRC 必須有共同的 doctrine 而不是各做各的。

2. **「視野的擴張」(Alex Slide 62)** — 這是英文 setup + 中文 kicker 的最後一擊。Board 喜歡這種詩意但有重量的句子,適合放在董事會簡報的第一張或最後一張。我會用「我們的視野必須跟攻擊者一樣寬」作為今年資安戰略主題句。

3. **「Doctrine beats tools」** — 這句直接對應到我長年想壓制的 vendor sprawl 問題。我有 12 家資安廠商,每年 renewal 時 board 都會問「這些東西為什麼這麼多,有沒有重疊」。我可以用這句話 reframe 成「我們需要的不是更少廠商,是更清楚的 doctrine 來指揮這些廠商」。

4. **「20 分鐘對 1 天」(Slide 55 第三段)** — 最具操作性的 ROI argument。我可以直接算給 board 看:「我家紅隊一年做 12 次內部演練,每次平均 2 週、總工時 240 人天。如果 AI 紅隊把 cycle time 從 1 天壓到 20 分鐘,代表我同一個 budget 可以做 30 倍量的演練 — 或者用 1/30 的 budget 做同樣量。Risk-adjusted ROI 怎麼算都站得住腳。」

### 為什麼 A / B / C / D 是這個分數

**A = 4.5:** 整體滿意度高,因為 framing / narrative / 數字三項全部到位。扣 0.5 是因為 Athena 這套系統的 vendor / open source / commercial licensing status 講者完全沒提 — 我作為買單者,聽完最直接的疑問是「我能不能用」、「多少錢」、「合規上有沒有問題」,這三個都沒有答案。

**B = 3.5:** 學到「全新東西」的程度其實一般,因為我去年已經讀過 NCC Group、Mandiant 對 AI-augmented red team 的研究,Storm-0558 / Midnight Blizzard 我家 SOC monthly threat brief 都過。真正新的是「OODA × C5ISR 雙框架」的整合 — 這個 framing 我之前沒看過,而且講者把它做到 production-grade。但講者沒有給我 peer benchmark(別家金控的 CISO 怎麼看),這是 B 沒給更高的原因。

**C = 4.5:** 跟我極度相關,但不是因為技術細節,是因為 board narrative 的 last-mile delivery。我們金控業最大的痛點就是「資安治理跟董事會語言之間的翻譯成本」,這場 talk 直接解決了我下半年董事會簡報的 70% framing 問題。扣 0.5 是因為純地端 AD 的部分(slide 33-54)對我家比較弱,我家的核心系統在 Azure / private cloud 為主,純地端 AD 的攻擊面比較有限 — 但 Alex 段把這個 gap 補上了。

**D = 5:** 走出去的時候我手上有三個明確的 actions:(1)下個月跟 vendor team 安排「Athena-style AI 紅隊演練」的 RFI,看市場上有沒有商業產品或 MSSP 提供類似服務(2)三個月內把 Alex 的 defender 三問題加進我家 RACI matrix 跟年度 audit scope(3)半年內向 board 提案「AI 攻擊時代資安投資再平衡」案,前置簡報直接用今天這 5 張投影片。

### Harry 段我的感受(CISO lens)

Harry 那 20 分鐘對我來說是「戰略性 demo」,不是「技術 demo」。WEB01 → DC-01 → ACCT-DB01 在 20 分鐘內全自動 pwned 這件事,從技術細節看我聽不懂、從戰略結果看我不能更懂。我的工作不是判斷 Athena 的 OODA loop 有沒有實作得漂亮,是判斷「攻擊者用這種能力的時候,我家防得住嗎」。答案是:防不住。我家紅隊上個月做的 internal AD 演練,從 initial foothold 到 DA 花了 3 天 — 這還是有人盯著、有人優化路徑的條件下。Athena 18 分鐘做完同樣的事,代表我們的不對稱戰場已經輸給未來的對手了。

戰術層 demo 對戰略層的意義在於「具體化威脅」。Board 永遠在問「AI 真的會威脅我們嗎,還是又是廠商炒作」。Slide 39 的「WEB01 COMPROMISED Δ+7m27s」這種 ops log 風格的時間戳,比任何 PowerPoint 都更有說服力。我會請我家 SOC manager 重新檢視我們的 detection coverage,看 Slide 36 那個 nmap → debug.aspx 的 footprint 我們的 EDR / NDR 抓不抓得到。

對 board 有衝擊的:Slide 28(30×)、Slide 54(Mission Complete 四格)、Slide 32(踩過的坑 — 因為太多 vendor 從不講失敗 case,Harry 講三個失敗給的 credibility 是這場 talk 最罕見的禮物)。

工程細節對我沒衝擊的:Slide 13-20 引擎內部、Slide 17 composite confidence 公式、Slide 41-49 AS-REP / ADCS 細節、Slide 51 secretsdump 原理。這些不是我的工作,我團隊紅隊 lead 看了會點頭,但對我的 board narrative 沒貢獻。

### Alex 段我的感受(CISO lens)

Alex 那 10 分鐘 punching above its weight。10 分鐘短、密度高、但每一張都打到 CISO 痛點。Cloud pivot 是我這個位置最熟悉的恐懼面,因為我每年的 pen test 報告 finding 集中在 cloud / hybrid identity,而 board 對這個的理解永遠停在「我們有 Microsoft E5 license」。

Alex Slide 56(DA = 入場券)是我整場 talk 最對齊我下半年 board 議題的一張。我家 hybrid identity 架構就是 Entra Connect + AD FS + PTA,三套都跑。Slide 58(blast radius 圖)那條從「初始入侵 → AD 立足點 → DA → 混合身分 → Azure 租戶 → M365 信箱 → Key Vault → 跨雲 / 供應鏈」的鏈條,我會直接拿來在董事會議上 walkthrough。Board 會問「我們在哪一段?」這正是我希望他們問的問題。

Slide 59(flAWS.cloud Orient JSON 真實 log)技術上很 solid,但對我的 board narrative 用處有限 — 這張更適合給我家 Cloud Security Architect 看,讓他評估 Athena 的 production-readiness。我自己更在意 Slide 60 的 in-the-wild 三例,這是 media briefing 等級的素材。

Slide 61(三個 defender 提問)是 last-mile delivery。「你的紅隊能同時看雲端 + 地端嗎?」這個問題我下週就會在 audit committee 提。我家紅隊跟 SOC 一直是兩個 silo,雲端跟地端的 visibility 也是分開的 — 這三題正好戳破這個 gap。我會把這三問加進明年 internal audit 的 RACI。

### 我希望講者多講 / 沒講的

第一,**vendor 中立性 / 商業地位**沒講清楚。Athena 是 open source 嗎?是 Cheehoo Labs 的內部 R&D 工具嗎?還是商業產品?我家紅隊能不能拿來用?授權多少?如果是 Cheehoo Labs 在賣服務,那這場 talk 本質是 vendor pitch,我聽的角度會完全不同。我希望結尾(Slide 67)直接放一張「Athena 的取得路徑」說明:商業 / 開源 / 委託服務 三個選項。

第二,**防守視角**完全缺席。整場 30 分鐘都是攻擊視角,沒有一張投影片回答「我家 SOC 偵測得到 Athena 的哪一步?」、「Athena 的哪些 footprint 是 EDR / NDR 該抓的?」、「composite confidence 0.87 在我家 SIEM 上長什麼樣?」這對 CISO 是最大的 missing piece。Alex 的三個 defender 問題是 strategic-level 的提示,但缺少 tactical 的 detection coverage 對應表。如果有 Slide 額外加一張「Athena 五個 ATT&CK technique 對應到的偵測 control gap」,這場 talk 對 SOC 經理直接有用。

第三,**法規 / 合規視角**完全沒提。我家是金控,deploy 任何 AI-powered offensive tool 都要過 FSC 報備、要過 board cyber risk committee、要簽 third-party risk assessment。如果 Athena 用 OpenAI / Anthropic API,客戶資料(包括 ports、credentials、internal hostnames)會不會傳出去?這個問題沒有答案我就不能採購。Slide 63 提到「Federated LLM(在地推論)」是 roadmap — 但 roadmap 不是現在就有的東西。

第四,**peer benchmark**沒給。我希望聽到「歐美金融業現在是 Y% 的 CISO 已經把 AI 紅隊納入年度 budget」、「亞洲金融業的 baseline 是什麼」這種 industry data。這場 talk 的視角是研發者視角,不是 buyer 視角 — 我能理解,但這是它沒拿到 5/5 的原因之一。

### Bottom line — 我下個 fiscal year budget 會因此調整嗎

會,而且方向已經明確。我下半年 board 提案的三條 line item:

1. **MDR 換約 / 加錢**:現任 MDR 廠商的 mean-time-to-detect 是 18 分鐘、mean-time-to-respond 是 47 分鐘。Athena 的 demo 證明 18 分鐘攻擊者已經三段全破,我的 MDR 必須降到個位數 minutes 才有意義。Renewal 我會明確提出 MTTR < 10 min 的 SLA,做不到就換廠商。

2. **紅隊 AI 武裝化**:增加 30-50% budget 給 internal red team,target 是把 cycle time 從一週級別壓到一日級別。具體方式包括:採購商業 AI 紅隊產品(如果 Athena 商業可採購,我會列入評估)、訓練 red team lead 自己 build 類似系統、跟 MSSP 合作做 quarterly AI-augmented exercise。

3. **Hybrid identity hardening**:這是 Alex 段直接刺激出來的 line item。我家 Entra Connect / AD FS / PTA 整套架構需要重新做一次 attack surface review,加上 conditional access policy 強化、Token theft detection、PRT 監控。預算大概在 NT$ 千萬等級。

這場 talk 對我 fiscal year budget 的影響大概是 ±3-5%(在 8 位數的 baseline 上),但對「我怎麼向 board 解釋這些調整」的影響是 100%。30 分鐘換來下半年董事會議簡報的 framework — 對 CISO 來說,這是當天最 high-leverage 的投資。
