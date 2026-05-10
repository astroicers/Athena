# SPEC: alpha-05 — athena-events

| 欄位 | 內容 |
|------|------|
| **狀態** | `Completed` |
| **ADR** | ADR-106 |
| **ROADMAP task** | alpha-05 |

## Goal

實作型別化事件總線，取代 v1.x 的 ws_manager god-object。

## Done When

- [x] `AthenaEvent` enum 涵蓋所有操作生命週期事件
- [x] `EventBus::publish()` 發送事件
- [x] `EventBus::subscribe()` 返回 broadcast receiver
- [x] 容量設定為 1024（可在設定中調整）
- [ ] 單元測試：publish + subscribe 往返，lagged receiver 不 panic

## Rollback Plan

無生產流量依賴，直接 revert。
