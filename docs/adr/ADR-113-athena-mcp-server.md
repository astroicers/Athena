# [ADR-113]: Athena 對外暴露 MCP Server（雙向 MCP）

| 欄位 | 內容 |
|------|------|
| **狀態** | `Accepted` |
| **日期** | 2026-05-10 |
| **決策者** | Athena Team |

## 背景

Athena 1.x 只作為 MCP client（呼叫 24 個工具容器）。若要讓外部 AI agent（Claude Code、其他 LLM）透過 MCP protocol 呼叫 Athena 的能力，需要 Athena 同時作為 MCP server。

## 決策

新增 `athena-mcp-server` crate，實作 MCP JSON-RPC 2024-11-05 協議：

- 端點：`POST /mcp` — 處理 `initialize`、`tools/list`、`tools/call`
- 初始工具集（5 個）：`athena_run_iteration`、`athena_list_facts`、`athena_c5isr_status`、`athena_generate_report`、`athena_abort_operation`
- 回應格式：`{"jsonrpc":"2.0","id":...,"result":{"content":[{"type":"text","text":"..."}]}}`
- 整合至 `athena-api` 的 axum router

## 後果

- 雙向 MCP：Athena 同時是 client（呼叫工具容器）和 server（被 Claude Code 呼叫）
- 工具清單可由外部 AI agent 動態探索（`tools/list`）

## 關聯

- 取代：ADR-024（單向 MCP client only）
- 依賴：ADR-102（headless API）、ADR-103（Bearer token）
