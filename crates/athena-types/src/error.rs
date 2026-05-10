use thiserror::Error;

#[derive(Debug, Error)]
pub enum AthenaError {
    #[error("operation not found: {0}")]
    OperationNotFound(String),
    #[error("target out of scope: {0}")]
    OutOfScope(String),
    #[error("decision blocked: {0}")]
    DecisionBlocked(String),
    #[error("execution failed: {0}")]
    ExecutionFailed(String),
    #[error("mcp error: {0}")]
    McpError(String),
    #[error("llm error: {0}")]
    LlmError(String),
    #[error("database error: {0}")]
    DatabaseError(String),
    #[error("config error: {0}")]
    ConfigError(String),
    #[error("internal: {0}")]
    Internal(String),
}
