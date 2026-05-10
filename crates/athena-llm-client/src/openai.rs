use async_trait::async_trait;
use athena_types::AthenaError;
use reqwest::Client;
use serde::{Deserialize, Serialize};
use crate::{LlmClient, LlmRequest, LlmResponse};

const OPENAI_API_URL: &str = "https://api.openai.com/v1/chat/completions";

pub struct OpenAiClient {
    client: Client,
    api_key: String,
    default_model: String,
}

impl OpenAiClient {
    pub fn new(api_key: impl Into<String>, default_model: impl Into<String>) -> Self {
        Self {
            client: Client::new(),
            api_key: api_key.into(),
            default_model: default_model.into(),
        }
    }
}

#[derive(Serialize)]
struct OpenAiRequest<'a> {
    model: &'a str,
    max_tokens: u32,
    messages: Vec<OpenAiMessage>,
}

#[derive(Serialize)]
struct OpenAiMessage {
    role: String,
    content: String,
}

#[derive(Deserialize)]
struct OpenAiResponse {
    choices: Vec<OpenAiChoice>,
    usage: OpenAiUsage,
}

#[derive(Deserialize)]
struct OpenAiChoice {
    message: OpenAiChoiceMessage,
}

#[derive(Deserialize)]
struct OpenAiChoiceMessage {
    content: String,
}

#[derive(Deserialize)]
struct OpenAiUsage {
    prompt_tokens: u32,
    completion_tokens: u32,
}

#[async_trait]
impl LlmClient for OpenAiClient {
    async fn complete(&self, req: LlmRequest) -> Result<LlmResponse, AthenaError> {
        let model = if req.model.is_empty() { &self.default_model } else { &req.model };

        // Prepend system message if present
        let mut messages: Vec<OpenAiMessage> = Vec::new();
        if let Some(system) = &req.system {
            messages.push(OpenAiMessage { role: "system".into(), content: system.clone() });
        }
        for m in &req.messages {
            messages.push(OpenAiMessage { role: m.role.clone(), content: m.content.clone() });
        }

        let body = OpenAiRequest { model, max_tokens: req.max_tokens, messages };

        let resp = self.client
            .post(OPENAI_API_URL)
            .bearer_auth(&self.api_key)
            .header("content-type", "application/json")
            .json(&body)
            .send()
            .await
            .map_err(|e| AthenaError::LlmError(e.to_string()))?;

        let status = resp.status();
        if !status.is_success() {
            let text = resp.text().await.unwrap_or_default();
            return Err(AthenaError::LlmError(format!("OpenAI API {status}: {text}")));
        }

        let api_resp: OpenAiResponse = resp.json().await
            .map_err(|e| AthenaError::LlmError(format!("parse error: {e}")))?;

        let content = api_resp.choices.into_iter()
            .next()
            .map(|c| c.message.content)
            .unwrap_or_default();

        Ok(LlmResponse {
            content,
            input_tokens: api_resp.usage.prompt_tokens,
            output_tokens: api_resp.usage.completion_tokens,
        })
    }

    fn model_name(&self) -> &str { &self.default_model }
}
