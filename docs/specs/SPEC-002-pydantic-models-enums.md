# SPEC-002：Pydantic Models + Enums

> 實作 13 個 Enum 與 12 個 Pydantic Model，建立後端型別安全基礎。

| 欄位 | 內容 |
|------|------|
| **規格 ID** | SPEC-002 |
| **關聯 ADR** | ADR-008（SQLite Schema 設計） |
| **估算複雜度** | 中 |
| **建議模型** | Sonnet |
| **HITL 等級** | minimal |

---

## 🎯 目標（Goal）

> 根據 `data-architecture.md` Section 2（Enums）與 Section 4（Models）的完整定義，實作 13 個共用列舉（`enums.py`）與 12 個 Pydantic Model 檔案，為後端 API、資料庫層及前端型別對映提供單一真相來源。

---

## 📥 輸入規格（Inputs）

| 參數名稱 | 型別 | 來源 | 限制條件 |
|----------|------|------|----------|
| 13 個 Enum 定義 | 文件 | `data-architecture.md` Section 2 | 完全對映，不可增減 |
| 12 個 Model 定義 | 文件 | `data-architecture.md` Section 4 | 欄位名稱、型別、預設值嚴格對齊 |
| 主鍵策略 | ADR | ADR-008 決策 | UUID TEXT 主鍵 |
| TacticalOption 結構 | 文件 | `data-architecture.md` Section 4「PentestGPTRecommendation」 | 包含 7 個欄位 |

---

## 📤 輸出規格（Expected Output）

**成功情境：**

### 1. `backend/app/models/enums.py` — 13 個 Enum

```python
from enum import Enum

class OODAPhase(str, Enum):
    OBSERVE = "observe"
    ORIENT = "orient"
    DECIDE = "decide"
    ACT = "act"

class OperationStatus(str, Enum):
    PLANNING = "planning"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ABORTED = "aborted"

class TechniqueStatus(str, Enum):
    UNTESTED = "untested"
    QUEUED = "queued"
    RUNNING = "running"
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"

class MissionStepStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

class AgentStatus(str, Enum):
    ALIVE = "alive"
    DEAD = "dead"
    PENDING = "pending"
    UNTRUSTED = "untrusted"

class ExecutionEngine(str, Enum):
    CALDERA = "caldera"
    SHANNON = "shannon"

class C5ISRDomain(str, Enum):
    COMMAND = "command"
    CONTROL = "control"
    COMMS = "comms"
    COMPUTERS = "computers"
    CYBER = "cyber"
    ISR = "isr"

class C5ISRDomainStatus(str, Enum):
    OPERATIONAL = "operational"
    ACTIVE = "active"
    NOMINAL = "nominal"
    ENGAGED = "engaged"
    SCANNING = "scanning"
    DEGRADED = "degraded"
    OFFLINE = "offline"
    CRITICAL = "critical"

class FactCategory(str, Enum):
    CREDENTIAL = "credential"
    HOST = "host"
    NETWORK = "network"
    SERVICE = "service"
    VULNERABILITY = "vulnerability"
    FILE = "file"

class LogSeverity(str, Enum):
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class KillChainStage(str, Enum):
    RECON = "recon"
    WEAPONIZE = "weaponize"
    DELIVER = "deliver"
    EXPLOIT = "exploit"
    INSTALL = "install"
    C2 = "c2"
    ACTION = "action"

class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class AutomationMode(str, Enum):
    MANUAL = "manual"
    SEMI_AUTO = "semi_auto"
```

### 2. 12 個 Model 檔案

每個檔案位於 `backend/app/models/`，對映 `data-architecture.md` Section 4 的完整結構：

| 檔案 | 主 Model | 附屬 Model |
|------|----------|-----------|
| `operation.py` | `Operation` | — |
| `target.py` | `Target` | — |
| `agent.py` | `Agent` | — |
| `technique.py` | `Technique` | — |
| `technique_execution.py` | `TechniqueExecution` | — |
| `fact.py` | `Fact` | — |
| `ooda.py` | `OODAIteration` | — |
| `recommendation.py` | `PentestGPTRecommendation` | `TacticalOption` |
| `mission.py` | `MissionStep` | — |
| `c5isr.py` | `C5ISRStatus` | — |
| `log_entry.py` | `LogEntry` | — |
| `user.py` | `User` | — |

