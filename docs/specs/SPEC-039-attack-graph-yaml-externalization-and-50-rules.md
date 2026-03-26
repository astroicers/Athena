# SPEC-039：Attack Graph YAML Externalization and 50+ Rules

> 結構完整的規格書讓 AI 零確認直接執行。

| 欄位 | 內容 |
|------|------|
| **規格 ID** | SPEC-039 |
| **關聯 ADR** | ADR-036 |
| **估算複雜度** | 高 |

---

## 🎯 目標（Goal）

> 將攻擊圖引擎的硬編碼 `_PREREQUISITE_RULES`（13 條）遷移至外部 YAML 檔案，擴展至 50 條以上規則覆蓋至少 8 個 MITRE ATT&CK 戰術類別，同時修正 Dijkstra 權重公式語意混淆問題與死支修剪過度激進問題，提升攻擊路徑規劃的覆蓋率與正確性。

---

## 📥 輸入規格（Inputs）

### YAML 規則檔案路徑

| 參數名稱 | 型別 | 來源 | 限制條件 |
|----------|------|------|----------|
| YAML 檔案路徑 | string | 檔案系統 | `backend/app/data/technique_rules.yaml` |
| 環境變數覆蓋 | string | `TECHNIQUE_RULES_PATH` | 可選，預設使用上述路徑 |

### YAML Schema 定義

```yaml
# backend/app/data/technique_rules.yaml
version: "1.0"
rules:
  - technique_id: "T1595.001"          # string, 必填, MITRE ATT&CK 技術 ID
    tactic_id: "TA0043"                # string, 必填, MITRE ATT&CK 戰術 ID
    required_facts: []                 # list[string], 必填, 可為空
    produced_facts:                    # list[string], 必填, 至少一項
      - "network.host.ip"
      - "service.open_port"
    risk_level: "low"                  # string, 必填, enum: low | medium | high | critical
    base_confidence: 0.95              # float, 必填, 範圍 0.0-1.0
    information_gain: 0.9              # float, 必填, 範圍 0.0-1.0
    effort: 1                          # int, 必填, 範圍 1-5
    enables:                           # list[string], 必填, 可為空
      - "T1595.002"
      - "T1190"
      - "T1110.001"
    alternatives: []                   # list[string], 必填, 可為空
    platforms:                         # list[string], 必填, enum 值: linux | windows
      - "linux"
      - "windows"
    description: "Active Scanning: Scanning IP Blocks"  # string, 必填, 規則語意說明
```

### YAML 欄位驗證規則

| 欄位 | 類型 | 必填 | 驗證規則 |
|------|------|------|----------|
| `version` | string | 是 | 頂層欄位，目前僅接受 `"1.0"` |
| `rules` | list | 是 | 至少包含 1 條規則 |
| `technique_id` | string | 是 | 正規表達式 `^T\d{4}(\.\d{3})?$` |
| `tactic_id` | string | 是 | 正規表達式 `^TA\d{4}$`，且必須存在於 `_TACTIC_ORDER` |
| `required_facts` | list[string] | 是 | 可為空列表 |
| `produced_facts` | list[string] | 是 | 至少包含一項 |
| `risk_level` | string | 是 | enum: `low`, `medium`, `high`, `critical` |
| `base_confidence` | float | 是 | `0.0 <= x <= 1.0` |
| `information_gain` | float | 是 | `0.0 <= x <= 1.0` |
| `effort` | int | 是 | `1 <= x <= 5` |
| `enables` | list[string] | 是 | 可為空列表，每項須為有效 technique_id 格式 |
| `alternatives` | list[string] | 是 | 可為空列表，每項須為有效 technique_id 格式 |
| `platforms` | list[string] | 是 | 至少一項，每項為 `linux` 或 `windows` |
| `description` | string | 是 | 長度 1-500 |

### Pydantic 驗證 Model

```python
# 新增於 backend/app/models/attack_graph.py

from pydantic import BaseModel, Field, field_validator
import re

class TechniqueRuleSchema(BaseModel):
    """Pydantic schema for YAML rule validation."""
    technique_id: str = Field(..., pattern=r"^T\d{4}(\.\d{3})?$")
    tactic_id: str = Field(..., pattern=r"^TA\d{4}$")
    required_facts: list[str]
    produced_facts: list[str] = Field(..., min_length=1)
    risk_level: Literal["low", "medium", "high", "critical"]
    base_confidence: float = Field(..., ge=0.0, le=1.0)
    information_gain: float = Field(..., ge=0.0, le=1.0)
    effort: int = Field(..., ge=1, le=5)
    enables: list[str]
    alternatives: list[str]
    platforms: list[Literal["linux", "windows"]] = Field(..., min_length=1)
    description: str = Field(..., min_length=1, max_length=500)

class TechniqueRulesFile(BaseModel):
    """Top-level YAML file schema."""
    version: Literal["1.0"]
    rules: list[TechniqueRuleSchema] = Field(..., min_length=1)
```

---

## 📤 輸出規格（Expected Output）

### 1. TechniqueRule Model 擴展

`backend/app/models/attack_graph.py` 第 34-45 行的 `TechniqueRule` dataclass 新增兩個欄位：

