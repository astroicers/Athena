# Athena — 開發路線圖

> 版本：1.4 | 更新日期：2026-02-26
> 狀態：Phase 0~8.5 完成 — v0.1.0 POC 發佈 | 84 個測試（44 pytest + 40 Vitest）

---

## 總覽

Athena 是一套 AI 驅動的 C5ISR 網路作戰指揮平台。本路線圖描述從設計到正式開源發佈的完整旅程。

**目前進度**：Phase 0~8.5 全部完成。v0.1.0 POC 版本已發佈。後端 44 pytest（60% 覆蓋率）+ 前端 40 Vitest 測試全數通過。

---

## Phase 0：設計與架構 `完成`

> 期間：已完成 | 交付物：全部已推送至 GitHub

### 0.1 UI 設計 `完成`

| 交付物 | 檔案 | 狀態 |
|--------|------|------|
| 設計系統 | `athena-design-system.pen` | 56 個元件、32 個變數 |
| 應用外殼 | `athena-shell.pen` | Sidebar + AlertBanner + ContentSlot |
| C5ISR 指揮看板 | `athena-c5isr-board.pen` | KPI 卡片、OODA 指示器、PentestGPT 推薦 |
| MITRE 導航器 | `athena-mitre-navigator.pen` | ATT&CK 矩陣、Kill Chain、技術詳情 |
| 任務規劃器 | `athena-mission-planner.pen` | 任務步驟、OODA 時間軸、主機卡片 |
| 戰場監控 | `athena-battle-monitor.pen` | 3D 拓樸 Demo、日誌串流、Agent 信標 |

### 0.2 架構文件 `完成`

| 交付物 | 檔案 | 內容 |
|--------|------|------|
| 資料架構 | `docs/architecture/data-architecture.md` | 13 個 Enum、12 個 Model、SQLite Schema、REST API、種子資料 |
| 專案結構 | `docs/architecture/project-structure.md` | Monorepo 佈局、各層職責、開發階段 |
| AI 上下文 | `CLAUDE.md` | 完整專案上下文（C5ISR、OODA、技術棧） |

### 0.3 關鍵設計決策 `完成`

| 決策 | 選擇 | 理由 |
|------|------|------|
| 自動化模式 | 半自動 + 手動覆寫 | 軍事合規 + AI 價值 + PTLR 市場定位 |
| 拓樸視覺化 | react-force-graph-3d | 3D WebGL、粒子動畫、React 原生元件 |
| 後端 | Python 3.11 + FastAPI + SQLite | 輕量 POC、Pydantic 模型 |
| 前端 | Next.js 14 + React 18 + Tailwind v4 | App Router、設計 Token 整合 |
| 執行引擎 | Caldera（主要）+ Shannon（選用） | Apache 2.0 + AGPL-3.0（API 隔離） |

---

## Phase 1：專案骨架 `完成`

> 完成日期：2026-02-25 | SPEC-001

### 1.1 建立目錄骨架

```
Athena/
├── design/          ← 搬入 6 個 .pen 檔
├── backend/app/
│   ├── models/
│   ├── routers/
│   ├── services/
│   ├── clients/
│   └── seed/
├── frontend/src/
│   ├── app/
│   ├── components/
│   ├── types/
│   ├── hooks/
│   └── lib/
└── infra/
```

### 1.2 根目錄設定檔

- [x] `.gitignore` — Python、Node、SQLite、.env 排除規則
- [x] `.env.example` — 所有環境變數及預設值
- [x] `Makefile` — dev、seed、test、clean 指令
- [x] `docker-compose.yml` — 後端 + 前端服務

### 1.3 搬移設計資產

- [x] 將所有 `.pen` 檔從根目錄搬至 `design/`

---

## Phase 2：後端基礎 `完成`

> 完成日期：2026-02-25 | SPEC-002 / SPEC-003 / SPEC-004

### 2.1 Pydantic Models + Enums

