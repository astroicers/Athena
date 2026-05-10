use async_trait::async_trait;
use athena_types::{OperationId, AthenaError};
use athena_knowledge::constraint::OperationalConstraints;

#[async_trait]
pub trait ConfigEngine: Send + Sync {
    async fn get_constraints(&self, op_id: &OperationId) -> Result<OperationalConstraints, AthenaError>;
}
