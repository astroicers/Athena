use async_trait::async_trait;
use athena_types::{Fact, FactTrait, OperationId, AthenaError};

#[async_trait]
pub trait FactRepository: Send + Sync {
    async fn insert(&self, fact: Fact) -> Result<(), AthenaError>;
    async fn list(&self, op_id: &OperationId) -> Result<Vec<Fact>, AthenaError>;
    async fn exists(&self, op_id: &OperationId, trait_name: &FactTrait, value: &str) -> Result<bool, AthenaError>;
}
