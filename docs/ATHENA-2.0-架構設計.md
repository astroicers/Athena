# Athena 2.0 架構設計文件

> **版本：** 2.0-draft-r4
> **日期：** 2026-05-10
> **狀態：** 規劃中（待實作）
> **Branch：** `athena-2.0`（orphan branch，與 main 完全隔離）

---

## 一、為什麼要重寫？

Athena 1.x 以 Python + FastAPI + Next.js 建構，在快速驗證概念（PoC）上非常成功，但累積了幾個根本性的問題：

| 問題 | 說明 |
|------|------|
| **Runtime 型別錯誤** | Python 的型別檢查只在執行時發生，錯誤往往在生產環境才被發現 |
| **模組邊界模糊** | 39 個服務之間的依賴關係混亂，改一個地方容易影響其他地方 |
| **WebSocket 耦合** | 14 個不同服務直接呼叫 `ws_manager.broadcast()`，形成上帝物件 |
| **決策引擎鎖死** | OODA 是唯一決策模型，無法換成其他思考框架 |
| **Claude 住在裡面** | LLM 硬編碼在系統內部，無法從外部用 MCP 協定呼叫 Athena |
| **人類知識難以重用** | 滲透測試指令、技巧、文件散落各處，無法被系統化查詢 |
| **容器管理能力弱** | Docker Compose 缺乏健康重啟、資源限制、滾動更新等能力 |

**Athena 2.0 的五個核心設計目標：**

1. **全 Rust 重寫** — 讓編譯器在編譯期就抓到 90% 的 bug
2. **決策引擎可抽換** — OODA 是預設引擎，但整個決策框架是可替換的模組
3. **系統暴露 MCP** — Athena 對外是一個 MCP Server，Claude 從外部呼叫 Athena，而不是住在裡面
4. **人類知識工具化** — 指令、技巧、PDF 文件封裝成可查詢的知識庫 MCP 工具 + Skills
5. **k3s 部署** — 一個工具一個容器，完全隔離，防止工具崩潰互相影響

---

## 二、核心設計原則

### 原則一：型別優先（Types First）

`athena-types` crate 沒有任何內部依賴，定義所有領域型別。

```rust
// 錯誤示範（v1 Python）：傳字串，無法保證正確性
async fn get_operation(op_id: &str) -> Operation { ... }

// 正確（v2 Rust）：傳 newtype，型別錯誤無法編譯
async fn get_operation(op_id: &OperationId) -> Operation { ... }
```

### 原則二：每個能力都是一個 Trait

每個模組對外只暴露它的 `pub trait`，換實作 = 換一行 `Arc::new()`，其餘程式碼不需要改動。

### 原則三：事件，不要回呼

服務只 `publish()` 型別事件，WebSocket 閘道獨立訂閱並廣播，消除 v1 中 14 個服務都持有 `ws_manager` 參照的上帝物件問題。

### 原則四：雙向 MCP

Athena 同時是 MCP 客戶端（呼叫外部工具）和 MCP Server（對外暴露自身能力）。AI agent（Claude）從外部透過 MCP 協定與 Athena 互動，不需要住在系統內部。

### 原則五：知識即工具

人類的滲透測試經驗（指令備忘錄、提權技巧、PDF 文件、GTFOBins）轉化為可被系統查詢的工具。

### 原則六：一工具一容器（Tool Isolation）

每個 MCP 工具都是獨立的容器。隔離的目的是：

- 工具崩潰不影響其他工具
- 防止不同工具的依賴版本衝突（Python 套件、二進位工具等）
- 每個工具可以獨立更新、重啟
- 多個使用者同時呼叫不同工具不互相干擾

k3s 負責管理這 24 個容器的生命週期、健康檢查、資源限制和服務發現。

---

## 三、全系統架構圖

```
╔══════════════════════════════════════════════════════════════════════╗
║                    ATHENA 2.0 — 全系統架構                            ║
╚══════════════════════════════════════════════════════════════════════╝

  外部 AI Agent（Claude / 任何 LLM）
         │
         │  MCP 協定（JSON-RPC over HTTP）
         ▼
╔═══════════════════════════════════════╗
║         athena-mcp-server             ║
║      Athena 對外暴露的 MCP Server      ║
╚══════════════╦════════════════════════╝
               ║ 內部呼叫
               ▼
╔═══════════════════════════════════════════════════════════════╗
║                     Athena Core                                ║
║                                                                ║
║  ┌─────────────────────────────────────────────────────────┐  ║
║  │               決策引擎層（可抽換）                         │  ║
║  │  DecisionEngine trait                                    │  ║
║  │  ┌──────────┐  ┌─────────────┐  ┌───────────────────┐   │  ║
║  │  │   OODA   │  │ Kill Chain  │  │ Human-in-the-Loop │   │  ║
║  │  │ （預設）  │  │  （2.1）    │  │    （2.1）         │   │  ║
║  │  └────┬─────┘  └─────────────┘  └───────────────────┘   │  ║
║  │       │ OODA 狀態機（預設實作）                            │  ║
║  │  ┌────▼──────────────────────────────────────────────┐   │  ║
║  │  │  Observe ──► Orient ──► Decide ──► Act            │   │  ║
║  │  │  觀察        定向        決策        行動          │   │  ║
║  │  │  （每個階段都是獨立可抽換的 trait 實作）            │   │  ║
║  │  └───────────────────────────────────────────────────┘   │  ║
║  └─────────────────────────────────────────────────────────┘  ║
╚═══════════════════════════════════════════════════════════════╝
         │                                │
         ▼                                ▼
╔═════════════════════╗       ╔══════════════════════════════════╗
║  athena-pentest-kb  ║       ║     k3s — 24 個 MCP 工具容器     ║
║  滲透測試知識庫      ║       ║     （一工具一容器，完全隔離）     ║
║  MCP Server         ║       ║                                  ║
║                     ║       ║  nmap-scanner         Pod        ║
║  提權技巧            ║       ║  osint-recon           Pod       ║
║  橫向移動技巧        ║       ║  web-scanner           Pod       ║
║  PDF 文件            ║       ║  api-fuzzer            Pod       ║
║  GTFOBins           ║       ║  credential-checker    Pod       ║
║  操作筆記            ║       ║  bloodhound-collector  Pod       ║
╚═════════════════════╝       ║  impacket-ad           Pod       ║
                              ║  certipy-ad            Pod       ║
                              ║  netexec-suite         Pod       ║
                              ║  responder-capture     Pod       ║
                              ║  hashcat-crack         Pod       ║
                              ║  ... 共 24 個容器                ║
                              ╚══════════════════════════════════╝

─────────────────────── 基礎設施層（k3s）────────────────────────

╔══════════════════════════════════════════════════════════════════╗
║                     k3s 叢集                                      ║
║                                                                  ║
║  Namespace: athena-core         Namespace: athena-tools          ║
║  ┌──────────────────────────┐   ┌──────────────────────────────┐ ║
║  │ athena-api     Deployment│   │ nmap-scanner          Pod    │ ║
║  │ athena-mcp-srv Deployment│   │ osint-recon           Pod    │ ║
║  │ athena-worker  Deployment│   │ web-scanner           Pod    │ ║
║  │ athena-kb      Deployment│   │ credential-checker    Pod    │ ║
║  │ postgres       Deployment│   │ bloodhound-collector  Pod    │ ║
║  └──────────────────────────┘   │ impacket-ad           Pod    │ ║
║                                 │ ... 共 24 個 Pod              │ ║
║  Helm Charts（每個服務一個）      └──────────────────────────────┘ ║
║  Argo CD（GitOps 自動部署）                                        ║
╚══════════════════════════════════════════════════════════════════╝
```