- [x] `backend/app/models/enums.py` — 13 個共用列舉
  - OODAPhase、OperationStatus、TechniqueStatus、MissionStepStatus
  - AgentStatus、ExecutionEngine、C5ISRDomain、C5ISRDomainStatus
  - FactCategory、LogSeverity、KillChainStage、RiskLevel、AutomationMode
- [x] 12 個實體模型：Operation、Target、Agent、Technique、TechniqueExecution、Fact、OODAIteration、PentestGPTRecommendation、MissionStep、C5ISRStatus、LogEntry、User

### 2.2 資料庫層

- [x] `backend/app/database.py` — SQLite 連線 + Session 管理
- [x] Schema 初始化 — 13 條 CREATE TABLE 語句
- [x] `backend/app/config.py` — Pydantic BaseSettings

### 2.3 種子資料

- [x] `backend/app/seed/demo_scenario.py` — OP-2024-017「奪取 Domain Admin」
  - 1 個作戰行動、5 個目標主機、4 個 Agent、4 個任務步驟
  - 6 個 C5ISR 域狀態、1 則 PentestGPT 推薦
  - 範例情報、日誌紀錄、OODA 迭代

### 2.4 REST API（核心路由）

- [x] `routers/operations.py` — CRUD + 摘要端點
- [x] `routers/ooda.py` — 觸發、當前、歷史、時間軸
- [x] `routers/techniques.py` — 技術目錄 + 執行矩陣
- [x] `routers/missions.py` — 任務步驟 CRUD + 執行
- [x] `routers/targets.py` — 目標主機 + 拓樸（nodes + edges）
- [x] `routers/agents.py` — Agent 列表 + Caldera 同步
- [x] `routers/c5isr.py` — C5ISR 六域狀態
- [x] `routers/logs.py` — 分頁日誌紀錄
- [x] `routers/ws.py` — WebSocket 即時事件串流

### 2.5 FastAPI 入口

- [x] `backend/app/main.py` — CORS、Lifespan（DB 初始化 + 種子載入）、掛載路由

**驗證**：`cd backend && python -c "from app.models import *"` + `make seed` + API 於 `localhost:8000` 回應

---

## Phase 3：前端基礎 `完成`

> 完成日期：2026-02-26 | SPEC-005

### 3.1 TypeScript 型別

- [x] `frontend/src/types/enums.ts` — 對映後端列舉
- [x] 11 個實體型別檔：operation、target、agent、technique、fact、ooda、recommendation、mission、c5isr、log、api
- [x] `frontend/src/types/index.ts` — 統一匯出

### 3.2 核心佈局（依 Shell 設計稿）

- [x] `app/layout.tsx` — 根佈局含 Sidebar
- [x] `components/layout/Sidebar.tsx` — 導覽 + 系統狀態 + 使用者
- [x] `components/layout/AlertBanner.tsx` — 全域警示列
- [x] `components/layout/PageHeader.tsx` — 頁面標題列
- [x] `components/layout/CommandInput.tsx` — 底部指令輸入

### 3.3 API + WebSocket Hooks

- [x] `lib/api.ts` — Fetch 封裝（base URL、錯誤處理）
- [x] `hooks/useOperation.ts` — 作戰資料管理
- [x] `hooks/useWebSocket.ts` — WebSocket 連線 + 事件派發
- [x] `hooks/useOODA.ts` — OODA 階段訂閱
- [x] `hooks/useLiveLog.ts` — 即時日誌串流

### 3.4 原子元件（依設計系統）

- [x] Button、Badge、StatusDot、Toggle、ProgressBar、HexIcon
- [x] NavItem、TabBar
- [x] HexConfirmModal

**驗證**：`npm run dev` 於 `localhost:3000` 渲染含 Sidebar 的應用外殼

---

## Phase 4：畫面實作 `完成`

> 完成日期：2026-02-26 | SPEC-006

### 4.1 C5ISR 指揮看板（`/c5isr`）— 主儀表板

