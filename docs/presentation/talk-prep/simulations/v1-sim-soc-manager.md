# v1 模擬聽眾回饋 — 甲方藍隊 SOC 主管

**版本：** v1 (2026-05-06 deck)
**模擬日期：** 2026-05-06
**場景：** CYBERSEC Taiwan 2026 30-min Breakout Session（Harry 20 min on-prem AD demo + Alex 10 min cloud pivot）

---

## Persona Profile

我管台灣某 Tier-1 金控的 SOC，團隊 12 人 24x7，~5000 endpoints，AD + Entra ID hybrid 環境，技術棧是 Splunk + CrowdStrike Falcon + Microsoft Defender XDR。每天讀 MITRE ATT&CK feeds、Mandiant、CrowdStrike intel briefing。內部 KPI：IR MTTR 4 小時、初步 triage 15 分鐘、CIS 與 ISO 27001/CMMC 合規。今天來 CYBERSEC 是因為老闆問了我一句「AI 紅隊跟我們有什麼關係」，而我正在寫明年的 detection roadmap — 我得回去交代：(1) 這些攻擊在我的 SIEM 裡長什麼樣？(2) 我的 detection rule 要怎麼調？(3) Conditional Access 政策夠不夠？(4) 能不能拿 Athena 來做 purple team？

---

## 回饋表

| 項目 | 評分/回答 |
|------|----------|
| A. 整體滿意度 | **3/5** |
| B. 學到新東西 | **3/5** |
| C. 跟我有關 | **4/5** |
| D. 回去會行動 | **3.5/5** |
| E. 一句話回饋 | 「Slide 33 的設定錯誤全景表是我下週 hardening review 的 baseline，slide 43 的 AS-REP OPSEC 那段讓我冒冷汗 — 但整場沒有一條 Splunk SPL、沒有一條 KQL、沒有一條 Sigma rule，我這場聽完還是不知道我的 SIEM 抓不抓得到。」 |
| F. 最記得的 | Slide 43 那句「padata: (empty)、etype rc4-hmac、網路上看起來就是一次正常的 AS-REQ、noise_cost: 2」— 這直接戳中我最焦慮的事。我的 Splunk Windows Security 4768 rule 只在 PreAuthType=0 加上 ticket etype=rc4 同時觸發才告警；但「合法 Kerberos 流量」這四個字讓我懷疑我的 baseline alert 在 production 一定噪音爆炸所以被同事關掉。回去第一件事是 grep 我們的 detection lib 看那條 rule 還活著沒。 |
| G. 最想滑手機時刻 | Slide 8（軍事 C2→C5ISR 演化）整個段落跟 slide 22（為什麼 OODA + C5ISR 接在一起）。我承認 framing 有意思，但對藍隊主管來說「兵種協同 → 作戰體系」是 leadership keynote 的詞、不是技術 talk 的詞。Slide 28 那個大字 30× TEMPO IS THE WEAPON 也很想跳過 — 我知道 AI 快、我焦慮的不是修辭，我焦慮的是我 IR playbook 的 SLA 從 4 小時要改成多少分鐘。Slide 17 的 Brier score 0.31→0.12 對我也沒意義，那是給 ML 工程師聽的，不是給 SOC 聽的。 |
| H. 同事問怎說 | 「上半場 Harry 的 demo 蠻硬的，三台靶機全強密碼、AS-REP + ADCS ESC1 + secretsdump 串起來 18 分鐘破到財務 DB。但這場 talk 的問題是：他從攻擊者視角講完整套，沒有切到藍隊的 telemetry。我們需要的是『這台 DC 上 Event ID 4768 + 4769 應該長什麼樣、什麼參數可以拿來寫 detection』、『certipy req 在 Defender for Identity 會不會 alert』、『secretsdump 走 SMB 在 CrowdStrike telemetry 會不會看到 lsass open handle』— 這場全部沒講。Alex 那 10 分鐘把 Storm-0558/Midnight Blizzard/Volt Typhoon 串起來 frame 成 hybrid identity 威脅還算切題，但時間太短。三個 takeaway：(1) 拿 slide 33 當我 AD hardening checklist，(2) 把 slide 43 的 AS-REP padata empty + etype 23 拿回去 audit 我們的 rule，(3) 把 Alex slide 7 防守者三問直接帶到下次 CISO meeting。其他都是知識更新、沒有可立即落地的 detection 規則。」 |

---

## 詳細分析

### 為什麼 A / B / C / D 是這個分數

**A 整體滿意度 3/5。** 對非藍隊聽眾這場可能是 4 或 5，但對我這個職位它的命中率有限。30 分鐘把雙講者 + on-prem demo + cloud pivot + APT case studies 都塞進來是合理 trade-off，但代價是每一段都只能停留在「攻擊面是什麼」的層次，沒空回答「我怎麼看見它」。我整場期待的「telemetry chapter」從頭到尾沒出現。

