use async_trait::async_trait;
use athena_types::AthenaError;
use reqwest::Client;
use serde_json::{json, Value};
use dashmap::DashMap;
use std::collections::HashMap;
use std::sync::Arc;
use crate::{McpClient, McpToolResult, circuit_breaker::CircuitBreaker};

// AD technique→Athena logical tool name (preserved from v1 engine_router.py)
static AD_TECHNIQUE_TO_MCP: &[(&str, &str)] = &[
    ("T1046",     "nmap"),
    ("T1190",     "web-scanner"),
    ("T1059.003", "shell"),
    ("T1059.004", "shell"),
    ("T1078",     "credential-check"),
    ("T1110",     "brute-force"),
    ("T1083",     "file-enum"),
    ("T1082",     "sysinfo"),
    ("T1016",     "net-enum"),
    ("T1033",     "user-enum"),
    ("T1135",     "smb-enum"),
    ("T1201",     "policy-enum"),
    ("T1003",     "credential-dump"),
    ("T1018",     "host-discovery"),
    ("T1049",     "conn-enum"),
    ("T1069",     "group-enum"),
    ("T1087",     "account-enum"),
    ("T1210",     "exploit-check"),
    ("T1595",     "recon"),
    ("T1592",     "osint"),
];

// Athena logical tool name → FastMCP function name registered inside the container
static TOOL_NAME_MAP: &[(&str, &str)] = &[
    ("nmap",             "nmap_scan"),
    ("web-scanner",      "web_http_probe"),
    ("osint",            "crtsh_query"),
    ("privesc-check",    "privesc_scan"),
    ("lateral-move",     "lateral_move"),
    ("credential-dump",  "dump_credentials"),
    ("netexec",          "netexec_run"),
    ("host-discovery",   "host_discovery"),
    ("sysinfo",          "sysinfo"),
    ("user-enum",        "user_enum"),
    ("net-enum",         "net_enum"),
    ("smb-enum",         "smb_enum"),
    ("credential-check", "credential_check"),
    ("brute-force",      "brute_force"),
    ("file-enum",        "file_enum"),
    ("account-enum",     "account_enum"),
    ("group-enum",       "group_enum"),
    ("conn-enum",        "conn_enum"),
    ("exploit-check",    "exploit_check"),
    ("policy-enum",      "policy_enum"),
    ("recon",            "recon"),
    ("shell",            "shell_exec"),
];

// Default per-tool base URLs when not overridden via config
static DEFAULT_TOOL_PORTS: &[(&str, u16)] = &[
    ("nmap",             9101),
    ("web-scanner",      9102),
    ("osint",            9103),
    ("privesc-check",    9104),
    ("lateral-move",     9105),
    ("credential-dump",  9106),
    ("netexec",          9107),
    ("host-discovery",   9108),
    ("sysinfo",          9109),
    ("user-enum",        9110),
];

/// MCP StreamableHTTP client — implements the standard MCP JSON-RPC protocol.
///
/// Each tool runs in its own container on a dedicated port. Requests go to
/// `POST {tool_url}/mcp` with Accept: application/json, text/event-stream.
/// A session is established per-tool on first use via the MCP `initialize`
/// handshake; the returned `mcp-session-id` header is reused for all
/// subsequent calls to that tool.
pub struct StreamableMcpClient {
    client: Client,
    /// Logical tool name → base URL (e.g. "nmap" → "http://localhost:9101")
    tool_urls: HashMap<String, String>,
    /// Cached session IDs per tool, populated lazily on first call.
    sessions: Arc<DashMap<String, String>>,
    breakers: Arc<DashMap<String, CircuitBreaker>>,
    failure_threshold: u32,
    recovery_timeout_secs: u64,
}

impl StreamableMcpClient {
    /// Build with a custom tool→URL map (from config).
    pub fn new(tool_urls: HashMap<String, String>) -> Self {
        let client = Client::builder()
            .connect_timeout(std::time::Duration::from_secs(3))
            .timeout(std::time::Duration::from_secs(30))
            // Disable connection pooling: FastMCP containers are long-lived but
            // idle TCP connections get silently dropped after minutes, causing
            // "error decoding response body" on the next reuse.
            .pool_max_idle_per_host(0)
            .build()
            .unwrap_or_default();
        Self {
            client,
            tool_urls,
            sessions: Arc::new(DashMap::new()),
            breakers: Arc::new(DashMap::new()),
            failure_threshold: 5,
            recovery_timeout_secs: 30,
        }
    }

    /// Build with defaults: all tools on the given host with well-known ports.
    pub fn with_defaults(host: &str) -> Self {
        Self::new(Self::default_tool_urls(host))
    }

