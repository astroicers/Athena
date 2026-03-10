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

> 列出本功能的狀態變動對系統其他部分的影響。
> 若無跨模組影響，填「無」並說明理由。

| 本功能的狀態變動 | 受影響的既有功能 | 預期行為 |
|-----------------|----------------|---------|
| （例：用戶餘額扣減） | （例：帳戶總覽頁面）| （例：餘額即時更新，無需重新載入） |

---

## ⚠️ 邊界條件（Edge Cases）

- Case 1：輸入為空時的行為
- Case 2：並發請求時的安全性
- Case 3：（依實際情境補充）

### 回退方案（Rollback Plan）

> 若此功能部署後出現問題，如何安全回退？

- **回退方式**：（revert commit / feature flag / migration DOWN / 手動步驟）
- **不可逆評估**：此變更是否有不可逆部分？（如：DB column DROP、外部通知已發送）
  - 若有不可逆部分，說明替代的風險緩解措施
- **資料影響**：回退後使用者資料是否受影響？

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
