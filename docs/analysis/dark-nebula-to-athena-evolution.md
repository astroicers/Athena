# 從 Dark Nebula 到 Athena：兩代攻擊平台架構演進分析

> 文件日期：2026-02-27
> 狀態：分析完成

---

## 摘要

本文件對比同一開發者的兩代網路安全攻擊平台架構：

- **Dark Nebula 生態系**（2022-2024）：`dark-nebula` / `dark-nebula-frontend` / `dark-nebula-backend` / `recon-pocket`
- **Athena**（2024-present）：AI 驅動 C5ISR 網路作戰指揮平台

核心發現：

1. Dark Nebula 解決的是 **工具編排** 問題 — 如何高效執行滲透工具並串接結果
2. Athena 解決的是 **作戰決策** 問題 — 如何決定執行哪些工具、何時執行、為什麼執行
3. 這代表從 **工具管線架構 (Tool Pipeline)** 到 **決策迴圈架構 (Decision Loop)** 的範式轉移

---

## 一、專案概覽

### Dark Nebula 生態系

| 倉庫 | 技術棧 | 用途 | 狀態 |
|------|--------|------|------|
| `dark-nebula` | Makefile/YAML, k3s, Argo Workflows | 編排與工作流管理 | 停止開發 (2024-06) |
| `dark-nebula-backend` | TypeScript, Express.js, K8s Client | 後端 API + K8s 整合 | 早期階段 (2024-02) |
| `dark-nebula-frontend` | Vue3, Nuxt3, TypeScript, Tailwind | 儀表板 UI | 早期階段 (2024-02) |
| `recon-pocket` | Python, Bash, Docker Compose | 單機偵察工具 | 低度維護 (2026-01) |

### Athena

| 組件 | 技術棧 | 用途 |
|------|--------|------|
| Backend | Python 3.11, FastAPI, SQLite, Pydantic | OODA 引擎 + C5ISR 映射 + API |
| Frontend | Next.js 14, React 18, Tailwind v4, Three.js | 指揮官儀表板 + 3D 可視化 |
| 執行層 | MITRE Caldera (Apache 2.0), Shannon (AGPL-3.0 API 隔離) | 技術執行引擎 |
| AI 層 | PentestGPT + Claude/GPT-4 | Orient 戰術分析 |

---

## 二、核心範式轉移

> **Dark Nebula 問的是「如何高效執行工具？」**
> **Athena 問的是「如何做出正確的戰術決策？」**

| 面向 | Dark Nebula | Athena |
|------|-----------|--------|
| 核心範式 | **工具管線 (Tool Pipeline)** | **決策迴圈 (Decision Loop)** |
| 編排方式 | Argo Workflows (宣告式 YAML DAG) | OODA Controller (動態狀態機) |
| 工具封裝 | 自建 Docker 容器 (三層模式) | 委託執行引擎 (Caldera/Shannon API) |
| 決策層 | 人工判斷 (黑箱) | AI + 人類混合 (風險分級自動化) |
| 情報分析 | 無 | PentestGPT Orient Engine |
| 組織框架 | 無 | C5ISR 軍事六域 |
| 即時性 | 輪詢 Argo 狀態 | WebSocket 推播 (7 種事件) |
| 基建需求 | Kubernetes 叢集 | Docker Compose |

---

## 三、使用者原始三步構想的映射

開發者在 Dark Nebula 時期的設計理念為三步走：

1. **建立工具容器** — 讓系統可以使用該容器
2. **串接容器成 Workflow** — 建立輸入輸出，形成一個 recon workflow
3. **擴增與整併** — workflow 輸出經指揮官判斷後，串接至下一個 workflow，最終整併成完整攻擊套路

### Step 1：建立工具容器

| | Dark Nebula | Athena |
|---|-----------|--------|
| 實現方式 | **直接實現** — 每個滲透工具獨立 Docker 容器，三層模式：Tool → Parser → Uploader | **抽象委託** — 工具以 Caldera "ability" 形式存在，透過 `BaseEngineClient.execute()` 統一呼叫 |
| 工具清單 | subfinder, assetfinder, amass, nmap, nikto, gobuster, nuclei, sqlmap 等 14+ 容器 | Caldera 內建 ability 庫 (MITRE ATT&CK 對應) |
| 新增工具 | 寫 Dockerfile + Parser + Uploader + Argo Template | 在 Caldera 註冊 ability 或擴充 `BaseEngineClient` |
| 優勢 | 完全控制每個工具的版本、配置、輸出格式 | 零維護成本，直接使用 Caldera 社群生態 |
| 劣勢 | 需自行維護所有容器映像 | 失去工具層級的細粒度控制 |

**關鍵差異**：Dark Nebula 自建工具容器生態，Athena 則站在 Caldera 的肩膀上。

### Step 2：容器串接成 Workflow

