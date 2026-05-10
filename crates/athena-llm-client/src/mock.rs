use async_trait::async_trait;
use athena_types::AthenaError;
use crate::{LlmClient, LlmRequest, LlmResponse};

pub struct MockLlmClient {
    pub fixed_response: Option<String>,
}

impl MockLlmClient {
    pub fn new() -> Self {
        Self { fixed_response: None }
    }

    pub fn with_response(response: impl Into<String>) -> Self {
        Self { fixed_response: Some(response.into()) }
    }
}

impl Default for MockLlmClient {
    fn default() -> Self { Self::new() }
}

#[async_trait]
impl LlmClient for MockLlmClient {
    async fn complete(&self, req: LlmRequest) -> Result<LlmResponse, AthenaError> {
        let content = self.fixed_response.clone().unwrap_or_else(|| {
            // Return structured mock orient recommendation JSON
            serde_json::json!({
                "summary": "Mock orient analysis: target appears to be a Linux web server",
                "recommended_techniques": ["T1046", "T1078", "T1059.004"],
                "risk_score": 0.35,
                "rationale": "Low-risk reconnaissance techniques recommended based on observed services"
            }).to_string()
        });
        Ok(LlmResponse {
            content,
            input_tokens: req.messages.iter().map(|m| m.content.len() as u32 / 4).sum::<u32>() + 50,
            output_tokens: 200,
        })
    }

    fn model_name(&self) -> &str { "mock" }
}
