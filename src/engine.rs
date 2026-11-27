// SPDX-License-Identifier: Apache-2.0
use async_trait::async_trait;
use crate::{OperationId, OodaIterationId, ExecutionOutcome, AthenaError, PhaseContext};

/// Hot-swap contract: the entire decision loop is swappable as a unit (ADR-119).
/// Moved from athena-engine-ooda to athena-types so dependents (athena-orchestrator, etc.)
/// only need to import the trait, not the full engine crate.
#[async_trait]
pub trait DecisionEngine: Send + Sync {
    fn name(&self) -> &'static str;

    /// Run one OODA iteration with no external context injection.
    async fn run_iteration(
        &self,
        op_id: &OperationId,
    ) -> Result<(OodaIterationId, ExecutionOutcome), AthenaError>;

    /// Run one OODA iteration with a caller-supplied PhaseContext.
    /// Used by TaskAgent (ADR-132) to inject task-scoped constraints
    /// (allowed techniques, target scope) without modifying the engine internals.
    /// Default implementation ignores ctx and delegates to run_iteration.
    async fn run_with_context(
        &self,
        op_id: &OperationId,
        _ctx: PhaseContext,
    ) -> Result<(OodaIterationId, ExecutionOutcome), AthenaError> {
        self.run_iteration(op_id).await
    }

    async fn abort(&self, op_id: &OperationId) -> Result<(), AthenaError>;
}
