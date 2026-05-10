use axum::{http::StatusCode, response::{IntoResponse, Response}, Json};
use athena_types::AthenaError;
use serde_json::json;

pub struct ApiError(pub AthenaError);

impl From<AthenaError> for ApiError {
    fn from(e: AthenaError) -> Self {
        Self(e)
    }
}

impl IntoResponse for ApiError {
    fn into_response(self) -> Response {
        let (status, msg) = match &self.0 {
            AthenaError::OperationNotFound(m) => (StatusCode::NOT_FOUND, m.clone()),
            AthenaError::OutOfScope(m) => (StatusCode::FORBIDDEN, m.clone()),
            AthenaError::DecisionBlocked(m) => (StatusCode::UNPROCESSABLE_ENTITY, m.clone()),
            AthenaError::DatabaseError(m) => (StatusCode::INTERNAL_SERVER_ERROR, m.clone()),
            _ => (StatusCode::INTERNAL_SERVER_ERROR, self.0.to_string()),
        };
        (status, Json(json!({ "error": msg }))).into_response()
    }
}
