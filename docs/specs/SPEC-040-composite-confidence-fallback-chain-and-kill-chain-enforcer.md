# SPEC-040：複合信心評分、引擎回退鏈與 Kill Chain 強制器

> 結構完整的規格書讓 AI 零確認直接執行。

| 欄位 | 內容 |
|------|------|
| **規格 ID** | SPEC-040 |
| **關聯 ADR** | ADR-037 |
| **估算複雜度** | M（單元件中等，三元件合併為 M-L） |

---

## 🎯 目標（Goal）

> 將 Decision Engine 的信心評分從單一 LLM 來源升級為四來源複合評分（LLM + 歷史成功率 + 攻擊圖節點信心 + 目標狀態），加入 Kill Chain 跳階懲罰機制，並為 Engine Router 實作引擎回退鏈，使 Act 階段在主引擎失敗時自動切換至替代引擎。

---

## 📥 輸入規格（Inputs）

### 元件 A：複合信心評分（Composite Confidence）

| 參數名稱 | 型別 | 來源 | 限制條件 |
|----------|------|------|----------|
| raw_confidence | float | `recommendation.get("confidence", 0.0)` — LLM 輸出 | 0.0–1.0 |
| technique_id | string | `recommendation.recommended_technique_id` | MITRE ATT&CK ID |
| target_id | string (UUID) | DecisionEngine 選定的 target | 必須存在於 targets 表 |
| operation_id | string (UUID) | 當前 operation | 必須存在於 operations 表 |
| tactic_id | string | 從 `attack_graph_nodes` 或 `_PREREQUISITE_RULES` 查詢 | TA00xx 格式 |

### 元件 B：引擎回退鏈（Engine Fallback Chain）

| 參數名稱 | 型別 | 來源 | 限制條件 |
|----------|------|------|----------|
| engine | string | DecisionEngine 的 `engine` 欄位 | `"mcp_ssh"` / `"metasploit"` / `"c2"` |
| result | dict | `_execute_single()` 回傳值 | 必須包含 `status` 和 `error` 欄位 |
| operation_id | string (UUID) | 呼叫端傳入 | WebSocket 廣播用 |

### 元件 C：Kill Chain 強制器（Kill Chain Enforcer）

| 參數名稱 | 型別 | 來源 | 限制條件 |
|----------|------|------|----------|
| operation_id | string (UUID) | DecisionEngine 傳入 | — |
| tactic_id | string | 推薦技術的 tactic ID | TA00xx 格式 |
| target_id | string (UUID) | 目標 target | — |

---

## 📤 輸出規格（Expected Output）

### 元件 A：複合信心評分

**公式：**

```
composite = 0.30 * llm + 0.30 * historical + 0.25 * graph + 0.15 * target_state - kc_penalty
final = clamp(composite, 0.0, 1.0)
```

**各來源計算方式：**

| 來源 | 權重 | 計算方式 | 無資料時預設值 |
|------|------|---------|-------------|
| LLM (`llm`) | 0.30 | `recommendation.get("confidence", 0.0)` — 原始 LLM 輸出 | 0.0 |
| 歷史成功率 (`historical`) | 0.30 | `成功次數 / 總執行次數` — 查詢 `technique_executions` 表中同一 `technique_id` 的記錄 | 0.5（無歷史資料時） |
| 攻擊圖節點信心 (`graph`) | 0.25 | 從 `attack_graph_nodes` 查詢同一 `operation_id` + `technique_id` + `target_id` 的 `confidence` 值 | 0.5（無節點時） |
| 目標狀態 (`target_state`) | 0.15 | 基於 `targets` 表欄位的加權分數（見下方） | 0.5（無 target 時） |
| Kill Chain 懲罰 (`kc_penalty`) | 扣除 | KillChainEnforcer 計算的懲罰值 | 0.0 |

**權重設計理由（ADR-037）：**

- 0.30 LLM：具備策略性上下文理解能力，但幻覺風險使其不宜超過 30%
- 0.30 Historical：來自實際執行的地面真相，作為經驗性對照權重與 LLM 相等
- 0.25 Graph：確定性的先決條件滿足度計算，可靠度高
- 0.15 Target state：重要但資料常不完整

**目標狀態分數計算：**

```python
def _compute_target_state_score(target_row: dict, has_edr: bool) -> float:
    score = 0.5  # 基準值
    if target_row.get("is_compromised"):
        score += 0.2
    if (target_row.get("privilege_level") or "").lower() in ("root", "system", "administrator"):
        score += 0.15
    if target_row.get("access_status") == "lost":
        score -= 0.1
    # EDR 偵測：從 facts 表查詢 trait='host.edr' 或 trait='host.av'
    if has_edr:
        score -= 0.2
    return max(0.0, min(1.0, score))
```

**回傳結構（新增欄位注入 `DecisionEngine.evaluate()` 回傳的 dict）：**

```python
{
    # ...existing fields (technique_id, target_id, engine, risk_level, auto_approved, etc.)...
    "composite_confidence": 0.72,       # 複合信心值
    "confidence_breakdown": {
        "llm": 0.85,
        "historical": 0.67,
        "graph": 0.70,
        "target_state": 0.65,
        "kc_penalty": 0.05,
    },
}
```

