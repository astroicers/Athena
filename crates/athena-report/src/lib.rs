use async_trait::async_trait;
use athena_types::{OperationId, AthenaError};
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PentestReport {
    pub op_id: String,
    pub title: String,
    pub executive_summary: String,
    pub findings: Vec<Finding>,
    pub generated_at: chrono::DateTime<chrono::Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Finding {
    pub id: String,
    pub title: String,
    pub severity: String,
    pub description: String,
    pub remediation: String,
}

#[async_trait]
pub trait ReportGenerator: Send + Sync {
    async fn generate(&self, op_id: &OperationId) -> Result<PentestReport, AthenaError>;
    async fn to_markdown(&self, report: &PentestReport) -> String;
    async fn to_json(&self, report: &PentestReport) -> serde_json::Value;
}