    /// Return the default tool→URL map for a given host (used by main.rs).
    pub fn default_tool_urls(host: &str) -> HashMap<String, String> {
        DEFAULT_TOOL_PORTS.iter()
            .map(|(name, port)| (name.to_string(), format!("http://{}:{}", host, port)))
            .collect()
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

    fn tool_url(&self, tool: &str) -> Option<&str> {
        self.tool_urls.get(tool).map(String::as_str)
    }

    /// Resolve Athena logical name ("nmap") → FastMCP function name ("nmap_scan").
    fn mcp_function_name(tool: &str) -> &str {
        TOOL_NAME_MAP.iter()
            .find(|(t, _)| *t == tool)
            .map(|(_, f)| *f)
            .unwrap_or(tool)
    }

    pub fn technique_to_tool(technique_id: &str) -> Option<&'static str> {
        AD_TECHNIQUE_TO_MCP.iter()
            .find(|(t, _)| *t == technique_id)
            .map(|(_, tool)| *tool)
    }

    /// Get cached session ID for a tool, or negotiate a new one via `initialize`.
    async fn get_or_create_session(&self, tool: &str, base_url: &str) -> Result<String, AthenaError> {
        // Fast path: session already cached
        if let Some(sid) = self.sessions.get(tool) {
            return Ok(sid.clone());
        }

        let url = format!("{}/mcp", base_url);
        let body = json!({
            "jsonrpc": "2.0",
            "id": 0,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "athena", "version": "2.0"}
            }
        });

        let resp = self.client
            .post(&url)
            .header("Accept", "application/json, text/event-stream")
            .header("Content-Type", "application/json")
            .json(&body)
            .send()
            .await
            .map_err(|e| AthenaError::McpError(format!("initialize failed for {tool}: {e}")))?;

        let session_id = resp
            .headers()
            .get("mcp-session-id")
            .and_then(|v| v.to_str().ok())
            .map(str::to_owned)
            .ok_or_else(|| AthenaError::McpError(format!("No mcp-session-id from {tool}")))?;

        self.sessions.insert(tool.to_string(), session_id.clone());
        tracing::debug!(tool, session_id, "MCP session established");
        Ok(session_id)
    }

    /// Parse a body that may be either plain JSON or an SSE stream.
    ///
    /// FastMCP returns `text/event-stream` with:
    ///   `: ping - ...\n\nevent: message\ndata: {...json...}\n\n`
    /// We find the last `data: ` line and parse its JSON payload.
    fn parse_sse_or_json(body: &str) -> Result<Value, serde_json::Error> {
        // Look for the last `data: ` line (SSE format)
        let json_str = body.lines()
            .filter(|l| l.starts_with("data: "))
            .last()
            .map(|l| &l["data: ".len()..])
            .unwrap_or(body.trim());
        serde_json::from_str(json_str)
    }

    /// Parse MCP JSON-RPC response envelope and unwrap the inner content.
    ///
    /// FastMCP wraps tool output as:
    /// {"result": {"content": [{"type": "text", "text": "<JSON string>"}]}}
    fn unwrap_mcp_response(resp: &Value) -> Result<Value, AthenaError> {
        // Check for JSON-RPC error
        if let Some(err) = resp.get("error") {
            let msg = err.get("message").and_then(|m| m.as_str()).unwrap_or("unknown MCP error");
            return Err(AthenaError::McpError(msg.to_string()));
        }

        let content = resp
            .get("result")
            .and_then(|r| r.get("content"))
            .and_then(|c| c.as_array())
            .and_then(|arr| arr.first())
            .ok_or_else(|| AthenaError::McpError("MCP response missing result.content[0]".into()))?;

        // Content item may be {"type":"text","text":"<json>"} or direct object
        if let Some(text) = content.get("text").and_then(|t| t.as_str()) {
            // Inner text may itself be a JSON string
            serde_json::from_str(text).or_else(|_| {
                // Plain text — wrap in {"output": text} for uniform downstream handling
                Ok(json!({"output": text}))
            })
        } else {
            Ok(content.clone())
        }
    }
}

#[async_trait]
impl McpClient for StreamableMcpClient {
    async fn call(&self, tool: &str, params: Value) -> Result<McpToolResult, AthenaError> {
        {
            let breaker = self.breaker_for(tool);
            if breaker.is_open() {
                return Err(AthenaError::McpError(format!(
                    "Circuit breaker OPEN for tool '{tool}' — fast fail"
                )));
            }
        }

        let base_url = self.tool_url(tool).ok_or_else(|| {
            AthenaError::McpError(format!("No URL configured for tool '{tool}'"))
        })?.to_string();
        let url = format!("{}/mcp", base_url);
        let fn_name = Self::mcp_function_name(tool);

        // Establish (or retrieve cached) MCP session
        let session_id = self.get_or_create_session(tool, &base_url).await
            .map_err(|e| {
                self.breaker_for(tool).record_failure();
                e
            })?;

        let body = json!({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": fn_name,
                "arguments": params,
            }
        });

