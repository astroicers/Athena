# SPEC-062：BUG-frontend-enum-i18n-sync

| 欄位 | 內容 |
|------|------|
| **規格 ID** | SPEC-062 |
| **關聯 ADR** | 無（UI/配置修正，無架構決策） |
| **估算複雜度** | 中 |
| **建議模型** | Sonnet |
| **HITL 等級** | minimal |
| **狀態** | ✅ 完成 |
| **完成日期** | 2026-04-28 |

---

## 🎯 目標

後端 Python enum 新增值後，前端 TypeScript enum、i18n 翻譯、顏色 map、選單選項未同步更新，導致：
- Tool Registry category badge 一律灰色
- AddToolModal 只能選 6/14 個 category
- OODA failed/complete 無視覺
- Operations aborted/FA 無樣式
- War Room engine 選單缺項（winrm/mock/metasploit/mcp）

---

## 📤 輸出規格

| 元件 | 修復前 | 修復後 |
|------|--------|--------|
| ToolRegistryTable category badge | 全部灰色 | 各 category 顯示對應顏色 |
| AddToolModal category 選單 | 6 個選項 | 14 個選項 |
| OODAIndicator | failed/complete 無視覺 | failed=全紅、complete=全綠 |
| Operations status badge | aborted 無樣式 | 紅色 badge |
| Operations profile badge | FA 無樣式 | 紅色 badge |
| War Room engine 選單 | 3 個選項 | 7 個選項 |
| Console | MISSING_MESSAGE 錯誤 | 無 MISSING_MESSAGE |

---

## 🔗 追溯性

| 實作檔案 | 說明 | 最後驗證日期 |
|----------|------|-------------|
| `frontend/src/types/enums.ts` | 補齊 OODAPhase/ExecutionEngine/FactCategory/AutomationMode | 2026-04-28 |
| `frontend/messages/en.json` | 新增 OODA.failed/complete、WarRoom engine keys、Operations.profileFA | 2026-04-28 |
| `frontend/messages/zh-TW.json` | 同步 en.json，924 keys 一致 | 2026-04-28 |
| `frontend/src/components/tools/ToolRegistryTable.tsx` | CATEGORY_COLORS 鍵名修正為 14 個完整 category | 2026-04-28 |
| `frontend/src/components/tools/AddToolModal.tsx` | CATEGORY_OPTIONS 補齊至 14 個 | 2026-04-28 |
| `frontend/src/components/ooda/OODAIndicator.tsx` | 加入 FAILED/COMPLETE early-return 渲染 | 2026-04-28 |
| `frontend/src/app/operations/page.tsx` | 補 aborted/FA 樣式 | 2026-04-28 |
| `frontend/src/app/warroom/page.tsx` | 補 4 個 engine 選項 | 2026-04-28 |
| `frontend/src/components/warroom/OODATimelineBlock.tsx` | 補 FAILED/COMPLETE 至 PHASE_COLORS/PHASE_KEYS | 2026-04-28 |

---

## ✅ 驗收標準

- [x] Tool Registry category badge 各顯示對應顏色（非一律灰色）
- [x] AddToolModal 下拉有 14 個 category 可選
- [x] OODA failed/complete 狀態有對應視覺（全紅/全綠）
- [x] Operations aborted 顯示紅色 badge、FA profile 有樣式
- [x] War Room engine 選單有 winrm/mock/metasploit/mcp 選項
- [x] `make i18n-check` 通過（en.json 與 zh-TW.json 924 keys 一致）
- [x] Console 無 MISSING_MESSAGE 錯誤
- [ ] `tech-debt: test-pending`（enum 同步的單元測試待補）

---

## 🚫 禁止事項

- 不修改後端 Python enum 定義
- 不引入新依賴
