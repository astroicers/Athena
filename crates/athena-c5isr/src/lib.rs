use async_trait::async_trait;
use athena_types::{OperationId, AthenaError};
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct C5isrStatus {
    pub command: f32,
    pub control: f32,
    pub communications: f32,
    pub computers: f32,
    pub intelligence: f32,
    pub surveillance: f32,
    pub overall: f32,
}

#[async_trait]
pub trait C5isrMapper: Send + Sync {
    async fn assess(&self, op_id: &OperationId) -> Result<C5isrStatus, AthenaError>;
}
