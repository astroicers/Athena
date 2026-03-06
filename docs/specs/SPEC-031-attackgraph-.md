# SPEC-031：AttackGraph 攻擊路徑圖引擎

> 結構完整的規格書讓 AI 零確認直接執行。

| 欄位 | 內容 |
|------|------|
| **規格 ID** | SPEC-031 |
| **狀態** | Accepted |
| **版本** | 1.0.0 |
| **作者** | Athena Contributors |
| **建立日期** | 2026-03-06 |
| **關聯 ADR** | ADR-028（攻擊路徑圖引擎 Attack Graph Engine） |
| **估算複雜度** | 高 |
| **建議模型** | Opus |
| **HITL 等級** | minimal |

---

## 🎯 目標（Goal）

> 實作 Athena 的攻擊路徑圖引擎（AttackGraphEngine），以 deterministic 有向加權圖取代目前 OrientEngine 的單步建議模式，為指揮官提供從 Initial Access 到最終目標的全域攻擊路徑可視化、多步路徑規劃、以及基於 MetaGraph 啟發的加權優先級排序。此為 ADR-028 Phase 1（Deterministic Skeleton）的完整實作規格。

---

## 📥 輸入規格（Inputs）

### 1. AttackGraphEngine.rebuild() — 圖建構 / 增量更新

| 參數名稱 | 型別 | 來源 | 限制條件 |
|----------|------|------|----------|
| db | `aiosqlite.Connection` | FastAPI DI / OODAController | 有效的 DB 連線 |
| operation_id | `str` | URL path parameter / OODA cycle | UUID 格式，必須對應已存在的 operation |

引擎從 DB 讀取的內部資料來源：

| 資料來源 | 表 | 用途 |
|----------|------|------|
| 已知情報 | `facts` | 判斷 prerequisite 是否滿足（`trait` + `value` 匹配） |
| 已執行技術 | `technique_executions` | 標記已探索節點 (`explored` / `failed`) |
| 可用 playbooks | `technique_playbooks` | Layer 1 規則集的 technique 覆蓋範圍 |
| 目標清單 | `targets` | 建構跨 target 的 lateral movement 邊 |
| 技術定義 | `techniques` | 取得 tactic_id、risk_level 等元資料 |

### 2. REST API — GET /api/operations/{operation_id}/attack-graph

| 參數名稱 | 型別 | 來源 | 限制條件 |
|----------|------|------|----------|
| operation_id | `str` | URL path | UUID 格式，必須存在 |

### 3. REST API — POST /api/operations/{operation_id}/attack-graph/rebuild

| 參數名稱 | 型別 | 來源 | 限制條件 |
|----------|------|------|----------|
| operation_id | `str` | URL path | UUID 格式，必須存在 |

---

## 📤 輸出規格（Expected Output）

### 1. Python 資料模型（`backend/app/models/attack_graph.py`）

```python
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class NodeStatus(str, Enum):
    EXPLORED = "explored"
    IN_PROGRESS = "in_progress"
    PENDING = "pending"
    UNREACHABLE = "unreachable"
    FAILED = "failed"
    PRUNED = "pruned"


class EdgeRelationship(str, Enum):
    ENABLES = "enables"
    REQUIRES = "requires"
    ALTERNATIVE = "alternative"
    LATERAL = "lateral"


@dataclass
class AttackNode:
    node_id: str
    target_id: str
    technique_id: str            # MITRE ATT&CK ID (e.g., T1003.001)
    tactic_id: str               # MITRE Tactic ID (e.g., TA0006)
    status: NodeStatus
    confidence: float            # 0.0-1.0
    risk_level: str              # low / medium / high / critical
    information_gain: float      # 0.0-1.0
    effort: int                  # estimated OODA iterations
    prerequisites: list[str]     # required fact traits
    satisfied_prerequisites: list[str]
    source: str = "deterministic"
    execution_id: Optional[str] = None
    depth: int = 0


@dataclass
class AttackEdge:
    edge_id: str
    source: str                  # AttackNode.node_id
    target: str                  # AttackNode.node_id
    weight: float                # 0.0-1.0
    relationship: EdgeRelationship
    required_facts: list[str]
    source_type: str = "deterministic"


@dataclass
class AttackGraph:
    graph_id: str
    operation_id: str
    nodes: dict[str, AttackNode]
    edges: list[AttackEdge]
    recommended_path: list[str]
    explored_paths: list[list[str]]
    unexplored_branches: list[str]
    coverage_score: float
    updated_at: str
```

### 2. Pydantic API Schemas（加入 `backend/app/models/api_schemas.py`）

