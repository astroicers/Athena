# SPEC-038：C5ISR 域評估報告實作

> 結構完整的規格書讓 AI 零確認直接執行。

| 欄位 | 內容 |
|------|------|
| **規格 ID** | SPEC-038 |
| **關聯 ADR** | ADR-035 |
| **估算複雜度** | L（大型 — 後端與前端皆需顯著變更） |

---

## 🎯 目標（Goal）

> 將 C5ISR 六域健康度從虛榮指標（vanity metrics）升級為結構化域評估報告（Domain Assessment Report）。每個域產出包含 executive summary、加權指標、資產清冊、戰術評估、風險向量、建議行動與跨域影響的完整報告。`detail` 欄位改為儲存 JSON 序列化的 `DomainReport`，`health_pct` 保留供六角儀表向後相容顯示。前端 DomainCard 新增展開/收合功能，展開時渲染完整報告。

---

## 📥 輸入規格（Inputs）

### 後端輸入（每次 OODA 迭代觸發 `C5ISRMapper.update()`）

| 參數名稱 | 型別 | 來源 | 說明 |
|----------|------|------|------|
| `db` | `aiosqlite.Connection` | FastAPI DI | 資料庫連線 |
| `operation_id` | `str (UUID)` | `ooda_controller` | 當前作戰 ID |

### 各域所需 DB 查詢

| 域 | 查詢表 | 所需欄位 | 目的 |
|----|--------|----------|------|
| **Command** | `operations` | `ooda_iteration_count`, `max_iterations` | 決策吞吐量 |
| | `recommendations` | `accepted`, `created_at` | 接受率、停滯偵測 |
| | `ooda_directives` | `consumed_at` | 指令消耗率 |
| **Control** | `agents` | `status`, `last_beacon`, `paw`, `host_id` | Agent 存活率、beacon 新鮮度 |
| | `targets` | `access_status` | 存取穩定性 |
| **Comms** | `ws_manager` | 活躍連線數（記憶體） | WebSocket 連線健康 |
| | `tool_registry` | `enabled`, `kind='tool'` | MCP 可用性 |
| | `broadcast` 結果 | 成功/失敗計數 | 廣播成功率 |
| **Computers** | `targets` | `is_compromised`, `privilege_level`, `hostname`, `ip_address`, `access_status` | 入侵率、權限深度 |
| | `technique_executions` | `status`, kill chain 階段 | Kill chain 推進度 |
| **Cyber** | `technique_executions` | `status`, `engine`, `created_at`, `technique_id` | 偵察/利用成功率、趨勢 |
| | `techniques` | `tactic` | 區分偵察類與利用類 |
| **ISR** | `recommendations` | `confidence`, `created_at` | 信心趨勢 |
| | `facts` | `trait`, `category` | 事實覆蓋率 |
| | `attack_graph_nodes` | `status` | 圖譜覆蓋率 |

### 前端輸入（WebSocket `c5isr.update` 事件）

| 欄位 | 型別 | 說明 |
|------|------|------|
| `domains[].report` | `DomainReport \| null` | 新增：完整域報告 JSON（見輸出規格） |
| `domains[].health_pct` | `number` | 保留：向後相容健康百分比 |
| `domains[].status` | `string` | 保留：語義狀態 |

---

## 📤 輸出規格（Expected Output）

### 後端資料結構

#### `DomainReport` dataclass（新增於 `backend/app/services/c5isr_mapper.py`）

```python
from dataclasses import dataclass, field, asdict
from enum import Enum
import json

class RiskSeverity(str, Enum):
    CRIT = "CRIT"
    WARN = "WARN"
    INFO = "INFO"

@dataclass
class DomainMetric:
    """單一加權指標。"""
    name: str                # e.g. "decision_throughput"
    value: float             # 0.0-100.0
    weight: float            # 0.0-1.0
    numerator: int | None = None
    denominator: int | None = None

@dataclass
class RiskVector:
    """風險項目。"""
    severity: RiskSeverity   # CRIT / WARN / INFO
    message: str

@dataclass
class DomainReport:
    """結構化域評估報告。"""
    executive_summary: str
    health_pct: float
    status: str                          # C5ISRDomainStatus.value
    metrics: list[DomainMetric] = field(default_factory=list)
    asset_roster: list[dict] = field(default_factory=list)
    tactical_assessment: str = ""
    risk_vectors: list[RiskVector] = field(default_factory=list)
    recommended_actions: list[str] = field(default_factory=list)
    cross_domain_impacts: list[str] = field(default_factory=list)

    def to_json(self) -> str:
        """序列化為 JSON 字串（儲存至 DB detail 欄位）。"""
        return json.dumps(asdict(self), ensure_ascii=False)

    @classmethod
    def from_json(cls, raw: str) -> "DomainReport":
        """從 JSON 字串反序列化。損壞時回傳空報告。"""
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return cls(executive_summary="", health_pct=0.0, status="critical")
        data["metrics"] = [DomainMetric(**m) for m in data.get("metrics", [])]
        data["risk_vectors"] = [RiskVector(**r) for r in data.get("risk_vectors", [])]
        return cls(**data)
```

