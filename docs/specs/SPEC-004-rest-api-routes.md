# SPEC-004：REST API 路由

> 實作 35+ REST API 端點 + WebSocket 路由 + FastAPI 入口。

| 欄位 | 內容 |
|------|------|
| **規格 ID** | SPEC-004 |
| **狀態** | Accepted |
| **關聯 ADR** | ADR-008（Schema）、ADR-011（無 Auth）、ADR-007（WebSocket） |
| **估算複雜度** | 中 |
| **建議模型** | Sonnet |
| **HITL 等級** | standard |

---

## 🎯 目標（Goal）

> 根據 `data-architecture.md` Section 6 的 REST API 定義，實作 11 個 Router 模組 + 1 個 WebSocket 路由 + FastAPI 入口 `main.py`，提供完整的後端 API 層供前端與外部工具消費。

---

## 📥 輸入規格（Inputs）

| 參數名稱 | 型別 | 來源 | 限制條件 |
|----------|------|------|----------|
| 35+ API 端點定義 | 文件 | `data-architecture.md` Section 6 | 路徑、方法、功能嚴格對映 |
| 7 種 WebSocket 事件 | ADR | ADR-007 決策 | 事件名稱與格式嚴格對映 |
| 無身份驗證 | ADR | ADR-011 | 不加任何 auth middleware |
| CORS 配置 | ADR | ADR-011 | 僅允許 localhost:3000 |
| Pydantic Models | SPEC | SPEC-002 輸出 | 使用已定義的 Model 作為回應型別 |
| Database 層 | SPEC | SPEC-003 輸出 | 使用 `get_db()` 作為 Depends |

---

## 📤 輸出規格（Expected Output）

**成功情境：**

### 1. `backend/app/main.py`

```python
# FastAPI 應用入口
# - CORS middleware: allow_origins=["http://localhost:3000"]
# - Lifespan: startup → init_db() + seed if empty
# - 掛載所有 router (prefix="/api")
# - WebSocket route 單獨掛載 (prefix="/ws")
```

### 2. 11 個 Router 檔案

| 檔案 | 路由前綴 | 端點數 |
|------|---------|-------|
| `routers/operations.py` | `/api/operations` | 5 |
| `routers/ooda.py` | `/api/operations/{id}/ooda` | 4 |
| `routers/techniques.py` | `/api/techniques` | 2 |
| `routers/missions.py` | `/api/operations/{id}/mission` | 4 |
| `routers/targets.py` | `/api/operations/{id}/targets` + `/topology` | 2 |
| `routers/agents.py` | `/api/operations/{id}/agents` | 2 |
| `routers/facts.py` | `/api/operations/{id}/facts` | 1 |
| `routers/c5isr.py` | `/api/operations/{id}/c5isr` | 2 |
| `routers/logs.py` | `/api/operations/{id}/logs` | 1 |
| `routers/recommendations.py` | `/api/operations/{id}/recommendations` | 2 |
| `routers/health.py` | `/api/health` | 1 |
| `routers/ws.py` | `/ws/{operation_id}` | 1 (WebSocket) |

### 3. 完整端點清單

```
-- Operations --
GET    /api/operations                                  → List[Operation]
POST   /api/operations                                  → Operation
GET    /api/operations/{id}                             → Operation
PATCH  /api/operations/{id}                             → Operation
GET    /api/operations/{id}/summary                     → OperationSummary (composite)

-- OODA Cycle --
POST   /api/operations/{id}/ooda/trigger                → OODAIteration
GET    /api/operations/{id}/ooda/current                → OODAIteration
GET    /api/operations/{id}/ooda/history                → List[OODAIteration]
GET    /api/operations/{id}/ooda/timeline               → List[OODATimelineEntry]

-- Techniques --
GET    /api/techniques                                  → List[Technique]
GET    /api/operations/{id}/techniques                  → List[TechniqueWithStatus]

-- Mission --
GET    /api/operations/{id}/mission/steps               → List[MissionStep]
POST   /api/operations/{id}/mission/steps               → MissionStep
PATCH  /api/operations/{id}/mission/steps/{sid}         → MissionStep
POST   /api/operations/{id}/mission/execute             → ExecutionResult

-- Targets --
GET    /api/operations/{id}/targets                     → List[Target]
GET    /api/operations/{id}/topology                    → TopologyData

-- Agents --
GET    /api/operations/{id}/agents                      → List[Agent]
POST   /api/operations/{id}/agents/sync                 → SyncResult

-- Facts --
GET    /api/operations/{id}/facts                       → List[Fact]

-- C5ISR --
GET    /api/operations/{id}/c5isr                       → List[C5ISRStatus]
PATCH  /api/operations/{id}/c5isr/{domain}              → C5ISRStatus

-- Logs --
GET    /api/operations/{id}/logs                        → PaginatedLogs

-- Recommendations --
GET    /api/operations/{id}/recommendations/latest      → PentestGPTRecommendation
POST   /api/operations/{id}/recommendations/{rid}/accept → AcceptResult

-- Health --
GET    /api/health                                       → HealthStatus

-- WebSocket --
WS     /ws/{operation_id}                               → Event stream
```

