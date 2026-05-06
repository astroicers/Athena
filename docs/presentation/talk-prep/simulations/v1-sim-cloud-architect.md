# v1 模擬聽眾回饋 — 企業雲端架構師（製造業）

**版本：** v1 (2026-05-06 deck)
**模擬日期：** 2026-05-06
**場景：** CYBERSEC Taiwan 2026 30-min Breakout Session

## Persona Profile

製造業中型企業（約 1500 員工，半導體周邊製造）的 cloud architect。地端一個 forest 加三個 sub-domain，約 3000 endpoints。Hybrid identity 兩年前上線：Entra Connect + Azure AD Connect Health + Conditional Access，M365 全公司用，ERP 正在分批移轉到 Azure。CTO 上禮拜開會問「我們的 AI 防禦怎樣？對方是 ChatGPT，我們是什麼？」我來 CYBERSEC 找答案，特別是雲端那段。

---

## 回饋表

| 項目 | 評分 / 回答 |
|------|------------|
| A. 整體滿意度 | **4/5** |
| B. 學到新東西 | **3.5/5** |
| C. 跟我有關 | **4.5/5** |
| D. 回去會行動 | **4.5/5** |
| E. 一句話回饋 | 「Harry 段是 demo，Alex 段是診斷書 — 那張 8 節點 blast radius 我下週直接放進 board deck，三個提問直接給 CTO。」 |
| F. 最記得的 | **Alex slide 59「核爆當量 8 節點 blast radius」** — 從「初始入侵 → AD 立足 → DA → 混合身分 → Azure 租戶 → M365 信箱 → Key Vault → 跨雲供應鏈」一條鏈拉完。我以前只能跟 CTO 講「DA 漏了會很慘」，他聽完一臉「多慘？」。這張圖回答了那個問題：DA 是中段，不是終點。後面還有四個節點是我們真正資料住的地方。Alex slide 56 那句「DA 不是終點，是入場券」更狠 — 因為我之前真的用過這個句子安慰自己（DA 沒被打到應該還好），現在才意識到自己框架就錯了。 |
| G. 最想滑手機時刻 | Slide 14-20（Architecture / Orient JSON / Decision Engine / 17 個 MCP / 動態路由 / Schema sandbox）。我承認 confidence = (LLM × validation × history)^(1/3) 這個公式很乾淨，但我不寫 Python、不調 LLM、也不會建 MCP server — 這 7 張對我像背景噪音。我大概有 3 分鐘在偷看 LinkedIn。Slide 41-48 的 AS-REP / certipy / hashcat 細節我也跟不上 — 概念知道，但我不會手動 reproduce，知道結果就好。後面 slide 60 的 Storm-0558 / Midnight Blizzard / Volt Typhoon 三段我也覺得太國際視角，我想知道台灣 / 製造業同業有沒有被打過。 |
| H. 同事問怎說 | 「值得聽的不是 demo（demo 你看完 slide 54 那張 20 分鐘 / 3-3 / 0 介入的 tile 就懂了），值得聽的是後面 10 分鐘那段雲端。Alex 把 DA 為什麼不是終點、hybrid identity 為什麼是真正的控制面講清楚了 — 這個觀念之前我跟老闆講不清楚。下禮拜我會先抓我們三個 sub-domain 的 ESC1 + AS-REP 自檢，然後拉一張我們公司版的 8 節點 blast radius 給 CTO。重點不是工具，是那張圖跟那三個提問。」 |

---

## 詳細分析

### Harry 段（on-prem AD demo）我的感受

老實說，前 20 分鐘給我的感覺是「精彩但不是給我聽的」。我很久沒看 AD 攻擊 demo 了，看 AS-REP Roasting + ADCS ESC1 + secretsdump 串成一條 18 分鐘的鏈，當下確實有 wow factor — 特別是 slide 34 那張「密碼全部強密碼」配 slide 33 的「五條 AD 設定錯誤，沒有一條跟密碼有關」對比，這個 framing 我會偷走。我們公司年度資安檢核還在問「員工密碼複雜度是否符合規範」，slide 33 + 34 就是給 CTO 看為什麼這個問題已經過時了。

但我必須誠實 — slide 14-20 那段 Architecture（Orient JSON、Decision Engine 三道閥、0.87 怎麼算、17 個 MCP、hardcoded dict → 動態路由、Schema sandbox）對我來說是 7 分鐘的注意力黑洞。我知道講者在炫技、在說「這不是隨便接 ChatGPT API」，但我沒有要建這個系統，我要的是「對方怎麼打我」跟「我怎麼擋」。Brier score 從 0.31 降到 0.12 — 這對 ML engineer 是賣點，對我是雜訊。

Slide 33（AD 全景）對我超有用。我們公司 ADCS 沒在用（鬆口氣），但「無約束委派」「DoesNotRequirePreAuth」「xp_cmdshell」這三條我一個都不敢保證 0 個案例。這張表我直接拍下來當下週 AD audit 的 checklist。Slide 47（ESC1 三條件）也是 — 雖然我們沒上 ADCS，但下個 sprint 萬一要用，我已經知道哪三個 flag 不能勾。

