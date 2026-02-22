# Athena — Data Architecture

> Version: 1.0 | Date: 2026-02-22 | Status: POC Design

---

## 1. Core Concepts

### Athena vs Operation Codename

- **Athena** = the platform (C5ISR Cyber Operations Command Platform)
- **Codename** = a specific operation instance running on Athena

```
Athena Platform
├── Operation: PHANTOM-EYE  (OP-2024-017)  "Obtain Domain Admin"
├── Operation: GHOST-BLADE  (OP-2024-018)  future mission...
└── Operation: IRON-VEIL    (OP-2024-019)  future mission...
```

### Automation Mode: Semi-Auto with Manual Override

```
Mode Switch (UI):
○ MANUAL      — Every OODA DECIDE step requires commander approval
● SEMI-AUTO   — Risk-based automation (default)

Semi-Auto Risk Threshold Rules:
├─ RiskLevel.LOW      → Auto-execute (recon, scan)
├─ RiskLevel.MEDIUM   → Auto-queue, requires commander approve
├─ RiskLevel.HIGH     → Mandatory HexConfirmModal confirmation
└─ RiskLevel.CRITICAL → Always manual (exfiltration, destructive)
```

### OODA Loop → Screen Mapping

```
OBSERVE  → Battle Monitor    (auto: agents report, facts update)
ORIENT   → MITRE Navigator   (auto: PentestGPT analyzes, generates options)
DECIDE   → C5ISR Board       (human/auto: commander reviews, approves)
         → Mission Planner   (human: selects technique, assigns engine)
ACT      → Battle Monitor    (auto: Caldera/Shannon executes)
         → Mission Planner   (auto: step status updates)
```

---

## 2. Enums (Shared Backend + Frontend)

| Enum | Values | Usage |
|------|--------|-------|
| `OODAPhase` | observe, orient, decide, act | OODA cycle stage |
| `OperationStatus` | planning, active, paused, completed, aborted | Operation lifecycle |
| `TechniqueStatus` | untested, queued, running, success, partial, failed | MITRE technique execution state |
| `MissionStepStatus` | queued, running, completed, failed, skipped | Mission step lifecycle |
| `AgentStatus` | alive, dead, pending, untrusted | Agent heartbeat state |
| `ExecutionEngine` | caldera, shannon | Execution engine |
| `C5ISRDomain` | command, control, comms, computers, cyber, isr | C5ISR six domains |
| `C5ISRDomainStatus` | operational, active, nominal, engaged, scanning, degraded, offline, critical | Domain health |
| `FactCategory` | credential, host, network, service, vulnerability, file | Intelligence classification |
| `LogSeverity` | info, success, warning, error, critical | Log severity level |
| `KillChainStage` | recon, weaponize, deliver, exploit, install, c2, action | Cyber Kill Chain 7 stages |
| `RiskLevel` | low, medium, high, critical | Risk assessment |
| `AutomationMode` | manual, semi_auto | Automation mode |

---

## 3. Entity Relationship Diagram

```
┌──────────────┐       ┌────────────────┐
│   User       │       │   Operation    │
│──────────────│       │────────────────│
│ id           │◄──────│ operator_id    │
│ callsign     │       │ code           │  "OP-2024-017"
│ role         │       │ codename       │  "PHANTOM-EYE"
└──────────────┘       │ status         │
                       │ ooda_phase     │
                       │ automation_mode│
                       │ risk_threshold │
                       │ threat_level   │
                       │ success_rate   │
                       └───────┬────────┘
                               │ 1:N
              ┌────────────────┼────────────────┬──────────────┐
              │                │                │              │
              ▼                ▼                ▼              ▼
    ┌─────────────┐  ┌────────────────┐ ┌────────────┐ ┌────────────┐
    │   Target    │  │ OODAIteration  │ │ MissionStep│ │C5ISRStatus │
    │─────────────│  │────────────────│ │────────────│ │────────────│
    │ hostname    │  │ iteration_num  │ │ step_number│ │ domain     │
    │ ip_address  │  │ phase          │ │ technique  │ │ status     │
    │ role        │  │ observe/orient │ │ target     │ │ health_pct │
    │ compromised │  │ decide/act     │ │ engine     │ └────────────┘
    └──────┬──────┘  └───────┬────────┘ │ status     │
           │ 1:N             │ 1:1      └────────────┘
           ▼                 ▼
    ┌─────────────┐  ┌────────────────┐
    │   Agent     │  │Recommendation  │
    │─────────────│  │────────────────│
    │ paw         │  │ situation      │
    │ status      │  │ confidence     │
    │ privilege   │  │ options (JSON) │
    │ last_beacon │  │ accepted       │
    └─────────────┘  └────────────────┘

    ┌─────────────┐  ┌────────────────┐  ┌────────────┐
    │  Technique  │  │TechExecution   │  │    Fact     │
    │─────────────│  │────────────────│  │────────────│
    │ mitre_id    │◄─│ technique_id   │  │ trait      │
    │ name        │  │ target_id      │  │ value      │
    │ tactic      │  │ engine         │  │ category   │
    │ risk_level  │  │ status         │  │ score      │
    │ kill_chain  │  │ result_summary │  └────────────┘
    └─────────────┘  └────────────────┘

    ┌────────────┐
    │  LogEntry  │
    │────────────│
    │ severity   │
    │ source     │
    │ message    │
    └────────────┘
```