```python
@dataclass
class TechniqueRule:
    technique_id: str
    tactic_id: str
    required_facts: list[str]
    produced_facts: list[str]
    risk_level: str
    base_confidence: float
    information_gain: float
    effort: int
    enables: list[str]
    alternatives: list[str]
    platforms: list[str] = field(default_factory=lambda: ["linux", "windows"])
    description: str = ""
```

### 2. 規則載入函式

`backend/app/services/attack_graph_engine.py` 第 45-133 行的硬編碼 `_PREREQUISITE_RULES` 清單替換為 `_load_rules()` 函式：

```python
import os
import time
import yaml
from pathlib import Path

_DEFAULT_RULES_PATH = Path(__file__).parent.parent / "data" / "technique_rules.yaml"

def _load_rules(path: Path | None = None) -> list[TechniqueRule]:
    """Load technique rules from YAML file with Pydantic validation.

    Args:
        path: YAML file path. Defaults to backend/app/data/technique_rules.yaml.
              Can be overridden via TECHNIQUE_RULES_PATH env var.

    Returns:
        List of validated TechniqueRule objects.

    Raises:
        FileNotFoundError: YAML file does not exist.
        ValueError: YAML content fails Pydantic validation.
    """
    if path is None:
        env_path = os.environ.get("TECHNIQUE_RULES_PATH")
        path = Path(env_path) if env_path else _DEFAULT_RULES_PATH

    start = time.perf_counter()

    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    # Pydantic validation
    validated = TechniqueRulesFile(**raw)

    rules = []
    for r in validated.rules:
        rules.append(TechniqueRule(
            technique_id=r.technique_id,
            tactic_id=r.tactic_id,
            required_facts=r.required_facts,
            produced_facts=r.produced_facts,
            risk_level=r.risk_level,
            base_confidence=r.base_confidence,
            information_gain=r.information_gain,
            effort=r.effort,
            enables=r.enables,
            alternatives=r.alternatives,
            platforms=r.platforms,
            description=r.description,
        ))

    elapsed_ms = (time.perf_counter() - start) * 1000
    logger.info("Loaded %d technique rules from %s in %.1fms", len(rules), path, elapsed_ms)

    return rules


def reload_rules(path: Path | None = None) -> None:
    """Hot-reload rules without restart. Thread-safe via module-level replacement."""
    global _PREREQUISITE_RULES, _RULE_BY_TECHNIQUE
    new_rules = _load_rules(path)
    new_lookup = {r.technique_id: r for r in new_rules}
    # Atomic swap
    _PREREQUISITE_RULES = new_rules
    _RULE_BY_TECHNIQUE = new_lookup
    logger.info("Hot-reloaded %d technique rules", len(new_rules))


# Module-level initialization
_PREREQUISITE_RULES: list[TechniqueRule] = _load_rules()
_RULE_BY_TECHNIQUE: dict[str, TechniqueRule] = {r.technique_id: r for r in _PREREQUISITE_RULES}
```

### 3. 直接成本公式

`backend/app/services/attack_graph_engine.py` 第 297-306 行的 `compute_edge_weight()` 替換為 `compute_edge_cost()`：

**新公式：**

```
cost = 0.35 * (1 - confidence) + 0.25 * (1 - information_gain) + 0.25 * risk_cost + 0.15 * effort_norm
```

**變數定義：**

| 變數 | 定義 | 範圍 | 說明 |
|------|------|------|------|
| `confidence` | `AttackNode.confidence` | 0.0-1.0 | 技術成功率估計，越高越好 |
| `information_gain` | `AttackNode.information_gain` | 0.0-1.0 | 預期情報收益，越高越好 |
| `risk_cost` | `RISK_COST_MAP[risk_level]` | 0.1-1.0 | 被偵測風險，越低越好 |
| `effort_norm` | `min(effort / 5.0, 1.0)` | 0.0-1.0 | 正規化耗時，越低越好 |
| `cost` | 最終成本值 | 0.0-1.0 | 越低代表越佳路徑 |

**risk_cost 對應表：**

| 風險等級 | risk_cost | 語意 |
|----------|-----------|------|
| `low` | 0.1 | 幾乎不會觸發告警 |
| `medium` | 0.3 | 可能觸發 SIEM 規則 |
| `high` | 0.6 | 大概率觸發 EDR/IDS |
| `critical` | 1.0 | 必定觸發告警，可能導致存取喪失 |

**係數設計依據：**

| 係數 | 權重 | 理由 |
|------|------|------|
| 0.35 | confidence | 作戰成功率為首要考量，失敗的技術浪費時間且可能觸發警報 |
| 0.25 | information_gain | 情報探索價值是紅隊行動的核心驅動力，高 IG 技術開啟更多後續路徑 |
| 0.25 | risk_cost | 隱蔽性對紅隊至關重要，高風險技術可能導致被偵測和存取喪失 |
| 0.15 | effort | 時間為次要因素，但同等條件下應優先選擇低耗時路徑 |

**實作程式碼：**