| | Dark Nebula | Athena |
|---|-----------|--------|
| 實現方式 | **Argo Workflows DAG** — `templateRef` 組合多個 WorkflowTemplate，定義 step 依賴 | **OODA 迴圈** — 每次迭代動態決定下一步技術，非預先定義 |
| 資料流 | Tool stdout → Parser (JSON) → Uploader (Redis) → Combiner (聚合) | ExecutionResult → FactCollector (結構化情報) → SQLite Facts 表 |
| 並行模式 | Argo DAG 原生支援設計時平行 | 單一 OODA 循環序列執行，每步由 AI 動態選擇 |
| 範例 | `subdomain-enumeration.yaml`: subfinder ‖ assetfinder ‖ crt-sh → combiner | OODA iteration: observe → orient (AI 推薦 3 選項) → decide → act |

**關鍵差異**：Dark Nebula 的工作流是靜態的（設計時決定），Athena 的是動態的（執行時決定）。

### Step 3：指揮官判斷 + 串接至下一個 Workflow → 整併成完整攻擊套路

**這是 Dark Nebula 未能完成、Athena 核心突破的部分。**

| | Dark Nebula | Athena |
|---|-----------|--------|
| 指揮官判斷 | **黑箱** — 人類看 Redis/Argo UI 輸出，腦中判斷，手動觸發下一個 workflow | **結構化** — `OrientEngine` 提供 3 個戰術選項含推理、風險等級、信心度；`DecisionEngine` 依風險分級自動/半自動決策 |
| Workflow 串接 | 手動：Phase 1 → 人工判讀 → 手動觸發 Phase 2 | 自動：OODA iteration N 完成 → FactCollector 收集情報 → Orient 分析 → 自動觸發 iteration N+1 |
| 攻擊套路整併 | **未實現** — 設計構想但未落地 | **已實現** — Operation 物件追蹤整條 kill chain，mission_steps 定義完整攻擊路徑，所有 OODA 迭代歷史串成完整作戰記錄 |

**關鍵發現**：Step 3 是 Dark Nebula 架構的天花板，也是 Athena 架構的起點。Dark Nebula 能串接工具，但 workflow 之間的「指揮官判斷」是一個人工黑箱。Athena 將這個黑箱替換為：

- `FactCollector` — 從工具輸出中結構化擷取情報
- `OrientEngine` — AI 驅動的戰術分析，產出 3 個帶推理的選項
- `DecisionEngine` — 依風險等級自動/半自動決策

---

## 四、八維度深度對比

### 4.1 編排模型

| | Dark Nebula | Athena |
|---|-----------|--------|
| 引擎 | Argo Workflows (Kubernetes-native) | OODA Loop Controller (Python state machine) |
| 定義方式 | 宣告式 YAML (靜態 DAG) | 動態每次迭代 (AI 驅動) |
| 排程 | DAG 平行度在設計時確定 | 序列 OODA 循環，每步動態選擇 |
| 適應性 | 無 — workflow 照原樣執行 | 有 — 失敗技術觸發死路剪枝，下次 Orient 自動規避 |
| 可重現性 | 高 — 同一 YAML 產出同一結果 | 低 — AI 輸出不確定 |

### 4.2 工具抽象

| | Dark Nebula | Athena |
|---|-----------|--------|
| 封裝 | 三層容器模式 (Tool → Parser → Uploader) | `BaseEngineClient` 介面統一封裝 |
| 粒度 | 每個工具獨立映像，完全控制 | 執行委託給外部引擎，工具為黑箱 |
| 擴展 | 新 Dockerfile + Argo Template | Caldera 內註冊或實作 `BaseEngineClient` |
| 輸出 | Raw text → Python Parser → JSON → Redis | `ExecutionResult` dataclass (success, output, facts[], error) |

### 4.3 資料持久化

| | Dark Nebula | Athena |
|---|-----------|--------|
| 訊息匯流排 | Redis (pub/sub + key-value) | SQLite (持久) + WebSocket (即時) |
| 資料模型 | Ad-hoc JSON (每工具不同) | 13 Enums + 12 Pydantic Models + 13 SQL 表 |
| 情報持久化 | Redis (預設揮發性) | SQLite Facts 表 (category, trait, value, score) |
| 跨階段資料 | Kubernetes PVC (檔案) | 關聯查詢跨 ooda_iterations、technique_executions、facts、recommendations 表 |

### 4.4 決策自動化

| | Dark Nebula | Athena |
|---|-----------|--------|
| 決策者 | 人類操作員 (純手動) | AI + 人類混合 (ADR-004) |
| 自動化 | 無 | 風險分級：CRITICAL→手動 / HIGH→確認對話框 / MEDIUM→閾值比較 / LOW→自動執行 |
| 透明度 | 無 (決策在人類腦中) | 完整：situation_assessment + reasoning_text + confidence + 3 ranked options |
| 稽核軌跡 | 無 | recommendations 表 + ooda_iterations 表 |

