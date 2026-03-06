# [ADR-028]: 攻擊路徑圖引擎 (Attack Graph Engine)

| 欄位 | 內容 |
|------|------|
| **狀態** | `Accepted` |
| **日期** | 2026-03-06 |
| **決策者** | Athena Core Team |

---

## 背景（Context）

Athena 目前的 OODA 循環中，`OrientEngine`（`backend/app/services/orient_engine.py`）在每輪 Orient 階段向 LLM 提交當前作戰情境，取得**單步建議**（3 個選項，選最高 confidence）。此架構在 ADR-003 與 ADR-013 中確立，運作至今可處理線性攻擊場景，但存在以下結構性限制：

### 1. 無全域攻擊路徑規劃

OrientEngine 的輸出粒度為「下一步該做什麼」，而非「從初始存取到最終目標的完整路徑」。指揮官（Commander）無法在作戰開始前看到所有可行攻擊向量的全貌。這等同於戰場指揮官只能看見眼前 100 公尺，而非整張作戰地圖。

### 2. 無已探索 / 未探索路徑追蹤

`technique_executions` 表記錄了哪些技術已執行成功或失敗，但缺乏「技術之間的因果關係」資料結構。例如：T1003.001（LSASS Dump）成功後 **啟用** T1021.001（WinRM Lateral Movement），但目前系統僅以平面清單呈現，無法區分哪些路徑已被探索、哪些分支仍待嘗試。

### 3. 無加權優先級排序

當前 OrientEngine 的 `confidence` 分數僅針對單步建議計算。缺乏跨多步路徑的累積權重，無法回答「哪條完整路徑從 Initial Access 到 Domain Admin 的成功機率最高」。

### 4. 前端無法可視化攻擊面拓撲

`AttackPathTimeline.tsx` 以 MITRE ATT&CK 14 個 Tactic 為水平軸的平面時間線呈現技術執行記錄，但無法表達技術之間的有向圖關係（前置條件、替代路徑、因果鏈）。War Room 的 3D 拓撲（`NetworkTopology.tsx`，使用 react-force-graph-3d）呈現的是網路節點，而非攻擊路徑。

### 業界參考

**Escape.tech MetaGraph**：採用 technology-agnostic 的 bipartite directed graph（Resolvers + Resources），節點權重基於三個維度 — 成功機率（success probability）、資訊量（information quantity）、CRUD 循環數 — 並使用 reinforcement learning 動態更新權重。此方法讓模糊測試引擎能優先探索高價值路徑，避免在低價值分支浪費資源。

**XBOW Attack Path Discovery**：專注於深度多步攻擊鏈探索（deep multi-step attack chains），能發現傳統單步掃描遺漏的複合漏洞利用路徑。其核心洞見是：真正危險的攻擊往往需要串連 3-5 個看似低風險的步驟。

ADR-013 已預留 Pattern 6（圖驅動推理）給正式版，指出「攻擊路徑的隱性關聯需依賴 LLM 自行推斷」為技術債。本 ADR 正式解決此技術債。

---

## 評估選項（Options Considered）

### 選項 A：LLM 驅動攻擊路徑生成（LLM-Driven Attack Path Generation）

擴展 OrientEngine 的 system prompt，要求 LLM 在每次 `analyze()` 呼叫時輸出完整的攻擊路徑樹（JSON 格式），而非僅單步建議。LLM 根據 Facts、已完成 / 失敗技術、MITRE ATT&CK 知識，一次性生成完整有向圖。

- **優點**：
  - 開發成本最低，僅需修改 prompt template 和 output schema
  - LLM 具備跨領域推理能力，能發現非結構化的創新攻擊路徑
  - 自然語言推理可覆蓋 MITRE ATT&CK 未定義的邊緣案例
  - 完全利用現有 `orient_engine.py` 架構，無需新建 service
