# v1 模擬聽眾回饋 — AI/ML 研究員（agentic AI lens）

**版本：** v1 (2026-05-06 deck)
**模擬日期：** 2026-05-06
**場景：** CYBERSEC Taiwan 2026 30-min Breakout Session

## Persona Profile

台灣某大學 NLP / agent lab 的 applied ML 研究員，2 年資。研究方向是 LLM agent framework — long-horizon planning、tool use、self-correction，發過兩篇 paper（一篇 EMNLP 2025）。讀完 ReAct (Yao 2022)、Tree-of-Thoughts (Yao 2023)、Reflexion (Shinn 2023)、HuggingGPT、MetaGPT、PentestGPT (Deng 2023)、Nebula、AutoAttacker 後，覺得**資安越來越像 agentic AI 的 testbed** — 真實 long-horizon、有 ground-truth reward、有 adversary。今天來 CYBERSEC 是想看 Athena 是不是真的有 doctrine，還是 LangChain 加軍事 buzzword。

## 回饋表

| 項目 | 評分/回答 |
|------|----------|
| A. 整體滿意度 | **3/5** |
| B. 學到新東西 | **3/5** |
| C. 跟我有關 | **3.5/5** |
| D. 回去會行動 | **3/5** |
| E. 一句話回饋 | 「Slide 17 的 composite confidence + Brier 0.31→0.12 是全場唯一一個 ML researcher 會拍照存起來的 number。其他 30× / 0.87 / 'doctrine beats tools' 都是 marketing。」 |
| F. 最記得的 | Slide 17 的 `composite = (LLM × validation × history)^(1/3)` 加 Laplace smoothing `(s+1)/(t+2)` — 這是整場唯一**有 mechanism 的 calibration claim**。Brier score 從 0.31 降到 0.12 也是少數有 quantitative metric 的 slide。雖然 200 sample 太小、demo 環境不算 ground truth、沒講 calibration plot 怎麼做的，但至少他們有意識到 LLM confidence 是 uncalibrated — 這比 90% 講者已經高了。我心裡想：「OK，這個 team 知道 ReAct 的 confidence 不能直接用。」 |
| G. 最想滑手機時刻 | **Slide 28（30× TEMPO）**。一個巨大的 `30×` 浮在螢幕上，沒有 baseline、沒有 confidence interval、沒有 task-level breakdown。30× 是相對什麼？人類紅隊平均 10 小時？資深 OSCP holder 1 小時？完整的 nmap+manual+Metasploit pipeline？這個 number 不能 cite、不能 reproduce、不能 falsify。在我的 lab 這種 slide 會被 reviewer 直接退稿。**Slide 4（三條信條 prologue）**也一樣 — "DOCTRINE BEATS TOOLS" 是 slogan，不是 claim。我心裡 flag 了一下：這是 keynote 結構，不是 research talk 結構。 |
| H. 同事問怎說 | 「Engineering case study，不是 research breakthrough。最有意思的是兩個 design choice：(1) composite confidence 把 LLM-self-reported probability 跟 history success rate 跟 validation outcome 用 geometric mean 合成、用 Laplace 處理 cold start，這個不複雜但 thoughtful；(2) Slide 25 的 failure-fact + 30 min cooldown — 是 Reflexion 的 episodic memory 變體加上 transient-failure recovery，不錯的 hack。但對應的 evaluation 很弱：3 台 lab 機器、200 OODA rounds、沒有 baseline agent、沒有 ablation、沒有 token cost report。如果這是 EMNLP submission 我會 reject 但鼓勵 resubmit；如果這是 industry conference talk，可以聽。Slide 65（vs PentestGPT/Nebula）對比寫得太友善了 — Nebula 也有 RAG state 不只是 "partial"。」 |

## 詳細分析

### 技術論述審計（最重要的章節）

