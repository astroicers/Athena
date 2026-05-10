// Athena MCP Server — exposes Athena capabilities to external AI agents
// Full implementation in 2.0-rc
use axum::{Router, routing::post, Json};
use serde::{Deserialize, Serialize};
use serde_json::Value;

#[derive(Debug, Deserialize)]
pub struct McpRequest {
    pub jsonrpc: String,
    pub id: Value,
    pub method: String,
    pub params: Option<Value>,
}

#[derive(Debug, Serialize)]
pub struct McpResponse {
    pub jsonrpc: String,
    pub id: Value,
    pub result: Option<Value>,
    pub error: Option<McpError>,
}

#[derive(Debug, Serialize)]
pub struct McpError {
    pub code: i32,
    pub message: String,
}

pub fn create_mcp_router() -> Router {
    Router::new()
        .route("/mcp", post(mcp_handler))
}

async fn mcp_handler(Json(req): Json<McpRequest>) -> Json<McpResponse> {
    Json(McpResponse {
        jsonrpc: "2.0".into(),
        id: req.id,
        result: Some(serde_json::json!({"stub": true, "method": req.method})),
        error: None,
    })
}
