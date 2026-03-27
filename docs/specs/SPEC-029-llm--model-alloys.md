# SPEC-029：LLM 多模型動態路由器 (Model Alloys)

> 結構完整的規格書讓 AI 零確認直接執行。

| 欄位 | 內容 |
|------|------|
| **規格 ID** | SPEC-029 |
| **狀態** | Accepted |
| **版本** | 1.0.0 |
| **作者** | Athena Contributors |
| **建立日期** | 2026-03-06 |
| **關聯 ADR** | ADR-026（多模型動態路由 Model Alloys） |
| **估算複雜度** | 低 |
| **建議模型** | Sonnet |
| **HITL 等級** | minimal |

---

## 🎯 目標（Goal）

依據 ADR-026 決策，在 `LLMClient` 中實作 **Static Task-to-Model Mapping**，讓不同任務類型自動路由至對應的 Claude 模型（Opus / Sonnet / Haiku），降低 40-60% LLM API 成本且不犧牲戰術決策品質。

---

## 📥 輸入規格（Inputs）

### 1. 新增設定項 — `backend/app/config.py`

| 參數名稱 | 型別 | 來源 | 預設值 | 說明 |
|----------|------|------|--------|------|
| `CLAUDE_MODEL_OPUS` | `str` | `.env` / 環境變數 | `"claude-opus-4-6"` | Opus 模型 ID |
| `CLAUDE_MODEL_SONNET` | `str` | `.env` / 環境變數 | `"claude-sonnet-4-20250514"` | Sonnet 模型 ID |
| `CLAUDE_MODEL_HAIKU` | `str` | `.env` / 環境變數 | `"claude-haiku-35-20241022"` | Haiku 模型 ID |
| `MODEL_ALLOYS` | `dict[str, str]` | 硬編碼（引用上方三個變數） | 見下方映射表 | 任務類型 → 模型映射 |

**`MODEL_ALLOYS` 映射表：**

```python
# config.py 新增（Settings class 內部）
CLAUDE_MODEL_OPUS: str = "claude-opus-4-6"
CLAUDE_MODEL_SONNET: str = "claude-sonnet-4-20250514"
CLAUDE_MODEL_HAIKU: str = "claude-haiku-35-20241022"
```

```python
# config.py 新增（module level，Settings class 之後）
TASK_MODEL_MAP: dict[str, str] = {
    "orient_analysis": settings.CLAUDE_MODEL_OPUS,
    "fact_summary": settings.CLAUDE_MODEL_SONNET,
    "node_summary": settings.CLAUDE_MODEL_HAIKU,
    "format_report": settings.CLAUDE_MODEL_HAIKU,
    "classify_vulnerability": settings.CLAUDE_MODEL_HAIKU,
}
```

### 2. `LLMClient.call()` 新增參數

| 參數名稱 | 型別 | 必填 | 預設值 | 說明 |
|----------|------|------|--------|------|
| `task_type` | `str \| None` | 否 | `None` | 任務類型 key，用於查詢 `TASK_MODEL_MAP` |

**模型解析優先順序**（向後相容）：

```
1. 呼叫端顯式傳入 model= 參數 → 使用該模型（最高優先）
2. 呼叫端傳入 task_type= → 查詢 TASK_MODEL_MAP[task_type]
3. 以上皆無 → fallback 至 settings.CLAUDE_MODEL（Opus）
```

### 3. 各呼叫端傳入的 task_type

| 呼叫端檔案 | 呼叫位置 | 傳入的 `task_type` |
|-----------|---------|-------------------|
| `orient_engine.py` | `_call_llm()` L685 | `"orient_analysis"` |
| `node_summarizer.py` | `get_node_summary()` L291 | `"node_summary"`（取代現有 `model=model_name`） |

---

## 📤 輸出規格（Expected Output）

### `LLMClient.call()` 行為變更

**呼叫範例：**

```python
# orient_engine.py — 戰術決策，路由至 Opus
result = await get_llm_client().call(
    system_prompt, user_prompt,
    task_type="orient_analysis",
)

# node_summarizer.py — 節點摘要，路由至 Haiku
result = await get_llm_client().call(
    _NODE_SUMMARY_SYSTEM_PROMPT, user_prompt,
    task_type="node_summary",
    max_tokens=2000,
    temperature=0.5,
    timeout=30.0,
)
```

**日誌輸出（INFO level）：**

```
LLM call: task_type=orient_analysis, model=claude-opus-4-6
LLM call: task_type=node_summary, model=claude-haiku-35-20241022
LLM call: task_type=None, model=claude-opus-4-6  (fallback)
```

