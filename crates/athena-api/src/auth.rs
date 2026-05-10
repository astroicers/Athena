use axum::{
    extract::{Request, State},
    http::StatusCode,
    middleware::Next,
    response::Response,
};
use std::sync::Arc;
use crate::AppState;

pub async fn bearer_auth_middleware(
    State(_state): State<Arc<AppState>>,
    request: Request,
    next: Next,
) -> Result<Response, StatusCode> {
    // Skip auth for /api/health
    if request.uri().path() == "/api/health" {
        return Ok(next.run(request).await);
    }

    // Dev mode: no token configured → allow all requests
    let configured_token = std::env::var("ATHENA_API_TOKEN")
        .ok()
        .filter(|t| !t.is_empty());

    let Some(expected) = configured_token else {
        return Ok(next.run(request).await);
    };

    let token = request
        .headers()
        .get("Authorization")
        .and_then(|v| v.to_str().ok())
        .and_then(|v| v.strip_prefix("Bearer "));

    match token {
        Some(t) if t == expected => Ok(next.run(request).await),
        _ => Err(StatusCode::UNAUTHORIZED),
    }
}
