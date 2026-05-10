pub mod anthropic;
pub mod openai;
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
pub use anthropic::AnthropicClient;
pub use openai::OpenAiClient;

#[cfg(test)]
mod tests {
    use super::*;
    use mock::MockLlmClient;

    #[tokio::test]
    async fn mock_returns_default_response() {
        let client = MockLlmClient::new();
        let req = LlmRequest::new("mock", "system prompt", "what should I do?");
        let resp = client.complete(req).await.unwrap();
        assert!(!resp.content.is_empty());
        assert_eq!(client.model_name(), "mock");
    }

    #[tokio::test]
    async fn mock_returns_fixed_response() {
        let client = MockLlmClient::with_response(r#"{"summary":"test","recommended_techniques":["T1046"],"risk_score":0.2,"rationale":"ok"}"#);
        let req = LlmRequest::new("mock", "system", "user msg");
        let resp = client.complete(req).await.unwrap();
        assert!(resp.content.contains("T1046"));
    }

    #[test]
    fn llm_request_builder() {
        let req = LlmRequest::new("claude-opus-4-7", "you are an expert", "analyse this");
        assert_eq!(req.model, "claude-opus-4-7");
        assert_eq!(req.messages.len(), 1);
        assert_eq!(req.messages[0].role, "user");
        assert!(req.system.is_some());
        assert_eq!(req.max_tokens, 4096);
    }

    #[test]
    fn llm_message_constructors() {
        let u = LlmMessage::user("hello");
        let a = LlmMessage::assistant("hi");
        assert_eq!(u.role, "user");
        assert_eq!(a.role, "assistant");
    }
}