- **缺點**：
  - 非確定性 — 相同輸入可能產生不同圖結構，難以做 regression testing
  - 昂貴 — 完整圖生成需要大量 context tokens，每次 OODA 迭代的 API 成本顯著增加
  - 無法保證圖一致性 — LLM 可能產生循環邊、孤立節點、或違反 ATT&CK prerequisite 的路徑
  - Output 大小不可預測，可能超出 max_tokens 限制
- **風險**：LLM hallucination 可能創造實際不可行的攻擊路徑（例如在無 AD 環境建議 Kerberoasting），誤導指揮官決策。圖結構的 schema validation 複雜度遠高於目前的單步建議 validation。

### 選項 B：確定性攻擊圖引擎（Deterministic AttackGraph Service）

新建 `backend/app/services/attack_graph_engine.py`，以規則引擎（rule engine）為核心，根據 `facts` 表的已知情報 + `techniques` 表的 MITRE ATT&CK prerequisite 映射，建構加權有向圖。每個 AttackNode 對應一個 MITRE technique，Edge 代表 prerequisite 或 enablement 關係，權重由確定性公式計算（基於 fact 驗證狀態、歷史成功率、風險等級）。

- **優點**：
  - 完全確定性 — 相同 Facts 輸入必然產生相同圖結構，可做 snapshot testing
  - 計算速度快（純 SQL 查詢 + 記憶體圖運算），無 LLM API 延遲
  - 圖一致性由程式碼保證（DAG validation、prerequisite checking）
  - 無額外 API 成本
  - 圖更新為增量式 — 新 Fact 進入時只需局部重新計算受影響的子圖
- **缺點**：
  - 需要手動定義大量 prerequisite 規則（MITRE ATT&CK 有 600+ 個 techniques，每個的 prerequisite 組合不同）
  - 規則引擎無法發現「創意路徑」— 僅能沿預定義的規則邊行走
  - 維護成本隨 MITRE ATT&CK 版本更新而增長
- **風險**：規則覆蓋率不足可能導致遺漏可行攻擊向量。純確定性方法在面對零日漏洞或非標準配置時缺乏適應能力。

### 選項 C：混合模式（Deterministic Graph + LLM Enhancement）

分兩層建構攻擊圖：

**Layer 1 — 確定性骨架圖（Deterministic Skeleton）**：`AttackGraphEngine` 根據 Facts + prerequisite 規則生成基礎有向圖，保證結構一致性和最低可行攻擊路徑覆蓋。

**Layer 2 — LLM 智慧增強（LLM Enrichment）**：OrientEngine 在現有 `analyze()` 流程中接收骨架圖摘要作為額外 context，LLM 可建議：(a) 新增規則引擎未涵蓋的創意邊（creative edges），(b) 動態調整節點 confidence 權重，(c) 標註高風險路徑的緩解建議。LLM 產出的新邊需通過基本 validation（不得產生循環、prerequisite 合理性檢查）後才合併入圖。

- **優點**：
  - 確定性基礎保證圖結構一致，可測試、可回溯
  - LLM 增強補足規則引擎的盲區，能發現創意攻擊鏈
  - 借鏡 MetaGraph 的加權模型，結合確定性公式（Layer 1）與動態學習（Layer 2 LLM 建議）
  - 增量設計 — Phase 1 可先上線 Layer 1（純確定性），Phase 2 再加 Layer 2（LLM 增強）
  - LLM 成本可控 — 圖摘要注入 prompt 僅需 ~200 tokens，不需要 LLM 生成完整圖
- **缺點**：
  - 架構複雜度高於選項 A 或 B — 需要維護兩層邏輯和它們之間的合併策略
  - LLM 建議的邊需要 validation pipeline（循環檢測、prerequisite 驗證）
  - 需定義「規則邊」與「LLM 建議邊」的信任層級差異
- **風險**：中等 — 兩層邏輯的邊衝突（deterministic edge 權重 vs. LLM 建議權重）需要明確的衝突解決策略。可透過優先信任 deterministic 層、LLM 層僅作為 advisory 來緩解。

---

## 決策（Decision）

我們選擇 **選項 C：混合模式（Deterministic Graph + LLM Enhancement）**，因為：

