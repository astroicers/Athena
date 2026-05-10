use async_trait::async_trait;
use std::sync::Arc;
use athena_types::{Fact, FactTrait, FactValue, OperationId, AthenaError};
use athena_facts::FactRepository;
use athena_mcp_client::McpClient;

#[async_trait]
pub trait ObservePhase: Send + Sync {
    async fn collect(&self, op_id: &OperationId) -> Result<Vec<Fact>, AthenaError>;
    async fn summarize(&self, op_id: &OperationId) -> Result<String, AthenaError>;
}

pub struct DefaultObserver {
    fact_repo: Arc<dyn FactRepository>,
    mcp: Arc<dyn McpClient>,
}

impl DefaultObserver {
    pub fn new(fact_repo: Arc<dyn FactRepository>, mcp: Arc<dyn McpClient>) -> Self {
        Self { fact_repo, mcp }
    }
}

#[async_trait]
impl ObservePhase for DefaultObserver {
    async fn collect(&self, op_id: &OperationId) -> Result<Vec<Fact>, AthenaError> {
        // Read seed facts to determine scan target
        let existing = self.fact_repo.list(op_id).await.unwrap_or_default();
        let target_ip = existing.iter().find_map(|f| {
            if f.trait_name.0 == "target_ip" {
                if let FactValue::Text(ip) = &f.value { Some(ip.clone()) } else { None }
            } else {
                None
            }
        });

        // Only attempt nmap if we have a target
        if let Some(ref ip) = target_ip {
            // nmap_scan(target, ports) — no op_id in FastMCP function signature
            let params = serde_json::json!({ "target": ip });

            if self.mcp.health_check("nmap").await {
                let result = self.mcp.call("nmap", params).await?;
                if result.success {
                    let facts_to_insert = extract_nmap_facts(op_id, &result.output);
                    for fact in facts_to_insert {
                        self.fact_repo.insert(fact).await?;
                    }
                }
            }
        }

        self.fact_repo.list(op_id).await
    }

    async fn summarize(&self, op_id: &OperationId) -> Result<String, AthenaError> {
        let facts = self.fact_repo.list(op_id).await?;
        if facts.is_empty() {
            return Ok("No facts collected yet.".into());
        }

        let lines: Vec<String> = facts.iter().map(|f| {
            let val = match &f.value {
                FactValue::Text(s) => s.clone(),
                FactValue::Number(n) => n.to_string(),
                FactValue::Bool(b) => b.to_string(),
            };
            format!("[{}] {}: {} (confidence: {}%, source: {})",
                f.op_id, f.trait_name.0, val, f.confidence, f.source)
        }).collect();

        Ok(format!("Observation summary ({} facts):\n{}", facts.len(), lines.join("\n")))
    }
}

/// Extract open-port facts from nmap output, supporting both FastMCP and legacy formats.
fn extract_nmap_facts(op_id: &OperationId, output: &serde_json::Value) -> Vec<Fact> {
    let mut facts = Vec::new();

    // New FastMCP format: {"facts": [{"trait": "service.open_port", "value": "22/tcp/..."}]}
    if let Some(arr) = output.get("facts").and_then(|v| v.as_array()) {
        for f in arr {
            let trait_name = f.get("trait").and_then(|v| v.as_str()).unwrap_or("unknown");
            let value = f.get("value").and_then(|v| v.as_str()).unwrap_or("");
            let confidence: u8 = if trait_name.starts_with("network.host.ip") { 95 }
                else if trait_name.starts_with("service.open_port") { 90 }
                else { 75 };
            facts.push(Fact {
                id: uuid::Uuid::new_v4(),
                op_id: op_id.clone(),
                trait_name: FactTrait(trait_name.into()),
                value: FactValue::Text(value.into()),
                source: "nmap".into(),
                confidence,
                collected_at: chrono::Utc::now(),
            });
        }
        return facts;
    }

    // Legacy format: {"open_ports": ["22", "80"]}
    if let Some(ports) = output.get("open_ports").and_then(|v| v.as_array()) {
        for port in ports {
            if let Some(p) = port.as_str() {
                facts.push(Fact {
                    id: uuid::Uuid::new_v4(),
                    op_id: op_id.clone(),
                    trait_name: FactTrait("open_port".into()),
                    value: FactValue::Text(p.to_string()),
                    source: "nmap".into(),
                    confidence: 90,
                    collected_at: chrono::Utc::now(),
                });
            }
        }
    }
    facts
}