#### JSON 結構範例（儲存於 `c5isr_statuses.detail`）

```json
{
  "executive_summary": "指揮決策吞吐量正常，接受率 85%，無停滯跡象",
  "health_pct": 78.5,
  "status": "nominal",
  "metrics": [
    {
      "name": "decision_throughput",
      "value": 80.0,
      "weight": 0.40,
      "numerator": 8,
      "denominator": 10
    },
    {
      "name": "acceptance_rate",
      "value": 85.0,
      "weight": 0.35,
      "numerator": 17,
      "denominator": 20
    },
    {
      "name": "directive_consumption",
      "value": 66.7,
      "weight": 0.25,
      "numerator": 2,
      "denominator": 3
    }
  ],
  "asset_roster": [
    {"type": "directive", "id": "d-001", "status": "consumed"},
    {"type": "directive", "id": "d-002", "status": "pending"}
  ],
  "tactical_assessment": "OODA 迭代穩定推進中，指揮官指令消耗率偏低，建議確認是否有未處理的策略指導。",
  "risk_vectors": [
    {"severity": "WARN", "message": "指令消耗率低於 70%，可能存在未被 Orient 處理的策略指導"}
  ],
  "recommended_actions": [
    "檢視未消耗的指令並確認其相關性",
    "考慮增加 OODA 迭代上限以提高決策吞吐量"
  ],
  "cross_domain_impacts": [
    "ISR：決策吞吐量影響情報收集的迭代深度",
    "Control：接受率影響 Agent 派遣頻率"
  ]
}
```

### 各域 `_build_X_report()` 方法與加權公式

以下方法皆新增於 `C5ISRMapper` class 內（`backend/app/services/c5isr_mapper.py`），各回傳 `DomainReport`。

所有域的 `health_pct` 統一以加權公式計算：

```
health_pct = round(sum(metric.value * metric.weight for metric in metrics), 1)
```

#### 1. `_build_command_report(db, operation_id) -> DomainReport`

| 指標 | 欄位名 | 權重 | 計算方式 | 退化機制 |
|------|--------|------|----------|----------|
| 決策吞吐量 | `decision_throughput` | 0.40 | `min(100, ooda_count / max(1, expected_iterations) * 100)` — `expected_iterations` = `operations.max_iterations` 或預設 20 | 停滯懲罰（見下方） |
| 接受率 | `acceptance_rate` | 0.35 | `accepted_count / total_recommendations * 100`（無 recommendation 時為 50.0 基線） | 無退化 |
| 指令消耗率 | `directive_consumption` | 0.25 | `consumed_directives / total_directives * 100`（無指令時為 100.0） | 無退化 |

**停滯懲罰（stall penalty）**：查詢最近 3 筆 `recommendations.created_at`，若最舊一筆距今超過 `ooda_iteration_count * 30s * 3`（即 3 次迭代週期無新 recommendation），`decision_throughput.value` 減 20（下限 0）。

**SQL 範例**：

```sql
-- 決策吞吐量
SELECT ooda_iteration_count, max_iterations FROM operations WHERE id = ?;

-- 接受率
SELECT COUNT(*) as total,
       SUM(CASE WHEN accepted = 1 THEN 1 ELSE 0 END) as accepted
FROM recommendations WHERE operation_id = ?;

-- 指令消耗率
SELECT COUNT(*) as total,
       SUM(CASE WHEN consumed_at IS NOT NULL THEN 1 ELSE 0 END) as consumed
FROM ooda_directives WHERE operation_id = ?;

-- 停滯偵測
SELECT created_at FROM recommendations
WHERE operation_id = ? ORDER BY created_at DESC LIMIT 3;
```

**Asset Roster**：列出所有 `ooda_directives`，包含 `id`、`directive`（截取前 80 字元）、`status`（consumed/pending）。

