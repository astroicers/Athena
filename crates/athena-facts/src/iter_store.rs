use async_trait::async_trait;
use sqlx::{PgPool, Row};
use athena_types::{OperationId, OodaIterationId, AthenaError};
use serde_json::{json, Value};

#[async_trait]
pub trait IterationStore: Send + Sync {
    /// Insert a row when iteration completes (op_id + iter_id both known post-run).
    async fn record(&self, op_id: &OperationId, iter_id: &OodaIterationId) -> Result<(), AthenaError>;
    /// List all operations with iteration counts.
    async fn list_operations(&self) -> Result<Vec<Value>, AthenaError>;
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

    async fn list_operations(&self) -> Result<Vec<Value>, AthenaError> {
        let rows = sqlx::query(
            r#"SELECT o.id, o.name, o.status, o.created_at,
                      COUNT(i.id) AS iteration_count
               FROM operations o
               LEFT JOIN ooda_iterations i ON i.operation_id = o.id
               GROUP BY o.id
               ORDER BY o.created_at DESC
               LIMIT 100"#,
        )
        .fetch_all(&self.pool)
        .await
        .map_err(|e| AthenaError::DatabaseError(e.to_string()))?;

        Ok(rows.iter().map(|r| {
            let id: uuid::Uuid = r.try_get("id").unwrap_or_default();
            let name: String = r.try_get("name").unwrap_or_default();
            let status: String = r.try_get("status").unwrap_or_default();
            let created_at: chrono::DateTime<chrono::Utc> = r.try_get("created_at").unwrap_or_else(|_| chrono::Utc::now());
            let iteration_count: i64 = r.try_get("iteration_count").unwrap_or(0);
            json!({
                "op_id": id.to_string(),
                "name": name,
                "status": status,
                "created_at": created_at,
                "iteration_count": iteration_count,
            })
        }).collect())
    }
}

/// No-op implementation for tests and non-postgres deployments.
pub struct NoopIterationStore;

#[async_trait]
impl IterationStore for NoopIterationStore {
    async fn record(&self, _op_id: &OperationId, _iter_id: &OodaIterationId) -> Result<(), AthenaError> {
        Ok(())
    }
    async fn list_operations(&self) -> Result<Vec<Value>, AthenaError> {
        Ok(vec![])
    }
}