```python
class AttackGraphNode(BaseModel):
    node_id: str
    target_id: str
    technique_id: str
    tactic_id: str
    status: str                  # NodeStatus.value
    confidence: float
    risk_level: str
    information_gain: float
    effort: int
    prerequisites: list[str]
    satisfied_prerequisites: list[str]
    source: str
    execution_id: str | None
    depth: int


class AttackGraphEdge(BaseModel):
    edge_id: str
    source: str
    target: str
    weight: float
    relationship: str            # EdgeRelationship.value
    required_facts: list[str]
    source_type: str


class AttackGraphResponse(BaseModel):
    graph_id: str
    operation_id: str
    nodes: list[AttackGraphNode]
    edges: list[AttackGraphEdge]
    recommended_path: list[str]
    explored_paths: list[list[str]]
    unexplored_branches: list[str]
    coverage_score: float
    updated_at: str
    stats: AttackGraphStats


class AttackGraphStats(BaseModel):
    total_nodes: int
    explored_nodes: int
    pending_nodes: int
    failed_nodes: int
    pruned_nodes: int
    total_edges: int
    path_count: int              # number of distinct root-to-leaf paths
    max_depth: int
```

### 3. REST API Response

**`GET /api/operations/{operation_id}/attack-graph`**

成功 (200):
```json
{
  "graph_id": "uuid",
  "operation_id": "uuid",
  "nodes": [
    {
      "node_id": "uuid",
      "target_id": "uuid",
      "technique_id": "T1595.002",
      "tactic_id": "TA0043",
      "status": "explored",
      "confidence": 0.92,
      "risk_level": "low",
      "information_gain": 0.8,
      "effort": 1,
      "prerequisites": [],
      "satisfied_prerequisites": [],
      "source": "deterministic",
      "execution_id": "uuid-of-execution",
      "depth": 0
    }
  ],
  "edges": [
    {
      "edge_id": "uuid",
      "source": "node-uuid-1",
      "target": "node-uuid-2",
      "weight": 0.83,
      "relationship": "enables",
      "required_facts": ["service.open_port"],
      "source_type": "deterministic"
    }
  ],
  "recommended_path": ["node-uuid-1", "node-uuid-2", "node-uuid-3"],
  "explored_paths": [["node-uuid-1", "node-uuid-2"]],
  "unexplored_branches": ["node-uuid-4", "node-uuid-5"],
  "coverage_score": 0.47,
  "updated_at": "2026-03-06T12:00:00Z",
  "stats": {
    "total_nodes": 23,
    "explored_nodes": 8,
    "pending_nodes": 7,
    "failed_nodes": 2,
    "pruned_nodes": 3,
    "total_edges": 31,
    "path_count": 5,
    "max_depth": 6
  }
}
```

**`POST /api/operations/{operation_id}/attack-graph/rebuild`**

成功 (200): 同上結構（回傳重建後的完整圖）

失敗情境：

| 錯誤類型 | HTTP Code | 處理方式 |
|----------|-----------|----------|
| operation 不存在 | 404 | `{"detail": "Operation not found"}` |
| operation 無 targets | 200 | 回傳空圖 (`nodes: [], edges: []`) |
| operation 無 facts | 200 | 回傳僅含 unreachable 節點的圖 |

### 4. WebSocket Event

Event type: `graph.updated`

```json
{
  "operation_id": "uuid",
  "graph_id": "uuid",
  "stats": {
    "total_nodes": 23,
    "explored_nodes": 8,
    "pending_nodes": 7,
    "coverage_score": 0.47
  },
  "updated_at": "2026-03-06T12:00:00Z"
}
```

---

## 🔧 核心演算法（Core Algorithms）

### 1. Prerequisite 規則集（Prerequisite Rule Registry）

每個可建構的攻擊節點由一組規則定義，格式如下：

```python
@dataclass
class TechniqueRule:
    technique_id: str              # MITRE ATT&CK ID
    tactic_id: str                 # MITRE Tactic ID
    required_facts: list[str]      # fact traits that must exist
    produced_facts: list[str]      # fact traits this technique produces on success
    risk_level: str                # low / medium / high / critical
    base_confidence: float         # default confidence when prerequisites met
    information_gain: float        # expected info gain (0.0-1.0)
    effort: int                    # estimated OODA iterations
    enables: list[str]             # technique_ids this enables on success
    alternatives: list[str]        # mutually exclusive technique_ids
```

初始規則集覆蓋 `technique_playbooks` 表中已註冊的 ~28 個 techniques。規則硬編碼於 `attack_graph_engine.py` 的 `_PREREQUISITE_RULES` 常數中。範例：

