# SPEC: beta1-08 — athena-engine-ooda

| 欄位 | 內容 |
|------|------|
| **狀態** | `Pending` |
| **ADR** | ADR-112, ADR-109 |
| **ROADMAP task** | beta1-08 |

## Goal

實作完整 OODA 狀態機，串聯四個階段 trait，驗證整個循環在 mock 模式下可完整執行。

## Done When

- [ ] `DecisionEngine` trait（`run_iteration()`, `abort()`）
- [ ] `OodaEngine` 串聯 Observe → Orient → Decide → Act
- [ ] `OodaState` enum 追蹤當前狀態
- [ ] `MOCK_LLM=true` 環境變數下使用 `MockLlmClient`
- [ ] 整合測試：以所有 mock 依賴跑完整一次 OODA 循環，不 panic，回傳 ExecutionOutcome

## Rollback Plan

無生產流量，直接 revert。
