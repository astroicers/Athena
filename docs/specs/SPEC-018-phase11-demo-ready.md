# SPEC-018：Phase 11 Demo 就緒 — UI/UX 精修 + OODA 資料完整性

> 傘形 SPEC，覆蓋 Phase 11 所有新增/修改模組。已實作完成，補建 SPEC 以符合 ASP Pre-Implementation Gate。

| 欄位 | 內容 |
|------|------|
| **規格 ID** | SPEC-018 |
| **關聯 ADR** | 無架構影響（功能性 side-effects 補齊 + UX 基礎設施） |
| **估算複雜度** | 高（跨 8 個前端 + 3 個後端檔案） |
| **建議模型** | Opus |
| **HITL 等級** | standard |
| **tech-debt** | ~~`test-pending`~~ 已清償（24 tests） |

---

## 🎯 目標（Goal）

> 讓 Demo 流程順暢：指揮官觸發 OODA → 即時看到所有頁面更新（Mission Steps 進度、Live Log、C5ISR 變化、Target 入侵狀態）→ 匯出報告。三層修復：(1) 後端 OODA side-effects 補齊 (2) 前端即時更新機制 (3) 全局 UX 基礎設施。

---

## 📥 輸入規格（Inputs）

| 參數名稱 | 型別 | 來源 | 限制條件 |
|----------|------|------|----------|
| `operation_id` | str | URL path | 已存在的作戰 ID |
| OODA trigger 結果 | dict | `ooda_controller.trigger_cycle()` | 各階段 side-effects |
| WebSocket 事件 | JSON | `ws_manager.broadcast()` | 8 種事件類型 |

---

## 📤 預期輸出（Expected Output）

### 後端
1. OODA 觸發後 `mission_steps` 從 QUEUED → running → completed 逐步推進
2. 每個 OODA 階段寫入 `log_entries`（至少 4 條/迭代）
3. Act 成功時 `targets.is_compromised = 1`、`agents.status = 'alive'`
4. `operations` 計數器（`techniques_executed`、`active_agents`）即時更新
5. `GET /operations/{op_id}/report` 回傳 10 段落 JSON
6. `POST /operations/{op_id}/reset` 重置全部作戰資料

### 前端
7. 四頁面首次載入顯示 PageLoading 掃描動畫
8. API 錯誤透過 Toast 通知（非靜默吞掉）
9. C5ISR / Navigator / Planner 加入 WebSocket 即時監聽
10. Planner 頁面有 EXPORT 按鈕觸發報告下載

---

## ✅ 驗收條件（Done When）

- [x] `curl /api/operations/op-0001/ooda/trigger` 後 mission_steps 非全部 QUEUED
- [x] `curl /api/operations/op-0001/logs` 回傳 ≥ 4 筆 log entries
- [x] `curl /api/operations/op-0001/targets` 有 `is_compromised: true` 的 target
- [x] `curl /api/operations/op-0001/report` 回傳含 10 個 key 的 JSON
- [x] `POST /api/operations/op-0001/reset` 後所有資料歸零
- [x] 四頁面有 Loading 狀態
- [x] 後端掛掉時前端顯示 Toast 錯誤
- [x] Planner 觸發 OODA 後 C5ISR 頁面即時更新
- [x] `tech-debt: test-pending` — 5 個新模組單元測試已補齊：
  - `backend/tests/test_reports.py`（5 tests）
  - `backend/tests/test_admin.py`（5 tests）
  - `frontend/src/contexts/__tests__/ToastContext.test.tsx`（4 tests）
  - `frontend/src/components/ui/__tests__/Toast.test.tsx`（3 tests）
  - `frontend/src/components/ui/__tests__/PageLoading.test.tsx`（2 tests）
  - `frontend/src/components/ooda/__tests__/RecommendationPanel.test.tsx`（5 tests）

---

## 🔲 邊界條件（Edge Cases）