---

## 四、決策引擎層（DecisionEngine trait）

**決策引擎本身是可抽換的**。OODA 只是眾多決策框架中的一種實作。

```
╔══════════════════════════════════════════════════════════════════════╗
║                  決策引擎層（Decision Engine Layer）                   ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║  // athena-engine-ooda/src/lib.rs 中定義的核心 trait                  ║
║  pub trait DecisionEngine: Send + Sync {                             ║
║      // 執行一個完整的決策循環                                          ║
║      async fn run_cycle(&self, op_id: &OperationId)                  ║
║          -> Result<CycleOutcome, AthenaError>;                       ║
║                                                                      ║
║      // 取得目前決策狀態                                               ║
║      async fn current_state(&self, op_id: &OperationId)             ║
║          -> Result<EngineState, AthenaError>;                        ║
║                                                                      ║
║      fn name(&self) -> &'static str;                                 ║
║  }                                                                   ║
║                                                                      ║
╠══════════════╦════════════════╦═════════════╦════════════════════════╣
║              ║                ║             ║                        ║
║  OODA        ║  Kill Chain    ║  PDCA       ║  Human-in-the-Loop     ║
║  Engine      ║  Engine        ║  Engine     ║  Engine                ║
║  （預設）     ║  線性進攻框架   ║  持續改善   ║  每步暫停等人工確認      ║
║              ║  （2.1）        ║  （2.1）    ║  適合高價值目標（2.1）  ║
╚══════════════╩════════════════╩═════════════╩════════════════════════╝
```

### OODA Engine 內部四個可抽換階段

```
╔══════════════════════════════════════════════════════════════════╗
║                 OODA Engine（預設決策引擎）                         ║
╠══════════════╦════════════════╦══════════════╦════════════════════╣
║              ║                ║              ║                    ║
║   OBSERVE    ║    ORIENT      ║    DECIDE    ║       ACT          ║
║   觀察        ║    定向         ║    決策      ║       行動          ║
║              ║                ║              ║                    ║
║ ObservePhase ║ OrientPhase    ║ DecidePhase  ║ ActPhase           ║
║ trait        ║ trait          ║ trait        ║ trait              ║
║              ║                ║              ║                    ║
║ 可換：        ║ 可換：          ║ 可換：        ║ 可換：              ║
║ MockObserve  ║ MockOrient     ║ MockDecide   ║ MockAct（測試）     ║
║ （測試）      ║ GeminiOrient   ║ RL-based     ║ DryRunAct（只印）  ║
║              ║ OllamaOrient   ║              ║                    ║
╚══════════════╩════════════════╩══════════════╩════════════════════╝
```

### main.rs 熱插拔範例

```rust
// ── 選擇決策引擎────────────────────────────────────────────────
let engine: Arc<dyn DecisionEngine> = match config.engine_mode {
    EngineMode::Ooda      => Arc::new(OodaEngine::new(observe, orient, decide, act)),
    EngineMode::KillChain => Arc::new(KillChainEngine::new(act.clone())),  // 2.1
    EngineMode::Manual    => Arc::new(HumanInLoopEngine::new()),           // 2.1
};

// ── OODA 內部，LLM 可以換────────────────────────────────────────
let orient: Arc<dyn OrientPhase> = match config.llm_backend {
    LlmBackend::Claude => Arc::new(ClaudeOrientEngine::new(llm.clone())),
    LlmBackend::OpenAi => Arc::new(OpenAiOrientEngine::new(llm.clone())),
    LlmBackend::Mock   => Arc::new(MockOrientEngine::new()),
};

// ── 執行引擎可以換──────────────────────────────────────────────
let exec: Arc<dyn ExecutionEngine> = match config.engine_type {
    EngineType::Ssh  => Arc::new(SshEngine::new(&config)),
    EngineType::Mock => Arc::new(MockEngine::new()),
};
```

---

## 五、雙向 MCP 架構

