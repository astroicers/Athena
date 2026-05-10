pub mod http;
pub mod circuit_breaker;

use async_trait::async_trait;
use athena_types::AthenaError;
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct McpToolCall {
    pub tool: String,
    pub params: serde_json::Value,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct McpToolResult {
    pub tool: String,
    pub output: serde_json::Value,
    pub success: bool,
    pub error: Option<String>,
}

#[async_trait]
pub trait McpClient: Send + Sync {
    async fn call(&self, tool: &str, params: serde_json::Value) -> Result<McpToolResult, AthenaError>;
    async fn health_check(&self, tool: &str) -> bool;
    fn available_tools(&self) -> Vec<String>;
}

pub use http::HttpMcpClient;
pub use circuit_breaker::{CircuitBreaker, CircuitState};
