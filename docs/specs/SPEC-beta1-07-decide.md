# SPEC: beta1-07 — athena-decide

| 欄位 | 內容 |
|------|------|
| **狀態** | `Pending` |
| **ADR** | ADR-101, ADR-109 |
| **ROADMAP task** | beta1-07 |

## Goal

實作 OODA 決策階段，根據 OrientRecommendation 和 OperationalConstraints 決定是否批准執行及選擇技術。

## Done When

- [ ] `DecidePhase` trait（`evaluate(op_id, recommendation, constraints)`）
- [ ] `RiskMatrixDecider` — 若 risk_score > constraints.require_approval_above_risk，拒絕；否則過濾 denied_techniques，回傳批准的 Decision
- [ ] `MockDecider` — 可設定 approved=true/false
- [ ] 單元測試：高風險拒絕、低風險批准、denied_techniques 過濾

## Rollback Plan

純邏輯，無副作用。直接 revert。