- [x] 4 張 KPI MetricCard（Agents、成功率、技術數、已竊取資料）
- [x] C5ISR 六域狀態看板含健康度指示列
- [x] OODA 階段指示器
- [x] PentestGPT 推薦卡片
- [x] 作戰行動資料表
- [x] 迷你拓樸預覽

### 4.2 MITRE 導航器（`/navigator`）— ATT&CK 矩陣

- [x] MITRE ATT&CK 矩陣格（按 Tactic 分欄的 MITRECell）
- [x] Kill Chain 進度指示器（7 階段）
- [x] 技術詳情面板
- [x] PentestGPT 建議整合

### 4.3 任務規劃器（`/planner`）— 任務管理

- [x] 任務步驟 DataTable（步驟#、技術、目標、引擎、狀態）
- [x] OODA 時間軸條目
- [x] 主機節點卡片（5 個目標）
- [x] 步驟執行控制

### 4.4 戰場監控（`/monitor`）— 即時作戰

- [x] **3D 網路拓樸**（react-force-graph-3d）
  - 8 種連線類型：攻擊路徑、執行中滲透、C2 通道、掃描、橫向移動、權限提升、資料竊取、網路連結
  - 依狀態變色的發光球體節點
  - 邊線上的粒子流動動畫
  - 節點懸停提示 + 點擊詳情面板
- [x] Agent 信標面板（即時狀態燈號）
- [x] 即時日誌串流（WebSocket 驅動）
- [x] 威脅等級儀表

**驗證**：4 個畫面皆可載入種子資料渲染，WebSocket 事件即時更新

---

## Phase 5：OODA 循環引擎 `完成`

> 完成日期：2026-02-26 | SPEC-007 / SPEC-008

### 5.1 服務層

- [x] `services/ooda_controller.py` — OODA 狀態機（Observe → Orient → Decide → Act）
- [x] `services/fact_collector.py` — 標準化執行結果為情報
- [x] `services/orient_engine.py` — PentestGPT API 整合（態勢評估）
- [x] `services/decision_engine.py` — 基於 AI + 風險 + 自動化模式的技術選擇
- [x] `services/engine_router.py` — 將技術路由至 Caldera 或 Shannon
- [x] `services/c5isr_mapper.py` — 聚合各來源的 C5ISR 域健康度

### 5.2 半自動化邏輯

- [x] 基於風險等級的自動執行（LOW → 自動、MEDIUM → 排隊、HIGH → 確認、CRITICAL → 手動）
- [x] HIGH 風險決策的 HexConfirmModal 整合
- [x] 指揮官可隨時手動覆寫

### 5.3 外部客戶端

- [x] `clients/caldera_client.py` — Caldera REST API（operations、abilities、agents）
- [x] `clients/shannon_client.py` — Shannon API（AI 自適應執行）

**驗證**：透過 API 觸發 OODA 循環 → PentestGPT 推薦技術 → Caldera 執行 → 收集情報 → C5ISR 更新

---

## Phase 6：整合與 Docker 部署 `完成`

> 完成日期：2026-02-26 | SPEC-009 / SPEC-010

### 6.1 Demo 流程：OP-2024-017「PHANTOM-EYE」

```
步驟 1：OBSERVE — Agent 回報網路掃描結果
步驟 2：ORIENT  — PentestGPT 分析：「DC-01 上可執行 LSASS dump」
步驟 3：DECIDE  — 指揮官審閱 3 個選項，批准 T1003.001
步驟 4：ACT     — Caldera 執行 LSASS dump，收集憑證
步驟 5：OBSERVE — 新情報：取得 CORP\Administrator 憑證
步驟 6：ORIENT  — PentestGPT：「已達成 Domain Admin，建議進行資料竊取」
→ 循環持續...
```

### 6.2 WebSocket 事件流

