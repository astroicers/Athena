use async_trait::async_trait;
use athena_types::AthenaError;
use reqwest::Client;
use serde::{Deserialize, Serialize};
use crate::{LlmClient, LlmRequest, LlmResponse};

const ANTHROPIC_API_URL: &str = "https://api.anthropic.com/v1/messages";
const ANTHROPIC_VERSION: &str = "2023-06-01";

pub struct AnthropicClient {
    client: Client,
    api_key: String,
    default_model: String,
}

impl AnthropicClient {
    pub fn new(api_key: impl Into<String>, default_model: impl Into<String>) -> Self {
        Self {
            client: Client::new(),
            api_key: api_key.into(),
            default_model: default_model.into(),
        }
    }
}

// Anthropic wire types
#[derive(Serialize)]
struct AnthropicRequest<'a> {
    model: &'a str,
    max_tokens: u32,
    #[serde(skip_serializing_if = "Option::is_none")]
    system: Option<Vec<AnthropicSystemBlock<'a>>>,
    messages: Vec<AnthropicMessage<'a>>,
}

#[derive(Serialize)]
struct AnthropicSystemBlock<'a> {
    r#type: &'static str,
    text: &'a str,
    #[serde(skip_serializing_if = "Option::is_none")]
    cache_control: Option<CacheControl>,
}

#[derive(Serialize)]
struct CacheControl {
    r#type: &'static str,
}

#[derive(Serialize)]
struct AnthropicMessage<'a> {
    role: &'a str,
    content: &'a str,
}

#[derive(Deserialize)]
struct AnthropicResponse {
    content: Vec<AnthropicContent>,
    usage: AnthropicUsage,
}

#[derive(Deserialize)]
struct AnthropicContent {
    text: String,
}

#[derive(Deserialize)]
struct AnthropicUsage {
    input_tokens: u32,
    output_tokens: u32,
}

#[derive(Deserialize)]
struct AnthropicError {
    error: AnthropicErrorDetail,
}

#[derive(Deserialize)]
struct AnthropicErrorDetail {
    message: String,
}

#[async_trait]
impl LlmClient for AnthropicClient {
    async fn complete(&self, req: LlmRequest) -> Result<LlmResponse, AthenaError> {
        let model = if req.model.is_empty() { &self.default_model } else { &req.model };

        // Build system blocks with prompt caching on the last (largest) block
        let system = req.system.as_deref().map(|text| {
            vec![AnthropicSystemBlock {
                r#type: "text",
                text,
                cache_control: Some(CacheControl { r#type: "ephemeral" }),
            }]
        });

        let messages: Vec<AnthropicMessage> = req.messages.iter()
            .map(|m| AnthropicMessage { role: &m.role, content: &m.content })
            .collect();

        let body = AnthropicRequest {
            model,
            max_tokens: req.max_tokens,
            system,
            messages,
        };

        let resp = self.client
            .post(ANTHROPIC_API_URL)
            .header("x-api-key", &self.api_key)
            .header("anthropic-version", ANTHROPIC_VERSION)
            .header("anthropic-beta", "prompt-caching-2024-07-31")
            .header("content-type", "application/json")
            .json(&body)
            .send()
            .await
            .map_err(|e| AthenaError::LlmError(e.to_string()))?;

        let status = resp.status();
        if !status.is_success() {
            let text = resp.text().await.unwrap_or_default();
            let msg = serde_json::from_str::<AnthropicError>(&text)
                .map(|e| e.error.message)
                .unwrap_or(text);
            return Err(AthenaError::LlmError(format!("Anthropic API {status}: {msg}")));
        }

        let api_resp: AnthropicResponse = resp.json().await
            .map_err(|e| AthenaError::LlmError(format!("parse error: {e}")))?;

        let content = api_resp.content.into_iter()
            .map(|c| c.text)
            .collect::<Vec<_>>()
            .join("");

        Ok(LlmResponse {
            content,
            input_tokens: api_resp.usage.input_tokens,
            output_tokens: api_resp.usage.output_tokens,
        })
    }

    fn model_name(&self) -> &str { &self.default_model }
}
