# SPEC: beta1-01 — athena-llm-client

| 欄位 | 內容 |
|------|------|
| **狀態** | `In Progress` |
| **ADR** | ADR-104 |
| **ROADMAP task** | beta1-01 |

## Goal

實作 LLM 客戶端，支援 Anthropic Claude（帶 prompt caching）和 OpenAI，以及 Mock 實作供測試使用。

## Done When

- [x] `LlmClient` trait（`complete()`, `model_name()`）
- [x] `MockLlmClient` — 可設定固定回應，用於測試
- [ ] `AnthropicClient` — reqwest 呼叫 Messages API，支援 prompt caching header
- [ ] `OpenAiClient` — reqwest 呼叫 Chat Completions API
- [ ] 單元測試：MockLlmClient 正確回傳設定的回應
- [ ] 整合測試（需要 API key）：Anthropic 真實呼叫

## Rollback Plan

純客戶端，無副作用。直接 revert。
