# SPEC-017：Anthropic SDK 遷移

> 將 OrientEngine 的 Claude API 呼叫從 httpx 原始 HTTP 升級為官方 Anthropic Python SDK。

| 欄位 | 內容 |
|------|------|
| **規格 ID** | SPEC-017 |
| **關聯 ADR** | ADR-005（PentestGPT Orient 引擎） |
| **估算複雜度** | 低 |
| **建議模型** | Sonnet |
| **HITL 等級** | standard |

---

## 🎯 目標（Goal）

> 將 `OrientEngine._call_claude()` 從 `httpx.AsyncClient` 原始 HTTP POST 呼叫遷移至官方 `anthropic.AsyncAnthropic` SDK，獲得自動重試、連線復用、型別化錯誤處理，並新增 Bearer token 認證支援。遷移後 `_call_claude()` 回傳介面（`str`）不變，上層 `analyze()` 的 JSON 解析邏輯無需修改。

---

## 📥 輸入規格（Inputs）

| 參數名稱 | 型別 | 來源 | 限制條件 |
|----------|------|------|----------|
| ANTHROPIC_API_KEY | string | .env | `sk-ant-...` 格式，與 AUTH_TOKEN 至少填一個 |
| ANTHROPIC_AUTH_TOKEN | string | .env | **新增** — Bearer token 認證（替代 API key） |
| CLAUDE_MODEL | string | .env | **更新預設** — `claude-opus-4-6`（舊：`claude-opus-4-20250514`） |
| MOCK_LLM | bool | .env | true=跳過所有 LLM 呼叫（不初始化 SDK） |

---

## 📤 輸出規格（Expected Output）

**`_call_claude()` 行為（SDK 遷移後）：**

| 行為 | 遷移前 (httpx) | 遷移後 (SDK) |
|------|---------------|-------------|
| Client 生命週期 | 每次呼叫 `httpx.AsyncClient()` | 單一 `AsyncAnthropic` 實例，lazy init |
| 認證 | 僅 `x-api-key` header | API key + Bearer token（雙重支援） |
| 重試 | 無 | SDK 內建 2 次指數退避（429/5xx） |
| 錯誤類型 | `httpx.HTTPStatusError` | `anthropic.RateLimitError` 等型別化例外 |
| 回應解析 | `resp.json()["content"][0]["text"]` | `message.content[0].text`（型別安全） |
| 回傳值 | `str` | `str`（**不變**） |

**健康檢查回應（`GET /api/health`）：**

只設 `ANTHROPIC_AUTH_TOKEN`（無 API key）：
```json
{
  "services": {
    "llm": "claude"
  }
}
```

兩者都沒設：
```json
{
  "services": {
    "llm": "unavailable"
  }
}
```

---

## ⚠️ 邊界條件（Edge Cases）

- Case 1：只設 `ANTHROPIC_API_KEY` — SDK 用 `api_key=` 初始化，行為與遷移前相同
- Case 2：只設 `ANTHROPIC_AUTH_TOKEN` — SDK 用 `auth_token=` 初始化，走 Bearer token 認證
- Case 3：兩者都設 — SDK 同時設定 `api_key` + `auth_token`，API 接受兩個 header
- Case 4：兩者都沒設 — `_call_llm()` 跳過 Claude，嘗試 OpenAI fallback
- Case 5：`MOCK_LLM=True` — `analyze()` 在進入 `_call_llm()` 前直接回傳 mock，SDK 完全不初始化
- Case 6：Claude API 回傳空 `content` — 拋出 `ValueError("Empty content in Claude response")`，`_call_llm()` 捕獲後嘗試 OpenAI fallback
- Case 7：Claude API 429/500 — SDK 自動重試 2 次後仍失敗，`_call_llm()` 捕獲後嘗試 OpenAI fallback

---

## 📝 修改範圍

| 檔案 | 修改類型 | 說明 |
|------|----------|------|
| `backend/pyproject.toml` | 新增依賴 | `anthropic>=0.49.0` |
| `backend/app/config.py` | 新增欄位 + 改預設 | `ANTHROPIC_AUTH_TOKEN`、`CLAUDE_MODEL` |
| `backend/app/services/orient_engine.py` | 重寫方法 | `_call_claude()` 改用 SDK |
| `backend/app/routers/health.py` | 條件更新 | 檢查 `AUTH_TOKEN` |
| `backend/tests/test_spec_007_ooda_services.py` | 重寫測試 | mock SDK 取代 mock httpx |
| `backend/tests/test_integration_real_mode.py` | 修復 bug | `_call_claude()` 參數修正 |
| `.env.example` | 文件更新 | 新增 `ANTHROPIC_AUTH_TOKEN` |

