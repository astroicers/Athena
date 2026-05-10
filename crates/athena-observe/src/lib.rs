use async_trait::async_trait;
use athena_types::{Fact, OperationId, AthenaError};

#[async_trait]
pub trait ObservePhase: Send + Sync {
    async fn collect(&self, op_id: &OperationId) -> Result<Vec<Fact>, AthenaError>;
    async fn summarize(&self, op_id: &OperationId) -> Result<String, AthenaError>;
}
