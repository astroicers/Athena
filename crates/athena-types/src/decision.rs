use serde::{Deserialize, Serialize};
use uuid::Uuid;

#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct OodaIterationId(pub Uuid);

impl OodaIterationId {
    pub fn new() -> Self { Self(Uuid::new_v4()) }
}

impl Default for OodaIterationId {
    fn default() -> Self { Self::new() }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OrientRecommendation {
    pub summary: String,
    pub recommended_techniques: Vec<String>,
    pub risk_score: f32,
    pub rationale: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Decision {
    pub approved: bool,
    pub techniques: Vec<String>,
    pub reason: String,
    pub risk_accepted: f32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TechniqueParams {
    pub technique_id: String,
    pub params: serde_json::Value,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExecutionResult {
    pub technique_id: String,
    pub success: bool,
    pub output: String,
    pub new_facts: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExecutionOutcome {
    pub results: Vec<ExecutionResult>,
    pub facts_collected: usize,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum HealthStatus {
    Healthy,
    Degraded,
    Unhealthy,
}
