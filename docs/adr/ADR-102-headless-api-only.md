# [ADR-102]: 無前端、純 API 架構

| 欄位 | 內容 |
|------|------|
| **狀態** | `Accepted` |
| **日期** | 2026-05-10 |
| **決策者** | Athena Team |

## 背景

Athena 1.x 包含 Next.js 前端，但 UI 開發拖慢後端進度，且 Claude 作為主要操作介面使 UI 的必要性降低。

## 決策

Athena 2.0 為 **headless API-only**。所有互動透過：
1. HTTP REST API（`athena-api`，axum）
2. MCP Server（`athena-mcp-server`）
3. WebSocket 事件流（`athena-ws`）

前端作為獨立專案，不在 2.0 範圍內。

## 關聯

- 取代：ADR-009（隱含）