### 元件 B：引擎回退鏈

**回退映射表：**

```python
_FALLBACK_CHAIN: dict[str, list[str]] = {
    "mcp_ssh":     ["metasploit", "c2"],
    "metasploit":  ["mcp_ssh", "c2"],
    "c2":          ["mcp_ssh"],
}
```

**終端性錯誤（不觸發回退）：**

```python
_TERMINAL_ERRORS: list[str] = [
    "scope violation",
    "platform mismatch",
    "blocked by rules of engagement",
]

def _is_terminal_error(error: str | None) -> bool:
    if not error:
        return False
    lower = error.lower()
    return any(te in lower for te in _TERMINAL_ERRORS)
```

**WebSocket 事件格式：**

```python
# 事件類型: "execution.fallback"
{
    "execution_id": "uuid",
    "technique_id": "T1059.004",
    "failed_engine": "mcp_ssh",
    "fallback_engine": "metasploit",
    "failed_error": "connection timed out",
    "attempt": 1,           # 第幾次回退嘗試（1-based）
    "max_attempts": 2,      # 該引擎的最大回退數
}
```

**最終回傳 dict 新增欄位：**

```python
{
    # ...existing fields (execution_id, technique_id, target_id, engine, status, etc.)...
    "fallback_history": [
        {"engine": "mcp_ssh", "error": "connection timed out"},
    ],
    "final_engine": "metasploit",  # 實際成功執行的引擎（或最後失敗的引擎）
}
```

### 元件 C：Kill Chain 強制器

**Kill Chain 階段順序與 MITRE Tactic 映射：**

```python
_KILL_CHAIN_STAGES: list[tuple[int, str, str, bool]] = [
    # (stage, tactic_id, name, required)
    (0,  "TA0043", "Reconnaissance",        True),
    (1,  "TA0042", "Resource Development",  False),  # 可跳過
    (2,  "TA0001", "Initial Access",        True),
    (3,  "TA0002", "Execution",             True),
    (4,  "TA0003", "Persistence",           False),  # 可跳過
    (5,  "TA0004", "Privilege Escalation",  True),
    (6,  "TA0005", "Defense Evasion",       False),  # 可跳過
    (7,  "TA0006", "Credential Access",     True),
    (8,  "TA0007", "Discovery",             True),
    (9,  "TA0008", "Lateral Movement",      True),
    (10, "TA0009", "Collection",            True),
    (11, "TA0011", "Command and Control",   False),  # 可跳過
    (12, "TA0010", "Exfiltration",          True),
    (13, "TA0040", "Impact",               True),
]
```

**可跳過階段（`required: False`）：** TA0042、TA0003、TA0005、TA0011

**懲罰規則：**
- 每跳過一個 `required: True` 的階段：扣 0.05
- 最大累計懲罰：0.25
- 跳過 `required: False` 的階段：不扣分

**回傳結構：**

```python
@dataclass
class KillChainPenalty:
    penalty: float              # 0.0–0.25
    skipped_stages: list[str]   # e.g. ["TA0001 (Initial Access)", "TA0002 (Execution)"]
    warning: str | None         # 人類可讀警告訊息，無跳階時為 None
```

---

## 🔗 副作用與連動（Side Effects）

| 本功能的狀態變動 | 受影響的既有功能 | 預期行為 |
|-----------------|----------------|---------|
| `confidence` 改為複合計算 | `DecisionEngine.evaluate()` 中的 `confidence < 0.5` 閘控（第 144 行） | 使用 `composite_confidence` 取代 `raw_confidence` 進行閘控判斷 |
| 複合信心可能低於原始 LLM 信心 | 自動核准門檻判斷 | 某些原本自動核准的技術可能降為需確認（歷史成功率低或目標有 EDR） |
| 複合信心可能高於原始 LLM 信心 | 同上 | 某些原本需確認的技術可能升為自動核准（歷史成功率高時） |
| `execute()` 重命名為 `_execute_single()` | `ooda_controller.py` 中呼叫 `engine_router.execute()` | 無影響 — 外部 API 維持 `execute()` 不變 |
| 回退嘗試產生額外 `technique_executions` 記錄 | Orient 的歷史執行摘要 | 回退嘗試的 engine 欄位正確記錄實際使用的引擎 |
| `execution.fallback` WebSocket 事件 | 前端 WarRoom 即時更新 | 前端需處理新事件類型（可選，初版不處理不影響功能） |
| KillChainEnforcer 懲罰扣分 | 複合信心最終值 | 跳階推薦的信心值降低，可能觸發人工確認 |

---

## ⚠️ 邊界條件（Edge Cases）

### 元件 A：複合信心

- **Case A1**：`technique_executions` 表中該技術無任何歷史執行記錄 — `historical` 回退為 0.5（中性值）
- **Case A2**：`attack_graph_nodes` 中該技術/目標無對應節點 — `graph` 回退為 0.5
- **Case A3**：`target_id` 為 None（DecisionEngine 未找到 target） — 所有 DB 查詢跳過，使用預設值 `{historical: 0.5, graph: 0.5, target_state: 0.5}`
- **Case A4**：歷史成功率為 0.0（該技術從未成功） — 正常計入，會顯著拉低複合信心
- **Case A5**：LLM 回傳 confidence > 1.0 或 < 0.0 — 在計算前 `clamp(raw_confidence, 0.0, 1.0)`