#### 2. `_build_control_report(db, operation_id) -> DomainReport`

| 指標 | 欄位名 | 權重 | 計算方式 | 退化機制 |
|------|--------|------|----------|----------|
| Agent 存活率 | `agent_liveness` | 0.50 | `alive_agents / total_agents * 100`（無 agent 時為 0.0） | 無退化 |
| 存取穩定性 | `access_stability` | 0.30 | `active_targets / (active_targets + lost_targets) * 100` — `access_status='active'` 為分子，`access_status IN ('active','lost')` 為分母；分母為 0 時值為 0.0 | 無退化 |
| Beacon 新鮮度 | `beacon_freshness` | 0.20 | 所有 alive agent 的 `last_beacon` 距今平均秒數，轉換為 `max(0, 100 - avg_staleness_sec / 60 * 10)`；無 alive agent 時為 0.0 | `last_beacon` 超過 5 分鐘（300 秒）的 agent，每個額外懲罰 -5（下限 0） |

**SQL 範例**：

```sql
-- Agent 存活率
SELECT COUNT(*) as total,
       SUM(CASE WHEN status = 'alive' THEN 1 ELSE 0 END) as alive
FROM agents WHERE operation_id = ?;

-- 存取穩定性
SELECT SUM(CASE WHEN access_status = 'active' THEN 1 ELSE 0 END) as active_count,
       SUM(CASE WHEN access_status IN ('active', 'lost') THEN 1 ELSE 0 END) as total_accessed
FROM targets WHERE operation_id = ?;

-- Beacon 新鮮度
SELECT last_beacon FROM agents
WHERE operation_id = ? AND status = 'alive' AND last_beacon IS NOT NULL;
```

**Asset Roster**：列出所有 agents，包含 `paw`、`status`、`host_id`、`last_beacon`、`privilege`。

#### 3. `_build_comms_report(db, operation_id) -> DomainReport`

| 指標 | 欄位名 | 權重 | 計算方式 |
|------|--------|------|----------|
| WebSocket 連線 | `ws_connections` | 0.40 | `min(100, self._ws.active_connection_count() * 50)` — 至少 2 連線 = 100% |
| MCP 可用性 | `mcp_availability` | 0.30 | `enabled_tools / total_tools * 100`（查 `tool_registry WHERE kind='tool'`） |
| 廣播成功率 | `broadcast_success` | 0.30 | `self._ws._broadcast_success / max(1, self._ws._broadcast_total) * 100` — `_broadcast_total` 為 0 時值為 100.0（無失敗記錄=假設成功） |

**需新增 `backend/app/ws_manager.py`（現行 L25-62）方法與屬性**：

```python
# ws_manager.py — __init__（L29）新增
self._broadcast_total: int = 0
self._broadcast_success: int = 0

# ws_manager.py — 新增方法（L77 之前）
def active_connection_count(self) -> int:
    """回傳所有 operation 的活躍 WebSocket 連線總數。"""
    return sum(len(conns) for conns in self._connections.values())

# ws_manager.py — broadcast()（L44-62）內新增計數
# 在方法開頭：self._broadcast_total += 1
# 遍歷完 connections 後：若至少一個 ws.send_text 成功（無 exception）則 self._broadcast_success += 1
```

**SQL 範例**：

```sql
-- MCP 可用性
SELECT COUNT(*) as total,
       SUM(CASE WHEN enabled = 1 THEN 1 ELSE 0 END) as enabled_count
FROM tool_registry WHERE kind = 'tool';
```

**Asset Roster**：列出已啟用的 MCP tools，包含 `tool_id`、`name`、`enabled`。

#### 4. `_build_computers_report(db, operation_id) -> DomainReport`

| 指標 | 欄位名 | 權重 | 計算方式 |
|------|--------|------|----------|
| 入侵率 | `compromise_rate` | 0.40 | `compromised_targets / total_targets * 100`（無 target 時為 0.0） |
| 權限深度 | `privilege_depth` | 0.35 | `root_targets / max(1, compromised_targets) * 100` — `privilege_level='Root'` 為 root_targets |
| Kill Chain 推進度 | `killchain_advancement` | 0.25 | 依最高已達成 kill chain 階段給分：`recon=20, weaponize=30, deliver=40, exploit=50, install=70, c2=85, action=100`；無 execution 時為 0 |

**SQL 範例**：

