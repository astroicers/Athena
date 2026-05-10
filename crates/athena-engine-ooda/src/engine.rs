use async_trait::async_trait;
use std::sync::Arc;
use athena_types::{OperationId, OodaIterationId, ExecutionOutcome, AthenaError};
use athena_observe::ObservePhase;
use athena_orient::OrientPhase;
use athena_decide::DecidePhase;
use athena_act::ActPhase;
use athena_knowledge::constraint::OperationalConstraints;
use crate::DecisionEngine;

pub struct OodaEngine {
    observe: Arc<dyn ObservePhase>,
    orient: Arc<dyn OrientPhase>,
    decide: Arc<dyn DecidePhase>,
    act: Arc<dyn ActPhase>,
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
        Self { observe, orient, decide, act, constraints }
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

        // Orient
        let recommendation = self.orient.analyze(op_id, &obs_summary, "").await?;

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