1. **解決 ADR-013 遺留的 Pattern 6 技術債** — 正式引入圖驅動推理，無需外部圖資料庫（Neo4j），以 Python in-memory graph + SQLite 持久化實現
2. **增量交付策略** — Layer 1（確定性骨架圖）可獨立上線並提供即時價值，Layer 2（LLM 增強）作為後續增量
3. **MetaGraph 啟發的加權模型** — 借鏡 Escape.tech 的三維權重（exploitability、information gain、effort），但以較簡化的公式實現
4. **前端可視化基礎** — 有向圖結構天然適配 react-force-graph-3d 或 D3.js directed graph，可整合進現有 War Room 3D 拓撲
5. **OrientEngine 增強而非取代** — 圖摘要作為 `_build_prompt()` 的新 Section 注入，不改變 `analyze()` 的回傳格式和下游合約

### 核心資料結構

```python
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class NodeStatus(str, Enum):
    """攻擊節點狀態"""
    EXPLORED = "explored"         # 已成功執行
    IN_PROGRESS = "in_progress"   # 正在執行中
    PENDING = "pending"           # 具備前置條件，可執行
    UNREACHABLE = "unreachable"   # 前置條件未滿足
    FAILED = "failed"             # 執行失敗
    PRUNED = "pruned"             # 被 dead branch pruning 排除


class EdgeRelationship(str, Enum):
    """邊的語意關係"""
    ENABLES = "enables"           # source 成功後啟用 target
    REQUIRES = "requires"         # target 需要 source 的產出（fact）
    ALTERNATIVE = "alternative"   # 互斥替代路徑
    LATERAL = "lateral"           # 跨 target 的橫向移動


@dataclass
class AttackNode:
    """攻擊圖節點 — 一個 (target, technique) 組合"""
    node_id: str                          # UUID
    target_id: str                        # FK → targets.id
    technique_id: str                     # MITRE ATT&CK ID (e.g., T1003.001)
    tactic_id: str                        # MITRE Tactic ID (e.g., TA0006)
    status: NodeStatus                    # 節點當前狀態
    confidence: float                     # 0.0-1.0 可利用性分數
    risk_level: str                       # low / medium / high / critical
    information_gain: float               # 0.0-1.0 預期情報收益（MetaGraph 啟發）
    effort: int                           # 估計 OODA 迭代數
    prerequisites: list[str]              # 需要存在的 fact traits
    satisfied_prerequisites: list[str]    # 已驗證滿足的 fact traits
    source: str = "deterministic"         # "deterministic" | "llm_suggested"
    execution_id: Optional[str] = None    # FK → technique_executions.id（若已執行）
    depth: int = 0                        # 從 root 的距離（kill chain 深度）


@dataclass
class AttackEdge:
    """攻擊圖邊 — 兩個 AttackNode 之間的關係"""
    edge_id: str                          # UUID
    source: str                           # AttackNode.node_id
    target: str                           # AttackNode.node_id
    weight: float                         # 0.0-1.0 優先級分數
    relationship: EdgeRelationship        # 邊的語意類型
    required_facts: list[str]             # 觸發此邊需要的 facts
    source_type: str = "deterministic"    # "deterministic" | "llm_suggested"


@dataclass
class AttackGraph:
    """完整攻擊圖"""
    graph_id: str                         # UUID
    operation_id: str                     # FK → operations.id
    nodes: dict[str, AttackNode]          # node_id → AttackNode
    edges: list[AttackEdge]               # 所有邊
    recommended_path: list[str]           # 最優路徑（ordered node_ids）
    explored_paths: list[list[str]]       # 已探索的完整路徑
    unexplored_branches: list[str]        # 待探索的分支節點 IDs
    coverage_score: float                 # 0.0-1.0 攻擊面覆蓋率
    updated_at: str                       # ISO8601 最後更新時間
```

### 權重計算公式（MetaGraph 啟發）

