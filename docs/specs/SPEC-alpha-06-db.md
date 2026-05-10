# SPEC: alpha-06 — athena-db

| 欄位 | 內容 |
|------|------|
| **狀態** | `In Progress` |
| **ADR** | ADR-111 |
| **ROADMAP task** | alpha-06 |

## Goal

建立 sqlx PostgreSQL 連線池和初始 schema migration，讓所有業務 crate 透過 `DatabasePool` 存取資料庫。

## Done When

- [x] `DatabasePool::connect(url)` 建立 PgPool
- [x] `0001_initial.sql` migration：operations、targets、facts、ooda_iterations 四張表
- [ ] `run_migrations()` 在 `main.rs` 啟動時執行
- [ ] 連線到 k3s postgres（192.168.0.27:30543）驗證通過
- [ ] 單元測試：pool 建立（需要 test postgres）

## Rollback Plan

Drop migration：`cargo sqlx database drop`。
