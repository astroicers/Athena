use axum::{extract::State, Json};
use serde_json::{json, Value};
use std::sync::Arc;
use uuid::Uuid;
use athena_types::OperationId;

use crate::{McpRequest, McpResponse, McpServerState, athena_err_to_mcp, tools};

pub async fn mcp_handler(
    State(state): State<Arc<McpServerState>>,
    Json(req): Json<McpRequest>,
) -> Json<McpResponse> {
    let id = req.id.clone();
    let resp = dispatch(state, req).await;
    Json(resp.unwrap_or_else(|e| McpResponse::err(id, -32000, e.to_string())))
}

async fn dispatch(
    state: Arc<McpServerState>,
    req: McpRequest,
) -> Result<McpResponse, Box<dyn std::error::Error + Send + Sync>> {
    let id = req.id.clone();

    match req.method.as_str() {
        "initialize" => Ok(McpResponse::ok(id, json!({
            "protocolVersion": "2024-11-05",
            "capabilities": { "tools": {} },
            "serverInfo": {
                "name": "athena-mcp-server",
                "version": env!("CARGO_PKG_VERSION"),
            }
        }))),

        "notifications/initialized" => Ok(McpResponse::ok(id, json!({}))),

        "tools/list" => Ok(McpResponse::ok(id, tools::tools_list_result())),

        "tools/call" => {
            let params = req.params.unwrap_or_default();
            let tool_name = params.get("name")
                .and_then(|v| v.as_str())
                .unwrap_or("");
            let args = params.get("arguments").cloned().unwrap_or(json!({}));
            Ok(call_tool(state, id, tool_name, args).await)
        }

        _ => Ok(McpResponse::err(id, -32601, format!("method not found: {}", req.method))),
    }
}

async fn call_tool(
    state: Arc<McpServerState>,
    id: Value,
    name: &str,
    args: Value,
) -> McpResponse {
    match name {
        "athena_run_iteration" => {
            let op_id = parse_or_new_op_id(&args);
            match state.engine.run_iteration(&op_id).await {
                Ok((iter_id, outcome)) => McpResponse::ok(id, tool_result(json!({
                    "op_id": op_id.to_string(),
                    "iter_id": iter_id.to_string(),
                    "facts_collected": outcome.facts_collected,
                    "results": outcome.results.len(),
                }))),
                Err(e) => athena_err_to_mcp(id, e),
            }
        }

        "athena_list_facts" => {
            let Some(op_id) = parse_op_id(&args) else {
                return McpResponse::err(id, -32602, "missing op_id");
            };
            match state.fact_repo.list(&op_id).await {
                Ok(facts) => McpResponse::ok(id, tool_result(
                    serde_json::to_value(&facts).unwrap_or(json!([]))
                )),
                Err(e) => athena_err_to_mcp(id, e),
            }
        }

        "athena_c5isr_status" => {
            let Some(op_id) = parse_op_id(&args) else {
                return McpResponse::err(id, -32602, "missing op_id");
            };
            match state.c5isr.assess(&op_id).await {
                Ok(status) => McpResponse::ok(id, tool_result(
                    serde_json::to_value(&status).unwrap_or(json!({}))
                )),
                Err(e) => athena_err_to_mcp(id, e),
            }
        }

        "athena_generate_report" => {
            let Some(op_id) = parse_op_id(&args) else {
                return McpResponse::err(id, -32602, "missing op_id");
            };
            let fmt = args.get("format").and_then(|v| v.as_str()).unwrap_or("json");
            match state.report.generate(&op_id).await {
                Ok(report) => {
                    let content = if fmt == "markdown" {
                        let md = state.report.to_markdown(&report).await;
                        json!(md)
                    } else {
                        state.report.to_json(&report).await
                    };
                    McpResponse::ok(id, tool_result(content))
                }
                Err(e) => athena_err_to_mcp(id, e),
            }
        }

        "athena_abort_operation" => {
            let Some(op_id) = parse_op_id(&args) else {
                return McpResponse::err(id, -32602, "missing op_id");
            };
            match state.engine.abort(&op_id).await {
                Ok(()) => McpResponse::ok(id, tool_result(json!({ "aborted": true }))),
                Err(e) => athena_err_to_mcp(id, e),
            }
        }

        _ => McpResponse::err(id, -32601, format!("tool not found: {name}")),
    }
}

fn tool_result(content: Value) -> Value {
    json!({
        "content": [{ "type": "text", "text": content.to_string() }],
        "isError": false,
    })
}

fn parse_op_id(args: &Value) -> Option<OperationId> {
    args.get("op_id")
        .and_then(|v| v.as_str())
        .and_then(|s| Uuid::parse_str(s).ok())
        .map(OperationId)
}

fn parse_or_new_op_id(args: &Value) -> OperationId {
    parse_op_id(args).unwrap_or_else(OperationId::new)
}
