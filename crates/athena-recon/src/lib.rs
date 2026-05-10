use async_trait::async_trait;
use std::sync::Arc;
use athena_types::{Target, Fact, FactTrait, FactValue, OperationId, AthenaError};
use athena_mcp_client::McpClient;
use uuid::Uuid;
use chrono::Utc;

#[async_trait]
pub trait ReconEngine: Send + Sync {
    async fn recon(&self, op_id: &OperationId, target: &Target) -> Result<Vec<Fact>, AthenaError>;
}

pub struct McpReconEngine {
    mcp: Arc<dyn McpClient>,
}

impl McpReconEngine {
    pub fn new(mcp: Arc<dyn McpClient>) -> Self {
        Self { mcp }
    }

    fn target_addr(target: &Target) -> Option<String> {
        if let Some(ref h) = target.hostname { return Some(h.clone()); }
        if let Some(ref ip) = target.ip { return Some(ip.ip().to_string()); }
        None
    }
}

#[async_trait]
impl ReconEngine for McpReconEngine {
    async fn recon(&self, op_id: &OperationId, target: &Target) -> Result<Vec<Fact>, AthenaError> {
        let addr = Self::target_addr(target)
            .ok_or_else(|| AthenaError::ExecutionFailed("Target has no address".into()))?;

        // Run sequential recon tools: host-discovery → nmap → sysinfo → user-enum
        let recon_sequence = ["host-discovery", "nmap", "sysinfo", "user-enum"];
        let mut all_facts = Vec::new();
        let source = "recon";

        for tool in &recon_sequence {
            if !self.mcp.health_check(tool).await {
                tracing::debug!(tool, "recon tool unhealthy, skipping");
                continue;
            }

            // FastMCP functions take only target-related args, not op_id
            let params = serde_json::json!({ "target": addr });

            match self.mcp.call(tool, params).await {
                Ok(result) if result.success => {
                    let facts = extract_recon_facts(op_id, &result.output, source, tool);
                    all_facts.extend(facts);
                }
                Ok(result) => {
                    tracing::warn!(tool, error = ?result.error, "recon tool returned failure");
                }
                Err(e) => {
                    tracing::warn!(tool, error = %e, "recon tool call failed");
                }
            }
        }

        Ok(all_facts)
    }
}

fn make_text_fact(op_id: &OperationId, trait_name: &str, value: impl Into<String>, source: &str, confidence: u8) -> Fact {
    Fact {
        id: Uuid::new_v4(),
        op_id: op_id.clone(),
        trait_name: FactTrait(trait_name.into()),
        value: FactValue::Text(value.into()),
        source: source.into(),
        confidence,
        collected_at: Utc::now(),
    }
}

fn extract_recon_facts(op_id: &OperationId, output: &serde_json::Value, source: &str, tool: &str) -> Vec<Fact> {
    let mut facts = Vec::new();
    match tool {
        "host-discovery" => {
            if let Some(hosts) = output.get("live_hosts").and_then(|v| v.as_array()) {
                for h in hosts {
                    if let Some(ip) = h.as_str() {
                        facts.push(make_text_fact(op_id, "live_host", ip, source, 85));
                    }
                }
            }
        }
        "nmap" => {
            if let Some(ports) = output.get("open_ports").and_then(|v| v.as_array()) {
                for p in ports {
                    if let Some(port) = p.as_str() {
                        facts.push(make_text_fact(op_id, "open_port", port, source, 90));
                    }
                }
            }
            if let Some(services) = output.get("services").and_then(|v| v.as_array()) {
                for s in services {
                    if let Some(svc) = s.as_str() {
                        facts.push(make_text_fact(op_id, "service", svc, source, 80));
                    }
                }
            }
        }
        "sysinfo" => {
            for (key, trait_name) in [("os", "os"), ("hostname", "hostname"), ("kernel", "kernel_version")] {
                if let Some(v) = output.get(key).and_then(|v| v.as_str()) {
                    facts.push(make_text_fact(op_id, trait_name, v, source, 85));
                }
            }
        }
        "user-enum" => {
            if let Some(users) = output.get("users").and_then(|v| v.as_array()) {
                for u in users {
                    if let Some(user) = u.as_str() {
                        facts.push(make_text_fact(op_id, "local_user", user, source, 80));
                    }
                }
            }
        }
        _ => {}
    }
    facts
}

#[cfg(test)]
mod tests {
    use super::*;
    use athena_mcp_client::{McpClient, McpToolResult};
    use athena_types::TargetId;
    use serde_json::json;
    use std::collections::HashMap;

    struct MockMcp {
        responses: HashMap<String, serde_json::Value>,
    }

    #[async_trait]
    impl McpClient for MockMcp {
        async fn call(&self, tool: &str, _params: serde_json::Value) -> Result<McpToolResult, AthenaError> {
            let output = self.responses.get(tool).cloned().unwrap_or(json!({}));
            Ok(McpToolResult { tool: tool.into(), output, success: true, error: None })
        }
        async fn health_check(&self, tool: &str) -> bool {
            self.responses.contains_key(tool)
        }
        fn available_tools(&self) -> Vec<String> {
            self.responses.keys().cloned().collect()
        }
    }

    fn target_with_ip(ip: &str) -> Target {
        Target {
            id: TargetId::new(),
            hostname: None,
            ip: Some(ip.parse().unwrap()),
            os: None,
            tags: vec![],
        }
    }

    #[tokio::test]
    async fn recon_collects_facts_from_all_healthy_tools() {
        let mut responses = HashMap::new();
        responses.insert("host-discovery".into(), json!({ "live_hosts": ["10.0.0.1"] }));
        responses.insert("nmap".into(), json!({ "open_ports": ["22", "80"] }));
        responses.insert("sysinfo".into(), json!({ "os": "Linux", "hostname": "victim" }));
        responses.insert("user-enum".into(), json!({ "users": ["root", "admin"] }));

        let mcp = Arc::new(MockMcp { responses });
        let engine = McpReconEngine::new(mcp);
        let op_id = OperationId::new();
        let target = target_with_ip("10.0.0.1/32");

        let facts = engine.recon(&op_id, &target).await.unwrap();
        // 1 live_host + 2 open_ports + 2 sysinfo + 2 users = 7
        assert_eq!(facts.len(), 7);
    }

    #[tokio::test]
    async fn recon_skips_unhealthy_tools() {
        let mut responses = HashMap::new();
        responses.insert("nmap".into(), json!({ "open_ports": ["443"] }));
        // host-discovery, sysinfo, user-enum NOT in map → health_check returns false

        let mcp = Arc::new(MockMcp { responses });
        let engine = McpReconEngine::new(mcp);
        let op_id = OperationId::new();
        let target = target_with_ip("10.0.0.1/32");

        let facts = engine.recon(&op_id, &target).await.unwrap();
        assert_eq!(facts.len(), 1);
        assert_eq!(facts[0].trait_name.0, "open_port");
    }

    #[tokio::test]
    async fn recon_fails_without_target_address() {
        let mcp = Arc::new(MockMcp { responses: HashMap::new() });
        let engine = McpReconEngine::new(mcp);
        let op_id = OperationId::new();
        let target = Target { id: TargetId::new(), hostname: None, ip: None, os: None, tags: vec![] };
        assert!(engine.recon(&op_id, &target).await.is_err());
    }
}
