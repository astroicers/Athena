# OODA Pipeline — PhaseContext 資料流

> ADR-118 實作後的管道架構。所有圖以 Mermaid 語法撰寫，可在 GitHub、VSCode、Obsidian 直接渲染。

---

## 1. 正常模式（LLM 驅動）

```mermaid
sequenceDiagram
    participant API as POST /api/operations
    participant Engine as OodaEngine
    participant Obs as DefaultObserver
    participant Orient as ClaudeOrientEngine
    participant Decide as RiskMatrixDecider
    participant Act as ActRouter
    participant DB as PostgreSQL

    API->>DB: INSERT seed facts<br/>(target_ip)
    API->>Engine: run_iteration(op_id)

    Engine->>Engine: PhaseContext::new(op_id, iter_id)

    Engine->>Obs: observe.run(ctx)
    Obs->>DB: fact_repo.list(op_id)
    Obs->>Obs: collect() → nmap MCP call
    Obs->>DB: fact_repo.insert(open_port facts)
    Obs->>Obs: summarize() → obs_summary
    Obs-->>Engine: ctx.obs_summary = "N facts: ..."

    Engine->>Orient: orient.run(ctx)
    Orient->>Orient: analyze(obs_summary, graph)
    Note over Orient: Claude LLM call<br/>14 orient rules applied
    Orient-->>Engine: ctx.recommendation = OrientRecommendation<br/>risk_score, techniques, summary

    Engine->>Decide: decide.run(ctx, constraints)
    Decide->>Decide: risk_score > 0.80?
    alt risk_score ≤ 0.80
        Decide-->>Engine: ctx.decision = Decision{approved: true}
    else risk_score > 0.80
        Decide-->>Engine: ctx.decision = Decision{approved: false}<br/>"human approval required"
    end

    Engine->>Act: act.run(ctx)
    Act->>Act: route technique → SSH/MCP
    Act-->>Engine: ctx.outcome = ExecutionOutcome

    Engine-->>API: (iter_id, outcome)
```

---

## 2. Operator Override 模式（繞過 LLM 和 risk gate）

```mermaid
sequenceDiagram
    participant API as POST /api/operations<br/>mode=operator_override
    participant Engine as OodaEngine
    participant Obs as DefaultObserver
    participant Orient as OrientPhase
    participant Decide as DecidePhase
    participant Act as ActRouter
    participant DB as PostgreSQL

    API->>DB: INSERT seed facts<br/>(target_ip, operator_override)
    Note over DB: operator_override fact:<br/>"techniques=T1046,T1059 reason=..."
    API->>API: WARN log: "OPERATOR OVERRIDE"
    API->>Engine: run_iteration(op_id)

    Engine->>Engine: PhaseContext::new(op_id, iter_id)<br/>extensions = {}

    Engine->>Obs: observe.run(ctx)
    Obs->>DB: fact_repo.list(op_id)
    Obs->>Obs: lift_operator_override()
    Note over Obs: 解析 operator_override fact<br/>→ ctx.extensions["operator_override_techniques"]<br/>→ ctx.extensions["operator_override_reason"]
    Obs-->>Engine: ctx.extensions 已注入

    Engine->>Orient: orient.run(ctx)
    Orient->>Orient: operator_techniques() is_some()?
    Note over Orient: ✅ extensions 有值<br/>→ 跳過 LLM 完全不呼叫
    Orient-->>Engine: ctx.recommendation =<br/>OrientRecommendation{risk_score: 1.0,<br/>summary: "operator override — LLM skipped"}

    Engine->>Decide: decide.run(ctx, constraints)
    Decide->>Decide: operator_techniques() is_some()?
    Note over Decide: ✅ 直接核准<br/>→ 跳過 risk threshold 檢查
    Decide-->>Engine: ctx.decision =<br/>Decision{approved: true,<br/>reason: "operator override: <reason>"}

    Engine->>Act: act.run(ctx)
    Act->>Act: route T1046 → MCP nmap
    Act-->>Engine: ctx.outcome = ExecutionOutcome
    Note over Act: MCP 容器若未啟動則 WARN log<br/>但不中斷 iteration

    Engine-->>API: (iter_id, outcome)<br/>response: {mode: "operator_override"}
```

---

## 3. PhaseContext 結構與 extensions 傳遞路徑