### 元件 B：引擎回退

- **Case B1**：主引擎回傳終端性錯誤（scope violation） — 不觸發回退，直接回傳失敗
- **Case B2**：所有回退引擎都失敗 — 回傳最後一個引擎的失敗結果，`fallback_history` 包含所有嘗試
- **Case B3**：`engine` 值不在 `_FALLBACK_CHAIN` 中（例如 `"mcp"`） — 不觸發回退，行為與現有邏輯一致
- **Case B4**：回退引擎也回傳終端性錯誤 — 停止回退鏈，回傳該終端性錯誤
- **Case B5**：認證失敗觸發 `_handle_access_lost()`（SPEC-037）後進入回退 — 正常回退，因為認證失敗不是終端性錯誤
- **Case B6**：回退期間 WebSocket 連線中斷 — `broadcast()` 已有 try/except 保護，不影響回退邏輯

### 元件 C：Kill Chain 強制器

- **Case C1**：推薦技術的 tactic_id 不在 `_KILL_CHAIN_STAGES` 中 — penalty = 0.0，無警告
- **Case C2**：推薦 TA0008（Lateral Movement）但 TA0001（Initial Access）從未成功 — 跳過 TA0001 + TA0002 等必要階段，累計懲罰
- **Case C3**：跳過 6 個以上必要階段 — 懲罰仍上限為 0.25
- **Case C4**：推薦 TA0043（Reconnaissance，stage 0） — 無前置階段可跳過，penalty = 0.0
- **Case C5**：同一 target 在不同 OODA 迭代中完成不同階段 — 查詢該 target 的所有成功執行記錄，跨迭代累計

### 回退方案（Rollback Plan）

- **回退方式**：revert commit(s)
- **不可逆評估**：此變更完全可逆。新增的 `kill_chain_enforcer.py` 為獨立模組，刪除後不影響既有功能。`_execute_single()` 重命名可在 revert 時恢復為 `execute()`
- **資料影響**：無 DB schema 變更，回退不影響資料

---

## 🏗️ 實作細節（Implementation Details）

### 檔案變更清單

| 檔案 | 變更類型 | 說明 |
|------|---------|------|
| `backend/app/services/decision_engine.py` | 修改 | 新增 `_compute_composite_confidence()` 及四個子方法；`evaluate()` 改用複合信心 |
| `backend/app/services/engine_router.py` | 修改 | 重命名 `execute()` → `_execute_single()`；新 `execute()` 包裝回退邏輯 |
| `backend/app/services/kill_chain_enforcer.py` | **新增** | Kill Chain 跳階懲罰計算模組 |
| `backend/tests/test_composite_confidence.py` | **新增** | 複合信心單元測試 |
| `backend/tests/test_engine_fallback.py` | **新增** | 引擎回退鏈單元測試 |
| `backend/tests/test_kill_chain_enforcer.py` | **新增** | Kill Chain 強制器單元測試 |

### 元件 A：複合信心評分 — `decision_engine.py` 虛擬碼

