# [ADR-111]: sqlx 編譯期查詢檢查延至 rc 階段

| 欄位 | 內容 |
|------|------|
| **狀態** | `Accepted` |
| **日期** | 2026-05-10 |
| **決策者** | Athena Team |

## 背景

sqlx 支援編譯期 SQL 查詢驗證（`sqlx::query!` macro），但需要在編譯時連線到資料庫（`DATABASE_URL` 環境變數）。在 alpha/beta 階段這會造成 CI 複雜度。

## 決策

alpha 和 beta 階段使用 `sqlx::query()` 動態查詢（不在編譯期驗證）。在 2.0-rc 階段，啟用 `sqlx::query!` macro 並在 CI 中提供 postgres 服務，實現完整的編譯期 SQL 檢查。

## 後果

- **正面**：alpha/beta CI 更簡單
- **負面**：rc 之前 SQL 錯誤只能在執行期發現
- **追蹤**：ROADMAP task rc-01 負責開啟此功能