Slide 54 那個 4-tile（20 min / 3-3 / 0 人工 / 100% 信心可解釋）就是我帶給 CTO 的封面。CTO 問「對方是 ChatGPT，我們是什麼」— 答案就在這張 tile 上。20 分鐘、零介入、可重播。我們的 SOC SLA 是 P1 事件 4 小時內 acknowledge — 我自己想就臉綠。

Slide 32（踩過的坑）我意外覺得有用。EDR 擋 LSASS dump 後 composite confidence 自動降到 0.34、改走 SAM hive — 這個「失敗會記憶、會調整」的細節，回答了我心裡那個「AI 不就是瞎猜嗎？」的疑問。我會用這張說服老闆：對方不是運氣，是體系。

### Alex 段（cloud pivot）我的感受

**這 10 分鐘是我整場最有感的部分，特別是 slide 56-61 這 6 張。**

**Slide 56（DA 不是終點 — 是入場券）—** 開場那句把我釘住了。我之前自我安慰的邏輯就是：「DA 我們有 audit、密碼有輪替、PAM 有上、應該還好」。Alex 一句話把這個邏輯打掉：DA 不是城堡的鑰匙，是登機證。後面的飛機才是真正裝資料的地方。我們公司客戶資料、CTO 信箱、Azure Key Vault、ERP credentials — 這些東西沒有一個住在地端 AD。如果攻擊者拿到 DA 後 5 分鐘就 pivot 到 Entra ID 然後拿 Global Admin，我地端再硬也沒意義。**這一張 slide 我會 screenshot 給 CTO，標題就改成「為什麼地端 AD audit 不夠」。**

**Slide 57（C5ISR 雲端對應表）—** 這張我會直接抄進我們公司的內部 wiki。左欄地端、右欄雲端，ISR / Computers / Comms / Cyber 各一行。我跟 platform team 跟 SOC team 平常各講各的語言：platform team 講 Entra principal、SOC 講 KQL alert、我講 architecture diagram。這張表是「同一場戰爭的不同前線」這個 framing — 我可以拿來說服 SOC 把 AD 4768 / 4769 跟 Entra sign-in log 接到同一個 dashboard。下個 sprint 我會跟 SOC lead 開會，這張表就是 talking point。

**Slide 58（flAWS Orient JSON）—** 我必須說這張對我有點吃力。JSON 我看得懂，但 T1190 / T1046 / T1592.004 這三個 ATT&CK 編號我得 google。但那個 punchline 我接到了：「小兵看到三個選項都試一遍。指揮官看到 SSRF 確認 + IAM role 已 enum — 選 0.95，跳過 0.75 / 0.65。」這對我的 takeaway 是：**對方不會在我們前面亂試，他們會看 fact 直接挑最高分那條打。** 我們 SOC 現在的 alert 設計是「行為偵測」— 假設攻擊者會在多個低分動作之間試錯。如果對方是指揮官式 AI，這個假設就破了。這張我會帶到 SOC review。

**Slide 59（核爆當量 8 節點 blast radius）— 這張是我整場最重要的單一 slide。** 從「初始入侵 → AD 立足 → DA → 混合身分介接層 → Azure 租戶 → M365 信箱 → Key Vault → 跨雲 / 供應鏈」一條鏈下去，每一個節點都是我們公司真實有的資產類別。我下週要做 board 簡報的「AI 威脅 briefing」— 第一張就是這個。我打算把節點換成我們自己的：「初始入侵 = 釣魚 → AD 立足 → DA → Entra Connect → 我們的 Azure tenant → CTO/CFO 信箱 → 我們的 Key Vault（裡面有 ERP DB password 跟客戶 API key）→ 上下游客戶租戶」。8 個節點變成董事會看得懂的 8 個風險。傳統 CVSS 那種 10 分制根本算不出這種跨資產當量 — 這正是 Alex 說的「核爆當量」。

**Slide 60（真實事件 Storm-0558 / Midnight Blizzard / Volt Typhoon）—** 這張我反而沒那麼有感。不是不重要，是太國際視角。Storm-0558 我兩年前就在新聞看過，Volt Typhoon 跟 LOTL 我們 SOC 也聽過簡報。我希望這張能換掉一個 case 變成「台灣本地 / 製造業同業」的案例 — 哪怕只是匿名化的「某半導體相關企業 2024 年透過 Entra Connect 被打」也好。我來這場 talk 的潛台詞是「我隔壁工廠有沒有出事」，這張沒回答我的潛台詞。

**Slide 61（三個提問）— 直接帶給 CTO。** 「紅隊能同時看到雲端 + 地端嗎？」「SOC 是否把 AD / Entra / M365 / 雲端密鑰當成同一張圖？」「事件應變跟得上 AI 攻擊速度嗎？」這三題我們公司答案分別是：no（紅隊外包，他們只測地端）/ no（兩支 dashboard）/ no（4 小時 SLA vs 20 分鐘 kill chain）。三個 no 就是三個下季度 OKR。**這張 slide 比我自己寫一頁紙說服 CTO 撥預算還有效。**

