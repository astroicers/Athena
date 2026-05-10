use athena_events::{EventBus, AthenaEvent};
use axum::{
    Router,
    extract::{State, WebSocketUpgrade, ws::{WebSocket, Message}},
    response::Response,
    routing::get,
};
use std::sync::Arc;
use tokio::sync::broadcast;
use tracing::debug;

pub struct WsGateway {
    pub event_bus: Arc<EventBus>,
}

impl WsGateway {
    pub fn new(event_bus: Arc<EventBus>) -> Self {
        Self { event_bus }
    }

    pub async fn handle_socket(&self, mut socket: WebSocket) {
        let mut rx: broadcast::Receiver<AthenaEvent> = self.event_bus.subscribe();
        loop {
            tokio::select! {
                msg = rx.recv() => {
                    match msg {
                        Ok(event) => {
                            if let Ok(json) = serde_json::to_string(&event) {
                                debug!(event = %json, "ws broadcast");
                                if socket.send(Message::Text(json.into())).await.is_err() {
                                    break;
                                }
                            }
                        }
                        Err(broadcast::error::RecvError::Closed) => break,
                        Err(broadcast::error::RecvError::Lagged(_)) => continue,
                    }
                }
                msg = socket.recv() => {
                    // client closed or sent something; ignore payload, only watch for close
                    if msg.is_none() { break; }
                }
            }
        }
    }
}

// ── axum route ───────────────────────────────────────────────────────────────

async fn ws_upgrade_handler(
    State(gateway): State<Arc<WsGateway>>,
    ws: WebSocketUpgrade,
) -> Response {
    ws.on_upgrade(move |socket| async move {
        gateway.handle_socket(socket).await;
    })
}

pub fn ws_routes(gateway: Arc<WsGateway>) -> Router {
    Router::new()
        .route("/ws", get(ws_upgrade_handler))
        .with_state(gateway)
}

#[cfg(test)]
mod tests {
    use super::*;
    use tokio::time::{timeout, Duration};

    #[tokio::test]
    async fn event_bus_subscriber_receives_event() {
        let bus = Arc::new(EventBus::new());
        let mut rx = bus.subscribe();

        let op_id = athena_types::OperationId::new();
        bus.publish(AthenaEvent::OperationStarted { op_id: op_id.clone() });

        let event = timeout(Duration::from_millis(100), rx.recv()).await
            .expect("timeout").expect("recv error");
        assert!(matches!(event, AthenaEvent::OperationStarted { .. }));
    }

    #[tokio::test]
    async fn gateway_routes_registered() {
        let bus = Arc::new(EventBus::new());
        let gateway = Arc::new(WsGateway::new(bus));
        // Just verify the router is constructible (route registration panics on duplicate)
        let _router = ws_routes(gateway);
    }

    #[tokio::test]
    async fn lagged_receiver_continues() {
        let bus = Arc::new(EventBus::new());
        let mut rx = bus.subscribe();

        // Flood the channel beyond capacity to trigger Lagged error
        for _ in 0..1100 {
            bus.publish(AthenaEvent::AlertRaised {
                op_id: athena_types::OperationId::new(),
                severity: athena_events::AlertSeverity::Info,
                message: "flood".into(),
            });
        }

        // Receiver should be able to continue receiving (either Lagged or Ok)
        let _result = rx.recv().await;
        // No panic = pass
    }
}
