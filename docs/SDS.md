# 軟體設計規格書 (Software Design Specification)

---

| 欄位 | 內容 |
|------|------|
| **專案名稱** | Athena — AI 驅動自動化滲透測試平台 |
| **版本** | v0.2.0 |
| **最後更新** | 2026-04-10 |
| **狀態** | Accepted |
| **依據 SRS** | 尚未建立 |
| **作者** | Athena Team |
| **審閱者** | — |

---

## 1. 系統架構概覽

### 1.1 架構風格

本系統採用**分層式單體架構（Layered Monolith）**結合 **REST API + WebSocket** 即時通訊，主要考量：

- POC 階段快速迭代，無需微服務級別的部署複雜度
- OODA 循環引擎內部服務間存在高度耦合的資料流，單體內呼叫零延遲
- 前後端完全分離，後續可獨立拆分服務而不影響前端
- 透過 Docker Compose 編排，可選掛載 C2 Engine / Metasploit / MCP Tool Servers

**架構原則：**

1. 依賴方向單向向下：Frontend → Backend API → Services → Database
2. 所有外部執行引擎透過抽象介面（`EngineRouter`）存取，實作可替換
3. AI 整合（OrientEngine）支援 `MOCK_LLM` 模式，確保無 API Key 亦可開發測試
4. 即時資料透過 WebSocket 推播，前端不需輪詢

### 1.2 分層架構說明

```
┌──────────────────────────────────────────────────────────────┐
│              Presentation Layer（表現層）                      │
│   Next.js 14 (App Router) + React 18 + Tailwind CSS v4       │
│   next-intl (en / zh-TW) · react-force-graph-3d · Mermaid    │
│   WebSocket Client (useWebSocket hook)                        │
├──────────────────────────────────────────────────────────────┤
│              Application Layer（應用層）                       │
│   FastAPI Routers (26 路由模組)                                │
│   Pydantic v2 請求/回應驗證 · ORJSONResponse                  │
│   WebSocket Manager (即時事件推播)                             │
├──────────────────────────────────────────────────────────────┤
│              Business Logic Layer（業務層）                    │
│   OODAController — 循環協調器                                  │
│   OrientEngine (Claude AI) · DecisionEngine · FactCollector   │
│   ConstraintEngine · C5ISRMapper · AttackGraphEngine          │
│   ReconEngine · InitialAccessEngine · OsintEngine             │
│   AgentSwarm · KillChainEnforcer · OpsecMonitor               │
├──────────────────────────────────────────────────────────────┤
│              Infrastructure Layer（基礎設施層）                │
│   asyncpg + PostgreSQL 16 · Alembic Migrations                │
│   EngineRouter → DirectSSHEngine / C2EngineClient /           │
│                  MetasploitEngineAdapter / MCPEngineClient     │
│   MCPClientManager (MCP Tool Servers)                          │
│   LLMClient (Anthropic Claude API)                             │
└──────────────────────────────────────────────────────────────┘
```

### 1.3 部署架構

```
localhost (開發 / POC 部署)
    │
    ├── :58080  Frontend (Next.js node:20-alpine multi-stage)
    │     │
    │     ▼
    ├── :58000  Backend  (FastAPI python:3.12-slim + nmap)
    │     │
    │     ├──────────────────────────────────────────┐
    │     ▼                                          ▼
    ├── :55432  PostgreSQL 16-alpine                 WebSocket /api/ws/{operation_id}
    │
    │   ── 可選 Profiles ──
    ├── :58888  C2 Engine  (Caldera, profile: c2)
    ├── :55553  Metasploit RPC  (profile: msf)
    └── :5809x  MCP Tool Servers x7  (profile: mcp)
            ├── mcp-nmap       :58091
            ├── mcp-osint      :58092
            ├── mcp-vuln       :58093
            ├── mcp-web        :58094
            ├── mcp-api-fuzzer :58095
            ├── mcp-cred       :58096
            └── mcp-attack-exec :58097
```

**基礎設施選擇：**

| 元件 | 服務 | 理由 |
|------|------|------|
| 容器編排 | Docker Compose 3.8 | POC 階段，單機部署足夠；profile 機制按需啟動選用元件 |
| 資料庫 | PostgreSQL 16-alpine | ACID、JSONB 支援、asyncpg 非同步連線池 |
| 後端框架 | FastAPI + uvloop | 原生 async/await、自動 OpenAPI 文件、ORJSONResponse 高效序列化 |
| 前端框架 | Next.js 14 (App Router) | React Server Components、i18n 路由、靜態最佳化 |
| AI 推理 | Anthropic Claude API | OrientEngine 戰術分析，支援 MOCK_LLM 模式脫線開發 |
| 即時通訊 | FastAPI WebSocket | 原生支援，無需額外中間件 |

---

## 2. 模組設計

### 2.1 後端模組清單

#### 2.1.1 路由層（Routers）

