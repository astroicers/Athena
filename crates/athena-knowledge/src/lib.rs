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

#[cfg(test)]
mod tests {
    use super::*;
    use crate::constraint::OperationalConstraints;

    #[test]
    fn load_yaml_dir_nonexistent_returns_empty() {
        let result: Result<Vec<TechniqueEntry>, _> = load_yaml_dir("/tmp/nonexistent_athena_dir_xyz");
        assert!(result.is_ok());
        assert!(result.unwrap().is_empty());
    }

    #[test]
    fn load_yaml_dir_parses_valid_yaml() {
        use std::fs;
        let dir = tempfile::tempdir().unwrap();
        let yaml = r#"
id: T1046
name: Network Service Scanning
description: Scan for open ports
category: discovery
mcp_tool: nmap
parameters: []
prerequisites: []
risk_level: low
"#;
        fs::write(dir.path().join("technique.yaml"), yaml).unwrap();
        let entries: Vec<TechniqueEntry> = load_yaml_dir(dir.path()).unwrap();
        assert_eq!(entries.len(), 1);
        assert_eq!(entries[0].id, "T1046");
        assert_eq!(entries[0].risk_level, RiskLevel::Low);
    }

    #[test]
    fn operational_constraints_defaults() {
        let c = OperationalConstraints::default();
        assert_eq!(c.max_noise_level, 5);
        assert!(c.allowed_techniques.is_empty());
        assert_eq!(c.require_approval_above_risk, Some(0.8));
    }

    #[test]
    fn risk_level_serde() {
        let rl = RiskLevel::Critical;
        let s = serde_json::to_string(&rl).unwrap();
        assert_eq!(s, "\"critical\"");
        let back: RiskLevel = serde_json::from_str(&s).unwrap();
        assert_eq!(back, RiskLevel::Critical);
    }
}