```python
# 新增 import
from app.services.kill_chain_enforcer import KillChainEnforcer

class DecisionEngine:
    """Decide phase: apply ADR-004 risk threshold rules to PentestGPT recommendation."""

    def __init__(self):
        self._enforcer = KillChainEnforcer()

    async def evaluate(self, db, operation_id, recommendation) -> dict:
        # ... 現有邏輯取得 rec_technique_id, options, target_id ...

        raw_confidence = recommendation.get("confidence", 0.0)

        # ── 新增：取得 tactic_id ──
        tactic_id = await self._resolve_tactic_id(
            db, operation_id, rec_technique_id, target_id
        )

        # ── 新增：計算複合信心 ──
        composite, breakdown = await self._compute_composite_confidence(
            db, operation_id, rec_technique_id, target_id, raw_confidence, tactic_id
        )

        # ── 變更：使用 composite 取代 raw_confidence 進行閘控 ──
        confidence = composite

        # ... 現有閘控邏輯（confidence < 0.5, CRITICAL, HIGH 等，不變） ...

        # ── 新增：回傳時注入新欄位 ──
        result = {
            **base,
            "composite_confidence": composite,
            "confidence_breakdown": breakdown,
            # ...existing fields...
        }
        return result

    # ── 新增方法 ─────────────────────────────────────────────────

    async def _compute_composite_confidence(
        self,
        db: aiosqlite.Connection,
        operation_id: str,
        technique_id: str,
        target_id: str | None,
        raw_confidence: float,
        tactic_id: str | None,
    ) -> tuple[float, dict]:
        """四來源複合信心評分 + Kill Chain 懲罰。"""
        raw_confidence = max(0.0, min(1.0, raw_confidence))

        hist_rate = await self._get_historical_success_rate(db, technique_id)
        graph_conf = await self._get_graph_node_confidence(
            db, operation_id, technique_id, target_id
        )
        target_score = await self._get_target_state_score(db, target_id)

        kc_result = await self._enforcer.evaluate_skip(
            db, operation_id, tactic_id, target_id
        )

        composite = (
            0.30 * raw_confidence
            + 0.30 * hist_rate
            + 0.25 * graph_conf
            + 0.15 * target_score
            - kc_result.penalty
        )
        composite = max(0.0, min(1.0, composite))

        breakdown = {
            "llm": raw_confidence,
            "historical": hist_rate,
            "graph": graph_conf,
            "target_state": target_score,
            "kc_penalty": kc_result.penalty,
        }
        return composite, breakdown

    async def _get_historical_success_rate(
        self, db: aiosqlite.Connection, technique_id: str
    ) -> float:
        """查詢 technique_executions 中同一 technique_id 的成功率。"""
        cursor = await db.execute(
            "SELECT COUNT(*) as total, "
            "SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successes "
            "FROM technique_executions WHERE technique_id = ?",
            (technique_id,),
        )
        row = await cursor.fetchone()
        total = row["total"] if isinstance(row, dict) else row[0]
        successes = row["successes"] if isinstance(row, dict) else row[1]
        if not total:
            return 0.5  # 無歷史資料 → 中性值
        return (successes or 0) / total

    async def _get_graph_node_confidence(
        self, db: aiosqlite.Connection,
        operation_id: str, technique_id: str, target_id: str | None,
    ) -> float:
        """從 attack_graph_nodes 取得節點信心值。"""
        if not target_id:
            return 0.5
        cursor = await db.execute(
            "SELECT confidence FROM attack_graph_nodes "
            "WHERE operation_id = ? AND technique_id = ? AND target_id = ? "
            "ORDER BY updated_at DESC LIMIT 1",
            (operation_id, technique_id, target_id),
        )
        row = await cursor.fetchone()
        if not row:
            return 0.5  # 無節點 → 中性值
        return row["confidence"] if isinstance(row, dict) else row[0]

    async def _get_target_state_score(
        self, db: aiosqlite.Connection, target_id: str | None,
    ) -> float:
        """計算目標狀態分數。"""
        if not target_id:
            return 0.5
        cursor = await db.execute(
            "SELECT is_compromised, privilege_level, access_status "
            "FROM targets WHERE id = ?",
            (target_id,),
        )
        row = await cursor.fetchone()
        if not row:
            return 0.5

        is_compromised = row["is_compromised"] if isinstance(row, dict) else row[0]
        privilege = (
            (row["privilege_level"] if isinstance(row, dict) else row[1]) or ""
        )
        access_status = (
            (row["access_status"] if isinstance(row, dict) else row[2]) or ""
        )

        score = 0.5
        if is_compromised:
            score += 0.2
        if privilege.lower() in ("root", "system", "administrator"):
            score += 0.15
        if access_status == "lost":
            score -= 0.1

        # EDR 偵測：查詢 facts 表
        edr_cursor = await db.execute(
            "SELECT COUNT(*) FROM facts "
            "WHERE source_target_id = ? AND trait IN ('host.edr', 'host.av')",
            (target_id,),
        )
        edr_row = await edr_cursor.fetchone()
        edr_count = edr_row[0] if edr_row else 0
        if edr_count > 0:
            score -= 0.2

        return max(0.0, min(1.0, score))

    async def _resolve_tactic_id(
        self, db: aiosqlite.Connection,
        operation_id: str, technique_id: str, target_id: str | None,
    ) -> str | None:
        """從 attack_graph_nodes 或 _PREREQUISITE_RULES 取得 tactic_id。"""
        if target_id:
            cursor = await db.execute(
                "SELECT tactic_id FROM attack_graph_nodes "
                "WHERE operation_id = ? AND technique_id = ? AND target_id = ? "
                "LIMIT 1",
                (operation_id, technique_id, target_id),
            )
            row = await cursor.fetchone()
            if row:
                return row["tactic_id"] if isinstance(row, dict) else row[0]
        # 回退至靜態規則表
        from app.services.attack_graph_engine import _RULE_BY_TECHNIQUE  # noqa: PLC0415
        rule = _RULE_BY_TECHNIQUE.get(technique_id)
        return rule.tactic_id if rule else None
```

### 元件 B：引擎回退鏈 — `engine_router.py` 虛擬碼

