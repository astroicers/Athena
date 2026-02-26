# SPEC-004：REST API 路由

> 實作 35+ REST API 端點 + WebSocket 路由 + FastAPI 入口。

| 欄位 | 內容 |
|------|------|
| **規格 ID** | SPEC-004 |
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

## ✅ 驗收標準（Done When）

- [ ] `make test-filter FILTER=spec_004` 全數通過
- [ ] `cd backend && uvicorn app.main:app --port 8000` — 啟動無錯誤
- [ ] `curl http://localhost:8000/docs` — 顯示 Swagger UI
- [ ] `curl http://localhost:8000/api/operations` — 回傳 JSON 列表
- [ ] `curl http://localhost:8000/api/operations/{id}/c5isr` — 回傳 6 筆 C5ISR 狀態
- [ ] `curl http://localhost:8000/api/techniques` — 回傳技術目錄
- [ ] `curl http://localhost:8000/api/operations/{id}/recommendations/latest` — 回傳推薦
- [ ] `curl http://localhost:8000/api/health` — 回傳 `{"status": "ok", ...}`
- [ ] Swagger UI 顯示所有 35+ 端點，按 tag 分組
- [ ] WebSocket `ws://localhost:8000/ws/{operation_id}` 可連線

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
