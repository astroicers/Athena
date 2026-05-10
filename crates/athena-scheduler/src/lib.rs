use async_trait::async_trait;
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
}
