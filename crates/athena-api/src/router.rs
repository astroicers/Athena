use axum::{Router, routing::get, Json};
use serde_json::{json, Value};
use std::sync::Arc;
use crate::AppState;

pub fn api_routes() -> Router<Arc<AppState>> {
    Router::new()
        .route("/health", get(health_handler))
}

async fn health_handler() -> Json<Value> {
    Json(json!({
        "status": "ok",
        "version": env!("CARGO_PKG_VERSION"),
        "service": "athena",
    }))
}