```sql
-- 入侵率 + 權限深度
SELECT COUNT(*) as total,
       SUM(CASE WHEN is_compromised = 1 THEN 1 ELSE 0 END) as compromised,
       SUM(CASE WHEN is_compromised = 1 AND privilege_level = 'Root' THEN 1 ELSE 0 END) as root_count
FROM targets WHERE operation_id = ?;

-- Kill Chain 推進度（取最高階段）
SELECT DISTINCT t.kill_chain_stage
FROM technique_executions te
JOIN techniques t ON te.technique_id = t.mitre_id
WHERE te.operation_id = ? AND te.status = 'success';
```

Kill chain 階段對應分數映射（依 `backend/app/models/enums.py` L101-108 `KillChainStage` enum）：

```python
_KILLCHAIN_SCORES = {
    "recon": 20, "weaponize": 30, "deliver": 40,
    "exploit": 50, "install": 70, "c2": 85, "action": 100,
}
```

**Asset Roster**：列出所有 targets，包含 `hostname`、`ip_address`、`is_compromised`、`privilege_level`、`access_status`。

#### 5. `_build_cyber_report(db, operation_id) -> DomainReport`

| 指標 | 欄位名 | 權重 | 計算方式 | 退化機制 |
|------|--------|------|----------|----------|
| 偵察成功率 | `recon_success` | 0.25 | recon 類 execution 的 `success / total * 100`（無 recon 時為 0.0） | 無退化 |
| 利用成功率 | `exploit_success` | 0.45 | 非 recon 類 execution 的 `success / total * 100`（無利用類時為 0.0） | 無退化 |
| 近期趨勢 | `recent_trend` | 0.30 | 最近 5 次 execution 的成功率 vs 整體成功率差值：`base + delta`，`base = overall_success_rate * 100`，`delta = (recent_rate - overall_rate) * 100`，結果 clamp 至 [0, 100] | 下降趨勢偵測：若 `recent_rate < overall_rate - 0.20` 則值固定為 0 |

**偵察/非偵察分類**：依 `techniques.tactic` 判斷，tactic 為 `Reconnaissance` 或 `Discovery` 為偵察類，其餘為利用類。使用 LEFT JOIN `techniques` on `te.technique_id = t.mitre_id`，未匹配時 `tactic` 為 NULL，預設歸類為利用類。

**SQL 範例**：

```sql
-- 分類統計
SELECT
    CASE WHEN t.tactic IN ('Reconnaissance', 'Discovery') THEN 'recon' ELSE 'exploit' END as category,
    COUNT(*) as total,
    SUM(CASE WHEN te.status = 'success' THEN 1 ELSE 0 END) as success
FROM technique_executions te
LEFT JOIN techniques t ON te.technique_id = t.mitre_id
WHERE te.operation_id = ?
GROUP BY category;

-- 最近 5 次
SELECT status FROM technique_executions
WHERE operation_id = ? ORDER BY created_at DESC LIMIT 5;

-- 整體成功率
SELECT COUNT(*) as total,
       SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as success
FROM technique_executions WHERE operation_id = ?;
```

#### 6. `_build_isr_report(db, operation_id) -> DomainReport`

| 指標 | 欄位名 | 權重 | 計算方式 |
|------|--------|------|----------|
| 信心趨勢 | `confidence_trend` | 0.35 | 最近 5 筆 `recommendations.confidence` 的平均值 * 100（無 recommendation 時為 0.0） |
| 事實覆蓋率 | `fact_coverage` | 0.35 | `distinct_trait_categories / 7 * 100` — 7 = `FactCategory` enum 成員數（credential, host, network, osint, service, vulnerability, file；見 `enums.py` L83-89）；category 由 `facts.category` 取得 |
| 圖譜覆蓋率 | `graph_coverage` | 0.30 | `reachable_or_completed_nodes / total_nodes * 100`（`attack_graph_nodes.status IN ('reachable','completed')`）；無節點時為 0.0 |

**SQL 範例**：

```sql
-- 信心趨勢
SELECT confidence FROM recommendations
WHERE operation_id = ? ORDER BY created_at DESC LIMIT 5;

-- 事實覆蓋率
SELECT COUNT(DISTINCT category) as distinct_categories
FROM facts WHERE operation_id = ?;

-- 圖譜覆蓋率
SELECT COUNT(*) as total,
       SUM(CASE WHEN status IN ('reachable', 'completed') THEN 1 ELSE 0 END) as covered
FROM attack_graph_nodes WHERE operation_id = ?;
```