### 對既有功能的回傳值影響

無。`LLMClient.call()` 的回傳型別仍為 `str`，所有下游消費者（`OrientEngine`、`NodeSummarizer`）無需修改回傳值處理邏輯。

---

## 🔗 副作用與連動（Side Effects）

| 副作用 | 觸發條件 | 影響模組 | 驗證方式 |
|--------|---------|---------|---------|
| node_summarizer 模型切換至 Haiku | `task_type="node_summary"` 呼叫 LLMClient.call() | 節點摘要 API（`GET /api/targets/{id}/summary`） | 日誌確認 `model=claude-haiku-35-20241022`；摘要品質人工審查 |
| orient_engine 明確指定 task_type | `task_type="orient_analysis"` 呼叫 LLMClient.call() | OODA Orient 分析 | 日誌確認 `task_type=orient_analysis, model=claude-opus-4-6`（行為不變） |
| NODE_SUMMARY_MODEL 標記 deprecated | config.py 載入時 | `config.py` 設定管理 | 確認 NODE_SUMMARY_MODEL 仍存在但加註 `# DEPRECATED` |
| LLM 呼叫日誌新增 task_type 欄位 | 任何 LLMClient.call() 呼叫 | 日誌系統 | INFO 日誌格式為 `LLM call: task_type={type}, model={model}` |

---

## ⚠️ 邊界條件（Edge Cases）

### Case 1：未知的 task_type

```python
# 呼叫端傳入未定義的 task_type
result = await client.call(prompt, user, task_type="unknown_task")
```

**預期行為**：`TASK_MODEL_MAP.get("unknown_task")` 回傳 `None`，fallback 至 `settings.CLAUDE_MODEL`（Opus）。記錄 WARNING 日誌：

```
WARNING: Unknown task_type 'unknown_task', falling back to default model claude-opus-4-6
```

### Case 2：模型不可用（API 回傳 404 / model not found）

**預期行為**：由既有的 `LLMClient` 多後端 fallback 機制處理（Claude API Key → Claude OAuth → OpenAI）。本 SPEC 不修改 fallback 邏輯。若 Haiku 模型 ID 過期或不可用，Anthropic SDK 會拋出例外，觸發現有 fallback chain。

### Case 3：同時傳入 `model=` 和 `task_type=`

```python
result = await client.call(prompt, user, model="claude-sonnet-4-20250514", task_type="orient_analysis")
```

**預期行為**：`model=` 參數優先。最終使用 `claude-sonnet-4-20250514`，忽略 `task_type` 映射。這確保呼叫端在特殊情況下可以覆蓋映射表。

### Case 4：`MOCK_LLM=True` 模式

**預期行為**：`node_summarizer.py` 在 `MOCK_LLM=True` 時直接回傳 mock 資料，不呼叫 `LLMClient.call()`。`orient_engine.py` 亦同。模型路由邏輯不影響 mock 行為。`model_name` 在 mock 路徑中應反映 `TASK_MODEL_MAP` 的解析結果（用於日誌一致性），但不影響實際回傳值。

### Case 5：環境變數覆蓋

```bash
# .env
CLAUDE_MODEL_HAIKU=claude-haiku-35-20250415  # 升級至新版 Haiku
```

**預期行為**：`settings.CLAUDE_MODEL_HAIKU` 被覆蓋，`TASK_MODEL_MAP` 中所有引用 Haiku 的任務自動使用新模型 ID。無需修改映射表。

### ⏪ Rollback Plan

| 回滾步驟 | 資料影響 | 回滾驗證 | 回滾已測試 |
|---------|---------|---------|----------|
| `git revert` 對應 commit | 無 — 不修改任何資料庫 schema 或持久化資料 | `make test` 全數通過；所有 LLM 呼叫恢復至 `settings.CLAUDE_MODEL`（Opus） | 否（需手動驗證） |
| 快速降級（不 revert）：設定 `CLAUDE_MODEL_HAIKU=claude-sonnet-4-20250514` | 無 | Haiku 任務自動升級至 Sonnet，無需程式碼變更或重新部署 | 是（環境變數覆蓋已驗證） |

---

## 🧪 測試矩陣（Test Matrix）