**B 學到新東西 3/5。** AS-REP roasting / ADCS ESC1 / secretsdump 我都熟（我們去年自己跑過 BloodHound on-prem audit），但 slide 32 那個「200+ 次 demo 的三個 failure mode（EDR 擋 LSASS、Bloodhound timeout partial facts、平行鏈 race condition）」是這場我覺得最 honest 的一張 — 因為它承認 AI 紅隊不是萬能的、有真實的工程 trade-off。Slide 25 那個「failed technique cooldown 30 min」也是個我沒想過的細節 — 我以為 AI 紅隊只會狂打同一招直到被擋，原來他們有 retry policy 跟我 IR 那本 playbook 的 backoff 一樣概念。Alex 段把 Storm-0558 / Midnight Blizzard / Volt Typhoon 三個 case 並列 frame 成「混合身分都是同一場戰爭」這個敘事我之前沒這樣串過，蠻有用。

**C 跟我有關 4/5。** 命中度很高 — AD demo + hybrid identity blast radius 就是我每天 Splunk 上看的那張圖。Slide 33 的「五條設定錯誤、沒有一條跟密碼有關」直接呼應我們去年做完 Microsoft Defender for Identity Secure Score 之後的結論。slide 51 secretsdump 走 SMB 看起來是合法 admin 流量這件事 — 對，這就是我為什麼睡不好的原因之一。Alex slide 5 那張 blast radius 圖（AD → hybrid → Azure tenant → M365 → Key Vault → 跨雲供應鏈）是我下週 risk register 要重畫的。

**D 回去會行動 3.5/5。** 不是 4 或 5 是因為我帶走的不是 detection rule、是 hardening checklist。檢查 ESC1 三條件、grep 我們 KEV/legacy 帳號的 DoesNotRequirePreAuth、audit ADCS 模板 enrollment ACL、檢查我們有沒有 Microsoft Defender for Identity 的 ADCS sensor — 這些都是我的 hardening work，不是 SOC detection work。我下週 AD team 會收到我一張 ticket 清單，但我的 detection engineer 還是會問我「老闆，我的 Sigma rule 要寫什麼」— 而我答不出來。

### Harry 段（on-prem AD demo）我的感受

**開場三條信條（slide 4）+ chapter 1 traditional kill chain（slide 6-7）：** 我懂他們在做敘事的鋪陳，但對我來說 fact-driven / doctrine-beats-tools / tempo-is-the-weapon 三個詞重複太多次。第三次看到 30× 的時候我開始想我中午吃什麼。藍隊聽眾是來找規則的、不是來聽哲學。如果是給 CISO 聽的 keynote 我會接受，30 分鐘技術 breakout 我覺得三個 doctrine 在 slide 4 出現一次、slide 58 refrain 一次就夠了 — slide 28 那個 full-screen 30× 大字應該換成「攻擊速度從 1 天壓到 20 分鐘 — 你的 IR SLA 還是 4 小時嗎」這種對藍隊有殺傷力的句子。

**Architecture chapter（slide 14-20 引擎室）：** 這段我跟一半。動態路由 vs hardcoded dict（slide 19）、tools/list schema 當 sandbox（slide 20）、dead_end facts 寫回 DB 影響後續決策（slide 25）— 這些對我規劃 purple team 有參考價值。如果我們以後要拿 Athena 做 internal red team automation，我需要知道它的工程 boundary 在哪。但 Brier score 0.12（slide 17）那種 ML metrics 對 SOC 沒意義，那段時間我希望被拿來講「Decide engine 的 noise_budget 100 是怎麼跟我 Splunk 上的 telemetry 量對應的」— 因為 noise_cost: 2（slide 43）這種 number 如果能跟「在你的 SIEM 上會產生 N 條 log」mapping，那就變成 purple team 計分卡。

**Operation demo（slide 29-54）這段最硬，也是我最有感的：**

