# SPEC: alpha-09 — athena-workspace binary

| 欄位 | 內容 |
|------|------|
| **狀態** | `Completed` |
| **ADR** | ADR-108 |
| **ROADMAP task** | alpha-09 |

## Goal

實作主程式入口，作為唯一的「組合根」（composition root）——在此處進行所有 `Arc<dyn Trait>` 的 DI wiring。

## Done When

- [x] `main.rs` 載入 `AthenaConfig`
- [x] 初始化 `EventBus`
- [x] 建立 `AppState` 並注入所有依賴
- [x] 呼叫 `create_router()` 並在設定的端口上啟動 axum server
- [ ] `cargo run` 啟動後 `GET /api/health` 回傳 200

## Rollback Plan

二進位工具，無資料庫操作，直接停止即可。