#[cfg(test)]
mod tests {
    use super::*;
    use athena_facts::InMemoryFactRepository;
    use athena_mcp_client::{McpToolResult};
    use serde_json::json;
    use uuid::Uuid;

    struct MockMcp { healthy: bool }

    #[async_trait]
    impl McpClient for MockMcp {
        async fn call(&self, tool: &str, _params: serde_json::Value) -> Result<McpToolResult, AthenaError> {
            Ok(McpToolResult {
                tool: tool.into(),
                output: json!({ "open_ports": ["22", "80", "443"] }),
                success: true,
                error: None,
            })
        }
        async fn health_check(&self, _tool: &str) -> bool { self.healthy }
        fn available_tools(&self) -> Vec<String> { vec!["nmap".into()] }
    }

    #[tokio::test]
    async fn collect_with_healthy_mcp_inserts_facts() {
        let repo = Arc::new(InMemoryFactRepository::new());
        let op_id = OperationId::new();

        // Seed target_ip so nmap is triggered
        repo.insert(Fact {
            id: Uuid::new_v4(),
            op_id: op_id.clone(),
            trait_name: FactTrait("target_ip".into()),
            value: FactValue::Text("10.0.0.1".into()),
            source: "api".into(),
            confidence: 100,
            collected_at: chrono::Utc::now(),
        }).await.unwrap();

        let mcp = Arc::new(MockMcp { healthy: true });
        let observer = DefaultObserver::new(repo.clone(), mcp);

        let facts = observer.collect(&op_id).await.unwrap();
        // seed fact (target_ip) + 3 open_port facts
        assert_eq!(facts.len(), 4);
        assert!(facts.iter().any(|f| f.trait_name.0 == "open_port"));
    }

    #[tokio::test]
    async fn collect_without_target_skips_nmap() {
        let repo = Arc::new(InMemoryFactRepository::new());
        let mcp = Arc::new(MockMcp { healthy: true });
        let observer = DefaultObserver::new(repo, mcp);
        let op_id = OperationId::new();

        // No target_ip seed — nmap should not be called even though MCP is healthy
        let facts = observer.collect(&op_id).await.unwrap();
        assert!(facts.is_empty());
    }

    #[tokio::test]
    async fn collect_with_unhealthy_mcp_returns_seed_only() {
        let repo = Arc::new(InMemoryFactRepository::new());
        let op_id = OperationId::new();
        repo.insert(Fact {
            id: Uuid::new_v4(),
            op_id: op_id.clone(),
            trait_name: FactTrait("target_ip".into()),
            value: FactValue::Text("10.0.0.1".into()),
            source: "api".into(),
            confidence: 100,
            collected_at: chrono::Utc::now(),
        }).await.unwrap();

        let mcp = Arc::new(MockMcp { healthy: false });
        let observer = DefaultObserver::new(repo, mcp);

        let facts = observer.collect(&op_id).await.unwrap();
        // Only the seed fact
        assert_eq!(facts.len(), 1);
        assert_eq!(facts[0].trait_name.0, "target_ip");
    }

    #[tokio::test]
    async fn summarize_with_no_facts() {
        let repo = Arc::new(InMemoryFactRepository::new());
        let mcp = Arc::new(MockMcp { healthy: false });
        let observer = DefaultObserver::new(repo, mcp);
        let op_id = OperationId::new();

        let summary = observer.summarize(&op_id).await.unwrap();
        assert_eq!(summary, "No facts collected yet.");
    }

    #[tokio::test]
    async fn summarize_formats_facts() {
        let repo = Arc::new(InMemoryFactRepository::new());
        let fact = Fact {
            id: Uuid::new_v4(),
            op_id: OperationId::new(),
            trait_name: FactTrait("os".into()),
            value: FactValue::Text("Linux".into()),
            source: "test".into(),
            confidence: 75,
            collected_at: chrono::Utc::now(),
        };
        let op_id = fact.op_id.clone();
        repo.insert(fact).await.unwrap();

        let mcp = Arc::new(MockMcp { healthy: false });
        let observer = DefaultObserver::new(repo, mcp);
        let summary = observer.summarize(&op_id).await.unwrap();
        assert!(summary.contains("os: Linux"));
        assert!(summary.contains("1 facts"));
    }
}
