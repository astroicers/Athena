use async_trait::async_trait;
use std::sync::Arc;
use athena_types::{OperationId, AthenaError};
use athena_facts::FactRepository;
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct C5isrStatus {
    pub command: f32,
    pub control: f32,
    pub communications: f32,
    pub computers: f32,
    pub intelligence: f32,
    pub surveillance: f32,
    pub overall: f32,
}

impl C5isrStatus {
    pub fn compute_overall(&mut self) {
        self.overall = (self.command + self.control + self.communications
            + self.computers + self.intelligence + self.surveillance) / 6.0;
    }
}

#[async_trait]
pub trait C5isrMapper: Send + Sync {
    async fn assess(&self, op_id: &OperationId) -> Result<C5isrStatus, AthenaError>;
}

// Derives C5ISR scores from collected facts
pub struct FactDrivenC5isrMapper {
    fact_repo: Arc<dyn FactRepository>,
}

impl FactDrivenC5isrMapper {
    pub fn new(fact_repo: Arc<dyn FactRepository>) -> Self {
        Self { fact_repo }
    }
}

#[async_trait]
impl C5isrMapper for FactDrivenC5isrMapper {
    async fn assess(&self, op_id: &OperationId) -> Result<C5isrStatus, AthenaError> {
        let facts = self.fact_repo.list(op_id).await?;

        let has = |trait_name: &str| -> bool {
            facts.iter().any(|f| f.trait_name.0 == trait_name)
        };

        let count = |trait_name: &str| -> usize {
            facts.iter().filter(|f| f.trait_name.0 == trait_name).count()
        };

        // Scoring heuristics derived from fact types
        let mut status = C5isrStatus {
            // Command: credential access enables commanding the target
            command: if has("valid_credential") { 0.8 } else { 0.2 },
            // Control: active shell session or execution path
            control: if has("open_port") && count("open_port") >= 1 { 0.6 } else { 0.1 },
            // Communications: known services = comms channels mapped
            communications: if has("service") || has("open_port") { 0.7 } else { 0.2 },
            // Computers: OS/hostname identified
            computers: if has("os") && has("hostname") { 0.9 } else if has("live_host") { 0.5 } else { 0.1 },
            // Intelligence: vulnerability data
            intelligence: if has("vulnerability") { 0.8 } else if has("kernel_version") { 0.4 } else { 0.2 },
            // Surveillance: user enumeration and network mapping
            surveillance: {
                let user_score = if has("local_user") { 0.5 } else { 0.0 };
                let net_score = if has("network_segment") || has("live_host") { 0.5 } else { 0.0 };
                f32::min(user_score + net_score, 1.0)
            },
            overall: 0.0,
        };
        status.compute_overall();
        Ok(status)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use athena_facts::InMemoryFactRepository;
    use athena_types::{Fact, FactTrait, FactValue, TargetId};
    use uuid::Uuid;
    use chrono::Utc;

    async fn insert_fact(repo: &InMemoryFactRepository, op_id: &OperationId, trait_name: &str, value: &str) {
        let fact = Fact {
            id: Uuid::new_v4(),
            op_id: op_id.clone(),
            trait_name: FactTrait(trait_name.into()),
            value: FactValue::Text(value.into()),
            source: "test".into(),
            confidence: 80,
            collected_at: Utc::now(),
        };
        repo.insert(fact).await.unwrap();
    }

    #[tokio::test]
    async fn no_facts_yields_low_scores() {
        let repo = Arc::new(InMemoryFactRepository::new());
        let mapper = FactDrivenC5isrMapper::new(repo);
        let op_id = OperationId::new();
        let status = mapper.assess(&op_id).await.unwrap();
        assert!(status.overall < 0.4, "No facts should yield low overall score");
    }

    #[tokio::test]
    async fn rich_facts_yield_high_scores() {
        let repo = Arc::new(InMemoryFactRepository::new());
        let op_id = OperationId::new();
        for (t, v) in [
            ("valid_credential", "admin:pass"),
            ("open_port", "22"),
            ("service", "ssh"),
            ("os", "Linux"),
            ("hostname", "target"),
            ("vulnerability", "CVE-2021-44228"),
            ("local_user", "root"),
            ("network_segment", "10.0.0.0/24"),
        ] {
            insert_fact(&repo, &op_id, t, v).await;
        }
        let mapper = FactDrivenC5isrMapper::new(repo);
        let status = mapper.assess(&op_id).await.unwrap();
        assert!(status.overall > 0.6, "Rich facts should yield high overall: {}", status.overall);
    }

    #[tokio::test]
    async fn overall_is_mean_of_domains() {
        let repo = Arc::new(InMemoryFactRepository::new());
        let mapper = FactDrivenC5isrMapper::new(repo);
        let op_id = OperationId::new();
        let status = mapper.assess(&op_id).await.unwrap();
        let expected = (status.command + status.control + status.communications
            + status.computers + status.intelligence + status.surveillance) / 6.0;
        assert!((status.overall - expected).abs() < 0.001);
    }
}