| 模組名稱 | 職責 | 主要端點 |
|----------|------|----------|
| `operations` | 行動 CRUD、狀態管理 | `GET/POST /api/operations` |
| `targets` | 目標主機管理 | `GET/POST /api/operations/{id}/targets` |
| `techniques` | ATT&CK 技術庫與執行狀態 | `GET /api/techniques` |
| `ooda` | OODA 循環觸發與儀表板 | `POST /api/operations/{id}/ooda/trigger` |
| `facts` | 情報蒐集結果 | `GET /api/operations/{id}/facts` |
| `vulnerabilities` | 弱點發現 | `GET /api/operations/{id}/vulns` |
| `recon` | 偵察掃描觸發 | `POST /api/operations/{id}/recon` |
| `agents` | C2 Agent 管理 | `GET /api/operations/{id}/agents` |
| `c5isr` | C5ISR 態勢感知 | `GET /api/operations/{id}/c5isr` |
| `constraints` | 作戰約束條件 | `GET /api/operations/{id}/constraints` |
| `attack_graph` | 攻擊圖引擎 | `GET /api/operations/{id}/attack-graph` |
| `dashboard` | 總覽面板資料 | `GET /api/operations/{id}/dashboard` |
| `terminal` | 互動式終端機 | `POST /api/operations/{id}/terminal/exec` |
| `tools` | MCP 工具註冊與狀態 | `GET /api/tools` |
| `reports` | 滲透報告產生 | `POST /api/operations/{id}/reports` |
| `recommendations` | AI 建議 | `GET /api/operations/{id}/recommendations` |
| `opsec` | OPSEC 監控 | `GET /api/operations/{id}/opsec` |
| `logs` | 即時日誌 | `GET /api/operations/{id}/logs` |
| `objectives` | 任務目標 | `GET/POST /api/operations/{id}/objectives` |
| `missions` | 任務排程 | `POST /api/operations/{id}/missions` |
| `engagements` | 測試案例管理 | `GET/POST /api/engagements` |
| `poc` | PoC 記錄 | `GET/POST /api/operations/{id}/poc` |
| `health` | 健康檢查 | `GET /api/health` |
| `admin` | 管理功能 | `GET /api/admin/*` |
| `ws` | WebSocket 即時推播 | `WS /api/ws/{operation_id}` |
| `playbooks` | 技術 Playbook 知識庫 | `GET /api/playbooks` |

#### 2.1.2 服務層（Services）

| 服務名稱 | 職責 | 內部依賴 | 外部依賴 |
|----------|------|----------|----------|
| `OODAController` | OODA 循環協調器，無業務邏輯，僅調度下列五大服務 | FactCollector, OrientEngine, DecisionEngine, EngineRouter, C5ISRMapper | WebSocketManager |
| `FactCollector` | Observe 階段：彙整所有情報（主機、服務、憑證、弱點） | — | asyncpg |
| `OrientEngine` | Orient 階段：以 Claude AI 分析情勢並產生攻擊建議 | FactCollector | Anthropic Claude API (MOCK_LLM) |
| `DecisionEngine` | Decide 階段：從建議中選擇最優技術與目標 | — | — |
| `EngineRouter` | Act 階段：路由至正確的執行引擎 | DirectSSHEngine, C2EngineClient, MetasploitEngineAdapter, MCPEngineClient | 外部 C2/MSF |
| `ConstraintEngine` | 從 C5ISR 健康度 + OPSEC 狀態推導作戰約束 | C5ISRMapper, OpsecMonitor | — |
| `C5ISRMapper` | 將作戰狀態映射到 C5ISR 六域（Command, Control, Comms, Computers, Cyber, ISR） | — | asyncpg |
| `ReconEngine` | 偵察掃描協調（nmap、OSINT、弱點查詢） | MCPClientManager | MCP Tool Servers |
| `InitialAccessEngine` | 初始存取技術執行 | EngineRouter | SSH / C2 |
| `OsintEngine` | 開源情報蒐集 | MCPClientManager | MCP OSINT Server |
| `AttackGraphEngine` | 攻擊圖建構與路徑分析 | — | asyncpg |
| `AgentSwarm` | 多 Agent 並行執行調度 | EngineRouter | C2 Engine |
| `KillChainEnforcer` | Kill Chain 階段推進驗證 | — | — |
| `OpsecMonitor` | 操作安全監控（噪音等級、偵測風險） | — | asyncpg |
| `ReportGenerator` | 結構化滲透測試報告產出 | — | asyncpg |
| `ScopeValidator` | RoE 範圍驗證，確保操作不超出授權範圍 | — | — |
| `VulnLookup` | CVE 弱點查詢（NVD） | — | MCP Vuln Server |
| `ExploitValidator` | Exploit 可用性驗證 | — | — |
| `MCPClientManager` | MCP Tool Server 連線管理與呼叫 | — | 7 台 MCP Servers |
| `LLMClient` | Anthropic Claude SDK 封裝 | — | Anthropic API |
| `MissionProfileLoader` | 任務設定檔載入（SR/CO/SP/FA） | — | — |
| `NodeSummarizer` | 攻擊圖節點摘要 | LLMClient | Claude API |
| `SkillLoader` | 技術 Playbook 知識庫載入 | — | 檔案系統 |

#### 2.1.3 客戶端層（Clients）

| 客戶端 | 職責 | 通訊協定 |
|--------|------|----------|
| `DirectSSHEngine` | 直接 SSH 連線執行指令（內建，無需外部 C2） | SSH (paramiko / asyncssh) |
| `C2EngineClient` | Caldera C2 REST API 整合 | HTTP REST |
| `MetasploitEngineAdapter` | Metasploit Framework RPC 整合 | MSGPACK-RPC |
| `MCPEngineClient` | MCP Tool Server 統一呼叫介面 | HTTP (Streamable HTTP) |
| `MockC2Client` | 測試用模擬 C2 客戶端 | In-memory |

### 2.2 核心模組詳細設計

#### OODAController（循環協調器）

**職責：** 協調 Observe → Orient → Decide → Act 四階段轉換，本身不含業務邏輯，僅負責呼叫五大服務並管理狀態轉移。

**核心介面：**

