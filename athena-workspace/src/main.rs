use std::net::SocketAddr;
use std::path::Path;
use std::sync::Arc;
use anyhow::Result;
use tracing::info;

use athena_config::AthenaConfig;
use athena_events::EventBus;
use athena_api::{create_router, AppState};

use athena_facts::InMemoryFactRepository;
use athena_llm_client::MockLlmClient;
use athena_mcp_client::HttpMcpClient;
use athena_mcp_fact_extractor::McpFactExtractor;
use athena_exec_ssh::{SshExecutionEngine, ssh::SshConfig};
use athena_observe::DefaultObserver;
use athena_orient::ClaudeOrientEngine;
use athena_decide::RiskMatrixDecider;
use athena_act::ActRouter;
use athena_engine_ooda::OodaEngine;
use athena_scheduler::OodaScheduler;
use athena_scope::CidrScopeValidator;
use athena_opsec::InMemoryOpsecMonitor;
use athena_c5isr::FactDrivenC5isrMapper;
use athena_vuln::NvdClient;
use athena_brief::FactBriefGenerator;
use athena_report::FactReportGenerator;
use athena_recon::McpReconEngine;
use athena_knowledge::constraint::OperationalConstraints;
use athena_attack_graph::DijkstraAttackGraph;
use athena_skills_loader::FileSystemSkillsLoader;