### 我會帶回去做的三件事

**第一件 — 下週的 CTO briefing。** 用 slide 54（4-tile mission complete）開場、slide 56（DA 入場券）做 framing、slide 59（8 節點 blast radius）做衝擊、slide 61（三個提問）做 ask。整套素材 4 張 slide，30 分鐘 briefing。CTO 上禮拜問的「我們的 AI 防禦怎樣」我這次有答案：我們現在 0/3，我需要這三件事的預算。

**第二件 — 下個 sprint 啟動 hybrid identity audit。** 不是 AD audit，是 hybrid identity audit。具體三個動作：(1) AS-REP Roasting 全 forest 自檢（slide 41-43 的概念，我會用 Get-ADUser filter DoesNotRequirePreAuth），雖然我以為應該沒事但 Alex 一講我就決定要驗一遍；(2) Entra Connect 帳號的 sync scope 重審 — 這個 service account 漏了等於 slide 59 的 4 號節點開門；(3) Conditional Access 對 break-glass account 的覆蓋 — 我們現在的 CA policy 排除 emergency account，這就是 Storm-0558 那種 token 偽造的入口。這三個我會在下個 sprint backlog 開三張 ticket。

**第三件 — 跟 SOC lead 開會做 dashboard 整併。** 用 slide 57 那張對應表當 agenda。把 AD 事件（4768/4769/4624）跟 Entra sign-in log、Azure activity log、M365 audit log 接到同一個 SIEM view，並設一條 cross-correlation rule：「同一身份 30 分鐘內出現 AD privileged action + Entra anomalous sign-in」就 page on-call。這條規則就是 slide 61 第二題的具體答案。

### 為什麼 A 是 4 不是 5

整體 4 分而非 5 分，原因有三：

第一，前段 Harry 的 architecture 那 7 張對我是純損耗。如果我是 ML engineer 或紅隊工程師會給 5，但我是 cloud architect — slide 14-20 對我的價值低於滑手機看 LinkedIn。30 分鐘的 talk 有 7 分鐘對我無感是真實的 cost。

第二，slide 60 那三個 APT 案例如果有一個換成台灣本地或亞太區的，這場 talk 對我的「在地相關性」會直接 +0.5。製造業聽眾來看 talk 是想知道隔壁工廠有沒有出事，國際 case 滿足不了這個潛台詞。

第三，Alex 段時間太短。10 分鐘要把「DA pivot 雲端 + hybrid identity blast radius + 三個 APT case + 三個提問」全塞進去，每一張都只能停 1 分鐘。我希望 slide 59 的 8 節點 blast radius 多 60 秒（每一個節點停 5 秒讓我吸收）、slide 61 的三個提問多 30 秒（讓我有時間想我們公司的答案）。如果整個 30 分鐘是 Alex 主講、Harry 段壓到 15 分鐘只展 demo + 結論，我會給 5 分。但這不是這場 talk 的設計，我接受。

**整場最高 ROI 就是 slide 56 + 59 + 61 這三張。** 每一張都能直接放進 board deck。10 分鐘換 3 張可用 slide，CP 值極高。

### 一個我希望加的 — 一個我希望砍的

**希望加的：在 slide 60 之後加一張「台灣製造業同業匿名 case」。** 不需要點名，可以說「2024 年某半導體周邊製造業，員工 2000 人左右，hybrid identity 上線 3 年。攻擊者透過釣魚拿到一個 helpdesk 帳號，3 天內 pivot 到 Entra Global Admin，最終影響 X 個客戶租戶」— 這種敘事會讓「核爆當量」從理論變成同業教訓。我猜講者沒講是因為 NDA，但哪怕用 CISA 公告 / iThome 報導 / 研究單位 case study 也好。對台灣聽眾，本地案例的衝擊力是國際案例的 3 倍。

**希望砍的：Slide 17（0.87 怎麼算的 — 拆解 confidence）跟 slide 20（Schema 是介面，也是 sandbox）。** 這兩張是 internals。對 ML engineer / pentester 寫 doctrine 的人是黃金，對我這種讀架構圖的人是負擔。如果要保留，建議合併成一張並把 Brier score / Laplace smoothing / prompt injection allowlist 全收進 backup slide，需要的人 Q&A 再問。**砍掉這兩張可以多 90 秒給 Alex 段的 slide 59，整場對 cloud architect 觀眾的價值密度會明顯上升。**

整場下來，我覺得 Harry 段提供了 demo 衝擊（讓 CTO 願意撥預算），Alex 段提供了戰略框架（讓我知道預算花哪裡）。兩段缺一不可，但對我這個 persona，後 10 分鐘的單位時間價值是前 20 分鐘的兩倍。**這是 cloud architect 來這場 talk 的正確期待管理 — 你要忍前 20 分鐘的紅隊噴飯時刻，後 10 分鐘才是給你的。**