### 4.5 情報分析

| | Dark Nebula | Athena |
|---|-----------|--------|
| 分析引擎 | 無 | PentestGPT Orient Engine (5 大分析框架) |
| Kill Chain 感知 | 隱式 (Phase 1/2/3/4 命名) | 顯式：14 階段 MITRE ATT&CK kill chain 追蹤 |
| 失敗學習 | 無 — 失敗工具就是失敗 | 死路剪枝：失敗技術觸發同類前置條件的排除 |

### 4.6 即時通訊

| | Dark Nebula | Athena |
|---|-----------|--------|
| 更新機制 | 輪詢 Argo API | WebSocket 推播 |
| 事件類型 | N/A | 7 種：log.new, agent.beacon, execution.update, ooda.phase, c5isr.update, fact.new, recommendation |

### 4.7 前端介面

| | Dark Nebula | Athena |
|---|-----------|--------|
| 框架 | Nuxt3/Vue3 | Next.js 14/React 18 |
| 主要視角 | 工具執行儀表板 | C5ISR 指揮官儀表板 (6 域健康度) |
| 可視化 | 平面 workflow 狀態 | 3D 力導向網路拓撲 (react-force-graph-3d) |
| 互動模式 | 觸發 workflow → 檢視結果 | 決策迴圈：檢視推薦 → 批准/駁回 → 觀察結果 |

### 4.8 基礎建設

| | Dark Nebula | Athena |
|---|-----------|--------|
| 需求 | k3s 叢集 + Argo Operator + Redis + Docker Registry | Docker Compose (2 容器：backend + frontend) |
| 門檻 | 高 (需 Kubernetes 知識) | 低 (單一 `docker-compose up`) |
| 擴展性 | k3s 橫向擴展 (加節點) | 單機部署 |

---

## 五、Athena 超越原始構想的獨創概念

以下概念在 Dark Nebula 中完全不存在：

| 概念 | 說明 |
|------|------|
| **C5ISR 六域框架** | 所有功能映射至 Command/Control/Comms/Computers/Cyber/ISR，每域計算健康百分比 (0-100) 和狀態 (8 級：operational → critical) |
| **OODA 迴圈引擎** | 6 個服務解耦 (observe/orient/decide/act/mapper/controller)，作為一級架構原語而非概念覆蓋 |
| **AI 戰術顧問** | OrientEngine 每次迭代提供 3 個帶推理的戰術選項，整合 5 大分析框架 |
| **風險分級自動化** | DecisionEngine 依技術風險等級漸進式授權 (ADR-004) |
| **雙引擎抽象 + 授權隔離** | Caldera (Apache 2.0) + Shannon (AGPL-3.0) 透過 API 邊界嚴格隔離 |
| **3D 戰場可視化** | react-force-graph-3d + Three.js 力導向網路拓撲 |
| **結構化情報模型** | Facts 表含 category/trait/value/score 欄位，支援跨迭代情報累積 |

---

## 六、得與失

### 獲得

| 能力 | 說明 |
|------|------|
| AI 輔助決策 | 從「人類逐行看輸出」升級為「AI 分析 + 3 選項推薦」 |
| 自適應執行 | 失敗技術觸發死路剪枝，下次 Orient 自動規避 |
| 作戰框架 | C5ISR 六域提供整體態勢感知，不再是散亂的工具狀態 |
| 完整稽核軌跡 | 每次 OODA 迭代留存 observe/orient/decide/act 摘要 |
| 低基建門檻 | Docker Compose 取代 Kubernetes 叢集 |
| 即時態勢感知 | WebSocket 推播取代輪詢 |

### 失去

| 能力 | 說明 | 彌補路徑 |
|------|------|----------|
| 工具容器直接控制 | 無法快速新增自定義工具，受限於 Caldera ability 庫 | 擴充 `BaseEngineClient` 實作 `ContainerEngineClient` |
| K8s 橫向擴展 | 單機部署無法水平擴展工具執行 | ROADMAP Phase 9.6 Helm Chart |
| 宣告式工作流可重現性 | OODA 動態循環不可逐步重現 (AI 輸出不確定) | `ooda_iterations` 表提供稽核但非重現 |
| 離線操作 | Orient 階段需要 LLM API 連線 | `MOCK_LLM=True` 降級模式 |
| 快速偵察模式 | 無 recon-pocket 等輕量單目標偵察 | 可作為簡化 OODA 模板實現 |
| 工具層級可觀測性 | 三層模式 (Tool→Parser→Uploader) 的細粒度輸出解析 | FactCollector 部分補償 |

---

## 七、反向增強：Dark Nebula 概念可強化 Athena 的方向

### 7.1 容器工具擴展層

