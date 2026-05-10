# SPEC: beta1-06 — athena-orient

| 欄位 | 內容 |
|------|------|
| **狀態** | `Pending` |
| **ADR** | ADR-104, ADR-109 |
| **ROADMAP task** | beta1-06 |

## Goal

實作 OODA 定向階段，呼叫 LLM 分析觀察摘要和攻擊圖，回傳結構化的 OrientRecommendation。

## Orient Rules（移植自 v1.x orient_engine.py）

system prompt 包含以下規則（1-14）：
1. 優先低噪音技術
2. 僅推薦授權範圍內目標
3. 風險評分 0.0~1.0，>0.7 需要人工審核
4. 推薦技術必須有對應 MCP 工具
5-14. （其餘規則在實作時從架構文件移植）

## Done When

- [ ] `OrientPhase` trait（`analyze(op_id, obs_summary, graph_summary)`）
- [ ] `ClaudeOrientEngine` — 建構 system prompt + user prompt，呼叫 `LlmClient`，解析 JSON 回應為 `OrientRecommendation`
- [ ] `MockOrientEngine` — 回傳固定 OrientRecommendation
- [ ] 單元測試：MockOrientEngine，以及 JSON 解析邏輯

## Rollback Plan

純 LLM 呼叫，無副作用。直接 revert。
