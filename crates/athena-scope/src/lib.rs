use async_trait::async_trait;
use athena_types::{Target, AthenaError};
use ipnetwork::IpNetwork;
use std::net::IpAddr;

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

// In-memory scope list: a set of allowed CIDRs + optional explicit hostnames
pub struct CidrScopeValidator {
    allowed_networks: Vec<IpNetwork>,
    allowed_hostnames: Vec<String>,
    deny_all_by_default: bool,
}

impl CidrScopeValidator {
    pub fn new(allowed_networks: Vec<IpNetwork>, allowed_hostnames: Vec<String>) -> Self {
        Self {
            allowed_networks,
            allowed_hostnames,
            deny_all_by_default: true,
        }
    }

    pub fn allow_all() -> Self {
        Self {
            allowed_networks: vec![],
            allowed_hostnames: vec![],
            deny_all_by_default: false,
        }
    }

    fn ip_in_scope(&self, ip: IpAddr) -> bool {
        if !self.deny_all_by_default { return true; }
        self.allowed_networks.iter().any(|net| net.contains(ip))
    }
}

#[async_trait]
impl ScopeValidator for CidrScopeValidator {
    async fn is_in_scope(&self, target: &Target) -> Result<bool, AthenaError> {
        if !self.deny_all_by_default {
            return Ok(true);
        }

        // Check IP
        if let Some(ref net) = target.ip {
            if self.ip_in_scope(net.ip()) {
                return Ok(true);
            }
        }

        // Check hostname
        if let Some(ref h) = target.hostname {
            if self.allowed_hostnames.iter().any(|allowed| allowed == h) {
                return Ok(true);
            }
        }

        Ok(false)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use athena_types::{TargetId};

    fn target(ip: Option<&str>, hostname: Option<&str>) -> Target {
        Target {
            id: TargetId::new(),
            hostname: hostname.map(|s| s.into()),
            ip: ip.and_then(|s| s.parse().ok()),
            os: None,
            tags: vec![],
        }
    }

    #[tokio::test]
    async fn ip_in_scope_cidr() {
        let validator = CidrScopeValidator::new(
            vec!["10.0.0.0/24".parse().unwrap()],
            vec![],
        );
        assert!(validator.is_in_scope(&target(Some("10.0.0.5/32"), None)).await.unwrap());
        assert!(!validator.is_in_scope(&target(Some("192.168.1.1/32"), None)).await.unwrap());
    }

    #[tokio::test]
    async fn hostname_in_scope() {
        let validator = CidrScopeValidator::new(
            vec![],
            vec!["target.internal".into()],
        );
        assert!(validator.is_in_scope(&target(None, Some("target.internal"))).await.unwrap());
        assert!(!validator.is_in_scope(&target(None, Some("evil.com"))).await.unwrap());
    }

    #[tokio::test]
    async fn allow_all_permits_everything() {
        let validator = CidrScopeValidator::allow_all();
        assert!(validator.is_in_scope(&target(Some("8.8.8.8/32"), None)).await.unwrap());
    }

    #[tokio::test]
    async fn assert_in_scope_returns_err_for_out_of_scope() {
        let validator = CidrScopeValidator::new(vec![], vec![]);
        let result = validator.assert_in_scope(&target(Some("1.2.3.4/32"), None)).await;
        assert!(matches!(result, Err(AthenaError::OutOfScope(_))));
    }
}
