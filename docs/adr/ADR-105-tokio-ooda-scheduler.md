# [ADR-105]: tokio 定時器驅動 OODA Scheduler

| 欄位 | 內容 |
|------|------|
| **狀態** | `Accepted` |
| **日期** | 2026-05-10 |
| **決策者** | Athena Team |

## 背景

v1.x 使用 APScheduler（Python）管理 OODA 循環計時，耦合在 FastAPI 中。需要一個更乾淨的非同步計時機制。

## 決策

`athena-scheduler` 使用 `tokio::time::interval` 為每個 Operation 建立獨立的非同步循環，透過 `Arc<dyn DecisionEngine>` 驅動 OODA 迭代。每個 Operation 的 scheduler handle 存放在 `DashMap<OperationId, JoinHandle<()>>`。

## 關聯

- 取代：ADR-023（隱含）
