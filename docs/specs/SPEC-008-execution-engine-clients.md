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

## 🔗 副作用與連動（Side Effects）

| 副作用 | 觸發條件 | 影響的系統/模組 | 驗證方式 |
|--------|---------|----------------|----------|
| Mock 模式自動切換 | Caldera URL 不可達 | `engine_router`（SPEC-007）fallback 至 `MockCalderaClient` | `GET /api/health` → `services.caldera` 顯示 "mock" |
| Agent 狀態同步 | `CalderaClient.sync_agents()` 呼叫 | `Agent` 表（DB）、前端 Battle Monitor 的 AgentBeacon | `GET /api/agents` 確認 Agent 列表與 Caldera 同步 |
| ExecutionResult 傳播 | `execute()` 完成後 | `engine_router` → `fact_collector`（SPEC-007）萃取情報 | 確認 `ExecutionResult.facts` 被正確傳遞至 `fact_collector.collect()` |

### 🔄 Rollback Plan

| 項目 | 說明 |
|------|------|
| **回滾步驟** | `git revert` 移除 `backend/app/clients/` 目錄（`c2_client.py`、`mock_c2_client.py`、`mcp_engine_client.py`、`metasploit_client.py`、`__init__.py`） |
| **資料影響** | Client 為無狀態 HTTP 封裝，無 DB schema 變更；回滾後 `engine_router` 需同步移除 client 呼叫 |
| **回滾驗證** | `make test` 全數通過（移除 client 後 OODA Act 階段需 stub）；確認無 `import shannon` 殘留 |
| **回滾已測試** | ☐ 是 / ☑ 否（client 為 OODA 引擎的硬依賴，回滾需連帶處理 SPEC-007） |

## 🧪 測試矩陣（Test Matrix）

| # | 類型 | 輸入條件 | 預期結果 | 對應場景 |
|---|------|---------|---------|---------|
| P1 | ✅ 正向 | `MockCalderaClient.execute("T1595.001", target)` | `ExecutionResult(success=True, facts=[{type: "network.host.ip", ...}])` | S1 |
| P2 | ✅ 正向 | `MockCalderaClient.execute("T1003.001", target)` | `ExecutionResult(success=True, facts=[{type: "credential.hash", ...}])` | S1 |
| P3 | ✅ 正向 | `CalderaClient.is_available()` 對可達的 Caldera | 回傳 `True` | S1 |
| N1 | ❌ 負向 | `CalderaClient.execute()` 對不可達的 Caldera | `ExecutionResult(success=False, error="timeout")` 或 fallback 至 mock | S2 |
| N2 | ❌ 負向 | `ShannonClient` 且 `SHANNON_URL=""` | `is_available()` 回傳 `False`；`execute()` 拋出 `EngineNotAvailableError` | S2 |
| N3 | ❌ 負向 | Caldera API 回傳非 JSON 格式 | `ExecutionResult(success=False, error="parse error")` | S2 |
| B1 | 🔶 邊界 | `MockCalderaClient.execute()` 未知 ability_id | `ExecutionResult(success=True, facts=[])` | S3 |
| B2 | 🔶 邊界 | httpx timeout 30s 到期 | 回傳 `ExecutionResult(success=False, error="timeout")` | S3 |

## 🎬 驗收場景（Acceptance Scenarios）

```gherkin
Feature: SPEC-008 執行引擎客戶端
  作為 Athena 平台開發者
  我想要 Caldera 和 Shannon 的統一 HTTP 客戶端介面
  以便 OODA Act 階段可透過統一介面執行 MITRE ATT&CK 技術

  Background:
    Given 後端已啟動
    And 環境變數已設定（CALDERA_URL、SHANNON_URL）

  Scenario: S1 - Mock 模式執行預錄技術
    Given CALDERA_URL 未設定或不可達
    And MockCalderaClient 自動啟用
    When execute("T1595.001", "192.168.1.10")
    Then 回傳 ExecutionResult(success=True)
    And facts 含 network.host.ip 類型情報
    And 執行延遲 2-5 秒（模擬真實感）

  Scenario: S2 - Shannon 未配置時完全停用
    Given SHANNON_URL 為空字串
    When ShannonClient 初始化
    Then is_available() 回傳 False
    And execute() 拋出 EngineNotAvailableError

  Scenario: S3 - 未知 ability_id 仍回傳成功
    Given MockCalderaClient 已啟用
    When execute("T9999.999", "192.168.1.10")
    Then 回傳 ExecutionResult(success=True, facts=[])
    And 不拋出例外

  Scenario: S4 - 授權隔離驗證
    Given codebase 中所有 Python 檔案
    When 搜尋 "import shannon" 或 "from shannon import"
    Then 搜尋結果為零筆
```

## 🔍 追溯性（Traceability）

| 類型 | 檔案路徑 |
|------|---------|
| 實作 — Client 基礎 | `backend/app/clients/__init__.py` |
| 實作 — C2 Client | `backend/app/clients/c2_client.py` |
| 實作 — Mock C2 Client | `backend/app/clients/mock_c2_client.py` |
| 實作 — MCP Engine Client | `backend/app/clients/mcp_engine_client.py` |
| 實作 — Metasploit Client | `backend/app/clients/metasploit_client.py` |
| 實作 — 引擎註冊 | `backend/app/services/engine_registry.py` |
| 實作 — 引擎路由 | `backend/app/services/engine_router.py` |
| 測試 — Engine Fallback | `backend/tests/test_engine_fallback.py` |
| 測試 — MCP Engine Routing | `backend/tests/test_mcp_engine_routing.py` |
| 測試 — E2E OODA（含 client 呼叫） | `backend/tests/test_e2e_ooda_loop.py` |

## 👁️ 可觀測性（Observability）

| 項目 | 說明 |
|------|------|
| **關鍵指標** | `execute()` 延遲（ms）、成功率、引擎切換次數（Caldera↔Shannon↔Mock） |
| **日誌** | 每次 `execute()` 記錄 `INFO`：ability_id + target + engine + duration；Mock 模式記錄 `DEBUG` |
| **錯誤追蹤** | 連線失敗 → `WARNING` + fallback 記錄；timeout → `ERROR` + ExecutionResult.error |
| **健康檢查** | `GET /api/health` → `services.caldera`（connected/disconnected/mock）、`services.shannon`（connected/disabled） |

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