```
╔══════════════════════════════════════════════════════════════════════╗
║                          雙向 MCP 架構                                ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║  方向 A：Athena 作為 MCP 客戶端（呼叫 24 個工具容器）                  ║
║  ─────────────────────────────────────────────                       ║
║  Athena Core（athena-mcp-client）                                    ║
║    ├──► nmap-scanner     k3s Pod（Port 58010）                       ║
║    ├──► osint-recon      k3s Pod（Port 58011）                       ║
║    ├──► bloodhound-coll  k3s Pod（Port 58012）                       ║
║    ├──► impacket-ad      k3s Pod（Port 58013）                       ║
║    ├──► certipy-ad       k3s Pod（Port 58014）                       ║
║    ├──► ... 共 24 個 Pod                                             ║
║    └──► athena-pentest-kb k3s Pod（Port 58099）                      ║
║                                                                      ║
║    每個 Pod：circuit breaker 保護 + 健康檢查 + 自動重啟               ║
║                                                                      ║
║  方向 B：Athena 作為 MCP Server（對外暴露自身能力）                    ║
║  ─────────────────────────────────────────────                       ║
║  外部 AI Agent（Claude / GPT / 任何 LLM）                            ║
║    ├──► create_operation()         建立滲透測試作業                   ║
║    ├──► trigger_ooda_cycle()       觸發 OODA 決策循環                ║
║    ├──► list_recommendations()     列出 AI 建議                      ║
║    ├──► approve_recommendation()   核准執行動作                       ║
║    ├──► query_facts()              查詢情報事實                       ║
║    ├──► get_c5isr_status()         取得 C5ISR 六域健康                ║
║    ├──► get_attack_graph()         取得攻擊路徑圖                     ║
║    ├──► query_pentest_kb()         查詢滲透知識庫                     ║
║    └──► generate_report()          產生滲透測試報告                   ║
║                                                                      ║
║  重要意涵：                                                           ║
║  • Claude 不需要「住在」Athena 裡面                                   ║
║  • Orient 引擎可以是人工（Human-in-the-Loop），Claude 從外部協助      ║
║  • 任何支援 MCP 的 AI agent 都可以驅動 Athena                        ║
╚══════════════════════════════════════════════════════════════════════╝
```

---

## 六、滲透測試知識庫（athena-pentest-kb）

把人類的滲透測試經驗轉化為系統可查詢的工具。

```
╔══════════════════════════════════════════════════════════════════════╗
║                     athena-pentest-kb                                 ║
║         （滲透測試知識庫 — MCP Server + Skill 雙層封裝）               ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║  知識來源：                                                           ║
║  • 提權指令備忘錄（sudo abuse, SUID, cron, PATH hijack...）           ║
║  • PDF 文件（OSCP notes, 課程材料, 研究報告）                         ║
║  • HackTricks / PayloadsAllTheThings 整理                            ║
║  • GTFOBins（從二進位檔逃脫的方法）                                    ║
║  • 自己的操作筆記（Markdown 格式）                                     ║
║  • CVE PoC 程式碼和說明                                               ║
║  • 橫向移動技巧（Pass-the-Hash, Kerberoasting, AS-REP...）            ║
║  • 雲端錯誤設定（AWS IMDS, Azure MSI, GCP 服務帳號）                  ║
║                                                                      ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║  知識庫目錄結構：                                                      ║
║                                                                      ║
║  kb/                                                                 ║
║  ├── privesc/linux/                                                  ║
║  │   ├── suid.md              提權：SUID 利用（偵測指令 + 利用指令）   ║
║  │   ├── sudo-abuse.md        提權：sudo 錯誤設定                    ║
║  │   ├── cron-jobs.md         提權：Cron job 劫持                   ║
║  │   ├── path-hijack.md       提權：PATH 環境變數劫持                ║
║  │   └── capabilities.md      提權：Linux capabilities              ║
║  ├── privesc/windows/                                                ║
║  │   ├── token-abuse.md       提權：Token 竊取                      ║
║  │   └── alwaysinstallelevated.md                                    ║
║  ├── lateral/                                                        ║
║  │   ├── pass-the-hash.md     橫向移動                               ║
║  │   ├── kerberoasting.md     橫向移動                               ║
║  │   └── as-rep-roasting.md   橫向移動                               ║
║  ├── initial-access/          初始存取                               ║
║  ├── persistence/             持久化                                  ║
║  ├── cloud/                   雲端攻擊                                ║
║  └── index.json               全文索引（tantivy，啟動時建立）          ║
║                                                                      ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║  對外暴露的 MCP 工具：                                                 ║
║                                                                      ║
║  search_kb(query, category?)                                         ║
║    → 全文搜尋知識庫                                                    ║
║    → 範例：search_kb("SUID python3") → 找到 GTFOBins 利用方式         ║
║                                                                      ║
║  get_privesc_techniques(os, context)                                 ║
║    → 根據 OS 和情境取得適合的提權技巧                                   ║
║    → 範例：get_privesc_techniques("linux", "sudo_l_output: ...")     ║
║                                                                      ║
║  get_gtfobins(binary_name)                                           ║
║    → 查詢特定二進位檔的 GTFOBins 逃脫方式                              ║
║    → 範例：get_gtfobins("python3") → Shell 逃脫指令                   ║
║                                                                      ║
║  get_technique_commands(mitre_id)                                    ║
║    → 根據 MITRE ID 取得實際執行指令                                    ║
║    → 範例：get_technique_commands("T1548.001") → SUID 指令           ║
║                                                                      ║
║  import_document(path, category)                                     ║
║    → 匯入 PDF / Markdown 文件進知識庫                                  ║
║                                                                      ║
║  add_note(topic, note)                                               ║
║    → 加入個人操作筆記                                                  ║
║                                                                      ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║  知識庫條目格式（Markdown + YAML frontmatter）：                       ║
║                                                                      ║
║  ---                                                                 ║
║  id: linux-privesc-suid-python3                                      ║
║  category: privesc/linux                                             ║
║  mitre_id: T1548.001                                                 ║
║  os: linux                                                           ║
║  noise_level: low                                                    ║
║  risk_level: high                                                    ║
║  tags: [suid, python, gtfobins]                                      ║
║  ---                                                                 ║
║  # Python3 SUID 提權                                                  ║
║  ## 偵測指令                                                          ║
║  find / -perm -u=s -type f 2>/dev/null | grep python                 ║
║  ## 利用指令                                                          ║
║  python3 -c 'import os; os.execl("/bin/sh", "sh", "-p")'            ║
║  ## 注意事項                                                          ║
║  • 噪音等級：低（只在本機執行，不產生網路流量）                            ║
║  • 部分系統的 python3 SUID 可能是蜜罐                                  ║
║                                                                      ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║  對應的 Skill 檔案（告訴 AI「何時用、如何解讀」）：                      ║
║                                                                      ║
║  skills/pentest/privesc-linux.md                                     ║
║  → 何時觸發 get_privesc_techniques()                                  ║
║  → 如何解讀輸出並選擇技術                                               ║
║  → 如何驗證提權是否成功                                                 ║
║  → OPSEC 注意事項（噪音等級、蜜罐風險）                                 ║
║                                                                      ║
║  Skills 的分工：                                                       ║
║  • MCP 工具 = 「執行查詢」（拿到具體的指令和技巧）                       ║
║  • Skill 檔案 = 「決策知識」（何時用、如何判斷結果、注意什麼）            ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
```

