# SPEC-013：Backend Test Suite

> 為 Athena 後端建立 pytest 測試套件，落實 ASP 模板要求的 `make test-filter` 驗收機制。

| 欄位 | 內容 |
|------|------|
| **規格 ID** | SPEC-013 |
| **關聯 ADR** | 無（測試基礎設施，不涉及架構變更） |
| **估算複雜度** | 中 |
| **建議模型** | Sonnet |
| **HITL 等級** | minimal |

---

## 🎯 目標（Goal）

> 建立 pytest 測試套件，覆蓋 API Smoke Tests + OODA Services 單元測試 + Client Mock 測試（~40-50 tests），使 CI 綠燈有實質意義，並落實 ASP SPEC 模板中 `make test-filter FILTER=spec-NNN` 的驗收要求。

---

## 📥 輸入規格（Inputs）

| 參數名稱 | 型別 | 來源 | 限制條件 |
|----------|------|------|----------|
| 12 tables schema | SQL DDL | `database.py` `_CREATE_TABLES` | 測試使用 in-memory SQLite |
| Demo seed data | Python | `seed/demo_scenario.py` | 可選載入供整合測試 |
| Mock clients | Python | `clients/mock_caldera_client.py` | MOCK_CALDERA=true |
| Mock LLM | Config | `config.py` MOCK_LLM | MOCK_LLM=true |
| 6 個 OODA services | Python | `services/*.py` | 測試需注入 mock ws_manager |
| 11 個 API routers | Python | `routers/*.py` | 透過 httpx.AsyncClient 測試 |

---

## 📤 輸出規格（Expected Output）

**成功情境：**

### 1. Test Infrastructure（`backend/tests/conftest.py`）

```python
# Fixtures:
# - tmp_db: in-memory SQLite, 12 tables initialized, per-test isolation
# - seeded_db: tmp_db + demo_scenario seed data
# - client: httpx.AsyncClient → FastAPI app, get_db overridden to tmp_db
# - mock_ws_manager: MagicMock for WebSocketManager
```

### 2. API Smoke Tests（`backend/tests/test_spec_004_api.py`）

覆蓋：health、operations CRUD、techniques、targets、agents、facts、c5isr、logs、recommendations、operation summary — 約 15 tests

### 3. OODA Services 單元測試（`backend/tests/test_spec_007_ooda_services.py`）

覆蓋：
- DecisionEngine（7 tests）：ADR-004 風險閾值全路徑
- OrientEngine（3 tests）：MOCK_LLM 模式回傳驗證
- FactCollector（3 tests）：萃取與摘要
- C5ISRMapper（4 tests）：health→status 映射 + 六域更新
- OODAController（3 tests）：完整循環 + DB 記錄驗證

### 4. Client Mock Tests（`backend/tests/test_spec_008_clients.py`）

覆蓋：MockCalderaClient 5 methods + Shannon disabled state + CalderaClient 介面 — 約 8 tests

**失敗情境：**

| 錯誤類型 | 處理方式 |
|----------|----------|
| DB fixture 初始化失敗 | conftest 檢查 aiosqlite 可用 |
| Import 循環 | 測試在 backend/ 目錄執行，使用 `app.` prefix |
| WebSocket 依賴 | 透過 MagicMock 注入，不建立真實連線 |

---

## ⚠️ 邊界條件（Edge Cases）

- Case 1：in-memory SQLite 不支援 WAL mode → conftest 跳過 WAL pragma
- Case 2：seed data 依賴 operations table 為空 → 每個 test 使用新 DB
- Case 3：FastAPI lifespan 在測試中不自動觸發 → 手動 init_db
- Case 4：aiosqlite.Row factory 需在每個 connection 設定
- Case 5：OODAController singleton 需在測試間重置（清除 `_controller` 全域變數）

---

## 副作用與連動（Side Effects）

| 變更項目 | 影響範圍 | 說明 |
|----------|----------|------|
| `conftest.py` fixtures | 全後端測試 | `tmp_db`, `seeded_db`, `client`, `mock_ws_manager` 為全域 fixtures，新測試檔可直接引用 |
| `Makefile` targets | CI/CD | `test-backend`, `test-filter`, `coverage` 新增或更新，影響 CI pipeline |
| `requirements-dev.txt` | 開發環境 | 新增 `pytest-asyncio`, `pytest-cov`, `httpx` 等測試依賴 |

---

## Rollback Plan

| 步驟 | 指令 | 驗證 |
|------|------|------|
| 1. 還原程式碼 | `git revert <commit>` | `git log` 確認 revert commit |
| 2. 確認生產碼不受影響 | `make lint` | lint 通過（測試碼獨立於 production） |
| 3. 驗證 CI | CI pipeline 仍可執行（test target 退化為空或跳過） | 不阻擋 deploy |

---

## 測試矩陣（Test Matrix）

