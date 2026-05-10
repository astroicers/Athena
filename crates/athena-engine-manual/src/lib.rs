// Stub — implementation deferred to Athena 2.1
use async_trait::async_trait;
use athena_types::{OperationId, OodaIterationId, ExecutionOutcome, AthenaError};

#[async_trait]
pub trait DecisionEngine: Send + Sync {
    fn name(&self) -> &'static str;
    async fn run_iteration(&self, op_id: &OperationId) -> Result<(OodaIterationId, ExecutionOutcome), AthenaError>;
    async fn abort(&self, op_id: &OperationId) -> Result<(), AthenaError>;
}