```python
_PREREQUISITE_RULES: list[TechniqueRule] = [
    # --- Reconnaissance ---
    TechniqueRule(
        technique_id="T1595.001",
        tactic_id="TA0043",
        required_facts=[],                          # No prerequisites — entry point
        produced_facts=["network.host.ip", "service.open_port"],
        risk_level="low",
        base_confidence=0.95,
        information_gain=0.9,
        effort=1,
        enables=["T1595.002", "T1190", "T1110.001"],
        alternatives=[],
    ),
    TechniqueRule(
        technique_id="T1595.002",
        tactic_id="TA0043",
        required_facts=["network.host.ip"],
        produced_facts=["vuln.cve"],
        risk_level="low",
        base_confidence=0.85,
        information_gain=0.8,
        effort=1,
        enables=["T1190"],
        alternatives=[],
    ),
    # --- Initial Access ---
    TechniqueRule(
        technique_id="T1190",
        tactic_id="TA0001",
        required_facts=["service.open_port"],
        produced_facts=["service.web"],
        risk_level="medium",
        base_confidence=0.6,
        information_gain=0.7,
        effort=2,
        enables=["T1059.004"],
        alternatives=["T1110.001"],
    ),
    TechniqueRule(
        technique_id="T1110.001",
        tactic_id="TA0001",
        required_facts=["service.open_port"],
        produced_facts=["credential.ssh"],
        risk_level="medium",
        base_confidence=0.7,
        information_gain=0.6,
        effort=1,
        enables=["T1059.004", "T1078.001"],
        alternatives=["T1190"],
    ),
    # --- Execution ---
    TechniqueRule(
        technique_id="T1059.004",
        tactic_id="TA0002",
        required_facts=["credential.ssh"],
        produced_facts=["host.os", "host.user", "host.process"],
        risk_level="medium",
        base_confidence=0.85,
        information_gain=0.5,
        effort=1,
        enables=["T1003.001", "T1087", "T1083", "T1046"],
        alternatives=[],
    ),
    # --- Credential Access ---
    TechniqueRule(
        technique_id="T1003.001",
        tactic_id="TA0006",
        required_facts=["credential.ssh", "host.user"],
        produced_facts=["credential.hash"],
        risk_level="high",
        base_confidence=0.75,
        information_gain=0.9,
        effort=1,
        enables=["T1021.004", "T1558.003"],
        alternatives=["T1003.003"],
    ),
    # --- Discovery ---
    TechniqueRule(
        technique_id="T1087",
        tactic_id="TA0007",
        required_facts=["credential.ssh"],
        produced_facts=["host.user"],
        risk_level="low",
        base_confidence=0.9,
        information_gain=0.4,
        effort=1,
        enables=["T1078.001"],
        alternatives=[],
    ),
    TechniqueRule(
        technique_id="T1083",
        tactic_id="TA0007",
        required_facts=["credential.ssh"],
        produced_facts=["host.file"],
        risk_level="low",
        base_confidence=0.9,
        information_gain=0.3,
        effort=1,
        enables=[],
        alternatives=[],
    ),
    TechniqueRule(
        technique_id="T1046",
        tactic_id="TA0007",
        required_facts=["credential.ssh"],
        produced_facts=["service.open_port"],
        risk_level="low",
        base_confidence=0.9,
        information_gain=0.5,
        effort=1,
        enables=["T1021.004"],
        alternatives=[],
    ),
    # --- Lateral Movement ---
    TechniqueRule(
        technique_id="T1021.004",
        tactic_id="TA0008",
        required_facts=["credential.ssh", "network.host.ip"],
        produced_facts=["host.session"],
        risk_level="medium",
        base_confidence=0.65,
        information_gain=0.8,
        effort=2,
        enables=["T1059.004"],  # recursive: new target gets Execution
        alternatives=["T1021.001"],
    ),
    # --- Persistence ---
    TechniqueRule(
        technique_id="T1053.003",
        tactic_id="TA0003",
        required_facts=["credential.ssh", "host.os"],
        produced_facts=["host.persistence"],
        risk_level="medium",
        base_confidence=0.7,
        information_gain=0.2,
        effort=1,
        enables=[],
        alternatives=["T1543.002"],
    ),
    # --- Collection ---
    TechniqueRule(
        technique_id="T1560.001",
        tactic_id="TA0009",
        required_facts=["credential.ssh", "host.file"],
        produced_facts=["host.file"],
        risk_level="medium",
        base_confidence=0.8,
        information_gain=0.3,
        effort=1,
        enables=["T1105"],
        alternatives=[],
    ),
    # --- C2 / Exfiltration ---
    TechniqueRule(
        technique_id="T1105",
        tactic_id="TA0011",
        required_facts=["credential.ssh", "host.binary"],
        produced_facts=["host.binary"],
        risk_level="medium",
        base_confidence=0.75,
        information_gain=0.2,
        effort=1,
        enables=[],
        alternatives=[],
    ),
    # (Windows rules follow the same pattern — omitted for brevity,
    #  see ADR-028 for technique_playbooks seed list)
]
```

規則集可在未來透過 JSON 檔案或 DB 表擴展，但 Phase 1 以硬編碼 Python 常數為主。

### 2. 圖建構演算法（Graph Construction — `rebuild()`）

