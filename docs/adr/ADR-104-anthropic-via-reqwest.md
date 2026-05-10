# [ADR-104]: 透過 reqwest 呼叫 Anthropic API（無官方 Rust SDK）

| 欄位 | 內容 |
|------|------|
| **狀態** | `Accepted` |
| **日期** | 2026-05-10 |
| **決策者** | Athena Team |

## 背景

Anthropic 尚未提供官方 Rust SDK。需要決定如何從 Rust 呼叫 Claude API。

## 決策

使用 `reqwest 0.12`（rustls-tls feature，無 OpenSSL 依賴）直接構造 HTTP 請求呼叫 Anthropic Messages API。實作封裝在 `athena-llm-client::AnthropicClient`，對外暴露 `LlmClient` trait。

啟用 Anthropic prompt caching（`cache_control: {"type": "ephemeral"}`）於 system prompt，減少重複的 orient phase token 費用。

## 關聯

- 取代：ADR-014（隱含）