```python
RISK_COST_MAP: dict[str, float] = {
    "low": 0.1,
    "medium": 0.3,
    "high": 0.6,
    "critical": 1.0,
}

@staticmethod
def compute_edge_cost(target_node: AttackNode) -> float:
    """Direct cost formula — lower value = better path.

    cost = 0.35*(1-confidence) + 0.25*(1-information_gain)
         + 0.25*risk_cost + 0.15*effort_norm

    Designed for Dijkstra shortest-path: semantically intuitive,
    no desirability-inversion needed.
    """
    risk_cost = RISK_COST_MAP.get(target_node.risk_level, 0.3)
    effort_norm = min(target_node.effort / 5.0, 1.0)
    return (
        0.35 * (1.0 - target_node.confidence)
        + 0.25 * (1.0 - target_node.information_gain)
        + 0.25 * risk_cost
        + 0.15 * effort_norm
    )
```

**所有呼叫 `compute_edge_weight()` 的位置必須改為 `compute_edge_cost()`，並移除 Dijkstra 中的 `cost = 1.0 - weight` 反轉：**

| 檔案 | 行號 | 原始碼 | 修改後 |
|------|------|--------|--------|
| `attack_graph_engine.py` | 297-306 | `compute_edge_weight(target_node, alpha, beta, gamma)` | `compute_edge_cost(target_node)` |
| `attack_graph_engine.py` | 342 | `cost = 1.0 - edge.weight` | `cost = edge.weight`（weight 已是成本） |
| `attack_graph_engine.py` | 650 | `weight = self.compute_edge_weight(target_node)` | `weight = self.compute_edge_cost(target_node)` |
| `attack_graph_engine.py` | 669 | `weight = self.compute_edge_weight(alt_node)` | `weight = self.compute_edge_cost(alt_node)` |
| `attack_graph_engine.py` | 690 | `weight = self.compute_edge_weight(lateral_node)` | `weight = self.compute_edge_cost(lateral_node)` |

### 4. 修剪邏輯修正

**Bug 描述**：`prune_dead_branches()` 在 T1110.001（Brute Force）失敗時，因 T1190（Exploit Public-Facing Application）共享 `service.open_port` 前置條件和 `TA0001` 戰術類別，被一併修剪。但 T1190 是 T1110.001 的替代技術（在 `alternatives` 清單中），攻擊向量完全不同，不應被修剪。

**修正範圍**：`backend/app/services/attack_graph_engine.py` 第 439-499 行

**`prune_dead_branches()` 修正虛擬碼：**

```python
def prune_dead_branches(self, graph: AttackGraph) -> int:
    pruned_count = 0
    failed_nodes = [n for n in graph.nodes.values() if n.status == NodeStatus.FAILED]

    for failed in failed_nodes:
        # 取得失敗節點的 rule，以獲取 alternatives 清單
        failed_rule = _RULE_BY_TECHNIQUE.get(failed.technique_id)
        protected_techniques: set[str] = set()
        if failed_rule:
            protected_techniques = set(failed_rule.alternatives)

        # 尋找兄弟節點：同 tactic_id、同 target_id
        siblings = [
            n for n in graph.nodes.values()
            if n.tactic_id == failed.tactic_id
            and n.target_id == failed.target_id
            and n.node_id != failed.node_id
            and n.status not in (NodeStatus.EXPLORED, NodeStatus.FAILED, NodeStatus.PRUNED)
        ]

        for sibling in siblings:
            # >>> 新增保護：若 sibling 在 alternatives 清單中，跳過修剪 <<<
            if sibling.technique_id in protected_techniques:
                logger.debug(
                    "Protecting alternative technique %s from pruning "
                    "(alternative of failed %s)",
                    sibling.technique_id, failed.technique_id,
                )
                continue

            shared_prereqs = set(sibling.prerequisites) & set(failed.prerequisites)
            if shared_prereqs:
                sibling.status = NodeStatus.PRUNED
                pruned_count += 1

    pruned_count += self._propagate_prune(graph)
    return pruned_count
```

**`_propagate_prune()` 修正虛擬碼：**

```python
def _propagate_prune(self, graph: AttackGraph) -> int:
    count = 0
    changed = True
    while changed:
        changed = False
        # 建立 incoming edge map（包含 ALTERNATIVE edges 作為保護來源）
        incoming_normal: dict[str, list[str]] = defaultdict(list)
        incoming_alt: dict[str, list[str]] = defaultdict(list)
        for edge in graph.edges:
            if edge.relationship == EdgeRelationship.ALTERNATIVE:
                incoming_alt[edge.target].append(edge.source)
            else:
                incoming_normal[edge.target].append(edge.source)

        for nid, node in graph.nodes.items():
            if node.status in (NodeStatus.PRUNED, NodeStatus.FAILED, NodeStatus.EXPLORED):
                continue
            normal_sources = incoming_normal.get(nid, [])
            if not normal_sources:
                continue

            # 檢查所有 normal incoming 是否全為 PRUNED/FAILED
            all_normal_dead = all(
                graph.nodes[s].status in (NodeStatus.PRUNED, NodeStatus.FAILED)
                for s in normal_sources
                if s in graph.nodes
            )

            if not all_normal_dead:
                continue

            # >>> 新增保護：檢查是否有存活的 alternative incoming <<<
            alt_sources = incoming_alt.get(nid, [])
            has_alive_alt = any(
                graph.nodes[s].status not in (NodeStatus.PRUNED, NodeStatus.FAILED)
                for s in alt_sources
                if s in graph.nodes
            )

            if has_alive_alt:
                # 至少有一條替代路徑仍存活，不修剪
                continue

            node.status = NodeStatus.PRUNED
            count += 1
            changed = True
    return count
```

