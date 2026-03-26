# SPEC-008：執行引擎客戶端

> 實作 Caldera + Shannon 統一 Client 介面，含 mock 模式與 fallback 邏輯。

| 欄位 | 內容 |
|------|------|
| **規格 ID** | SPEC-008 |
| **關聯 ADR** | ADR-006（執行引擎抽象層與授權隔離） |
| **估算複雜度** | 中 |
| **建議模型** | Sonnet |
| **HITL 等級** | standard |

---

## 🎯 目標（Goal）

> 實作 Caldera 和 Shannon 的統一 HTTP 客戶端介面，封裝外部執行引擎的 REST API 呼叫，使 OODA Act 階段可透過統一介面執行 MITRE ATT&CK 技術，並在引擎不可用時提供 mock/fallback 機制。

---

## 📥 輸入規格（Inputs）

| 參數名稱 | 型別 | 來源 | 限制條件 |
|----------|------|------|----------|
| 統一介面定義 | ADR | ADR-006 決策 | `execute()`, `get_status()`, `list_abilities()` |
| 授權隔離 | ADR | ADR-006 | Shannon 僅 HTTP API，不 import 任何 AGPL 程式碼 |
| Caldera REST API v2 | 外部 | MITRE Caldera 文件 | `/api/v2/operations`, `/api/v2/abilities` |
| Shannon API | 外部 | Shannon 文件 | `/execute`, `/status` |
| 環境變數 | 檔案 | `.env.example` | `CALDERA_URL`, `CALDERA_API_KEY`, `SHANNON_URL` |

---

## 📤 輸出規格（Expected Output）

**成功情境：**

### 1. 基礎介面（`clients/__init__.py` 或各 client 中定義）

```python
from dataclasses import dataclass

@dataclass
class ExecutionResult:
    success: bool
    execution_id: str
    output: str | None
    facts: list[dict]         # 萃取的情報
    error: str | None

class BaseEngineClient:
    """統一引擎客戶端介面"""

    async def execute(
        self, ability_id: str, target: str, params: dict | None = None
    ) -> ExecutionResult:
        """執行一個 MITRE 技術 ability"""
        raise NotImplementedError

    async def get_status(self, execution_id: str) -> str:
        """查詢執行狀態"""
        raise NotImplementedError

    async def list_abilities(self) -> list[dict]:
        """列出可用 abilities"""
        raise NotImplementedError

    async def is_available(self) -> bool:
        """健康檢查"""
        raise NotImplementedError
```

### 2. `clients/caldera_client.py`

```python
class CalderaClient(BaseEngineClient):
    """
    MITRE Caldera REST API v2 封裝。
    授權：Apache 2.0（安全）。
    """

    def __init__(self, base_url: str, api_key: str = ""):
        # httpx.AsyncClient 初始化
        # base_url: settings.CALDERA_URL (default: http://localhost:8888)

    async def execute(self, ability_id, target, params=None) -> ExecutionResult:
        """
        Caldera API 呼叫流程：
        1. POST /api/v2/operations — 建立 operation
        2. 加入 ability 至 operation
        3. 等待完成（polling get_status）
        4. GET /api/v2/operations/{id}/report — 取得結果
        5. 標準化為 ExecutionResult
        """

    async def get_status(self, execution_id) -> str:
        """GET /api/v2/operations/{id} → status"""

    async def list_abilities(self) -> list[dict]:
        """GET /api/v2/abilities → 過濾可用 abilities"""

    async def is_available(self) -> bool:
        """GET /api/v2/health → True/False"""

    async def sync_agents(self, operation_id: str) -> list[dict]:
        """GET /api/v2/agents → 同步 Agent 狀態至 Athena DB"""
```

### 3. `clients/shannon_client.py`

```python
class ShannonClient(BaseEngineClient):
    """
    Shannon AI 引擎 REST API 封裝。
    授權：AGPL-3.0 — 僅透過 HTTP API 呼叫，不 import 任何程式碼。
    """

    def __init__(self, base_url: str):
        # base_url: settings.SHANNON_URL
        # 若 SHANNON_URL 為空，self.enabled = False

    async def execute(self, ability_id, target, params=None) -> ExecutionResult:
        """
        Shannon API 呼叫：
        1. POST /execute — 提交 task
        2. Polling /status/{task_id} — 等待完成
        3. 標準化為 ExecutionResult
        若 not self.enabled → raise EngineNotAvailableError
        """

    async def get_status(self, execution_id) -> str:
        """GET /status/{id}"""

    async def list_abilities(self) -> list[dict]:
        """Shannon 不使用固定 abilities，回傳空列表"""

    async def is_available(self) -> bool:
        """self.enabled and 健康檢查通過"""
```

