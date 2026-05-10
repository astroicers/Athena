use async_trait::async_trait;
use athena_types::{OperationId, AthenaError};
use dashmap::DashMap;
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OpsecStatus {
    pub noise_level: u8,
    pub threat_level: ThreatLevel,
    pub remaining_budget: i32,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum ThreatLevel {
    Green,
    Yellow,
    Orange,
    Red,
}

impl ThreatLevel {
    fn from_noise(noise: u8) -> Self {
        match noise {
            0..=3 => ThreatLevel::Green,
            4..=5 => ThreatLevel::Yellow,
            6..=7 => ThreatLevel::Orange,
            _ => ThreatLevel::Red,
        }
    }
}

#[async_trait]
pub trait OpsecMonitor: Send + Sync {
    async fn status(&self, op_id: &OperationId) -> Result<OpsecStatus, AthenaError>;
    async fn consume_budget(&self, op_id: &OperationId, cost: i32) -> Result<(), AthenaError>;
}

pub struct InMemoryOpsecMonitor {
    max_budget: i32,
    // per-op: (accumulated_noise, budget_consumed)
    state: DashMap<String, (u8, i32)>,
}

impl InMemoryOpsecMonitor {
    pub fn new(max_budget: i32) -> Self {
        Self { max_budget, state: DashMap::new() }
    }
}

#[async_trait]
impl OpsecMonitor for InMemoryOpsecMonitor {
    async fn status(&self, op_id: &OperationId) -> Result<OpsecStatus, AthenaError> {
        let key = op_id.to_string();
        let (noise, consumed) = self.state.get(&key)
            .map(|e| *e.value())
            .unwrap_or((0, 0));
        Ok(OpsecStatus {
            noise_level: noise,
            threat_level: ThreatLevel::from_noise(noise),
            remaining_budget: self.max_budget - consumed,
        })
    }

    async fn consume_budget(&self, op_id: &OperationId, cost: i32) -> Result<(), AthenaError> {
        let key = op_id.to_string();
        let mut entry = self.state.entry(key).or_insert((0, 0));
        let (noise, consumed) = entry.value_mut();
        *consumed += cost;
        // Noise grows logarithmically with consumption
        *noise = ((*consumed as f32).log2().max(0.0) as u8).min(10);
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn initial_status_is_green_full_budget() {
        let monitor = InMemoryOpsecMonitor::new(100);
        let op_id = OperationId::new();
        let status = monitor.status(&op_id).await.unwrap();
        assert_eq!(status.threat_level, ThreatLevel::Green);
        assert_eq!(status.remaining_budget, 100);
        assert_eq!(status.noise_level, 0);
    }

    #[tokio::test]
    async fn consume_reduces_budget() {
        let monitor = InMemoryOpsecMonitor::new(100);
        let op_id = OperationId::new();
        monitor.consume_budget(&op_id, 40).await.unwrap();
        let status = monitor.status(&op_id).await.unwrap();
        assert_eq!(status.remaining_budget, 60);
    }

    #[tokio::test]
    async fn high_consumption_raises_threat_level() {
        let monitor = InMemoryOpsecMonitor::new(1000);
        let op_id = OperationId::new();
        monitor.consume_budget(&op_id, 200).await.unwrap();
        let status = monitor.status(&op_id).await.unwrap();
        assert!(status.noise_level >= 4, "High consumption should raise noise");
        assert!(status.threat_level != ThreatLevel::Green);
    }

    #[test]
    fn threat_level_thresholds() {
        assert_eq!(ThreatLevel::from_noise(0), ThreatLevel::Green);
        assert_eq!(ThreatLevel::from_noise(4), ThreatLevel::Yellow);
        assert_eq!(ThreatLevel::from_noise(6), ThreatLevel::Orange);
        assert_eq!(ThreatLevel::from_noise(9), ThreatLevel::Red);
    }
}