### 5. 完整 50+ 規則清單

以下為 `technique_rules.yaml` 的完整規則集，按 MITRE ATT&CK 戰術分類。

#### 既有規則（13 條 — 從硬編碼遷移）

| # | technique_id | tactic_id | 說明 | platforms |
|---|-------------|-----------|------|-----------|
| 1 | T1595.001 | TA0043 | Active Scanning: Scanning IP Blocks | linux, windows |
| 2 | T1595.002 | TA0043 | Active Scanning: Vulnerability Scanning | linux, windows |
| 3 | T1190 | TA0001 | Exploit Public-Facing Application | linux, windows |
| 4 | T1110.001 | TA0001 | Brute Force: Password Guessing | linux, windows |
| 5 | T1059.004 | TA0002 | Command and Scripting Interpreter: Unix Shell | linux |
| 6 | T1003.001 | TA0006 | OS Credential Dumping: LSASS Memory | windows |
| 7 | T1087 | TA0007 | Account Discovery | linux, windows |
| 8 | T1083 | TA0007 | File and Directory Discovery | linux, windows |
| 9 | T1046 | TA0007 | Network Service Discovery | linux, windows |
| 10 | T1021.004 | TA0008 | Remote Services: SSH | linux |
| 11 | T1053.003 | TA0003 | Scheduled Task/Job: Cron | linux |
| 12 | T1560.001 | TA0009 | Archive Collected Data: Archive via Utility | linux, windows |
| 13 | T1105 | TA0011 | Ingress Tool Transfer | linux, windows |

#### P1 — Windows/Active Directory 攻擊鏈（新增 15 條）

| # | technique_id | tactic_id | 說明 | required_facts | produced_facts | risk_level | confidence | IG | effort | enables | alternatives | platforms |
|---|-------------|-----------|------|----------------|----------------|------------|------------|-----|--------|---------|-------------|-----------|
| 14 | T1558.003 | TA0006 | Steal or Forge Kerberos Tickets: Kerberoasting | credential.domain_user, host.ad_domain | credential.service_hash | medium | 0.80 | 0.85 | 2 | T1550.002, T1003.006 | T1003.001 | windows |
| 15 | T1003.006 | TA0006 | OS Credential Dumping: DCSync | credential.domain_admin, host.ad_domain | credential.ntds_hash | critical | 0.90 | 0.95 | 2 | T1550.002, T1550.003, T1558.001 | T1003.003 | windows |
| 16 | T1003.003 | TA0006 | OS Credential Dumping: NTDS | credential.domain_admin, host.ad_domain | credential.ntds_hash | critical | 0.85 | 0.90 | 3 | T1550.002, T1550.003 | T1003.006 | windows |
| 17 | T1021.001 | TA0008 | Remote Services: Remote Desktop Protocol | credential.domain_user, network.host.ip | host.session | medium | 0.70 | 0.65 | 2 | T1059.001 | T1021.002, T1021.006 | windows |
| 18 | T1021.002 | TA0008 | Remote Services: SMB/Windows Admin Shares | credential.domain_user, network.host.ip | host.session, host.file | medium | 0.75 | 0.70 | 2 | T1059.001 | T1021.001, T1021.006 | windows |
| 19 | T1021.006 | TA0008 | Remote Services: Windows Remote Management | credential.domain_user, network.host.ip | host.session | medium | 0.70 | 0.65 | 2 | T1059.001 | T1021.001, T1021.002 | windows |
| 20 | T1021.003 | TA0008 | Remote Services: Distributed Component Object Model | credential.domain_admin, network.host.ip | host.session | high | 0.60 | 0.60 | 3 | T1059.001 | T1021.002 | windows |
| 21 | T1548.002 | TA0004 | Abuse Elevation Control Mechanism: Bypass User Account Control | credential.domain_user, host.os | host.elevated_session | medium | 0.65 | 0.70 | 2 | T1059.001, T1543.003 | T1068 | windows |
| 22 | T1547.001 | TA0003 | Boot or Logon Autostart Execution: Registry Run Keys | credential.domain_user, host.session | host.persistence | low | 0.85 | 0.20 | 1 | — | T1053.005 | windows |
| 23 | T1053.005 | TA0003 | Scheduled Task/Job: Scheduled Task | credential.domain_user, host.session | host.persistence | medium | 0.80 | 0.25 | 1 | — | T1547.001 | windows |
| 24 | T1550.002 | TA0008 | Use Alternate Authentication Material: Pass the Hash | credential.hash, network.host.ip | host.session | high | 0.75 | 0.75 | 2 | T1059.001 | T1550.003 | windows |
| 25 | T1550.003 | TA0008 | Use Alternate Authentication Material: Pass the Ticket | credential.kerberos_ticket, network.host.ip | host.session | high | 0.70 | 0.70 | 2 | T1059.001 | T1550.002 | windows |
| 26 | T1558.001 | TA0006 | Steal or Forge Kerberos Tickets: Golden Ticket | credential.krbtgt_hash, host.ad_domain | credential.kerberos_ticket | critical | 0.95 | 0.95 | 3 | T1550.003 | T1558.002 | windows |
| 27 | T1558.002 | TA0006 | Steal or Forge Kerberos Tickets: Silver Ticket | credential.service_hash, host.ad_domain | credential.kerberos_ticket | high | 0.85 | 0.80 | 2 | T1550.003 | T1558.001 | windows |
| 28 | T1543.003 | TA0003 | Create or Modify System Process: Windows Service | credential.domain_admin, host.session | host.persistence | high | 0.80 | 0.30 | 2 | — | T1053.005 | windows |