**Slide 13（Athena 引擎骨架 — OBSERVE/ORIENT/DECIDE/ACT）：基本 pass。** 把 OODA 對應到「facts DB write → LLM prompt → decision policy → MCP dispatch」這個 pipeline 是合理的。從 ML 角度看，這就是一個 **ReAct-style agent loop**（Yao et al., 2022 — *ReAct: Synergizing Reasoning and Acting in Language Models*），只是把 thought / action / observation 換成軍事術語。沒問題，**但也不要假裝這是一個新 architecture**。OBSERVE 寫進 PostgreSQL Facts DB 這個設計其實是 HuggingGPT (Shen 2023) 跟 MetaGPT (Hong 2023) 的 shared scratchpad 的 SQL 版本。把 short-term memory externalize 成 relational store 的好處是 multi-agent 共享 + replayable，這個我同意。但 deck 沒有講 facts retrieval policy（Orient prompt 裡塞多少 facts？token budget 怎麼控？舊 facts 怎麼 evict？）— 這才是 mechanism，不是 OODA × C5ISR mapping。

**Slide 15（Orient JSON 結構 + 三 options）：schema 設計合理，但沒有真的解釋「為什麼是 3 個 options」。** 這是一個 top-k action sampling 加上 ATT&CK technique ID 作為 hard structure。從 LLM 角度看，這是 **structured output / function calling** 的一個應用，跟 LangChain 的 tool calling 沒有本質差別。值得稱讚的是把 `mcp_tool` 跟 `technique_id` 解耦 — technique 是 doctrine layer 的決策 (T1558.004)，tool 是 execution layer 的派工 (impacket-ad:asrep_roast)。這個 two-level abstraction 在 PentestGPT (Deng 2023) 的 task tree 裡也有類似設計，但 Athena 把它寫成 fixed schema 比 PentestGPT 的 free-form text 容易 verify、容易 ablate。**沒解決的問題**：3 個 options 之間 confidence 的 calibration 怎麼互相約束？如果 top-1 0.87、top-2 0.71，這個 gap 是 LLM 自己估的還是有 normalization？deck 沒講。

**Slide 17（composite confidence — 核心技術論述）：這是全場最 ML-literate 的一張，但仍有缺口。**

公式 `composite = (LLM × validation × history)^(1/3)` 是 geometric mean over three independent signals。這個選擇我同意 — geometric mean 對單一極小值敏感，是「one-vote-veto」behavior，比 arithmetic mean 適合 OPSEC-critical decision。Laplace smoothing `(s+1)/(t+2)` 是 textbook Beta(1,1) prior 的 posterior mean，cold-start 用 0.5 是合理 default。

**但我有四個 reviewer questions：**
1. **Brier 0.31 → 0.12 的 ground truth 是什麼？** Brier score 需要 binary outcome — 「technique 成功 / 失敗」是用 `exit_code == 0` 還是 `new_facts > 0` 判定？validation_score 同時是 composite 的輸入跟 Brier 的 ground truth 嗎？這是 **circular evaluation**，會讓 Brier 看起來比實際好。如果是這樣，0.12 不可信。
2. **200 OODA rounds, demo environment** — sample size 太小、distribution shift 嚴重。Lab 環境的 EDR 行為跟 production 完全不同。我會問：post-deployment 在多少不同環境跑過？
3. **Calibration plot 在哪裡？** Brier score 是 scalar metric，但 calibration 的 visual diagnostic 是 reliability diagram (Niculescu-Mizil & Caruana 2005)。如果他們有 reliability diagram 應該要放出來。
4. **LLM_confidence 的來源？** Claude self-reported probability 是 token-level logprob 還是 verbalized probability（"I'm 87% sure"）？後者是出名 unreliable 的（Lin et al., 2022 — *Teaching Models to Express Their Uncertainty in Words*）。

整體：方向對，setup 嚴謹度不到 ML conference 標準，但比業界 99% 的「我 LLM agent 信心 0.9」高。

**Slide 19（hardcoded dict → dynamic LLM routing）：這就是 LangChain router chain。**

```python
# 新版本：
orient_resp = llm_orient(facts)
tool = orient_resp["mcp_tool"]
engine_router.dispatch(tool, args)
```

這跟 LangChain 的 `RouterChain` / `MultiPromptChain` 概念完全一致 — LLM 看 metadata 自己選 tool，新 tool 上線只要 register schema。**沒有新東西**，但他們應該也沒打算 claim 是新東西。我比較想看的是：**如果 LLM 選錯 tool（下游 fail），有沒有 reflective re-routing？** 這對應 Reflexion (Shinn 2023) 的 verbal RL — fail 之後 LLM 看 error trace 修正下次的 tool selection。Slide 20 提到「engine_router 驗 schema → 不合 → 回 Orient 重選 → 連續 2 次失敗 → 標 dead_end」，這就是一個 lightweight 的 reflective loop，OK，但「2 次」這個 magic number 沒解釋為什麼。

