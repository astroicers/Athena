use axum::{
    Router,
    extract::{Path, Query, State},
    routing::{delete, get, post},
    Json,
};
use serde::Deserialize;
use serde_json::{json, Value};
use std::sync::Arc;
use uuid::Uuid;
use athena_types::{OperationId, Target, TargetId};
use crate::{AppState, error::ApiError};

// ── helpers ──────────────────────────────────────────────────────────────────

fn op_id(s: &str) -> Result<OperationId, ApiError> {
    Uuid::parse_str(s)
        .map(OperationId)
        .map_err(|_| ApiError(athena_types::AthenaError::OperationNotFound(format!("invalid uuid: {s}"))))
}

// ── request / response DTOs ──────────────────────────────────────────────────

#[derive(Deserialize)]
pub struct StartSchedulerRequest {
    pub interval_secs: u64,
}

#[derive(Deserialize)]
pub struct ConsumeOpsecRequest {
    pub cost: i32,
}

#[derive(Deserialize)]
pub struct SearchKbQuery {
    pub q: String,
    #[serde(default = "default_limit")]
    pub limit: usize,
}
fn default_limit() -> usize { 10 }

#[derive(Deserialize)]
pub struct SearchCveQuery {
    pub keyword: String,
    #[serde(default = "default_limit")]
    pub limit: usize,
}

#[derive(Deserialize)]
pub struct ReconRequest {
    pub target_hostname: Option<String>,
    pub target_ip: Option<String>,
}

// ── route table ──────────────────────────────────────────────────────────────

pub fn api_routes() -> Router<Arc<AppState>> {
    Router::new()
        // health
        .route("/health", get(health_handler))
        // operations & OODA
        .route("/operations", post(run_iteration))
        .route("/operations/:op_id/abort", post(abort_operation))
        .route("/operations/:op_id/iterate", post(run_iteration_for_op))
        // facts
        .route("/operations/:op_id/facts", get(list_facts))
        .route("/operations/:op_id/facts/count", get(count_facts))
        // observe / orient / decide / act
        .route("/operations/:op_id/observe", post(observe))
        .route("/operations/:op_id/observe/summary", get(observe_summary))
        .route("/operations/:op_id/orient", post(orient))
        .route("/operations/:op_id/decide", post(decide))
        .route("/operations/:op_id/act", post(act))
        // scheduler
        .route("/operations/:op_id/scheduler/start", post(scheduler_start))
        .route("/operations/:op_id/scheduler/stop", delete(scheduler_stop))
        .route("/scheduler/active", get(scheduler_active))
        // scope
        .route("/operations/:op_id/scope/check", post(scope_check))
        // opsec
        .route("/operations/:op_id/opsec", get(opsec_status))
        .route("/operations/:op_id/opsec/consume", post(opsec_consume))
        // c5isr
        .route("/operations/:op_id/c5isr", get(c5isr_assess))
        // vuln
        .route("/vuln/cve/:cve_id", get(vuln_lookup))
        .route("/vuln/search", get(vuln_search))
        // pentest kb
        .route("/kb/search", get(kb_search))
        .route("/kb/:id", get(kb_get))
        .route("/kb/category/:category", get(kb_list_by_category))
        // brief & report
        .route("/operations/:op_id/brief", get(brief_generate))
        .route("/operations/:op_id/report", get(report_generate))
        .route("/operations/:op_id/report/markdown", get(report_markdown))
        // recon
        .route("/operations/:op_id/recon", post(recon))
}

// ── handlers ─────────────────────────────────────────────────────────────────

async fn health_handler() -> Json<Value> {
    Json(json!({
        "status": "ok",
        "version": env!("CARGO_PKG_VERSION"),
        "service": "athena",
    }))
}

async fn run_iteration(State(state): State<Arc<AppState>>) -> Result<Json<Value>, ApiError> {
    let op_id = OperationId::new();
    let (iter_id, outcome) = state.engine.run_iteration(&op_id).await?;
    Ok(Json(json!({
        "op_id": op_id.to_string(),
        "iter_id": iter_id.to_string(),
        "facts_collected": outcome.facts_collected,
    })))
}

async fn run_iteration_for_op(
    State(state): State<Arc<AppState>>,
    Path(id): Path<String>,
) -> Result<Json<Value>, ApiError> {
    let op = op_id(&id)?;
    let (iter_id, outcome) = state.engine.run_iteration(&op).await?;
    Ok(Json(json!({
        "op_id": id,
        "iter_id": iter_id.to_string(),
        "facts_collected": outcome.facts_collected,
    })))
}

async fn abort_operation(
    State(state): State<Arc<AppState>>,
    Path(id): Path<String>,
) -> Result<Json<Value>, ApiError> {
    let op = op_id(&id)?;
    state.engine.abort(&op).await?;
    Ok(Json(json!({ "aborted": true, "op_id": id })))
}