```python
class OODAController:
    def __init__(
        self,
        fact_collector: FactCollector,
        orient_engine: OrientEngine,
        decision_engine: DecisionEngine,
        engine_router: EngineRouter,
        c5isr_mapper: C5ISRMapper,
        ws_manager: WebSocketManager,
        swarm_executor: SwarmExecutor | None = None,
    ): ...

    async def trigger_cycle(
        self, db: asyncpg.Connection, operation_id: str
    ) -> OODAIteration:
        """觸發一輪 OODA 循環：
        1. Observe — FactCollector 彙整情報
        2. Orient — OrientEngine (Claude AI) 分析態勢
        3. Decide — DecisionEngine 選擇技術+目標
        4. Act    — EngineRouter 路由至執行引擎
        5. 更新 C5ISR 態勢 + 推播 WebSocket 事件
        """
```

**OODA 循環流程：**

```
                    ┌──────────────────────────────┐
                    │       OODAController         │
                    │      trigger_cycle()         │
                    └──────────┬───────────────────┘
                               │
           ┌───────────────────┼───────────────────┐
           ▼                   ▼                   ▼
    ConstraintEngine    FactCollector        C5ISRMapper
    evaluate()          observe()            refresh()
           │                   │                   │
           ▼                   ▼                   │
    OperationalConstraints  Facts[]                │
           │                   │                   │
           └───────┬───────────┘                   │
                   ▼                               │
            OrientEngine.analyze()                 │
            (Claude AI / MOCK_LLM)                 │
                   │                               │
                   ▼                               │
            Recommendations[]                      │
                   │                               │
                   ▼                               │
            DecisionEngine.select()                │
                   │                               │
                   ▼                               │
            EngineRouter.execute()                 │
            ├── DirectSSHEngine                    │
            ├── C2EngineClient                     │
            ├── MetasploitEngineAdapter             │
            └── MCPEngineClient                    │
                   │                               │
                   ▼                               │
            WebSocketManager.broadcast() ◄─────────┘
```

#### OrientEngine（AI 分析引擎）

**職責：** 以 Anthropic Claude API 分析蒐集到的情報（Facts），產生結構化的攻擊建議（Recommendations）。

**關鍵行為：**

- `MOCK_LLM=true` 時回傳預設建議，不呼叫外部 API
- 接受 `OperationalConstraints` 限制建議數量（`orient_max_options`）
- 輸出符合 Pydantic v2 模型的結構化 JSON
- **結構化 Failure Context（SPEC-053）**：Orient 查詢 `technique_executions` 時 JOIN `targets` 並讀取 `failure_category` 欄位，把失敗紀錄以 `<technique> on <host> [<category>]: <error>` 格式餵給 LLM，讓 system prompt 的 Rule #2 Dead Branch Pruning 能真正運作
- **Rule #9 IA-Exhausted Exploit Pivot（SPEC-053, ADR-046）**：當 Section 7 Failed Techniques 含 T1110.*/T1078.* with `[auth_failure]` 類別，且 target 有 `service.open_port` fact 匹配 `exploitable_banners.yaml` signature，system prompt 強制推薦 T1190 + `engine=metasploit`。明確聲明為 Rule #6（No Redundant Recommendations）的 exception

#### EngineRouter（執行引擎路由器）

**職責：** 根據技術需求與目標平台，將 Act 階段的指令路由到正確的執行引擎。

**路由邏輯：**

| 條件 | 路由目標 |
|------|----------|
| 目標支援 SSH + 無需持久 Agent | `DirectSSHEngine` |
| 目標有已部署 Caldera Agent | `C2EngineClient` |
| 需要 Metasploit 模組 | `MetasploitEngineAdapter` |
| MCP 工具可執行 | `MCPEngineClient` |
| 測試/開發環境 | `MockC2Client` |

**執行引擎列舉（`ExecutionEngine` enum）：** SSH, PERSISTENT_SSH, C2, METASPLOIT, WINRM, MCP, MOCK

**SPEC-053 擴充：結構化失敗分類**

- 模組層新增 `_classify_failure(error, engine) -> str` 純函數 heuristic，將錯誤訊息分類為 8 種 `failure_category` 值之一：`auth_failure`, `service_unreachable`, `exploit_failed`, `privilege_insufficient`, `prerequisite_missing`, `tool_error`, `timeout`, `unknown`
- 所有執行路徑（`_execute_initial_access`, `_execute_mcp`, `_execute_metasploit`, `_finalize_execution` 匯流）在失敗時寫入 `technique_executions.failure_category`，供 OrientEngine 下一輪 Observe 時消費
- **跨類別 Pivot 的歸屬**：本 Router 不做執行層 auto-pivot（拒絕 ADR-046 選項 A）；當 IA 失敗時返回 `engine='initial_access'` + `failure_category='auth_failure'`，由 Orient 於下一 OODA iteration 依 Rule #9 決定是否推 T1190

#### MetasploitRPCEngine（SPEC-053 One-Shot Mode）

**職責：** 透過 msfrpcd RPC 執行 exploit module，但**不維持 persistent session**。

**關鍵行為：**

- 每次 `_run_exploit()` 都是獨立一次循環：launch exploit → poll for new session → write probe_cmd → read output → `shell.stop()` 釋放
- 移除原本「walk `client.sessions.list` 找 target_host match 重用」的邏輯（SPEC-053 前曾導致 vsftpd 2.3.4 backdoor 僵屍 session 汙染）
- Session wait timeout 可由 `settings.METASPLOIT_SESSION_WAIT_SEC`（預設 60 秒）配置
- 成功回傳 `{status: success, shell: sid, output, engine: metasploit}`——其中 `shell` 欄位只作審計紀錄，**session 在 return 時已被 stop**
- `backend/app/routers/terminal.py` 偵測到 `credential.root_shell` fact 時，透過 `MetasploitRPCEngine.get_exploit_for_service()` 重跑 exploit 建立 fresh session 供 websocket 使用