```mermaid
graph LR
    subgraph PhaseContext
        A[op_id\niter_id]
        B[obs_summary\n由 Observe 填入]
        C[recommendation\n由 Orient 填入]
        D[decision\n由 Decide 填入]
        E[outcome\n由 Act 填入]
        F[extensions: HashMap\n自由 key-value]
    end

    subgraph "extensions 已知 key"
        G["attack_graph_summary\n由 Engine 注入\n給 Orient 使用"]
        H["operator_override_techniques\n由 Observe.lift() 注入\n給 Orient + Decide 短路"]
        I["operator_override_reason\n由 Observe.lift() 注入\n記錄在 Decision.reason"]
    end

    F --> G
    F --> H
    F --> I
```

---

## 4. 四個 Phase Trait 的熱插拔替換範圍

```mermaid
graph TD
    subgraph "可替換的實作（只改 main.rs 一行）"
        O1[DefaultObserver]
        O2[AgentlessObserver\n讀 CMDB 不跑 nmap]

        OR1[ClaudeOrientEngine\nAnthropic LLM]
        OR2[OllamaOrientEngine\n本地 LLM]
        OR3[PassthroughOrient\n不呼叫 LLM]

        D1[RiskMatrixDecider\nrisk > 0.80 擋住]
        D2[OperatorDirectDecider\n操作員直接指定技術]
        D3[AlwaysApproveDecider\n測試用]

        A1[ActRouter\nSSH + MCP 路由]
        A2[DryRunActRouter\n只 log 不執行]
    end

    subgraph "固定管道（改順序 = 改 engine.rs）"
        E[OodaEngine::run_iteration]
        E -->|run| OBSERVE[ObservePhase]
        OBSERVE -->|ctx| ORIENT[OrientPhase]
        ORIENT -->|ctx| DECIDE[DecidePhase]
        DECIDE -->|ctx| ACT[ActPhase]
    end

    O1 -.->|實作| OBSERVE
    O2 -.->|實作| OBSERVE
    OR1 -.->|實作| ORIENT
    OR2 -.->|實作| ORIENT
    OR3 -.->|實作| ORIENT
    D1 -.->|實作| DECIDE
    D2 -.->|實作| DECIDE
    D3 -.->|實作| DECIDE
    A1 -.->|實作| ACT
    A2 -.->|實作| ACT
```

---

## 5. Operator Override API 呼叫範例

```bash
# 正常模式（LLM 驅動 + risk gate）
curl -X POST http://localhost:58000/api/operations \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "recon-192.168.0.28",
    "target_ip": "192.168.0.28"
  }'

# Operator Override（risk 0.95 已人工批准，跳過 LLM）
curl -X POST http://localhost:58000/api/operations \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "approved-attack",
    "target_ip": "192.168.0.28",
    "mode": "operator_override",
    "operator_techniques": ["T1046", "T1059.004"],
    "override_reason": "risk 0.95 approved by team lead 2026-05-11"
  }'
```

**Log 驗證點**（確認路徑正確）：

| Log 行 | 正常模式 | Override 模式 |
|--------|---------|--------------|
| `ORIENT: entering phase` | 接著呼叫 LLM | 直接短路 |
| `ORIENT complete summary=` | Claude 分析文字 | `"operator override — LLM skipped"` |
| `DECIDE complete approved=` | `true`/`false` 視 risk | 永遠 `true` |
| `DECIDE complete reason=` | `"Approved N technique(s)..."` | `"operator override: <reason>"` |

---

## 6. 三層緩解計劃執行狀態

```mermaid
gantt
    title OODA Pipeline 彈性緩解計劃
    dateFormat YYYY-MM-DD
    section 層 1 — 戰術短路
        OperatorDirectDecider      :done, 2026-05-11, 1d
        PassthroughOrient          :done, 2026-05-11, 1d
        API mode=operator_override :done, 2026-05-11, 1d
    section 層 2 — PhaseContext（ADR-118）
        PhaseContext 型別          :done, 2026-05-11, 1d
        四個 phase trait run()     :done, 2026-05-11, 1d
        Observe lift_operator      :done, 2026-05-11, 1d
        端對端驗證                  :done, 2026-05-11, 1d
    section 層 3 — 可配置 Pipeline（2.1）
        Phase Registry             :2026-06-01, 14d
        athena.toml pipeline config :2026-06-01, 14d
        動態 dispatch               :2026-06-01, 14d
```
