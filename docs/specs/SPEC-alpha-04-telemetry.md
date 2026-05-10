# SPEC: alpha-04 — athena-telemetry

| 欄位 | 內容 |
|------|------|
| **狀態** | `Completed` |
| **ADR** | ADR-100 |
| **ROADMAP task** | alpha-04 |

## Goal

提供統一的 tracing 初始化函式，支援 JSON（生產）和 pretty（開發）兩種格式。

## Done When

- [x] `init()` — JSON 格式，讀取 `RUST_LOG` 環境變數
- [x] `init_pretty()` — 人類可讀格式，用於開發
- [ ] 無需單元測試（純 side-effect 初始化）

## Rollback Plan

無副作用，直接 revert。
