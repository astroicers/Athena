use std::net::SocketAddr;
use std::sync::Arc;
use anyhow::Result;
use tracing::info;

use athena_config::AthenaConfig;
use athena_events::EventBus;
use athena_api::{create_router, AppState};

#[tokio::main]
async fn main() -> Result<()> {
    athena_telemetry::init_pretty();

    let config = AthenaConfig::load_or_default();
    info!(version = env!("CARGO_PKG_VERSION"), "Athena 2.0 starting");

    let event_bus = Arc::new(EventBus::new());

    let state = Arc::new(AppState {
        event_bus,
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
