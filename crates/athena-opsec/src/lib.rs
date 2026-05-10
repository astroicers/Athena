use async_trait::async_trait;
use athena_types::{OperationId, AthenaError};
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OpsecStatus {
    pub noise_level: u8,
    pub threat_level: ThreatLevel,
    pub remaining_budget: i32,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum ThreatLevel {
    Green,
    Yellow,
    Orange,
    Red,
}

#[async_trait]
pub trait OpsecMonitor: Send + Sync {
    async fn status(&self, op_id: &OperationId) -> Result<OpsecStatus, AthenaError>;
    async fn consume_budget(&self, op_id: &OperationId, cost: i32) -> Result<(), AthenaError>;
}