---

## 4. Backend Models (Python / Pydantic)

### Operation

```python
class Operation(BaseModel):
    id: str                             # UUID
    code: str                           # "OP-2024-017"
    name: str                           # "Obtain Domain Admin"
    codename: str                       # "PHANTOM-EYE"
    strategic_intent: str
    status: OperationStatus
    current_ooda_phase: OODAPhase
    ooda_iteration_count: int
    threat_level: float                 # 0.0 - 10.0
    success_rate: float                 # 0 - 100
    techniques_executed: int
    techniques_total: int
    active_agents: int
    data_exfiltrated_bytes: int
    automation_mode: AutomationMode     # manual / semi_auto
    risk_threshold: RiskLevel           # Semi-Auto threshold
    operator_id: str | None
    created_at: datetime
    updated_at: datetime
```

### Target

```python
class Target(BaseModel):
    id: str
    hostname: str                       # "DC-01"
    ip_address: str                     # "10.0.1.5"
    os: str | None                      # "Windows Server 2019"
    role: str                           # "Domain Controller"
    network_segment: str                # "10.0.1.0/24"
    is_compromised: bool
    privilege_level: str | None         # "SYSTEM" | "Admin" | "User"
    operation_id: str
```

### Agent

```python
class Agent(BaseModel):
    id: str
    paw: str                            # "AGENT-7F3A"
    host_id: str                        # FK -> Target
    status: AgentStatus
    privilege: str                      # "SYSTEM"
    last_beacon: datetime | None
    beacon_interval_sec: int
    platform: str                       # "windows"
    operation_id: str
```

### Technique

```python
class Technique(BaseModel):
    id: str
    mitre_id: str                       # "T1003.001"
    name: str                           # "OS Credential Dumping: LSASS Memory"
    tactic: str                         # "Credential Access"
    tactic_id: str                      # "TA0006"
    kill_chain_stage: KillChainStage
    risk_level: RiskLevel               # Inherent risk (drives Semi-Auto behavior)
    caldera_ability_id: str | None
    platforms: list[str]
```

### TechniqueExecution

```python
class TechniqueExecution(BaseModel):
    id: str
    technique_id: str                   # mitre_id
    target_id: str
    operation_id: str
    ooda_iteration_id: str | None
    engine: ExecutionEngine
    status: TechniqueStatus
    result_summary: str | None
    facts_collected_count: int
    started_at: datetime | None
    completed_at: datetime | None
    error_message: str | None
```

### Fact

```python
class Fact(BaseModel):
    id: str
    trait: str                          # "host.user.name"
    value: str                          # "CORP\\Administrator"
    category: FactCategory
    source_technique_id: str | None
    source_target_id: str | None
    operation_id: str
    score: int
    collected_at: datetime
```

### OODAIteration

```python
class OODAIteration(BaseModel):
    id: str
    operation_id: str
    iteration_number: int
    phase: OODAPhase
    observe_summary: str | None
    orient_summary: str | None
    decide_summary: str | None
    act_summary: str | None
    recommendation_id: str | None
    technique_execution_id: str | None
    started_at: datetime
    completed_at: datetime | None
```

### PentestGPTRecommendation