| ID | 類型 | 場景 | 預期結果 | 場景參照 |
|----|------|------|---------|---------|
| P1 | 正向 | `task_type="orient_analysis"` 呼叫 LLMClient.call() | effective_model 為 Opus（`claude-opus-4-6`） | Scenario: 任務類型正確路由至對應模型 |
| P2 | 正向 | `task_type="node_summary"` 呼叫 LLMClient.call() | effective_model 為 Haiku（`claude-haiku-35-20241022`） | Scenario: 任務類型正確路由至對應模型 |
| P3 | 正向 | `task_type="fact_summary"` 呼叫 LLMClient.call() | effective_model 為 Sonnet（`claude-sonnet-4-20250514`） | Scenario: 任務類型正確路由至對應模型 |
| N1 | 負向 | `task_type="unknown_task"` | fallback 至 `settings.CLAUDE_MODEL`（Opus），記錄 WARNING 日誌 | Scenario: 未知 task_type 安全降級 |
| N2 | 負向 | `task_type=None` | fallback 至 `settings.CLAUDE_MODEL`（Opus） | Scenario: 未知 task_type 安全降級 |
| B1 | 邊界 | 同時傳入 `model="claude-sonnet-4-20250514"` + `task_type="orient_analysis"` | `model=` 優先，effective_model 為 Sonnet | Scenario: 顯式 model 參數覆蓋 task_type |
| B2 | 邊界 | 環境變數覆蓋 `CLAUDE_MODEL_HAIKU=claude-haiku-35-20250415` | TASK_MODEL_MAP 中所有 Haiku 任務自動使用新模型 ID | Scenario: 任務類型正確路由至對應模型 |

---

## 🎭 驗收場景（Acceptance Scenarios）

```gherkin
Feature: LLM 多模型動態路由器 (Model Alloys)
  Background:
    Given LLMClient 服務已初始化
    And TASK_MODEL_MAP 包含 5 個任務類型映射
    And MOCK_LLM 為 False

  Scenario: 任務類型正確路由至對應模型
    When orient_engine 呼叫 LLMClient.call(task_type="orient_analysis")
    Then LLMClient 使用 claude-opus-4-6 模型
    And INFO 日誌記錄 "task_type=orient_analysis, model=claude-opus-4-6"
    When node_summarizer 呼叫 LLMClient.call(task_type="node_summary")
    Then LLMClient 使用 claude-haiku-35-20241022 模型
    And INFO 日誌記錄 "task_type=node_summary, model=claude-haiku-35-20241022"

  Scenario: 未知 task_type 安全降級
    When 呼叫 LLMClient.call(task_type="nonexistent_task")
    Then LLMClient fallback 至 settings.CLAUDE_MODEL（Opus）
    And WARNING 日誌記錄 "Unknown task_type 'nonexistent_task'"
    When 呼叫 LLMClient.call(task_type=None)
    Then LLMClient fallback 至 settings.CLAUDE_MODEL（Opus）

  Scenario: 顯式 model 參數覆蓋 task_type
    When 呼叫 LLMClient.call(model="claude-sonnet-4-20250514", task_type="orient_analysis")
    Then LLMClient 使用 claude-sonnet-4-20250514（忽略 task_type 映射）
    And 不記錄 WARNING 日誌
```

---

## 🔗 追溯性（Traceability）

| 追溯項目 | 檔案路徑 | 狀態 |
|---------|---------|------|
| Config 模型設定 + TASK_MODEL_MAP | `backend/app/config.py` | 已實作 |
| LLMClient.call() task_type 參數 | `backend/app/services/llm_client.py` | 已實作 |
| OrientEngine task_type 傳入 | `backend/app/services/orient_engine.py` | 已實作 |
| NodeSummarizer task_type 遷移 | `backend/app/services/node_summarizer.py` | 已實作 |
| main.py 整合 | `backend/app/main.py` | 已實作 |
| 單元測試 — 模型路由 | `backend/tests/test_llm_model_routing.py` | 已實作 |
| E2E 測試 | （待實作） | （待實作） |

> 追溯日期：2026-03-26

---

## 📊 可觀測性（Observability）

| 面向 | 指標/日誌 | 說明 |
|------|----------|------|
| **Logging** | `INFO: LLM call: task_type={task_type}, model={effective_model}` | 每次 LLM 呼叫記錄任務類型與實際使用模型 |
| **Logging** | `WARNING: Unknown task_type '{task_type}', falling back to default model {model}` | 未知 task_type 降級日誌 |
| **Metrics** | `llm_calls_total{task_type, model}` | 各任務類型 + 模型組合的呼叫次數（counter） |
| **Metrics** | `llm_call_duration_seconds{task_type, model}` | 各任務類型的 LLM 呼叫耗時（histogram） |
| **Metrics** | `llm_fallback_total{reason}` | 降級次數（counter，label: unknown_task_type / model_unavailable） |
| **Health** | `CLAUDE_MODEL_OPUS/SONNET/HAIKU` 環境變數 | 可透過環境變數即時調整模型路由，無需重新部署 |

