// SPDX-License-Identifier: Apache-2.0
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

impl std::fmt::Display for OodaIterationId {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}", self.0)
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ToolCall {
    pub tool:      String,
    pub container: String,
    pub rationale: String,
    /// Additional parameters beyond target IP (e.g. exploit_module, scan_type).
    /// Populated by Orient LLM; merged into mcp.call() params by Act router.
    #[serde(default)]
    pub params:    serde_json::Value,
}

fn default_risk_score() -> f32 { 0.5 }

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OrientRecommendation {
    pub summary: String,
    #[serde(default)]
    pub recommended_techniques: Vec<String>,
    #[serde(default = "default_risk_score")]
    pub risk_score: f32,
    #[serde(default)]
    pub rationale: String,
    #[serde(default)]
    pub tool_calls: Vec<ToolCall>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Decision {
    pub approved: bool,
    pub techniques: Vec<String>,
    pub reason: String,
    pub risk_accepted: f32,
}
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExecutionResult {
    pub technique_id: String,
    pub success: bool,
    pub output: String,
    pub new_facts: Vec<String>,
}

#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct ExecutionOutcome {
    pub results: Vec<ExecutionResult>,
    pub facts_collected: usize,
}
