use async_trait::async_trait;
use athena_types::{OperationId, OrientRecommendation, AthenaError};

#[async_trait]
pub trait OrientPhase: Send + Sync {
    async fn analyze(
        &self,
        op_id: &OperationId,
        observation_summary: &str,
        attack_graph_summary: &str,
    ) -> Result<OrientRecommendation, AthenaError>;
}
