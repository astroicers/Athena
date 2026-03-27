# SPEC-046：Mission Profile & Technique Noise/Risk Tagging

> 結構完整的規格書讓 AI 零確認直接執行。

| 欄位 | 內容 |
|------|------|
| **規格 ID** | SPEC-046 |
| **關聯 ADR** | ADR-039 |
| **估算複雜度** | 中 |

---

## 🎯 目標（Goal）

> 為每個 operation 新增任務類型（SR/CO/SP/FA），為每個 technique 標記 noise_level，
> 讓 Orient Engine 依據任務類型過濾超過噪音上限的技術。指揮官可選擇適合場景的
> 作戰模式，系統自動調整 OODA 參數。

---

## 📥 輸入規格（Inputs）

| 參數名稱 | 型別 | 來源 | 限制條件 |
|----------|------|------|----------|
| mission_profile | string | operations.mission_profile | SR / CO / SP / FA，預設 SP |
| noise_level | string | techniques.noise_level | low / medium / high，預設 medium |

---

## 📤 輸出規格（Expected Output）

**Mission Profile Config (from YAML):**
```json
{
  "name": "Standard Pentest",
  "max_noise": "high",
  "max_parallel": 5,
  "min_confidence": 0.5,
  "orient_max_options": 3,
  "noise_budget_10min": 50,
  "c5isr_thresholds": { ... }
}
```

**Orient Engine Filtering:**
- CO mode: techniques with noise_level=high excluded from candidates
- SR mode: only noise_level=low techniques allowed

---

## 🔗 副作用與連動（Side Effects）

| 本功能的狀態變動 | 受影響的既有功能 | 預期行為 | 驗證方式 |
|-----------------|----------------|---------|----------|
| operations.mission_profile 新欄位 | 建立 operation API | 可選 mission_profile 參數 | POST /operations 含 mission_profile 欄位 |
| techniques.noise_level 新欄位 | Orient 推薦清單 | 超過上限的技術被排除 | Orient Engine CO 模式不推薦 high-noise |
| Mission Profile YAML 設定 | Constraint Engine (Phase 2) | 提供閾值配置 | MissionProfileLoader.get_profile() 回傳正確值 |
| noise_risk_matrix.yaml 新增 | Seed data / technique 初始化 | 35+ techniques 標記 noise_level | make test 驗證 seed data 完整性 |

---

## ⚠️ 邊界條件（Edge Cases）

- Case 1：未指定 mission_profile → 預設 SP
- Case 2：technique 無 noise_level → 預設 medium
- Case 3：max_noise=all (FA) → 不做過濾

### 回退方案（Rollback Plan）

| 項目 | 內容 |
|------|------|
| **回退方式** | Alembic migration DOWN（DROP COLUMN IF EXISTS） |
| **不可逆評估** | 無不可逆部分，新增欄位皆有 DEFAULT 值 |
| **資料影響** | 回退後 mission_profile/noise_level 欄位消失，不影響核心功能 |
| **依賴回退** | 移除 mission_profiles.yaml 及 noise_risk_matrix.yaml；Orient Engine 恢復無過濾行為 |

---

## 🧪 測試矩陣（Test Matrix）

| ID | 類型 | 場景 | 輸入 | 預期結果 |
|----|------|------|------|----------|
| P1 | 正向 | MissionProfileLoader 載入 CO 設定 | `get_profile('CO')` | 回傳 max_noise='medium', max_parallel=3 |
| P2 | 正向 | Orient Engine CO 模式過濾 | CO mode + technique noise_level=high | 該 technique 不在推薦清單中 |
| P3 | 正向 | 建立 operation 含 mission_profile | POST /operations {mission_profile: 'SR'} | 201, mission_profile='SR' |
| N1 | 負向 | 無效 mission_profile | POST /operations {mission_profile: 'XX'} | 422 Validation Error |
| N2 | 負向 | noise_allowed 超限 | `noise_allowed('high', 'SR')` | False |
| B1 | 邊界 | 未指定 mission_profile | POST /operations {} | 預設 mission_profile='SP' |
| B2 | 邊界 | technique 無 noise_level | seed technique without noise_level | 預設 noise_level='medium' |
| B3 | 邊界 | FA 模式不過濾 | FA mode + technique noise_level=high | technique 仍在推薦清單中 |