```python
# ── 新增常數（檔案頂層） ─────────────────────────────────────────

_FALLBACK_CHAIN: dict[str, list[str]] = {
    "mcp_ssh":    ["metasploit", "c2"],
    "metasploit": ["mcp_ssh", "c2"],
    "c2":         ["mcp_ssh"],
}

_TERMINAL_ERRORS: list[str] = [
    "scope violation",
    "platform mismatch",
    "blocked by rules of engagement",
]

def _is_terminal_error(error: str | None) -> bool:
    """判斷錯誤是否為終端性（不應回退）。"""
    if not error:
        return False
    lower = error.lower()
    return any(te in lower for te in _TERMINAL_ERRORS)


class EngineRouter:
    # ── 步驟 1：現有 execute() 重命名為 _execute_single() ──
    # 所有內部邏輯完全不變，僅將方法名稱從 execute 改為 _execute_single

    async def _execute_single(
        self, db, technique_id, target_id, engine, operation_id,
        ooda_iteration_id=None,
    ) -> dict:
        """原有 execute() 邏輯，未修改。"""
        # ... 現有完整邏輯（MCP route → Metasploit route → engine selection） ...

    # ── 步驟 2：新的 execute() 包裝回退邏輯 ──

    async def execute(
        self, db: aiosqlite.Connection, technique_id: str, target_id: str,
        engine: str, operation_id: str, ooda_iteration_id: str | None = None,
    ) -> dict:
        """帶回退鏈的執行入口。

        邏輯：
        1. 嘗試主引擎
        2. 成功或終端性錯誤 → 直接回傳
        3. 非終端性失敗 → 依序嘗試 _FALLBACK_CHAIN 中的替代引擎
        4. 每次回退廣播 execution.fallback WebSocket 事件
        """
        fallback_history: list[dict] = []

        # 嘗試主引擎
        result = await self._execute_single(
            db, technique_id, target_id, engine, operation_id, ooda_iteration_id,
        )

        # 成功或終端性錯誤 → 直接回傳
        if result.get("status") == "success" or _is_terminal_error(result.get("error")):
            result["fallback_history"] = fallback_history
            result["final_engine"] = result.get("engine", engine)
            return result

        # 記錄主引擎失敗
        fallback_history.append({
            "engine": engine,
            "error": result.get("error"),
        })

        # 依序嘗試回退引擎
        fallback_engines = _FALLBACK_CHAIN.get(engine, [])
        for attempt, fallback_engine in enumerate(fallback_engines, start=1):
            # 廣播回退事件
            await self._ws.broadcast(operation_id, "execution.fallback", {
                "execution_id": result.get("execution_id"),
                "technique_id": technique_id,
                "failed_engine": fallback_history[-1]["engine"],
                "fallback_engine": fallback_engine,
                "failed_error": fallback_history[-1]["error"],
                "attempt": attempt,
                "max_attempts": len(fallback_engines),
            })

            logger.info(
                "Fallback attempt %d/%d: %s -> %s for technique %s",
                attempt, len(fallback_engines),
                fallback_history[-1]["engine"],
                fallback_engine, technique_id,
            )

            result = await self._execute_single(
                db, technique_id, target_id, fallback_engine,
                operation_id, ooda_iteration_id,
            )

            if result.get("status") == "success" or _is_terminal_error(
                result.get("error")
            ):
                result["fallback_history"] = fallback_history
                result["final_engine"] = result.get("engine", fallback_engine)
                return result

            # 記錄此次回退失敗
            fallback_history.append({
                "engine": fallback_engine,
                "error": result.get("error"),
            })

        # 所有引擎都失敗
        result["fallback_history"] = fallback_history
        result["final_engine"] = result.get(
            "engine",
            fallback_engines[-1] if fallback_engines else engine,
        )
        return result
```

### 元件 C：Kill Chain 強制器 — `backend/app/services/kill_chain_enforcer.py`