async fn list_facts(
    State(state): State<Arc<AppState>>,
    Path(id): Path<String>,
) -> Result<Json<Value>, ApiError> {
    let op = op_id(&id)?;
    let facts = state.fact_repo.list(&op).await?;
    Ok(Json(serde_json::to_value(&facts).unwrap_or(json!([]))))
}

async fn count_facts(
    State(state): State<Arc<AppState>>,
    Path(id): Path<String>,
) -> Result<Json<Value>, ApiError> {
    let op = op_id(&id)?;
    let count = state.fact_repo.count(&op).await?;
    Ok(Json(json!({ "op_id": id, "count": count })))
}

async fn observe(
    State(state): State<Arc<AppState>>,
    Path(id): Path<String>,
) -> Result<Json<Value>, ApiError> {
    let op = op_id(&id)?;
    let count = state.fact_repo.count(&op).await?;
    Ok(Json(json!({ "op_id": id, "facts_before": count })))
}

async fn observe_summary(
    State(state): State<Arc<AppState>>,
    Path(id): Path<String>,
) -> Result<Json<Value>, ApiError> {
    let op = op_id(&id)?;
    let facts = state.fact_repo.list(&op).await?;
    let summary = facts.iter()
        .map(|f| format!("{}: {}", f.trait_name.0, match &f.value {
            athena_types::FactValue::Text(s) => s.clone(),
            athena_types::FactValue::Number(n) => n.to_string(),
            athena_types::FactValue::Bool(b) => b.to_string(),
        }))
        .collect::<Vec<_>>()
        .join("\n");
    Ok(Json(json!({ "op_id": id, "summary": summary })))
}

async fn orient(
    State(state): State<Arc<AppState>>,
    Path(id): Path<String>,
) -> Result<Json<Value>, ApiError> {
    let op = op_id(&id)?;
    let (iter_id, outcome) = state.engine.run_iteration(&op).await?;
    Ok(Json(json!({
        "op_id": id,
        "iter_id": iter_id.to_string(),
        "facts_collected": outcome.facts_collected,
    })))
}

async fn decide(
    State(state): State<Arc<AppState>>,
    Path(id): Path<String>,
) -> Result<Json<Value>, ApiError> {
    let op = op_id(&id)?;
    let opsec = state.opsec.status(&op).await?;
    Ok(Json(json!({
        "op_id": id,
        "opsec_noise": opsec.noise_level,
        "threat_level": format!("{:?}", opsec.threat_level),
    })))
}

async fn act(
    State(state): State<Arc<AppState>>,
    Path(id): Path<String>,
) -> Result<Json<Value>, ApiError> {
    let op = op_id(&id)?;
    let (iter_id, outcome) = state.engine.run_iteration(&op).await?;
    Ok(Json(json!({
        "op_id": id,
        "iter_id": iter_id.to_string(),
        "results": outcome.results.len(),
    })))
}

async fn scheduler_start(
    State(state): State<Arc<AppState>>,
    Path(id): Path<String>,
    Json(body): Json<StartSchedulerRequest>,
) -> Result<Json<Value>, ApiError> {
    let op = op_id(&id)?;
    state.scheduler.start(op, body.interval_secs).await;
    Ok(Json(json!({ "op_id": id, "started": true, "interval_secs": body.interval_secs })))
}

async fn scheduler_stop(
    State(state): State<Arc<AppState>>,
    Path(id): Path<String>,
) -> Result<Json<Value>, ApiError> {
    let op = op_id(&id)?;
    state.scheduler.stop(&op).await?;
    Ok(Json(json!({ "op_id": id, "stopped": true })))
}

async fn scheduler_active(State(state): State<Arc<AppState>>) -> Json<Value> {
    let ops = state.scheduler.active_operations();
    Json(json!({ "active": ops }))
}

async fn scope_check(
    State(state): State<Arc<AppState>>,
    Path(id): Path<String>,
    Json(body): Json<Value>,
) -> Result<Json<Value>, ApiError> {
    let hostname = body.get("hostname").and_then(|v| v.as_str()).map(String::from);
    let ip_str = body.get("ip").and_then(|v| v.as_str());
    let ip = ip_str.and_then(|s| s.parse().ok());
    let target = Target { id: TargetId::new(), hostname, ip, os: None, tags: vec![] };
    let in_scope = state.scope.is_in_scope(&target).await?;
    Ok(Json(json!({ "op_id": id, "in_scope": in_scope })))
}

async fn opsec_status(
    State(state): State<Arc<AppState>>,
    Path(id): Path<String>,
) -> Result<Json<Value>, ApiError> {
    let op = op_id(&id)?;
    let status = state.opsec.status(&op).await?;
    Ok(Json(json!({
        "op_id": id,
        "noise_level": status.noise_level,
        "budget_remaining": status.remaining_budget,
        "threat_level": format!("{:?}", status.threat_level),
    })))
}