### 4. API Schema 模型（Request/Response）

在各 router 檔案中定義（或獨立 `schemas.py`）：

- `OperationCreate` / `OperationUpdate` — 建立/更新作戰的請求 body
- `MissionStepCreate` — 建立任務步驟的請求 body
- `TopologyData` — `{ nodes: List[TopologyNode], edges: List[TopologyEdge] }`
- `OODATimelineEntry` — 時間軸呈現用的扁平結構
- `TechniqueWithStatus` — Technique + 最新 TechniqueExecution 狀態合併
- `PaginatedLogs` — `{ items: List[LogEntry], total: int, page: int, page_size: int }`
- `HealthStatus` — `{ status: str, version: str, services: { database, caldera, shannon, websocket, llm } }`（SPEC-009 定義回應格式）

### 5. WebSocket Manager

```python
# routers/ws.py
# - 連線管理（per operation_id）
# - 7 種事件廣播：log.new, agent.beacon, execution.update,
#   ooda.phase, c5isr.update, fact.new, recommendation
# - JSON 格式：{ "event": str, "data": dict, "timestamp": str }
```

**失敗情境：**

| 錯誤類型 | HTTP Code | 處理方式 |
|----------|-----------|----------|
| Operation 不存在 | 404 | `{"detail": "Operation not found"}` |
| 參數格式錯誤 | 422 | FastAPI 自動 Pydantic 驗證 |
| C5ISR domain 無效 | 400 | `{"detail": "Invalid domain"}` |
| 種子資料未載入 | 200 | 回傳空列表（不報錯） |

---

## ⚠️ 邊界條件（Edge Cases）

- `GET /api/operations/{id}/summary` 為複合端點——需 JOIN operations + c5isr + latest recommendation
- `GET /api/operations/{id}/topology` 需從 targets 和 agents 建構 nodes/edges（非直接 DB 查詢）
- `POST /api/operations/{id}/ooda/trigger` 為 OODA 引擎的觸發入口——Phase 2 階段僅建立 stub（回傳 mock 或 DB 紀錄），Phase 5 才接入真實引擎
- `POST /api/operations/{id}/agents/sync` 為 Caldera 同步入口——Phase 2 階段回傳 stub
- `POST /api/operations/{id}/mission/execute` 為任務執行入口——Phase 2 階段回傳 stub
- `GET /api/operations/{id}/logs` 需支援分頁（`?page=1&page_size=50`）
- WebSocket 連線斷開時需清理 connection pool
- CORS 僅允許 `http://localhost:3000`（ADR-011）

---

## 🔗 副作用與連動（Side Effects）

| 副作用 | 觸發條件 | 影響的系統/模組 | 驗證方式 |
|--------|---------|----------------|----------|
| API 路徑變更影響前端 fetch 呼叫 | 任一端點 URL 或 HTTP method 變更時 | SPEC-005 `lib/api.ts`、所有 `useOperation`/`useOODA` 等 hooks | 前端 `npm run build` 無錯誤；E2E 測試通過 |
| WebSocket 事件格式變更影響即時更新 | WS 事件名稱或 data 結構變更時 | SPEC-005 `useWebSocket` hook、前端所有訂閱 WS 的元件 | WebSocket 連線測試確認事件格式正確 |
| CORS 設定影響跨域請求 | `allow_origins` 清單變更時 | 前端 localhost:3000 的 API 呼叫 | `curl -H "Origin: http://localhost:3000" ...` 確認 CORS header |
| `main.py` lifespan 影響 DB 初始化 | startup 事件順序或 seed 邏輯變更時 | SPEC-003 `init_db()` 與 `demo_scenario` | 啟動 uvicorn 後確認 `/api/health` 回傳 ok |

