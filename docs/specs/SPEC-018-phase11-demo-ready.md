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
