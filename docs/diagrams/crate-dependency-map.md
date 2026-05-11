# Athena 2.0 — Crate 依賴圖與職責

> ADR-101 鐵律：執行引擎 crate 不得互相依賴；所有 SQL 只在 athena-db。

---

## 1. 完整 Crate 依賴圖

```mermaid
graph TD
    %% Foundation（零依賴層）
    subgraph foundation["Foundation（零依賴）"]
        TYPES[athena-types\n所有 domain struct + PhaseContext]
        TELEM[athena-telemetry\ntracing + Prometheus]
    end

    %% Infrastructure
    subgraph infra["Infrastructure"]
        CONFIG[athena-config\nfigment toml+env]
        DB[athena-db\nsqlx PostgreSQL migrations]
        EVENTS[athena-events\ntyped pub-sub EventBus]
    end

    %% Knowledge & Policy
    subgraph knowledge["Knowledge & Policy"]
        KNOW[athena-knowledge\nOperationalConstraints]
        POLICY[athena-policy\nRoE PolicyEngine]
        KB[athena-pentest-kb\nTantivyKnowledgeBase]
        SKILLS[athena-skills-loader\nFileSystemSkillsLoader]
        SCOPE[athena-scope\nCidrScopeValidator]
    end

    %% Client Layer
    subgraph clients["Clients"]
        LLM[athena-llm-client\nAnthropicClient MockLlmClient]
        MCP[athena-mcp-client\nStreamableMcpClient\ncircuit breaker]
        EXTRACTOR[athena-mcp-fact-extractor\nFastMCP → Fact]
    end

    %% OODA Phases
    subgraph phases["OODA Phases（Arc dyn Trait）"]
        OBS[athena-observe\nDefaultObserver\nObservePhase]
        ORI[athena-orient\nClaudeOrientEngine\nPassthroughOrient\nOrientPhase]
        DEC[athena-decide\nRiskMatrixDecider\nOperatorDirectDecider\nDecidePhase]
        ACT_LIB[athena-act\nActRouter\nActPhase]
    end

    %% Execution Engines
    subgraph exec["Execution Engines（互不依賴）"]
        SSH[athena-exec-ssh\nrussh SshExecutionEngine]
        META[athena-exec-metasploit\n2.1 stub]
        C2[athena-exec-c2\n2.1 stub]
        WINRM[athena-exec-winrm\n2.1 stub]
    end

    %% Intelligence
    subgraph intel["Intelligence"]
        ATTACK[athena-attack-graph\nDijkstraAttackGraph]
        OPSEC[athena-opsec\nInMemoryOpsecMonitor]
        C5ISR[athena-c5isr\nFactDrivenC5isrMapper]
        VULN[athena-vuln\nNvdClient]
        RECON[athena-recon\nMcpReconEngine]
        BRIEF[athena-brief\nFactBriefGenerator]
        REPORT[athena-report\nFactReportGenerator]
    end

    %% Core Engine
    ENGINE[athena-engine-ooda\nOodaEngine\nDecisionEngine trait]
    FACTS[athena-facts\nSqlxFactRepository\nSqlxIterationStore]
    SWARM[athena-swarm\nParallelSwarm]
    SCHED[athena-scheduler\nOodaScheduler]

    %% API & Binary
    API[athena-api\naxum router AppState]
    BIN[athena-workspace\nmain.rs DI wiring]

    %% Dependency edges
    TYPES --> CONFIG
    TYPES --> DB
    TYPES --> EVENTS
    TYPES --> KNOW
    TYPES --> POLICY
    TYPES --> KB
    TYPES --> SKILLS
    TYPES --> SCOPE
    TYPES --> LLM
    TYPES --> MCP
    TYPES --> EXTRACTOR
    TYPES --> OBS
    TYPES --> ORI
    TYPES --> DEC
    TYPES --> ACT_LIB
    TYPES --> SSH
    TYPES --> ATTACK
    TYPES --> OPSEC
    TYPES --> C5ISR
    TYPES --> VULN
    TYPES --> RECON
    TYPES --> BRIEF
    TYPES --> REPORT
    TYPES --> ENGINE
    TYPES --> FACTS
    TYPES --> SWARM
    TYPES --> SCHED
    TYPES --> API

    DB --> FACTS
    FACTS --> OBS
    FACTS --> C5ISR
    FACTS --> BRIEF
    FACTS --> REPORT
    FACTS --> API

    MCP --> OBS
    MCP --> ACT_LIB
    MCP --> RECON
    EXTRACTOR --> OBS
    EXTRACTOR --> ACT_LIB

    LLM --> ORI
    KB --> ORI
    SKILLS --> ORI
    KNOW --> DEC
    POLICY --> DEC
    SSH --> ACT_LIB
    ATTACK --> ENGINE
    OBS --> ENGINE
    ORI --> ENGINE
    DEC --> ENGINE
    ACT_LIB --> ENGINE
    ACT_LIB --> SWARM
    ENGINE --> SCHED
    ENGINE --> API
    FACTS --> API
    SCHED --> API
    SCOPE --> API
    OPSEC --> API
    C5ISR --> API
    VULN --> API
    KB --> API
    BRIEF --> API
    REPORT --> API
    RECON --> API
    EVENTS --> API
    API --> BIN
```