#### P2 — Linux 提權與持久化（新增 10 條）

| # | technique_id | tactic_id | 說明 | required_facts | produced_facts | risk_level | confidence | IG | effort | enables | alternatives | platforms |
|---|-------------|-----------|------|----------------|----------------|------------|------------|-----|--------|---------|-------------|-----------|
| 29 | T1548.001 | TA0004 | Abuse Elevation Control Mechanism: Setuid and Setgid | credential.ssh, host.os | credential.root_shell | medium | 0.55 | 0.80 | 2 | T1059.004 | T1548.003, T1068 | linux |
| 30 | T1548.003 | TA0004 | Abuse Elevation Control Mechanism: Sudo and Sudo Caching | credential.ssh, host.user | credential.root_shell | medium | 0.60 | 0.80 | 2 | T1059.004 | T1548.001, T1068 | linux |
| 31 | T1068 | TA0004 | Exploitation for Privilege Escalation | credential.ssh, host.os, vuln.cve | credential.root_shell | high | 0.50 | 0.90 | 3 | T1059.004 | T1548.001, T1548.003 | linux, windows |
| 32 | T1098.004 | TA0003 | Account Manipulation: SSH Authorized Keys | credential.root_shell | host.persistence | low | 0.90 | 0.20 | 1 | — | T1053.003 | linux |
| 33 | T1574.006 | TA0004 | Hijack Execution Flow: Dynamic Linker Hijacking (LD_PRELOAD) | credential.ssh, host.os | credential.root_shell | high | 0.45 | 0.75 | 3 | T1059.004 | T1548.001 | linux |
| 34 | T1574.001 | TA0004 | Hijack Execution Flow: DLL Search Order Hijacking / Shared Library Injection | credential.ssh, host.os | credential.root_shell | high | 0.45 | 0.70 | 3 | T1059.004 | T1574.006 | linux |
| 35 | T1136.001 | TA0003 | Create Account: Local Account | credential.root_shell | host.persistence, host.user | medium | 0.85 | 0.25 | 1 | — | T1098.004 | linux, windows |
| 36 | T1611 | TA0004 | Escape to Host (Container Escape) | credential.ssh, host.container | credential.root_shell | critical | 0.40 | 0.90 | 4 | T1059.004 | T1068 | linux |
| 37 | T1543.002 | TA0003 | Create or Modify System Process: Systemd Service | credential.root_shell, host.os | host.persistence | medium | 0.80 | 0.25 | 1 | — | T1053.003 | linux |
| 38 | T1059.001 | TA0002 | Command and Scripting Interpreter: PowerShell | credential.domain_user, host.session | host.os, host.user, host.process | medium | 0.85 | 0.50 | 1 | T1059.003 | T1059.003 | windows |

#### P3 — 補足缺失類別（新增 14 條）

**Discovery（TA0007）— 新增 5 條：**

| # | technique_id | tactic_id | 說明 | required_facts | produced_facts | risk_level | confidence | IG | effort | enables | alternatives | platforms |
|---|-------------|-----------|------|----------------|----------------|------------|------------|-----|--------|---------|-------------|-----------|
| 39 | T1087.001 | TA0007 | Account Discovery: Local Account | credential.ssh | host.user | low | 0.90 | 0.40 | 1 | T1078.001 | T1087.002 | linux, windows |
| 40 | T1087.002 | TA0007 | Account Discovery: Domain Account | credential.domain_user, host.ad_domain | host.user, host.ad_users | low | 0.90 | 0.55 | 1 | T1558.003 | T1087.001 | windows |
| 41 | T1069.001 | TA0007 | Permission Groups Discovery: Local Groups | credential.ssh | host.groups | low | 0.90 | 0.35 | 1 | T1548.001, T1548.003 | T1069.002 | linux, windows |
| 42 | T1135 | TA0007 | Network Share Discovery | credential.domain_user, network.host.ip | host.file, network.share | low | 0.85 | 0.50 | 1 | T1021.002 | — | windows |
| 43 | T1018 | TA0007 | Remote System Discovery | credential.ssh, network.host.ip | network.host.ip | low | 0.90 | 0.60 | 1 | T1021.004, T1021.001 | — | linux, windows |

**Discovery（TA0007）— 既有規則已涵蓋 T1082/T1083/T1057，以下為增補：**