---

## 七、觀察層（Observe Layer）

```
╔══════════════════════════════════════════════════════════╗
║                   athena-observe                          ║
║            （實作 ObservePhase trait）                     ║
║                                                           ║
║  輸入：當前作業 ID                                         ║
║  輸出：observe_summary（給 Orient 的摘要字串）              ║
║                                                           ║
║  流程：                                                    ║
║  1. 從 DB 讀取最近執行結果                                  ║
║  2. 過濾已知事實（dedup by trait+value 組合）               ║
║  3. 依 mission_profile 判斷情報是否足夠                     ║
║  4. 情報不足 → 觸發自動偵查（委派給 athena-recon）           ║
║  5. 組裝 observe_summary 回傳                               ║
╚════╦══════════════════╦════════════════════╦══════════════╝
     ║                  ║                    ║
     ▼                  ▼                    ▼
╔══════════════╗  ╔═══════════════╗  ╔══════════════════════╗
║ athena-facts ║  ║ athena-recon  ║  ║  athena-mcp-client   ║
║ 事實儲存庫   ║  ║ 自動偵查      ║  ║  呼叫 nmap-scanner   ║
║              ║  ║               ║  ║  Pod（k3s 服務發現）  ║
║ FactRepo     ║  ║ ReconEngine   ║  ║                      ║
║ trait：       ║  ║ trait：        ║  ║  circuit breaker    ║
║ list()       ║  ║ scan()        ║  ║  per-Pod 狀態追蹤    ║
║ insert()     ║  ║ enumerate()   ║  ╚══════════════════════╝
║ dedup()      ║  ╚═══════════════╝
╚══════════════╝
```

---

## 八、定向層（Orient Layer）

```
╔══════════════════════════════════════════════════════════════════╗
║                      athena-orient                                ║
║               （實作 OrientPhase trait）                          ║
║                                                                   ║
║  輸入：observe_summary + attack_graph_summary                     ║
║  輸出：OrientRecommendation（3 個戰術建議）                         ║
║                                                                   ║
║  流程：                                                            ║
║  1. 向 athena-pentest-kb 查詢當前情境的技巧                        ║
║  2. prompt_builder 組裝提示詞（14 條規則 + 知識庫內容）              ║
║  3. 呼叫 LLM（透過 athena-llm-client）                             ║
║  4. 解析 JSON 回應，驗證 MITRE ID 格式                              ║
║  5. noise_filter 過濾噪音超標的建議                                 ║
╚════╦══════════════════╦════════════════╦═══════════════════════════╝
     ║                  ║                ║
     ▼                  ▼                ▼
╔══════════════╗  ╔═════════════╗  ╔═══════════════════════╗
║ athena-llm-  ║  ║ athena-     ║  ║  athena-pentest-kb    ║
║ client       ║  ║ skills-     ║  ║  查詢當前情境技巧       ║
║              ║  ║ loader      ║  ║                       ║
║ Anthropic    ║  ║ 讀取 Skill  ║  ║  get_privesc_tech-    ║
║ Claude（預設）║  ║ 注入提示詞  ║  ║  niques(os, context)  ║
║ OpenAI(備援) ║  ╚═════════════╝  ║  get_gtfobins(binary) ║
╚══════════════╝                   ╚═══════════════════════╝
```

**Orient 的 14 條規則**（移植自 v1，在 Rust 實作為常數，每條都有單元測試）：

| 規則 | 說明 |
|------|------|
| 1 | 只使用 MITRE ATT&CK 框架內的技術 ID |
| 2 | 建議必須對齊當前殺傷鏈階段 |
| 3 | 根據目標主機的開放服務選擇對應技術 |
| 4 | 有可用憑證時優先選擇憑證攻擊 |
| 5 | OPSEC 噪音等級必須符合任務設定 |
| 6 | 只有 relay_available=true 時才建議 reverse shell |
| 7 | relay 不可用時禁止所有需要 callback 的技術 |
| 8 | 不建議核模組 / rootkit 等高風險技術 |
| 9 | 偵測到跨類別樞紐機會時明確標示 |
| 10-14 | 從 v1 `orient_engine.py` 原樣移植 |

---

## 九、決策層（Decide Layer）

```
╔══════════════════════════════════════════════════════════════════╗
║                      athena-decide                                ║
║               （實作 DecidePhase trait）                          ║
║                                                                   ║
║  決策矩陣（風險 × 自動模式）：                                     ║
║  ┌──────────┬──────────────┬──────────────────────────────────┐  ║
║  │ 風險等級  │  自動模式    │ 決策                              │  ║
║  ├──────────┼──────────────┼──────────────────────────────────┤  ║
║  │ CRITICAL │ 任何模式     │ 強制人工確認                       │  ║
║  │ HIGH     │ semi_auto    │ 人工確認                           │  ║
║  │ MEDIUM   │ semi_auto    │ 自動執行                           │  ║
║  │ LOW      │ 任何模式     │ 自動執行                           │  ║
║  └──────────┴──────────────┴──────────────────────────────────┘  ║
║                                                                   ║
║  阻擋條件（任一成立 → 拒絕執行）：                                  ║
║  • 殺傷鏈階段被禁用                                               ║
║  • 目標不在 RoE 範圍內（athena-scope 驗證）                        ║
║  • OPSEC CRITICAL 告警啟動（athena-opsec 查詢）                   ║
║  • Agent 能力不匹配                                               ║
╚══════════════════════════════════════════════════════════════════╝
```

