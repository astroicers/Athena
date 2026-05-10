# SPEC: alpha-02 — athena-types

| 欄位 | 內容 |
|------|------|
| **狀態** | `Completed` |
| **ADR** | ADR-100, ADR-109 |
| **ROADMAP task** | alpha-02 |

## Goal

定義所有零依賴的領域型別（newtype wrappers + enums + structs），確保整個系統有統一的型別詞彙。

## Done When

- [x] `OperationId(Uuid)` newtype，實作 Display、Hash、Eq
- [x] `TargetId(Uuid)` newtype
- [x] `OodaIterationId(Uuid)` newtype
- [x] `Fact`、`FactTrait`、`FactValue` 結構
- [x] `Decision`、`OrientRecommendation`、`ExecutionOutcome`、`ExecutionResult` 結構
- [x] `AthenaError` enum（thiserror）
- [x] `HealthStatus` enum
- [x] 所有型別實作 `Serialize`、`Deserialize`
- [ ] 單元測試：newtype 建立、Display、序列化往返

## Rollback Plan

純型別定義，無副作用。直接 revert。
