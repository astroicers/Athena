use async_trait::async_trait;
use std::sync::Arc;
use athena_types::{OperationId, OrientRecommendation, Decision, AthenaError, PhaseContext};
use athena_knowledge::constraint::OperationalConstraints;
use athena_policy::PolicyEngine;
use serde_json::json;

#[async_trait]
pub trait DecidePhase: Send + Sync {
    async fn evaluate(
        &self,
        op_id: &OperationId,
        recommendation: &OrientRecommendation,
        constraints: &OperationalConstraints,
    ) -> Result<Decision, AthenaError>;

    /// PhaseContext pipeline entry point.
    /// Checks extensions for operator_override_techniques first; falls back to evaluate().
    async fn run(&self, mut ctx: PhaseContext, constraints: &OperationalConstraints) -> Result<PhaseContext, AthenaError> {
        // Operator override: bypass risk gate, use operator-specified techniques directly
        if let Some(techs) = ctx.operator_techniques() {
            let reason = ctx.extensions
                .get("operator_override_reason")
                .and_then(|v| v.as_str())
                .unwrap_or("operator override")
                .to_owned();
            ctx.decision = Some(Decision {
                approved: true,
                techniques: techs,
                reason: format!("operator override: {reason}"),
                risk_accepted: 1.0,
            });
            return Ok(ctx);
        }
        let rec = ctx.require_recommendation()?;
        let decision = self.evaluate(&ctx.op_id, rec, constraints).await?;
        ctx.decision = Some(decision);
        Ok(ctx)
    }
}

pub struct RiskMatrixDecider {
    policy: Option<Arc<dyn PolicyEngine>>,
}

impl RiskMatrixDecider {
    pub fn new() -> Self { Self { policy: None } }

    pub fn with_policy(mut self, policy: Arc<dyn PolicyEngine>) -> Self {
        self.policy = Some(policy);
        self
    }
}

impl Default for RiskMatrixDecider {
    fn default() -> Self { Self::new() }
}

#[async_trait]
impl DecidePhase for RiskMatrixDecider {
    async fn evaluate(
        &self,
        _op_id: &OperationId,
        recommendation: &OrientRecommendation,
        constraints: &OperationalConstraints,
    ) -> Result<Decision, AthenaError> {
        // Block techniques explicitly denied
        let approved_techniques: Vec<String> = recommendation.recommended_techniques
            .iter()
            .filter(|t| !constraints.denied_techniques.contains(t))
            .filter(|t| {
                // If allowed_techniques is non-empty, only allow listed ones
                constraints.allowed_techniques.is_empty()
                    || constraints.allowed_techniques.contains(t)
            })
            .cloned()
            .collect();

        // Check if risk threshold requires human approval
        let approval_required = constraints.require_approval_above_risk
            .map(|threshold| recommendation.risk_score > threshold)
            .unwrap_or(false);

        if approval_required {
            return Ok(Decision {
                approved: false,
                techniques: vec![],
                reason: format!(
                    "Risk score {:.2} exceeds threshold {:.2} — human approval required",
                    recommendation.risk_score,
                    constraints.require_approval_above_risk.unwrap_or(0.8)
                ),
                risk_accepted: recommendation.risk_score,
            });
        }

        if approved_techniques.is_empty() {
            return Ok(Decision {
                approved: false,
                techniques: vec![],
                reason: "All recommended techniques are blocked by operational constraints".into(),
                risk_accepted: recommendation.risk_score,
            });
        }

        // Run RoE policy check on each approved technique; drop any that are denied
        let policy_cleared: Vec<String> = if let Some(pe) = &self.policy {
            let mut cleared = Vec::new();
            for technique in &approved_techniques {
                let ctx = json!({
                    "technique": technique,
                    "noise_level": (recommendation.risk_score * 10.0) as u8,
                });
                let pd = pe.evaluate(technique, &ctx).await
                    .unwrap_or_else(|_| athena_policy::PolicyDecision { allowed: true, reason: String::new() });
                if pd.allowed {
                    cleared.push(technique.clone());
                }
            }
            cleared
        } else {
            approved_techniques
        };

        if policy_cleared.is_empty() {
            return Ok(Decision {
                approved: false,
                techniques: vec![],
                reason: "All techniques denied by RoE policy".into(),
                risk_accepted: recommendation.risk_score,
            });
        }

        Ok(Decision {
            approved: true,
            techniques: policy_cleared.clone(),
            reason: format!(
                "Approved {} technique(s) at risk score {:.2}",
                policy_cleared.len(),
                recommendation.risk_score
            ),
            risk_accepted: recommendation.risk_score,
        })
    }
}

/// Bypasses risk evaluation entirely — operator explicitly specifies techniques.
/// Intended for red team scenarios where the operator knows exactly what to run
/// and has already accepted the risk. Every use is recorded via risk_accepted=1.0
/// so audit logs show a deliberate override, not an error.
pub struct OperatorDirectDecider {
    techniques: Vec<String>,
    reason: String,
}