**Slide 25（failure-fact + 30 min cooldown）：thoughtful 的 episodic memory + transient-failure recovery，是全場我會抄回 lab 的 design pattern。**

把 `attempt.failed: T1003.001 / reason=edr_blocked` 寫進 Facts DB 然後在下一輪 Orient prompt 注入「以下技術已失敗，勿重推」— 這是 **Reflexion 的 episodic memory（Shinn et al., 2023）的工程化變體**。30 min cooldown 解決 transient failure 的問題（EDR 更新、新憑證），不會讓 agent 永久 stuck — 這個我覺得很好。比起 Reflexion 用 verbal feedback 在 prompt 裡 accumulate，把 failure structured 成 `(technique_id, reason, ts, cooldown)` 是更 maintainable 的工程設計。

**但仍有 missing piece**：reason 欄位是誰填的？LLM 自己 explain 失敗原因嗎？如果是 LLM hallucinate 原因（"我猜是 EDR 擋的"），那 cooldown logic 就不可信。應該至少從 MCP tool 的 stderr 抽 structured signal，或者用 rule-based 從 exit_code 推。Slide 25 沒講這個 detail。

**Slide 28（30× TEMPO）：no baseline = no claim。**

這是全場最讓我翻白眼的一張。「30 秒一個 OODA loop」對應的 baseline 應該是什麼？
- 人類紅隊資深 operator 平均處理時間（per kill chain step）？
- ReAct agent 在同 task 的 wall-clock？
- Tree-of-Thoughts (Yao 2023) 的 search-based agent？
- PentestGPT 的 prompt-loop interactive mode？

ML paper 沒有 baseline 是 desk reject。30× 在 industry talk 是「不錯的 marketing number」，但 ML researcher 看到只會問：30× faster than what, on what task, with what success rate?

**還有一個我特別在意的**：speed 是不是 trade-off accuracy？OODA 30s/loop 意味著 LLM 沒有時間做 deep reasoning（不能像 Tree-of-Thoughts 那樣 search 多條 branch）。如果他們犧牲 reasoning depth 換 tempo，那 30× speed 的代價是 false positive 增加 / dead-end retry 變多。這個 trade-off curve 應該要呈現，否則 30× 是無意義的數字。

**Slide 65（vs PentestGPT / Nebula / AutoAttacker）：對比不公平。**

| | Athena 對 PentestGPT 的描述 | 我的看法 |
|---|---|---|
| state | "✗（無狀態）" | PentestGPT (Deng 2023) 有 task tree state，是 hierarchical 而非 flat。寫 ✗ 不公平。 |
| auto | "半自動" | 對，這個 OK。 |

| | Athena 對 Nebula 的描述 | 我的看法 |
|---|---|---|
| state | "partial" | Nebula 有 RAG over exploit corpus + recent context。"partial" 是 dismissive 的標籤。 |
| auto | "✗" | Nebula 有自動 chain，雖然不像 Athena 那麼端到端。 |

更公平的比較應該包含：
- **AutoAttacker (Xu 2024)** — 已經被 deck 提到但沒對比 framework
- **PentestGPT** 的 Reasoning / Generation / Parsing module 拆解
- **CALDERA** with LLM extension（學術界已經有人做）
- **HackerGPT / WhiteRabbitNeo** — community fine-tuned models

Athena 的 differentiator 應該是：**(1) MCP 作為 tool abstraction layer**（這個確實乾淨）、**(2) composite confidence 加 noise budget 的量化決策**（這個確實少見）、**(3) PostgreSQL persistent state 加 advisory lock for parallel chains**（slide 32 提到）。把這三點講清楚比 dismiss PentestGPT 更有說服力。

### Harry 段我的感受（attention as ML researcher）

Slide 1-12（Doctrine 鋪陳）— 我大概 50% 在心裡 OOD。OODA 從 Boyd 韓戰 F-86 來、C5ISR 從美軍演化來 — 這些 narrative 對沒讀過 agentic AI 的觀眾應該很有用，但對我來說全部可以替換成「ReAct loop + memory module + tool router + safety layer」這個 ML vocabulary。我在等 mechanism。

