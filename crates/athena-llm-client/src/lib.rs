use async_trait::async_trait;
use athena_types::AthenaError;
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LlmMessage {
    pub role: String,
    pub content: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LlmRequest {
    pub model: String,
    pub messages: Vec<LlmMessage>,
    pub max_tokens: u32,
    pub system: Option<String>,
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

pub struct MockLlmClient;

#[async_trait]
impl LlmClient for MockLlmClient {
    async fn complete(&self, req: LlmRequest) -> Result<LlmResponse, AthenaError> {
        Ok(LlmResponse {
            content: format!("[MOCK] Responding to {} messages", req.messages.len()),
            input_tokens: 100,
            output_tokens: 50,
        })
    }
    fn model_name(&self) -> &str { "mock" }
}
