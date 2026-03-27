# SPEC-048：OPSEC Monitoring and Cross-Domain Penalty

> 結構完整的規格書讓 AI 零確認直接執行。

| 欄位 | 內容 |
|------|------|
| **規格 ID** | SPEC-048 |
| **關聯 ADR** | ADR-XXX（若有） |
| **估算複雜度** | 低 / 中 / 高 |
| **建議模型**（optional） | Haiku / Sonnet / Opus（省略時由 AI 依複雜度自行判斷） |
| **HITL 等級**（optional） | minimal / standard / strict（省略時沿用 `.ai_profile` 設定） |

---

## 🎯 目標（Goal）

> 一句話：這個功能解決什麼問題？對誰有價值？

---

## 📥 輸入規格（Inputs）

| 參數名稱 | 型別 | 來源 | 限制條件 |
|----------|------|------|----------|
| param_a | string | HTTP Body | 長度 1-255 |
| param_b | int | Query | 必須 > 0 |

---

## 📤 輸出規格（Expected Output）

**成功情境：**
```json
{
  "status": "ok",
  "data": {}
}
```

**失敗情境：**

| 錯誤類型 | HTTP Code | 處理方式 |
|----------|-----------|----------|
| 參數缺失 | 400 | 回傳缺失欄位名稱 |
| 未授權 | 401 | 導向登入 |

---

## 🔗 副作用與連動（Side Effects）

| 本功能的狀態變動 | 受影響的既有功能 | 預期行為 | 驗證方式 |
|-----------------|----------------|---------|----------|
| OPSEC score 即時更新 | Constraint Engine 約束計算 | OPSEC 分數低於閾值時觸發 hard_limit | test_constraint_engine 驗證閾值觸發 |
| Cross-domain penalty 寫入 | C5ISR domain health | 跨域懲罰降低相關 domain healthPct | test_opsec_monitor 驗證 penalty 傳播 |
| OPSEC event 記錄 | Dashboard time-series API | 事件可在時間軸查詢 | test_dashboard_api 驗證歷史查詢 |
| threat_level 變動 | War Room ConstraintBanner | 即時顯示威脅等級變化 | E2E sit-vuln-opsec 驗證 UI 更新 |

---

## ⚠️ 邊界條件（Edge Cases）

- Case 1：輸入為空時的行為
- Case 2：並發請求時的安全性
- Case 3：（依實際情境補充）

### 回退方案（Rollback Plan）

| 項目 | 內容 |
|------|------|
| **回退方式** | Alembic migration DOWN + revert commit |
| **不可逆評估** | 無不可逆部分；OPSEC event 歷史記錄可安全刪除 |
| **資料影響** | 回退後 OPSEC 分數欄位消失，Constraint Engine 恢復不含 OPSEC 約束的行為 |
| **依賴回退** | opsec_monitor service 停用；threat_level service 恢復預設值 |

---

## 🧪 測試矩陣（Test Matrix）

| ID | 類型 | 場景 | 輸入 | 預期結果 |
|----|------|------|------|----------|
| P1 | 正向 | OPSEC monitor 偵測高噪音行動 | action with noise_level=high 完成 | OPSEC score 下降，event 記錄寫入 |
| P2 | 正向 | Cross-domain penalty 傳播 | CYBER domain OPSEC violation | COMMS domain healthPct 受 penalty 降低 |
| P3 | 正向 | threat_level 計算正確 | 多個 domain degraded | threat_level 反映最嚴重域狀態 |
| N1 | 負向 | 無效 domain 名稱 | penalty target='INVALID' | 400 Bad Request 或靜默忽略 |
| N2 | 負向 | OPSEC score 不能低於 0 | 大量 penalty 累積 | score clamp 至 0，不產生負值 |
| B1 | 邊界 | 無行動時 OPSEC 不變 | 空 OODA cycle | OPSEC score 維持初始值 |
| B2 | 邊界 | 所有 domain 同時 critical | 六域 healthPct < 50 | Constraint Engine 產生所有 hard_limits |

---

## 🎬 驗收場景（Acceptance Scenarios）

```gherkin
Feature: OPSEC Monitoring 與 Cross-Domain Penalty

  Scenario: 高噪音行動觸發 OPSEC 分數下降與跨域懲罰
    Given operation 處於 OODA Act 階段
    And 當前 OPSEC score 為 85
    When 執行 noise_level="high" 的 technique
    Then OPSEC score 下降至少 10 點
    And 相關 domain 的 healthPct 受 cross-domain penalty 降低
    And opsec event 記錄寫入 event store

  Scenario: OPSEC 分數低於閾值觸發 Constraint Engine hard_limit
    Given OPSEC score 為 25（低於 CRITICAL 閾值）
    When Constraint Engine 執行 evaluate()
    Then hard_limits 包含 OPSEC 相關約束
    And War Room 顯示 ConstraintBanner 警告

  Scenario: 低噪音行動不影響 OPSEC 分數
    Given operation 處於 OODA Act 階段
    And 當前 OPSEC score 為 90
    When 執行 noise_level="low" 的 technique
    Then OPSEC score 不變或僅微幅下降（≤2 點）
```

---

## 🔗 追溯性（Traceability）

| 實作檔案 | 測試檔案 | 最後驗證日期 |
|----------|----------|-------------|
| `backend/app/services/opsec_monitor.py` | `backend/tests/test_opsec_monitor.py` | 2026-03-26 |
| `backend/app/models/opsec.py` | `backend/tests/test_opsec_api.py` | 2026-03-26 |
| `backend/app/routers/opsec.py` | `backend/tests/test_opsec_router.py` | 2026-03-26 |
| `backend/app/services/threat_level.py` | `backend/tests/test_opsec_monitor.py` | 2026-03-26 |
| `backend/app/services/constraint_engine.py` | `backend/tests/test_constraint_engine.py` | 2026-03-26 |
| `frontend/e2e/sit-vuln-opsec.spec.ts` | — (E2E) | 2026-03-26 |

---

## 📊 可觀測性（Observability）

| 指標名稱 | 類型 | 觸發條件 | 用途 |
|----------|------|----------|------|
| `opsec.score.updated` | Gauge | OPSEC score 變動時 | 即時監控 OPSEC 健康度 |
| `opsec.penalty.applied` | Counter | cross-domain penalty 觸發 | 追蹤跨域懲罰頻率 |
| `opsec.violation.detected` | Counter | 高噪音行動完成時 | 監控 OPSEC 違規次數 |
| `threat_level.changed` | Counter | threat_level 等級變更 | 追蹤威脅等級升降趨勢 |

---

## ✅ 驗收標準（Done When）

> 必須包含至少一項可驗證的測試條件。
> 提示：除了「功能正常運作」，也應列出「狀態變動後，依賴方即時反映」的驗收條件。

- [ ] `make test-filter FILTER=spec-000` 全數通過
- [ ] `make lint` 無 error
- [ ] 回應時間 < ____ms（留空則不限制）
- [ ] 副作用連動已驗證（見 Side Effects）
- [ ] 已更新 `docs/architecture.md`（若有架構變動）
- [ ] 已更新 `CHANGELOG.md`

---

## 🚫 禁止事項（Out of Scope）

- 不要修改：
- 不要引入新依賴：

---

## 📎 參考資料（References）

- 相關 ADR：
- 現有類似實作：
- 外部文件：

