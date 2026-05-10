use sqlx::PgPool;
use thiserror::Error;

#[derive(Debug, Error)]
pub enum DbError {
    #[error("connection error: {0}")]
    Connection(#[from] sqlx::Error),
}

pub struct DatabasePool {
    pub pool: PgPool,
}

impl DatabasePool {
    pub async fn connect(url: &str) -> Result<Self, DbError> {
        let pool = PgPool::connect(url).await?;
        Ok(Self { pool })
    }
}