**不修改：**

| 檔案 | 原因 |
|------|------|
| `orient_engine.py`（`_call_openai`） | 不在範圍 — 保持 httpx |
| `orient_engine.py`（`_build_prompt`、prompts） | 不動 |
| `orient_engine.py`（`analyze()` JSON 解析） | 不動 |
| `conftest.py` | `httpx.AsyncClient(ASGITransport)` — 無關 |
| `caldera_client.py` / `shannon_client.py` | 用 httpx — 無關 |

---

## ✅ 驗收標準（Done When）

- [x] `make test` 全部通過（MOCK_LLM=true 預設）
- [x] `ruff check backend/` 無 lint 問題
- [x] `orient_engine.py` 不再直接呼叫 `httpx` 存取 Anthropic API
- [x] `orient_engine.py` 使用 `anthropic.AsyncAnthropic` SDK
- [x] `config.py` 包含 `ANTHROPIC_AUTH_TOKEN` 欄位
- [x] `config.py` 的 `CLAUDE_MODEL` 預設為 `claude-opus-4-6`
- [x] `health.py` 在只設 `ANTHROPIC_AUTH_TOKEN` 時回報 `"llm": "claude"`
- [x] `test_orient_call_claude_sends_system_param` 使用 SDK mock 通過
- [x] `test_call_claude_returns_json` 的參數簽名修正
- [x] `.env.example` 包含 `ANTHROPIC_AUTH_TOKEN` 說明

---

## 🚫 禁止事項（Out of Scope）

- 不要遷移 `_call_openai()` — 保持 httpx
- 不要引入 LangChain 或其他 LLM 框架
- 不要新增 streaming 支援（回應為小 JSON，不需要）
- 不要新增 extended thinking / adaptive thinking（結構化 JSON 輸出任務，不需要）
- 不要新增 structured outputs（`output_config.format`）— 當前 JSON-parse-with-fallback 方式可靠
- 不要修改 prompt 模板或 `_build_prompt()` 邏輯
- 不要修改 `analyze()` 的 JSON 解析和驗證邏輯

---

## 📎 參考資料（References）

- 關聯 ADR：ADR-005（PentestGPT Orient 引擎）
- 關聯 SPEC：SPEC-007（OODA 循環引擎）、SPEC-012（外部專案整合）、SPEC-015（Orient Prompt 工程）
- Anthropic Python SDK：https://github.com/anthropics/anthropic-sdk-python
- SDK 認證文件：支援 `api_key`（X-Api-Key header）+ `auth_token`（Authorization: Bearer header）
- 實施計畫：`/home/ubuntu/.claude/plans/compressed-squishing-sunset.md`

---

## 副作用與連動（Side Effects）

| 副作用 | 觸發條件 | 影響模組 | 驗證方式 |
|--------|----------|----------|----------|
| SDK client 單例生命週期 | `AsyncAnthropic` lazy init，首次 `_call_claude()` 時建立 | `backend/app/services/orient_engine.py` | `test_spec_007_ooda_services.py` 驗證 mock SDK |
| 錯誤類型變更 | `httpx.HTTPStatusError` → `anthropic.RateLimitError` 等 | `ooda_controller.py` 上層 try/except | 既有 OODA 測試迴歸 |
| `config.py` 新增欄位 | `ANTHROPIC_AUTH_TOKEN` 環境變數 | `backend/app/config.py`、`.env.example` | `make test` 驗證預設值無破壞 |
| Health endpoint 行為變更 | 僅設 `AUTH_TOKEN` 時 LLM 狀態顯示 `"claude"` | `backend/app/routers/health.py` | 健康檢查單元測試 |

---

## Rollback Plan

| 回滾步驟 | 資料影響 | 回滾驗證 | 回滾已測試 |
|----------|----------|----------|------------|
| 1. `git revert` SDK 遷移 commit，還原 `_call_claude()` 為 httpx 版本 | 無資料影響（stateless API 呼叫） | `make test` 全通過 | 是（遷移前測試通過） |
| 2. 移除 `anthropic` 依賴（`pyproject.toml`） | 無 | `pip install -e .` 成功 | 是 |
| 3. 還原 `config.py` 移除 `ANTHROPIC_AUTH_TOKEN` | 無（env var 不影響 DB） | `make test` 全通過 | 是 |

---

## 測試矩陣（Test Matrix）