```python
class TacticalOption(BaseModel):
    technique_id: str
    technique_name: str
    reasoning: str
    risk_level: RiskLevel
    recommended_engine: ExecutionEngine
    confidence: float                   # 0.0 - 1.0
    prerequisites: list[str]

class PentestGPTRecommendation(BaseModel):
    id: str
    operation_id: str
    ooda_iteration_id: str
    situation_assessment: str
    recommended_technique_id: str
    confidence: float
    options: list[TacticalOption]
    reasoning_text: str
    accepted: bool | None
    created_at: datetime
```

### MissionStep

```python
class MissionStep(BaseModel):
    id: str
    operation_id: str
    step_number: int
    technique_id: str
    technique_name: str
    target_id: str
    target_label: str
    engine: ExecutionEngine
    status: MissionStepStatus
```

### C5ISRStatus

```python
class C5ISRStatus(BaseModel):
    id: str
    operation_id: str
    domain: C5ISRDomain
    status: C5ISRDomainStatus
    health_pct: float                   # 0-100
    detail: str
```

### LogEntry

```python
class LogEntry(BaseModel):
    id: str
    timestamp: datetime
    severity: LogSeverity
    source: str
    message: str
    operation_id: str | None
    technique_id: str | None
```

---

## 5. SQLite Schema

```sql
CREATE TABLE users (
    id TEXT PRIMARY KEY,
    callsign TEXT NOT NULL,
    role TEXT DEFAULT 'Commander',
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE operations (
    id TEXT PRIMARY KEY,
    code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    codename TEXT NOT NULL,
    strategic_intent TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'planning',
    current_ooda_phase TEXT NOT NULL DEFAULT 'observe',
    ooda_iteration_count INTEGER DEFAULT 0,
    threat_level REAL DEFAULT 0.0,
    success_rate REAL DEFAULT 0.0,
    techniques_executed INTEGER DEFAULT 0,
    techniques_total INTEGER DEFAULT 0,
    active_agents INTEGER DEFAULT 0,
    data_exfiltrated_bytes INTEGER DEFAULT 0,
    automation_mode TEXT DEFAULT 'semi_auto',
    risk_threshold TEXT DEFAULT 'medium',
    operator_id TEXT REFERENCES users(id),
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE targets (
    id TEXT PRIMARY KEY,
    hostname TEXT NOT NULL,
    ip_address TEXT NOT NULL,
    os TEXT,
    role TEXT NOT NULL,
    network_segment TEXT DEFAULT '10.0.1.0/24',
    is_compromised INTEGER DEFAULT 0,
    privilege_level TEXT,
    operation_id TEXT REFERENCES operations(id),
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE agents (
    id TEXT PRIMARY KEY,
    paw TEXT NOT NULL,
    host_id TEXT REFERENCES targets(id),
    status TEXT DEFAULT 'pending',
    privilege TEXT DEFAULT 'User',
    last_beacon TEXT,
    beacon_interval_sec INTEGER DEFAULT 5,
    platform TEXT DEFAULT 'windows',
    operation_id TEXT REFERENCES operations(id),
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE techniques (
    id TEXT PRIMARY KEY,
    mitre_id TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    tactic TEXT NOT NULL,
    tactic_id TEXT NOT NULL,
    description TEXT,
    kill_chain_stage TEXT DEFAULT 'exploit',
    risk_level TEXT DEFAULT 'medium',
    caldera_ability_id TEXT,
    platforms TEXT DEFAULT '["windows"]'
);

CREATE TABLE technique_executions (
    id TEXT PRIMARY KEY,
    technique_id TEXT NOT NULL,
    target_id TEXT REFERENCES targets(id),
    operation_id TEXT REFERENCES operations(id),
    ooda_iteration_id TEXT,
    engine TEXT DEFAULT 'caldera',
    status TEXT DEFAULT 'queued',
    result_summary TEXT,
    facts_collected_count INTEGER DEFAULT 0,
    started_at TEXT,
    completed_at TEXT,
    error_message TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE facts (
    id TEXT PRIMARY KEY,
    trait TEXT NOT NULL,
    value TEXT NOT NULL,
    category TEXT DEFAULT 'host',
    source_technique_id TEXT,
    source_target_id TEXT,
    operation_id TEXT REFERENCES operations(id),
    score INTEGER DEFAULT 1,
    collected_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE ooda_iterations (
    id TEXT PRIMARY KEY,
    operation_id TEXT REFERENCES operations(id),
    iteration_number INTEGER NOT NULL,
    phase TEXT DEFAULT 'observe',
    observe_summary TEXT,
    orient_summary TEXT,
    decide_summary TEXT,
    act_summary TEXT,
    recommendation_id TEXT,
    technique_execution_id TEXT,
    started_at TEXT DEFAULT (datetime('now')),
    completed_at TEXT
);

CREATE TABLE recommendations (
    id TEXT PRIMARY KEY,
    operation_id TEXT REFERENCES operations(id),
    ooda_iteration_id TEXT,
    situation_assessment TEXT NOT NULL,
    recommended_technique_id TEXT NOT NULL,
    confidence REAL NOT NULL,
    options TEXT NOT NULL,
    reasoning_text TEXT NOT NULL,
    accepted INTEGER,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE mission_steps (
    id TEXT PRIMARY KEY,
    operation_id TEXT REFERENCES operations(id),
    step_number INTEGER NOT NULL,
    technique_id TEXT NOT NULL,
    technique_name TEXT NOT NULL,
    target_id TEXT REFERENCES targets(id),
    target_label TEXT NOT NULL,
    engine TEXT DEFAULT 'caldera',
    status TEXT DEFAULT 'queued',
    created_at TEXT DEFAULT (datetime('now')),
    started_at TEXT,
    completed_at TEXT
);

CREATE TABLE c5isr_statuses (
    id TEXT PRIMARY KEY,
    operation_id TEXT REFERENCES operations(id),
    domain TEXT NOT NULL,
    status TEXT NOT NULL,
    health_pct REAL DEFAULT 100.0,
    detail TEXT DEFAULT '',
    updated_at TEXT DEFAULT (datetime('now')),
    UNIQUE(operation_id, domain)
);

CREATE TABLE log_entries (
    id TEXT PRIMARY KEY,
    timestamp TEXT DEFAULT (datetime('now')),
    severity TEXT DEFAULT 'info',
    source TEXT NOT NULL,
    message TEXT NOT NULL,
    operation_id TEXT,
    technique_id TEXT,
    target_id TEXT
);
```

