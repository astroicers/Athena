# SPEC: alpha-08 — athena-api stub

| 欄位 | 內容 |
|------|------|
| **狀態** | `Completed` |
| **ADR** | ADR-102, ADR-103 |
| **ROADMAP task** | alpha-08 |

## Goal

建立最小可用的 axum HTTP server，只暴露 `GET /api/health`，驗證整個 DI 鏈可以啟動。

## Done When

- [x] `GET /api/health` 回傳 `{"status":"ok","version":"2.0.0-alpha.1","service":"athena"}`
- [x] `AppState` 持有 `Arc<EventBus>`
- [x] `create_router(state)` 工廠函式
- [ ] 整合測試：`curl localhost:58000/api/health` 回傳 200

## Rollback Plan

停止服務即可，無持久化副作用。
