use async_trait::async_trait;
use std::collections::HashSet;
use std::sync::Mutex;
use athena_types::{Fact, FactTrait, OperationId, AthenaError};
use crate::FactRepository;

// Key for deduplication: (op_id, trait_name, text_value)
type DedupeKey = (String, String, String);

pub struct InMemoryFactRepository {
    facts: Mutex<Vec<Fact>>,
    seen: Mutex<HashSet<DedupeKey>>,
}

impl InMemoryFactRepository {
    pub fn new() -> Self {
        Self {
            facts: Mutex::new(Vec::new()),
            seen: Mutex::new(HashSet::new()),
        }
    }

    fn make_key(fact: &Fact) -> DedupeKey {
        let value_str = match &fact.value {
            athena_types::FactValue::Text(s) => s.clone(),
            athena_types::FactValue::Number(n) => n.to_string(),
            athena_types::FactValue::Bool(b) => b.to_string(),
        };
        (fact.op_id.to_string(), fact.trait_name.0.clone(), value_str)
    }
}

impl Default for InMemoryFactRepository {
    fn default() -> Self { Self::new() }
}

#[async_trait]
impl FactRepository for InMemoryFactRepository {
    async fn insert(&self, fact: Fact) -> Result<(), AthenaError> {
        let key = Self::make_key(&fact);
        let mut seen = self.seen.lock().unwrap();
        if seen.contains(&key) {
            return Ok(()); // silently deduplicate
        }
        seen.insert(key);
        self.facts.lock().unwrap().push(fact);
        Ok(())
    }

    async fn list(&self, op_id: &OperationId) -> Result<Vec<Fact>, AthenaError> {
        let op_str = op_id.to_string();
        let facts = self.facts.lock().unwrap();
        Ok(facts.iter()
            .filter(|f| f.op_id.to_string() == op_str)
            .cloned()
            .collect())
    }

    async fn exists(&self, op_id: &OperationId, trait_name: &FactTrait, value: &str) -> Result<bool, AthenaError> {
        let key: DedupeKey = (op_id.to_string(), trait_name.0.clone(), value.to_string());
        Ok(self.seen.lock().unwrap().contains(&key))
    }

    async fn count(&self, op_id: &OperationId) -> Result<usize, AthenaError> {
        let op_str = op_id.to_string();
        Ok(self.facts.lock().unwrap()
            .iter()
            .filter(|f| f.op_id.to_string() == op_str)
            .count())
    }
}
