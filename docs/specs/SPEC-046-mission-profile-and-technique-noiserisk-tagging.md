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

| 本功能的狀態變動 | 受影響的既有功能 | 預期行為 |
|-----------------|----------------|---------|
| operations.mission_profile 新欄位 | 建立 operation API | 可選 mission_profile 參數 |
| techniques.noise_level 新欄位 | Orient 推薦清單 | 超過上限的技術被排除 |
| Mission Profile YAML 設定 | Constraint Engine (Phase 2) | 提供閾值配置 |

---

## ⚠️ 邊界條件（Edge Cases）

- Case 1：未指定 mission_profile → 預設 SP
- Case 2：technique 無 noise_level → 預設 medium
- Case 3：max_noise=all (FA) → 不做過濾

### 回退方案（Rollback Plan）

- **回退方式**：Alembic migration DOWN（DROP COLUMN IF EXISTS）
- **不可逆評估**：無不可逆部分，新增欄位皆有 DEFAULT 值
- **資料影響**：回退後 mission_profile/noise_level 欄位消失，不影響核心功能

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
