# [ADR-108]: 建構子注入，禁止全域單例

| 欄位 | 內容 |
|------|------|
| **狀態** | `Accepted` |
| **日期** | 2026-05-10 |
| **決策者** | Athena Team |

## 背景

v1.x 使用大量全域 singleton（`global_config`、`global_db_pool`、`ws_manager`），導致測試困難和隱性依賴。

## 決策

所有依賴透過建構子參數（`Arc<dyn Trait>`）注入。禁止使用 `lazy_static!`、`once_cell::sync::Lazy` 或任何形式的全域可變狀態。唯一的例外是 `athena-workspace/src/main.rs` 中的 DI wiring，這是明確的「組合根」（composition root）。

## 成功指標

| 指標 | 目標 |
|------|------|
| 全域 static mut | 0 |
| lazy_static 使用數 | 0（測試外） |
| 單元測試可以 mock 所有依賴 | 100% |
