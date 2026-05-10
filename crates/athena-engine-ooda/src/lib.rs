pub mod engine;
pub mod state;

pub use engine::OodaEngine;
pub use state::OodaState;

use async_trait::async_trait;
use athena_types::{OperationId, OodaIterationId, ExecutionOutcome, AthenaError};

// Top-level hot-swap contract: the entire decision loop is swappable
#[async_trait]
pub trait DecisionEngine: Send + Sync {
    fn name(&self) -> &'static str;
    async fn run_iteration(
        &self,
        op_id: &OperationId,
    ) -> Result<(OodaIterationId, ExecutionOutcome), AthenaError>;
    async fn abort(&self, op_id: &OperationId) -> Result<(), AthenaError>;
}
