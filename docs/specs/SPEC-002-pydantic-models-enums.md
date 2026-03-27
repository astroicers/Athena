# SPEC-002：Pydantic Models + Enums

> 實作 13 個 Enum 與 12 個 Pydantic Model，建立後端型別安全基礎。

| 欄位 | 內容 |
|------|------|
| **規格 ID** | SPEC-002 |
| **狀態** | Accepted |
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

## 🔗 副作用與連動（Side Effects）

| 副作用 | 觸發條件 | 影響的系統/模組 | 驗證方式 |
|--------|---------|----------------|----------|
| Enum 值變更影響 DB seed 與 API 回應 | 任一 Enum 成員名稱或值修改時 | SPEC-003（seed 資料 INSERT 值）、SPEC-004（API 回應 JSON 值）、SPEC-005（前端 TypeScript enum 對映） | `python -c "from app.models.enums import *"` 無錯誤；grep 全專案確認 enum 值一致 |
| Model 欄位變更影響 SQL schema 與 API schema | 任一 Model 新增/移除/重命名欄位時 | SPEC-003（CREATE TABLE 欄位）、SPEC-004（Request/Response schema）、SPEC-005（TypeScript interface） | 對照 `data-architecture.md` Section 4 逐欄位驗證 |
| `__init__.py` 匯出清單影響全後端 import | 新增或移除 Model 檔案時 | 所有 `from app.models import X` 的模組 | `python -c "from app.models import *; print('OK')"` |

### 🔄 Rollback Plan

| 項目 | 說明 |
|------|------|
| **回滾步驟** | 1. `git revert <commit>` 還原 models 變更 2. 確認 SPEC-003/004 未依賴新 Model（若已依賴需一併還原） |
| **資料影響** | 無直接資料影響——Model 為純 Python 定義，不操作 DB |
| **回滾驗證** | `python -c "from app.models import *"` 成功；SPEC-003 seed 可正常執行 |
| **回滾已測試** | ☑ 否（Model 為型別定義，回滾風險低） |

## 🧪 測試矩陣（Test Matrix）

| # | 類型 | 輸入條件 | 預期結果 | 對應場景 |
|---|------|---------|---------|---------|
| P1 | ✅ 正向 | `from app.models.enums import OODAPhase` | 匯入成功，`len(OODAPhase) == 4` | S1 |
| P2 | ✅ 正向 | 建立 `Operation(id='test', code='OP-001', ...)` 含所有必填欄位 | Pydantic 驗證通過，`model_dump()` 回傳正確 dict | S1 |
| P3 | ✅ 正向 | `PentestGPTRecommendation` 含 `options: list[TacticalOption]` | 巢狀 Model 驗證通過，TacticalOption 有 7 個欄位 | S1 |
| N1 | ❌ 負向 | `Operation(id='test')` 缺少必填欄位 | 拋出 `ValidationError`，列出缺少的欄位名稱 | S2 |
| N2 | ❌ 負向 | `OODAPhase("invalid_value")` 傳入不存在的 enum 值 | 拋出 `ValueError` | S2 |
| B1 | 🔶 邊界 | `Technique(platforms=[])` 空 list | 驗證通過，platforms 為空 list | S3 |
| B2 | 🔶 邊界 | `PentestGPTRecommendation(accepted=None)` 三態 | 驗證通過，`accepted` 為 None（未決定） | S3 |
| B3 | 🔶 邊界 | `Technique(description=None)` nullable 欄位 | 驗證通過，`description` 為 None | S3 |

## 🎭 驗收場景（Acceptance Scenarios）

```gherkin
Feature: SPEC-002 Pydantic Models 與 Enums
  作為 Athena 平台開發者
  我想要 13 個 Enum 與 12 個 Pydantic Model 的型別安全定義
  以便 後端 API、資料庫層及前端型別對映有單一真相來源

  Background:
    Given backend/app/models/ 目錄已建立（SPEC-001）

  # --- 正向場景 ---

  Scenario: S1 - 所有 Enum 與 Model 可成功匯入
    Given 13 個 Enum 定義於 enums.py
    And 12 個 Model 分別定義於各自檔案
    When 執行 `from app.models import *`
    Then 匯入無錯誤
    And OODAPhase 有 4 個成員（observe, orient, decide, act）
    And C5ISRDomain 有 6 個成員
    And Operation Model 可用有效參數實例化

  Scenario: S1b - TacticalOption 為 PentestGPTRecommendation 的巢狀子模型
    Given PentestGPTRecommendation Model 已定義
    When 建立含 options 陣列的 PentestGPTRecommendation 實例
    Then TacticalOption 有 7 個欄位
    And options 為 list[TacticalOption] 型別

  # --- 負向場景 ---

  Scenario: S2 - 缺少必填欄位時拋出 ValidationError
    Given Operation Model 需要 id、code、name、codename 等必填欄位
    When 僅提供 id 建立 Operation 實例
    Then 拋出 Pydantic ValidationError
    And 錯誤訊息包含缺少的欄位名稱

  # --- 邊界場景 ---

  Scenario: S3 - Nullable 與空值欄位正確處理
    Given Technique Model 的 description 為 Optional[str]
    And PentestGPTRecommendation 的 accepted 為 bool | None
    When 傳入 None 值
    Then 驗證通過，欄位值為 None
```

## 🔗 追溯性（Traceability）

| 實作檔案 | 測試檔案 | 最後驗證日期 |
|----------|----------|-------------|
| `backend/app/models/enums.py` | `backend/tests/test_spec_004_api.py`（間接驗證 enum 值） | 2026-03-26 |
| `backend/app/models/operation.py` | `backend/tests/test_operations_router.py` | 2026-03-26 |
| `backend/app/models/target.py` | `backend/tests/test_targets_router.py` | 2026-03-26 |
| `backend/app/models/agent.py` | `backend/tests/test_agents_router.py` | 2026-03-26 |
| `backend/app/models/technique.py` | `backend/tests/test_techniques_router.py` | 2026-03-26 |
| `backend/app/models/technique_execution.py` | `backend/tests/test_spec_004_api.py` | 2026-03-26 |
| `backend/app/models/fact.py` | `backend/tests/test_facts_router.py` | 2026-03-26 |
| `backend/app/models/ooda.py` | `backend/tests/test_ooda_router.py` | 2026-03-26 |
| `backend/app/models/recommendation.py` | `backend/tests/test_recommendations_router.py` | 2026-03-26 |
| `backend/app/models/mission.py` | `backend/tests/test_missions_router.py` | 2026-03-26 |
| `backend/app/models/c5isr.py` | `backend/tests/test_c5isr_router.py` | 2026-03-26 |
| `backend/app/models/log_entry.py` | `backend/tests/test_logs_router.py` | 2026-03-26 |
| `backend/app/models/user.py` | `backend/tests/test_admin_router.py`（間接） | 2026-03-26 |
| `backend/app/models/__init__.py` | （驗收標準中的 import 驗證） | 2026-03-26 |

## 📊 可觀測性（Observability）

N/A（純型別定義模組，無執行時行為。Enum/Model 驗證錯誤由 Pydantic 在 API 層自動捕獲並回傳 422）

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

