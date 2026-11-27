// SPDX-License-Identifier: Apache-2.0
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

/// Retryability class for an [`AthenaError`] (ADR-152 / C3).
///
/// `Transient` = retrying the SAME operation may succeed (an infra blip — network,
/// model-load, DB hiccup). `Permanent` = re-issuing the same op cannot change the outcome.
///
/// This axis is ORTHOGONAL to ADR-151's "advance to the NEXT exploit candidate": that
/// decision is driven by `shell_landed` + the candidate list, NOT by this class. So
/// `ExecutionFailed` is `Permanent` (re-running the SAME exploit won't help) even though a
/// failed exploit is exactly the case ADR-151's loop falls through on.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ErrorClass {
    Transient,
    Permanent,
}

impl AthenaError {
    /// Stable machine code per variant (e.g. `"mcp_error"`). For classification and a future
    /// API error layer. The string is part of the contract — do not change it for a variant.
    pub fn code(&self) -> &'static str {
        match self {
            AthenaError::OperationNotFound(_) => "operation_not_found",
            AthenaError::OutOfScope(_) => "out_of_scope",
            AthenaError::DecisionBlocked(_) => "decision_blocked",
            AthenaError::ExecutionFailed(_) => "execution_failed",
            AthenaError::McpError(_) => "mcp_error",
            AthenaError::LlmError(_) => "llm_error",
            AthenaError::DatabaseError(_) => "database_error",
            AthenaError::ConfigError(_) => "config_error",
            AthenaError::Internal(_) => "internal",
        }
    }

    /// Transient/Permanent classification (ADR-152). See [`ErrorClass`].
    pub fn class(&self) -> ErrorClass {
        match self {
            // Infra blips — retrying the SAME op may succeed.
            AthenaError::McpError(_)
            | AthenaError::LlmError(_)
            | AthenaError::DatabaseError(_) => ErrorClass::Transient,
            // Re-issuing the same op cannot change the outcome.
            AthenaError::OperationNotFound(_)
            | AthenaError::OutOfScope(_)
            | AthenaError::DecisionBlocked(_)
            | AthenaError::ExecutionFailed(_)
            | AthenaError::ConfigError(_)
            | AthenaError::Internal(_) => ErrorClass::Permanent,
        }
    }

    /// True if retrying the SAME operation may succeed (ADR-152). Consumed by ADR-151's
    /// candidate loop to decide retry-same-candidate (transient) vs advance (permanent).
    pub fn is_retryable(&self) -> bool {
        matches!(self.class(), ErrorClass::Transient)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn transient_variants_are_retryable() {
        for e in [
            AthenaError::McpError("x".into()),
            AthenaError::LlmError("x".into()),
            AthenaError::DatabaseError("x".into()),
        ] {
            assert_eq!(e.class(), ErrorClass::Transient, "{} should be Transient", e.code());
            assert!(e.is_retryable(), "{} should be retryable", e.code());
        }
    }

    #[test]
    fn permanent_variants_are_not_retryable() {
        // ADR-152: ExecutionFailed is Permanent (NOT Transient) — fall-through-to-next-exploit
        // is ADR-151's job, orthogonal to is_retryable().
        for e in [
            AthenaError::OperationNotFound("x".into()),
            AthenaError::OutOfScope("x".into()),
            AthenaError::DecisionBlocked("x".into()),
            AthenaError::ExecutionFailed("x".into()),
            AthenaError::ConfigError("x".into()),
            AthenaError::Internal("x".into()),
        ] {
            assert_eq!(e.class(), ErrorClass::Permanent, "{} should be Permanent", e.code());
            assert!(!e.is_retryable(), "{} should NOT be retryable", e.code());
        }
    }

    #[test]
    fn codes_are_unique_across_all_variants() {
        let codes = [
            AthenaError::OperationNotFound(String::new()).code(),
            AthenaError::OutOfScope(String::new()).code(),
            AthenaError::DecisionBlocked(String::new()).code(),
            AthenaError::ExecutionFailed(String::new()).code(),
            AthenaError::McpError(String::new()).code(),
            AthenaError::LlmError(String::new()).code(),
            AthenaError::DatabaseError(String::new()).code(),
            AthenaError::ConfigError(String::new()).code(),
            AthenaError::Internal(String::new()).code(),
        ];
        let mut uniq = codes.to_vec();
        uniq.sort_unstable();
        uniq.dedup();
        assert_eq!(uniq.len(), codes.len(), "every variant must have a unique code");
    }
}