| 條件 | 預期行為 |
|------|----------|
| OODA 觸發但 mock 執行失敗 | `_write_log` 寫入 warning，mission_step 不推進到 completed |
| Reset 後再 OODA | iteration_number 從 1 重新計算 |
| 連續快速 OODA | 受 `if operation.ooda_state != "idle"` 保護，回傳 409 |
| 後端完全掛掉 | 前端 Toast 顯示連線錯誤，不再靜默空白 |
| WebSocket 斷線 | `useWebSocket` hook 自動重連（已有 reconnect 機制）|

---

## 📁 影響檔案

### 新建
- `backend/app/routers/reports.py`
- `backend/app/routers/admin.py`
- `frontend/src/contexts/ToastContext.tsx`
- `frontend/src/components/ui/Toast.tsx`
- `frontend/src/components/ui/PageLoading.tsx`
- `frontend/src/components/ooda/RecommendationPanel.tsx`

### 修改
- `backend/app/services/ooda_controller.py`
- `backend/app/main.py`
- `frontend/src/app/c5isr/page.tsx`
- `frontend/src/app/navigator/page.tsx`
- `frontend/src/app/planner/page.tsx`
- `frontend/src/app/monitor/page.tsx`
- `frontend/src/components/layout/client-shell.tsx`
- `frontend/src/lib/api.ts`

---

## 副作用與連動（Side Effects）

| 副作用 | 觸發條件 | 影響模組 | 驗證方式 |
|--------|----------|----------|----------|
| OODA side-effects 寫入 mission_steps / log_entries | `ooda_controller.trigger_cycle()` 執行 | `backend/app/services/ooda_controller.py`、DB mission_steps / log_entries 表 | `test_spec_007_ooda_services.py` + `test_e2e_ooda_loop.py` |
| WebSocket 廣播 8 種事件 | OODA 各階段完成時 | 前端 4 頁面（c5isr / navigator / planner / monitor） | `frontend/e2e/full-workflow.spec.ts` 驗證即時更新 |
| Toast 全域注入 | `ToastContext.tsx` 包裹 `client-shell.tsx` | 前端所有頁面的錯誤處理 | `frontend/src/contexts/__tests__/ToastContext.test.tsx` |
| Report / Admin router 新增 | `main.py` 註冊新 router | `backend/app/main.py` 路由表 | `test_reports.py` + `test_admin.py` |

---

## Rollback Plan

| 回滾步驟 | 資料影響 | 回滾驗證 | 回滾已測試 |
|----------|----------|----------|------------|
| 1. 還原 `ooda_controller.py` side-effects 寫入邏輯 | mission_steps 不再自動推進；log_entries 不再自動寫入 | `make test` 通過；OODA trigger 仍可呼叫（無 side-effect） | 是（遷移前行為） |
| 2. 移除 Toast / PageLoading 元件 | 前端錯誤回到靜默模式 | 前端 `npm run build` 成功；頁面可載入 | 是 |
| 3. 移除 reports / admin router | `/report` `/reset` API 不可用 | `make test` 通過；既有路由不受影響 | 是 |

---

## 測試矩陣（Test Matrix）

| ID | 類型 | 場景 | 輸入 | 預期結果 | 場景參照 |
|----|------|------|------|----------|----------|
| P1 | 正向 | OODA 觸發後 mission_steps 推進 | `POST /api/operations/op-0001/ooda/trigger` | mission_steps 含 running/completed 狀態 | S1 |
| P2 | 正向 | 報告匯出含 10 個 key | `GET /api/operations/op-0001/report` | 回傳 JSON 含 10 個頂層 key | S1 |
| N1 | 負向 | 後端掛掉時前端顯示 Toast | API server 不可達 | Toast 顯示連線錯誤訊息 | S2 |
| N2 | 負向 | OODA 非 idle 時重複觸發 | 連續兩次 POST trigger | 第二次回傳 409 Conflict | S2 |
| B1 | 邊界 | Reset 後再觸發 OODA | `POST /reset` → `POST /ooda/trigger` | iteration_number 從 1 重新計算 | S3 |
| B2 | 邊界 | WebSocket 斷線後重連 | 前端 ws 斷線 | `useWebSocket` 自動重連；重連後收到最新事件 | S3 |

---

## 驗收場景（Acceptance Scenarios）

