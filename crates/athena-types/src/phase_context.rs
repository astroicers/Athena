use std::collections::HashMap;
use serde_json::Value;
use crate::{OperationId, OodaIterationId, OrientRecommendation, Decision, ExecutionOutcome, AthenaError};

/// Shared state bag passed through every OODA phase in sequence.
///
/// Each phase reads what it needs and writes its output back into the context.
/// The `extensions` map carries operator overrides and inter-phase data that
/// don't fit the fixed fields, without requiring struct changes.
#[derive(Debug, Clone)]
pub struct PhaseContext {
    pub op_id: OperationId,
    pub iter_id: OodaIterationId,

    /// Produced by ObservePhase
    pub obs_summary: String,

    /// Produced by OrientPhase
    pub recommendation: Option<OrientRecommendation>,

    /// Produced by DecidePhase
    pub decision: Option<Decision>,

    /// Produced by ActPhase
    pub outcome: Option<ExecutionOutcome>,

    /// Free-form extension bag. Well-known keys:
    ///   "operator_override_techniques" — Vec<String> as JSON array
    ///   "operator_override_reason"     — String
    pub extensions: HashMap<String, Value>,
}

impl PhaseContext {
    pub fn new(op_id: OperationId, iter_id: OodaIterationId) -> Self {
        Self {
            op_id,
            iter_id,
            obs_summary: String::new(),
            recommendation: None,
            decision: None,
            outcome: None,
            extensions: HashMap::new(),
        }
    }

    /// Returns the OrientRecommendation or an Internal error if Orient has not run yet.
    pub fn require_recommendation(&self) -> Result<&OrientRecommendation, AthenaError> {
        self.recommendation.as_ref().ok_or_else(|| {
            AthenaError::Internal("PhaseContext: OrientRecommendation not set — Orient phase has not run".into())
        })
    }

    /// Returns the Decision or an Internal error if Decide has not run yet.
    pub fn require_decision(&self) -> Result<&Decision, AthenaError> {
        self.decision.as_ref().ok_or_else(|| {
            AthenaError::Internal("PhaseContext: Decision not set — Decide phase has not run".into())
        })
    }

    /// Read operator_override_techniques from extensions, if present.
    pub fn operator_techniques(&self) -> Option<Vec<String>> {
        self.extensions
            .get("operator_override_techniques")
            .and_then(|v| v.as_array())
            .map(|arr| arr.iter().filter_map(|v| v.as_str().map(str::to_owned)).collect())
    }

    /// Convenience: consume context and produce ExecutionOutcome for engine return.
    pub fn into_outcome(self) -> ExecutionOutcome {
        self.outcome.unwrap_or_else(|| ExecutionOutcome {
            results: vec![],
            facts_collected: 0,
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::ExecutionResult;

    #[test]
    fn new_context_has_empty_fields() {
        let op = OperationId::new();
        let it = OodaIterationId::new();
        let ctx = PhaseContext::new(op.clone(), it.clone());
        assert_eq!(ctx.op_id, op);
        assert_eq!(ctx.iter_id, it);
        assert!(ctx.obs_summary.is_empty());
        assert!(ctx.recommendation.is_none());
        assert!(ctx.decision.is_none());
        assert!(ctx.extensions.is_empty());
    }

    #[test]
    fn require_recommendation_errors_when_none() {
        let ctx = PhaseContext::new(OperationId::new(), OodaIterationId::new());
        assert!(ctx.require_recommendation().is_err());
    }

    #[test]
    fn require_decision_errors_when_none() {
        let ctx = PhaseContext::new(OperationId::new(), OodaIterationId::new());
        assert!(ctx.require_decision().is_err());
    }

    #[test]
    fn operator_techniques_parses_extension() {
        let mut ctx = PhaseContext::new(OperationId::new(), OodaIterationId::new());
        ctx.extensions.insert(
            "operator_override_techniques".into(),
            serde_json::json!(["T1046", "T1059"]),
        );
        let techs = ctx.operator_techniques().unwrap();
        assert_eq!(techs, vec!["T1046", "T1059"]);
    }

    #[test]
    fn into_outcome_returns_empty_when_none() {
        let ctx = PhaseContext::new(OperationId::new(), OodaIterationId::new());
        let outcome = ctx.into_outcome();
        assert!(outcome.results.is_empty());
        assert_eq!(outcome.facts_collected, 0);
    }

    #[test]
    fn into_outcome_returns_act_result() {
        let mut ctx = PhaseContext::new(OperationId::new(), OodaIterationId::new());
        ctx.outcome = Some(ExecutionOutcome {
            results: vec![ExecutionResult {
                technique_id: "T1046".into(),
                success: true,
                output: "ok".into(),
                new_facts: vec![],
            }],
            facts_collected: 3,
        });
        let outcome = ctx.into_outcome();
        assert_eq!(outcome.results.len(), 1);
        assert_eq!(outcome.facts_collected, 3);
    }
}