---

## 🎬 驗收場景（Acceptance Scenarios）

```gherkin
Feature: Mission Profile 任務類型與 Technique Noise/Risk 標記

  Scenario: 指揮官以 Covert 模式建立 operation 並驗證 Orient 過濾
    Given 系統已載入 mission_profiles.yaml 含 SR/CO/SP/FA 四種設定
    And 存在 technique "nmap-syn-scan" with noise_level "high"
    When 指揮官建立 operation with mission_profile "CO"
    Then operation.mission_profile 為 "CO"
    And Orient Engine 推薦清單不包含 "nmap-syn-scan"

  Scenario: 未指定 mission_profile 時使用預設值
    When 指揮官建立 operation 未指定 mission_profile
    Then operation.mission_profile 預設為 "SP"
    And Orient Engine 使用 SP 設定的 max_noise 閾值過濾

  Scenario: FA 模式允許所有噪音等級的技術
    Given 指揮官建立 operation with mission_profile "FA"
    When Orient Engine 執行推薦
    Then 所有 noise_level 的 technique 均可出現在推薦清單中
```

---

## 🔗 追溯性（Traceability）

| 實作檔案 | 測試檔案 | 最後驗證日期 |
|----------|----------|-------------|
| `backend/app/services/mission_profile_loader.py` | `backend/tests/test_mission_profile.py` | 2026-03-26 |
| `backend/app/services/orient_engine.py` | `backend/tests/test_constraint_engine.py` | 2026-03-26 |
| `backend/app/models/operation.py` | `backend/tests/test_operations_router.py` | 2026-03-26 |
| `backend/app/data/noise_risk_matrix.yaml` | `backend/tests/test_mission_profile.py` | 2026-03-26 |
| `backend/app/data/mission_profiles.yaml` | `backend/tests/test_mission_profile.py` | 2026-03-26 |
| `backend/app/routers/operations.py` | `backend/tests/test_operations_router.py` | 2026-03-26 |
| `backend/app/database/seed.py` | — | 2026-03-26 |

---

## 📊 可觀測性（Observability）

| 指標名稱 | 類型 | 觸發條件 | 用途 |
|----------|------|----------|------|
| `operation.mission_profile.selected` | Counter | operation 建立時 | 追蹤各 mission profile 使用頻率 |
| `orient.technique.filtered_by_noise` | Counter | Orient Engine 過濾 technique 時 | 監控噪音過濾命中率 |
| `orient.noise_allowed.check` | Histogram | noise_allowed() 呼叫 | 量測每輪過濾延遲 |

---

## ✅ 驗收標準（Done When）

- [ ] `operations` 表有 `mission_profile` 欄位（VARCHAR(2), DEFAULT 'SP'）
- [ ] `techniques` 表有 `noise_level` 欄位（VARCHAR(10), DEFAULT 'medium'）
- [ ] `mission_profiles.yaml` 定義 SR/CO/SP/FA 四種設定
- [ ] `MissionProfileLoader.get_profile('CO')` 回傳正確設定
- [ ] `noise_allowed('medium', 'CO')` → True, `noise_allowed('high', 'CO')` → False
- [ ] Seed data 中 35+ techniques 皆有 noise_level 標記
- [ ] Orient Engine 在 CO 模式下不推薦 noise:high 技術
- [ ] 建立 operation 時可指定 mission_profile
- [ ] `make test` 通過，無回歸

---

## 🚫 禁止事項（Out of Scope）

- 不修改 C5ISR 計算邏輯（Phase 2）
- 不實作 OPSEC 監控（Phase 3）
- 不修改 Decide/ACT 邏輯（Phase 2）

---

## 📎 參考資料（References）

- ADR-039: Mission Profile 任務類型與 Technique Noise/Risk 標記制
- Plan: `/home/ubuntu/.claude/plans/logical-munching-finch.md` Phase 1