每個 Model 必須：
- 繼承 `pydantic.BaseModel`
- 使用 `data-architecture.md` 定義的完整欄位（名稱、型別、預設值）
- 引用 `enums.py` 中的列舉型別
- `id` 欄位使用 `str` 型別（UUID TEXT 策略，ADR-008）
- `datetime` 欄位使用 `datetime` 型別（而非 `str`）

### 3. `backend/app/models/__init__.py`

統一匯出所有 Model 與 Enum：

```python
from .enums import *
from .operation import Operation
from .target import Target
from .agent import Agent
from .technique import Technique
from .technique_execution import TechniqueExecution
from .fact import Fact
from .ooda import OODAIteration
from .recommendation import PentestGPTRecommendation, TacticalOption
from .mission import MissionStep
from .c5isr import C5ISRStatus
from .log_entry import LogEntry
from .user import User
```

**失敗情境：**

| 錯誤類型 | 處理方式 |
|----------|----------|
| Enum 值拼寫錯誤 | 對照 data-architecture.md 逐一驗證 |
| Model 欄位遺漏 | 逐欄位對照 data-architecture.md Section 4 |

---

## ⚠️ 邊界條件（Edge Cases）

- `TacticalOption` 不是獨立資料表——它是 `PentestGPTRecommendation.options` 的 JSON 結構化子模型
- `Technique.description` 型別為 `str | None`——用於 UI TechniqueCard 顯示，SQLite schema 中已有 `description TEXT` 欄位
- `Technique.platforms` 型別為 `list[str]`，在 SQLite 中存為 JSON TEXT（`'["windows"]'`）
- `PentestGPTRecommendation.options` 型別為 `list[TacticalOption]`，在 SQLite 中存為 JSON TEXT
- `PentestGPTRecommendation.accepted` 型別為 `bool | None`（三態：未決定 / 接受 / 拒絕）
- `User` 模型為最小化 stub（ADR-011）：僅 `id`、`callsign`、`role`、`created_at`
- 所有 `datetime` 欄位使用 `from datetime import datetime`

---

## ✅ 驗收標準（Done When）

- [x] `cd backend && python -c "from app.models import *; print('OK')"` — 成功
- [x] `cd backend && python -c "from app.models.enums import OODAPhase, C5ISRDomain; print(len(OODAPhase), len(C5ISRDomain))"` — 輸出 `4 6`
- [x] `cd backend && python -c "from app.models import Operation; o = Operation(id='test', code='OP-001', name='Test', codename='TEST', strategic_intent='test', status='active', current_ooda_phase='observe', created_at='2026-01-01T00:00:00', updated_at='2026-01-01T00:00:00'); print(o.model_dump())"` — 成功
- [x] `cd backend && python -c "from app.models import PentestGPTRecommendation, TacticalOption; print('TacticalOption fields:', list(TacticalOption.model_fields.keys()))"` — 印出 7 個欄位
- [x] 13 個 Enum class 全部繼承 `(str, Enum)`
- [x] 12 個 Model 檔案全部存在且可獨立 import

---

## 🚫 禁止事項（Out of Scope）

- 不要實作 SQLAlchemy ORM Model（本專案使用原生 SQL + Pydantic）
- 不要新增 `data-architecture.md` 未定義的欄位
- 不要移除 `data-architecture.md` 已定義的欄位
- 不要建立 API schema（Request/Response Model）——那是 SPEC-004 的範圍
- 不要引入 `uuid` 自動生成邏輯——ID 生成在 seed 或 router 中處理

---

## 📎 參考資料（References）

- ADR-008：[SQLite Schema 設計](../adr/ADR-008-sqlite-data-schema-design.md)
- 資料架構：[data-architecture.md](../architecture/data-architecture.md) Section 2（Enums）+ Section 4（Models）
- ADR-011：[POC 不實作身份驗證](../adr/ADR-011-no-auth-for-poc.md)（User stub）

<!-- tech-debt: scenario-pending — v3.2 upgrade: needs test matrix + Gherkin scenarios -->
<!-- tech-debt: observability-pending — v3.3 upgrade: needs observability section -->
