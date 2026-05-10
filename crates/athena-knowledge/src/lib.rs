pub mod technique;
pub mod constraint;

use serde::{Deserialize, Serialize};
use thiserror::Error;
use std::path::Path;

#[derive(Debug, Error)]
pub enum KnowledgeError {
    #[error("io error: {0}")]
    Io(#[from] std::io::Error),
    #[error("yaml parse error: {0}")]
    Parse(#[from] serde_yaml::Error),
    #[error("not found: {0}")]
    NotFound(String),
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TechniqueEntry {
    pub id: String,
    pub name: String,
    pub description: String,
    pub category: String,
    pub mcp_tool: Option<String>,
    pub parameters: Vec<TechniqueParam>,
    pub prerequisites: Vec<String>,
    pub risk_level: RiskLevel,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TechniqueParam {
    pub name: String,
    pub required: bool,
    pub description: String,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum RiskLevel {
    Low,
    Medium,
    High,
    Critical,
}

pub fn load_yaml_dir<T: for<'de> Deserialize<'de>>(
    dir: impl AsRef<Path>,
) -> Result<Vec<T>, KnowledgeError> {
    let dir = dir.as_ref();
    let mut results = Vec::new();
    if !dir.exists() {
        return Ok(results);
    }
    for entry in std::fs::read_dir(dir)? {
        let entry = entry?;
        let path = entry.path();
        if path.extension().and_then(|e| e.to_str()) == Some("yaml") {
            let content = std::fs::read_to_string(&path)?;
            let parsed: T = serde_yaml::from_str(&content)?;
            results.push(parsed);
        }
    }
    Ok(results)
}
