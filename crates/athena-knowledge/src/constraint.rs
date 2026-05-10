use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OperationalConstraints {
    pub max_noise_level: u8,
    pub allowed_techniques: Vec<String>,
    pub denied_techniques: Vec<String>,
    pub time_window_hours: Option<u8>,
    pub require_approval_above_risk: Option<f32>,
}

impl Default for OperationalConstraints {
    fn default() -> Self {
        Self {
            max_noise_level: 5,
            allowed_techniques: vec![],
            denied_techniques: vec![],
            time_window_hours: None,
            require_approval_above_risk: Some(0.8),
        }
    }
}