### 2.3 前端模組結構

```
frontend/src/
├── app/                          # Next.js App Router 頁面
│   ├── warroom/                  # 戰情室（主操作面板）
│   ├── operations/               # 行動管理
│   ├── attack-graph/             # 攻擊圖視覺化 (react-force-graph-3d)
│   ├── attack-surface/           # 攻擊面分析
│   ├── vulns/                    # 弱點列表
│   ├── tools/                    # MCP 工具管理
│   ├── decisions/                # AI 決策歷史
│   ├── opsec/                    # OPSEC 監控
│   ├── poc/                      # PoC 記錄
│   └── planner/                  # 任務規劃器
├── components/
│   ├── atoms/                    # 基礎元件（Badge, Button, Toggle）
│   ├── layout/                   # 版面配置（Sidebar）
│   ├── c5isr/                    # C5ISR 視覺化
│   │   ├── MermaidRenderer       # Mermaid 圖表渲染
│   │   ├── OODAFlowDiagram       # OODA 流程圖
│   │   ├── C5ISRHealthGrid       # C5ISR 六域健康面板
│   │   └── ConstraintStatusPanel # 約束條件狀態面板
│   ├── nav/                      # 導覽元件（TabBar）
│   ├── warroom/                  # 戰情室專用元件
│   ├── terminal/                 # 互動式終端機
│   ├── ooda/                     # OODA 視覺化元件
│   ├── vulns/                    # 弱點顯示元件
│   ├── tools/                    # 工具管理元件
│   ├── mitre/                    # ATT&CK 矩陣元件
│   ├── cards/                    # 卡片元件
│   ├── modal/                    # 對話框元件
│   ├── planner/                  # 規劃器元件
│   └── data/                     # 資料展示元件
├── hooks/                        # 自定義 React Hooks
│   ├── useWebSocket.ts           # WebSocket 連線管理
│   ├── useC5ISRData.ts           # C5ISR 態勢資料
│   ├── useOODA.ts                # OODA 狀態與觸發
│   ├── useOperation.ts           # 行動狀態
│   ├── useAttackGraph.ts         # 攻擊圖資料
│   ├── useVulns.ts               # 弱點資料
│   ├── useTools.ts               # MCP 工具狀態
│   ├── useTerminal.ts            # 終端機互動
│   ├── useReconScan.ts           # 偵察掃描
│   ├── useLiveLog.ts             # 即時日誌
│   ├── useOPSEC.ts               # OPSEC 監控
│   ├── useSituationData.ts       # 態勢資料
│   ├── useStageCounts.ts         # Kill Chain 階段計數
│   ├── useExecutionUpdate.ts     # 執行狀態更新
│   ├── useGlobalAlerts.ts        # 全域警報
│   └── useMCPServers.ts          # MCP Server 狀態
└── i18n/                         # next-intl 國際化（en / zh-TW）
```

---

## 3. 資料設計

### 3.1 ER Diagram 描述

```
operations (1) ──< (N) targets
    │                    │
    │                    └──< (N) vuln_findings
    │
    ├──< (N) ooda_iterations
    │         │
    │         └── → recommendations (1)
    │         └── → technique_executions (1)
    │
    ├──< (N) facts
    │         │
    │         ├── → source_technique (FK)
    │         └── → source_target (FK)
    │
    ├──< (N) agents
    │         └── → host (FK → targets)
    │
    ├──< (N) c5isr_statuses
    │
    ├──< (N) constraints (runtime, derived)
    │
    ├──< (N) logs
    │
    ├──< (N) reports
    │
    └──< (N) opsec_events

techniques (獨立，與 operations 透過 technique_executions 關聯)
    └── mitre_id (T1003.001) + tactic + kill_chain_stage

tools (獨立，MCP 工具註冊表)
    └── tool_id + category + mitre_techniques[]

engagements (獨立，測試案例容器)
    └──< (N) operations
```

### 3.2 核心資料模型

**`operations` — 滲透行動：**

| 欄位 | 類型 | 說明 |
|------|------|------|
| `id` | UUID | 主鍵 |
| `code` | VARCHAR | 行動代碼，如 `OP-2024-017` |
| `name` | VARCHAR | 行動名稱 |
| `codename` | VARCHAR | 代號，如 `PHANTOM-EYE` |
| `strategic_intent` | TEXT | 戰略目標描述 |
| `status` | ENUM | `planning / active / paused / completed / aborted` |
| `current_ooda_phase` | ENUM | `observe / orient / decide / act / failed` |
| `ooda_iteration_count` | INT | 已完成 OODA 循環次數 |
| `threat_level` | FLOAT | 威脅等級 0.0-10.0 |
| `success_rate` | FLOAT | 成功率 0-100 |
| `techniques_executed` | INT | 已執行技術數 |
| `techniques_total` | INT | 總計畫技術數 |
| `active_agents` | INT | 存活 Agent 數 |
| `automation_mode` | ENUM | `manual / semi_auto / auto_full` |
| `risk_threshold` | ENUM | `low / medium / high / critical` |
| `mission_profile` | ENUM | `SR (隱匿偵察) / CO (秘密行動) / SP (標準滲透) / FA (全面突擊)` |
| `created_at` | TIMESTAMPTZ | 建立時間 |
| `updated_at` | TIMESTAMPTZ | 更新時間 |