#[tokio::main]
async fn main() -> Result<()> {
    athena_telemetry::init_pretty();

    let config = AthenaConfig::load_or_default();
    info!(version = env!("CARGO_PKG_VERSION"), "Athena 2.0 starting");

    // ── fact repository ───────────────────────────────────────────────────────
    let fact_repo: Arc<dyn athena_facts::FactRepository> =
        Arc::new(InMemoryFactRepository::new());

    // ── mcp client ────────────────────────────────────────────────────────────
    let mcp_base = std::env::var("MCP_BASE_URL")
        .unwrap_or_else(|_| config.mcp.base_url.clone());
    let mcp: Arc<dyn athena_mcp_client::McpClient> = Arc::new(
        HttpMcpClient::new(mcp_base, vec![
            "nmap".into(), "web-scanner".into(), "api-fuzzer".into(),
            "dns-enum".into(), "ssl-checker".into(), "smtp-tester".into(),
        ])
    );

    // ── llm client ────────────────────────────────────────────────────────────
    let llm_model = std::env::var("ANTHROPIC_MODEL")
        .unwrap_or_else(|_| config.llm.default_model.clone());
    let llm: Arc<dyn athena_llm_client::LlmClient> =
        if std::env::var("MOCK_LLM").as_deref() == Ok("true") {
            Arc::new(MockLlmClient::new())
        } else {
            let api_key = std::env::var("ANTHROPIC_API_KEY")
                .ok()
                .filter(|k| !k.is_empty())
                .or_else(|| resolve_claude_oauth_token())
                .unwrap_or_default();
            if api_key.is_empty() {
                tracing::warn!("no ANTHROPIC_API_KEY or Claude OAuth token found — LLM calls will fail");
            } else {
                tracing::info!("LLM auth: using {} key", if api_key.starts_with("sk-ant-oat") { "OAuth" } else { "API" });
            }
            Arc::new(athena_llm_client::AnthropicClient::new(api_key, llm_model.clone()))
        };

    // ── OODA phases ───────────────────────────────────────────────────────────
    let extractor: Arc<dyn athena_mcp_fact_extractor::FactExtractor> =
        Arc::new(McpFactExtractor::new());

    let ssh_engine: Arc<dyn athena_exec_ssh::ExecutionEngine> =
        Arc::new(SshExecutionEngine::new(SshConfig::default()));

    let observe: Arc<dyn athena_observe::ObservePhase> =
        Arc::new(DefaultObserver::new(Arc::clone(&fact_repo), Arc::clone(&mcp)));

    // Build KB early so orient can use it for context injection
    let kb: Arc<dyn athena_pentest_kb::KnowledgeBase> = {
        let tkvb = athena_pentest_kb::TantivyKnowledgeBase::new_in_memory()?;
        if let Ok(entries) = athena_pentest_kb::loader::load_markdown_dir(Path::new("data/kb")) {
            let _ = tkvb.add_entries(entries);
        }
        Arc::new(tkvb)
    };

    let skills_loader = Arc::new(FileSystemSkillsLoader::new("data/skills"));

    let orient: Arc<dyn athena_orient::OrientPhase> =
        Arc::new(ClaudeOrientEngine::new(Arc::clone(&llm), llm_model)
            .with_kb(Arc::clone(&kb))
            .with_skills(skills_loader));

    let decide: Arc<dyn athena_decide::DecidePhase> =
        Arc::new(RiskMatrixDecider::new());

    let act: Arc<dyn athena_act::ActPhase> =
        Arc::new(ActRouter::new(Some(ssh_engine), Some(Arc::clone(&mcp)), Arc::clone(&extractor)));

    let attack_graph = Arc::new(DijkstraAttackGraph::new(vec![]));

    let engine: Arc<dyn athena_engine_ooda::DecisionEngine> =
        Arc::new(OodaEngine::new(observe, orient, decide, act, OperationalConstraints::default())
            .with_attack_graph(attack_graph));

    // ── scheduler ─────────────────────────────────────────────────────────────
    let scheduler = Arc::new(OodaScheduler::new(Arc::clone(&engine)));

    // ── intelligence modules ──────────────────────────────────────────────────
    let scope: Arc<dyn athena_scope::ScopeValidator> =
        Arc::new(CidrScopeValidator::allow_all());

    let opsec: Arc<dyn athena_opsec::OpsecMonitor> =
        Arc::new(InMemoryOpsecMonitor::new(1000));

    let c5isr: Arc<dyn athena_c5isr::C5isrMapper> =
        Arc::new(FactDrivenC5isrMapper::new(Arc::clone(&fact_repo)));

    let vuln_api_key = std::env::var("NVD_API_KEY").ok();
    let vuln: Arc<dyn athena_vuln::VulnerabilityManager> =
        Arc::new(NvdClient::new(vuln_api_key));

    let brief: Arc<dyn athena_brief::BriefGenerator> =
        Arc::new(FactBriefGenerator::new(Arc::clone(&fact_repo), Arc::clone(&c5isr)));

    let report: Arc<dyn athena_report::ReportGenerator> =
        Arc::new(FactReportGenerator::new(Arc::clone(&fact_repo)));

    let recon: Arc<dyn athena_recon::ReconEngine> =
        Arc::new(McpReconEngine::new(Arc::clone(&mcp)));

    // ── assemble state & serve ────────────────────────────────────────────────
    let event_bus = Arc::new(EventBus::new());

    let state = Arc::new(AppState {
        event_bus,
        engine,
        fact_repo,
        scope,
        opsec,
        c5isr,
        vuln,
        kb,
        brief,
        report,
        scheduler,
        recon,
    });

    let app = create_router(state);

    let addr: SocketAddr = format!("{}:{}", config.server.host, config.server.port)
        .parse()
        .expect("invalid bind address");

    info!(%addr, "listening");

    let listener = tokio::net::TcpListener::bind(addr).await?;
    axum::serve(listener, app).await?;

    Ok(())
}

/// Reads the OAuth access token from ~/.claude/.credentials.json when
/// ANTHROPIC_API_KEY is not set. The sk-ant-oat01-... token works with
/// the standard x-api-key header on api.anthropic.com.
fn resolve_claude_oauth_token() -> Option<String> {
    let path = dirs::home_dir()?.join(".claude").join(".credentials.json");
    let text = std::fs::read_to_string(path).ok()?;
    let val: serde_json::Value = serde_json::from_str(&text).ok()?;
    val["claudeAiOauth"]["accessToken"].as_str().map(str::to_owned)
}