- **Slide 33（AD 設定錯誤全景）** — 5 條（ASP.NET injection / DoesNotRequirePreAuth / ADCS ESC1 / unconstrained delegation / xp_cmdshell）我整張拍照當 hardening review checklist。重點是最後那行「五條，沒有一條跟密碼有關」— 這是我下週跟資安委員會講「為什麼密碼政策變嚴沒用」最直接的素材。
- **Slide 41-43（AS-REP roasting 原理 + OPSEC）** — 整場最讓我冒冷汗的段落。slide 43 三點（padata 空、enc-part rc4-hmac etype 23、看起來像合法 AS-REQ）我得回去用 KQL 查 DC 的 4768 events 看我有沒有 baseline 鎖 PreAuthType=0；如果有，那 noise level 是多少；如果沒有，detection engineer 下週要寫一條 SecurityEvent | where EventID == 4768 and PreAuthType == 0 and TicketEncryptionType == 0x17 的 query。但講者沒給這條 query — 我得自己寫。
- **Slide 45-47（ADCS ESC1）** — 三條件（ENROLLEE_SUPPLIES_SUBJECT / Client Auth EKU / low-priv enrollment ACE）我們去年做 Microsoft Defender for Identity 升級的時候有掃過，但 certipy req 那條 transaction 在我的 SIEM 裡會留什麼 log、Defender for Identity 會不會自動 alert、AD CS 4886 event 是不是 baseline 監控 — 這場沒回答。我下週要 ping 我 AD team 確認 ADCS auditing policy。
- **Slide 51（secretsdump 走 SMB）** — 「防火牆無感、Windows 把它當作日常檔案分享流量」這句講出來的時候我心裡 OS 是「對 — 然後呢？」。我的 NDR（Vectra）對 SMB ADMIN$ + IPC$ 連線有 detection model，但一個 DA 走 secretsdump 跟一個 sysadmin 走管理工具的差別只在 LSASS handle pattern 跟 session token freshness — 這些 EDR telemetry 怎麼長、CrowdStrike 抓不抓得到，講者沒告訴我。

**收尾 lessons learned（slide 55）+ doctrine refrain（slide 58）+ closing（slide 59）：** 「AI 不會取代紅隊，AI 會把紅隊速度乘 30 倍」這句話是給紅隊聽眾的安慰，對我藍隊來說我在意的是「我的紅隊速度乘 30，我藍隊的 detection latency 也要乘以 1/30 嗎」— 這是這場 talk 沒回答的問題。

### Alex 段（cloud pivot）我的感受

**Slide 1-3（接手敘事 + DA 是入場券 + C5ISR 延伸到雲端）：** 開場「Domain Admin → ?」轉場接得乾淨，比 Harry 的 doctrine refrain 更有力。地端 ↔ Entra ID/Azure/M365 的 split 完全是我每天看的圖。C5ISR 延伸表（ISR 從 nmap 變 IMDS / Comms 從 Kerberos 變 PRT/refresh token）— 這個 framing 我會抄到下次 SOC 月會的開場 slide，因為它一張表就解釋為什麼「我的 AD 監控和我的 cloud 監控是同一張威脅圖」。

**Slide 4（flAWS Orient JSON real log）：** 這張是 Alex 段最強的證據 — 真實 log、rec_id、timestamp、三個 confidence option。對我的價值不是「AI 怎麼判斷」，是「如果我們以後跑 cloud pentest exercise，這種 JSON 結構可以當 purple team kill-chain 的 telemetry-to-decision mapping」。但跟 Harry 段一樣 — 這張沒告訴我 SSRF + IMDS 那個 transaction 在我 AWS GuardDuty 上會看到什麼 finding type、我的 CloudTrail logs 應該 query 什麼、我 CSPM（我們用 Wiz）有沒有 detection rule。

**Slide 5（blast radius 圖）：** AD 立足 → 混合身分 → Azure tenant → M365 → Key Vault → 跨雲供應鏈。這張我會直接抄到我的 risk register。但我希望 Alex 在這停 30 秒講「對應的 detection 控制點是什麼」 — Conditional Access 的 sign-in risk policy 卡哪一段、Identity Protection 的 user risk 卡哪一段、Defender for Cloud Apps 的 anomaly detection 卡哪一段 — 結果他直接跳到 in-the-wild。

**Slide 6（Storm-0558 / Midnight Blizzard / Volt Typhoon）：** 這三個 case 我都跟過 IR briefing，但把它們放在同一張並列說「差別只在工具是 Python script 還是 AI」這個 framing 對我是新的。我下次 board threat briefing 直接抄。

**Slide 7（防守者三問）：** 這張是 Alex 段對藍隊主管最 actionable 的一張 — 三個問題（紅隊看不看得到 cloud + on-prem 同時、SOC 把 AD/Entra/M365/key 視為同一張圖嗎、IR 跟得上 AI 速度嗎）我直接帶去 leadership briefing。但問題是 — 答案如果是 no，我下一步該做什麼？這場沒給。如果這頁可以加一個 reference architecture（哪些 telemetry 要接、哪些 detection rule 要寫、哪些 Conditional Access 要強化），那就完美了。

**整體：** Alex 10 分鐘 cover hybrid identity 我覺得 frame 對了但 depth 不夠 — 不是他的錯，是時間限制。他能做的就是把雲端「核彈當量」拍給觀眾看 → 製造焦慮 → 留 takeaway 三問。他做到了。但對我來說，他這 10 分鐘比 Harry 的 20 分鐘更值得 — 因為 Harry 講的我大部分知道，Alex 講的 cloud pivot 是我下個季度 detection roadmap 的重點。