| # | technique_id | tactic_id | 說明 | required_facts | produced_facts | risk_level | confidence | IG | effort | enables | alternatives | platforms |
|---|-------------|-----------|------|----------------|----------------|------------|------------|-----|--------|---------|-------------|-----------|
| 44 | T1082 | TA0007 | System Information Discovery | credential.ssh | host.os, host.arch | low | 0.95 | 0.45 | 1 | T1068 | — | linux, windows |
| 45 | T1057 | TA0007 | Process Discovery | credential.ssh | host.process | low | 0.90 | 0.35 | 1 | — | — | linux, windows |

**Exfiltration（TA0010）— 新增 3 條：**

| # | technique_id | tactic_id | 說明 | required_facts | produced_facts | risk_level | confidence | IG | effort | enables | alternatives | platforms |
|---|-------------|-----------|------|----------------|----------------|------------|------------|-----|--------|---------|-------------|-----------|
| 46 | T1048.001 | TA0010 | Exfiltration Over Alternative Protocol: Exfiltration Over Symmetric Encrypted Non-C2 Protocol | credential.ssh, host.file | exfil.data | high | 0.70 | 0.30 | 2 | — | T1048.002 | linux, windows |
| 47 | T1048.002 | TA0010 | Exfiltration Over Alternative Protocol: Exfiltration Over Asymmetric Encrypted Non-C2 Protocol | credential.ssh, host.file | exfil.data | medium | 0.75 | 0.30 | 2 | — | T1048.001 | linux, windows |
| 48 | T1074.001 | TA0009 | Data Staged: Local Data Staging | credential.ssh, host.file | host.staged_data | low | 0.85 | 0.20 | 1 | T1048.001, T1048.002 | — | linux, windows |

**Impact（TA0040）— 新增 2 條：**

| # | technique_id | tactic_id | 說明 | required_facts | produced_facts | risk_level | confidence | IG | effort | enables | alternatives | platforms |
|---|-------------|-----------|------|----------------|----------------|------------|------------|-----|--------|---------|-------------|-----------|
| 49 | T1489 | TA0040 | Service Stop | credential.root_shell | impact.service_disruption | critical | 0.85 | 0.10 | 1 | — | T1486 | linux, windows |
| 50 | T1486 | TA0040 | Data Encrypted for Impact | credential.root_shell, host.file | impact.ransomware | critical | 0.80 | 0.10 | 3 | — | T1489 | linux, windows |

**Defense Evasion（TA0005）— 新增 2 條：**

| # | technique_id | tactic_id | 說明 | required_facts | produced_facts | risk_level | confidence | IG | effort | enables | alternatives | platforms |
|---|-------------|-----------|------|----------------|----------------|------------|------------|-----|--------|---------|-------------|-----------|
| 51 | T1070.001 | TA0005 | Indicator Removal: Clear Windows Event Logs | credential.domain_admin, host.session | host.evasion | medium | 0.80 | 0.10 | 1 | — | T1070.002 | windows |
| 52 | T1070.002 | TA0005 | Indicator Removal: Clear Linux or Mac System Logs | credential.root_shell | host.evasion | medium | 0.80 | 0.10 | 1 | — | T1070.001 | linux |

**Credential Access（TA0006）— 增補：**

| # | technique_id | tactic_id | 說明 | required_facts | produced_facts | risk_level | confidence | IG | effort | enables | alternatives | platforms |
|---|-------------|-----------|------|----------------|----------------|------------|------------|-----|--------|---------|-------------|-----------|
| 53 | T1078.001 | TA0006 | Valid Accounts: Default Accounts | service.open_port | credential.ssh | low | 0.40 | 0.60 | 1 | T1059.004 | T1110.001 | linux, windows |

**Initial Access（TA0001）— 增補：**

| # | technique_id | tactic_id | 說明 | required_facts | produced_facts | risk_level | confidence | IG | effort | enables | alternatives | platforms |
|---|-------------|-----------|------|----------------|----------------|------------|------------|-----|--------|---------|-------------|-----------|
| 54 | T1133 | TA0001 | External Remote Services | service.open_port, credential.ssh | host.session | medium | 0.75 | 0.65 | 1 | T1059.004 | T1190, T1110.001 | linux, windows |

**Lateral Movement（TA0008）— 增補：**

| # | technique_id | tactic_id | 說明 | required_facts | produced_facts | risk_level | confidence | IG | effort | enables | alternatives | platforms |
|---|-------------|-----------|------|----------------|----------------|------------|------------|-----|--------|---------|-------------|-----------|
| 55 | T1069.002 | TA0007 | Permission Groups Discovery: Domain Groups | credential.domain_user, host.ad_domain | host.groups, host.ad_groups | low | 0.90 | 0.50 | 1 | T1558.003 | T1069.001 | windows |

**合計：13（既有） + 15（P1） + 10（P2） + 17（P3）= 55 條規則**

### 6. Hot-Reload API 端點

在 `backend/app/routers/admin.py` 新增端點：

```python
@router.post("/admin/rules/reload", tags=["admin"])
async def reload_technique_rules():
    """Hot-reload technique rules from YAML without restart."""
    from app.services.attack_graph_engine import reload_rules
    reload_rules()
    return {"status": "ok", "message": "Rules reloaded"}
```