```
def rebuild(db, operation_id):
    1. 查詢所有 targets（含 is_compromised 狀態）
    2. 查詢所有 facts（operation_id 過濾）
    3. 查詢所有 technique_executions（status 映射至 NodeStatus）
    4. 建立 fact_traits_set = {fact.trait for fact in facts}

    5. 清空該 operation 的舊圖資料（DELETE FROM attack_graph_nodes/edges WHERE operation_id = ?)

    6. 對每個 target × 每個 TechniqueRule 組合：
       a. 建立 AttackNode
       b. 計算 satisfied_prerequisites = rule.required_facts ∩ fact_traits_set
       c. 判斷 status：
          - 若 technique_executions 中有 success → EXPLORED
          - 若 technique_executions 中有 running → IN_PROGRESS
          - 若 technique_executions 中有 failed → FAILED
          - 若 all prerequisites satisfied → PENDING
          - else → UNREACHABLE
       d. 若 status == FAILED，檢查同 target 的 alternative techniques
          中是否有共享失敗原因（相同 prerequisite 依賴），若是則標記為 PRUNED
       e. 計算 confidence（見下方公式）
       f. 計算 depth（BFS 從 entry-point nodes 計算）

    7. 建構邊（Edges）：
       a. enables 邊：對 rule.enables 中的每個 target_technique_id，
          建立 source → target 邊（relationship=ENABLES）
       b. requires 邊：對 prerequisite 依賴鏈，建立隱式 requires 邊
       c. alternative 邊：對 rule.alternatives，建立雙向 ALTERNATIVE 邊
       d. lateral 邊：若 target A 的 technique produces credential.ssh，
          且 target B 存在且未 compromised，建立跨 target 的 LATERAL 邊

    8. 計算所有邊的 weight（MetaGraph 公式）
    9. 計算 recommended_path（Dijkstra 最短路徑，cost = 1 - weight）
    10. 計算 explored_paths（DFS 從 root 沿 EXPLORED 節點收集）
    11. 計算 unexplored_branches（PENDING 且有至少一條入邊來自 EXPLORED 的節點）
    12. 計算 coverage_score = explored_nodes / total_reachable_nodes
    13. 寫入 attack_graph_nodes 和 attack_graph_edges 表
    14. 廣播 WebSocket event "graph.updated"
    15. 回傳 AttackGraph
```

### 3. 權重計算公式（Weight Formula）

```python
def compute_edge_weight(
    target_node: AttackNode,
    alpha: float = 0.5,
    beta: float = 0.3,
    gamma: float = 0.2,
) -> float:
    """
    W = alpha * C + beta * IG + gamma * (1 - E_norm)

    C     = target_node.confidence      (exploitability: 0.0-1.0)
    IG    = target_node.information_gain (info gain: 0.0-1.0)
    E     = target_node.effort           (normalized: effort / 5, capped at 1.0)

    alpha, beta, gamma 預設 0.5, 0.3, 0.2（和為 1.0）
    """
    e_norm = min(target_node.effort / 5.0, 1.0)
    return alpha * target_node.confidence + \
           beta * target_node.information_gain + \
           gamma * (1.0 - e_norm)
```

Confidence 計算規則：

| 條件 | confidence 值 |
|------|--------------|
| 基礎值（prerequisite 全部滿足） | `rule.base_confidence` |
| prerequisite 部分滿足 | `rule.base_confidence * (satisfied / total)` |
| 已有同 technique 在其他 target 成功 | `+0.1`（上限 1.0） |
| 同 tactic 有其他 technique 失敗 | `-0.05`（下限 0.0） |
| LLM 建議調整（Phase 2） | `+/- 0.15`（上限 1.0、下限 0.0） |

### 4. 最優路徑演算法（Recommended Path — Dijkstra）

```python
def compute_recommended_path(graph: AttackGraph) -> list[str]:
    """
    使用 Dijkstra 演算法計算從任意 entry-point node（depth=0, status != FAILED）
    到最深 PENDING/UNREACHABLE 節點的最高權重路徑。

    Edge cost = 1.0 - edge.weight（使權重越高的邊 cost 越低）

    若圖中無 PENDING 節點（全部 EXPLORED 或 FAILED），
    回傳空 list。
    """
```

實作注意事項：
- 使用 `heapq` 實作 min-priority queue
- Source nodes = 所有 `depth == 0` 的節點（entry points）
- Destination = 所有 `status == PENDING` 的節點中，選擇 `information_gain` 最高者
- 路徑經過 FAILED 或 PRUNED 節點時 cost 設為 `float('inf')`（不可通過）
- 若圖不連通（存在多個 connected components），對每個 component 獨立計算，取全域最優

### 5. Dead Branch Pruning 演算法

```python
def prune_dead_branches(graph: AttackGraph) -> int:
    """
    當一個 technique 失敗時：
    1. 推斷失敗原因：查詢 technique_executions.error_message
    2. 識別共享失敗原因的 sibling techniques（同 tactic、同 target、
       共享至少一個 prerequisite）
    3. 將這些 sibling 標記為 PRUNED
    4. 遞迴地將 PRUNED 節點的所有下游 UNREACHABLE 節點也標記為 PRUNED
       （若該節點的所有入邊均來自 PRUNED/FAILED 節點）

    回傳：被 prune 的節點數量
    """
```

### 6. Cycle Detection（DAG 驗證）

圖建構完成後必須執行 cycle detection 以保證 DAG 性質：

```python
def detect_cycles(edges: list[AttackEdge]) -> list[list[str]]:
    """
    使用 DFS 的 color marking（white/gray/black）偵測有向圖中的環。
    回傳所有偵測到的環（as lists of node_ids）。

    若偵測到環：
    1. 記錄 WARNING log
    2. 移除環中 weight 最低的邊（打破環）
    3. 重新計算受影響的路徑
    """
```