```python
def compute_edge_weight(edge: AttackEdge, source_node: AttackNode,
                        target_node: AttackNode) -> float:
    """
    W = alpha * C + beta * IG + gamma * (1 - E_norm)

    C  = target_node.confidence (可利用性)
    IG = target_node.information_gain (情報收益)
    E  = target_node.effort (標準化後取反：低 effort = 高分)

    alpha=0.5, beta=0.3, gamma=0.2 (預設，可由 operation risk_threshold 調整)
    """
    alpha, beta, gamma = 0.5, 0.3, 0.2
    e_norm = min(target_node.effort / 5.0, 1.0)  # 5 OODA 迭代為上限
    return alpha * target_node.confidence + \
           beta * target_node.information_gain + \
           gamma * (1.0 - e_norm)
```

### 架構整合

```
┌──────────────────────────────────────────────────────────────────┐
│                        OODA Controller                          │
│   ┌──────────┐    ┌───────────────────┐    ┌────────────────┐   │
│   │ Observe  │───>│ AttackGraphEngine │───>│  OrientEngine  │   │
│   │ (facts)  │    │ (Layer 1: 骨架圖) │    │ (Layer 2: LLM) │   │
│   └──────────┘    └─────────┬─────────┘    └───────┬────────┘   │
│                             │                      │            │
│                    ┌────────▼────────┐    ┌────────▼────────┐   │
│                    │  attack_graphs  │    │ recommendations │   │
│                    │   (SQLite 表)   │    │   (SQLite 表)   │   │
│                    └────────┬────────┘    └─────────────────┘   │
│                             │                                   │
│                    ┌────────▼────────┐                           │
│                    │   WebSocket     │                           │
│                    │ "graph.updated" │                           │
│                    └────────┬────────┘                           │
└─────────────────────────────┼───────────────────────────────────┘
                              │
                    ┌─────────▼──────────┐
                    │   Frontend (3D)    │
                    │ AttackGraphView    │
                    │ (force-graph-3d /  │
                    │  D3 directed)      │
                    └────────────────────┘
```

### 新增 SQLite 表

```sql
CREATE TABLE IF NOT EXISTS attack_graph_nodes (
    id TEXT PRIMARY KEY,
    operation_id TEXT REFERENCES operations(id) ON DELETE CASCADE,
    target_id TEXT REFERENCES targets(id),
    technique_id TEXT NOT NULL,          -- MITRE ATT&CK ID
    tactic_id TEXT NOT NULL,             -- MITRE Tactic ID
    status TEXT DEFAULT 'unreachable',   -- NodeStatus enum
    confidence REAL DEFAULT 0.0,
    risk_level TEXT DEFAULT 'medium',
    information_gain REAL DEFAULT 0.0,
    effort INTEGER DEFAULT 1,
    prerequisites TEXT DEFAULT '[]',     -- JSON array of fact traits
    satisfied_prerequisites TEXT DEFAULT '[]',
    source TEXT DEFAULT 'deterministic', -- "deterministic" | "llm_suggested"
    execution_id TEXT,                   -- FK to technique_executions.id
    depth INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS attack_graph_edges (
    id TEXT PRIMARY KEY,
    operation_id TEXT REFERENCES operations(id) ON DELETE CASCADE,
    source_node_id TEXT REFERENCES attack_graph_nodes(id),
    target_node_id TEXT REFERENCES attack_graph_nodes(id),
    weight REAL DEFAULT 0.0,
    relationship TEXT DEFAULT 'enables', -- EdgeRelationship enum
    required_facts TEXT DEFAULT '[]',    -- JSON array
    source_type TEXT DEFAULT 'deterministic',
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_agn_operation ON attack_graph_nodes(operation_id);
CREATE INDEX IF NOT EXISTS idx_agn_status ON attack_graph_nodes(operation_id, status);
CREATE INDEX IF NOT EXISTS idx_age_operation ON attack_graph_edges(operation_id);
CREATE INDEX IF NOT EXISTS idx_age_source ON attack_graph_edges(source_node_id);
CREATE INDEX IF NOT EXISTS idx_age_target ON attack_graph_edges(target_node_id);
```

### 實作分階段計畫

