use async_trait::async_trait;
use athena_types::{OperationId, AthenaError};
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AttackPath {
    pub nodes: Vec<AttackNode>,
    pub total_risk: f32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AttackNode {
    pub technique_id: String,
    pub prerequisite: Option<String>,
    pub risk: f32,
}

#[async_trait]
pub trait AttackGraphEngine: Send + Sync {
    async fn compute_paths(&self, op_id: &OperationId, entry_points: Vec<String>) -> Result<Vec<AttackPath>, AthenaError>;
    async fn to_summary(&self, paths: &[AttackPath]) -> String;
}