ALTERNATIVE 邊為雙向邊，在 cycle detection 中需特殊處理：
- ALTERNATIVE 邊不參與 Dijkstra 路徑計算
- ALTERNATIVE 邊不計入 cycle detection（它們表達的是互斥關係，非因果關係）

---

## 🗄️ SQLite Schema（新增表）

```sql
-- 加入 database.py 的 _CREATE_TABLES 列表

CREATE TABLE IF NOT EXISTS attack_graph_nodes (
    id TEXT PRIMARY KEY,
    operation_id TEXT REFERENCES operations(id) ON DELETE CASCADE,
    target_id TEXT REFERENCES targets(id),
    technique_id TEXT NOT NULL,
    tactic_id TEXT NOT NULL,
    status TEXT DEFAULT 'unreachable',
    confidence REAL DEFAULT 0.0,
    risk_level TEXT DEFAULT 'medium',
    information_gain REAL DEFAULT 0.0,
    effort INTEGER DEFAULT 1,
    prerequisites TEXT DEFAULT '[]',
    satisfied_prerequisites TEXT DEFAULT '[]',
    source TEXT DEFAULT 'deterministic',
    execution_id TEXT,
    depth INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS attack_graph_edges (
    id TEXT PRIMARY KEY,
    operation_id TEXT REFERENCES operations(id) ON DELETE CASCADE,
    source_node_id TEXT REFERENCES attack_graph_nodes(id) ON DELETE CASCADE,
    target_node_id TEXT REFERENCES attack_graph_nodes(id) ON DELETE CASCADE,
    weight REAL DEFAULT 0.0,
    relationship TEXT DEFAULT 'enables',
    required_facts TEXT DEFAULT '[]',
    source_type TEXT DEFAULT 'deterministic',
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_agn_operation ON attack_graph_nodes(operation_id);
CREATE INDEX IF NOT EXISTS idx_agn_status ON attack_graph_nodes(operation_id, status);
CREATE INDEX IF NOT EXISTS idx_agn_technique ON attack_graph_nodes(operation_id, technique_id);
CREATE INDEX IF NOT EXISTS idx_age_operation ON attack_graph_edges(operation_id);
CREATE INDEX IF NOT EXISTS idx_age_source ON attack_graph_edges(source_node_id);
CREATE INDEX IF NOT EXISTS idx_age_target ON attack_graph_edges(target_node_id);
```

---

## 📂 檔案建立 / 修改清單（Files）

### 新建檔案

| 檔案 | 說明 |
|------|------|
| `backend/app/services/attack_graph_engine.py` | AttackGraphEngine class — rebuild(), compute_recommended_path(), prune_dead_branches(), detect_cycles(), build_orient_summary() |
| `backend/app/models/attack_graph.py` | AttackNode, AttackEdge, AttackGraph, NodeStatus, EdgeRelationship, TechniqueRule dataclasses |
| `backend/app/routers/attack_graph.py` | REST endpoints: GET + POST /attack-graph |
| `backend/tests/test_attack_graph.py` | 完整測試套件（見驗收標準） |
| `frontend/src/types/attackGraph.ts` | TypeScript 型別：AttackGraphNode, AttackGraphEdge, AttackGraphResponse, AttackGraphStats |

### 修改檔案

| 檔案 | 修改內容 |
|------|----------|
| `backend/app/database.py` | 在 `_CREATE_TABLES` 末尾新增 `attack_graph_nodes` 和 `attack_graph_edges` 兩張表的 DDL + indexes |
| `backend/app/models/api_schemas.py` | 新增 `AttackGraphNode`, `AttackGraphEdge`, `AttackGraphResponse`, `AttackGraphStats` Pydantic schemas |
| `backend/app/services/ooda_controller.py` | 在 Observe 完成後（第 1 步和第 2 步之間）新增 `AttackGraphEngine.rebuild()` 呼叫 |
| `backend/app/services/orient_engine.py` | 在 `_build_prompt()` 新增 Section 10: ATTACK GRAPH STATUS（注入圖摘要至 LLM prompt） |
| `backend/app/main.py` | 註冊 `attack_graph.router` |
| `frontend/src/components/mitre/AttackPathTimeline.tsx` | 新增攻擊圖摘要面板（coverage score、recommended path、unexplored branches） |

---

## 🔧 實作細節（Implementation Details）

### 1. AttackGraphEngine Class 介面

```python
class AttackGraphEngine:
    """Deterministic attack graph builder (ADR-028 Layer 1)."""

    def __init__(self, ws_manager: WebSocketManager):
        self._ws = ws_manager

    async def rebuild(
        self,
        db: aiosqlite.Connection,
        operation_id: str,
    ) -> AttackGraph:
        """Full rebuild: clear existing graph, construct from facts + rules."""

    async def get_graph(
        self,
        db: aiosqlite.Connection,
        operation_id: str,
    ) -> AttackGraph | None:
        """Load persisted graph from SQLite. Returns None if no graph exists."""

    def build_orient_summary(self, graph: AttackGraph) -> str:
        """Generate text summary for OrientEngine prompt Section 10.

        Format:
        ## 10. ATTACK GRAPH STATUS
        Graph coverage: 47% (8/17 nodes explored)
        Recommended path: T1595.001 → T1110.001 → T1059.004 → T1003.001 (W=0.83)
        Current position: T1059.004 (Execution) [explored]
        Next best node: T1003.001 (Credential Access) confidence=0.75
        Unexplored high-value branches:
          - T1021.004 (Lateral Movement) confidence=0.65, info_gain=0.8
        Dead branches (pruned):
          - T1190 (Initial Access) — pruned: web service not vulnerable
        """
```