### 🔄 Rollback Plan

| 項目 | 說明 |
|------|------|
| **回滾步驟** | 1. `git revert <commit>` 還原 router 與 main.py 變更 2. 確認前端 API 呼叫回退至對應版本 |
| **資料影響** | API 層不持久化資料——資料由 SPEC-003 DB 層管理；POST/PATCH 端點的資料變更需檢查 DB 狀態 |
| **回滾驗證** | `uvicorn app.main:app` 啟動成功；Swagger UI `/docs` 顯示正確端點數 |
| **回滾已測試** | ☑ 否（API 層無狀態，回滾風險低） |

## 🧪 測試矩陣（Test Matrix）

| # | 類型 | 輸入條件 | 預期結果 | 對應場景 |
|---|------|---------|---------|---------|
| P1 | ✅ 正向 | `GET /api/operations` | 200，回傳 Operation 列表（含種子 OP-2024-017） | S1 |
| P2 | ✅ 正向 | `POST /api/operations` 含有效 body | 201，建立新 Operation 並回傳完整物件 | S1 |
| P3 | ✅ 正向 | `GET /api/operations/{id}/c5isr` | 200，回傳 6 筆 C5ISR 狀態 | S1 |
| P4 | ✅ 正向 | `GET /api/health` | 200，回傳 `{"status": "ok", ...}` 含服務狀態 | S1 |
| P5 | ✅ 正向 | `WS /ws/{operation_id}` 連線 | WebSocket 握手成功，接收事件 | S1 |
| N1 | ❌ 負向 | `GET /api/operations/nonexistent-id` | 404，`{"detail": "Operation not found"}` | S2 |
| N2 | ❌ 負向 | `POST /api/operations` body 缺少必填欄位 | 422，Pydantic ValidationError 詳情 | S2 |
| N3 | ❌ 負向 | `PATCH /api/operations/{id}/c5isr/invalid_domain` | 400，`{"detail": "Invalid domain"}` | S2 |
| B1 | 🔶 邊界 | `GET /api/operations/{id}/logs?page=1&page_size=0` | 回傳空列表或 422 參數錯誤 | S3 |
| B2 | 🔶 邊界 | 種子資料未載入時 `GET /api/operations` | 200，回傳空列表（不報錯） | S3 |
| B3 | 🔶 邊界 | WebSocket 連線斷開後重連 | connection pool 清理完成，新連線正常 | S3 |

## 🎭 驗收場景（Acceptance Scenarios）

```gherkin
Feature: SPEC-004 REST API 路由
  作為 Athena 平台開發者
  我想要 35+ REST API 端點與 WebSocket 路由
  以便 前端與外部工具可消費完整的後端 API 層

  Background:
    Given 後端已啟動（uvicorn app.main:app）
    And 資料庫已初始化並載入種子資料（SPEC-003）

  # --- 正向場景 ---

  Scenario: S1 - Operations CRUD 端點正常運作
    Given 種子資料包含 OP-2024-017
    When GET /api/operations
    Then 回傳 200 且列表包含至少 1 筆 Operation
    And 每筆 Operation 含 id、code、codename、status 欄位

  Scenario: S1b - Swagger UI 顯示所有端點
    When 存取 /docs
    Then 頁面渲染 Swagger UI
    And 顯示 35+ 端點按 tag 分組（Operations、OODA、Techniques、Mission 等）

  Scenario: S1c - WebSocket 連線與事件廣播
    Given 有效的 operation_id
    When 建立 WebSocket 連線至 /ws/{operation_id}
    Then 連線握手成功
    And 可接收 JSON 格式事件（含 event、data、timestamp 欄位）

  # --- 負向場景 ---

  Scenario: S2 - 不存在的 Operation 回傳 404
    Given 資料庫中無 id 為 "nonexistent" 的 Operation
    When GET /api/operations/nonexistent
    Then 回傳 404
    And body 包含 {"detail": "Operation not found"}

  Scenario: S2b - 參數格式錯誤回傳 422
    When POST /api/operations 且 body 缺少 code 欄位
    Then 回傳 422
    And body 包含 Pydantic 驗證錯誤詳情

  # --- 邊界場景 ---

  Scenario: S3 - 種子資料未載入時回傳空列表
    Given 資料庫已初始化但無種子資料
    When GET /api/operations
    Then 回傳 200 且列表為空
    And 不拋出錯誤
```

## 🔗 追溯性（Traceability）