**`targets` — 目標主機：**

| 欄位 | 類型 | 說明 |
|------|------|------|
| `id` | UUID | 主鍵 |
| `hostname` | VARCHAR | 主機名稱，如 `DC-01` |
| `ip_address` | VARCHAR | IP 位址，如 `10.0.1.5` |
| `os` | VARCHAR | 作業系統，如 `Windows Server 2019` |
| `role` | VARCHAR | 角色，如 `Domain Controller` |
| `network_segment` | VARCHAR | 網段，如 `10.0.1.0/24` |
| `is_compromised` | BOOLEAN | 是否已攻破 |
| `is_active` | BOOLEAN | 是否存活 |
| `privilege_level` | VARCHAR | 當前權限等級 (`SYSTEM / Admin / User`) |
| `operation_id` | UUID FK | 所屬行動 |

**`techniques` — ATT&CK 技術：**

| 欄位 | 類型 | 說明 |
|------|------|------|
| `id` | UUID | 主鍵 |
| `mitre_id` | VARCHAR | MITRE ATT&CK ID，如 `T1003.001` |
| `name` | VARCHAR | 技術名稱 |
| `tactic` | VARCHAR | 戰術分類，如 `Credential Access` |
| `tactic_id` | VARCHAR | 戰術 ID，如 `TA0006` |
| `kill_chain_stage` | ENUM | `recon / weaponize / deliver / exploit / install / c2 / action` |
| `risk_level` | ENUM | `low / medium / high / critical` |
| `platforms` | TEXT[] | 支援平台列表 |

**`facts` — 情報事實：**

| 欄位 | 類型 | 說明 |
|------|------|------|
| `id` | UUID | 主鍵 |
| `trait` | VARCHAR | 情報特徵，如 `host.user.name` |
| `value` | TEXT | 情報值，如 `CORP\Administrator` |
| `category` | ENUM | `credential / host / network / osint / service / vulnerability / file / poc / web / defense` |
| `source_technique_id` | UUID FK | 來源技術 |
| `source_target_id` | UUID FK | 來源目標 |
| `operation_id` | UUID FK | 所屬行動 |
| `score` | INT | 情報可信度分數 |
| `collected_at` | TIMESTAMPTZ | 蒐集時間 |

**`ooda_iterations` — OODA 循環迭代：**

| 欄位 | 類型 | 說明 |
|------|------|------|
| `id` | UUID | 主鍵 |
| `operation_id` | UUID FK | 所屬行動 |
| `iteration_number` | INT | 迭代序號 |
| `phase` | ENUM | 當前階段 |
| `observe_summary` | TEXT | Observe 階段摘要 |
| `orient_summary` | TEXT | Orient 階段摘要（AI 分析） |
| `decide_summary` | TEXT | Decide 階段摘要 |
| `act_summary` | TEXT | Act 階段摘要 |
| `started_at` | TIMESTAMPTZ | 開始時間 |
| `completed_at` | TIMESTAMPTZ | 完成時間 |

**`vuln_findings` — 弱點發現：**

| 欄位 | 類型 | 說明 |
|------|------|------|
| `cve_id` | VARCHAR | CVE 編號 |
| `service` | VARCHAR | 受影響服務 |
| `version` | VARCHAR | 軟體版本 |
| `cvss_score` | FLOAT | CVSS 分數 0.0-10.0 |
| `severity` | VARCHAR | `critical / high / medium / low / info` |
| `description` | TEXT | 弱點描述 |
| `exploit_available` | BOOLEAN | 是否有公開 exploit |
| `target_id` | UUID FK | 所屬目標 |
| `operation_id` | UUID FK | 所屬行動 |

**`c5isr_statuses` — C5ISR 態勢：**

| 欄位 | 類型 | 說明 |
|------|------|------|
| `id` | UUID | 主鍵 |
| `operation_id` | UUID FK | 所屬行動 |
| `domain` | ENUM | `command / control / comms / computers / cyber / isr` |
| `status` | ENUM | `operational / active / nominal / engaged / scanning / degraded / offline / critical` |
| `health_pct` | FLOAT | 健康度 0-100 |
| `detail` | TEXT | 詳細說明 |
| `numerator` | INT | 分子指標（如存活 Agent 數） |
| `denominator` | INT | 分母指標（如 Agent 總數） |
| `metric_label` | VARCHAR | 指標標籤 |

**`agents` — C2 Agent：**

| 欄位 | 類型 | 說明 |
|------|------|------|
| `id` | UUID | 主鍵 |
| `paw` | VARCHAR | Agent 識別碼，如 `AGENT-7F3A` |
| `host_id` | UUID FK | 所在目標主機 |
| `status` | ENUM | `alive / dead / pending / untrusted` |
| `privilege` | VARCHAR | 權限等級 |
| `last_beacon` | TIMESTAMPTZ | 最後回報時間 |
| `platform` | VARCHAR | 平台（windows / linux） |
| `operation_id` | UUID FK | 所屬行動 |

**`tools` — MCP 工具註冊表：**

| 欄位 | 類型 | 說明 |
|------|------|------|
| `tool_id` | VARCHAR | 工具唯一識別碼 |
| `name` | VARCHAR | 工具名稱 |
| `kind` | ENUM | `tool / engine` |
| `category` | ENUM | `reconnaissance / enumeration / vulnerability_scanning / credential_access / exploitation / execution` |
| `enabled` | BOOLEAN | 是否啟用 |
| `config_json` | JSONB | 工具設定 |
| `mitre_techniques` | TEXT[] | 關聯 MITRE 技術 ID |
| `risk_level` | VARCHAR | 風險等級 |

