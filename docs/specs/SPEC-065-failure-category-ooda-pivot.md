# SPEC-065：failure_category 枚舉與 ooda.pivot 決策流

| 欄位 | 內容 |
|------|------|
| **規格 ID** | SPEC-065 |
| **關聯 ADR** | ADR-046（Cross-Category Pivot）、ADR-005（OODA 架構） |
| **估算複雜度** | 低 |
| **建議模型** | Haiku |
| **HITL 等級** | standard |
| **狀態** | ✅ 已實作（補文件） |
| **完成日期** | 2026-05-02 |

---

## 🎯 目標

記錄 `technique_executions.failure_category` 枚舉的完整定義，以及 `ooda.pivot` WebSocket 事件的觸發條件與 payload 格式。這兩個機制是 SPEC-053（Orient-Driven Pivot）的執行層實作，但原始 SPEC-053 只描述了 Orient 的決策邏輯，未記錄 DB schema 枚舉與事件格式。

---

## 背景

當技術執行失敗時，`engine_router.py:_classify_failure()` 將錯誤訊息分類為標準化的 `failure_category` 字串，寫入 `technique_executions` 表。Orient Engine 在下一次 OODA 循環讀取這些 category，驅動 Rule #9（IA 耗盡後轉推 T1190）和 Rule #2（Dead Branch Pruning）。

當 Orient 決策為「auth_failure 後轉推 T1190」時，`ooda_controller.py:_detect_cross_category_pivot()` 偵測此模式並廣播 `ooda.pivot` 事件，供 War Room Timeline 顯示 Pivot Badge。

---

## 規格

### 1. failure_category 枚舉

| Category 值 | 說明 | 典型觸發錯誤訊息 |
|------------|------|----------------|
| `auth_failure` | 憑證被拒、登入失敗 | authentication failed, permission denied, login incorrect, access denied, invalid credentials |
| `service_unreachable` | 網路層阻擋 | connection refused, no route to host, connection timed out, host unreachable, no targetable services |
| `exploit_failed` | Exploit 模組執行但未取得 session | no session, exploit completed but no session was created |
| `privilege_insufficient` | 執行成功但權限不足 | operation not permitted, access denied（執行後）, insufficient privileges |
| `prerequisite_missing` | 上游 fact/憑證/Agent 不存在 | target not found, no valid credentials, agent not found |
| `tool_error` | MCP 工具 schema 錯誤 / 驗證失敗 | tool_not_found, validation_error, schema mismatch |
| `timeout` | 操作層級逾時 | timed out, deadline exceeded |
| `unknown` | 啟發式未匹配，安全 fallback | （其他所有情況） |

**分類邏輯**（`engine_router.py:_classify_failure`，行 216+）：
- 字串匹配使用 `lower()` 後子字串比對
- 順序優先：`auth_failure` > `service_unreachable` > `exploit_failed` > `privilege_insufficient` > `prerequisite_missing` > `tool_error` > `timeout` > `unknown`
- 同一錯誤可能觸發多個條件，以最先匹配為準

### 2. ooda.pivot 事件

**觸發條件**（`ooda_controller.py:_detect_cross_category_pivot`）：

```
目標 T 的最近失敗記錄 failure_category == "auth_failure"
  AND
當前決策 recommended_technique_id 屬於 {T1190, T1059.004, ...}（exploit/execution class）
  AND
失敗技術屬於 {T1110.*, T1078.*}（Initial Access credential class）
```

**Payload 格式**：

```json
{
  "iteration": 5,
  "from_technique": "T1110.001",
  "to_technique": "T1190",
  "reason": "auth_failure on SSH → exploit pivot (vsftpd 2.3.4 banner detected)",
  "target_id": "uuid",
  "confidence": 0.75
}
```

**WebSocket event name**：`ooda.pivot`

**War Room 顯示**：Timeline 在對應 iteration 顯示 `[AI Pivot Decision]` badge，`reason` 欄位顯示在 tooltip 中。

### 3. DB Schema（參考）

```sql
-- technique_executions 表的 failure_category 欄位
ALTER TABLE technique_executions
  ADD COLUMN failure_category TEXT
  CHECK (failure_category IN (
    'auth_failure', 'service_unreachable', 'exploit_failed',
    'privilege_insufficient', 'prerequisite_missing', 'tool_error',
    'timeout', 'unknown'
  ));
```

---

## 測試矩陣

| 場景 | 驗證方式 | 通過條件 |
|------|---------|---------|
| SSH 認證失敗 | 模擬 "authentication failed" | _classify_failure 回傳 "auth_failure" |
| 網路不通 | 模擬 "connection refused" | 回傳 "service_unreachable" |
| Exploit 無 session | 模擬 "no session was created" | 回傳 "exploit_failed" |
| Pivot 偵測 | T1110 auth_failure + 決策 T1190 | ooda.pivot 事件廣播 |
| Pivot 不觸發 | T1046 失敗 + 決策 T1087 | 無 ooda.pivot 事件 |

---

## 相依性

- `engine_router.py:_classify_failure()` — 分類邏輯
- `ooda_controller.py:_detect_cross_category_pivot()` — Pivot 偵測
- `ws_manager.py` — WebSocket 廣播
- `technique_executions` DB table — `failure_category` 欄位

---

## 驗收條件

- [ ] `_classify_failure()` 對 8 個 category 均有對應觸發關鍵字
- [ ] `_detect_cross_category_pivot()` 在 T1110 auth_failure + T1190 決策時廣播 `ooda.pivot`
- [ ] `ooda.pivot` payload 包含 from_technique, to_technique, reason, target_id, confidence
- [ ] War Room Timeline 顯示 Pivot Badge（前端 SPEC-053 相關實作）