---

## 6. REST API Endpoints

```
Base: http://localhost:8000/api

-- Operations --
GET    /operations                           List all operations
POST   /operations                           Create new operation
GET    /operations/{id}                      Get operation detail
PATCH  /operations/{id}                      Update operation
GET    /operations/{id}/summary              Composite C5ISR Board data

-- OODA Cycle --
POST   /operations/{id}/ooda/trigger         Start new OODA iteration
GET    /operations/{id}/ooda/current         Current iteration state
GET    /operations/{id}/ooda/history         All iterations
GET    /operations/{id}/ooda/timeline        Formatted timeline entries

-- Techniques --
GET    /techniques                           MITRE technique catalog
GET    /operations/{id}/techniques           Techniques with execution status (matrix)

-- Mission --
GET    /operations/{id}/mission/steps        List mission steps
POST   /operations/{id}/mission/steps        Add mission step
PATCH  /operations/{id}/mission/steps/{sid}  Update step
POST   /operations/{id}/mission/execute      Execute entire mission plan

-- Targets --
GET    /operations/{id}/targets              Target hosts
GET    /operations/{id}/topology             Topology (nodes + edges)

-- Agents --
GET    /operations/{id}/agents               Agent list
POST   /operations/{id}/agents/sync          Sync from Caldera

-- Facts --
GET    /operations/{id}/facts                Collected intelligence

-- C5ISR --
GET    /operations/{id}/c5isr                All 6 domain statuses
PATCH  /operations/{id}/c5isr/{domain}       Update domain status

-- Logs --
GET    /operations/{id}/logs                 Log entries (paginated)

-- Recommendations --
GET    /operations/{id}/recommendations/latest   Latest PentestGPT recommendation
POST   /operations/{id}/recommendations/{rid}/accept  Accept recommendation

-- WebSocket (Real-time) --
WS     /ws/{operation_id}                    Live event stream
  Events: log.new, agent.beacon, execution.update,
          ooda.phase, c5isr.update, fact.new, recommendation
```

---

## 7. UI-to-Data Traceability

