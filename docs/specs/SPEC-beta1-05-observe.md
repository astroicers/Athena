# SPEC: beta1-05 — athena-observe

| 欄位 | 內容 |
|------|------|
| **狀態** | `Pending` |
| **ADR** | ADR-101, ADR-109 |
| **ROADMAP task** | beta1-05 |

## Goal

實作 OODA 觀察階段，從 FactRepository 收集事實並生成摘要字串供 orient 使用。

## Done When

- [ ] `ObservePhase` trait（`collect()`, `summarize()`）
- [ ] `DefaultObserver` — 從 `FactRepository` 讀取所有 facts，生成 Markdown 摘要
- [ ] `MockObserver` — 回傳固定 facts，用於測試
- [ ] 單元測試：MockObserver 的 collect + summarize

## Rollback Plan

無副作用，直接 revert。