---

## 十、行動層（Act Layer）

```
╔══════════════════════════════════════════════════════════════════╗
║                       athena-act                                  ║
║                （實作 ActPhase trait）                             ║
║                                                                   ║
║  引擎選擇邏輯：                                                    ║
║  ┌──────────────────────────────────────────────────────────┐    ║
║  │ 技術 ID 在 AD 路由表？                                     │    ║
║  │   是 → 呼叫對應的 MCP 工具 Pod（k3s 服務發現）              │    ║
║  │   否 → 依 EXECUTION_ENGINE 環境變數：                      │    ║
║  │        ssh   → athena-exec-ssh（2.0）                      │    ║
║  │        msf   → athena-exec-metasploit（2.1）               │    ║
║  │        c2    → athena-exec-c2（2.1）                       │    ║
║  │        mock  → MockExecutionEngine（測試）                  │    ║
║  │   失敗 → fallback 引擎（SPEC-040）                          │    ║
║  └──────────────────────────────────────────────────────────┘    ║
╚═══╦═══════════════════════╦═════════════════════════════════════╝
    ║                       ║
    ▼                       ▼
╔═════════════╗   ╔══════════════════════════════════════════════╗
║ athena-exec ║   ║    athena-mcp-client                         ║
║ -ssh        ║   ║    呼叫 k3s 中各個 MCP 工具 Pod               ║
║ russh 0.44  ║   ║    每個 Pod 獨立容器，崩潰不互相影響           ║
╚═════════════╝   ║    k3s 服務發現（DNS）定位每個工具             ║
        │         ╚══════════════════════════════════════════════╝
        │                         │
        └──────────┬──────────────┘
                   ▼
      ╔════════════════════════════╗
      ║ athena-mcp-fact-extractor  ║
      ║ MCP 輸出 → 結構化 Fact      ║
      ║ 三層解析：JSON→dict→text   ║
      ╚════════════════════════════╝
```

---

## 十一、k3s 部署架構

### 為什麼一工具一容器，而不合併？

**工具隔離設計（保持 v1 的設計決策）：**

```
v1 問題場景（如果合併容器）：
  impacket-ad 套件更新 → 破壞 certipy-ad 的依賴 → 兩個工具都掛掉

v2 隔離設計（一工具一容器）：
  impacket-ad 容器更新 → 只影響 impacket-ad → certipy-ad 完全不受影響
  impacket-ad 崩潰    → k3s 自動重啟 impacket-ad → 其他工具繼續運行
  兩個使用者同時呼叫  → 各自的 Pod，資源獨立，不互相競爭
```

### k3s 解決 Docker Compose 的問題

| 問題 | Docker Compose | k3s（一工具一Pod） |
|------|---------------|------------------|
| 工具崩潰自動重啟 | restart: always（粗糙） | Health-based 重啟 |
| 資源限制 | 難以精確設定 | requests/limits 精確控制 |
| 服務發現 | 固定 port，需手動管理 | DNS 服務發現（serviceName:port） |
| 工具更新 | 需手動 pull + restart | Rolling update，zero downtime |
| 多工具同時運行 | 共享 host 資源 | 每個 Pod 獨立資源預算 |
| 密鑰管理 | .env 檔案 | k8s Secret |

### k3s Namespace 設計

```
Namespace: athena-core
  Deployments（Rust binary 服務）：
    athena-api           REST + WebSocket 伺服器
    athena-mcp-server    Athena 對外的 MCP Server
    athena-worker        OODA 排程 + 決策循環執行
    athena-pentest-kb    滲透測試知識庫 MCP Server
    postgres             PostgreSQL 資料庫
  Services（ClusterIP）：
    athena-api-svc       :58000
    athena-mcp-svc       :58001
    athena-kb-svc        :58002
    postgres-svc         :5432
  Secrets：
    athena-secrets       API Keys、DB 密碼
  ConfigMaps：
    athena-config        設定檔

Namespace: athena-tools
  24 個獨立 Deployment（一工具一容器）：
    nmap-scanner          :58010
    osint-recon           :58011
    vuln-lookup           :58012
    credential-checker    :58013
    attack-executor       :58014
    web-scanner           :58015
    api-fuzzer            :58016
    privesc-scanner       :58017
    credential-dumper     :58018
    lateral-mover         :58019
    bloodhound-collector  :58020
    netexec-suite         :58021
    certipy-ad            :58022
    responder-capture     :58023
    cloudfox-enum         :58024
    pacu-aws              :58025
    scoutsuite-audit      :58026
    impacket-ad           :58027
    ad-exploiter          :58028
    coercion-tools        :58029
    ad-persistence        :58030
    ntlm-relay            :58031
    hashcat-crack         :58032
    initial-access-exec   :58033
```

### Helm Chart 結構

```
helm/
├── athena-core/
│   ├── Chart.yaml
│   ├── values.yaml           dev / staging / prod 設定
│   └── templates/
│       ├── deployment-api.yaml
│       ├── deployment-worker.yaml
│       ├── deployment-mcp-server.yaml
│       ├── deployment-pentest-kb.yaml
│       ├── deployment-postgres.yaml
│       ├── service.yaml
│       ├── configmap.yaml
│       └── secret.yaml
└── athena-tools/
    ├── Chart.yaml
    ├── values.yaml
    └── templates/
        ├── deployment-nmap-scanner.yaml
        ├── deployment-bloodhound.yaml
        └── ... （每個工具一個 template）
```

### Argo CD GitOps