| UI Element | Screen | Data Source |
|-----------|--------|------------|
| KPI "12 Active Agents" | C5ISR Board | `Operation.active_agents` |
| KPI "47 Techniques" | C5ISR Board | `Operation.techniques_executed` |
| KPI "73% Success Rate" | C5ISR / Battle | `Operation.success_rate` |
| KPI "7.4 Threat Level" | C5ISR Board | `Operation.threat_level` |
| KPI "2.4 MB Exfiltrated" | Battle Monitor | `Operation.data_exfiltrated_bytes` |
| KPI "12 Active Connections" | Battle Monitor | `Operation.active_agents` |
| C5ISR 6-domain cards | C5ISR Board | `C5ISRStatus[]` |
| OODA indicator | C5ISR Board | `Operation.current_ooda_phase` |
| PentestGPT recommend card | C5ISR / MITRE | `PentestGPTRecommendation` |
| Active operations table | C5ISR Board | `TechniqueExecution[]` joined Technique + Target |
| Mini attack topology | C5ISR Board | `Target[]` + topology edges |
| ATT&CK matrix cells | MITRE Navigator | `TechniqueWithStatus[]` grouped by tactic |
| Kill Chain progress | MITRE Navigator | `KillChainStage[]` + status |
| Technique detail card | MITRE Navigator | `Technique` + execution stats |
| Mission steps table | Mission Planner | `MissionStep[]` |
| OODA timeline | Mission Planner | `OODATimelineEntry[]` |
| Target host cards | Mission Planner | `Target[]` |
| Network topology nodes | Battle Monitor | `TopologyNode[]` + `TopologyEdge[]` |
| Agent beacon list | Battle Monitor | `Agent[]` |
| Live log stream | Battle Monitor | `LogEntry[]` via WebSocket |
| SUCCESS victory log | Battle Monitor | `LogEntry { severity: "success" }` |
| Automation mode toggle | Sidebar / Header | `Operation.automation_mode` |

---

## 8. Demo Seed Data (OP-2024-017 "PHANTOM-EYE")

### Operation
| Field | Value |
|-------|-------|
| code | OP-2024-017 |
| name | Obtain Domain Admin |
| codename | PHANTOM-EYE |
| status | active |
| current_ooda_phase | decide |
| threat_level | 7.4 |
| success_rate | 73.0 |
| techniques_executed | 47 |
| techniques_total | 156 |
| active_agents | 12 |
| data_exfiltrated_bytes | 2516582 (2.4 MB) |
| automation_mode | semi_auto |
| risk_threshold | medium |

### Targets (5)
| Hostname | IP | Role | Compromised | Privilege |
|----------|----|------|-------------|-----------|
| DC-01 | 10.0.1.5 | Domain Controller | Yes | SYSTEM |
| WS-PC01 | 10.0.1.20 | Workstation | Yes | Admin |
| WS-PC02 | 10.0.1.21 | Workstation | No | - |
| DB-01 | 10.0.1.30 | Database Server | No | - |
| FS-01 | 10.0.1.40 | File Server | Yes | SYSTEM |

### Agents (4)
| PAW | Host | Status | Privilege |
|-----|------|--------|-----------|
| AGENT-7F3A | DC-01 | alive | SYSTEM |
| AGENT-2B1C | WS-PC01 | alive | Admin |
| AGENT-9E4D | WS-PC02 | pending | User |
| AGENT-5A7B | FS-01 | alive | SYSTEM |

### Mission Steps (4)
| # | Technique | Target | Engine | Status |
|---|-----------|--------|--------|--------|
| 01 | T1595.001 Active Scanning | 10.0.1.0/24 | CALDERA | completed |
| 02 | T1003.001 LSASS Memory | DC-01 | CALDERA | running |
| 03 | T1021.002 SMB/Admin$ | WS-PC01 | CALDERA | queued |
| 04 | T1059.001 PowerShell | WS-PC02 | SHANNON | queued |

### C5ISR Status (6)
| Domain | Status | Health |
|--------|--------|--------|
| COMMAND | operational | 100% |
| CONTROL | active | 90% |
| COMMS | degraded | 60% |
| COMPUTERS | nominal | 93% |
| CYBER | engaged | 73% |
| ISR | scanning | 67% |

### PentestGPT Recommendation
| Field | Value |
|-------|-------|
| technique | T1003.001 |
| confidence | 87% |
| reasoning | Target DC-01 runs Windows Server 2019 with SeDebugPrivilege available. LSASS process memory contains NTLM hashes for lateral movement. |
| prerequisites | SeDebugPrivilege (available), Local Admin (confirmed) |
| risk_level | medium |
| recommended_engine | caldera |