**Phase 1 — Deterministic Skeleton（Layer 1）**
1. 新建 `backend/app/services/attack_graph_engine.py`，實作 `AttackGraphEngine` class
2. 定義 prerequisite 規則集（初期覆蓋 `technique_playbooks` 表中已註冊的 techniques，約 20-30 個）
3. 新增 `attack_graph_nodes` 和 `attack_graph_edges` SQLite 表
4. 在 `ooda_controller.py` 的 Observe 完成後觸發 `AttackGraphEngine.rebuild()` — 增量更新圖
5. 新增 REST endpoint `GET /api/operations/{id}/attack-graph` 回傳完整圖 JSON
6. 新增 WebSocket event `graph.updated` 推送圖差異至前端
7. 新建 `frontend/src/components/attack-graph/AttackGraphView.tsx` 以有向圖可視化
8. `recommended_path` 使用 Dijkstra 最短路徑（以 `1 - weight` 為 edge cost）計算

**Phase 2 — LLM Enhancement（Layer 2）**
1. 在 `_build_prompt()` 新增 Section 10：圖摘要（top-5 pending nodes、recommended path、unexplored branches）
2. 擴展 LLM output schema，新增 optional `graph_suggestions` 欄位
3. 實作 `AttackGraphEngine.merge_llm_suggestions()` — 驗證 + 合併 LLM 建議的邊
4. LLM 建議邊的 `source_type` 標記為 `"llm_suggested"`，前端以不同顏色區分
5. 引入 validation pipeline：循環檢測（DFS）、prerequisite 存在性驗證、重複邊偵測

**Phase 3 — Reinforcement Learning 回饋（未來）**
1. 攻擊成功 / 失敗結果回饋至 `confidence` 權重 — 類似 MetaGraph 的強化學習
2. 跨 Operation 的歷史統計聚合 — 對相同 target profile 的成功率建立先驗

### OrientEngine Prompt 整合（Section 10 範例）

```
## 10. ATTACK GRAPH STATUS
Graph coverage: 47% (23/49 nodes explored)
Recommended path: T1595.002 → T1190 → T1059.001 → T1003.001 → T1021.002 (W=0.83)
Current position: T1059.001 (Execution — PowerShell) ✓
Next best node: T1003.001 (Credential Access — LSASS Memory) confidence=0.87
Unexplored high-value branches:
  - T1558.003 (Kerberoasting) via T1003.001, confidence=0.65, info_gain=0.9
  - T1078.002 (Valid Accounts: Domain) via T1558.003, confidence=0.55, info_gain=0.8
Dead branches (pruned):
  - T1055.001 (DLL Injection) — pruned: EDR detected similar technique T1055.003
```

---

## 後果（Consequences）

**正面影響：**

- **全域攻擊面可視化** — 指揮官首次能在作戰初期看到所有可行攻擊路徑的有向圖，包含路徑狀態（explored / pending / pruned）和優先級權重
- **多步路徑規劃** — 從 Reconnaissance 到 Impact 的完整路徑規劃能力，支持「如果 Path A 失敗，自動切換至 Path B」的自適應策略
- **OrientEngine 推理品質提升** — LLM 接收圖摘要作為額外 context，能做出更符合全域戰略的單步建議（而非近視推理）
- **ADR-013 Pattern 6 技術債清除** — 正式實現圖驅動推理，不再依賴 LLM 自行推斷攻擊路徑關聯
- **Dead Branch Pruning 自動化** — OrientEngine prompt 中的 Rule 2（Dead Branch Pruning）目前依賴 LLM 推斷，圖引擎可以確定性地追蹤失敗原因並修剪同類節點
- **ADR-027 Parallel Agent Swarm 基礎** — 攻擊圖的 `unexplored_branches` 天然適合作為並行 Agent 的任務分配依據
- **ADR-025 Exploit Validation 整合** — Validation 結果直接更新 AttackNode 的 `confidence` 權重，形成閉環回饋

**負面影響 / 技術債：**

