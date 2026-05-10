use figment::{Figment, providers::{Env, Format, Toml}};
use serde::{Deserialize, Serialize};
use thiserror::Error;

#[derive(Debug, Error)]
pub enum ConfigError {
    #[error("config load error: {0}")]
    Load(#[from] figment::Error),
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AthenaConfig {
    pub server: ServerConfig,
    pub database: DatabaseConfig,
    pub llm: LlmConfig,
    pub mcp: McpConfig,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ServerConfig {
    #[serde(default = "default_host")]
    pub host: String,
    #[serde(default = "default_port")]
    pub port: u16,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DatabaseConfig {
    pub url: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LlmConfig {
    pub anthropic_api_key: Option<String>,
    pub openai_api_key: Option<String>,
    #[serde(default = "default_model")]
    pub default_model: String,
    pub mock_mode: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct McpConfig {
    #[serde(default = "default_mcp_base")]
    pub base_url: String,
    #[serde(default = "default_timeout_secs")]
    pub timeout_secs: u64,
}

fn default_host() -> String { "0.0.0.0".into() }
fn default_port() -> u16 { 58000 }
fn default_model() -> String { "claude-opus-4-7".into() }
fn default_mcp_base() -> String { "http://localhost".into() }
fn default_timeout_secs() -> u64 { 30 }

impl AthenaConfig {
    pub fn load() -> Result<Self, ConfigError> {
        let config = Figment::new()
            .merge(Toml::file("athena.toml"))
            .merge(Env::prefixed("ATHENA_").split("__"))
            .extract()?;
        Ok(config)
    }

    pub fn load_or_default() -> Self {
        Self::load().unwrap_or_else(|_| Self::default())
    }
}

impl Default for AthenaConfig {
    fn default() -> Self {
        Self {
            server: ServerConfig { host: default_host(), port: default_port() },
            database: DatabaseConfig { url: "postgres://athena:athena@localhost:5432/athena".into() },
            llm: LlmConfig {
                anthropic_api_key: None,
                openai_api_key: None,
                default_model: default_model(),
                mock_mode: true,
            },
            mcp: McpConfig { base_url: default_mcp_base(), timeout_secs: default_timeout_secs() },
        }
    }
}