- [x] `log.new` — 即時日誌出現在戰場監控
- [x] `agent.beacon` — Agent 狀態燈號依心跳閃爍
- [x] `execution.update` — 技術執行狀態變更傳播至 MITRE 矩陣
- [x] `ooda.phase` — OODA 指示器在所有畫面同步切換
- [x] `c5isr.update` — 域健康度指示列更新
- [x] `fact.new` — 新情報出現在情報面板
- [x] `recommendation` — PentestGPT 卡片更新為最新建議

### 6.3 Docker 設定

- [x] `backend/Dockerfile` — Python 3.11 + uvicorn
- [x] `frontend/Dockerfile` — Node 20 + Next.js
- [x] `docker-compose.yml` — 一行指令啟動
- [x] `make dev` — 全端開發模式

**驗證**：`docker-compose up` → 開啟瀏覽器 → 看到完整 Demo 場景即時運行

---

## Phase 7：文件與開源發佈 `完成`

> 完成日期：2026-02-26 | SPEC-011 / SPEC-012

### 7.1 文件撰寫

- [x] 重寫 `README.md` — 專案概覽、截圖、快速啟動
- [x] `docs/GETTING_STARTED.md` — 安裝與設定指南
- [x] `docs/architecture.md` — 高層系統架構圖
- [x] `docs/DEMO_WALKTHROUGH.md` — 逐步 Demo 指南
- [x] `CONTRIBUTING.md` — 貢獻指南
- [x] `CHANGELOG.md` — 版本歷史

### 7.1.5 Vendor 整合（SPEC-012）

- [x] Caldera Docker 配置（`infra/caldera/docker-compose.caldera.yml`）
- [x] 基礎設施管理文件（`infra/README.md`）
- [x] Health endpoint 真實連線檢查
- [x] Agent sync 實作
- [x] CalderaClient retry + 版本檢查
- [x] Makefile vendor 管理 targets

### 7.2 開源合規

- [x] 選定授權條款 — Apache 2.0
- [x] `LICENSE` — Apache License 2.0 全文
- [x] 102 個原始碼檔加上 14 行 License Header（48 Python + 54 TypeScript）
- [x] `SECURITY.md` — 負責任揭露政策
- [x] 驗證 Shannon AGPL-3.0 API 隔離合規性 ✅

### 7.3 GitHub Repository

- [x] GitHub Actions CI（ruff + pytest + npm lint + build + docker）
- [x] Issue 模板（Bug 回報、功能請求）
- [x] PR 模板
- [x] ESLint 配置（next/core-web-vitals）
- [x] Ruff 配置（py311, E/F/I rules）
- [x] Dockerfile OCI image labels
- [ ] Repository 描述 + Topics 標籤（需在 GitHub 設定）
- [ ] README 截圖（需手動截圖）

### 7.4 首次發佈

- [x] 標記 `v0.1.0` — POC 版本
- [ ] GitHub Release 含 Changelog（需 push 後在 GitHub 建立）
- [ ] Demo 影片 / GIF 展示 OODA 循環運作（需手動錄製）

---

## Phase 8：後端測試套件 `完成`

> 完成日期：2026-02-26 | SPEC-013

### 8.0 測試基礎設施

- [x] `backend/tests/conftest.py` — in-memory SQLite + 4 fixtures（tmp_db、seeded_db、client、mock_ws_manager）
- [x] `backend/pyproject.toml` — pytest-cov 依賴 + asyncio_mode=auto 配置

### 8.1 API Smoke Tests（SPEC-004）

- [x] 15 個 API 端點 smoke tests — health、operations CRUD、techniques、targets、agents、facts、C5ISR、logs、recommendations、operation summary

### 8.2 OODA Services 單元測試（SPEC-007）

- [x] DecisionEngine（7 tests）— ADR-004 風險閾值規則：手動模式、低信心度、4 種風險等級
- [x] OrientEngine（3 tests）— Mock 推薦驗證：結構、信心度、推薦技術
- [x] FactCollector（3 tests）— 情報萃取：從 execution、空結果、摘要
- [x] C5ISRMapper（4 tests）— 健康度映射：OPERATIONAL/DEGRADED/CRITICAL + 六域更新
- [x] OODAController（3 tests）— 完整循環觸發、DB 記錄、階段更新