Slide 13-20（Architecture）— 注意力回來了。Slide 17 的 confidence math 是我這場唯一打開筆電記筆記的一張。Slide 20 的 prompt-injection-via-MCP-description 是個我沒想過的 attack surface — MCP description 進 LLM context 是 untrusted input，這是 Greshake et al. 2023 (*Not what you've signed up for*) 的 indirect prompt injection 在 agent ecosystem 的具體案例。Athena 用 allowlist + 純 ASCII + 無祈使句限制 description，是合理 mitigation 但也不夠 — 用 Anthropic 的 prompt injection classifier 或 LLM-based filter 會更 robust。

Slide 22-28（Framework deep-dive）— 又開始飄。Slide 22 的 OODA × C5ISR 「為什麼接在一起」對我是廢話 — 我不在乎軍事框架的歷史，我在乎 prompt structure 的具體選擇。Slide 28 的 30× big number 已經吐槽過了。

Slide 29-54（Operation kill chain demo）— 從 ML 角度我注意的不是「攻陷了什麼」，而是 **trace 的 transparency**。每個 stage 都有 OPS LOG、寫進 Facts DB、有 fact key — 這個 explainability infrastructure 比大多數 LLM agent paper 強，trace 可以拿來做 evaluation 跟 ablation。Slide 32（踩過的坑）我特別欣賞 — 願意公開三個 failure mode（EDR 擋 LSASS、Bloodhound 超時、parallel race condition）是負責任的 engineering culture。advisory lock 那個 trick 我可能會抄。

整體：**Harry 的 20 分鐘對 ML 受眾來說 30% 有料、50% 是 doctrine narrative、20% 是 demo flair**。如果是 ML conference 我會要求把 doctrine narrative 砍到 5 分鐘、把 mechanism (slide 13-20, 25) 擴充到 12 分鐘、demo 留 3 分鐘 highlight reel。

### Alex 段我的感受

10 分鐘從 on-prem AD pivot 到 cloud / hybrid identity，**對我這個 ML researcher 不是核心興趣**，但有兩個技術點我認可：

1. **Slide 60 的 flAWS.cloud Orient log（rec_id 00e38a61）** — 這是全場 Alex 段唯一可 fact-check 的 trace。Athena 在真實 cloud range 跑通 SSRF→IMDS→AWS cred 這條鏈、Orient JSON 完整 dump 出來。從 reproducibility 角度 +1 — 大多數 agentic AI security paper 連 trace 都不公開。Confidence 0.95 跟 top-2 0.75 / top-3 0.65 之間的 gap 比 on-prem demo (0.87 / 0.71 / 0.60) 更明顯，這個 spread 是不是 Anthropic Claude 在 cloud-context 上更 confident 還是 task structure 不同？沒講。

2. **Slide 61 的 blast radius 視覺化** — 從 ML evaluation 角度，這個 framing 提示了一個 evaluation metric 的可能性：不是 single-target success rate，而是 **graph reachability over identity graph**。如果未來 Athena 想做 benchmark，定義「from initial entry, expected number of reachable assets within K OODA loops」會是有意思的 metric。

但 Alex 段的弱點是：**Storm-0558 / Midnight Blizzard / Volt Typhoon 三個真實 APT 案例**（slide 62）跟 Athena 之間的 link 沒接緊。「差別只在於 — 攻擊者用的是 Python script，還是 AI」這句很有戲劇性，但我作為 ML researcher 想看的是：Athena 是否真的 reproduce 了 Storm-0558 的某個 phase？如果只是「概念上類似」，那這三個案例就是嚇人 anecdote，不是技術 evidence。

### 為什麼 A / B / C / D 是這個分數

**A = 3/5（整體）**：技術上是有東西，但結構是 keynote 不是 research talk。30 分鐘塞了 doctrine narrative + architecture + 完整 kill chain demo + cloud pivot — 每個部分都被壓扁。對 ML 受眾來說 mechanism 講太淺，對 defender 受眾來說 mechanism 講太深。中間地帶不討好。

**B = 3/5（學新東西）**：composite confidence + Laplace smoothing + failure cooldown 是 thoughtful 的工程設計，我會抄；MCP description 作為 prompt injection 攻擊面是新角度；advisory lock for parallel agent chains 是 nice-to-know。但這些都是 1-2 行 takeaway，不是 paradigm shift。

**C = 3.5/5（跟我有關）**：agentic AI security 是我研究方向的 testbed，所以「跟我有關」的天花板就在那裡。Athena 的 evaluation methodology 給我一個 cautionary tale（不要這樣做 evaluation），這算正面 takeaway。

**D = 3/5（行動）**：lab meeting 我會 share slide 17 的公式 + slide 25 的 failure-fact 設計。可能會把 Athena 當成下一篇 paper 的 baseline 去復現（但因為 closed source 估計會 fail）。比較實際的行動是 — 下次寫 LLM agent paper 的時候，我會把 Athena 的 evaluation gap 當成 motivation：「現有 agentic security work（如 Athena）使用 200-sample lab evaluation，缺乏 calibration diagnostic 跟 baseline comparison。本工作提出...」。

### 我希望看到的 — 我覺得不需要的

**希望看到（30 min 以內可以塞）：**

1. **Calibration plot** — slide 17 加一個 reliability diagram (predicted prob vs empirical accuracy)，比 Brier number 有 10× 說服力。
2. **Token cost / latency budget breakdown** — 30s/loop 對應多少 token cost？Claude Opus 還是 Sonnet？per kill chain 的 total cost？這對 ML 受眾來說是 reproducibility 的基本資訊。
3. **Hallucination rate** — 17 個 MCP tool 中，LLM 推薦不存在的 tool 或不合理的 args 的比例？slide 20 提到 dead_end 機制但沒給數字。
4. **Ablation** — 拿掉 history smoothing、只用 LLM_confidence 直接決策，failure rate 升多少？這是 ML reviewer 一定會問的。
5. **vs ReAct / ToT baseline** — 即使是手寫的 baseline agent，也比沒有強。

**不需要的：**

1. **Slide 4 + Slide 58 的「三條信條」首尾呼應** — 一次就夠，refrain 對 ML 受眾是負分（感覺像被推銷）。
2. **Slide 8（軍事 C2 → C5ISR 演化史）** — 完全可以砍。對 doctrine framework 沒有 incremental info，對 ML 受眾零價值。
3. **Slide 33-34（密碼強度全部強密碼）** — 已經在 demo 結果展現了，不需要單獨兩張 setup。砍掉 1-2 分鐘。
4. **Slide 41 / 45 / 51 的協定原理 deep-dive** — AS-REP / ESC1 / secretsdump 的原理對 attacker / defender 有用，對 ML researcher 是 noise。可以濃縮成一張「三個 AD misconfigurations chained together」。

省下的 5-7 分鐘塞 calibration plot + cost / latency + ablation。Q&A 時 ML / research-oriented 的問題會大幅減少。

### Bottom line（research perspective）

**這是一個 engineering case study，不是 doctrine breakthrough，也不是純 LLM wrapper。**

從學術光譜上看：
- 比 PentestGPT (EMNLP 2023 Industry Track) 更系統化、有 persistent state、有量化 decision policy。
- 比 Nebula / AutoAttacker 更 mature，特別是 fact-driven memory 跟 tool-routing abstraction。
- 但**沒有**像 Reflexion (NeurIPS 2023) / Tree-of-Thoughts (NeurIPS 2023) / Voyager (Wang 2023) 那樣有清楚的 algorithmic contribution + rigorous evaluation。

Athena 的真正貢獻是把幾個已知的 agent design pattern（ReAct loop + Reflexion-style episodic memory + tool routing + structured output + persistent state）組合起來，並在 cybersecurity 這個 high-stakes / well-defined-reward 的 domain 做 industrial-grade 工程化。**這不是 paper，是 system paper（如果他們寫的話）**。如果 Harry / Alex 願意把 evaluation 加嚴（real baseline、大樣本、calibration diagnostic、ablation），這可以是 NDSS / USENIX Security 的 systems track submission。

「Doctrine beats tools」作為 slogan 我不買單 — 真正勝出的是 engineering discipline + sound design choices。把這個寫進論文比寫進 keynote slogan 更值錢。

**留下印象的一句話：** "把 LLM confidence 過 Laplace smoothing 的 history success rate 校正" — 這句 ML researcher 聽得懂、會記住、會抄。其他 30× / 信條 / doctrine 都是 keynote noise。
