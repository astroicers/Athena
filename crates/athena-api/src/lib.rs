pub mod auth;
pub mod error;
pub mod router;

use axum::{Router, middleware as axum_middleware};
use std::sync::Arc;
use athena_events::EventBus;
use athena_engine_ooda::DecisionEngine;
use athena_facts::FactRepository;
use athena_scope::ScopeValidator;
use athena_opsec::OpsecMonitor;
use athena_c5isr::C5isrMapper;
use athena_vuln::VulnerabilityManager;
use athena_pentest_kb::KnowledgeBase;
use athena_brief::BriefGenerator;
use athena_report::ReportGenerator;
use athena_scheduler::OodaScheduler;
use athena_recon::ReconEngine;

pub struct AppState {
    pub event_bus: Arc<EventBus>,
    pub engine: Arc<dyn DecisionEngine>,
    pub fact_repo: Arc<dyn FactRepository>,
    pub scope: Arc<dyn ScopeValidator>,
    pub opsec: Arc<dyn OpsecMonitor>,
    pub c5isr: Arc<dyn C5isrMapper>,
    pub vuln: Arc<dyn VulnerabilityManager>,
    pub kb: Arc<dyn KnowledgeBase>,
    pub brief: Arc<dyn BriefGenerator>,
    pub report: Arc<dyn ReportGenerator>,
    pub scheduler: Arc<OodaScheduler>,
    pub recon: Arc<dyn ReconEngine>,
}

pub fn create_router(state: Arc<AppState>) -> Router {
    Router::new()
        .nest("/api", router::api_routes())
        .layer(axum_middleware::from_fn_with_state(state.clone(), auth::bearer_auth_middleware))
        .with_state(state)
}