**Asset Roster**：列出最近 10 筆 `facts`，包含 `trait`、`value`（截取前 60 字元）、`category`、`collected_at`。

### DB 變更

**無 schema 變更**。`c5isr_statuses.detail` 欄位型別已為 `TEXT`（見 `backend/app/database.py` L197-209），改為儲存 JSON 序列化的 `DomainReport` 取代原本的單行文字。`health_pct` 欄位保留且繼續更新（從 `DomainReport.health_pct` 取值）。

### WebSocket 廣播 payload 變更

**事件**：`c5isr.update`

**現行 payload**（`c5isr_mapper.py` L143-150）：

```json
{
  "domains": [
    {
      "id": "...",
      "operation_id": "...",
      "domain": "command",
      "status": "nominal",
      "health_pct": 78.5,
      "detail": "OODA cycle active",
      "numerator": 8,
      "denominator": null,
      "metric_label": "OODA iterations"
    }
  ]
}
```

**新 payload**（向後相容 — 新增 `report` 欄位）：

```json
{
  "domains": [
    {
      "id": "...",
      "operation_id": "...",
      "domain": "command",
      "status": "nominal",
      "health_pct": 78.5,
      "detail": "指揮決策吞吐量正常，接受率 85%，無停滯跡象",
      "numerator": 8,
      "denominator": 10,
      "metric_label": "decision_throughput",
      "report": {
        "executive_summary": "指揮決策吞吐量正常，接受率 85%，無停滯跡象",
        "health_pct": 78.5,
        "status": "nominal",
        "metrics": [ "..." ],
        "asset_roster": [ "..." ],
        "tactical_assessment": "...",
        "risk_vectors": [ "..." ],
        "recommended_actions": [ "..." ],
        "cross_domain_impacts": [ "..." ]
      }
    }
  ]
}
```

`detail` 欄位改為 `DomainReport.executive_summary`（向後相容，舊前端仍能顯示摘要文字）。`numerator` / `denominator` 改為第一個 metric 的值。`metric_label` 改為第一個 metric 的 name。`report` 為完整 `DomainReport` dict。

### 前端型別定義

**修改 `frontend/src/types/c5isr.ts`** — 新增型別並擴充 `C5ISRStatus`：

```typescript
export interface DomainMetric {
  name: string;
  value: number;
  weight: number;
  numerator: number | null;
  denominator: number | null;
}

export type RiskSeverity = "CRIT" | "WARN" | "INFO";

export interface RiskVector {
  severity: RiskSeverity;
  message: string;
}

export interface DomainReport {
  executive_summary: string;
  health_pct: number;
  status: string;
  metrics: DomainMetric[];
  asset_roster: Array<Record<string, unknown>>;
  tactical_assessment: string;
  risk_vectors: RiskVector[];
  recommended_actions: string[];
  cross_domain_impacts: string[];
}

export interface C5ISRStatus {
  id: string;
  operationId: string;
  domain: C5ISRDomain;
  status: C5ISRDomainStatus;
  healthPct: number;
  detail: string;
  numerator: number | null;
  denominator: number | null;
  metricLabel: string;
  report: DomainReport | null;  // 新增
}
```

### 前端元件變更

#### `DomainCard.tsx` — 展開/收合

- 新增 `expanded` state（`useState<boolean>(false)`）
- **收合狀態**（預設）：維持現有 UI — HexGauge + `executive_summary`（取自 `domain.detail`）+ ProgressBar。右上角顯示展開指示器（chevron icon），僅當 `domain.report` 不為 `null` 時顯示
- **展開狀態**：額外渲染以下區段（位於現有卡片下方展開）：
  1. **指標表格**：`report.metrics` — 每行顯示 `name`、`value`（含 `numerator/denominator` 標註）、`weight`、進度條
  2. **資產清冊**：`report.asset_roster` — 依 `type` 欄位分組的表格，每組最多顯示 10 筆
  3. **戰術評估**：`report.tactical_assessment` — 灰底文字段落
  4. **風險向量**：`report.risk_vectors` — 依 severity 著色的列表（CRIT=`text-athena-error`、WARN=`text-athena-warning`、INFO=`text-athena-info`）
  5. **建議行動**：`report.recommended_actions` — 有序列表（`<ol>`）
  6. **跨域影響**：`report.cross_domain_impacts` — 無序列表（`<ul>`）
- 展開觸發方式：點擊卡片任意處
- `report` 為 `null` 時不顯示展開指示器，點擊無效（向後相容）