---

## ✅ 驗收標準（Done When）

- [ ] `backend/app/config.py` 新增 `CLAUDE_MODEL_OPUS`、`CLAUDE_MODEL_SONNET`、`CLAUDE_MODEL_HAIKU` 設定項
- [ ] `backend/app/config.py` 新增 `TASK_MODEL_MAP` 字典，包含 5 個任務類型映射
- [ ] `LLMClient.call()` 新增 `task_type: str | None = None` 參數，模型解析邏輯：`model > TASK_MODEL_MAP[task_type] > settings.CLAUDE_MODEL`
- [ ] `LLMClient.call()` 新增 INFO 日誌記錄 `task_type` 和 `effective_model`
- [ ] 未知 `task_type` 時記錄 WARNING 並 fallback 至 `CLAUDE_MODEL`
- [ ] `orient_engine.py` 的 `_call_llm()` 傳入 `task_type="orient_analysis"`
- [ ] `node_summarizer.py` 的 LLM 呼叫改用 `task_type="node_summary"`，移除對 `settings.NODE_SUMMARY_MODEL` 的直接依賴
- [ ] `settings.NODE_SUMMARY_MODEL` 加註 `# DEPRECATED` 但保留（向後相容）
- [ ] `backend/tests/test_llm_model_routing.py` 新增，覆蓋以下場景：
  - `task_type` 正確路由至對應模型（5 個 task type 各一個 test case）
  - 未知 `task_type` fallback 至 `CLAUDE_MODEL`
  - `task_type=None` fallback 至 `CLAUDE_MODEL`
  - `model=` 參數優先於 `task_type`
  - 同時傳入 `model=` 和 `task_type=` 時 `model=` 勝出
- [ ] `make test` 全數通過
- [ ] `make lint` 無 error

---

## 🚫 禁止事項（Out of Scope）

- **不要**實作動態路由邏輯（選項 B）—— ADR-026 已決策為靜態映射
- **不要**實作 Cascading Fallback（選項 C）—— ADR-026 明確排除
- **不要**修改 `_call_claude()`、`_call_claude_oauth()`、`_call_openai()` 的內部實作
- **不要**修改 OpenAI fallback 的模型選擇邏輯（仍使用 `settings.OPENAI_MODEL`）
- **不要**刪除 `NODE_SUMMARY_MODEL` 設定項（僅 deprecate，保留向後相容）
- **不要**引入新的 Python 依賴
- **不要**修改資料庫 schema
- **不要**修改 WebSocket 事件格式
- **不要**實作 per-call token 用量追蹤（留待 ADR-026 Phase 3）

---

## 📎 參考資料（References）

- 關聯 ADR：[ADR-026 — 多模型動態路由 (Model Alloys)](../adr/ADR-026--model-alloys.md)
- 現有類似實作：`node_summarizer.py` L276 的 `settings.NODE_SUMMARY_MODEL` 模式
- 核心修改檔案：
  - `backend/app/config.py` — 新增模型設定項 + `TASK_MODEL_MAP`
  - `backend/app/services/llm_client.py` — `call()` 新增 `task_type` 參數 + 模型解析
  - `backend/app/services/orient_engine.py` — `_call_llm()` 傳入 `task_type`
  - `backend/app/services/node_summarizer.py` — 遷移至 `task_type` 統一機制
  - `backend/tests/test_llm_model_routing.py` — 新增測試檔案
- 外部參考：XBOW Model Alloys 技術（業界多模型路由實踐）
- 延伸 ADR：ADR-013（Orient Prompt Engineering）、ADR-014（Anthropic SDK Migration）

---

## 📐 實作指引（Implementation Guide）

> 以下為具體程式碼變更指引，確保 AI 可零確認執行。

### Step 1：`backend/app/config.py`

在 `Settings` class 內，`NODE_SUMMARY_MODEL` 行（L67）之前新增：

```python
CLAUDE_MODEL_OPUS: str = "claude-opus-4-6"
CLAUDE_MODEL_SONNET: str = "claude-sonnet-4-20250514"
CLAUDE_MODEL_HAIKU: str = "claude-haiku-35-20241022"
```

