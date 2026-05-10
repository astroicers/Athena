# [ADR-107]: Orphan Branch 策略

| 欄位 | 內容 |
|------|------|
| **狀態** | `Accepted` |
| **日期** | 2026-05-10 |
| **決策者** | Athena Team |

## 背景

Athena 2.0 是全新重寫，與 v1.x（main branch）沒有代碼繼承關係。需要決定如何管理版控隔離。

## 決策

使用 `git checkout --orphan athena-2.0` 建立 orphan branch。此 branch 與 `main` 完全隔離，沒有共同的 git history。v1.x 代碼保留在 `main`，2.0 開發完全在 `athena-2.0` 進行。

## 後果

- v1.x 生產環境不受影響
- 不會發生 merge conflict
- 無法直接 cherry-pick v1 commits（需手動移植）
