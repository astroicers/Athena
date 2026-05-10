use async_trait::async_trait;
use std::sync::Arc;
use athena_types::{OperationId, AthenaError};
use athena_facts::FactRepository;
use athena_c5isr::C5isrMapper;

#[async_trait]
pub trait BriefGenerator: Send + Sync {
    async fn generate(&self, op_id: &OperationId) -> Result<String, AthenaError>;
}

pub struct FactBriefGenerator {
    fact_repo: Arc<dyn FactRepository>,
    c5isr: Arc<dyn C5isrMapper>,
}

impl FactBriefGenerator {
    pub fn new(fact_repo: Arc<dyn FactRepository>, c5isr: Arc<dyn C5isrMapper>) -> Self {
        Self { fact_repo, c5isr }
    }
}

#[async_trait]
impl BriefGenerator for FactBriefGenerator {
    async fn generate(&self, op_id: &OperationId) -> Result<String, AthenaError> {
        let facts = self.fact_repo.list(op_id).await?;
        let c5isr = self.c5isr.assess(op_id).await?;

        let mut sections = vec![
            format!("# Operational Brief — Op {op_id}\n"),
            format!("## C5ISR Status\n"),
            format!("- Command: {:.0}%", c5isr.command * 100.0),
            format!("- Control: {:.0}%", c5isr.control * 100.0),
            format!("- Communications: {:.0}%", c5isr.communications * 100.0),
            format!("- Computers: {:.0}%", c5isr.computers * 100.0),
            format!("- Intelligence: {:.0}%", c5isr.intelligence * 100.0),
            format!("- Surveillance: {:.0}%", c5isr.surveillance * 100.0),
            format!("- **Overall: {:.0}%**\n", c5isr.overall * 100.0),
            format!("## Collected Facts ({} total)\n", facts.len()),
        ];

        // Group facts by trait_name
        let mut by_trait: std::collections::BTreeMap<String, Vec<String>> = Default::default();
        for fact in &facts {
            let val = match &fact.value {
                athena_types::FactValue::Text(s) => s.clone(),
                athena_types::FactValue::Number(n) => n.to_string(),
                athena_types::FactValue::Bool(b) => b.to_string(),
            };
            by_trait.entry(fact.trait_name.0.clone()).or_default().push(val);
        }

        for (trait_name, values) in &by_trait {
            sections.push(format!("### {trait_name}"));
            for v in values {
                sections.push(format!("- {v}"));
            }
            sections.push(String::new());
        }

        Ok(sections.join("\n"))
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use athena_facts::InMemoryFactRepository;
    use athena_c5isr::{C5isrStatus, C5isrMapper};
    use athena_types::{Fact, FactTrait, FactValue};
    use uuid::Uuid;
    use chrono::Utc;

    struct MockC5isr;
    #[async_trait]
    impl C5isrMapper for MockC5isr {
        async fn assess(&self, _op_id: &OperationId) -> Result<C5isrStatus, AthenaError> {
            Ok(C5isrStatus {
                command: 0.8, control: 0.6, communications: 0.7,
                computers: 0.9, intelligence: 0.5, surveillance: 0.4,
                overall: 0.65,
            })
        }
    }

    #[tokio::test]
    async fn brief_contains_c5isr_and_facts() {
        let repo = Arc::new(InMemoryFactRepository::new());
        let op_id = OperationId::new();
        repo.insert(Fact {
            id: Uuid::new_v4(),
            op_id: op_id.clone(),
            trait_name: FactTrait("open_port".into()),
            value: FactValue::Text("22".into()),
            source: "test".into(),
            confidence: 90,
            collected_at: Utc::now(),
        }).await.unwrap();

        let generator = FactBriefGenerator::new(repo, Arc::new(MockC5isr));
        let brief = generator.generate(&op_id).await.unwrap();

        assert!(brief.contains("C5ISR"));
        assert!(brief.contains("open_port"));
        assert!(brief.contains("65%"));
    }

    #[tokio::test]
    async fn brief_with_no_facts() {
        let repo = Arc::new(InMemoryFactRepository::new());
        let generator = FactBriefGenerator::new(repo, Arc::new(MockC5isr));
        let op_id = OperationId::new();
        let brief = generator.generate(&op_id).await.unwrap();
        assert!(brief.contains("0 total"));
    }
}
