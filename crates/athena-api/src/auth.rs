use axum::{
    extract::{Request, State},
    http::StatusCode,
    middleware::Next,
    response::Response,
};
use std::sync::Arc;
use crate::AppState;

pub async fn bearer_auth_middleware(
    State(state): State<Arc<AppState>>,
    request: Request,
    next: Next,
) -> Result<Response, StatusCode> {
    // Skip auth for /api/health
    if request.uri().path() == "/api/health" {
        return Ok(next.run(request).await);
    }

    let token = request
        .headers()
        .get("Authorization")
        .and_then(|v| v.to_str().ok())
        .and_then(|v| v.strip_prefix("Bearer "));

    match token {
        Some(t) if is_valid_token(t, &state) => Ok(next.run(request).await),
        _ => Err(StatusCode::UNAUTHORIZED),
    }
}

fn is_valid_token(token: &str, _state: &AppState) -> bool {
    // Token validated against ATHENA_API_TOKEN env var at startup
    if let Ok(expected) = std::env::var("ATHENA_API_TOKEN") {
        return token == expected;
    }
    // No token configured → allow all (dev mode)
    true
}