| ID | 類型 | 場景 | 輸入 | 預期結果 | 場景參照 |
|----|------|------|------|----------|----------|
| P1 | 正向 | SDK 正常呼叫 Claude 並回傳 JSON | `ANTHROPIC_API_KEY` 有效 + prompt | `_call_claude()` 回傳 str（JSON 內容） | S1 |
| P2 | 正向 | Bearer token 認證成功 | 僅設 `ANTHROPIC_AUTH_TOKEN` | SDK 使用 `auth_token=` 初始化，呼叫成功 | S1 |
| N1 | 負向 | 兩個認證都未設定 | 無 `API_KEY` 且無 `AUTH_TOKEN` | `_call_llm()` 跳過 Claude，嘗試 OpenAI fallback | S2 |
| N2 | 負向 | Claude API 回傳空 content | SDK 回傳 `message.content = []` | 拋出 `ValueError("Empty content")`，fallback OpenAI | S2 |
| B1 | 邊界 | Claude API 429 rate limit | SDK 自動重試 2 次後仍 429 | `RateLimitError` 被捕獲，fallback OpenAI | S3 |
| B2 | 邊界 | `MOCK_LLM=True` | 環境變數 `MOCK_LLM=true` | SDK 完全不初始化，`analyze()` 回傳 mock 結果 | S3 |

---

## 驗收場景（Acceptance Scenarios）

```gherkin
Feature: Anthropic SDK 遷移

  Background:
    Given OrientEngine 已初始化
    And MOCK_LLM 為 false

  Scenario: S1 — SDK 使用 API key 正常呼叫 Claude
    Given 環境變數 ANTHROPIC_API_KEY 已設定為有效值
    And CLAUDE_MODEL 設為 "claude-opus-4-6"
    When OrientEngine._call_claude() 被呼叫
    Then SDK 使用 AsyncAnthropic(api_key=...) 建立 client
    And 回傳值為 str 型別
    And 回傳值包含有效 JSON 內容

  Scenario: S2 — 認證全缺時 fallback 至 OpenAI
    Given 環境變數 ANTHROPIC_API_KEY 未設定
    And 環境變數 ANTHROPIC_AUTH_TOKEN 未設定
    When OrientEngine._call_llm() 被呼叫
    Then _call_claude() 被跳過
    And _call_openai() 被嘗試作為 fallback

  Scenario: S3 — MOCK_LLM 模式下 SDK 不初始化
    Given 環境變數 MOCK_LLM 設為 true
    When OrientEngine.analyze() 被呼叫
    Then AsyncAnthropic 未被實例化
    And 回傳值為預設 mock JSON
```

---

## 追溯性（Traceability）

| 項目 | 路徑 / 識別碼 | 狀態 |
|------|---------------|------|
| 規格文件 | `docs/specs/SPEC-017-anthropic-sdk-migration.md` | Done |
| 關聯 ADR | `docs/adr/ADR-005` | Accepted |
| OrientEngine 實作 | `backend/app/services/orient_engine.py` | 已遷移 |
| LLM Client | `backend/app/services/llm_client.py` | 已更新 |
| Config 欄位 | `backend/app/config.py` | 已新增 AUTH_TOKEN |
| Health Router | `backend/app/routers/health.py` | 已更新 |
| 單元測試 — OODA | `backend/tests/test_spec_007_ooda_services.py` | 已重寫 mock |
| 單元測試 — Orient | `backend/tests/test_orient_engine.py` | 通過 |
| 整合測試 | `backend/tests/test_integration_real_mode.py` | 已修正 |
| LLM 路由測試 | `backend/tests/test_llm_model_routing.py` | 通過 |
| 更新日期 | 2026-03-26 | — |

---

## 可觀測性（Observability）

| 面向 | 內容 |
|------|------|
| **指標（Metrics）** | `orient.claude_call.duration_seconds`（histogram）、`orient.claude_call.success_total` / `orient.claude_call.error_total`（counter）、`orient.fallback_to_openai_total`（counter） |
| **日誌（Logs）** | SDK 初始化模式（api_key / auth_token / both）、Claude 呼叫開始/完成/失敗（含 model 名稱）、Fallback 觸發原因 |
| **告警（Alerts）** | Claude API 連續失敗 ≥ 3 次（含 429）、fallback 比例超過 50%、MOCK_LLM=false 但 SDK 未初始化 |
| **故障偵測（Fault Detection）** | `RateLimitError` 頻率監控（sliding window 1min）、empty content 回傳頻率、SDK client 初始化失敗時立即 log error + 降級至 fallback |