### 3.3 Migration 計畫

| Migration 版本 | 說明 | 狀態 |
|----------------|------|------|
| V001 | 初始化 schema：operations, targets, techniques, facts | 已完成 |
| V002 | ooda_iterations, recommendations | 已完成 |
| V003 | agents, c5isr_statuses | 已完成 |
| V004 | vuln_findings, opsec_events | 已完成 |
| V005 | tools 註冊表、engagements | 已完成 |
| V006 | attack_graph 節點與邊 | 已完成 |
| V007 | reports, logs | 已完成 |
| 後續 | 全文搜尋索引、分區策略 | 規劃中 |

**Migration 原則：**

- 使用工具：Alembic（SQLAlchemy migration 框架）
- 資料庫驅動：asyncpg（純 async PostgreSQL driver）
- 連線池：`DatabaseManager` 封裝 `asyncpg.create_pool(min_size=5, max_size=20, command_timeout=60)`
- 必須向前相容，支援滾動部署
- 禁止在 migration 中撰寫業務邏輯

---

## 4. API 合約

### 4.1 基本規範

- **Base URL：** `/api`
- **認證：** 無（ADR-011：POC 階段跳過認證）
- **內容類型：** `Content-Type: application/json`
- **回應序列化：** `ORJSONResponse`（高效 JSON 序列化）
- **時間格式：** ISO 8601（`2026-01-15T10:30:00Z`）
- **ID 格式：** UUID v4（字串表示）
- **WebSocket：** `/api/ws/{operation_id}`

### 4.2 通用回應格式

**成功回應（單一資源）：**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Operation PHANTOM-EYE",
  "status": "active",
  ...
}
```

**成功回應（列表）：**

```json
[
  { "id": "...", "name": "...", ... },
  { "id": "...", "name": "...", ... }
]
```

**錯誤回應：**

```json
{
  "detail": "Operation not found"
}
```

### 4.3 核心 API 端點

#### 行動管理

| 方法 | 端點 | 說明 |
|------|------|------|
| `GET` | `/api/operations` | 列出所有行動 |
| `POST` | `/api/operations` | 建立新行動 |
| `GET` | `/api/operations/{id}` | 取得行動詳情 |
| `PATCH` | `/api/operations/{id}` | 更新行動狀態 |
| `DELETE` | `/api/operations/{id}` | 刪除行動 |

#### OODA 循環

| 方法 | 端點 | 說明 |
|------|------|------|
| `POST` | `/api/operations/{id}/ooda/trigger` | 觸發 OODA 循環 |
| `GET` | `/api/operations/{id}/ooda/dashboard` | OODA 儀表板（當前階段、迭代歷史） |
| `GET` | `/api/operations/{id}/ooda/iterations` | OODA 迭代列表 |
| `POST` | `/api/operations/{id}/ooda/directive` | 操作員手動指令注入 |

#### 目標與偵察

| 方法 | 端點 | 說明 |
|------|------|------|
| `GET` | `/api/operations/{id}/targets` | 列出目標主機 |
| `POST` | `/api/operations/{id}/targets` | 新增目標 |
| `POST` | `/api/operations/{id}/recon` | 觸發偵察掃描 |
| `GET` | `/api/operations/{id}/facts` | 列出蒐集到的情報 |
| `GET` | `/api/operations/{id}/vulns` | 列出弱點發現 |

#### 態勢感知

| 方法 | 端點 | 說明 |
|------|------|------|
| `GET` | `/api/operations/{id}/c5isr` | C5ISR 六域狀態 |
| `GET` | `/api/operations/{id}/constraints` | 當前作戰約束 |
| `GET` | `/api/operations/{id}/opsec` | OPSEC 事件與風險 |
| `GET` | `/api/operations/{id}/dashboard` | 綜合儀表板資料 |

#### 執行與工具

| 方法 | 端點 | 說明 |
|------|------|------|
| `GET` | `/api/techniques` | ATT&CK 技術庫 |
| `GET` | `/api/operations/{id}/agents` | 列出 C2 Agents |
| `POST` | `/api/operations/{id}/terminal/exec` | 終端機指令執行 |
| `GET` | `/api/tools` | MCP 工具註冊表 |
| `GET` | `/api/operations/{id}/attack-graph` | 攻擊圖資料 |

#### 報告與日誌

| 方法 | 端點 | 說明 |
|------|------|------|
| `POST` | `/api/operations/{id}/reports` | 產生滲透報告 |
| `GET` | `/api/operations/{id}/logs` | 即時日誌 |

### 4.4 WebSocket 合約

**端點：** `WS /api/ws/{operation_id}`

**事件格式：**

```json
{
  "event": "ooda_phase_changed",
  "data": {
    "phase": "orient",
    "iteration": 5,
    "summary": "Analyzing 42 facts..."
  },
  "timestamp": "2026-01-15T10:30:00Z"
}
```

**事件類型：**

| 事件名稱 | 說明 |
|----------|------|
| `ooda_phase_changed` | OODA 階段轉換 |
| `fact_collected` | 新情報蒐集 |
| `technique_executed` | 技術執行完成 |
| `agent_beacon` | Agent 回報心跳 |
| `c5isr_updated` | C5ISR 態勢更新 |
| `opsec_alert` | OPSEC 警報 |
| `target_compromised` | 目標已攻破 |
| `echo` | 心跳回應 |

### 4.5 全域錯誤碼

| HTTP Status | 說明 |
|-------------|------|
| 404 | 資源不存在（Operation / Target / Technique） |
| 422 | Pydantic 驗證失敗（請求格式錯誤） |
| 500 | 伺服器內部錯誤 |

> 注意：POC 階段無認證（ADR-011），因此不回傳 401/403。

---

## 5. 安全設計

### 5.1 當前安全狀態（POC）

根據 ADR-011，POC 階段**刻意跳過認證與授權**，專注於核心 OODA 引擎驗證。以下為現有安全機制：

| 機制 | 說明 |
|------|------|
| **RoE 範圍驗證** | `ScopeValidator` 確保所有操作不超出授權測試範圍 |
| **指令黑名單** | Terminal 路由對危險指令（`rm -rf`, `mkfs`, `dd`）進行阻擋 |
| **CORS 鎖定** | 僅允許 `localhost` 來源 |
| **無外部暴露** | Backend 綁定 `0.0.0.0:58000` 但預設僅本機存取 |
| **MCP 工具隔離** | 各 MCP Tool Server 獨立容器，權限隔離 |
| **憑證保護** | `.credentials.json` 以 read-only 掛載，不寫入容器 |

### 5.2 OPSEC 監控

`OpsecMonitor` 服務持續追蹤以下指標：

| 指標 | 監控內容 | 回應機制 |
|------|----------|----------|
| **噪音等級** | 單位時間內的掃描/指令頻率 | `NoiseLevel` enum: low/medium/high |
| **認證失敗** | 登入嘗試失敗次數 | `AUTH_FAILURE` 事件 |
| **偵測風險** | IDS/IPS 觸發可能性 | `DETECTION` 事件 → ConstraintEngine 介入 |
| **偽跡殘留** | 操作留下的痕跡 | `ARTIFACT` 事件 |

**OPSEC 嚴重度分級：** `INFO` → `WARNING` → `CRITICAL`

### 5.3 約束條件引擎

`ConstraintEngine` 從 C5ISR 健康度和 OPSEC 狀態推導作戰約束，影響 OODA 循環行為：

```python
class OperationalConstraints:
    warnings: list[ConstraintWarning]          # 軟約束（建議性）
    hard_limits: list[ConstraintLimit]         # 硬約束（強制性）
    orient_max_options: int = 3                # Orient 最大建議數
    min_confidence_override: float | None      # 最低信心度覆蓋
    max_parallel_override: int | None          # 最大並行數覆蓋
    blocked_targets: list[str]                 # 封鎖目標列表