---

## 🔗 副作用與連動（Side Effects）

| 本功能的狀態變動 | 受影響的既有功能 | 預期行為 |
|-----------------|----------------|---------|
| `detail` 欄位改存 JSON（`DomainReport.to_json()`） | `GET /api/operations/{id}/c5isr` 回傳 | 回傳 JSON 字串；前端 parse 後使用。DB 內仍為 TEXT，不影響 schema |
| `health_pct` 計算公式全面改變 | 六角儀表顯示數值 | Command 域不再自動膨脹至 100%；Comms 域不再硬編碼 60%；所有域 health_pct 基於加權指標 |
| `ws_manager` 新增 `active_connection_count()` | 無既有依賴 | 純新增方法，無副作用 |
| `ws_manager` 新增 `_broadcast_total` / `_broadcast_success` | `broadcast()` 方法 | 極微量開銷（兩個 int 累加），可忽略 |
| `numerator` / `denominator` / `metric_label` 語義改變 | 前端 DomainCard 摘要顯示 | 改為第一個 metric 的對應值，需更新前端顯示邏輯 |
| `c5isr.update` WebSocket payload 新增 `report` 欄位 | 前端 WebSocket handler | 需更新 handler 以 parse `report` 欄位 |
| Comms 域查詢 `tool_registry` | 無既有依賴 | 新增 1 次 DB 查詢 |
| Cyber 域 LEFT JOIN `techniques` 表 | 無既有依賴 | 新增 JOIN 查詢；`technique_id` 可能為非標準 mitre_id（如 `T1021.004_priv`），LEFT JOIN 確保不遺漏 |
| ISR 域查詢 `attack_graph_nodes` | 無既有依賴 | 新增 1 次 DB 查詢 |
| 每次 OODA 迭代 DB 查詢數增加 | OODA 迭代效能 | 從 ~5 次增至 ~15 次查詢；SQLite WAL 模式下預計增加 < 50ms |

---

## ⚠️ 邊界條件（Edge Cases）

- **Case 1**：Operation 剛建立、尚無任何 OODA 迭代 — 所有域 metrics 使用基線值：Command `decision_throughput=0`, `acceptance_rate=50`（基線）, `directive_consumption=100`（無指令=100%）；其餘域 metrics 值為 0；`executive_summary` 為描述性文字（如「尚未開始 OODA 迭代，等待首次 Observe」）
- **Case 2**：無 agents、無 targets — Control 域所有指標為 0，status 為 `CRITICAL`；Computers 域所有指標為 0；Asset Roster 為空陣列
- **Case 3**：所有 targets 已 compromised 且為 Root — Computers 域 `health_pct=100`；在 `risk_vectors` 加入 `INFO`：「所有目標已完全控制，考慮擴大攻擊面」
- **Case 4**：WebSocket 無連線（headless 模式）— Comms 域 `ws_connections=0`（0 分），但 `mcp_availability` 和 `broadcast_success` 仍正常計算；`health_pct` 不應為 0（MCP 可能正常運作）
- **Case 5**：`detail` 欄位儲存的 JSON 格式損壞 — `DomainReport.from_json()` catch `json.JSONDecodeError` / `TypeError`，回傳預設空報告（`health_pct=0.0`, `status='critical'`）
- **Case 6**：前端收到不含 `report` 欄位的 `c5isr.update` 事件（舊後端）— `report` 為 `null`，DomainCard 不顯示展開指示器，點擊無效（向後相容）
- **Case 7**：`_broadcast_total` 為 0（首次 Comms 計算前尚未有任何 broadcast）— `broadcast_success` 值設為 100.0（無失敗記錄=假設成功）
- **Case 8**：`technique_executions.technique_id` 無法 JOIN `techniques.mitre_id`（自由格式 ID 如 `T1021.004_priv`）— 使用 LEFT JOIN，未匹配時 `tactic` 為 NULL，預設歸類為利用類
- **Case 9**：`recommendations` 表中 `accepted` 為 NULL（尚未決定）— 不計入 `accepted_count`，僅計入 `total_recommendations`
- **Case 10**：`agents.last_beacon` 為 NULL — 該 agent 排除於 beacon 新鮮度計算之外

### 回退方案（Rollback Plan）

