use athena_events::{EventBus, AthenaEvent};
use axum::extract::ws::{WebSocket, Message};
use std::sync::Arc;
use tokio::sync::broadcast;
use serde_json;

pub struct WsGateway {
    event_bus: Arc<EventBus>,
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
                                if socket.send(Message::Text(json)).await.is_err() {
                                    break;
                                }
                            }
                        }
                        Err(broadcast::error::RecvError::Closed) => break,
                        Err(broadcast::error::RecvError::Lagged(_)) => continue,
                    }
                }
                msg = socket.recv() => {
                    if msg.is_none() { break; }
                }
            }
        }
    }
}
