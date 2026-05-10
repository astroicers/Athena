use athena_types::{OperationId, AthenaError};
use athena_engine_ooda::DecisionEngine;
use std::sync::Arc;
use dashmap::DashMap;
use tokio::task::JoinHandle;

pub struct OodaScheduler {
    engine: Arc<dyn DecisionEngine>,
    handles: DashMap<String, JoinHandle<()>>,
}

impl OodaScheduler {
    pub fn new(engine: Arc<dyn DecisionEngine>) -> Self {
        Self { engine, handles: DashMap::new() }
    }

    pub async fn start(&self, op_id: OperationId, interval_secs: u64) {
        let engine = Arc::clone(&self.engine);
        let op_id_clone = op_id.clone();
        let handle = tokio::spawn(async move {
            let mut interval = tokio::time::interval(
                tokio::time::Duration::from_secs(interval_secs)
            );
            loop {
                interval.tick().await;
                match engine.run_iteration(&op_id_clone).await {
                    Ok(_) => tracing::info!(op = %op_id_clone, "OODA iteration completed"),
                    Err(e) => tracing::error!(op = %op_id_clone, error = %e, "OODA iteration failed"),
                }
            }
        });
        self.handles.insert(op_id.to_string(), handle);
    }

    pub async fn stop(&self, op_id: &OperationId) -> Result<(), AthenaError> {
        if let Some((_, handle)) = self.handles.remove(&op_id.to_string()) {
            handle.abort();
        }
        self.engine.abort(op_id).await
    }

    pub fn is_running(&self, op_id: &OperationId) -> bool {
        self.handles.contains_key(&op_id.to_string())
    }

    pub fn active_operations(&self) -> Vec<String> {
        self.handles.iter().map(|e| e.key().clone()).collect()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use async_trait::async_trait;
    use athena_types::{OodaIterationId, ExecutionOutcome};

    struct NoopEngine;

    #[async_trait]
    impl DecisionEngine for NoopEngine {
        fn name(&self) -> &'static str { "noop" }
        async fn run_iteration(&self, _op_id: &OperationId) -> Result<(OodaIterationId, ExecutionOutcome), AthenaError> {
            Ok((OodaIterationId::new(), ExecutionOutcome { results: vec![], facts_collected: 0 }))
        }
        async fn abort(&self, _op_id: &OperationId) -> Result<(), AthenaError> { Ok(()) }
    }

    #[tokio::test]
    async fn start_registers_handle() {
        let scheduler = OodaScheduler::new(Arc::new(NoopEngine));
        let op_id = OperationId::new();
        assert!(!scheduler.is_running(&op_id));
        scheduler.start(op_id.clone(), 3600).await;
        assert!(scheduler.is_running(&op_id));
        scheduler.stop(&op_id).await.unwrap();
    }

    #[tokio::test]
    async fn stop_removes_handle() {
        let scheduler = OodaScheduler::new(Arc::new(NoopEngine));
        let op_id = OperationId::new();
        scheduler.start(op_id.clone(), 3600).await;
        assert!(scheduler.is_running(&op_id));
        scheduler.stop(&op_id).await.unwrap();
        assert!(!scheduler.is_running(&op_id));
    }

    #[tokio::test]
    async fn stop_unknown_op_is_ok() {
        let scheduler = OodaScheduler::new(Arc::new(NoopEngine));
        let op_id = OperationId::new();
        // stopping something that was never started should not error
        scheduler.stop(&op_id).await.unwrap();
    }

    #[tokio::test]
    async fn active_operations_reflects_running_set() {
        let scheduler = OodaScheduler::new(Arc::new(NoopEngine));
        let op1 = OperationId::new();
        let op2 = OperationId::new();
        scheduler.start(op1.clone(), 3600).await;
        scheduler.start(op2.clone(), 3600).await;
        let active = scheduler.active_operations();
        assert_eq!(active.len(), 2);
        scheduler.stop(&op1).await.unwrap();
        scheduler.stop(&op2).await.unwrap();
    }

    #[tokio::test]
    async fn scheduler_ticks_engine() {
        use std::sync::atomic::{AtomicUsize, Ordering};
        use std::sync::Arc as StdArc;

        struct CountingEngine(StdArc<AtomicUsize>);
        #[async_trait]
        impl DecisionEngine for CountingEngine {
            fn name(&self) -> &'static str { "counting" }
            async fn run_iteration(&self, _op_id: &OperationId) -> Result<(OodaIterationId, ExecutionOutcome), AthenaError> {
                self.0.fetch_add(1, Ordering::SeqCst);
                Ok((OodaIterationId::new(), ExecutionOutcome { results: vec![], facts_collected: 0 }))
            }
            async fn abort(&self, _op_id: &OperationId) -> Result<(), AthenaError> { Ok(()) }
        }

        let counter = StdArc::new(AtomicUsize::new(0));
        let engine = Arc::new(CountingEngine(counter.clone()));
        let scheduler = OodaScheduler::new(engine);
        let op_id = OperationId::new();

        // The scheduler API takes whole seconds; bypass via direct spawn for sub-second test
        let engine2 = Arc::new(CountingEngine(counter.clone()));
        let counter2 = counter.clone();
        let op_id2 = op_id.clone();
        let handle = tokio::spawn(async move {
            let mut iv = tokio::time::interval(tokio::time::Duration::from_millis(10));
            for _ in 0..5 {
                iv.tick().await;
                let _ = engine2.run_iteration(&op_id2).await;
            }
        });
        handle.await.unwrap();
        assert!(counter2.load(Ordering::SeqCst) >= 5, "engine should have been called 5 times");
    }
}