        let resp = self.client
            .post(&url)
            .header("Accept", "application/json, text/event-stream")
            .header("Content-Type", "application/json")
            .header("mcp-session-id", &session_id)
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
                // FastMCP returns text/event-stream even for single responses.
                // Parse as text and extract the JSON from the `data: ` line.
                let body_text = r.text().await
                    .map_err(|e| AthenaError::McpError(format!("read error from {tool}: {e}")))?;

                let mcp_resp: Value = Self::parse_sse_or_json(&body_text)
                    .map_err(|e| {
                        self.breaker_for(tool).record_failure();
                        AthenaError::McpError(format!("parse error from {tool}: {e}"))
                    })?;

                match Self::unwrap_mcp_response(&mcp_resp) {
                    Ok(output) => {
                        self.breaker_for(tool).record_success();
                        Ok(McpToolResult {
                            tool: tool.to_string(),
                            output,
                            success: true,
                            error: None,
                        })
                    }
                    Err(e) => {
                        self.breaker_for(tool).record_failure();
                        Err(e)
                    }
                }
            }
        }
    }

    async fn health_check(&self, tool: &str) -> bool {
        let base_url = match self.tool_url(tool) {
            Some(u) => u.to_string(),
            None => return false,
        };
        // Reuse existing session or negotiate a new one
        self.get_or_create_session(tool, &base_url).await.is_ok()
    }

    fn available_tools(&self) -> Vec<String> {
        self.tool_urls.keys().cloned().collect()
    }
}

// Keep HttpMcpClient as a type alias so existing tests that reference it still compile
pub use StreamableMcpClient as HttpMcpClient;

#[cfg(test)]
mod tests {
    use super::*;

    fn client_with_defaults() -> StreamableMcpClient {
        StreamableMcpClient::with_defaults("localhost")
    }

    #[test]
    fn technique_to_tool_known() {
        assert_eq!(StreamableMcpClient::technique_to_tool("T1046"), Some("nmap"));
        assert_eq!(StreamableMcpClient::technique_to_tool("T1190"), Some("web-scanner"));
        assert_eq!(StreamableMcpClient::technique_to_tool("T1003"), Some("credential-dump"));
    }

    #[test]
    fn technique_to_tool_unknown() {
        assert_eq!(StreamableMcpClient::technique_to_tool("T9999"), None);
    }

    #[test]
    fn mcp_function_name_resolves() {
        assert_eq!(StreamableMcpClient::mcp_function_name("nmap"), "nmap_scan");
        assert_eq!(StreamableMcpClient::mcp_function_name("web-scanner"), "web_http_probe");
        assert_eq!(StreamableMcpClient::mcp_function_name("osint"), "crtsh_query");
        // Unknown tool falls back to the tool name itself
        assert_eq!(StreamableMcpClient::mcp_function_name("custom-tool"), "custom-tool");
    }

    #[test]
    fn circuit_breaker_blocks_after_threshold() {
        let client = client_with_defaults()
            .with_circuit_breaker_config(2, 60);
        {
            let mut b = client.breaker_for("nmap");
            b.record_failure();
            b.record_failure();
        }
        assert!(client.breaker_for("nmap").is_open());
    }

    #[test]
    fn ad_routing_table_covers_all_entries() {
        let mut seen = std::collections::HashSet::new();
        for (t, _) in AD_TECHNIQUE_TO_MCP {
            assert!(seen.insert(*t), "Duplicate technique in routing table: {t}");
        }
        assert!(AD_TECHNIQUE_TO_MCP.len() >= 10);
    }

    #[test]
    fn tool_url_returns_none_for_unknown() {
        let client = StreamableMcpClient::new(HashMap::new());
        assert!(client.tool_url("unknown-tool").is_none());
    }

    #[test]
    fn unwrap_mcp_response_parses_text_content() {
        let resp = json!({
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "content": [{"type": "text", "text": "{\"facts\":[{\"trait\":\"open_port\",\"value\":\"22\"}]}"}]
            }
        });
        let output = StreamableMcpClient::unwrap_mcp_response(&resp).unwrap();
        assert!(output.get("facts").is_some());
    }

    #[test]
    fn unwrap_mcp_response_propagates_error() {
        let resp = json!({
            "jsonrpc": "2.0",
            "id": 1,
            "error": {"code": -32601, "message": "tool not found"}
        });
        let result = StreamableMcpClient::unwrap_mcp_response(&resp);
        assert!(result.is_err());
        assert!(result.unwrap_err().to_string().contains("tool not found"));
    }

    #[test]
    fn unwrap_mcp_plain_text_wraps_as_output() {
        let resp = json!({
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "content": [{"type": "text", "text": "Scan complete"}]
            }
        });
        let output = StreamableMcpClient::unwrap_mcp_response(&resp).unwrap();
        assert_eq!(output["output"].as_str(), Some("Scan complete"));
    }
}