```python
"""Kill Chain Enforcer — 跳階懲罰計算模組。

SPEC-040 / ADR-037 選項 C：對跳過必要 Kill Chain 階段的推薦施加信心懲罰。
"""

import logging
from dataclasses import dataclass, field

import aiosqlite

logger = logging.getLogger(__name__)

# Kill Chain 階段定義
_KILL_CHAIN_STAGES: list[tuple[int, str, str, bool]] = [
    # (stage, tactic_id, name, required)
    (0,  "TA0043", "Reconnaissance",        True),
    (1,  "TA0042", "Resource Development",  False),
    (2,  "TA0001", "Initial Access",        True),
    (3,  "TA0002", "Execution",             True),
    (4,  "TA0003", "Persistence",           False),
    (5,  "TA0004", "Privilege Escalation",  True),
    (6,  "TA0005", "Defense Evasion",       False),
    (7,  "TA0006", "Credential Access",     True),
    (8,  "TA0007", "Discovery",             True),
    (9,  "TA0008", "Lateral Movement",      True),
    (10, "TA0009", "Collection",            True),
    (11, "TA0011", "Command and Control",   False),
    (12, "TA0010", "Exfiltration",          True),
    (13, "TA0040", "Impact",               True),
]

_TACTIC_TO_STAGE: dict[str, int] = {t[1]: t[0] for t in _KILL_CHAIN_STAGES}
_TACTIC_TO_NAME: dict[str, str] = {t[1]: t[2] for t in _KILL_CHAIN_STAGES}
_TACTIC_REQUIRED: dict[str, bool] = {t[1]: t[3] for t in _KILL_CHAIN_STAGES}

_PENALTY_PER_SKIP = 0.05
_MAX_PENALTY = 0.25


@dataclass
class KillChainPenalty:
    penalty: float = 0.0
    skipped_stages: list[str] = field(default_factory=list)
    warning: str | None = None


class KillChainEnforcer:
    """計算推薦技術跳過必要 Kill Chain 階段時的信心懲罰。"""

    async def evaluate_skip(
        self,
        db: aiosqlite.Connection,
        operation_id: str,
        tactic_id: str | None,
        target_id: str | None,
    ) -> KillChainPenalty:
        """
        評估推薦的 tactic_id 是否跳過了前置必要階段。

        步驟：
        1. 查詢該 operation + target 已成功執行的 tactic_id 集合
        2. 判斷推薦 tactic 前方有哪些 required 階段未完成
        3. 計算懲罰值（每個跳過的 required 階段扣 0.05，上限 0.25）
        """
        if tactic_id is None or tactic_id not in _TACTIC_TO_STAGE:
            return KillChainPenalty()

        current_stage = _TACTIC_TO_STAGE[tactic_id]

        # 查詢已完成的 tactic 集合
        completed_tactics = await self._get_completed_tactics(
            db, operation_id, target_id
        )

        # 檢查前置必要階段
        skipped: list[str] = []
        for stage, tid, name, required in _KILL_CHAIN_STAGES:
            if stage >= current_stage:
                break  # 只檢查前置階段
            if not required:
                continue  # 可跳過的階段不計入懲罰
            if tid not in completed_tactics:
                skipped.append(f"{tid} ({name})")

        penalty = min(len(skipped) * _PENALTY_PER_SKIP, _MAX_PENALTY)

        warning = None
        if skipped:
            tactic_name = _TACTIC_TO_NAME.get(tactic_id, "?")
            warning = (
                f"Kill Chain skip warning: recommending {tactic_id} ({tactic_name}) "
                f"but required stages not completed: {', '.join(skipped)}. "
                f"Confidence penalty: -{penalty:.2f}"
            )
            logger.warning(warning)

        return KillChainPenalty(
            penalty=penalty, skipped_stages=skipped, warning=warning
        )

    async def _get_completed_tactics(
        self,
        db: aiosqlite.Connection,
        operation_id: str,
        target_id: str | None,
    ) -> set[str]:
        """查詢該 operation + target 已成功執行的 tactic_id 集合。

        透過 JOIN technique_executions 和 attack_graph_nodes 取得
        已成功執行之技術所對應的 tactic_id。
        """
        if not target_id:
            # 無 target 時查詢 operation 層級
            cursor = await db.execute(
                "SELECT DISTINCT agn.tactic_id "
                "FROM technique_executions te "
                "JOIN attack_graph_nodes agn "
                "  ON te.technique_id = agn.technique_id "
                "  AND te.operation_id = agn.operation_id "
                "WHERE te.operation_id = ? AND te.status = 'success'",
                (operation_id,),
            )
        else:
            cursor = await db.execute(
                "SELECT DISTINCT agn.tactic_id "
                "FROM technique_executions te "
                "JOIN attack_graph_nodes agn "
                "  ON te.technique_id = agn.technique_id "
                "  AND te.operation_id = agn.operation_id "
                "  AND te.target_id = agn.target_id "
                "WHERE te.operation_id = ? AND te.target_id = ? "
                "AND te.status = 'success'",
                (operation_id, target_id),
            )
        rows = await cursor.fetchall()
        return {
            (r["tactic_id"] if isinstance(r, dict) else r[0]) for r in rows
        }
```

---

## ✅ 驗收標準（Done When）

### Phase 1 — 複合信心評分

- [ ] `DecisionEngine.__init__()` 初始化 `KillChainEnforcer` 實例
- [ ] `_compute_composite_confidence()` 正確計算四來源加權分數
- [ ] 歷史成功率查詢 `technique_executions` 結果準確（含無資料回退 0.5）
- [ ] 攻擊圖節點信心查詢 `attack_graph_nodes` 結果準確（含無節點回退 0.5）
- [ ] 目標狀態分數正確反映 `is_compromised`/`privilege_level`/`access_status`/EDR 狀態
- [ ] EDR 偵測從 `facts` 表查詢 `host.edr` / `host.av` trait
- [ ] `evaluate()` 回傳值包含 `composite_confidence` 和 `confidence_breakdown`
- [ ] `confidence < 0.5` 閘控使用 `composite` 而非原始 LLM 信心
- [ ] LLM 回傳超出 0.0–1.0 範圍時正確 clamp
- [ ] `_resolve_tactic_id()` 優先從 `attack_graph_nodes` 查詢，回退至 `_RULE_BY_TECHNIQUE`

### Phase 2 — Kill Chain 強制器

- [ ] `backend/app/services/kill_chain_enforcer.py` 模組建立
- [ ] `KillChainEnforcer` 類別包含 `evaluate_skip()` 和 `_get_completed_tactics()` 方法
- [ ] `KillChainPenalty` dataclass 包含 `penalty`、`skipped_stages`、`warning` 欄位
- [ ] 跳過 1 個必要階段 → penalty = 0.05
- [ ] 跳過 5 個必要階段 → penalty = 0.25（上限）
- [ ] 跳過 6 個以上必要階段 → penalty 仍為 0.25
- [ ] 跳過可跳過階段（TA0042、TA0003、TA0005、TA0011） → penalty = 0.0
- [ ] 推薦 TA0043（stage 0） → penalty = 0.0（無前置階段）
- [ ] `tactic_id` 不在映射表中 → penalty = 0.0
- [ ] `KillChainPenalty.warning` 包含人類可讀的跳階資訊
- [ ] 懲罰正確整合至 `_compute_composite_confidence()` 公式

