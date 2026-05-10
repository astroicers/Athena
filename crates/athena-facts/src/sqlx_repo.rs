use async_trait::async_trait;
use sqlx::{PgPool, Row};
use athena_types::{Fact, FactTrait, FactValue, OperationId, AthenaError};
use crate::FactRepository;

pub struct SqlxFactRepository {
    pool: PgPool,
}

impl SqlxFactRepository {
    pub fn new(pool: PgPool) -> Self {
        Self { pool }
    }
}

#[async_trait]
impl FactRepository for SqlxFactRepository {
    async fn insert(&self, fact: Fact) -> Result<(), AthenaError> {
        let value_json = serde_json::to_value(&fact.value)
            .map_err(|e| AthenaError::Internal(e.to_string()))?;

        sqlx::query(
            r#"
            INSERT INTO facts (id, operation_id, trait_name, fact_value, source, confidence, collected_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            ON CONFLICT (operation_id, trait_name, fact_value) DO NOTHING
            "#,
        )
        .bind(fact.id)
        .bind(fact.op_id.0)
        .bind(fact.trait_name.0)
        .bind(value_json)
        .bind(fact.source)
        .bind(fact.confidence as i32)
        .bind(fact.collected_at)
        .execute(&self.pool)
        .await
        .map_err(|e| AthenaError::DatabaseError(e.to_string()))?;

        Ok(())
    }

    async fn list(&self, op_id: &OperationId) -> Result<Vec<Fact>, AthenaError> {
        let rows = sqlx::query(
            r#"
            SELECT id, operation_id, trait_name, fact_value, source, confidence, collected_at
            FROM facts
            WHERE operation_id = $1
            ORDER BY collected_at ASC
            "#,
        )
        .bind(op_id.0)
        .fetch_all(&self.pool)
        .await
        .map_err(|e| AthenaError::DatabaseError(e.to_string()))?;

        rows.into_iter()
            .map(|row| {
                let value_json: serde_json::Value = row.try_get("fact_value")
                    .map_err(|e| AthenaError::Internal(e.to_string()))?;
                let value: FactValue = serde_json::from_value(value_json)
                    .map_err(|e| AthenaError::Internal(format!("fact_value deserialize: {e}")))?;
                let confidence: i32 = row.try_get("confidence")
                    .map_err(|e| AthenaError::Internal(e.to_string()))?;
                Ok(Fact {
                    id: row.try_get("id").map_err(|e| AthenaError::Internal(e.to_string()))?,
                    op_id: OperationId(row.try_get("operation_id").map_err(|e| AthenaError::Internal(e.to_string()))?),
                    trait_name: FactTrait(row.try_get("trait_name").map_err(|e| AthenaError::Internal(e.to_string()))?),
                    value,
                    source: row.try_get("source").map_err(|e| AthenaError::Internal(e.to_string()))?,
                    confidence: confidence as u8,
                    collected_at: row.try_get("collected_at").map_err(|e| AthenaError::Internal(e.to_string()))?,
                })
            })
            .collect()
    }

    async fn exists(&self, op_id: &OperationId, trait_name: &FactTrait, value: &str) -> Result<bool, AthenaError> {
        // Match Text variant JSON representation: "value"
        let value_json = serde_json::json!(value);

        let row = sqlx::query(
            r#"
            SELECT COUNT(*) as count
            FROM facts
            WHERE operation_id = $1
              AND trait_name = $2
              AND fact_value = $3
            "#,
        )
        .bind(op_id.0)
        .bind(&trait_name.0)
        .bind(value_json)
        .fetch_one(&self.pool)
        .await
        .map_err(|e| AthenaError::DatabaseError(e.to_string()))?;

        let count: i64 = row.try_get("count").map_err(|e| AthenaError::Internal(e.to_string()))?;
        Ok(count > 0)
    }

    async fn count(&self, op_id: &OperationId) -> Result<usize, AthenaError> {
        let row = sqlx::query("SELECT COUNT(*) as count FROM facts WHERE operation_id = $1")
            .bind(op_id.0)
            .fetch_one(&self.pool)
            .await
            .map_err(|e| AthenaError::DatabaseError(e.to_string()))?;

        let count: i64 = row.try_get("count").map_err(|e| AthenaError::Internal(e.to_string()))?;
        Ok(count as usize)
    }
}
