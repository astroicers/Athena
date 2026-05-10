use async_trait::async_trait;
use athena_types::{Fact, FactTrait, FactValue, OperationId, AthenaError};
use athena_mcp_client::McpToolResult;
use uuid::Uuid;
use chrono::Utc;

#[async_trait]
pub trait FactExtractor: Send + Sync {
    async fn extract(&self, result: &McpToolResult, op_id: &OperationId) -> Result<Vec<Fact>, AthenaError>;
}

pub struct McpFactExtractor;

impl McpFactExtractor {
    pub fn new() -> Self { Self }
}

impl Default for McpFactExtractor {
    fn default() -> Self { Self::new() }
}

#[async_trait]
impl FactExtractor for McpFactExtractor {
    async fn extract(&self, result: &McpToolResult, op_id: &OperationId) -> Result<Vec<Fact>, AthenaError> {
        if !result.success {
            return Ok(vec![]);
        }
        let source = result.tool.clone();
        extract_facts_from_output(op_id, &result.output, &source)
    }
}

fn make_fact(op_id: &OperationId, trait_name: &str, value: impl Into<String>, source: &str, confidence: u8) -> Fact {
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

/// Map trait name prefix → confidence score.
fn trait_confidence(trait_name: &str) -> u8 {
    if trait_name.starts_with("service.open_port") { return 90; }
    if trait_name.starts_with("network.host.ip")   { return 95; }
    if trait_name.starts_with("host.os")            { return 75; }
    if trait_name.starts_with("web.vuln")           { return 80; }
    if trait_name.starts_with("access.")            { return 95; }
    70
}

fn extract_facts_from_output(op_id: &OperationId, output: &serde_json::Value, source: &str) -> Result<Vec<Fact>, AthenaError> {
    let mut facts = Vec::new();

    // ── New format: {"facts": [{"trait": "...", "value": "..."}]} ─────────────
    // FastMCP containers return this format; take it first when present.
    if let Some(facts_arr) = output.get("facts").and_then(|v| v.as_array()) {
        for f in facts_arr {
            let trait_name = f.get("trait").and_then(|v| v.as_str()).unwrap_or("unknown");
            let value = f.get("value").and_then(|v| v.as_str()).unwrap_or("");
            let confidence = trait_confidence(trait_name);
            facts.push(make_fact(op_id, trait_name, value, source, confidence));
        }
        return Ok(facts);
    }

    // ── Legacy format fallback (used by internal mocks and older callers) ─────

    // nmap / T1046: open_ports array
    if let Some(ports) = output.get("open_ports").and_then(|v| v.as_array()) {
        for p in ports {
            if let Some(port) = p.as_str().or_else(|| {
                // numeric port — leak a &str via Box to satisfy lifetime
                p.as_u64().map(|n| -> &str {
                    Box::leak(n.to_string().into_boxed_str())
                })
            }) {
                facts.push(make_fact(op_id, "open_port", port, source, 90));
            }
        }
    }

    // sysinfo / T1082
    if let Some(os) = output.get("os").and_then(|v| v.as_str()) {
        facts.push(make_fact(op_id, "os", os, source, 85));
    }
    if let Some(hostname) = output.get("hostname").and_then(|v| v.as_str()) {
        facts.push(make_fact(op_id, "hostname", hostname, source, 95));
    }
    if let Some(kernel) = output.get("kernel").and_then(|v| v.as_str()) {
        facts.push(make_fact(op_id, "kernel_version", kernel, source, 85));
    }

    // user-enum / T1033
    if let Some(users) = output.get("users").and_then(|v| v.as_array()) {
        for u in users {
            if let Some(user) = u.as_str() {
                facts.push(make_fact(op_id, "local_user", user, source, 80));
            }
        }
    }

    // credential-check / T1078
    if let Some(creds) = output.get("valid_credentials").and_then(|v| v.as_array()) {
        for c in creds {
            if let Some(cred) = c.as_str() {
                facts.push(make_fact(op_id, "valid_credential", cred, source, 95));
            }
        }
    }

    // net-enum / T1016
    if let Some(segs) = output.get("network_segments").and_then(|v| v.as_array()) {
        for s in segs {
            if let Some(seg) = s.as_str() {
                facts.push(make_fact(op_id, "network_segment", seg, source, 75));
            }
        }
    }

    // host-discovery / T1018
    if let Some(hosts) = output.get("live_hosts").and_then(|v| v.as_array()) {
        for h in hosts {
            if let Some(host) = h.as_str() {
                facts.push(make_fact(op_id, "live_host", host, source, 85));
            }
        }
    }

    // Generic vulnerabilities
    if let Some(vulns) = output.get("vulnerabilities").and_then(|v| v.as_array()) {
        for v in vulns {
            if let Some(cve) = v.as_str() {
                facts.push(make_fact(op_id, "vulnerability", cve, source, 70));
            }
        }
    }

    Ok(facts)
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    fn result(tool: &str, output: serde_json::Value) -> McpToolResult {
        McpToolResult { tool: tool.into(), output, success: true, error: None }
    }

    // ── Legacy format tests (preserved) ──────────────────────────────────────

    #[tokio::test]
    async fn extracts_open_ports() {
        let extractor = McpFactExtractor::new();
        let op_id = OperationId::new();
        let r = result("nmap", json!({ "open_ports": ["22", "80", "443"] }));
        let facts = extractor.extract(&r, &op_id).await.unwrap();
        assert_eq!(facts.len(), 3);
        assert!(facts.iter().all(|f| f.trait_name.0 == "open_port"));
        assert_eq!(facts[0].source, "nmap");
        assert_eq!(facts[0].confidence, 90);
    }

    #[tokio::test]
    async fn extracts_sysinfo_facts() {
        let extractor = McpFactExtractor::new();
        let op_id = OperationId::new();
        let r = result("sysinfo", json!({
            "os": "Linux",
            "hostname": "target01",
            "kernel": "5.15.0"
        }));
        let facts = extractor.extract(&r, &op_id).await.unwrap();
        assert_eq!(facts.len(), 3);
        let trait_names: Vec<&str> = facts.iter().map(|f| f.trait_name.0.as_str()).collect();
        assert!(trait_names.contains(&"os"));
        assert!(trait_names.contains(&"hostname"));
        assert!(trait_names.contains(&"kernel_version"));
    }

    #[tokio::test]
    async fn failed_result_returns_empty() {
        let extractor = McpFactExtractor::new();
        let op_id = OperationId::new();
        let r = McpToolResult {
            tool: "nmap".into(),
            output: json!({}),
            success: false,
            error: Some("timeout".into()),
        };
        let facts = extractor.extract(&r, &op_id).await.unwrap();
        assert!(facts.is_empty());
    }

    #[tokio::test]
    async fn extracts_credentials() {
        let extractor = McpFactExtractor::new();
        let op_id = OperationId::new();
        let r = result("credential-check", json!({ "valid_credentials": ["admin:admin123"] }));
        let facts = extractor.extract(&r, &op_id).await.unwrap();
        assert_eq!(facts.len(), 1);
        assert_eq!(facts[0].trait_name.0, "valid_credential");
        assert_eq!(facts[0].confidence, 95);
    }

    #[tokio::test]
    async fn extracts_live_hosts() {
        let extractor = McpFactExtractor::new();
        let op_id = OperationId::new();
        let r = result("host-discovery", json!({ "live_hosts": ["10.0.0.1", "10.0.0.5"] }));
        let facts = extractor.extract(&r, &op_id).await.unwrap();
        assert_eq!(facts.len(), 2);
        assert!(facts.iter().all(|f| f.trait_name.0 == "live_host"));
    }

    // ── New FastMCP format tests ──────────────────────────────────────────────

    #[tokio::test]
    async fn new_format_extracts_facts_array() {
        let extractor = McpFactExtractor::new();
        let op_id = OperationId::new();
        let r = result("nmap", json!({
            "facts": [
                {"trait": "service.open_port", "value": "22/tcp/ssh/unknown"},
                {"trait": "service.open_port", "value": "80/tcp/http/nginx"},
                {"trait": "network.host.ip",   "value": "192.168.0.28"}
            ],
            "raw_output": "Nmap scan report..."
        }));
        let facts = extractor.extract(&r, &op_id).await.unwrap();
        assert_eq!(facts.len(), 3);
        assert!(facts.iter().any(|f| f.trait_name.0 == "service.open_port"));
        assert!(facts.iter().any(|f| f.trait_name.0 == "network.host.ip"));
    }

    #[tokio::test]
    async fn new_format_confidence_by_trait_prefix() {
        let extractor = McpFactExtractor::new();
        let op_id = OperationId::new();
        let r = result("nmap", json!({
            "facts": [
                {"trait": "service.open_port", "value": "443/tcp/https"},
                {"trait": "network.host.ip",   "value": "10.0.0.1"},
                {"trait": "host.os",            "value": "Linux"},
                {"trait": "web.vuln.xss",       "value": "/search?q=<script>"},
                {"trait": "access.credential",  "value": "root:toor"},
                {"trait": "custom.trait",       "value": "something"}
            ]
        }));
        let facts = extractor.extract(&r, &op_id).await.unwrap();
        let by_trait: std::collections::HashMap<&str, u8> = facts.iter()
            .map(|f| (f.trait_name.0.as_str(), f.confidence))
            .collect();
        assert_eq!(by_trait["service.open_port"], 90);
        assert_eq!(by_trait["network.host.ip"],   95);
        assert_eq!(by_trait["host.os"],            75);
        assert_eq!(by_trait["web.vuln.xss"],       80);
        assert_eq!(by_trait["access.credential"],  95);
        assert_eq!(by_trait["custom.trait"],       70);
    }

    #[tokio::test]
    async fn new_format_takes_priority_over_legacy() {
        let extractor = McpFactExtractor::new();
        let op_id = OperationId::new();
        // Both new and legacy keys present — new format must win
        let r = result("nmap", json!({
            "facts": [{"trait": "service.open_port", "value": "22/tcp/ssh"}],
            "open_ports": ["22", "80", "443"]
        }));
        let facts = extractor.extract(&r, &op_id).await.unwrap();
        // Only 1 fact from new format, not 3 from legacy
        assert_eq!(facts.len(), 1);
        assert_eq!(facts[0].trait_name.0, "service.open_port");
    }
}