```gherkin
Feature: Phase 11 Demo 就緒 — OODA 資料完整性與 UX

  Background:
    Given 後端服務已啟動
    And 作戰 "op-0001" 已建立且包含至少一個 target

  Scenario: S1 — OODA 觸發後 mission_steps 與 log_entries 更新
    Given 作戰 "op-0001" 的 ooda_state 為 "idle"
    When 發送 POST /api/operations/op-0001/ooda/trigger
    Then 回傳 200 且 ooda_state 不為 "idle"
    And GET /api/operations/op-0001/logs 回傳至少 4 筆 log entries
    And mission_steps 中至少一筆狀態為 "completed"

  Scenario: S2 — 後端不可達時前端顯示 Toast 錯誤通知
    Given 前端頁面已載入
    When 後端服務中斷
    And 前端發起 API 請求
    Then 畫面顯示 Toast 錯誤通知
    And Toast 包含連線錯誤相關訊息

  Scenario: S3 — Reset 後 OODA 迭代從 1 重新計算
    Given 作戰 "op-0001" 已執行過至少一輪 OODA
    When 發送 POST /api/operations/op-0001/reset
    And 發送 POST /api/operations/op-0001/ooda/trigger
    Then OODA iteration_number 為 1
    And mission_steps 狀態全部重置
```

---

## 追溯性（Traceability）

| 項目 | 路徑 / 識別碼 | 狀態 |
|------|---------------|------|
| 規格文件 | `docs/specs/SPEC-018-phase11-demo-ready.md` | Done |
| OODA Controller | `backend/app/services/ooda_controller.py` | 已修改 |
| Reports Router | `backend/app/routers/reports.py` | 已新建 |
| Admin Router | `backend/app/routers/admin.py` | 已新建 |
| Toast Context | `frontend/src/contexts/ToastContext.tsx` | 已新建 |
| Toast 元件 | `frontend/src/components/ui/Toast.tsx` | 已新建 |
| PageLoading 元件 | `frontend/src/components/ui/PageLoading.tsx` | 已新建 |
| RecommendationPanel | `frontend/src/components/ooda/RecommendationPanel.tsx` | 已新建 |
| C5ISR 頁面 | `frontend/src/app/c5isr/page.tsx` | 已修改（WebSocket） |
| 後端測試 — Reports | `backend/tests/test_reports.py` | 5 tests 通過 |
| 後端測試 — Admin | `backend/tests/test_admin.py` | 5 tests 通過 |
| 前端測試 — Toast | `frontend/src/contexts/__tests__/ToastContext.test.tsx` | 4 tests 通過 |
| 前端測試 — Toast UI | `frontend/src/components/ui/__tests__/Toast.test.tsx` | 3 tests 通過 |
| 前端測試 — PageLoading | `frontend/src/components/ui/__tests__/PageLoading.test.tsx` | 2 tests 通過 |
| 前端測試 — RecommendationPanel | `frontend/src/components/ooda/__tests__/RecommendationPanel.test.tsx` | 5 tests 通過 |
| E2E 測試 | `frontend/e2e/full-workflow.spec.ts` | 通過 |
| 更新日期 | 2026-03-26 | — |

---

## 可觀測性（Observability）

| 面向 | 內容 |
|------|------|
| **指標（Metrics）** | `ooda.trigger.duration_seconds`（histogram）、`ooda.side_effect.write_total`（counter, label: table=mission_steps/log_entries/targets）、`report.export.total`（counter）、`ws.broadcast.total`（counter, label: event_type） |
| **日誌（Logs）** | OODA trigger 開始/完成（含 iteration_number）、side-effect 寫入筆數、Reset 執行紀錄、WebSocket 廣播事件類型與數量 |
| **告警（Alerts）** | OODA trigger 超過 30 秒未完成、side-effect 寫入失敗（DB error）、WebSocket 廣播失敗率 > 5% |
| **故障偵測（Fault Detection）** | mission_steps 全部 QUEUED 超過 60 秒（side-effect 未觸發）、log_entries 為空（寫入靜默失敗）、Report API 回傳不足 10 個 key |
