# [ADR-112]: DecisionEngine Trait — 決策引擎可抽換

| 欄位 | 內容 |
|------|------|
| **狀態** | `Accepted` |
| **日期** | 2026-05-10 |
| **決策者** | Athena Team |

## 背景

v1.x OODA 是唯一硬編碼的決策模型，無法換成 Kill Chain、PDCA 或手動控制模式。

## 決策

定義頂層 `DecisionEngine` trait（位於 `athena-engine-ooda::DecisionEngine`）：

```rust
#[async_trait]
pub trait DecisionEngine: Send + Sync {
    fn name(&self) -> &'static str;
    async fn run_iteration(&self, op_id: &OperationId)
        -> Result<(OodaIterationId, ExecutionOutcome), AthenaError>;
    async fn abort(&self, op_id: &OperationId) -> Result<(), AthenaError>;
}
```

`athena-scheduler` 只持有 `Arc<dyn DecisionEngine>`，不知道是 OODA 還是其他引擎。2.0 預設實作為 `OodaEngine`，2.1 加入 `KillChainEngine`、`ManualEngine`。

## 關聯

- 取代：ADR-003（隱含）
