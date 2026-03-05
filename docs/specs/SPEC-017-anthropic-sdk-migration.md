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
