use async_trait::async_trait;
use athena_types::{OperationId, OrientRecommendation, Decision, AthenaError};
use athena_knowledge::constraint::OperationalConstraints;

#[async_trait]
pub trait DecidePhase: Send + Sync {
    async fn evaluate(
        &self,
        op_id: &OperationId,
        recommendation: &OrientRecommendation,
        constraints: &OperationalConstraints,
    ) -> Result<Decision, AthenaError>;
}

pub struct RiskMatrixDecider;

impl RiskMatrixDecider {
    pub fn new() -> Self { Self }
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

        Ok(Decision {
            approved: true,
            techniques: approved_techniques,
            reason: format!(
                "Approved {} technique(s) at risk score {:.2}",
                recommendation.recommended_techniques.len(),
                recommendation.risk_score
            ),
            risk_accepted: recommendation.risk_score,
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
}
