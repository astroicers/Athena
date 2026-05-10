// Stub — implementation deferred to Athena 2.1
use async_trait::async_trait;
use athena_types::AthenaError;

#[async_trait]
pub trait OsintEngine: Send + Sync {
    async fn search(&self, query: &str) -> Result<Vec<String>, AthenaError>;
}