```

### 5.4 後續安全規劃

| 項目 | 優先級 | 預計版本 |
|------|--------|----------|
| JWT 認證 + RBAC | High | v0.3 |
| API Rate Limiting | Medium | v0.3 |
| Audit Log | Medium | v0.3 |
| TLS 傳輸加密 | High | v0.2（部署至非本機時） |
| Secrets Management | Medium | v0.3 |

---

## 6. 效能設計

### 6.1 非同步架構

整個後端基於 Python async/await 建構：

| 元件 | 非同步策略 |
|------|----------|
| **Web 框架** | FastAPI + uvloop（高效事件迴圈） |
| **資料庫** | asyncpg 連線池（min=5, max=20, timeout=60s） |
| **WebSocket** | FastAPI 原生 WebSocket，每個 Operation 一個房間 |
| **HTTP 回應** | ORJSONResponse（比標準 json 快 3-10 倍） |
| **AI 呼叫** | Anthropic SDK async client |
| **執行引擎** | 各 Client 皆為 async 實作 |

### 6.2 連線池管理

```python
class DatabaseManager:
    def __init__(self, dsn: str, min_size: int = 5, max_size: int = 20):
        ...

    async def startup(self) -> None:
        self._pool = await asyncpg.create_pool(
            dsn=self._dsn,
            min_size=self._min_size,
            max_size=self._max_size,
            command_timeout=60,
        )

    async def connection(self) -> AsyncGenerator[asyncpg.Connection, None]:
        async with self._pool.acquire() as conn:
            yield conn
