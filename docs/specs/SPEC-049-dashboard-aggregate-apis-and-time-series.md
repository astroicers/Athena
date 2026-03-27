# SPEC-049：Dashboard Aggregate APIs and Time-Series

> 結構完整的規格書讓 AI 零確認直接執行。

| 欄位 | 內容 |
|------|------|
| **規格 ID** | SPEC-049 |
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
| 新增 aggregate API endpoints | War Room Dashboard 前端 | 前端 polling 改用 aggregate endpoint 減少請求數 | test_dashboard_api 驗證回傳格式 |
| C5ISR history time-series 寫入 | C5ISR Health Grid 時間序列圖表 | 支援 15min/1h/24h 區間查詢 | test_dashboard_router 驗證 time range 過濾 |
| Dashboard cache layer | 所有 dashboard 消費端 | 首次請求後快取，15 秒 TTL | test_dashboard_api 驗證 cache hit/miss |

---

## ⚠️ 邊界條件（Edge Cases）

- Case 1：輸入為空時的行為
- Case 2：並發請求時的安全性
- Case 3：（依實際情境補充）

### 回退方案（Rollback Plan）

| 項目 | 內容 |
|------|------|
| **回退方式** | Revert commit + Alembic migration DOWN（若有 c5isr_status_history 表） |
| **不可逆評估** | 無不可逆部分；time-series 歷史資料可安全丟棄 |
| **資料影響** | 回退後 aggregate API 不可用，前端降級為個別 API 呼叫 |
| **依賴回退** | Dashboard cache layer 移除；前端 polling 恢復原始 endpoints |

---

## 🧪 測試矩陣（Test Matrix）

| ID | 類型 | 場景 | 輸入 | 預期結果 |
|----|------|------|------|----------|
| P1 | 正向 | Aggregate dashboard API 回傳完整資料 | GET /operations/{id}/dashboard | 包含 OODA + C5ISR + OPSEC 聚合資料 |
| P2 | 正向 | C5ISR time-series 查詢 | GET /operations/{id}/c5isr/history?range=1h | 回傳 1 小時內的 domain health 時間序列 |
| P3 | 正向 | Dashboard cache 命中 | 連續兩次相同 GET 請求 | 第二次從 cache 回傳，延遲 < 5ms |
| N1 | 負向 | 無效 operation ID | GET /operations/99999/dashboard | 404 Not Found |
| N2 | 負向 | 無效 time range | GET /c5isr/history?range=invalid | 422 Validation Error |
| B1 | 邊界 | 無 OODA iteration 的 operation | GET /operations/{new_id}/dashboard | 回傳空 OODA 區塊，C5ISR 為初始值 |
| B2 | 邊界 | 大量 time-series 記錄（1000+） | GET /c5isr/history?range=24h | 回傳分頁或截斷結果，回應時間 < 500ms |

---

## 🎬 驗收場景（Acceptance Scenarios）

```gherkin
Feature: Dashboard Aggregate APIs 與 Time-Series 查詢

  Scenario: 指揮官查看 operation dashboard 聚合資料
    Given operation "alpha-strike" 已執行 3 輪 OODA cycle
    And C5ISR 六域皆有歷史記錄
    When 指揮官呼叫 GET /operations/{id}/dashboard
    Then 回傳包含 currentPhase, iterationCount, c5isrDomains, opsecScore
    And 回應時間低於 200ms

  Scenario: C5ISR 歷史時間序列支援區間過濾
    Given operation 已運行 2 小時，C5ISR 每 15 秒記錄一次
    When 呼叫 GET /operations/{id}/c5isr/history?range=1h
    Then 僅回傳最近 1 小時的時間序列資料
    And 每筆記錄包含 timestamp, domain, healthPct, status

  Scenario: 新建 operation 的 dashboard 回傳空初始狀態
    Given operation 剛建立，尚無 OODA iteration
    When 呼叫 GET /operations/{id}/dashboard
    Then OODA 區塊為空（currentPhase=null, iterationCount=0）
    And C5ISR 六域 healthPct 皆為 100
```

---

## 🔗 追溯性（Traceability）

| 實作檔案 | 測試檔案 | 最後驗證日期 |
|----------|----------|-------------|
| `backend/app/routers/dashboard.py` | `backend/tests/test_dashboard_router.py` | 2026-03-26 |
| `backend/app/routers/dashboard.py` | `backend/tests/test_dashboard_api.py` | 2026-03-26 |
| `backend/app/services/c5isr_mapper.py` | `backend/tests/test_c5isr_router.py` | 2026-03-26 |
| `backend/app/models/schemas/c5isr.py` | `backend/tests/test_c5isr_domain_reports.py` | 2026-03-26 |
| `frontend/src/hooks/useSituationData.ts` | `frontend/e2e/sit-warroom-tabs.spec.ts` | 2026-03-26 |

---

## 📊 可觀測性（Observability）

| 指標名稱 | 類型 | 觸發條件 | 用途 |
|----------|------|----------|------|
| `dashboard.aggregate.latency` | Histogram | aggregate API 呼叫 | 監控聚合查詢效能 |
| `dashboard.cache.hit_ratio` | Gauge | cache hit/miss 事件 | 追蹤 cache 效率 |
| `c5isr.history.query_duration` | Histogram | time-series 查詢 | 監控歷史查詢延遲 |
| `c5isr.history.record_count` | Gauge | 每次查詢回傳筆數 | 監控資料量成長趨勢 |

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

