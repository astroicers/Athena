use async_trait::async_trait;
use athena_types::{Fact, AthenaError};
use athena_mcp_client::McpToolResult;

#[async_trait]
pub trait FactExtractor: Send + Sync {
    async fn extract(&self, result: &McpToolResult, source_tool: &str) -> Result<Vec<Fact>, AthenaError>;
}
