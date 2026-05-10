use async_trait::async_trait;
use athena_types::AthenaError;
use serde::{Deserialize, Serialize};
use std::collections::HashSet;

// ── public types ──────────────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PolicyDecision {
    pub allowed: bool,
    pub reason: String,
}

/// Declarative Rules-of-Engagement (RoE) policy.
///
/// ```yaml
/// name: engagement-alpha
/// default_deny: true
/// allowed_techniques:
///   - T1595
///   - T1046
/// denied_techniques:
///   - T1059.001
/// allowed_targets:
///   - "192.168.1.0/24"
/// max_noise_level: 3
/// ```
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RoePolicy {
    pub name: String,
    #[serde(default)]
    pub default_deny: bool,
    #[serde(default)]
    pub allowed_techniques: Vec<String>,
    #[serde(default)]
    pub denied_techniques: Vec<String>,
    #[serde(default)]
    pub allowed_targets: Vec<String>,
    #[serde(default = "default_noise")]
    pub max_noise_level: u8,
}

fn default_noise() -> u8 { 5 }

impl Default for RoePolicy {
    fn default() -> Self {
        Self {
            name: "default".into(),
            default_deny: false,
            allowed_techniques: vec![],
            denied_techniques: vec![],
            allowed_targets: vec![],
            max_noise_level: 5,
        }
    }
}

// ── trait ─────────────────────────────────────────────────────────────────────

#[async_trait]
pub trait PolicyEngine: Send + Sync {
    async fn evaluate(&self, action: &str, context: &serde_json::Value) -> Result<PolicyDecision, AthenaError>;
}

// ── RoE policy engine ────────────────────────────────────────────────────────

pub struct RoePolicyEngine {
    policy: RoePolicy,
    denied_set: HashSet<String>,
    allowed_set: HashSet<String>,
}

impl RoePolicyEngine {
    pub fn new(policy: RoePolicy) -> Self {
        let denied_set = policy.denied_techniques.iter().cloned().collect();
        let allowed_set = policy.allowed_techniques.iter().cloned().collect();
        Self { policy, denied_set, allowed_set }
    }

    pub fn from_yaml(yaml: &str) -> Result<Self, AthenaError> {
        let policy: RoePolicy = serde_yaml::from_str(yaml)
            .map_err(|e| AthenaError::ConfigError(format!("policy yaml: {e}")))?;
        Ok(Self::new(policy))
    }

    fn check_noise(&self, context: &serde_json::Value) -> Option<PolicyDecision> {
        let noise = context.get("noise_level")
            .and_then(|v| v.as_u64())
            .unwrap_or(0) as u8;
        if noise > self.policy.max_noise_level {
            Some(PolicyDecision {
                allowed: false,
                reason: format!("noise level {noise} exceeds policy max {}", self.policy.max_noise_level),
            })
        } else {
            None
        }
    }
}

#[async_trait]
impl PolicyEngine for RoePolicyEngine {
    async fn evaluate(&self, action: &str, context: &serde_json::Value) -> Result<PolicyDecision, AthenaError> {
        // 1. Explicit deny list always wins
        if self.denied_set.contains(action) {
            return Ok(PolicyDecision {
                allowed: false,
                reason: format!("technique '{action}' is explicitly denied by RoE"),
            });
        }

        // 2. Noise budget check
        if let Some(noise_block) = self.check_noise(context) {
            return Ok(noise_block);
        }

        // 3. Default-deny mode: must be on allowed list
        if self.policy.default_deny {
            if self.allowed_set.contains(action) {
                return Ok(PolicyDecision { allowed: true, reason: "explicitly allowed".into() });
            }
            return Ok(PolicyDecision {
                allowed: false,
                reason: format!("default-deny: '{action}' not in allowed_techniques"),
            });
        }

        // 4. Default-allow: any technique not denied is permitted
        Ok(PolicyDecision { allowed: true, reason: "permitted by default-allow policy".into() })
    }
}

// ── allow-all pass-through for dev / testing ─────────────────────────────────

pub struct AllowAllPolicy;

#[async_trait]
impl PolicyEngine for AllowAllPolicy {
    async fn evaluate(&self, _action: &str, _context: &serde_json::Value) -> Result<PolicyDecision, AthenaError> {
        Ok(PolicyDecision { allowed: true, reason: "allow-all policy".into() })
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    fn strict_policy() -> RoePolicyEngine {
        RoePolicyEngine::new(RoePolicy {
            name: "strict".into(),
            default_deny: true,
            allowed_techniques: vec!["T1595".into(), "T1046".into()],
            denied_techniques: vec!["T1059.001".into()],
            allowed_targets: vec![],
            max_noise_level: 3,
        })
    }

    #[tokio::test]
    async fn denied_technique_blocked() {
        let engine = strict_policy();
        let dec = engine.evaluate("T1059.001", &json!({})).await.unwrap();
        assert!(!dec.allowed);
        assert!(dec.reason.contains("explicitly denied"));
    }

    #[tokio::test]
    async fn allowed_technique_passes() {
        let engine = strict_policy();
        let dec = engine.evaluate("T1595", &json!({})).await.unwrap();
        assert!(dec.allowed);
    }

    #[tokio::test]
    async fn unknown_technique_blocked_under_default_deny() {
        let engine = strict_policy();
        let dec = engine.evaluate("T1190", &json!({})).await.unwrap();
        assert!(!dec.allowed);
        assert!(dec.reason.contains("default-deny"));
    }

    #[tokio::test]
    async fn noise_over_limit_blocked() {
        let engine = strict_policy();
        let dec = engine.evaluate("T1595", &json!({ "noise_level": 10 })).await.unwrap();
        assert!(!dec.allowed);
        assert!(dec.reason.contains("noise level"));
    }

    #[tokio::test]
    async fn default_allow_permits_unknown() {
        let engine = RoePolicyEngine::new(RoePolicy {
            name: "permissive".into(),
            default_deny: false,
            denied_techniques: vec![],
            ..Default::default()
        });
        let dec = engine.evaluate("T1190", &json!({})).await.unwrap();
        assert!(dec.allowed);
    }

    #[tokio::test]
    async fn yaml_roundtrip() {
        let yaml = r#"
name: test-roe
default_deny: true
allowed_techniques: ["T1595", "T1046"]
denied_techniques: ["T1059.001"]
max_noise_level: 4
"#;
        let engine = RoePolicyEngine::from_yaml(yaml).unwrap();
        let dec = engine.evaluate("T1595", &json!({})).await.unwrap();
        assert!(dec.allowed);
    }

    #[tokio::test]
    async fn allow_all_always_permits() {
        let engine = AllowAllPolicy;
        let dec = engine.evaluate("anything", &json!({})).await.unwrap();
        assert!(dec.allowed);
    }
}