```
改 helm/values.yaml → git push → Argo CD 自動 helm upgrade → k3s Rolling update
不需要 kubectl apply，不需要手動部署
```

---

## 十二、完整 Cargo Workspace 目錄結構

```
athena-2.0/
├── Cargo.toml                            ← workspace 根 manifest
├── Cargo.lock
│
├── crates/
│   ├── 基礎層（零依賴）
│   │   ├── athena-types/                 ← 所有領域型別，零依賴
│   │   ├── athena-config/                ← figment 設定載入
│   │   ├── athena-telemetry/             ← tracing + Prometheus
│   │   ├── athena-db/
│   │   │   ├── src/repositories/         ← 所有 SQL 只在這裡
│   │   │   └── src/migrations/           ← .sql 遷移檔案
│   │   ├── athena-events/                ← 型別化事件總線
│   │   ├── athena-knowledge/             ← YAML 知識庫載入器
│   │   └── athena-plugin/                ← 插件 trait + registry
│   │
│   ├── 情報支援層
│   │   ├── athena-facts/
│   │   ├── athena-vuln/
│   │   ├── athena-scope/
│   │   ├── athena-opsec/
│   │   ├── athena-c5isr/
│   │   ├── athena-attack-graph/
│   │   ├── athena-policy/
│   │   └── athena-config-engine/
│   │
│   ├── 外部客戶端層
│   │   ├── athena-llm-client/            ← reqwest → Anthropic + OpenAI
│   │   ├── athena-skills-loader/         ← 讀取 ~/.claude/skills/
│   │   ├── athena-mcp-client/            ← MCP HTTP+stdio + circuit breaker
│   │   └── athena-mcp-fact-extractor/    ← MCP 輸出 → Fact
│   │
│   ├── 知識庫層
│   │   └── athena-pentest-kb/
│   │       ├── src/
│   │       │   ├── indexer.rs            ← tantivy 全文索引
│   │       │   ├── search.rs             ← 查詢邏輯
│   │       │   ├── importer.rs           ← PDF / Markdown 匯入
│   │       │   └── mcp_server.rs         ← 對外暴露 MCP 工具
│   │       └── kb/
│   │           ├── privesc/linux/
│   │           ├── privesc/windows/
│   │           ├── lateral/
│   │           ├── initial-access/
│   │           ├── persistence/
│   │           └── cloud/
│   │
│   ├── 執行引擎層
│   │   ├── athena-exec-ssh/              ← russh（2.0 實作）
│   │   ├── athena-exec-metasploit/       ← MSF RPC（2.1）
│   │   ├── athena-exec-c2/               ← Caldera（2.1）
│   │   └── athena-exec-winrm/            ← WinRM（2.1）
│   │
│   ├── OODA 四個階段
│   │   ├── athena-observe/
│   │   ├── athena-orient/
│   │   │   ├── src/prompt_builder.rs
│   │   │   ├── src/rules.rs              ← 14 條規則（有單元測試）
│   │   │   └── src/noise_filter.rs
│   │   ├── athena-decide/
│   │   │   ├── src/risk_matrix.rs
│   │   │   ├── src/kill_chain.rs
│   │   │   └── src/confidence.rs
│   │   └── athena-act/
│   │       ├── src/router.rs
│   │       ├── src/ad_routing_table.rs   ← AD 技術→MCP 路由表（phf::Map）
│   │       └── src/pivot_detector.rs
│   │
│   ├── 決策引擎層
│   │   ├── athena-engine-ooda/           ← OODA 決策引擎（預設）
│   │   │   ├── src/controller.rs
│   │   │   ├── src/lifecycle.rs
│   │   │   └── src/locks.rs              ← DashMap<OperationId, Mutex>
│   │   ├── athena-engine-killchain/      ← Kill Chain 引擎（2.1）
│   │   └── athena-engine-manual/         ← 全人工引擎（2.1）
│   │
│   ├── 並行 + 輸出層
│   │   ├── athena-swarm/                 ← 多目標並行 + 拓撲排序
│   │   ├── athena-recon/
│   │   ├── athena-osint/                 ← （2.1）
│   │   ├── athena-relay/                 ← reverse shell relay（2.1）
│   │   ├── athena-brief/
│   │   └── athena-report/
│   │
│   └── API + MCP Server 層
│       ├── athena-ws/                    ← WebSocket 閘道
│       ├── athena-api/                   ← axum REST API（27 個路由器）
│       └── athena-mcp-server/            ← Athena 對外暴露的 MCP Server
│
├── athena-workspace/
│   └── src/main.rs                       ← DI 注入 + 服務啟動
│
├── data/                                 ← YAML 知識庫（v1 完全相同）
├── helm/                                 ← Helm Charts
│   ├── athena-core/
│   └── athena-tools/
├── argocd/                               ← Argo CD 設定
├── skills/                               ← 新增的 Skill 檔案
│   └── pentest/
│       ├── privesc-linux.md
│       ├── privesc-windows.md
│       ├── lateral-movement.md
│       └── post-exploitation.md
├── Dockerfile                            ← 多階段 Rust 建置
├── docker-compose.yml                    ← 本地開發用
└── Makefile
```

---

## 十三、Crate 依賴階層