- **回退方式**：revert commit(s)
- **不可逆評估**：此變更完全可逆。`detail` 欄位仍為 TEXT 型別，回退後重新寫入純文字即可。`health_pct` 回退後回到舊公式計算
- **資料影響**：回退後 `detail` 欄位內的 JSON 會被舊版代碼當作純文字顯示，但下一次 OODA 迭代會覆蓋為舊格式。`ws_manager` 的廣播計數為記憶體變數，重啟即清除
- **DB migration 需求**：無。不需要新增/移除欄位或索引

---

## ✅ 驗收標準（Done When）

### Phase 1 — 後端 DomainReport 資料結構與加權公式

- [ ] `RiskSeverity` enum、`DomainMetric`、`RiskVector`、`DomainReport` dataclass 定義於 `backend/app/services/c5isr_mapper.py`
- [ ] `DomainReport.to_json()` 正確序列化所有欄位（含巢狀 dataclass）
- [ ] `DomainReport.from_json()` 正確反序列化，含 `json.JSONDecodeError` / `TypeError` 防護
- [ ] `C5ISRMapper` 新增 6 個私有方法：`_build_command_report()`、`_build_control_report()`、`_build_comms_report()`、`_build_computers_report()`、`_build_cyber_report()`、`_build_isr_report()`
- [ ] 每個 `_build_X_report()` 回傳完整 `DomainReport`，至少包含：`executive_summary`（非空字串）、`health_pct`（加權計算，0.0-100.0）、`metrics`（2-3 個 `DomainMetric`）、`tactical_assessment`（非空字串）
- [ ] `C5ISRMapper.update()` 改為呼叫 `_build_X_report()` 並將 `report.to_json()` 存入 `detail` 欄位
- [ ] `health_pct` 由 `DomainReport.health_pct` 取值，與 `sum(metric.value * metric.weight)` 計算結果誤差 <= 0.1
- [ ] **Command 域無自動膨脹**：無真實 recommendation 時 `health_pct` 不可超過 50（`decision_throughput` 受限，`acceptance_rate` 為 50 基線）
- [ ] **Comms 域非硬編碼**：`health_pct` 反映真實 WebSocket 連線數與 MCP 可用性，非固定 60%
- [ ] 所有 6 個域的加權公式符合 ADR-035 定義的權重表
- [ ] `_health_to_status()` 方法不變（`c5isr_mapper.py` L156-172），繼續使用 `DomainReport.health_pct` 決定 `C5ISRDomainStatus`

### Phase 2 — ws_manager 擴充與 WebSocket payload

- [ ] `ws_manager.py` 新增 `active_connection_count() -> int` 方法（`backend/app/ws_manager.py`）
- [ ] `ws_manager.py` `__init__` 新增 `_broadcast_total: int = 0` 與 `_broadcast_success: int = 0`
- [ ] `ws_manager.py` `broadcast()` 方法內新增計數邏輯：每次呼叫 `_broadcast_total += 1`，至少一個 client 成功接收時 `_broadcast_success += 1`
- [ ] `c5isr.update` WebSocket payload 每個 domain dict 新增 `report` 欄位（完整 `DomainReport` dict）
- [ ] `detail` 欄位值改為 `DomainReport.executive_summary`（向後相容）
- [ ] 舊版前端（不認識 `report` 欄位）仍可正常顯示 `detail` + `health_pct`

### Phase 3 — 前端型別與 DomainCard 展開/收合

- [ ] `frontend/src/types/c5isr.ts` 新增 `DomainMetric`、`RiskVector`、`RiskSeverity`、`DomainReport` TypeScript type
- [ ] `C5ISRStatus` interface 新增 `report: DomainReport | null` 欄位
- [ ] `DomainCard.tsx` 新增 `expanded` state，實作展開/收合功能
- [ ] 收合時顯示：HexGauge + `executive_summary`（`domain.detail`）+ ProgressBar（現有行為）
- [ ] 展開時額外顯示：指標表格、資產清冊、戰術評估、風險向量（severity 著色）、建議行動（`<ol>`）、跨域影響（`<ul>`）
- [ ] `domain.report` 為 `null` 時不顯示展開指示器，點擊無效（向後相容）
- [ ] 風險向量 severity 著色：CRIT = `text-athena-error`、WARN = `text-athena-warning`、INFO = `text-athena-info`
- [ ] i18n 鍵值新增至 `frontend/messages/en.json` 與 `frontend/messages/zh-TW.json`（含：`metrics`、`assetRoster`、`tacticalAssessment`、`riskVectors`、`recommendedActions`、`crossDomainImpacts` 等）

### Phase 4 — 測試

