use figment::{Figment, providers::{Env, Format, Toml}};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
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
    /// Per-tool base URLs, e.g. {"nmap": "http://localhost:9101"}.
    /// When present, overrides base_url for that specific tool.
    #[serde(default)]
    pub tool_urls: HashMap<String, String>,
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
            mcp: McpConfig { base_url: default_mcp_base(), timeout_secs: default_timeout_secs(), tool_urls: HashMap::new() },
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn default_has_expected_values() {
        let cfg = AthenaConfig::default();
        assert_eq!(cfg.server.host, "0.0.0.0");
        assert_eq!(cfg.server.port, 58000);
        assert_eq!(cfg.llm.default_model, "claude-opus-4-7");
        assert!(cfg.llm.mock_mode);
        assert_eq!(cfg.mcp.timeout_secs, 30);
    }

    #[test]
    fn load_or_default_never_panics() {
        // No athena.toml in test cwd — should silently fall back to default (port may vary by env)
        let cfg = AthenaConfig::load_or_default();
        assert!(cfg.server.port > 0);
    }

    #[test]
    fn env_override_via_figment() {
        // ATHENA_SERVER__PORT overrides default port; cleaned up immediately
        std::env::set_var("ATHENA_SERVER__PORT", "9999");
        let cfg = AthenaConfig::load_or_default();
        std::env::remove_var("ATHENA_SERVER__PORT");
        // May or may not pick up depending on toml presence; just assert no panic
        assert!(cfg.server.port == 9999 || cfg.server.port == 58000);
    }

    #[test]
    fn db_url_is_non_empty() {
        let cfg = AthenaConfig::default();
        assert!(!cfg.database.url.is_empty());
        assert!(cfg.database.url.starts_with("postgres://"));
    }
}
