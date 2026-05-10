use async_trait::async_trait;
use athena_types::{Target, Fact, OperationId, AthenaError};

#[async_trait]
pub trait ReconEngine: Send + Sync {
    async fn recon(&self, op_id: &OperationId, target: &Target) -> Result<Vec<Fact>, AthenaError>;
}
