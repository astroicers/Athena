pub mod tools;
pub mod handler;

use axum::{Router, routing::post};
use std::sync::Arc;
use athena_types::AthenaError;
use athena_engine_ooda::DecisionEngine;
use athena_facts::FactRepository;
use athena_c5isr::C5isrMapper;
use athena_report::ReportGenerator;
use serde::{Deserialize, Serialize};
use serde_json::Value;

// ── MCP JSON-RPC envelope ────────────────────────────────────────────────────

#[derive(Debug, Clone, Deserialize)]
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
    #[serde(skip_serializing_if = "Option::is_none")]
    pub result: Option<Value>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub error: Option<McpError>,
}

#[derive(Debug, Serialize)]
pub struct McpError {
    pub code: i32,
    pub message: String,
}

impl McpResponse {
    pub fn ok(id: Value, result: Value) -> Self {
        Self { jsonrpc: "2.0".into(), id, result: Some(result), error: None }
    }

    pub fn err(id: Value, code: i32, msg: impl Into<String>) -> Self {
        Self {
            jsonrpc: "2.0".into(),
            id,
            result: None,
            error: Some(McpError { code, message: msg.into() }),
        }
    }
}

// ── shared server state ───────────────────────────────────────────────────────

pub struct McpServerState {
    pub engine: Arc<dyn DecisionEngine>,
    pub fact_repo: Arc<dyn FactRepository>,
    pub c5isr: Arc<dyn C5isrMapper>,
    pub report: Arc<dyn ReportGenerator>,
}

// ── router factory ────────────────────────────────────────────────────────────

pub fn create_mcp_router(state: Arc<McpServerState>) -> Router {
    Router::new()
        .route("/mcp", post(handler::mcp_handler))
        .with_state(state)
}

// ── error conversion ──────────────────────────────────────────────────────────

pub fn athena_err_to_mcp(id: Value, e: AthenaError) -> McpResponse {
    McpResponse::err(id, -32000, e.to_string())
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;
    use std::sync::Arc;
    use async_trait::async_trait;
    use athena_types::{OperationId, OodaIterationId, ExecutionOutcome, AthenaError};
    use athena_c5isr::C5isrStatus;
    use athena_facts::InMemoryFactRepository;
    use crate::handler::mcp_handler;
    use axum::{
        body::Body,
        http::{Request, StatusCode},
        Router, routing::post,
    };
    use tower::ServiceExt as _;

    struct MockEngine;
    #[async_trait]
    impl DecisionEngine for MockEngine {
        fn name(&self) -> &'static str { "mock" }
        async fn run_iteration(&self, op_id: &OperationId) -> Result<(OodaIterationId, ExecutionOutcome), AthenaError> {
            Ok((OodaIterationId::new(), ExecutionOutcome { results: vec![], facts_collected: 0 }))
        }
        async fn abort(&self, _op_id: &OperationId) -> Result<(), AthenaError> { Ok(()) }
    }

    struct MockC5isr;
    #[async_trait]
    impl C5isrMapper for MockC5isr {
        async fn assess(&self, _op_id: &OperationId) -> Result<C5isrStatus, AthenaError> {
            Ok(C5isrStatus {
                command: 0.5, control: 0.5, communications: 0.5,
                computers: 0.5, intelligence: 0.5, surveillance: 0.5,
                overall: 0.5,
            })
        }
    }

    struct MockReport;
    #[async_trait]
    impl ReportGenerator for MockReport {
        async fn generate(&self, op_id: &OperationId) -> Result<athena_report::PentestReport, AthenaError> {
            Ok(athena_report::PentestReport {
                op_id: op_id.to_string(),
                title: "Test".into(),
                executive_summary: "none".into(),
                findings: vec![],
                generated_at: chrono::Utc::now(),
            })
        }
        async fn to_markdown(&self, _r: &athena_report::PentestReport) -> String { "# md".into() }
        async fn to_json(&self, r: &athena_report::PentestReport) -> Value {
            serde_json::to_value(r).unwrap()
        }
    }

    fn make_state() -> Arc<McpServerState> {
        Arc::new(McpServerState {
            engine: Arc::new(MockEngine),
            fact_repo: Arc::new(InMemoryFactRepository::new()),
            c5isr: Arc::new(MockC5isr),
            report: Arc::new(MockReport),
        })
    }

    fn make_app() -> Router {
        let state = make_state();
        Router::new()
            .route("/mcp", post(mcp_handler))
            .with_state(state)
    }

    async fn post_mcp(app: Router, body: Value) -> Value {
        let req = Request::builder()
            .method("POST")
            .uri("/mcp")
            .header("content-type", "application/json")
            .body(Body::from(body.to_string()))
            .unwrap();
        let resp = app.oneshot(req).await.unwrap();
        assert_eq!(resp.status(), StatusCode::OK);
        let bytes = axum::body::to_bytes(resp.into_body(), usize::MAX).await.unwrap();
        serde_json::from_slice(&bytes).unwrap()
    }

    #[tokio::test]
    async fn initialize_returns_capabilities() {
        let app = make_app();
        let resp = post_mcp(app, json!({
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": { "protocolVersion": "2024-11-05" }
        })).await;
        assert_eq!(resp["result"]["serverInfo"]["name"], "athena-mcp-server");
        assert!(resp["result"]["capabilities"]["tools"].is_object());
    }

    #[tokio::test]
    async fn tools_list_returns_five_tools() {
        let app = make_app();
        let resp = post_mcp(app, json!({
            "jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": null
        })).await;
        let tools = resp["result"]["tools"].as_array().unwrap();
        assert_eq!(tools.len(), 5);
        let names: Vec<&str> = tools.iter()
            .map(|t| t["name"].as_str().unwrap())
            .collect();
        assert!(names.contains(&"athena_run_iteration"));
        assert!(names.contains(&"athena_generate_report"));
    }

    #[tokio::test]
    async fn run_iteration_returns_iter_id() {
        let app = make_app();
        let resp = post_mcp(app, json!({
            "jsonrpc": "2.0", "id": 3,
            "method": "tools/call",
            "params": { "name": "athena_run_iteration", "arguments": {} }
        })).await;
        assert!(resp.get("error").is_none(), "unexpected error: {resp}");
        assert!(resp["result"]["content"].is_array());
    }

    #[tokio::test]
    async fn unknown_method_returns_32601() {
        let app = make_app();
        let resp = post_mcp(app, json!({
            "jsonrpc": "2.0", "id": 4, "method": "bogus/method", "params": null
        })).await;
        assert_eq!(resp["error"]["code"], -32601);
    }

    #[tokio::test]
    async fn missing_op_id_returns_32602() {
        let app = make_app();
        let resp = post_mcp(app, json!({
            "jsonrpc": "2.0", "id": 5,
            "method": "tools/call",
            "params": { "name": "athena_list_facts", "arguments": {} }
        })).await;
        assert_eq!(resp["error"]["code"], -32602);
    }
}
