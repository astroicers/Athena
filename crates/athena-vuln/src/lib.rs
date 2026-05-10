use async_trait::async_trait;
use athena_types::AthenaError;
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CveEntry {
    pub cve_id: String,
    pub cvss_score: f32,
    pub description: String,
    pub published: chrono::DateTime<chrono::Utc>,
}

#[async_trait]
pub trait VulnerabilityManager: Send + Sync {
    async fn lookup_cve(&self, cve_id: &str) -> Result<CveEntry, AthenaError>;
    async fn search_cves(&self, keyword: &str, limit: usize) -> Result<Vec<CveEntry>, AthenaError>;
}