```
第 0 層（無依賴）
└── athena-types

第 1 層（基礎設施）
├── athena-config         deps: types
├── athena-telemetry      deps: tracing（外部）
├── athena-db             deps: types, config
├── athena-events         deps: types
├── athena-knowledge      deps: types, config
└── athena-plugin         deps: types

第 2 層（領域能力）
├── athena-facts          deps: types, db
├── athena-vuln           deps: types, db
├── athena-scope          deps: types, db
├── athena-opsec          deps: types, db
├── athena-c5isr          deps: types, db
├── athena-attack-graph   deps: types, knowledge
├── athena-policy         deps: types, config
└── athena-config-engine  deps: types, c5isr, opsec

第 3 層（外部客戶端）
├── athena-llm-client     deps: types, config
├── athena-skills-loader  deps: types, config
├── athena-mcp-client     deps: types, config, events
└── athena-mcp-fact-extractor deps: types, mcp-client

第 3.5 層（知識庫）
└── athena-pentest-kb     deps: types, config, mcp-client

第 4 層（執行引擎）
├── athena-exec-ssh       deps: types
├── athena-exec-metasploit deps: types
├── athena-exec-c2        deps: types
└── athena-exec-winrm     deps: types

第 5 層（OODA 四個階段）
├── athena-observe        deps: types, db, facts, recon, mcp-client
├── athena-orient         deps: types, db, llm-client, skills-loader, knowledge, attack-graph, pentest-kb
├── athena-decide         deps: types, db, knowledge, scope, config-engine
└── athena-act            deps: types, db, mcp-client, exec-ssh, mcp-fact-extractor

第 6 層（並行 + 輸出）
├── athena-swarm          deps: types, act（透過 trait）
├── athena-recon          deps: types, mcp-client
├── athena-brief          deps: types, db, llm-client
└── athena-report         deps: types, db

第 7 層（決策引擎）
├── athena-engine-ooda    deps: types, db, events, observe, orient, decide, act, swarm, c5isr
├── athena-engine-killchain deps: types, act
└── athena-engine-manual  deps: types

第 8 層（協調）
└── athena-scheduler      deps: types, engine-ooda（透過 DecisionEngine trait）

第 9 層（對外服務）
├── athena-ws             deps: types, events
├── athena-api            deps: types, engine-ooda, events, ws, db
└── athena-mcp-server     deps: types, engine-ooda, db, facts, c5isr, report

第 10 層（主程式）
└── athena-workspace      deps: api, mcp-server + 所有需要被注入的 crate
```

**鐵律：**
```
❌ 決策引擎層 不能 依賴 athena-api 或 athena-mcp-server
❌ 基礎層 不能 依賴 任何業務 crate
❌ 執行引擎 crate 不能 互相依賴
❌ 除 athena-db 外，任何 crate 不能 直接寫 SQL
```

---

## 十四、全部可模組化內容總表

| 模組分類 | Crate | Trait 介面 | 2.0 預設實作 | 可替換為 |
|---------|-------|-----------|------------|---------|
| **決策引擎** | `athena-engine-ooda` | `DecisionEngine` | OODA 狀態機 | PDCA、Kill Chain、Manual |
| **觀察階段** | `athena-observe` | `ObservePhase` | `DefaultObserver` | Mock、自定義 |
| **定向階段** | `athena-orient` | `OrientPhase` | Claude 分析引擎 | Mock、其他 LLM |
| **決策階段** | `athena-decide` | `DecidePhase` | 風險矩陣決策 | Mock、強化學習 |
| **行動階段** | `athena-act` | `ActPhase` | 引擎路由器 | Mock、DryRun |
| **LLM 後端** | `athena-llm-client` | `LlmClient` | Anthropic Claude | OpenAI、Gemini、Ollama |
| **SSH 引擎** | `athena-exec-ssh` | `ExecutionEngine` | russh | 任何 SSH 實作 |
| **MSF 引擎** | `athena-exec-metasploit` | `ExecutionEngine` | MSF RPC | Cobalt Strike |
| **C2 引擎** | `athena-exec-c2` | `ExecutionEngine` | Caldera | Sliver、任何 C2 |
| **MCP 客戶端** | `athena-mcp-client` | `McpClient` | HTTP+stdio | Mock、新傳輸層 |
| **MCP 工具容器** | k3s Pods（24 個） | — | 一工具一容器 | 任意新增 MCP 工具 |
| **事實儲存庫** | `athena-facts` | `FactRepository` | sqlx PostgreSQL | 記憶體版（測試） |
| **偵查引擎** | `athena-recon` | `ReconEngine` | MCP nmap Pod | 任何偵查工具 |
| **C5ISR 評估** | `athena-c5isr` | `C5isrMapper` | 六域加權評分 | 自定義評分邏輯 |
| **OPSEC 監控** | `athena-opsec` | `OpsecMonitor` | 噪音預算追蹤 | 外部 SIEM 整合 |
| **漏洞管理** | `athena-vuln` | `VulnerabilityManager` | NVD API | Tenable、Nessus |
| **攻擊路徑** | `athena-attack-graph` | `AttackGraphEngine` | Dijkstra | Neo4j 版 |
| **報告產生** | `athena-report` | `ReportGenerator` | Markdown + JSON | PDF、DOCX |
| **知識庫** | `athena-pentest-kb` | `KnowledgeBase` | 本地 Markdown | 向量資料庫版 |
| **Skills 載入** | `athena-skills-loader` | `SkillsLoader` | 本地檔案系統 | DB 版、遠端 |
| **範圍驗證** | `athena-scope` | `ScopeValidator` | IP/CIDR 比對 | 外部 RoE 系統 |
| **政策引擎** | `athena-policy` | `PolicyEngine` | YAML 規則 | 外部政策服務 |
| **並行執行** | `athena-swarm` | `SwarmExecutor` | tokio 信號量 | 不同並行策略 |
| **部署平台** | k3s | — | 單機 k3s | 完整 EKS/AKS |

---

## 十五、Rust 技術棧

| 用途 | Crate | 版本 |
|------|-------|------|
| 非同步執行時 | `tokio` | 1.x（full） |
| HTTP 伺服器 | `axum` | 0.7 |
| HTTP 客戶端 | `reqwest` | 0.12 |
| 資料庫 | `sqlx` | 0.8（postgres） |
| 設定載入 | `figment` | 0.10 |
| SSH 執行 | `russh` | 0.44 |
| JSON 序列化 | `serde_json` | 1.x |
| YAML 解析 | `serde_yaml` | 0.9 |
| 錯誤型別 | `thiserror` + `anyhow` | 1.x |
| 日誌追蹤 | `tracing` + `tracing-subscriber` | 0.1 / 0.3 |
| 並行 Map | `dashmap` | 6.x |
| 非同步 trait | `async-trait` | 0.1 |
| IP 範圍 | `ipnetwork` | 0.20 |
| 編譯期 Map | `phf` | 0.11 |
| UUID | `uuid` | 1.x（v4） |
| 時間 | `chrono` | 0.4 |
| 中間件 | `tower` + `tower-http` | 0.4 / 0.5 |
| 全文搜尋 | `tantivy` | 0.21（知識庫索引） |
| PDF 解析 | `pdf-extract` | 0.7（匯入 PDF） |
| Prometheus | `opentelemetry-prometheus` | 0.24 |

