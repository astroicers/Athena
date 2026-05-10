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

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn connect_malformed_url_returns_error() {
        // Malformed URL fails immediately without network timeout
        let result = DatabasePool::connect("not-a-valid-url").await;
        assert!(result.is_err());
    }

    #[test]
    fn db_error_display() {
        let e = sqlx::Error::RowNotFound;
        let db_err = DbError::Connection(e);
        assert!(db_err.to_string().contains("connection error"));
    }
}