---

## 2. ADR-101 鐵律視覺化

```mermaid
graph LR
    subgraph "❌ 禁止的依賴方向"
        API2[athena-api] -. 不可依賴 .-> ENGINE2[athena-engine-ooda]
        SSH2[athena-exec-ssh] -. 不可依賴 .-> META2[athena-exec-metasploit]
        META2 -. 不可依賴 .-> C22[athena-exec-c2]
        OBS2[athena-observe] -. 不可寫 SQL .-> DB2[PostgreSQL]
    end

    subgraph "✅ 正確的依賴方向"
        BIN2[athena-workspace\nmain.rs] --> API3[athena-api]
        BIN2 --> ENGINE3[athena-engine-ooda]
        BIN2 --> OBS3[athena-observe]
        Note["所有 SQL 透過\nathena-facts trait\n由 athena-db 實作"]
    end
```

---

## 3. main.rs DI Wiring 順序

```mermaid
flowchart TD
    A[load AthenaConfig] --> B[DatabasePool::connect]
    B --> C[SqlxFactRepository]
    B --> D[SqlxIterationStore]
    C --> E[StreamableMcpClient\ntool_urls map]
    E --> F[AnthropicClient / MockLlmClient]
    F --> G[McpFactExtractor]
    G --> H[SshExecutionEngine]
    C --> I[DefaultObserver\nfact_repo + mcp]
    F --> J[ClaudeOrientEngine\nllm + kb + skills]
    J --> K[RiskMatrixDecider]
    K --> L[ActRouter\nssh + mcp + extractor + fact_repo]
    I --> M[OodaEngine\nobserve + orient + decide + act]
    L --> M
    M --> N[OodaScheduler]
    N --> O[AppState]
    C --> O
    D --> O
    O --> P[axum Router\nGET POST /api/...]
```

---

## 4. MCP StreamableHTTP 協議流程

```mermaid
sequenceDiagram
    participant AR as ActRouter
    participant MC as StreamableMcpClient
    participant Cache as sessions DashMap
    participant Container as FastMCP Container\n(Python)

    AR->>MC: call("nmap", {target: "192.168.0.28"})
    MC->>MC: TOOL_NAME_MAP["nmap"] → "nmap_scan"
    MC->>Cache: get session for "nmap"

    alt no cached session
        MC->>Container: POST /mcp\nmethod: initialize
        Container-->>MC: 200 + mcp-session-id header
        MC->>Cache: store session id
    end

    MC->>Container: POST /mcp\nmcp-session-id: xxx\nmethod: tools/call\nparams: {name: "nmap_scan", arguments: {target}}

    Container-->>MC: text/event-stream\nevent: message\ndata: {"jsonrpc":"2.0","result":{...}}

    MC->>MC: parse_sse_or_json(body)\n→ extract last "data: " line
    MC->>MC: result["content"][0]["text"]\n→ inner JSON {"facts":[...]}
    MC-->>AR: McpToolResult{success, output}
```

---

## 5. Circuit Breaker 狀態機

```mermaid
stateDiagram-v2
    [*] --> Closed: 初始狀態（正常）

    Closed --> Open: 連續失敗 ≥ threshold\n(預設 5 次)
    Open --> HalfOpen: recovery_timeout 秒後\n(預設 30s)
    HalfOpen --> Closed: 下一次呼叫成功
    HalfOpen --> Open: 下一次呼叫失敗

    Closed: Closed\n正常路由請求
    Open: Open\n立即返回錯誤\n不送到容器
    HalfOpen: Half-Open\n允許一次探測請求
```
