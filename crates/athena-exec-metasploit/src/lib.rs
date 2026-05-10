// Stub — implementation deferred to Athena 2.1
use async_trait::async_trait;
use athena_types::{Target, TechniqueParams, ExecutionResult, HealthStatus, AthenaError};

#[async_trait]
pub trait ExecutionEngine: Send + Sync {
    fn name(&self) -> &'static str;
    async fn execute(&self, technique_id: &str, target: &Target, params: &TechniqueParams) -> Result<ExecutionResult, AthenaError>;
    async fn health_check(&self) -> HealthStatus;
}