### 我會帶回去做的三件事

1. **拿 slide 33 跟 slide 43 直接做 detection gap analysis。** 下週一 detection engineer meeting 我會把這張表發下去，每一行配對我們現有的 Splunk SPL / Defender XDR KQL，沒 cover 的就排進 Q3 detection backlog。重點：AS-REP roasting（4768 PreAuthType=0 + etype rc4）、ADCS 4886 + 4887 monitoring（檢查我們有沒有開 ADCS auditing policy）、SMB secretsdump（Defender for Identity Honeytoken + LSASS open handle from non-svchost EDR rule）。
2. **重畫 risk register 的 hybrid identity blast radius。** 拿 Alex slide 5 的圖，把 AD → 混合 → Azure tenant → M365 → Key Vault → 跨雲這條鏈，配對我們現有的 Conditional Access policy / Identity Protection policy / PIM elevation / Privileged Access Workstation — 看哪幾段是 unattended。下次 risk committee 用這張當 attack tree。
3. **跟內部 red team 提 purple team exercise。** 我們有自己的 internal red team（外包 + 內部 2 人）— 把 Athena demo 的 18 分鐘 timeline 當 baseline，內部 red team 要 reproduce 一次（不用 AI，純手動），讓我的 detection 在每一個 stage 至少觸發一條 alert，量我們的 detection coverage 跟 mean-time-to-detect。如果結果是某段 stage 完全沒 alert（例如 secretsdump 過 SMB），那就是下個 sprint 的 detection R&D priority。

### 我希望多講 / 少講的

**多講（這場最大缺口）：**

- **每一個 demo stage 對應的 telemetry 範例。** WEB01 RCE → IIS w3wp.exe spawn cmd.exe（Sysmon EID 1 + parent process）；AS-REP → 4768 event 範本；certipy req → ADCS 4886/4887 event；certipy auth PKINIT → 4768 with certificate；secretsdump → 4624 type 3 + LSASS handle from impacket process tree。每張 demo slide 旁邊配一條 Sigma rule yaml 我會給 5/5。
- **Alex slide 7 防守者三問的「如果答 no，下一步是什麼」。** 三問本身是 leadership material，但配一張「防禦架構五件事 — Conditional Access location/risk-based、Identity Protection user risk、PIM JIT、Defender for Identity ADCS sensor、Defender for Cloud Apps anomaly」對我落地價值會翻倍。
- **Athena 能不能當 purple team automation。** roadmap（slide 56）那四條（multi-domain / stealth / persistence / federated LLM）我有興趣，但我更想知道「AUTO_FULL 模式可不可以加一個 PURPLE_TEAM mode — 每執行一次 technique 就 generate 預期的 SIEM event signature 給藍隊比對」。如果能，這個工具的市場價值對我這種甲方 SOC 主管會直接乘 10。

**少講：**

- **C2 → C5ISR 軍事演化史（slide 8）整段。** 一張 slide 講「軍事先解決過、我們直接借」就夠，不需要兩張對比。
- **Slide 22（為什麼 OODA + C5ISR 要接在一起）那種 framework 對 framework 的元層討論。** 對 framework geek 有意思，對 SOC 沒用。可以濃縮成 slide 23-27 上方的 navigation breadcrumb。
- **Slide 28 30× TEMPO IS THE WEAPON 全螢幕大字。** 全場 doctrine refrain 已經三次（slide 4 prologue / slide 28 / slide 58 refrain），對藍隊聽眾邊際效用為負。把這個版位換成「AI 紅隊 18 分鐘到 ACCT-DB01 — 你的 IR triage 還是 15 分鐘嗎」這種對藍隊有殺傷力的句子，我會直接醒過來。
- **Slide 17 Brier score 0.12。** 對 ML 工程師有意義，對 SOC 主管 / pentester / 紅隊都沒用。改成「200 輪 demo 中 36% 第一推薦失敗 → 系統自動換路、平均 2.3 輪內找到 alternative」這種對工程實務有感的 metric，比 Brier score 強 10 倍。

---

**Bottom line：** 這場 talk 對 CISO / 紅隊 / 紅隊 vendor 是 4/5，對技術藍隊主管是 3/5。命中我的焦慮（AI 速度、AD 設定錯誤、hybrid identity blast radius）— 但沒給我任何一條可以直接拿去寫 SIEM detection rule 的 telemetry 範例。我帶走的是 hardening checklist + risk register update + leadership briefing material；我沒帶走的是任何一條 SPL / KQL / Sigma。如果 v2 deck 能在 Harry 段每個 demo stage 加一條 detection rule yaml 範本（哪怕只是 commented-out 的），這場對藍隊聽眾就從 3/5 跳到 4.5/5。
