pub mod sqlx_repo;
pub mod memory_repo;

use async_trait::async_trait;
use athena_types::{Fact, FactTrait, OperationId, AthenaError};

#[async_trait]
pub trait FactRepository: Send + Sync {
    async fn insert(&self, fact: Fact) -> Result<(), AthenaError>;
    async fn list(&self, op_id: &OperationId) -> Result<Vec<Fact>, AthenaError>;
    async fn exists(&self, op_id: &OperationId, trait_name: &FactTrait, value: &str) -> Result<bool, AthenaError>;
    async fn count(&self, op_id: &OperationId) -> Result<usize, AthenaError>;
}

pub use sqlx_repo::SqlxFactRepository;
pub use memory_repo::InMemoryFactRepository;

#[cfg(test)]
mod tests {
    use super::*;
    use athena_types::{Fact, FactTrait, FactValue, OperationId};
    use uuid::Uuid;
    use chrono::Utc;

    fn make_fact(op_id: &OperationId, trait_name: &str, value: &str) -> Fact {
        Fact {
            id: Uuid::new_v4(),
            op_id: op_id.clone(),
            trait_name: FactTrait(trait_name.into()),
            value: FactValue::Text(value.into()),
            source: "test".into(),
            confidence: 80,
            collected_at: Utc::now(),
        }
    }

    #[tokio::test]
    async fn in_memory_insert_and_list() {
        let repo = InMemoryFactRepository::new();
        let op_id = OperationId::new();
        repo.insert(make_fact(&op_id, "open_port", "22")).await.unwrap();
        let facts = repo.list(&op_id).await.unwrap();
        assert_eq!(facts.len(), 1);
        assert_eq!(facts[0].trait_name.0, "open_port");
    }

    #[tokio::test]
    async fn in_memory_deduplication() {
        let repo = InMemoryFactRepository::new();
        let op_id = OperationId::new();
        repo.insert(make_fact(&op_id, "open_port", "22")).await.unwrap();
        repo.insert(make_fact(&op_id, "open_port", "22")).await.unwrap(); // dup — ignored
        repo.insert(make_fact(&op_id, "open_port", "80")).await.unwrap();
        assert_eq!(repo.list(&op_id).await.unwrap().len(), 2);
    }

    #[tokio::test]
    async fn in_memory_exists() {
        let repo = InMemoryFactRepository::new();
        let op_id = OperationId::new();
        repo.insert(make_fact(&op_id, "os", "Linux")).await.unwrap();
        assert!(repo.exists(&op_id, &FactTrait("os".into()), "Linux").await.unwrap());
        assert!(!repo.exists(&op_id, &FactTrait("os".into()), "Windows").await.unwrap());
    }

    #[tokio::test]
    async fn in_memory_op_isolation() {
        let repo = InMemoryFactRepository::new();
        let op1 = OperationId::new();
        let op2 = OperationId::new();
        repo.insert(make_fact(&op1, "host", "10.0.0.1")).await.unwrap();
        repo.insert(make_fact(&op2, "host", "10.0.0.2")).await.unwrap();
        assert_eq!(repo.list(&op1).await.unwrap().len(), 1);
        assert_eq!(repo.list(&op2).await.unwrap().len(), 1);
    }

    #[tokio::test]
    async fn in_memory_count() {
        let repo = InMemoryFactRepository::new();
        let op_id = OperationId::new();
        assert_eq!(repo.count(&op_id).await.unwrap(), 0);
        repo.insert(make_fact(&op_id, "port", "443")).await.unwrap();
        assert_eq!(repo.count(&op_id).await.unwrap(), 1);
    }
}