將 Dark Nebula 的三層容器模式引入 Athena 作為第三個執行引擎：

```
BaseEngineClient (現有介面)
├── CalderaClient (現有)
├── ShannonClient (現有)
└── ContainerEngineClient (提議)
    ├── DockerToolRunner — 執行自定義 Docker 容器
    ├── OutputParser — 結構化輸出擷取
    └── FactAdapter — 轉換為 ExecutionResult + Facts
```

讓指揮官不僅能指揮 Caldera 武器庫，還能整合任意自定義工具容器。

### 7.2 Argo 子編排器

ACT 階段可引入 Argo 作為複雜多工具操作的子編排器：

- 簡單執行 → CalderaClient (單一技術)
- 複雜執行 → ArgoWorkflowClient (多工具 DAG，使用 Dark Nebula 的容器化工具庫)

### 7.3 Redis 高吞吐訊息匯流排

ROADMAP Phase 9.6 已規劃 Redis for WebSocket pub/sub。Dark Nebula 的 Redis 資料流架構（metadata enrichment + scan aggregation 模式）可提供成熟參考。

### 7.4 Quick Recon 模式

受 recon-pocket 啟發的輕量偵察功能，作為 OODA 循環前的預偵察階段：

- 使用者輸入目標 domain
- 自動執行 subfinder + nmap 等基礎偵察
- 結果直接注入 FactCollector
- 為首次 OODA Orient 提供充足初始情報

---

## 八、架構對比總覽矩陣

| 架構面向 | Dark Nebula | Athena | 演進方向 |
|----------|-----------|--------|----------|
| 核心範式 | Tool Pipeline | Decision Loop | 管線 → 迴圈 |
| 編排引擎 | Argo Workflows (K8s) | OODA Controller (Python) | 宣告式 → 自適應 |
| 工具封裝 | Docker 容器 (自建) | 引擎委託 (Caldera) | 自建 → 消費 |
| 決策機制 | 人工 (黑箱) | AI + 人類 (結構化) | 手動 → 半自動 |
| 情報分析 | 無 | PentestGPT + FactCollector | 缺席 → 核心功能 |
| 組織框架 | 無 | C5ISR 六域 | 無結構 → 軍事框架 |
| 資料持久化 | Redis (揮發性) | SQLite (持久性) | 揮發 → 持久 |
| 前端框架 | Vue3 (Nuxt3) | React (Next.js 14) | Vue → React |
| 即時通訊 | 輪詢 | WebSocket (7 事件) | Pull → Push |
| 基建門檻 | K8s 叢集 (高) | Docker Compose (低) | 複雜 → 簡單 |
| AI/LLM | 無 | Claude/GPT-4 (Orient) | 零 → 核心 |

---

## 九、結語：從工具操作員到作戰指揮官

```
Dark Nebula 時代                    Athena 時代
─────────────                      ──────────
「我要跑 subfinder」               「目標網段有什麼弱點？」
「nmap 掃完了，看看結果」            「Orient 建議 3 條攻擊路徑」
「手動判斷，觸發下一個 workflow」    「DecisionEngine：風險 MEDIUM，自動核准」
「最後手動整理成報告」              「Operation 完整記錄 kill chain 歷程」
```

### 三步構想完成度

```
            ┌──────────────────────────┐
            │   使用者三步構想完成度   │
            ├──────────┬───────────────┤
            │Dark Nebula│    Athena    │
  Step 1    │  ████ 100%│   ████ 100% │  建立工具容器 / 工具介面
  Step 2    │  ████ 100%│   ████ 100% │  串接成 workflow / OODA 迴圈
  Step 3    │  ░░░░  20%│   ████  90% │  指揮官判斷 + 攻擊套路整併
            └──────────┴───────────────┘
```

Dark Nebula 的三步構想中，Step 3「指揮官判斷」在當時是手動黑箱。Athena 用 AI Orient + Decision Engine 將這個黑箱結構化、自動化，實現了從「工具操作員」到「作戰指揮官」的範式跳躍。

而 Dark Nebula 的容器化工具生態與宣告式工作流仍具價值——不是作為獨立系統，而是作為 Athena 執行層的擴展選項，讓指揮官不僅能指揮 Caldera 內建武器庫，還能整合任意自定義工具容器。

---

## 專案處置建議

| 專案 | 建議處置 | 理由 |
|------|----------|------|
| `recon-pocket` | **Archive + 提煉工具容器至 Athena** | 工具容器可復用，編排層報廢（詳見 recon-pocket-integration-assessment.md） |
| `dark-nebula` | **Archive** | 編排概念已被 OODA Controller 取代 |
| `dark-nebula-frontend` | **Archive** | 技術棧不同 (Vue3 → React)，無可復用碼 |
| `dark-nebula-backend` | **Archive** | 技術棧不同 (Express → FastAPI)，無可復用碼 |