- **Prerequisite 規則維護負擔** — 初期需為已註冊的 ~20-30 個 playbook techniques 定義 prerequisite 映射，隨 technique 庫擴展需持續維護
- **新增 2 張 SQLite 表** — `attack_graph_nodes` 和 `attack_graph_edges` 增加 schema 複雜度，需在 `database.py` 的 migration 中加入
- **OODA 迭代延遲微增** — 每輪 Observe 後需觸發圖重建（增量式），預估增加 10-50ms（POC 規模 <100 nodes 下可忽略）
- **前端新組件開發** — `AttackGraphView.tsx` 需整合進 War Room 頁面，可能需調整現有 layout
- **Phase 2 LLM 建議 validation** — 需要實作 DAG validation pipeline，增加測試複雜度

**後續追蹤：**

- [ ] 建立 SPEC 文件：Attack Graph Engine 詳細規格（API 合約、prerequisite 規則格式、圖重建演算法）
- [ ] Phase 1 實作：`attack_graph_engine.py` + SQLite schema + REST endpoint + WebSocket event
- [ ] Phase 1 測試：snapshot test 驗證確定性圖一致性
- [ ] Phase 1 前端：`AttackGraphView.tsx` directed graph 可視化（評估 react-force-graph-3d vs. D3.js dagre layout）
- [ ] Phase 2 實作：OrientEngine prompt Section 10 注入 + LLM suggestion merge + validation pipeline
- [ ] Phase 3 評估：跨 Operation 歷史聚合的可行性分析

---

## 成功指標（Success Metrics）

| 指標 | 目標值 | 驗證方式 | 檢查時間 |
|------|--------|----------|----------|
| 圖一致性（Determinism） | 相同 Facts 輸入 → 100% 相同圖結構 | Snapshot testing（`pytest --snapshot-update`） | Phase 1 完成時 |
| 圖重建延遲 | < 100ms（100 nodes 以下） | `time.perf_counter()` 在 `rebuild()` 前後量測 | Phase 1 完成時 |
| Prerequisite 規則覆蓋率 | >= 80%（已註冊 playbook techniques） | 規則數 / playbook technique 數 | Phase 1 完成時 |
| 攻擊路徑發現率 | 比 OrientEngine 單步模式多發現 >= 30% 可行路徑 | 同一 Operation 下路徑數比對 | Phase 2 完成時 |
| API 回應時間（`GET /attack-graph`） | < 200ms | 負載測試 | Phase 1 部署後 |
| Orient 推理品質提升 | 圖摘要注入後 LLM confidence 平均提升 >= 5% | A/B 比對（有圖摘要 vs. 無圖摘要） | Phase 2 完成後 2 週 |
| 前端渲染效能 | 100 nodes + 200 edges 下 >= 30 FPS | Chrome DevTools Performance 面板 | Phase 1 前端完成時 |

> **重新評估觸發條件**：若 Phase 1 的 prerequisite 規則維護成本超過每個新 technique 30 分鐘，或 POC 規模超出 500 nodes 導致 SQLite 效能瓶頸，則需重新評估是否引入 Neo4j 或 PostgreSQL 圖擴展。

---

## 關聯（Relations）

- 取代：無（新增能力，不取代既有模組）
- 被取代：無
- 延續：ADR-013（Pattern 6 圖驅動推理的正式實現，解決該 ADR 明確標記的技術債）
- 整合：ADR-003（OODA 六服務架構 — AttackGraphEngine 作為新增的第七服務，在 Observe 與 Orient 之間）
- 整合：ADR-025（Exploit Validation — 驗證結果回饋至 AttackNode confidence 權重）
- 基礎：ADR-027（Parallel Agent Swarm — 攻擊圖的 unexplored branches 作為並行 Agent 任務分配來源）
- 整合：ADR-018（Technique Playbook — playbook 中已註冊的 techniques 為 Layer 1 規則的初始覆蓋範圍）
- 參考：Escape.tech MetaGraph（bipartite directed graph + reinforcement learning 加權）
- 參考：XBOW Attack Path Discovery（deep multi-step attack chain exploration）
