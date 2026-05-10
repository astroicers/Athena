use async_trait::async_trait;
use athena_types::{Target, AthenaError};

#[async_trait]
pub trait ScopeValidator: Send + Sync {
    async fn is_in_scope(&self, target: &Target) -> Result<bool, AthenaError>;
    async fn assert_in_scope(&self, target: &Target) -> Result<(), AthenaError> {
        if self.is_in_scope(target).await? {
            Ok(())
        } else {
            Err(AthenaError::OutOfScope(format!("{:?}", target.id)))
        }
    }
}
