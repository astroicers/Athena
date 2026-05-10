use async_trait::async_trait;
use sqlx::PgPool;
use athena_types::{OperationId, OodaIterationId, AthenaError};

#[async_trait]
pub trait IterationStore: Send + Sync {
    /// Insert a row when iteration completes (op_id + iter_id both known post-run).
    async fn record(&self, op_id: &OperationId, iter_id: &OodaIterationId) -> Result<(), AthenaError>;
}

pub struct SqlxIterationStore {
    pool: PgPool,
}

impl SqlxIterationStore {
    pub fn new(pool: PgPool) -> Self {
        Self { pool }
    }
}

#[async_trait]
impl IterationStore for SqlxIterationStore {
    async fn record(&self, op_id: &OperationId, iter_id: &OodaIterationId) -> Result<(), AthenaError> {
        // Ensure parent operation row exists
        sqlx::query(
            "INSERT INTO operations (id, name) VALUES ($1, 'auto') ON CONFLICT (id) DO NOTHING"
        )
        .bind(op_id.0)
        .execute(&self.pool)
        .await
        .map_err(|e| AthenaError::DatabaseError(e.to_string()))?;

        sqlx::query(
            r#"INSERT INTO ooda_iterations (id, operation_id, state, iteration_count, started_at, completed_at)
               VALUES ($1, $2, 'completed', 1, NOW(), NOW())
               ON CONFLICT (id) DO NOTHING"#,
        )
        .bind(iter_id.0)
        .bind(op_id.0)
        .execute(&self.pool)
        .await
        .map_err(|e| AthenaError::DatabaseError(e.to_string()))?;

        Ok(())
    }
}

/// No-op implementation for tests and non-postgres deployments.
pub struct NoopIterationStore;

#[async_trait]
impl IterationStore for NoopIterationStore {
    async fn record(&self, _op_id: &OperationId, _iter_id: &OodaIterationId) -> Result<(), AthenaError> {
        Ok(())
    }
}