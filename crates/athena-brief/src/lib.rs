use async_trait::async_trait;
use athena_types::{OperationId, AthenaError};

#[async_trait]
pub trait BriefGenerator: Send + Sync {
    async fn generate(&self, op_id: &OperationId) -> Result<String, AthenaError>;
}
