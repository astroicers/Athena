use async_trait::async_trait;
use athena_types::{OperationId, Decision, OodaIterationId, ExecutionOutcome, AthenaError};

#[async_trait]
pub trait ActPhase: Send + Sync {
    async fn execute(
        &self,
        op_id: &OperationId,
        decision: &Decision,
        iter_id: &OodaIterationId,
    ) -> Result<ExecutionOutcome, AthenaError>;
}