async fn opsec_consume(
    State(state): State<Arc<AppState>>,
    Path(id): Path<String>,
    Json(body): Json<ConsumeOpsecRequest>,
) -> Result<Json<Value>, ApiError> {
    let op = op_id(&id)?;
    state.opsec.consume_budget(&op, body.cost).await?;
    let status = state.opsec.status(&op).await?;
    Ok(Json(json!({
        "op_id": id,
        "budget_remaining": status.remaining_budget,
        "threat_level": format!("{:?}", status.threat_level),
    })))
}

async fn c5isr_assess(
    State(state): State<Arc<AppState>>,
    Path(id): Path<String>,
) -> Result<Json<Value>, ApiError> {
    let op = op_id(&id)?;
    let status = state.c5isr.assess(&op).await?;
    Ok(Json(serde_json::to_value(&status).unwrap_or(json!({}))))
}

async fn vuln_lookup(
    State(state): State<Arc<AppState>>,
    Path(cve_id): Path<String>,
) -> Result<Json<Value>, ApiError> {
    let entry = state.vuln.lookup_cve(&cve_id).await?;
    Ok(Json(serde_json::to_value(&entry).unwrap_or(json!({}))))
}

async fn vuln_search(
    State(state): State<Arc<AppState>>,
    Query(q): Query<SearchCveQuery>,
) -> Result<Json<Value>, ApiError> {
    let results = state.vuln.search_cves(&q.keyword, q.limit).await?;
    Ok(Json(serde_json::to_value(&results).unwrap_or(json!([]))))
}

async fn kb_search(
    State(state): State<Arc<AppState>>,
    Query(q): Query<SearchKbQuery>,
) -> Result<Json<Value>, ApiError> {
    let results = state.kb.search(&q.q, q.limit).await?;
    Ok(Json(serde_json::to_value(&results).unwrap_or(json!([]))))
}

async fn kb_get(
    State(state): State<Arc<AppState>>,
    Path(id): Path<String>,
) -> Result<Json<Value>, ApiError> {
    match state.kb.get(&id).await? {
        Some(entry) => Ok(Json(serde_json::to_value(&entry).unwrap_or(json!({})))),
        None => Err(ApiError(athena_types::AthenaError::OperationNotFound(format!("kb entry not found: {id}")))),
    }
}

async fn kb_list_by_category(
    State(state): State<Arc<AppState>>,
    Path(category): Path<String>,
) -> Result<Json<Value>, ApiError> {
    use athena_pentest_kb::KbCategory;
    let cat = match category.as_str() {
        "privilege_escalation" => KbCategory::PrivilegeEscalation,
        "lateral_movement"     => KbCategory::LateralMovement,
        "initial_access"       => KbCategory::InitialAccess,
        "persistence"          => KbCategory::Persistence,
        "defense_evasion"      => KbCategory::DefenseEvasion,
        "credential_access"    => KbCategory::CredentialAccess,
        "discovery"            => KbCategory::Discovery,
        "exfiltration"         => KbCategory::Exfiltration,
        _                      => KbCategory::CommandAndControl,
    };
    let entries = state.kb.list_by_category(&cat).await?;
    Ok(Json(serde_json::to_value(&entries).unwrap_or(json!([]))))
}

async fn brief_generate(
    State(state): State<Arc<AppState>>,
    Path(id): Path<String>,
) -> Result<Json<Value>, ApiError> {
    let op = op_id(&id)?;
    let brief = state.brief.generate(&op).await?;
    Ok(Json(json!({ "op_id": id, "brief": brief })))
}

async fn report_generate(
    State(state): State<Arc<AppState>>,
    Path(id): Path<String>,
) -> Result<Json<Value>, ApiError> {
    let op = op_id(&id)?;
    let report = state.report.generate(&op).await?;
    let json = state.report.to_json(&report).await;
    Ok(Json(json))
}

async fn report_markdown(
    State(state): State<Arc<AppState>>,
    Path(id): Path<String>,
) -> Result<Json<Value>, ApiError> {
    let op = op_id(&id)?;
    let report = state.report.generate(&op).await?;
    let md = state.report.to_markdown(&report).await;
    Ok(Json(json!({ "op_id": id, "markdown": md })))
}

async fn recon(
    State(state): State<Arc<AppState>>,
    Path(id): Path<String>,
    Json(body): Json<ReconRequest>,
) -> Result<Json<Value>, ApiError> {
    let op = op_id(&id)?;
    let ip = body.target_ip.as_deref().and_then(|s| s.parse().ok());
    let target = Target {
        id: TargetId::new(),
        hostname: body.target_hostname,
        ip,
        os: None,
        tags: vec![],
    };
    let facts = state.recon.recon(&op, &target).await?;
    for fact in &facts {
        let _ = state.fact_repo.insert(fact.clone()).await;
    }
    Ok(Json(json!({ "op_id": id, "facts_collected": facts.len() })))
}
