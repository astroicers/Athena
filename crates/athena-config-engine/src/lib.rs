use async_trait::async_trait;
use athena_types::{OperationId, AthenaError};
use athena_knowledge::constraint::OperationalConstraints;

#[async_trait]
pub trait ConfigEngine: Send + Sync {
    async fn get_constraints(&self, op_id: &OperationId) -> Result<OperationalConstraints, AthenaError>;
}

/// Static config engine — always returns a fixed set of constraints.
/// Used in tests and when no database-backed config is needed.
pub struct StaticConfigEngine {
    pub constraints: OperationalConstraints,
}

impl StaticConfigEngine {
    pub fn new(constraints: OperationalConstraints) -> Self { Self { constraints } }
    pub fn default_permissive() -> Self { Self::new(OperationalConstraints::default()) }
}

#[async_trait]
impl ConfigEngine for StaticConfigEngine {
    async fn get_constraints(&self, _op_id: &OperationId) -> Result<OperationalConstraints, AthenaError> {
        Ok(self.constraints.clone())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn static_engine_returns_constraints() {
        let engine = StaticConfigEngine::default_permissive();
        let op_id = OperationId::new();
        let c = engine.get_constraints(&op_id).await.unwrap();
        assert_eq!(c.max_noise_level, 5);
    }

    #[tokio::test]
    async fn static_engine_custom_constraints() {
        let mut c = OperationalConstraints::default();
        c.max_noise_level = 2;
        c.denied_techniques = vec!["T1059".into()];
        let engine = StaticConfigEngine::new(c);
        let op_id = OperationId::new();
        let result = engine.get_constraints(&op_id).await.unwrap();
        assert_eq!(result.max_noise_level, 2);
        assert!(result.denied_techniques.contains(&"T1059".to_string()));
    }
}