```

### 6.3 即時推播

WebSocket Manager 採用 per-operation 房間模式：

- 每個 Operation 維護一組 WebSocket 連線
- OODA 循環每個階段轉換時推播事件
- 前端透過 `useWebSocket` hook 訂閱，無需輪詢

### 6.4 併發處理

| 策略 | 說明 |
|------|------|
| **AgentSwarm** | 多 Agent 並行執行，`max_parallel_override` 受 ConstraintEngine 控制 |
| **MCP 並行呼叫** | MCPClientManager 支援同時呼叫多個 Tool Server |
| **無狀態 API** | Backend 不儲存 Session 狀態，支援水平擴展 |

---

## 7. ADR 交叉引用

| ADR ID | 標題 | 影響的設計決策 |
|--------|------|----------------|
| ADR-001 | 初始技術棧選擇 | 第 1 節架構風格、技術選型 |
| ADR-002 | Monorepo 專案結構 | 第 2 節模組設計、目錄結構 |
| ADR-003 | OODA 循環引擎架構 | 第 2.2 節 OODAController 設計 |
| ADR-004 | 半自動 + 手動覆蓋模式 | 第 2.2 節 AutomationMode enum |
| ADR-005 | PentestGPT Orient Engine | 第 2.2 節 OrientEngine (Claude AI) |
| ADR-006 | 執行引擎抽象與授權隔離 | 第 2.2 節 EngineRouter |
| ADR-007 | WebSocket 即時通訊 | 第 4.4 節 WebSocket 合約 |
| ADR-008 | SQLite 資料表設計（已遷移至 PostgreSQL） | 第 3 節資料設計 |
| ADR-009 | 前端元件架構 | 第 2.3 節前端模組結構 |
| ADR-010 | Docker Compose 部署 | 第 1.3 節部署架構 |
| ADR-011 | POC 跳過認證 | 第 5.1 節安全設計 |
| ADR-012 | C5ISR 框架映射 | 第 2.1.2 節 C5ISRMapper |
| ADR-013 | Orient Prompt 工程策略 | 第 2.2 節 OrientEngine |
| ADR-014 | Anthropic SDK 遷移 | 第 2.1.2 節 LLMClient |
| ADR-015 | Recon + Initial Access Kill Chain | 第 2.1.2 節 ReconEngine, InitialAccessEngine |
| ADR-017 | Direct SSH Engine | 第 2.1.3 節 DirectSSHEngine |
| ADR-021 | Agent 能力匹配 for C2 | 第 2.1.2 節 AgentSwarm |
| ADR-024 | MCP 架構與 Tool Server 整合 | 第 2.1.2 節 MCPClientManager |
| ADR-025 | Exploit 驗證層 | 第 2.1.2 節 ExploitValidator |
| ADR-027 | OODA + Agent 並行 Swarm | 第 2.1.2 節 AgentSwarm |
| ADR-028 | 攻擊圖引擎 | 第 2.1.2 節 AttackGraphEngine |
| ADR-030 | 標準化工具上架流程 | 第 2.1.3 節 MCP Tool Servers |

> 所有 ADR 狀態必須為 **Accepted** 後，對應設計方案才可進入實作階段。

---

## 附錄

### A. 技術債追蹤

| 項目 | 說明 | 優先級 | 預計解決版本 |
|------|------|--------|--------------|
| 認證系統缺失 | ADR-011 決定 POC 跳過認證，需在正式版補齊 | High | v0.3 |
| SQLite 殘留 | 部分測試仍使用 aiosqlite，需統一為 asyncpg | Medium | v0.2 |
| 前端狀態管理 | 目前依賴 hooks + props drilling，需評估 Zustand/Jotai | Low | v0.3 |
| MCP 工具錯誤處理 | 部分 MCP 呼叫回傳假錯誤（-32603），需加強重試與驗證 | Medium | v0.2 |
| OPSEC 事件持久化 | OPSEC 事件目前部分在記憶體中，需完整持久化至 PostgreSQL | Medium | v0.2 |

### B. 變更歷史

| 版本 | 日期 | 變更摘要 | 作者 |
|------|------|----------|------|
| v0.1.0 | 2026-03-25 | 初版建立，涵蓋完整架構、模組、資料、API、安全與效能設計 | Athena Team |

### C. 相關文件

- [`docs/adr/`](./adr/) — 架構決策記錄（ADR-001 ~ ADR-030）
- [`CLAUDE.md`](../CLAUDE.md) — AI-SOP-Protocol 行為憲法
- [`docker-compose.yml`](../docker-compose.yml) — 容器編排設定
- [`backend/app/`](../backend/app/) — 後端原始碼
- [`frontend/src/`](../frontend/src/) — 前端原始碼
- [`tools/`](../tools/) — MCP Tool Server 原始碼

### D. 列舉型別完整參考

| Enum 名稱 | 值 | 用途 |
|-----------|-----|------|
| `OODAPhase` | observe, orient, decide, act, failed | OODA 循環階段 |
| `OperationStatus` | planning, active, paused, completed, aborted | 行動狀態 |
| `TechniqueStatus` | untested, queued, running, success, partial, failed | 技術執行狀態 |
| `MissionStepStatus` | queued, running, completed, failed, skipped | 任務步驟狀態 |
| `AgentStatus` | alive, dead, pending, untrusted | Agent 狀態 |
| `ExecutionEngine` | ssh, persistent_ssh, c2, mock, metasploit, winrm, mcp | 執行引擎類型 |
| `C5ISRDomain` | command, control, comms, computers, cyber, isr | C5ISR 六域 |
| `C5ISRDomainStatus` | operational, active, nominal, engaged, scanning, degraded, offline, critical | C5ISR 域狀態 |
| `FactCategory` | credential, host, network, osint, service, vulnerability, file, poc, web, defense | 情報分類 |
| `LogSeverity` | info, success, warning, error, critical | 日誌嚴重度 |
| `KillChainStage` | recon, weaponize, deliver, exploit, install, c2, action | Kill Chain 階段 |
| `RiskLevel` | low, medium, high, critical | 風險等級 |
| `AutomationMode` | manual, semi_auto, auto_full | 自動化模式 |
| `MissionProfile` | SR (隱匿偵察), CO (秘密行動), SP (標準滲透), FA (全面突擊) | 任務設定檔 |
| `NoiseLevel` | low, medium, high | 噪音等級 |
| `OPSECSeverity` | info, warning, critical | OPSEC 嚴重度 |
| `OPSECEventType` | burst, auth_failure, high_noise, artifact, detection | OPSEC 事件類型 |
| `ConstraintLevel` | warning, critical | 約束等級 |
| `ToolKind` | tool, engine | 工具種類 |
| `ToolCategory` | reconnaissance, enumeration, vulnerability_scanning, credential_access, exploitation, execution | 工具分類 |
| `AccessStatus` | active, lost, unknown | 存取狀態 |