### 4. Mock 模式

當 `CALDERA_URL` 不可達或明確啟用 mock 時：

```python
class MockCalderaClient(BaseEngineClient):
    """
    Mock 模式：不呼叫真實 Caldera，回傳預錄結果。
    用於開發/測試/Demo 無 Caldera 時。
    """

    async def execute(self, ability_id, target, params=None) -> ExecutionResult:
        """
        依 ability_id 回傳預錄結果：
        - T1595.001 (Active Scanning) → success, facts: [network.host.ip]
        - T1003.001 (LSASS Memory) → success, facts: [credential.hash]
        - T1021.002 (SMB/Admin$) → success, facts: [host.session]
        - 其他 → success, facts: []
        """

    async def is_available(self) -> bool:
        return True  # Mock 永遠可用
```

**失敗情境：**

| 錯誤類型 | 處理方式 |
|----------|----------|
| Caldera 不可連線 | `is_available()` → False；fallback 至 MockCalderaClient |
| Shannon 未配置 | `ShannonClient.enabled = False`；`engine_router` 不路由至 Shannon |
| API 回應超時 | httpx timeout（30s）→ ExecutionResult(success=False, error="timeout") |
| API 回應格式錯誤 | 記錄 error + 回傳 ExecutionResult(success=False, error="parse error") |

---

## ⚠️ 邊界條件（Edge Cases）

- `SHANNON_URL` 為空字串時 `ShannonClient` 完全停用（不嘗試連線）
- `CalderaClient` 的 `sync_agents()` 需將 Caldera Agent 格式轉換為 Athena 的 `Agent` 模型
- Caldera API v2 需要 `api_key` header（若設定了 `CALDERA_API_KEY`）
- Mock client 需模擬 2-5 秒的執行延遲（`asyncio.sleep`）以呈現真實感
- `ExecutionResult.facts` 使用 dict 而非 Pydantic Model——由 `fact_collector` 負責標準化
- Shannon `execute()` 不使用固定 `ability_id`——傳入自然語言描述
- 所有 HTTP 呼叫使用 `httpx.AsyncClient`（不用 `requests`）

---

## ✅ 驗收標準（Done When）

- [x] `make test-filter FILTER=spec_008` 全數通過
- [x] `CalderaClient` 可呼叫 `execute()`、`get_status()`、`list_abilities()`、`is_available()`
- [x] `ShannonClient` 在 `SHANNON_URL=""` 時 `is_available()` 回傳 `False`
- [x] `MockCalderaClient` 回傳預錄的 T1595.001、T1003.001 結果
- [x] `CalderaClient.sync_agents()` 回傳標準化 Agent 列表
- [x] 所有 client 使用 `httpx.AsyncClient`（非同步）
- [x] 無任何 `import shannon` 或 `from shannon import` 語句（授權隔離）
- [x] mock 模式下完整 OODA 循環可執行（無需真實 Caldera）

---

## 🚫 禁止事項（Out of Scope）

- 不要 `import` Shannon 的任何 Python 套件——僅 HTTP API 呼叫（ADR-006）
- 不要使用 `requests` 庫——使用 `httpx`（非同步）
- 不要實作 OODA 引擎邏輯——SPEC-007 範圍
- 不要建立 Caldera/Shannon 的 Docker 配置——SPEC-010 範圍
- 不要實作完整的 Caldera operation 生命週期管理——POC 僅需基本 execute/status
- 不要硬編碼 Caldera API URL——從 `settings` 讀取

---

## 📎 參考資料（References）

- ADR-006：[執行引擎抽象層](../adr/ADR-006-execution-engine-abstraction-and-license-isolation.md)
- ADR-010：[Docker Compose 部署拓樸](../adr/ADR-010-docker-compose-deployment.md)（外部引擎配置）
- Caldera API 文件：https://caldera.readthedocs.io/en/latest/Server-Configuration.html
- SPEC-007：OODA Loop Engine（被依賴——engine_router 呼叫 client）

<!-- tech-debt: scenario-pending — v3.2 upgrade: needs test matrix + Gherkin scenarios -->
<!-- tech-debt: observability-pending — v3.3 upgrade: needs observability section -->
