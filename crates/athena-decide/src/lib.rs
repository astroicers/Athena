use async_trait::async_trait;
use athena_types::{OperationId, OrientRecommendation, Decision, AthenaError};
use athena_knowledge::constraint::OperationalConstraints;

#[async_trait]
pub trait DecidePhase: Send + Sync {
    async fn evaluate(
        &self,
        op_id: &OperationId,
        recommendation: &OrientRecommendation,
        constraints: &OperationalConstraints,
    ) -> Result<Decision, AthenaError>;
}
