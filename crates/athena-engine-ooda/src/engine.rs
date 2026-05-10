use async_trait::async_trait;
use std::sync::Arc;
use athena_types::{OperationId, OodaIterationId, ExecutionOutcome, AthenaError};
use athena_observe::ObservePhase;
use athena_orient::OrientPhase;
use athena_decide::DecidePhase;
use athena_act::ActPhase;
use athena_attack_graph::AttackGraphEngine;
use athena_knowledge::constraint::OperationalConstraints;
use crate::DecisionEngine;

pub struct OodaEngine {
    observe: Arc<dyn ObservePhase>,
    orient: Arc<dyn OrientPhase>,
    decide: Arc<dyn DecidePhase>,
    act: Arc<dyn ActPhase>,
    attack_graph: Option<Arc<dyn AttackGraphEngine>>,
    constraints: OperationalConstraints,
}

impl OodaEngine {
    pub fn new(
        observe: Arc<dyn ObservePhase>,
        orient: Arc<dyn OrientPhase>,
        decide: Arc<dyn DecidePhase>,
        act: Arc<dyn ActPhase>,
        constraints: OperationalConstraints,
    ) -> Self {
        Self { observe, orient, decide, act, attack_graph: None, constraints }
    }

    pub fn with_attack_graph(mut self, ag: Arc<dyn AttackGraphEngine>) -> Self {
        self.attack_graph = Some(ag);
        self
    }
}

#[async_trait]
impl DecisionEngine for OodaEngine {
    fn name(&self) -> &'static str { "ooda" }

    async fn run_iteration(
        &self,
        op_id: &OperationId,
    ) -> Result<(OodaIterationId, ExecutionOutcome), AthenaError> {
        let iter_id = OodaIterationId::new();

        // Observe
        let _facts = self.observe.collect(op_id).await?;
        let obs_summary = self.observe.summarize(op_id).await?;

        // Attack graph (optional — empty string if not configured)
        let graph_summary = if let Some(ag) = &self.attack_graph {
            let paths = ag.compute_paths(op_id, vec![]).await.unwrap_or_default();
            ag.to_summary(&paths).await
        } else {
            String::new()
        };

        // Orient
        let recommendation = self.orient.analyze(op_id, &obs_summary, &graph_summary).await?;

        // Decide
        let decision = self.decide.evaluate(op_id, &recommendation, &self.constraints).await?;

        // Act
        let outcome = self.act.execute(op_id, &decision, &iter_id).await?;

        Ok((iter_id, outcome))
    }

    async fn abort(&self, _op_id: &OperationId) -> Result<(), AthenaError> {
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use athena_types::{Fact, OrientRecommendation, Decision, ExecutionResult, FactTrait, FactValue};

    struct MockObserver;
    #[async_trait]
    impl ObservePhase for MockObserver {
        async fn collect(&self, op_id: &OperationId) -> Result<Vec<Fact>, AthenaError> {
            Ok(vec![Fact {
                id: uuid::Uuid::new_v4(),
                op_id: op_id.clone(),
                trait_name: FactTrait("open_port".into()),
                value: FactValue::Text("22".into()),
                source: "mock".into(),
                confidence: 90,
                collected_at: chrono::Utc::now(),
            }])
        }
        async fn summarize(&self, _op_id: &OperationId) -> Result<String, AthenaError> {
            Ok("1 open port: 22".into())
        }
    }

    struct MockOrient;
    #[async_trait]
    impl OrientPhase for MockOrient {
        async fn analyze(&self, _op_id: &OperationId, _obs: &str, _graph: &str) -> Result<OrientRecommendation, AthenaError> {
            Ok(OrientRecommendation {
                summary: "SSH exposed".into(),
                recommended_techniques: vec!["T1046".into()],
                risk_score: 0.3,
                rationale: "open port 22".into(),
            })
        }
    }

    struct MockDecide;
    #[async_trait]
    impl DecidePhase for MockDecide {
        async fn evaluate(&self, _op_id: &OperationId, rec: &OrientRecommendation, _c: &OperationalConstraints) -> Result<Decision, AthenaError> {
            Ok(Decision {
                approved: true,
                techniques: rec.recommended_techniques.clone(),
                reason: "approved by mock".into(),
                risk_accepted: rec.risk_score,
            })
        }
    }

    struct MockAct;
    #[async_trait]
    impl ActPhase for MockAct {
        async fn execute(&self, _op_id: &OperationId, decision: &Decision, _iter_id: &OodaIterationId) -> Result<ExecutionOutcome, AthenaError> {
            let results = decision.techniques.iter().map(|t| ExecutionResult {
                technique_id: t.clone(),
                success: true,
                output: "mock output".into(),
                new_facts: vec![],
            }).collect();
            Ok(ExecutionOutcome { results, facts_collected: 1 })
        }
    }

    #[tokio::test]
    async fn full_ooda_cycle_with_mocks() {
        let engine = OodaEngine::new(
            Arc::new(MockObserver),
            Arc::new(MockOrient),
            Arc::new(MockDecide),
            Arc::new(MockAct),
            OperationalConstraints::default(),
        );
        let op_id = OperationId::new();
        let (iter_id, outcome) = engine.run_iteration(&op_id).await.unwrap();
        // iter_id should be a valid UUID
        assert!(!iter_id.to_string().is_empty());
        // One technique executed successfully
        assert_eq!(outcome.results.len(), 1);
        assert!(outcome.results[0].success);
        assert_eq!(outcome.results[0].technique_id, "T1046");
    }

    #[tokio::test]
    async fn abort_returns_ok() {
        let engine = OodaEngine::new(
            Arc::new(MockObserver),
            Arc::new(MockOrient),
            Arc::new(MockDecide),
            Arc::new(MockAct),
            OperationalConstraints::default(),
        );
        let op_id = OperationId::new();
        engine.abort(&op_id).await.unwrap();
    }

    #[test]
    fn engine_name_is_ooda() {
        let engine = OodaEngine::new(
            Arc::new(MockObserver),
            Arc::new(MockOrient),
            Arc::new(MockDecide),
            Arc::new(MockAct),
            OperationalConstraints::default(),
        );
        assert_eq!(engine.name(), "ooda");
    }
}