---

## 十六、不動的部分

```
24 個 MCP 工具的程式碼邏輯      ← 完全不改，只是改用 k3s 管理生命週期
~/.claude/skills/              ← 現有 Skills 不改，新增 skills/pentest/
data/*.yaml                    ← YAML 知識庫完全相同
```

---

## 十七、實作分階段計畫

```
2.0-alpha（6 週）— 基礎建設
  • git checkout --orphan athena-2.0，Cargo workspace 骨架
  • athena-types, athena-config, athena-db（Alembic SQL 移植到 sqlx）
  • athena-events, athena-knowledge, athena-telemetry
  • athena-api stub（只有 GET /health）
  • k3s 安裝 + postgres Deployment + Helm chart 骨架
  驗收：cargo build --workspace 通過 + k3s postgres 可連線

2.0-beta1（4 週）— OODA 骨架
  • athena-llm-client（Anthropic + OpenAI via reqwest）
  • athena-skills-loader, athena-attack-graph
  • athena-observe, athena-orient, athena-decide
  • athena-engine-ooda（Mock 模式）, athena-scheduler
  驗收：MOCK_LLM=true 跑完整 OODA 循環不崩潰

2.0-beta2（4 週）— 執行 + MCP
  • athena-exec-ssh（russh）
  • athena-mcp-client（HTTP+stdio + circuit breaker）
  • athena-mcp-fact-extractor
  • athena-act, athena-swarm, athena-recon
  • 24 個 MCP 工具容器遷移至 k3s（各自獨立 Deployment）
  驗收：對測試目標跑完整 OODA 循環（SSH + MCP 工具）

2.0-beta3（3 週）— 情報 + 知識庫
  • athena-c5isr, athena-opsec, athena-scope, athena-vuln
  • athena-pentest-kb（Markdown 知識庫 + tantivy 索引 + MCP Server）
  • 撰寫初始知識庫條目（提權、橫向移動、初始存取各 10 條）
  • athena-brief, athena-report
  驗收：知識庫可查詢，C5ISR 健康，報告可產生

2.0-rc（3 週）— 完整對外服務
  • athena-api 全部 27 個路由器
  • athena-mcp-server（Athena 對外暴露 MCP）
  • athena-ws（WebSocket 閘道 + 事件訂閱）
  • Bearer token 認證中間件
  • Argo CD GitOps 設定
  驗收：外部 Claude 可透過 MCP 呼叫 Athena

2.1（後續）
  • athena-exec-metasploit, athena-exec-c2, athena-exec-winrm
  • athena-relay（reverse shell 中繼）
  • athena-engine-killchain, athena-engine-manual
  • athena-osint
  • Gemini / Groq / Ollama LLM 後端
  • 知識庫向量搜尋版（pgvector）
  • 多機 k3s 叢集擴展
  • k3s scale-to-zero（KEDA，工具按需啟動）
```

---

## 十八、需要新建的 ADR

| ADR 編號 | 決策內容 | 取代 |
|---------|---------|------|
| ADR-100 | Rust + Cargo Workspace 作為主要技術棧 | ADR-001 |
| ADR-101 | 每個能力一個 crate + 依賴規則 | ADR-002 |
| ADR-102 | 無前端、純 API 架構 | ADR-009 |
| ADR-103 | Bearer Token 認證 | ADR-011 |
| ADR-104 | 透過 reqwest 呼叫 Anthropic API（無官方 Rust SDK） | ADR-014 |
| ADR-105 | tokio 定時器取代 APScheduler | ADR-023 |
| ADR-106 | athena-events 型別總線取代直接 ws_manager 呼叫 | ADR-007 |
| ADR-107 | Orphan branch 策略 | — |
| ADR-108 | 建構子注入、禁止全域單例 | — |
| ADR-109 | `Arc<dyn Trait>` 熱插拔機制 | — |
| ADR-110 | russh 作為 SSH 後端 | ADR-017 |
| ADR-111 | sqlx 編譯期查詢檢查延至 rc 階段 | — |
| ADR-112 | DecisionEngine trait — 決策引擎可抽換 | ADR-003 |
| ADR-113 | Athena 對外暴露 MCP Server（雙向 MCP） | ADR-024 |
| ADR-114 | 滲透測試知識庫模組（athena-pentest-kb） | — |
| ADR-115 | k3s 作為容器編排平台取代 Docker Compose | ADR-010 |
| ADR-116 | 一工具一容器（Tool Isolation）設計決策 | — |
| ADR-117 | Argo CD GitOps 部署策略 | — |

---

## 十九、2.0 範圍外

| 項目 | 說明 |
|------|------|
| 前端（Next.js/React） | headless 優先，前端獨立開發 |
| Metasploit / C2 / WinRM 引擎 | Trait 定義好，2.1 實作 |
| Kill Chain / Manual 決策引擎 | Trait 定義好，2.1 實作 |
| Relay 中繼基礎設施 | 放 2.1 |
| OSINT 引擎 | 放 2.1 |
| Gemini / Groq / Ollama LLM | Anthropic + OpenAI 先上 |
| v1 PostgreSQL 資料遷移 | 全新 DB，重新填資料 |
| OAuth LLM 認證 | 只支援 API Key |
| CLI | API-first，CLI 另外建 |
| 知識庫向量搜尋 | tantivy 全文搜尋先上，pgvector 放 2.1 |
| k3s 多機叢集 | 單機先上，2.1 擴展 |
| k3s scale-to-zero | KEDA 按需啟動工具，放 2.1 |
