use async_trait::async_trait;
use athena_types::AthenaError;
use reqwest::Client;
use serde_json::{json, Value};
use dashmap::DashMap;
use std::sync::Arc;
use crate::{McpClient, McpToolResult, circuit_breaker::CircuitBreaker};

// AD technique→MCP tool routing table (ported from v1 engine_router.py)
static AD_TECHNIQUE_TO_MCP: &[(&str, &str)] = &[
    ("T1046",  "nmap"),
    ("T1190",  "web-scanner"),
    ("T1059.003", "shell"),
    ("T1059.004", "shell"),
    ("T1078",  "credential-check"),
    ("T1110",  "brute-force"),
    ("T1083",  "file-enum"),
    ("T1082",  "sysinfo"),
    ("T1016",  "net-enum"),
    ("T1033",  "user-enum"),
    ("T1135",  "smb-enum"),
    ("T1201",  "policy-enum"),
    ("T1003",  "credential-dump"),
    ("T1018",  "host-discovery"),
    ("T1049",  "conn-enum"),
    ("T1069",  "group-enum"),
    ("T1087",  "account-enum"),
    ("T1210",  "exploit-check"),
    ("T1595",  "recon"),
    ("T1592",  "osint"),
];

pub struct HttpMcpClient {
    client: Client,
    base_url: String,
    tools: Vec<String>,
    breakers: Arc<DashMap<String, CircuitBreaker>>,
    failure_threshold: u32,
    recovery_timeout_secs: u64,
}

impl HttpMcpClient {
    pub fn new(base_url: impl Into<String>, tools: Vec<String>) -> Self {
        let client = Client::builder()
            .connect_timeout(std::time::Duration::from_secs(3))
            .timeout(std::time::Duration::from_secs(10))
            .build()
            .unwrap_or_default();
        Self {
            client,
            base_url: base_url.into(),
            tools,
            breakers: Arc::new(DashMap::new()),
            failure_threshold: 5,
            recovery_timeout_secs: 30,
        }
    }

    pub fn with_circuit_breaker_config(mut self, failure_threshold: u32, recovery_timeout_secs: u64) -> Self {
        self.failure_threshold = failure_threshold;
        self.recovery_timeout_secs = recovery_timeout_secs;
        self
    }

    fn breaker_for(&self, tool: &str) -> dashmap::mapref::one::RefMut<'_, String, CircuitBreaker> {
        self.breakers
            .entry(tool.to_string())
            .or_insert_with(|| CircuitBreaker::new(self.failure_threshold, self.recovery_timeout_secs))
    }

    pub fn technique_to_tool(technique_id: &str) -> Option<&'static str> {
        AD_TECHNIQUE_TO_MCP.iter()
            .find(|(t, _)| *t == technique_id)
            .map(|(_, tool)| *tool)
    }
}

#[async_trait]
impl McpClient for HttpMcpClient {
    async fn call(&self, tool: &str, params: Value) -> Result<McpToolResult, AthenaError> {
        {
            let breaker = self.breaker_for(tool);
            if breaker.is_open() {
                return Err(AthenaError::McpError(format!(
                    "Circuit breaker OPEN for tool '{tool}' — fast fail"
                )));
            }
        }

        let url = format!("{}/tools/{}/call", self.base_url, tool);
        let body = json!({ "params": params });

        let resp = self.client
            .post(&url)
            .header("content-type", "application/json")
            .json(&body)
            .send()
            .await;

        match resp {
            Err(e) => {
                self.breaker_for(tool).record_failure();
                Err(AthenaError::McpError(format!("HTTP error calling {tool}: {e}")))
            }
            Ok(r) if !r.status().is_success() => {
                self.breaker_for(tool).record_failure();
                let status = r.status();
                let text = r.text().await.unwrap_or_default();
                Err(AthenaError::McpError(format!("Tool {tool} returned {status}: {text}")))
            }
            Ok(r) => {
                let output: Value = r.json().await
                    .map_err(|e| AthenaError::McpError(format!("parse error from {tool}: {e}")))?;
                self.breaker_for(tool).record_success();
                Ok(McpToolResult {
                    tool: tool.to_string(),
                    output,
                    success: true,
                    error: None,
                })
            }
        }
    }

    async fn health_check(&self, tool: &str) -> bool {
        let url = format!("{}/tools/{}/health", self.base_url, tool);
        match self.client.get(&url).send().await {
            Ok(r) => r.status().is_success(),
            Err(_) => false,
        }
    }

    fn available_tools(&self) -> Vec<String> {
        self.tools.clone()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn technique_to_tool_known() {
        assert_eq!(HttpMcpClient::technique_to_tool("T1046"), Some("nmap"));
        assert_eq!(HttpMcpClient::technique_to_tool("T1190"), Some("web-scanner"));
        assert_eq!(HttpMcpClient::technique_to_tool("T1003"), Some("credential-dump"));
    }

    #[test]
    fn technique_to_tool_unknown() {
        assert_eq!(HttpMcpClient::technique_to_tool("T9999"), None);
    }

    #[test]
    fn circuit_breaker_blocks_after_threshold() {
        let client = HttpMcpClient::new("http://localhost:9999", vec!["nmap".into()])
            .with_circuit_breaker_config(2, 60);
        // Manually trip the breaker
        {
            let mut b = client.breaker_for("nmap");
            b.record_failure();
            b.record_failure();
        }
        assert!(client.breaker_for("nmap").is_open());
    }

    #[test]
    fn ad_routing_table_covers_all_entries() {
        // Ensure no duplicate technique IDs
        let mut seen = std::collections::HashSet::new();
        for (t, _) in AD_TECHNIQUE_TO_MCP {
            assert!(seen.insert(*t), "Duplicate technique in routing table: {t}");
        }
        assert!(AD_TECHNIQUE_TO_MCP.len() >= 10);
    }
}