在 `NODE_SUMMARY_MODEL` 行加註 deprecated：

```python
NODE_SUMMARY_MODEL: str = "claude-sonnet-4-20250514"  # DEPRECATED: use TASK_MODEL_MAP["node_summary"]
```

在 `settings = Settings()` 之後（L71 後）新增：

```python
TASK_MODEL_MAP: dict[str, str] = {
    "orient_analysis": settings.CLAUDE_MODEL_OPUS,
    "fact_summary": settings.CLAUDE_MODEL_SONNET,
    "node_summary": settings.CLAUDE_MODEL_HAIKU,
    "format_report": settings.CLAUDE_MODEL_HAIKU,
    "classify_vulnerability": settings.CLAUDE_MODEL_HAIKU,
}
```

### Step 2：`backend/app/services/llm_client.py`

修改 `call()` 方法簽名（L61-70），新增 `task_type` 參數：

```python
async def call(
    self,
    system_prompt: str,
    user_prompt: str,
    *,
    model: str | None = None,
    task_type: str | None = None,
    max_tokens: int = 4000,
    temperature: float = 0.7,
    timeout: float = 60.0,
) -> str:
```

修改模型解析邏輯（L76），替換 `effective_model = model or settings.CLAUDE_MODEL`：

```python
from app.config import settings, TASK_MODEL_MAP

if model:
    effective_model = model
elif task_type:
    effective_model = TASK_MODEL_MAP.get(task_type)
    if effective_model is None:
        logger.warning("Unknown task_type '%s', falling back to default model %s", task_type, settings.CLAUDE_MODEL)
        effective_model = settings.CLAUDE_MODEL
else:
    effective_model = settings.CLAUDE_MODEL

logger.info("LLM call: task_type=%s, model=%s", task_type, effective_model)
```

### Step 3：`backend/app/services/orient_engine.py`

修改 `_call_llm()` 方法（L681-689），加入 `task_type`：

```python
async def _call_llm(self, system_prompt: str, user_prompt: str) -> str:
    from app.services.llm_client import get_llm_client

    result = await get_llm_client().call(
        system_prompt, user_prompt,
        task_type="orient_analysis",
    )
    if not result:
        logger.info("No LLM backend available, using mock recommendation")
        return json.dumps(_MOCK_RECOMMENDATION)
    return result
```

### Step 4：`backend/app/services/node_summarizer.py`

修改 `get_node_summary()` 中的 LLM 呼叫（L291-298），改用 `task_type`：

```python
raw = await get_llm_client().call(
    _NODE_SUMMARY_SYSTEM_PROMPT,
    user_prompt,
    task_type="node_summary",
    max_tokens=2000,
    temperature=0.5,
    timeout=30.0,
)
```

同步更新 mock 路徑中的 `model_name` 解析（L276），改為查詢 `TASK_MODEL_MAP`：

```python
from app.config import settings, TASK_MODEL_MAP
model_name = TASK_MODEL_MAP.get("node_summary", settings.CLAUDE_MODEL)
```

### Step 5：`backend/tests/test_llm_model_routing.py`（新增）

測試案例清單：

| Test Case | 描述 | 驗證 |
|-----------|------|------|
| `test_task_type_orient_routes_to_opus` | `task_type="orient_analysis"` | `effective_model == "claude-opus-4-6"` |
| `test_task_type_fact_summary_routes_to_sonnet` | `task_type="fact_summary"` | `effective_model == "claude-sonnet-4-20250514"` |
| `test_task_type_node_summary_routes_to_haiku` | `task_type="node_summary"` | `effective_model == "claude-haiku-35-20241022"` |
| `test_task_type_format_report_routes_to_haiku` | `task_type="format_report"` | `effective_model == "claude-haiku-35-20241022"` |
| `test_task_type_classify_vuln_routes_to_haiku` | `task_type="classify_vulnerability"` | `effective_model == "claude-haiku-35-20241022"` |
| `test_unknown_task_type_falls_back_to_default` | `task_type="nonexistent"` | `effective_model == settings.CLAUDE_MODEL` + WARNING 日誌 |
| `test_none_task_type_falls_back_to_default` | `task_type=None` | `effective_model == settings.CLAUDE_MODEL` |
| `test_explicit_model_overrides_task_type` | `model="X", task_type="orient_analysis"` | `effective_model == "X"` |
| `test_task_model_map_uses_settings_values` | 驗證 `TASK_MODEL_MAP` 引用 `settings.*` | 環境變數覆蓋生效 |

