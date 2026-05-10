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

#[cfg(test)]
mod tests {
    use super::*;
    use athena_types::OperationId;

    #[tokio::test]
    async fn publish_and_receive() {
        let bus = EventBus::new();
        let mut rx = bus.subscribe();

        let op_id = OperationId::new();
        bus.publish(AthenaEvent::OperationStarted { op_id: op_id.clone() });

        let received = rx.recv().await.unwrap();
        match received {
            AthenaEvent::OperationStarted { op_id: received_id } => {
                assert_eq!(received_id, op_id);
            }
            _ => panic!("unexpected event type"),
        }
    }

    #[tokio::test]
    async fn multiple_subscribers_each_receive() {
        let bus = EventBus::new();
        let mut rx1 = bus.subscribe();
        let mut rx2 = bus.subscribe();

        let op_id = OperationId::new();
        bus.publish(AthenaEvent::OperationCompleted { op_id: op_id.clone() });

        let e1 = rx1.recv().await.unwrap();
        let e2 = rx2.recv().await.unwrap();
        assert!(matches!(e1, AthenaEvent::OperationCompleted { .. }));
        assert!(matches!(e2, AthenaEvent::OperationCompleted { .. }));
    }

    #[tokio::test]
    async fn no_subscriber_does_not_panic() {
        let bus = EventBus::new();
        let op_id = OperationId::new();
        // publish with no subscribers should not panic
        bus.publish(AthenaEvent::OperationAborted {
            op_id,
            reason: "test".into(),
        });
    }

    #[test]
    fn alert_severity_serde() {
        let s = serde_json::to_string(&AlertSeverity::Critical).unwrap();
        assert_eq!(s, "\"critical\"");
    }
}
