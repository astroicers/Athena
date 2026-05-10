use serde::{Deserialize, Serialize};
use tokio::sync::broadcast;
use athena_types::{OperationId, OodaIterationId};

pub const EVENT_BUS_CAPACITY: usize = 1024;

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "type", rename_all = "snake_case")]
pub enum AthenaEvent {
    OperationStarted { op_id: OperationId },
    OperationCompleted { op_id: OperationId },
    OperationAborted { op_id: OperationId, reason: String },
    OodaIterationStarted { op_id: OperationId, iter_id: OodaIterationId },
    OodaIterationCompleted { op_id: OperationId, iter_id: OodaIterationId, facts_collected: usize },
    FactCollected { op_id: OperationId, trait_name: String, value: String },
    DecisionMade { op_id: OperationId, approved: bool, techniques: Vec<String> },
    ExecutionStarted { op_id: OperationId, technique_id: String },
    ExecutionCompleted { op_id: OperationId, technique_id: String, success: bool },
    AlertRaised { op_id: OperationId, severity: AlertSeverity, message: String },
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum AlertSeverity {
    Info,
    Warning,
    Critical,
}

pub struct EventBus {
    tx: broadcast::Sender<AthenaEvent>,
}

impl EventBus {
    pub fn new() -> Self {
        let (tx, _) = broadcast::channel(EVENT_BUS_CAPACITY);
        Self { tx }
    }

    pub fn publish(&self, event: AthenaEvent) {
        let _ = self.tx.send(event);
    }

    pub fn subscribe(&self) -> broadcast::Receiver<AthenaEvent> {
        self.tx.subscribe()
    }
}

impl Default for EventBus {
    fn default() -> Self { Self::new() }
}
