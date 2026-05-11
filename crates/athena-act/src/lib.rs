pub mod router;

use async_trait::async_trait;
use athena_types::{OperationId, Decision, OodaIterationId, ExecutionOutcome, AthenaError, PhaseContext};

#[async_trait]
pub trait ActPhase: Send + Sync {
    async fn execute(
        &self,
        op_id: &OperationId,
        decision: &Decision,
        iter_id: &OodaIterationId,
    ) -> Result<ExecutionOutcome, AthenaError>;

    /// PhaseContext pipeline entry point. Default impl calls execute().
    async fn run(&self, mut ctx: PhaseContext) -> Result<PhaseContext, AthenaError> {
        let decision = ctx.require_decision()?.clone();
        let outcome = self.execute(&ctx.op_id, &decision, &ctx.iter_id).await?;
        ctx.outcome = Some(outcome);
        Ok(ctx)
    }
}

pub use router::ActRouter;
