use async_trait::async_trait;
use std::sync::Arc;
use athena_types::{OperationId, Decision, OodaIterationId, ExecutionOutcome, ExecutionResult, AthenaError};
use athena_act::ActPhase;
use tokio::sync::Semaphore;

#[async_trait]
pub trait SwarmExecutor: Send + Sync {
    async fn execute_parallel(
        &self,
        op_id: &OperationId,
        decision: &Decision,
        iter_id: &OodaIterationId,
        max_concurrency: usize,
    ) -> Result<ExecutionOutcome, AthenaError>;
}

// Executes each approved technique concurrently, bounded by max_concurrency
pub struct ParallelSwarm {
    act: Arc<dyn ActPhase>,
}

impl ParallelSwarm {
    pub fn new(act: Arc<dyn ActPhase>) -> Self {
        Self { act }
    }
}

#[async_trait]
impl SwarmExecutor for ParallelSwarm {
    async fn execute_parallel(
        &self,
        op_id: &OperationId,
        decision: &Decision,
        iter_id: &OodaIterationId,
        max_concurrency: usize,
    ) -> Result<ExecutionOutcome, AthenaError> {
        if !decision.approved || decision.techniques.is_empty() {
            return Ok(ExecutionOutcome { results: vec![], facts_collected: 0 });
        }

        let sem = Arc::new(Semaphore::new(max_concurrency.max(1)));
        let mut handles = vec![];

        for technique in &decision.techniques {
            let act = Arc::clone(&self.act);
            let op_id = op_id.clone();
            let iter_id = iter_id.clone();
            let sem = Arc::clone(&sem);
            let single_decision = Decision {
                approved: true,
                techniques: vec![technique.clone()],
                reason: decision.reason.clone(),
                risk_accepted: decision.risk_accepted,
            };

            let handle = tokio::spawn(async move {
                let _permit = sem.acquire().await;
                act.execute(&op_id, &single_decision, &iter_id).await
            });
            handles.push(handle);
        }

        let mut all_results: Vec<ExecutionResult> = vec![];
        let mut total_facts = 0usize;

        for handle in handles {
            match handle.await {
                Ok(Ok(outcome)) => {
                    total_facts += outcome.facts_collected;
                    all_results.extend(outcome.results);
                }
                Ok(Err(e)) => {
                    tracing::error!(error = %e, "Swarm task failed");
                }
                Err(e) => {
                    tracing::error!(error = %e, "Swarm task panicked");
                }
            }
        }

        Ok(ExecutionOutcome { results: all_results, facts_collected: total_facts })
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use async_trait::async_trait;

    struct CountAct(Arc<tokio::sync::Mutex<Vec<String>>>);

    #[async_trait]
    impl ActPhase for CountAct {
        async fn execute(
            &self,
            _op_id: &OperationId,
            decision: &Decision,
            _iter_id: &OodaIterationId,
        ) -> Result<ExecutionOutcome, AthenaError> {
            let mut log = self.0.lock().await;
            for t in &decision.techniques {
                log.push(t.clone());
            }
            Ok(ExecutionOutcome {
                results: decision.techniques.iter().map(|t| ExecutionResult {
                    technique_id: t.clone(),
                    success: true,
                    output: "ok".into(),
                    new_facts: vec![],
                }).collect(),
                facts_collected: 0,
            })
        }
    }

    #[tokio::test]
    async fn executes_all_techniques() {
        let log = Arc::new(tokio::sync::Mutex::new(vec![]));
        let swarm = ParallelSwarm::new(Arc::new(CountAct(log.clone())));
        let op_id = OperationId::new();
        let iter_id = OodaIterationId::new();
        let decision = Decision {
            approved: true,
            techniques: vec!["T1046".into(), "T1082".into(), "T1033".into()],
            reason: "test".into(),
            risk_accepted: 0.3,
        };

        let outcome = swarm.execute_parallel(&op_id, &decision, &iter_id, 3).await.unwrap();
        assert_eq!(outcome.results.len(), 3);
        assert!(outcome.results.iter().all(|r| r.success));

        let mut logged = log.lock().await.clone();
        logged.sort();
        assert_eq!(logged, vec!["T1033", "T1046", "T1082"]);
    }

    #[tokio::test]
    async fn unapproved_returns_empty() {
        let log = Arc::new(tokio::sync::Mutex::new(vec![]));
        let swarm = ParallelSwarm::new(Arc::new(CountAct(log)));
        let op_id = OperationId::new();
        let iter_id = OodaIterationId::new();
        let decision = Decision {
            approved: false,
            techniques: vec!["T1046".into()],
            reason: "blocked".into(),
            risk_accepted: 0.9,
        };
        let outcome = swarm.execute_parallel(&op_id, &decision, &iter_id, 2).await.unwrap();
        assert!(outcome.results.is_empty());
    }

    #[tokio::test]
    async fn respects_concurrency_limit() {
        use std::sync::atomic::{AtomicUsize, Ordering};
        use std::sync::Arc as StdArc;

        struct PeakTracker {
            peak: StdArc<AtomicUsize>,
            current: StdArc<AtomicUsize>,
        }
        #[async_trait]
        impl ActPhase for PeakTracker {
            async fn execute(&self, _op: &OperationId, d: &Decision, _it: &OodaIterationId) -> Result<ExecutionOutcome, AthenaError> {
                let cur = self.current.fetch_add(1, Ordering::SeqCst) + 1;
                self.peak.fetch_max(cur, Ordering::SeqCst);
                tokio::time::sleep(tokio::time::Duration::from_millis(20)).await;
                self.current.fetch_sub(1, Ordering::SeqCst);
                Ok(ExecutionOutcome {
                    results: d.techniques.iter().map(|t| ExecutionResult { technique_id: t.clone(), success: true, output: "".into(), new_facts: vec![] }).collect(),
                    facts_collected: 0,
                })
            }
        }

        let peak = StdArc::new(AtomicUsize::new(0));
        let current = StdArc::new(AtomicUsize::new(0));
        let tracker = Arc::new(PeakTracker { peak: peak.clone(), current: current.clone() });
        let swarm = ParallelSwarm::new(tracker);
        let op_id = OperationId::new();
        let iter_id = OodaIterationId::new();
        let decision = Decision {
            approved: true,
            techniques: (0..6).map(|i| format!("T{i:04}")).collect(),
            reason: "test".into(),
            risk_accepted: 0.2,
        };
        swarm.execute_parallel(&op_id, &decision, &iter_id, 2).await.unwrap();
        assert!(peak.load(Ordering::SeqCst) <= 2, "Concurrency exceeded limit of 2");
    }
}