### 2. OODAController 整合位置

在 `ooda_controller.py` 的 `trigger_cycle()` 中，插入於 Observe 完成後、Orient 開始前：

```python
# 位置：在 observe_summary 取得後、orient.analyze() 呼叫前

# ── 1.5. ATTACK GRAPH REBUILD ──
from app.services.attack_graph_engine import AttackGraphEngine
graph_engine = AttackGraphEngine(self._ws)
attack_graph = await graph_engine.rebuild(db, operation_id)
graph_summary = graph_engine.build_orient_summary(attack_graph)
# graph_summary 會被注入 orient_engine 的 prompt
```

### 3. OrientEngine Prompt Section 10

在 `_ORIENT_USER_PROMPT_TEMPLATE` 中於 Section 8 之後新增：

```python
## 10. ATTACK GRAPH STATUS
{attack_graph_summary}
```

`_build_prompt()` 需要接受額外參數 `attack_graph_summary: str = ""`，並在 format 中注入。

### 4. Router 定義

```python
# backend/app/routers/attack_graph.py

from fastapi import APIRouter, Depends
import aiosqlite

from app.database import get_db
from app.models.api_schemas import AttackGraphResponse
from app.services.attack_graph_engine import AttackGraphEngine
from app.ws_manager import ws_manager

router = APIRouter(prefix="/api/operations/{operation_id}", tags=["attack-graph"])


@router.get("/attack-graph", response_model=AttackGraphResponse)
async def get_attack_graph(
    operation_id: str,
    db: aiosqlite.Connection = Depends(get_db),
):
    """Return the current attack graph for an operation."""
    engine = AttackGraphEngine(ws_manager)
    graph = await engine.get_graph(db, operation_id)
    if graph is None:
        # Auto-build on first request
        graph = await engine.rebuild(db, operation_id)
    return _to_response(graph)


@router.post("/attack-graph/rebuild", response_model=AttackGraphResponse)
async def rebuild_attack_graph(
    operation_id: str,
    db: aiosqlite.Connection = Depends(get_db),
):
    """Force rebuild the attack graph (manual trigger)."""
    engine = AttackGraphEngine(ws_manager)
    graph = await engine.rebuild(db, operation_id)
    return _to_response(graph)
```

### 5. Frontend TypeScript 型別

```typescript
// frontend/src/types/attackGraph.ts

export interface AttackGraphNode {
  nodeId: string;
  targetId: string;
  techniqueId: string;
  tacticId: string;
  status: "explored" | "in_progress" | "pending" | "unreachable" | "failed" | "pruned";
  confidence: number;
  riskLevel: string;
  informationGain: number;
  effort: number;
  prerequisites: string[];
  satisfiedPrerequisites: string[];
  source: "deterministic" | "llm_suggested";
  executionId: string | null;
  depth: number;
}

export interface AttackGraphEdge {
  edgeId: string;
  source: string;
  target: string;
  weight: number;
  relationship: "enables" | "requires" | "alternative" | "lateral";
  requiredFacts: string[];
  sourceType: "deterministic" | "llm_suggested";
}

export interface AttackGraphStats {
  totalNodes: number;
  exploredNodes: number;
  pendingNodes: number;
  failedNodes: number;
  prunedNodes: number;
  totalEdges: number;
  pathCount: number;
  maxDepth: number;
}

export interface AttackGraphResponse {
  graphId: string;
  operationId: string;
  nodes: AttackGraphNode[];
  edges: AttackGraphEdge[];
  recommendedPath: string[];
  exploredPaths: string[][];
  unexploredBranches: string[];
  coverageScore: number;
  updatedAt: string;
  stats: AttackGraphStats;
}
```

---

## 🔗 副作用與連動（Side Effects）

| 本功能的狀態變動 | 受影響的既有功能 | 預期行為 |
|-----------------|----------------|---------|
| `attack_graph_nodes` / `attack_graph_edges` 表寫入 | 無既有功能直接依賴（新表） | 新表不影響既有 query |
| OODAController 在 Observe 後觸發 rebuild | OODA 循環延遲 | 增加 10-50ms（100 nodes 規模），不影響 user-facing latency |
| OrientEngine prompt 新增 Section 10 | LLM token 消耗 | 增加 ~200-400 tokens（圖摘要），對 Opus context window 無壓力 |
| WebSocket `graph.updated` event | 前端需新增 listener | 前端不處理此 event 時，不會有副作用（fire-and-forget） |
| `api_schemas.py` 新增 4 個 Pydantic model | 無既有 model 衝突 | 新增 class 不影響既有 import |
| `database.py` 新增 2 張 CREATE TABLE | init_db() 執行時間 | 增加 ~5ms（CREATE TABLE IF NOT EXISTS 為 idempotent） |
| 前端 AttackPathTimeline 新增摘要面板 | Navigator 頁面 layout | 摘要面板加在 timeline 上方，不改變既有 timeline 行為 |