### Phase 3 — 引擎回退鏈

- [ ] 現有 `execute()` 重命名為 `_execute_single()`，內部邏輯完全不變
- [ ] 新 `execute()` 在主引擎成功時直接回傳（不觸發回退）
- [ ] 主引擎非終端性失敗 → 依序嘗試 `_FALLBACK_CHAIN` 中的引擎
- [ ] 終端性錯誤（scope violation / platform mismatch / blocked by RoE） → 不觸發回退
- [ ] 每次回退嘗試透過 WebSocket 廣播 `execution.fallback` 事件
- [ ] `execution.fallback` 事件包含 `failed_engine`、`fallback_engine`、`attempt`、`max_attempts`
- [ ] 回傳 dict 包含 `fallback_history` 和 `final_engine` 欄位
- [ ] 所有回退引擎都失敗 → 回傳最後一個引擎的結果 + 完整 `fallback_history`
- [ ] `engine` 值不在 `_FALLBACK_CHAIN` 中 → 不觸發回退，行為與現有邏輯一致
- [ ] `_is_terminal_error()` 為模組級函式（與既有 `_is_auth_failure()` 風格一致）

### 整合驗證

- [ ] 複合信心 + Kill Chain 懲罰端對端：LLM 高信心但跳階 → 信心下降觸發人工確認
- [ ] 回退鏈端對端：mcp_ssh 失敗 → metasploit 成功 → 最終結果為成功
- [ ] `make test` 全數通過（既有測試不受影響）

---

## 🧪 測試條件（Test Conditions）

### 複合信心單元測試 (`backend/tests/test_composite_confidence.py`)

```python
# TC-A1: 四來源正常計算
# llm=0.80, historical=0.60, graph=0.70, target_state=0.65, kc_penalty=0.0
# expected = 0.30*0.80 + 0.30*0.60 + 0.25*0.70 + 0.15*0.65
#          = 0.24 + 0.18 + 0.175 + 0.0975 = 0.6925
async def test_composite_normal_case():
    ...

# TC-A2: 無歷史資料 → historical 回退為 0.5
async def test_composite_no_history():
    # technique_executions 表中無該 technique_id 的記錄
    # historical = 0.5
    ...

# TC-A3: EDR 偵測 → target_state 扣 0.2
# base=0.5, is_compromised(+0.2), has_edr(-0.2) → target_state=0.5
async def test_composite_edr_penalty():
    ...

# TC-A4: LLM 信心超出範圍 → clamp
async def test_composite_clamp_raw_confidence():
    # raw_confidence=1.5 → clamped to 1.0
    # raw_confidence=-0.3 → clamped to 0.0
    ...

# TC-A5: target_id 為 None → 使用預設值
async def test_composite_no_target():
    # historical=0.5, graph=0.5, target_state=0.5
    ...

# TC-A6: 歷史成功率為 0% → 顯著拉低信心
async def test_composite_zero_success_rate():
    # 5 次執行全部失敗 → historical=0.0
    ...

# TC-A7: has_root + is_compromised → target_state 最高
async def test_composite_high_target_state():
    # score = 0.5 + 0.2 + 0.15 = 0.85
    ...

# TC-A8: access_lost + has_edr → target_state 最低
async def test_composite_low_target_state():
    # score = max(0.0, 0.5 - 0.1 - 0.2) = 0.2
    ...
```

### Kill Chain 強制器單元測試 (`backend/tests/test_kill_chain_enforcer.py`)

```python
# TC-C1: 無跳階 → penalty = 0.0
async def test_no_skip():
    # 推薦 TA0002(Execution), 已完成 TA0043+TA0001
    # 所有前置必要階段已完成 → penalty = 0.0
    ...

# TC-C2: 跳過 1 個必要階段 → penalty = 0.05
async def test_skip_one_required():
    # 推薦 TA0002(Execution), 已完成 TA0043, 跳過 TA0001(Initial Access)
    # skipped = ["TA0001 (Initial Access)"], penalty = 0.05
    ...

# TC-C3: 跳過可跳過階段 → penalty = 0.0
async def test_skip_optional_stage():
    # 推薦 TA0004(PrivEsc), 已完成 TA0043+TA0001+TA0002, 跳過 TA0003(Persistence)
    # TA0003 is required=False → penalty = 0.0
    ...

# TC-C4: 上限測試 → penalty = 0.25
async def test_max_penalty():
    # 推薦 TA0040(Impact), 無任何完成記錄
    # 跳過 10 個必要階段 → penalty = min(10 * 0.05, 0.25) = 0.25
    ...

# TC-C5: tactic_id 不在映射表 → penalty = 0.0
async def test_unknown_tactic():
    # tactic_id = "TA9999" → KillChainPenalty(penalty=0.0)
    ...

# TC-C6: target_id 為 None → 查詢 operation 層級
async def test_no_target_id():
    # 使用不帶 target_id 的 SQL 查詢
    ...

# TC-C7: tactic_id 為 None → penalty = 0.0
async def test_none_tactic():
    ...

# TC-C8: 推薦 stage 0 (TA0043) → penalty = 0.0
async def test_first_stage_no_penalty():
    # 無前置階段可跳過
    ...
```

