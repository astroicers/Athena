# SPEC: alpha-01 — Cargo Workspace 骨架

| 欄位 | 內容 |
|------|------|
| **狀態** | `Completed` |
| **ADR** | ADR-100, ADR-101 |
| **ROADMAP task** | alpha-01 |

## Goal

建立 Cargo workspace，定義所有 41 個 crate 的 Cargo.toml 和 lib.rs stub，確保 `cargo build --workspace` 通過。

## Done When

- [x] `Cargo.toml` workspace manifest 包含所有 41 個 crate
- [x] 每個 crate 有 `Cargo.toml` 和 `src/lib.rs`
- [x] `cargo build --workspace` 通過（無 error）
- [x] 所有核心 trait 介面已定義（DecisionEngine, ObservePhase, OrientPhase, DecidePhase, ActPhase, LlmClient, McpClient, FactRepository, ExecutionEngine）

## Rollback Plan

此為骨架建立，無生產流量，直接 `git revert` 即可。
