use serde::{Deserialize, Serialize};
use uuid::Uuid;
use ipnetwork::IpNetwork;

#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct TargetId(pub Uuid);

impl TargetId {
    pub fn new() -> Self { Self(Uuid::new_v4()) }
}

impl Default for TargetId {
    fn default() -> Self { Self::new() }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Target {
    pub id: TargetId,
    pub hostname: Option<String>,
    pub ip: Option<IpNetwork>,
    pub os: Option<String>,
    pub tags: Vec<String>,
}