### 引擎回退鏈單元測試 (`backend/tests/test_engine_fallback.py`)

```python
# TC-B1: 主引擎成功 → 不觸發回退
async def test_primary_success_no_fallback():
    # mock _execute_single 回傳 status="success"
    # assert result["fallback_history"] == []
    # assert result["final_engine"] == "mcp_ssh"
    ...

# TC-B2: 主引擎失敗 → 回退成功
async def test_fallback_success():
    # mcp_ssh 回傳 status="failed", error="connection timed out"
    # metasploit 回傳 status="success"
    # assert result["status"] == "success"
    # assert result["final_engine"] == "metasploit"
    # assert len(result["fallback_history"]) == 1
    # assert result["fallback_history"][0]["engine"] == "mcp_ssh"
    ...

# TC-B3: 終端性錯誤 → 不回退
async def test_terminal_error_no_fallback():
    # mcp_ssh 回傳 error="scope violation — target outside authorized range"
    # assert result["status"] == "failed"
    # assert result["fallback_history"] == []
    ...

# TC-B4: 所有引擎失敗
async def test_all_engines_fail():
    # mcp_ssh → metasploit → c2 全部回傳 status="failed"
    # assert result["status"] == "failed"
    # assert len(result["fallback_history"]) == 2  # mcp_ssh + metasploit 失敗記錄
    ...

# TC-B5: 回退引擎也回傳終端性錯誤 → 停止回退鏈
async def test_fallback_terminal_error_stops_chain():
    # mcp_ssh 失敗(non-terminal) → metasploit 回傳 "platform mismatch" → 停止
    # c2 不應被嘗試
    # assert len(result["fallback_history"]) == 1
    ...

# TC-B6: WebSocket 事件驗證
async def test_fallback_websocket_event():
    # mock ws_manager.broadcast
    # 驗證 broadcast 被呼叫，事件類型為 "execution.fallback"
    # 驗證 payload 包含 failed_engine, fallback_engine, attempt, max_attempts
    ...

# TC-B7: engine 不在 _FALLBACK_CHAIN → 不回退
async def test_unknown_engine_no_fallback():
    # engine="mcp" → _FALLBACK_CHAIN.get("mcp", []) == []
    # 回退鏈為空，直接回傳主引擎結果
    ...

# TC-B8: _is_terminal_error 函式測試
def test_is_terminal_error():
    assert _is_terminal_error("scope violation — target outside range") is True
    assert _is_terminal_error("Platform Mismatch: Windows required") is True
    assert _is_terminal_error("blocked by rules of engagement") is True
    assert _is_terminal_error("connection timed out") is False
    assert _is_terminal_error("authentication failed") is False
    assert _is_terminal_error(None) is False
    assert _is_terminal_error("") is False
    ...
```

---

## 🚫 禁止事項（Out of Scope）

- 不要修改 DB schema（不新增表或欄位）
- 不要修改 `attack_graph_engine.py` 中的節點信心計算邏輯
- 不要修改 WebSocket 連線管理邏輯（`ws_manager.py`）
- 不要引入新的外部依賴
- 不要修改 Orient 或 Observe 階段的任何邏輯
- 不要實作動態權重調校（ADR-037 後續追蹤項目，不在本 SPEC 範圍）
- 不要修改前端（`execution.fallback` 事件的前端處理為獨立 SPEC）
- 不要在回退鏈中加入重試（retry）邏輯 — 回退是切換引擎，不是重試同一引擎

---

## 📎 參考資料（References）

- 相關 ADR：ADR-037（複合信心與引擎回退鏈）、ADR-004（semi-auto with manual override）、ADR-006（execution engine abstraction）、ADR-003（OODA loop）、ADR-028（attack graph）
- 相關 SPEC：SPEC-037（access recovery — `_handle_access_lost`、`_is_auth_failure`）、SPEC-031（attack graph engine）
- 關鍵檔案：
  - `backend/app/services/decision_engine.py` — 現有信心評分與閘控邏輯（第 61 行 `confidence = recommendation.get("confidence", 0.0)`）
  - `backend/app/services/engine_router.py` — 現有執行路由（第 75–167 行 `execute()`），無回退機制
  - `backend/app/services/attack_graph_engine.py` — `_TACTIC_ORDER`（第 136 行）、`_RULE_BY_TECHNIQUE`（第 133 行）、節點信心計算（第 572–576 行）
  - `backend/app/services/kill_chain_enforcer.py` — 本 SPEC 新增模組
  - `backend/app/ws_manager.py` — `WebSocketManager.broadcast()` 介面
  - `backend/app/database.py` — `technique_executions` 表 schema（第 111 行）、`attack_graph_nodes` 表