| ID | 類型 | 場景 | 輸入 | 預期結果 |
|----|------|------|------|----------|
| P1 | Positive | API Smoke — Health endpoint | `GET /api/health` via httpx.AsyncClient | HTTP 200, `status: "ok"` |
| P2 | Positive | OODA Service — DecisionEngine 風險閾值 | risk_score=0.8, threshold=0.7 | 回傳 `requires_approval=True` |
| P3 | Positive | Client Mock — MockCalderaClient execute | mock 模式呼叫 `execute()` | 回傳 `ExecutionResult(success=True)` |
| N1 | Negative | API — 不存在的 operation ID | `GET /api/operations/nonexistent` | HTTP 404 |
| N2 | Negative | OODA Service — 空 observe summary | `orient_engine.analyze(op_id, "")` | 回傳 fallback mock recommendation |
| B1 | Boundary | DB fixture — 空資料庫查詢 | `GET /api/operations` on empty tmp_db | HTTP 200, 空陣列 `[]` |
| B2 | Boundary | OODAController singleton 重置 | 連續兩個 test 使用不同 DB | 各 test 隔離，無 state 洩漏 |

---

## 驗收場景（Acceptance Scenarios）

```gherkin
Feature: Backend Test Suite 測試基礎設施與覆蓋率

  Scenario: S1 — pytest 測試套件全數通過
    Given backend/tests/ 目錄包含 test_spec_004, test_spec_007, test_spec_008 測試檔
    And conftest.py 定義 tmp_db, client, mock_ws_manager fixtures
    When 執行 make test-backend
    Then 所有測試通過（0 failures）
    And 測試數量 >= 40

  Scenario: S2 — 測試過濾器可定位特定 SPEC 測試
    Given test_spec_007_ooda_services.py 存在
    When 執行 make test-filter FILTER=spec_007
    Then 僅執行 spec_007 相關測試
    And 測試全數通過

  Scenario: S3 — 測試間資料庫隔離
    Given 兩個連續測試使用 tmp_db fixture
    When 第一個測試寫入 operation 資料
    And 第二個測試查詢 operations
    Then 第二個測試查詢結果為空（per-test 隔離）
```

---

## 追溯性（Traceability）

| 類型 | 路徑 |
|------|------|
| Test Fixtures | `backend/tests/conftest.py` |
| API Smoke Tests | `backend/tests/test_spec_004_api.py` |
| OODA Service Tests | `backend/tests/test_spec_007_ooda_services.py` |
| Client Mock Tests | `backend/tests/test_spec_008_clients.py` |
| Orient Engine Tests | `backend/tests/test_orient_engine.py` |
| E2E OODA Tests | `backend/tests/test_e2e_ooda_loop.py` |
| 被測對象 — Routers | `backend/app/routers/*.py`（health, operations, techniques, targets, agents, facts, c5isr, logs, recommendations） |
| 被測對象 — Services | `backend/app/services/decision_engine.py`, `orient_engine.py`, `fact_collector.py`, `c5isr_mapper.py`, `ooda_controller.py` |
| 被測對象 — Clients | `backend/app/clients/c2_client.py`, `mock_c2_client.py` |
| Makefile | `Makefile`（test-backend, test-filter, coverage targets） |

---

## 可觀測性（Observability）

| 項目 | 內容 |
|------|------|
| CI 報告 | `make test-backend` 輸出 pytest summary，含 pass/fail/skip 計數 |
| 覆蓋率報告 | `make coverage` 輸出 HTML + terminal 覆蓋率報告，目標 > 60% |
| 測試篩選 | `make test-filter FILTER=spec_NNN` 輸出僅匹配測試結果 |
| 失敗診斷 | pytest `-v --tb=short` 預設輸出失敗測試的 traceback |

---

## ✅ 驗收標準（Done When）

- [x] `make test-backend` 全數通過（40+ tests, 0 failures）
- [x] `make test-filter FILTER=spec_004` 通過
- [x] `make test-filter FILTER=spec_007` 通過
- [x] `make test-filter FILTER=spec_008` 通過
- [x] `make coverage` 報告 > 60% 覆蓋率
- [x] `make lint` 無 error
- [x] 已更新 `CHANGELOG.md`

---

## 🚫 禁止事項（Out of Scope）

- 不要實作前端測試（jest / vitest）
- 不要實作 E2E / 瀏覽器自動化測試
- 不要實作 WebSocket 整合測試（僅 mock ws_manager）
- 不要修改既有 production code 來適應測試（測試適應 code，不是反過來）
- 不要引入新的外部測試框架（僅使用 pytest + pytest-asyncio + pytest-cov + httpx）

---

## 📎 參考資料（References）

- ASP SPEC 模板：`.asp/templates/SPEC_Template.md`（`make test-filter` 要求）
- SPEC-004：REST API Routes（被測對象）
- SPEC-007：OODA Loop Engine（被測對象）
- SPEC-008：Execution Engine Clients（被測對象）
- ADR-003：OODA 引擎架構（服務分層設計）
- ADR-004：半自動化模式（風險閾值規則）
- Makefile：`test-backend`、`test-filter`、`coverage` targets