### 8.3 Client Mock Tests（SPEC-008）

- [x] MockCalderaClient（5 tests）— execute 已知/未知技術、get_status、list_abilities、is_available
- [x] ShannonClient（3 tests）— disabled 狀態、execute 拋出異常、get_status
- [x] CalderaClient（1 test）— 結構驗證（check_version、sync_agents 可呼叫）

### 8.4 測試指標

- [x] 44 個 pytest 測試全數通過（0.21s）
- [x] `make test-filter FILTER=spec_004` — 15 passed
- [x] `make test-filter FILTER=spec_007` — 20 passed
- [x] `make test-filter FILTER=spec_008` — 9 passed
- [x] 程式碼覆蓋率 60%（`app/` 套件）

---

## Phase 8.5：前端測試套件 `完成`

> 完成日期：2026-02-26 | SPEC-014

### 8.5.0 測試基礎設施

- [x] `frontend/vitest.config.ts` — Vitest 配置（jsdom + @vitejs/plugin-react + vite-tsconfig-paths）
- [x] `frontend/src/test/setup.ts` — @testing-library/jest-dom 全域設定
- [x] `frontend/package.json` — 8 個 devDependencies + test/test:watch/test:coverage scripts

### 8.5.1 API 工具函式測試

- [x] 7 個測試 — toSnakeCase（simple + nested + array + primitives）、fromApiResponse（simple + nested）、api.get（mock fetch）

### 8.5.2 元件測試（28 tests）

- [x] Atom 元件（12 tests）— Button 3 + Toggle 3 + Badge 2 + StatusDot 1 + ProgressBar 2 + HexIcon 1
- [x] Card 元件（4 tests）— MetricCard 2 + TechniqueCard 1 + RecommendCard 1
- [x] Data 元件（4 tests）— DataTable 3 + LogEntryRow 1
- [x] Modal 元件（3 tests）— HexConfirmModal（hidden + visible + critical double confirm）
- [x] OODA 元件（2 tests）— OODAIndicator 1 + OODATimeline 1
- [x] MITRE 元件（1 test）— MITRECell
- [x] C5ISR 元件（1 test）— DomainCard
- [x] Nav 元件（1 test）— TabBar

### 8.5.3 Hook 測試（5 tests）

- [x] useOperation（2 tests）— fetches data + loading state
- [x] useOODA（2 tests）— null initial + phase update on event
- [x] useLiveLog（1 test）— empty array initially

### 8.5.4 CI 整合

- [x] `.github/workflows/ci.yml` — frontend job 加入 `npm test` 步驟
- [x] `make test-frontend` + `make test` 正常運作

### 8.5.5 測試指標

- [x] 40 個 Vitest 測試全數通過（1.55s）
- [x] 21 個測試檔案涵蓋 API utils + 15 個元件 + 3 個 Hooks

---

## Phase 9：未來增強 `未來`

> POC 之後的產品成熟功能

### 9.1 多作戰支援

- [ ] Sidebar 中的作戰列表 / 切換器
- [ ] 每個作戰獨立的 OODA 循環
- [ ] 跨作戰情報共享

### 9.2 進階拓樸

- [ ] VR 模式（react-force-graph-vr）
- [ ] 網路區段分組 / 叢集
- [ ] 攻擊路徑重播 / 時間軸拉桿
- [ ] 匯出拓樸為圖片 / 報告

### 9.3 身份驗證與 RBAC

- [ ] 使用者驗證（JWT）
- [ ] 角色權限：指揮官 / 操作員 / 觀察員
- [ ] 稽核日誌（誰在何時批准了什麼）

### 9.4 報告產出