- [ ] 單元測試：`DomainReport.to_json()` / `from_json()` round-trip 一致性
- [ ] 單元測試：`DomainReport.from_json()` 處理損壞 JSON 不 raise exception
- [ ] 單元測試：每個 `_build_X_report()` 方法至少 3 個測試案例 —（1）正常資料、（2）空資料/邊界、（3）退化觸發
- [ ] 單元測試：Command 域停滯懲罰 — 3 次迭代週期無新 recommendation 時 `decision_throughput` 減 20
- [ ] 單元測試：Command 域無自動膨脹 — `ooda_count=20` 但無 recommendation 時 `health_pct < 50`
- [ ] 單元測試：Comms 域在無 WebSocket 連線時 `ws_connections=0`，但有啟用 MCP tools 時 `health_pct > 0`
- [ ] 單元測試：Cyber 域下降趨勢偵測 — 最近 5 次成功率低於整體 20%+ 時 `recent_trend=0`
- [ ] 單元測試：ISR 域 `fact_coverage` 正確計算 distinct category 數
- [ ] 整合測試：完整 OODA 迭代後所有 6 域產出結構化報告，每個報告至少 3 個區段有非空內容
- [ ] 整合測試：health_pct 準確度 — 與加權指標計算結果誤差 <= 0.1
- [ ] 前端測試：`DomainCard` 展開/收合行為 — 點擊展開、再次點擊收合
- [ ] 前端測試：`report` 為 `null` 時無展開指示器
- [ ] `make test` 全數通過

---

## 🚫 禁止事項（Out of Scope）

- 不要修改 `c5isr_statuses` 表 schema（不新增/移除欄位）— `detail` 改存 JSON 不算 schema 變更
- 不要引入 LLM 生成報告（ADR-035 已決策為確定性組裝，選項 C 被否決）
- 不要移除 `health_pct` 欄位或停止更新（向後相容需求）
- 不要修改 OODA 迭代邏輯（`ooda_controller.py`）或 Orient 的 JSON output schema
- 不要引入新的 Python 或 npm 依賴
- 不要修改 `_health_to_status()` 的閾值對應表（`c5isr_mapper.py` L156-172）
- 不要變更 WebSocket 事件名稱（維持 `c5isr.update`）
- 不要在 `DomainReport` 中包含敏感資訊（密碼、API Key、憑證明文）
- 不要修改 `C5ISRStatusBoard.tsx` 或 `C5ISRFloatingPanel.tsx`（無需變更）

---

## 📎 參考資料（References）

- **關聯 ADR**：ADR-035（C5ISR 域評估報告架構）、ADR-012（C5ISR 框架映射）、ADR-003（OODA loop 架構）
- **前序 SPEC**：SPEC-037（OODA Access Recovery — `access_status` 欄位，`targets` 表）、SPEC-007（OODA loop engine）
- **關鍵檔案**：
  - `backend/app/services/c5isr_mapper.py` — 主要修改目標（現行 173 行，預估重寫後 ~550 行）
  - `backend/app/ws_manager.py` — 新增 `active_connection_count()` 與廣播計數（現行 L25-62）
  - `backend/app/database.py` — DB schema 參考（`c5isr_statuses` 表定義 L197-209；`recommendations` L168-179；`ooda_directives` L157-165；`agents` L82-94；`targets` L65-79；`technique_executions` L111-125；`facts` L127-138；`attack_graph_nodes` L305-324）
  - `backend/app/models/enums.py` — `C5ISRDomain`（L63-69）、`C5ISRDomainStatus`（L72-80）、`FactCategory`（L83-89）
  - `frontend/src/types/c5isr.ts` — 前端型別定義（新增 `DomainReport` 等型別）
  - `frontend/src/components/c5isr/DomainCard.tsx` — 展開/收合 UI 實作（現行 131 行）
  - `frontend/src/components/c5isr/C5ISRStatusBoard.tsx` — 父元件（不修改）
  - `frontend/src/components/c5isr/C5ISRFloatingPanel.tsx` — 浮動面板（不修改）
  - `frontend/src/components/c5isr/__tests__/DomainCard.test.tsx` — 現有測試（需擴充）
  - `frontend/messages/en.json` / `frontend/messages/zh-TW.json` — i18n 鍵值新增

<!-- tech-debt: scenario-pending — v3.2 upgrade: needs test matrix + Gherkin scenarios -->
<!-- tech-debt: observability-pending — v3.3 upgrade: needs observability section -->
