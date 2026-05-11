pub mod operation;
pub mod target;
pub mod fact;
pub mod decision;
pub mod error;
pub mod phase_context;

pub use operation::{OperationId, Operation, OperationStatus};
pub use target::{Target, TargetId};
pub use fact::{Fact, FactTrait, FactValue};
pub use decision::{Decision, OrientRecommendation, OodaIterationId, ExecutionOutcome, ExecutionResult, TechniqueParams, HealthStatus};
pub use error::AthenaError;
pub use phase_context::PhaseContext;

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn operation_id_is_unique() {
        let a = OperationId::new();
        let b = OperationId::new();
        assert_ne!(a, b);
    }

    #[test]
    fn operation_id_display() {
        let id = OperationId::new();
        let s = id.to_string();
        assert_eq!(s.len(), 36, "UUID display should be 36 chars");
        assert!(s.contains('-'));
    }

    #[test]
    fn ooda_iteration_id_is_unique() {
        let a = OodaIterationId::new();
        let b = OodaIterationId::new();
        assert_ne!(a, b);
    }

    #[test]
    fn target_id_default_is_unique() {
        let a = TargetId::default();
        let b = TargetId::default();
        assert_ne!(a, b);
    }

    #[test]
    fn fact_value_serialization_roundtrip() {
        let text = FactValue::Text("127.0.0.1".into());
        let json = serde_json::to_string(&text).unwrap();
        let back: FactValue = serde_json::from_str(&json).unwrap();
        assert_eq!(text, back);
    }

    #[test]
    fn fact_value_bool_roundtrip() {
        let val = FactValue::Bool(true);
        let json = serde_json::to_string(&val).unwrap();
        let back: FactValue = serde_json::from_str(&json).unwrap();
        assert_eq!(val, back);
    }

    #[test]
    fn athena_error_display() {
        let e = AthenaError::OperationNotFound("op-123".into());
        assert!(e.to_string().contains("op-123"));
    }

    #[test]
    fn operation_status_serde() {
        let status = OperationStatus::Active;
        let json = serde_json::to_string(&status).unwrap();
        assert_eq!(json, "\"active\"");
        let back: OperationStatus = serde_json::from_str(&json).unwrap();
        assert_eq!(back, OperationStatus::Active);
    }

    #[test]
    fn health_status_variants() {
        assert_ne!(HealthStatus::Healthy, HealthStatus::Unhealthy);
        assert_ne!(HealthStatus::Degraded, HealthStatus::Healthy);
    }

    #[test]
    fn orient_recommendation_fields() {
        let rec = OrientRecommendation {
            summary: "test".into(),
            recommended_techniques: vec!["T1046".into()],
            risk_score: 0.3,
            rationale: "low risk recon".into(),
        };
        assert_eq!(rec.recommended_techniques.len(), 1);
        assert!(rec.risk_score < 0.5);
    }

    #[test]
    fn decision_approved_fields() {
        let d = Decision {
            approved: true,
            techniques: vec!["T1046".into(), "T1078".into()],
            reason: "within constraints".into(),
            risk_accepted: 0.3,
        };
        assert!(d.approved);
        assert_eq!(d.techniques.len(), 2);
    }
}