---

## ⚠️ 邊界條件（Edge Cases）

### Case 1：空圖（Empty Graph）
- **觸發條件**：operation 無 targets 或 targets 無任何 facts
- **預期行為**：回傳 `AttackGraph` with `nodes={}`, `edges=[]`, `recommended_path=[]`, `coverage_score=0.0`
- **不應**：拋出 exception 或回傳 404

### Case 2：環路偵測（Cycle Detection）
- **觸發條件**：Lateral movement 邊（target A → target B → target A）可能導致 enables 環
- **預期行為**：`detect_cycles()` 偵測到環後，移除環中 weight 最低的邊，記錄 WARNING log
- **保證**：回傳的圖永遠為 DAG（ALTERNATIVE 邊除外，它們不參與路徑計算）

### Case 3：孤立節點（Orphan Nodes）
- **觸發條件**：某些 techniques 的 prerequisites 無法被任何其他 technique 的 produced_facts 滿足
- **預期行為**：保留為 `UNREACHABLE` 節點，不建立入邊。前端以灰色虛線表示
- **不應**：過濾掉這些節點（指揮官需要知道「這些技術存在但目前不可達」）

### Case 4：並發 rebuild 請求
- **觸發條件**：OODA 自動循環與手動 POST /rebuild 同時發生
- **預期行為**：使用 SQLite 的寫鎖序列化。後完成的 rebuild 覆蓋前一個的結果（last-write-wins）
- **不應**：導致 DB 死鎖或資料損壞

### Case 5：大量 targets（> 10 targets x 28 rules = 280 nodes）
- **觸發條件**：企業級測試環境有大量 targets
- **預期行為**：rebuild 完成時間 < 200ms。圖序列化 (JSON) < 500KB
- **緩解**：若節點數超過 500，僅為 compromised + active targets 建構完整子圖，其他 targets 僅建立 entry-point 節點

### Case 6：所有路徑均已探索或失敗
- **觸發條件**：所有 PENDING 節點已變為 EXPLORED 或 FAILED
- **預期行為**：`recommended_path` 回傳空 list，`coverage_score` 接近 1.0，圖摘要顯示 "All known paths explored"
- **不應**：無限循環或錯誤

### Case 7：Technique 不在 prerequisite rules 中
- **觸發條件**：OrientEngine 推薦了一個不在 `_PREREQUISITE_RULES` 中的 technique
- **預期行為**：該 technique 的執行結果仍更新 facts 表，下次 rebuild 時新 facts 可能解鎖其他已知 techniques 的 prerequisites
- **不應**：rebuild 拋出 KeyError 或忽略新 facts

### Case 8：跨 target lateral movement
- **觸發條件**：target A 上 credential.ssh 成功收集，target B 存在且未 compromised
- **預期行為**：建立 `LATERAL` 邊從 target A 的 credential 節點到 target B 的 T1021.004 節點
- **條件**：僅在 target B 有 `network.host.ip` fact（已被掃描過）時建立

### 回退方案（Rollback Plan）

- **回退方式**：`git revert` 該 commit。新建的 `attack_graph_nodes` 和 `attack_graph_edges` 表使用 `CREATE TABLE IF NOT EXISTS`，回退後不需 DROP（表會被忽略）。OODAController 中的 rebuild 呼叫被移除後，OODA 循環恢復原有行為
- **不可逆評估**：此變更為純新增（新表 + 新檔案 + 既有檔案的新增程式碼）。無 column DROP、無 data migration。完全可逆
- **資料影響**：回退後 `attack_graph_nodes` 和 `attack_graph_edges` 表資料變為孤立（不被任何程式碼讀取），無副作用。清理方式：`DROP TABLE IF EXISTS attack_graph_nodes; DROP TABLE IF EXISTS attack_graph_edges;`

---

## ✅ 驗收標準（Done When）

### 核心功能

- [ ] `backend/app/services/attack_graph_engine.py` 實作完成，包含 `rebuild()`, `get_graph()`, `build_orient_summary()`, `compute_recommended_path()`, `prune_dead_branches()`, `detect_cycles()`
- [ ] `backend/app/models/attack_graph.py` dataclasses 完成
- [ ] `backend/app/routers/attack_graph.py` 兩個 endpoints 可正常回應
- [ ] `backend/app/models/api_schemas.py` 新增 4 個 Pydantic schemas

### SQLite

- [ ] `backend/app/database.py` 中 `_CREATE_TABLES` 包含 `attack_graph_nodes` 和 `attack_graph_edges` DDL
- [ ] 新表含正確的 indexes（6 個 index）
- [ ] `init_db()` 執行後表已建立（`make test` 驗證）