### 7. 戰術類別覆蓋統計

| 戰術 ID | 戰術名稱 | 規則數量 | 覆蓋狀態 |
|---------|----------|---------|---------|
| TA0043 | Reconnaissance | 2 | 既有 |
| TA0001 | Initial Access | 3 | 增補 +1 |
| TA0002 | Execution | 2 | 增補 +1 |
| TA0003 | Persistence | 6 | 增補 +4 |
| TA0004 | Privilege Escalation | 7 | 新增 |
| TA0005 | Defense Evasion | 2 | 新增 |
| TA0006 | Credential Access | 6 | 增補 +4 |
| TA0007 | Discovery | 10 | 增補 +7 |
| TA0008 | Lateral Movement | 7 | 增補 +5 |
| TA0009 | Collection | 2 | 增補 +1 |
| TA0010 | Exfiltration | 2 | 新增 |
| TA0011 | Command and Control | 1 | 既有 |
| TA0040 | Impact | 2 | 新增 |
| **合計** | **13 個戰術** | **55 條** | **覆蓋 13/14 戰術** |

---

## 🔗 副作用與連動（Side Effects）

| 本功能的狀態變動 | 受影響的既有功能 | 預期行為 |
|-----------------|----------------|---------|
| `_PREREQUISITE_RULES` 從硬編碼改為 YAML 載入 | `_build_graph_in_memory()` 圖建構 | 行為不變，規則來源改為 YAML |
| `_RULE_BY_TECHNIQUE` 改為動態載入 | `_build_edges()`、`prune_dead_branches()` | 行為不變，lookup 方式不變 |
| `compute_edge_weight()` 改為 `compute_edge_cost()` | `compute_recommended_path()` Dijkstra | 移除 `cost = 1.0 - weight` 反轉，直接使用 weight 作為成本 |
| `compute_edge_weight()` 改為 `compute_edge_cost()` | `build_orient_summary()` 中的 total_weight 加總 | 語意從「好處加總」變為「成本加總」，數值解讀方式改變 |
| `compute_edge_weight()` 改為 `compute_edge_cost()` | `_break_cycles()` 中的 min weight 選擇 | 語意從「移除最低好處邊」變為「移除最低成本邊」-- 需確認此行為是否仍正確（移除最低成本邊 = 保留較高成本邊 = 保守策略）|
| 規則數量從 13 增至 55 | 每個 target 產生的 AttackNode 數量增至 55 | 圖的記憶體使用量和建構時間增加（預估在可接受範圍） |
| 修剪邏輯修正 | `prune_dead_branches()` | 替代技術不再被錯誤修剪，攻擊圖保留更多可行路徑 |
| `TechniqueRule` 新增 `platforms` 欄位 | 目前 `_build_graph_in_memory()` 未依平台過濾 | Phase 1 不過濾，後續可依 target OS 過濾 |
| `TechniqueRule` 新增 `description` 欄位 | 目前無使用方 | 僅供文件化和除錯使用 |

---

## ⚠️ 邊界條件（Edge Cases）

- **Case 1**：YAML 檔案不存在 — `_load_rules()` 拋出 `FileNotFoundError`，應用啟動失敗，錯誤訊息包含預期路徑
- **Case 2**：YAML 語法錯誤 — `yaml.safe_load()` 拋出 `yaml.YAMLError`，應用啟動失敗，錯誤訊息包含行號
- **Case 3**：Pydantic 驗證失敗（如 confidence > 1.0）— `TechniqueRulesFile` 拋出 `ValidationError`，錯誤訊息包含欄位名稱和違反的限制
- **Case 4**：`enables` 引用不存在的 technique_id — 此為 warning 層級，不阻擋載入（因為可能引用未來才新增的規則）。在 `_load_rules()` 中檢查並 `logger.warning()`
- **Case 5**：Hot-reload 期間有正在進行的 `rebuild()` — `reload_rules()` 透過原子性替換 module-level 變數，不影響正在執行的函式（Python GIL 保證 reference assignment 的原子性）
- **Case 6**：規則 `technique_id` 重複 — 後者覆蓋前者，`_load_rules()` 發出 `logger.warning()`
- **Case 7**：空的 `rules` 清單 — Pydantic `min_length=1` 驗證阻擋
- **Case 8**：`_break_cycles()` 語意在新公式下的影響 — 新公式下 weight 直接為成本值，`min(cycle_edges, key=lambda e: e.weight)` 移除成本最低的邊。這表示移除「最容易」的路徑以打破循環。若需保留最容易路徑，應改為 `max()`。建議 Phase 1 保持 `min()` 不變，後續依實測結果調整

### 回退方案（Rollback Plan）

- **回退方式**：revert commit + 刪除 `backend/app/data/technique_rules.yaml`
- **不可逆評估**：此變更完全可逆。`technique_rules.yaml` 為新檔案，`TechniqueRule` 的新欄位有 default 值，刪除後不影響既有程式碼
- **資料影響**：若已有使用新規則產生的攻擊圖存於資料庫，回退後這些圖的節點 technique_id 可能無法對應到規則。需執行 `DELETE FROM attack_graph_nodes WHERE technique_id NOT IN (...)` 清理

