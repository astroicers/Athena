# [ADR-043]: i18n Full Coverage with Locale Switcher

| 欄位 | 內容 |
|------|------|
| **狀態** | `Accepted` |
| **日期** | 2026-03-22 |
| **決策者** | 架構師 / 前端負責人 |

---

## 背景（Context）

War Room 重建（ADR-042）引入了 29 個 hardcoded 英文字串，導致前端出現中英文混雜的問題。整體前端缺乏統一的 i18n 策略：

1. **中英混雜**：部分元件使用中文、部分使用英文，無統一規則
2. **Hardcoded 字串**：War Room timeline 元件直接在 .tsx 中寫死文字，無法切換語言
3. **無語言切換機制**：使用者無法在 UI 中切換語言
4. **無 i18n 驗證工具**：缺少自動化工具確保翻譯鍵值的一致性

---

## 評估選項（Options Considered）

### 選項 A：手動翻譯 + 無切換機制

- **優點**：改動最小，直接將 hardcoded 字串改為中文
- **缺點**：無法支援英文使用者；未來新增字串仍會 hardcode
- **風險**：問題反覆出現

### 選項 B：next-intl 全覆蓋 + LocaleSwitcher

- **優點**：
  - next-intl 為 Next.js 生態的標準 i18n 方案
  - Cookie-based locale persistence，無 URL 污染
  - `useTranslations()` hook 強制所有 UI 文字經過翻譯系統
  - 自動化 schema 測試可驗證 zh-TW.json / en.json 鍵值對稱
- **缺點**：
  - 所有現有元件需遷移至 `useTranslations()` 呼叫
  - 需維護兩份翻譯檔案
- **風險**：翻譯檔案不同步（透過 CI 測試緩解）

---

## 決策（Decision）

我們選擇 **選項 B：next-intl 全覆蓋 + LocaleSwitcher**，因為：

1. Athena 需要同時支援 zh-TW（主要）和 en（備用）兩種語言
2. `useTranslations()` 從源頭防止 hardcoded 字串
3. 自動化測試確保翻譯鍵值一致性

### 具體規則

| 規則 | 說明 |
|------|------|
| **所有 UI 文字** | 必須使用 `useTranslations()` — 禁止 .tsx 中出現 hardcoded 字串 |
| **主要語言** | zh-TW（繁體中文） |
| **備用語言** | en（英文） |
| **語言切換** | LocaleSwitcher 元件位於全域 header（PageHeader trailing slot） |
| **Locale 持久化** | Cookie-based（`NEXT_LOCALE`），有效期 1 年 |
| **翻譯鍵值結構** | namespace.keyName 格式（例：`WarRoom.autoMode`） |
| **鍵值對稱驗證** | `i18n-schema.test.ts` — zh-TW.json 和 en.json 必須擁有完全相同的 key 結構 |
| **CI 驗證** | `make i18n-check` 在 CI 中執行，不通過則阻止合併 |

### 翻譯覆蓋範圍

- 27 個 War Room timeline 元件翻譯鍵
- Nav / Sidebar 導航項目
- 通用 UI 狀態（loading、error、empty state）
- 所有新增元件必須同步新增翻譯

---

## 後果（Consequences）

**正面影響：**
- 消除中英混雜問題，UI 語言一致
- 使用者可在 header 一鍵切換語言
- `i18n-schema.test.ts` 自動偵測遺漏的翻譯鍵
- `make i18n-check` 在 CI 中防止翻譯鍵不同步

**負面影響 / 技術債：**
- 所有元件必須使用 `useTranslations()` 而非直接寫字串，增加少量程式碼
- 需同時維護 zh-TW.json 和 en.json 兩份翻譯檔案
- 新增 UI 元件時需同步更新兩份翻譯檔案（開發流程新增一步）

**後續追蹤：**
- [x] LocaleSwitcher 元件實作完成
- [x] War Room timeline 翻譯鍵新增（27 keys）
- [x] `i18n-schema.test.ts` 驗證翻譯鍵對稱性
- [x] `make i18n-check` 整合
- [ ] CI pipeline 加入 `make i18n-check` 檢查
- [ ] 現有元件全面遷移至 `useTranslations()`（持續進行）

---

## 成功指標（Success Metrics）

| 指標 | 目標值 | 驗證方式 | 檢查時間 |
|------|--------|----------|----------|
| Hardcoded 字串數量 | 0 | `grep -rn` 掃描 .tsx 中的中英文字串 | 每次 PR |
| i18n 鍵值對稱率 | 100% | `i18n-schema.test.ts` | 每次 PR |
| `make i18n-check` | 通過 | CI check | 每次 PR |
| 語言切換可用性 | header 可見且可點擊 | E2E test | 每次部署 |

---

## 關聯（Relations）

- 取代：無
- 被取代：無
- 參考：ADR-041（Adopt Deep Gemstone v3 Design System）、ADR-042（War Room Vertical Campaign Timeline）、ADR-009（Frontend Component Architecture）
