# [ADR-106]: athena-events 型別總線取代直接 ws_manager 呼叫

| 欄位 | 內容 |
|------|------|
| **狀態** | `Accepted` |
| **日期** | 2026-05-10 |
| **決策者** | Athena Team |

## 背景

v1.x 有 14 個服務直接持有 `ws_manager` 參照並呼叫 `broadcast()`，形成上帝物件。任何服務都無法在不持有 ws_manager 的情況下廣播事件。

## 決策

建立 `athena-events::EventBus`（基於 `tokio::sync::broadcast`）作為唯一的事件發布點。所有 crate 只透過 `EventBus::publish(AthenaEvent)` 發送事件，永遠不直接觸碰 WebSocket。`athena-ws::WsGateway` 作為唯一的訂閱者，負責將事件廣播到 WebSocket 連線。

## 關聯

- 取代：ADR-007（隱含）