---

## ✅ 驗收標準（Done When）

### Phase 1 — YAML 外部化與規則載入

- [ ] `backend/app/data/technique_rules.yaml` 存在且包含 55 條規則
- [ ] `_load_rules()` 在應用啟動時成功載入所有規則，無 error/warning
- [ ] YAML 載入時間 < 100ms（`time.perf_counter()` 量測）
- [ ] `len(_PREREQUISITE_RULES) >= 50` 斷言成立
- [ ] 統計規則中不重複的 `tactic_id` 數量 >= 8
- [ ] Pydantic 驗證捕獲以下錯誤場景：
  - `base_confidence: 1.5` → `ValidationError`
  - `risk_level: "extreme"` → `ValidationError`
  - `technique_id: "INVALID"` → `ValidationError`
  - `produced_facts: []` → `ValidationError`
  - `platforms: []` → `ValidationError`
- [ ] `TechniqueRule` dataclass 包含 `platforms` 和 `description` 欄位

### Phase 2 — 成本公式重構

- [ ] `compute_edge_weight()` 已重命名為 `compute_edge_cost()`
- [ ] 所有呼叫點已更新
- [ ] Dijkstra 中的 `cost = 1.0 - edge.weight` 已改為 `cost = edge.weight`
- [ ] 成本公式驗證測試：
  - 高 confidence (0.95) + 高 IG (0.9) + low risk + effort 1 → cost 約 0.08
  - 低 confidence (0.4) + 低 IG (0.3) + high risk + effort 4 → cost 約 0.53
  - 驗證前者 cost < 後者 cost
- [ ] 路徑品質測試：建構兩條路徑「低風險低 IG」vs「中風險高 IG」，驗證 Dijkstra 優先推薦後者
- [ ] `RISK_COST_MAP` 包含四個等級且值為 0.1, 0.3, 0.6, 1.0

### Phase 3 — 修剪邏輯修正

- [ ] 修剪正確性測試：T1110.001 失敗後 T1190 仍為 `PENDING` 狀態
- [ ] 修剪正確性測試：T1110.001 失敗後，與 T1110.001 共享前置條件且**不在** `alternatives` 的兄弟節點被正確修剪
- [ ] 傳播修剪測試：當某節點所有 normal incoming edge 來源已死亡，但有存活的 alternative incoming edge，該節點不被修剪
- [ ] 傳播修剪測試：當某節點所有 incoming edge（含 alternative）來源均已死亡，該節點被正確修剪

### Phase 4 — Hot-Reload 與整合

- [ ] `POST /admin/rules/reload` 回傳 `{"status": "ok"}`
- [ ] Hot-reload 後 `_RULE_BY_TECHNIQUE` 包含更新後的規則
- [ ] `make test-filter FILTER=attack_graph` 全數通過
- [ ] 既有的 `build_orient_summary()` 在新規則集下正常運作
- [ ] `make lint` 無 error

---

## 🚫 禁止事項（Out of Scope）

- 不要依 target OS 過濾規則（`platforms` 欄位 Phase 1 僅載入不過濾，待後續 SPEC 實作過濾邏輯）
- 不要將規則遷移至資料庫（ADR-036 已決策為 YAML）
- 不要修改 `AttackGraph`、`AttackNode`、`AttackEdge` 的結構（僅修改 `TechniqueRule`）
- 不要修改 OODA 迭代邏輯或 Orient prompt schema
- 不要引入除 `pyyaml`（已有）和 `pydantic`（已有）以外的新依賴
- 不要修改 `_TACTIC_ORDER` 戰術順序或 `_TACTIC_NAMES` 映射表
- 不要在 YAML 中包含任何 Python 程式碼或 `!python` 標籤（必須使用 `yaml.safe_load`）

---

## 📎 參考資料（References）

- 相關 ADR：ADR-036（攻擊圖規則外部化與路徑最佳化）、ADR-028（攻擊圖引擎核心架構）
- 現有類似實作：`_PREREQUISITE_RULES` 硬編碼清單 in `attack_graph_engine.py` 第 45-130 行
- 關鍵檔案：
  - `backend/app/services/attack_graph_engine.py` — 引擎主體，規則載入、邊權計算、修剪邏輯
  - `backend/app/models/attack_graph.py` — 資料模型，`TechniqueRule` 擴展
  - `backend/app/data/technique_rules.yaml` — 新增 YAML 規則檔案（本 SPEC 建立）
  - `backend/app/routers/admin.py` — Hot-reload 端點
  - `backend/tests/test_attack_graph_engine.py` — 既有測試（需更新）
- 外部文件：
  - [MITRE ATT&CK Enterprise Matrix](https://attack.mitre.org/matrices/enterprise/)
  - SPEC-031（攻擊圖規格書）
  - SPEC-037（OODA Access Recovery — 參考 `credential.ssh.invalidated` fact 排除邏輯）

<!-- tech-debt: scenario-pending — v3.2 upgrade: needs test matrix + Gherkin scenarios -->
<!-- tech-debt: observability-pending — v3.3 upgrade: needs observability section -->