impl OperatorDirectDecider {
    pub fn new(techniques: Vec<String>, reason: impl Into<String>) -> Self {
        Self { techniques, reason: reason.into() }
    }
}

#[async_trait]
impl DecidePhase for OperatorDirectDecider {
    async fn evaluate(
        &self,
        _op_id: &OperationId,
        _recommendation: &OrientRecommendation,
        _constraints: &OperationalConstraints,
    ) -> Result<Decision, AthenaError> {
        Ok(Decision {
            approved: true,
            techniques: self.techniques.clone(),
            reason: format!("operator override: {}", self.reason),
            risk_accepted: 1.0,
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn rec(techniques: &[&str], risk: f32) -> OrientRecommendation {
        OrientRecommendation {
            summary: "test".into(),
            recommended_techniques: techniques.iter().map(|s| s.to_string()).collect(),
            risk_score: risk,
            rationale: "test rationale".into(),
        }
    }

    #[tokio::test]
    async fn approves_low_risk_techniques() {
        let decider = RiskMatrixDecider::new();
        let op_id = OperationId::new();
        let constraints = OperationalConstraints::default(); // threshold 0.8
        let result = decider.evaluate(&op_id, &rec(&["T1046"], 0.3), &constraints).await.unwrap();
        assert!(result.approved);
        assert_eq!(result.techniques, vec!["T1046"]);
    }

    #[tokio::test]
    async fn blocks_high_risk_above_threshold() {
        let decider = RiskMatrixDecider::new();
        let op_id = OperationId::new();
        let constraints = OperationalConstraints::default();
        let result = decider.evaluate(&op_id, &rec(&["T1078"], 0.9), &constraints).await.unwrap();
        assert!(!result.approved);
        assert!(result.reason.contains("human approval required"));
    }

    #[tokio::test]
    async fn filters_denied_techniques() {
        let decider = RiskMatrixDecider::new();
        let op_id = OperationId::new();
        let mut constraints = OperationalConstraints::default();
        constraints.denied_techniques = vec!["T1059".into()];
        let result = decider.evaluate(
            &op_id,
            &rec(&["T1046", "T1059"], 0.4),
            &constraints,
        ).await.unwrap();
        assert!(result.approved);
        assert!(!result.techniques.contains(&"T1059".to_string()));
        assert!(result.techniques.contains(&"T1046".to_string()));
    }

    #[tokio::test]
    async fn blocks_when_all_techniques_denied() {
        let decider = RiskMatrixDecider::new();
        let op_id = OperationId::new();
        let mut constraints = OperationalConstraints::default();
        constraints.denied_techniques = vec!["T1046".into()];
        let result = decider.evaluate(&op_id, &rec(&["T1046"], 0.2), &constraints).await.unwrap();
        assert!(!result.approved);
        assert!(result.reason.contains("blocked by operational constraints"));
    }

    #[tokio::test]
    async fn respects_allowed_techniques_whitelist() {
        let decider = RiskMatrixDecider::new();
        let op_id = OperationId::new();
        let mut constraints = OperationalConstraints::default();
        constraints.allowed_techniques = vec!["T1046".into()];
        let result = decider.evaluate(
            &op_id,
            &rec(&["T1046", "T1078"], 0.4),
            &constraints,
        ).await.unwrap();
        assert!(result.approved);
        assert_eq!(result.techniques, vec!["T1046"]);
    }

    #[tokio::test]
    async fn roe_policy_blocks_denied_technique() {
        use athena_policy::{RoePolicy, RoePolicyEngine};
        let policy = RoePolicy {
            name: "test".into(),
            default_deny: false,
            allowed_techniques: vec![],
            denied_techniques: vec!["T1059".into()],
            allowed_targets: vec![],
            max_noise_level: 10,
        };
        let decider = RiskMatrixDecider::new()
            .with_policy(Arc::new(RoePolicyEngine::new(policy)));
        let op_id = OperationId::new();
        let constraints = OperationalConstraints::default();
        let result = decider.evaluate(
            &op_id,
            &rec(&["T1059", "T1046"], 0.3),
            &constraints,
        ).await.unwrap();
        assert!(result.approved);
        assert!(!result.techniques.contains(&"T1059".to_string()));
        assert!(result.techniques.contains(&"T1046".to_string()));
    }

    #[tokio::test]
    async fn roe_policy_default_deny_blocks_unlisted() {
        use athena_policy::{RoePolicy, RoePolicyEngine};
        let policy = RoePolicy {
            name: "strict".into(),
            default_deny: true,
            allowed_techniques: vec!["T1046".into()],
            denied_techniques: vec![],
            allowed_targets: vec![],
            max_noise_level: 10,
        };
        let decider = RiskMatrixDecider::new()
            .with_policy(Arc::new(RoePolicyEngine::new(policy)));
        let op_id = OperationId::new();
        let constraints = OperationalConstraints::default();
        let result = decider.evaluate(
            &op_id,
            &rec(&["T1046", "T1078"], 0.3),
            &constraints,
        ).await.unwrap();
        assert!(result.approved);
        assert_eq!(result.techniques, vec!["T1046"]);
    }
}