| 實作檔案 | 測試檔案 | 最後驗證日期 |
|----------|----------|-------------|
| `backend/app/main.py` | `backend/tests/test_spec_004_api.py` | 2026-03-26 |
| `backend/app/routers/operations.py` | `backend/tests/test_operations_router.py` | 2026-03-26 |
| `backend/app/routers/ooda.py` | `backend/tests/test_ooda_router.py` | 2026-03-26 |
| `backend/app/routers/techniques.py` | `backend/tests/test_techniques_router.py` | 2026-03-26 |
| `backend/app/routers/missions.py` | `backend/tests/test_missions_router.py` | 2026-03-26 |
| `backend/app/routers/targets.py` | `backend/tests/test_targets_router.py` | 2026-03-26 |
| `backend/app/routers/agents.py` | `backend/tests/test_agents_router.py` | 2026-03-26 |
| `backend/app/routers/facts.py` | `backend/tests/test_facts_router.py` | 2026-03-26 |
| `backend/app/routers/c5isr.py` | `backend/tests/test_c5isr_router.py` | 2026-03-26 |
| `backend/app/routers/logs.py` | `backend/tests/test_logs_router.py` | 2026-03-26 |
| `backend/app/routers/recommendations.py` | `backend/tests/test_recommendations_router.py` | 2026-03-26 |
| `backend/app/routers/health.py` | `backend/tests/test_health_router.py` | 2026-03-26 |
| `backend/app/routers/ws.py` | `backend/tests/test_spec_004_api.py`（WebSocket 測試） | 2026-03-26 |
| `backend/app/ws_manager.py` | `backend/tests/test_spec_004_api.py` | 2026-03-26 |

## 📊 可觀測性（Observability）

| 面向 | 說明 |
|------|------|
| **關鍵指標** | API 回應延遲（p50/p95/p99）、每端點錯誤率（4xx/5xx）、WebSocket 活躍連線數、每秒請求數 |
| **日誌** | 每個請求記錄 method + path + status_code + latency（INFO）；422/500 錯誤記錄完整 body（ERROR）；WebSocket 連線/斷開記錄（INFO） |
| **告警** | 5xx 錯誤率 > 1% 持續 5 分鐘觸發告警；API 回應延遲 p95 > 2s 觸發告警 |
| **如何偵測故障** | `GET /api/health` 回傳各子系統狀態（database、caldera、shannon、websocket、llm）；Swagger UI `/docs` 可存取性 |

---

## ✅ 驗收標準（Done When）

- [x] `make test-filter FILTER=spec_004` 全數通過
- [x] `cd backend && uvicorn app.main:app --port 8000` — 啟動無錯誤
- [x] `curl http://localhost:8000/docs` — 顯示 Swagger UI
- [x] `curl http://localhost:8000/api/operations` — 回傳 JSON 列表
- [x] `curl http://localhost:8000/api/operations/{id}/c5isr` — 回傳 6 筆 C5ISR 狀態
- [x] `curl http://localhost:8000/api/techniques` — 回傳技術目錄
- [x] `curl http://localhost:8000/api/operations/{id}/recommendations/latest` — 回傳推薦
- [x] `curl http://localhost:8000/api/health` — 回傳 `{"status": "ok", ...}`
- [x] Swagger UI 顯示所有 35+ 端點，按 tag 分組
- [x] WebSocket `ws://localhost:8000/ws/{operation_id}` 可連線

---

## 🚫 禁止事項（Out of Scope）

- 不要實作 OODA 引擎業務邏輯（`ooda/trigger` 為 stub）——SPEC-007 範圍
- 不要實作 Caldera/Shannon 真實 API 呼叫——SPEC-008 範圍
- 不要加入任何身份驗證 middleware（ADR-011）
- 不要使用 ORM（SQLAlchemy）——使用原生 SQL 查詢
- 不要修改 SPEC-002 已定義的 Model 結構

---

## 📎 參考資料（References）

- 資料架構：[data-architecture.md](../architecture/data-architecture.md) Section 6（REST API Endpoints）
- ADR-007：[WebSocket 即時通訊](../adr/ADR-007-websocket-realtime-communication.md)
- ADR-008：[SQLite Schema](../adr/ADR-008-sqlite-data-schema-design.md)
- ADR-011：[POC 無身份驗證](../adr/ADR-011-no-auth-for-poc.md)
- SPEC-002：Pydantic Models（依賴）
- SPEC-003：Database 層（依賴）

