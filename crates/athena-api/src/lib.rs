pub mod router;

use axum::{Router, middleware};
use std::sync::Arc;
use athena_types::AthenaError;
use athena_events::EventBus;

pub struct AppState {
    pub event_bus: Arc<EventBus>,
}

pub fn create_router(state: Arc<AppState>) -> Router {
    Router::new()
        .nest("/api", router::api_routes())
        .with_state(state)
}
