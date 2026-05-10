pub mod mock;

use async_trait::async_trait;
use athena_types::AthenaError;
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LlmMessage {
    pub role: String,
    pub content: String,
}

impl LlmMessage {
    pub fn user(content: impl Into<String>) -> Self {
        Self { role: "user".into(), content: content.into() }
    }
    pub fn assistant(content: impl Into<String>) -> Self {
        Self { role: "assistant".into(), content: content.into() }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LlmRequest {
    pub model: String,
    pub messages: Vec<LlmMessage>,
    pub max_tokens: u32,
    pub system: Option<String>,
}

impl LlmRequest {
    pub fn new(model: impl Into<String>, system: impl Into<String>, user_msg: impl Into<String>) -> Self {
        Self {
            model: model.into(),
            messages: vec![LlmMessage::user(user_msg)],
            max_tokens: 4096,
            system: Some(system.into()),
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LlmResponse {
    pub content: String,
    pub input_tokens: u32,
    pub output_tokens: u32,
}

#[async_trait]
pub trait LlmClient: Send + Sync {
    async fn complete(&self, req: LlmRequest) -> Result<LlmResponse, AthenaError>;
    fn model_name(&self) -> &str;
}

pub use mock::MockLlmClient;
