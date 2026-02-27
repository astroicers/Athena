# [ADR-014]: Orient Engine LLM 整合從 HTTP API 遷移至 Anthropic/OpenAI Python SDK

| 欄位 | 內容 |
|------|------|
| **狀態** | `Accepted` |
| **日期** | 2026-02-27 |
| **決策者** | 專案負責人 |
| **取代** | ADR-005 中「HTTP API 呼叫」整合方式的描述 |

---

## 背景（Context）

Phase 5 實作的 `orient_engine.py` 原使用 `httpx` 直接呼叫 Claude / OpenAI HTTP API。Phase 9 修復 LLM 真實整合 bug 時（commit `6445f9e`），發現 HTTP API 整合存在以下問題：

1. **API 版本管理困難**——需手動維護 `anthropic-version` header（2023-06-01 → 2024-10-22），版本不匹配導致 400 錯誤
2. **回應解析脆弱**——需手動處理 JSON 結構差異（`content[0].text` vs `choices[0].message.content`）
3. **重試/超時無標準化**——需自行實作 retry 邏輯，SDK 已內建
4. **型別安全缺失**——HTTP 回應為 `dict`，無 IDE 自動補全

Phase 10（SPEC-015）升級 prompt 工程時，將 `_call_claude()` 和 `_call_openai()` 遷移至官方 Python SDK，解決上述所有問題。

---

## 評估選項

### 選項 A：維持 httpx 直接 HTTP 呼叫（原方案）
- 優點：零額外依賴、完全控制 HTTP 層
- 風險：版本管理手動、回應解析脆弱、無重試內建

### 選項 B：遷移至 Anthropic / OpenAI Python SDK（✅ 採用）
- 優點：自動版本管理、型別安全、內建重試、官方支援
- 風險：新增 2 個依賴（`anthropic`、`openai`）
- 成本：SDK 已透過 `pyproject.toml` 安裝，遷移工作量極小

---

## 決策

**採用選項 B**：使用 Anthropic Python SDK（`anthropic`）和 OpenAI Python SDK（`openai`）取代 `httpx` 直接 HTTP 呼叫。

### 核心改動
```python
# 之前（httpx HTTP API）
response = await self._http.post(
    "https://api.anthropic.com/v1/messages",
    headers={"anthropic-version": "2024-10-22", ...},
    json={"model": "claude-opus-4-20250514", "messages": [...]}
)
result = response.json()["content"][0]["text"]

# 之後（Anthropic SDK）
client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
response = client.messages.create(
    model="claude-opus-4-20250514",
    system=system_prompt,
    messages=[{"role": "user", "content": user_prompt}],
    max_tokens=4000
)
result = response.content[0].text
```

### 影響範圍
- `backend/app/services/orient_engine.py` — `_call_claude()` 和 `_call_openai()` 方法
- `backend/pyproject.toml` — 新增 `anthropic` 和 `openai` 依賴
- 外部介面 `analyze()` 回傳結構不變
- `MOCK_LLM=true` 路徑不受影響

---

## 未解決的 Trade-off

- `httpx` 仍用於 Caldera / Shannon HTTP API 呼叫（非 LLM），這是正確的——它們是 REST API，無官方 SDK
- 未來若 PentestGPT 有自己的 Python SDK，可進一步簡化 Orient Engine
