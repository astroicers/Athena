use async_trait::async_trait;
use athena_types::AthenaError;
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PolicyDecision {
    pub allowed: bool,
    pub reason: String,
}

#[async_trait]
pub trait PolicyEngine: Send + Sync {
    async fn evaluate(&self, action: &str, context: &serde_json::Value) -> Result<PolicyDecision, AthenaError>;
}