- [ ] 自動產生滲透測試報告（PDF）
- [ ] MITRE ATT&CK 覆蓋率熱力圖匯出
- [ ] AI 輔助的高層摘要產生

### 9.5 額外整合

- [ ] BloodHound 整合（AD 攻擊路徑）
- [ ] Nmap / Masscan 輸出匯入
- [ ] Cobalt Strike / Havoc C2 連接器
- [ ] Slack / Teams 關鍵事件通知

### 9.6 正式環境強化

- [ ] PostgreSQL 遷移（從 SQLite）
- [ ] Redis 用於 WebSocket pub/sub
- [ ] 速率限制 + 輸入驗證
- [ ] Helm Chart 用於 Kubernetes 部署

---

## 里程碑總覽

| 階段 | 名稱 | 關鍵交付物 | 相依性 |
|------|------|-----------|--------|
| **0** | 設計與架構 | UI 設計稿 + 資料模型文件 | 無 |
| **1** | 專案骨架 | 目錄結構 + 設定檔 | Phase 0 |
| **2** | 後端基礎 | 模型 + 資料庫 + API + 種子資料 | Phase 1 |
| **3** | 前端基礎 | 型別 + 佈局 + Hooks | Phase 1 |
| **4** | 畫面實作 | 4 個畫面 + 3D 拓樸 | Phase 2 + 3 |
| **5** | OODA 循環引擎 | AI 驅動決策循環 | Phase 4 |
| **6** | 整合與 Demo | 端對端 Demo 場景 | Phase 5 |
| **7** | 開源發佈 | 文件 + CI + v0.1.0 標記 | Phase 6 |
| **8** | 後端測試套件 | 44 pytest 測試 + 60% 覆蓋率 | Phase 7 |
| **8.5** | 前端測試套件 | 40 Vitest 測試 + CI 整合 | Phase 8 |
| **9** | 未來增強 | 多作戰、VR、身份驗證、報告 | Phase 8.5 |

```
Phase 0 ████████████████████ 完成
Phase 1 ████████████████████ 完成
Phase 2 ████████████████████ 完成
Phase 3 ████████████████████ 完成
Phase 4 ████████████████████ 完成
Phase 5 ████████████████████ 完成
Phase 6 ████████████████████ 完成
Phase 7 ████████████████████ 完成 ← v0.1.0 POC Release
Phase 8   ████████████████████ 完成 ← 44 pytest tests, 60% coverage
Phase 8.5 ████████████████████ 完成 ← 40 Vitest tests, 21 test files
Phase 9   ░░░░░░░░░░░░░░░░░░░░ 未來
```

---

## 技術棧參考

| 層級 | 技術 | 授權 |
|------|------|------|
| 後端 | Python 3.11 + FastAPI + Pydantic | MIT |
| 資料庫 | SQLite（POC）→ PostgreSQL（正式） | Public Domain |
| 前端 | Next.js 14 + React 18 + Tailwind v4 | MIT |
| 3D 拓樸 | react-force-graph-3d + Three.js | MIT |
| 設計 | Pencil.dev（.pen） | — |
| 執行引擎 | MITRE Caldera | Apache 2.0 |
| 執行引擎（選用） | Shannon | AGPL-3.0（API 隔離） |
| AI 智慧 | PentestGPT | MIT |
| 容器化 | Docker + docker-compose | Apache 2.0 |

---

## 相關文件

- [安裝指南](GETTING_STARTED.md) — 從零開始安裝與開發
- [Demo 操作手冊](DEMO_WALKTHROUGH.md) — 6 步 OODA 循環 Demo
- [系統架構](architecture.md) — 高層架構與 Mermaid 圖
- [資料架構](architecture/data-architecture.md) — 模型、Schema、API、種子資料
- [專案結構](architecture/project-structure.md) — 目錄佈局、各層職責
- [CHANGELOG](../CHANGELOG.md) — 版本歷史（Phase 0~6）
- [CLAUDE.md](../CLAUDE.md) — ASP 行為憲法
