use async_trait::async_trait;
use athena_types::{OperationId, Decision, OodaIterationId, ExecutionOutcome, AthenaError};

#[async_trait]
pub trait SwarmExecutor: Send + Sync {
    async fn execute_parallel(
        &self,
        op_id: &OperationId,
        decision: &Decision,
        iter_id: &OodaIterationId,
        max_concurrency: usize,
    ) -> Result<ExecutionOutcome, AthenaError>;
}