### OODA 整合

- [ ] `ooda_controller.py` 在 Observe 後觸發 `AttackGraphEngine.rebuild()`
- [ ] `orient_engine.py` 的 `_build_prompt()` 注入 Section 10 攻擊圖摘要
- [ ] 圖摘要格式符合 ADR-028 定義的範例

### 演算法正確性

- [ ] **確定性測試**：相同 facts 輸入 → 100% 相同圖結構（snapshot test）
- [ ] **權重計算測試**：`compute_edge_weight()` 對已知輸入回傳預期值（精度 ±0.01）
- [ ] **Dijkstra 路徑測試**：手工建構的 5 節點圖 → 正確的 recommended_path
- [ ] **Cycle detection 測試**：包含環的圖 → 正確偵測並移除最低 weight 邊
- [ ] **Dead branch pruning 測試**：failed 節點 → 正確 prune sibling + downstream
- [ ] **空圖測試**：無 facts → 回傳空圖不拋異常
- [ ] **孤立節點測試**：不可達 technique → 保留為 UNREACHABLE

### API

- [ ] `GET /api/operations/{op_id}/attack-graph` — 200 回傳完整圖
- [ ] `GET /api/operations/{op_id}/attack-graph` — 404 when operation 不存在
- [ ] `POST /api/operations/{op_id}/attack-graph/rebuild` — 200 回傳重建後的圖
- [ ] API 回應時間 < 200ms（100 nodes 規模）

### WebSocket

- [ ] rebuild 完成後 broadcast `graph.updated` event
- [ ] event payload 包含 `stats` 和 `updated_at`

### 測試

- [ ] `make test-filter FILTER=test_attack_graph` 全數通過
- [ ] 測試覆蓋率 >= 85%（`attack_graph_engine.py`）
- [ ] `make lint` 無 error

### 前端

- [ ] `frontend/src/types/attackGraph.ts` 型別定義完成
- [ ] `AttackPathTimeline.tsx` 新增圖摘要面板（coverage score、recommended path 顯示）

### 文件

- [ ] 已更新 `CHANGELOG.md`

### 效能指標

- [ ] 圖重建延遲 < 100ms（100 nodes 以下），使用 `time.perf_counter()` 量測
- [ ] API 回應 < 200ms（`GET /attack-graph`）
- [ ] SQLite 寫入 < 50ms（100 nodes + 200 edges 的 batch INSERT）

---

## 🚫 禁止事項（Out of Scope）

- **不要實作 Phase 2（LLM Enhancement）**：本 SPEC 僅覆蓋 Phase 1（Deterministic Skeleton）。LLM 建議邊的合併、validation pipeline、`graph_suggestions` output schema 延後至後續 SPEC
- **不要實作 Phase 3（Reinforcement Learning）**：跨 Operation 歷史聚合不在本 SPEC 範圍
- **不要引入 Neo4j 或其他圖資料庫**：使用 Python in-memory graph + SQLite 持久化
- **不要修改 OrientEngine 的 output schema**：`analyze()` 的回傳格式不變，僅修改輸入 prompt
- **不要修改既有 technique_executions 表結構**：攻擊圖透過查詢既有表取得執行狀態，不新增欄位
- **不要新增 Python 外部依賴**：graph algorithms 使用 Python stdlib（`heapq`, `collections`）實作，不引入 `networkx` 或其他第三方圖庫
- **不要修改 DecisionEngine 或 EngineRouter 的行為**：攻擊圖為 advisory（資訊展示），不影響自動執行決策邏輯
- **不要建立獨立的 AttackGraphView.tsx 頁面**：Phase 1 前端僅在 `AttackPathTimeline.tsx` 中新增摘要面板。完整的 directed graph 可視化（react-force-graph-3d / D3.js dagre）延後至 Phase 1.5 或 Phase 2

---

## 📎 參考資料（References）

- **關聯 ADR**：[ADR-028 攻擊路徑圖引擎](/docs/adr/ADR-028--attack-graph-engine.md) — Accepted，定義混合模式架構和資料結構
- **前置 SPEC**：[SPEC-007 OODA 循環引擎](/docs/specs/SPEC-007-ooda-loop-engine.md) — OODAController 6 服務架構
- **前置 SPEC**：[SPEC-021 Attack Path Timeline](/docs/specs/SPEC-021-attack-path-timeline.md) — 現有平面時間線元件（本 SPEC 擴展之）
- **現有實作**：
  - `backend/app/services/ooda_controller.py` — 整合位置
  - `backend/app/services/orient_engine.py` — prompt 注入位置
  - `backend/app/database.py` — schema 擴展位置
  - `frontend/src/components/mitre/AttackPathTimeline.tsx` — 前端擴展位置
- **外部參考**：
  - Escape.tech MetaGraph — bipartite directed graph + reinforcement learning（權重公式啟發來源）
  - XBOW Attack Path Discovery — deep multi-step attack chain exploration
  - MITRE ATT&CK Enterprise Matrix v15 — technique prerequisites 和 tactic 順序
