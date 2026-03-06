# [ADR-026]: 多模型動態路由 (Model Alloys)

| 欄位 | 內容 |
|------|------|
| **狀態** | `Accepted` |
| **日期** | 2026-03-06 |
| **決策者** | Athena Core Team |

---

## 背景（Context）

Athena 的 OODA 循環目前所有 LLM 呼叫均使用單一模型（`config.py` 中的 `CLAUDE_MODEL: str = "claude-opus-4-6"`）。無論任務複雜度高低，每次迭代皆以最高規格模型處理，造成以下問題：

1. **成本效率低下**：每次 OODA 循環中的 Orient 分析、節點摘要、事實整理等任務全部呼叫 Opus 級模型。以單次 Orient 分析約 4,000 output tokens 計算，每日 50 次循環的 API 成本顯著偏高。
2. **不必要的延遲**：簡單任務（如格式化報告、分類弱點）的回應時間被 Opus 模型的推理開銷拖慢。`node_summarizer.py` 的單節點摘要（max_tokens=2,000）使用 Opus 等同於殺雞用牛刀。
3. **無法針對任務特性最佳化**：戰術決策分析（Orient 引擎的 3 選項推薦）需要深度推理，但事實摘要和報告格式化只需要基本的語言理解。當前架構無法區分這兩類需求。
4. **缺乏成本可觀測性**：沒有 per-task 的模型使用追蹤，無法量化各任務的成本佔比。

### 現有架構分析

目前 LLM 呼叫鏈如下：

```
OrientEngine.analyze()
  → _call_llm()
    → LLMClient.call(system_prompt, user_prompt)  # model=None → defaults to CLAUDE_MODEL
      → _call_claude() / _call_claude_oauth() / _call_openai()

NodeSummarizer.get_node_summary()
  → LLMClient.call(..., model=settings.NODE_SUMMARY_MODEL)  # 已獨立使用 NODE_SUMMARY_MODEL
```

值得注意的是，`node_summarizer.py` 已經透過 `settings.NODE_SUMMARY_MODEL`（預設 `claude-sonnet-4-20250514`）實現了部分的模型分流。這證明現有 `LLMClient.call()` 的 `model` 參數已支援 per-call 模型指定，架構上無需大幅重構。

### 業界參考

XBOW 團隊提出的 **Model Alloys** 技術在單一對話線程內根據任務複雜度動態切換不同 AI 模型，在其漏洞利用框架中實現了顯著的成本優化且未犧牲關鍵決策品質。此概念直接適用於 Athena 的多任務 OODA 架構。

---

## 評估選項（Options Considered）

### 選項 A：任務類型靜態映射 (Static Task-to-Model Mapping)

在 `config.py` 中以字典形式定義任務類型與模型的對應關係，各呼叫端明確傳入任務類型：

```python
# config.py
MODEL_ALLOYS: dict[str, str] = {
    "orient_analysis": "claude-opus-4-6",         # 戰術決策 — 需要深度推理
    "fact_summary": "claude-sonnet-4-20250514",     # 事實摘要 — 中等複雜度
    "node_summary": "claude-haiku-35-20241022",     # 單節點摘要 — 簡單整理
    "format_report": "claude-haiku-35-20241022",    # 報告格式化 — 純格式任務
    "classify_vulnerability": "claude-haiku-35-20241022",  # 弱點分類 — 簡單分類
}
```

呼叫方式變更：

```python
# orient_engine.py — 高風險戰術決策維持 Opus
model = settings.MODEL_ALLOYS.get("orient_analysis", settings.CLAUDE_MODEL)
result = await get_llm_client().call(system_prompt, user_prompt, model=model)

# node_summarizer.py — 已有的模式，無需變更
result = await get_llm_client().call(..., model=settings.NODE_SUMMARY_MODEL)
```

- **優點**：
  - 實作簡單，僅需修改 `config.py` 新增映射表 + 各呼叫端加入 `task_type` 查詢
  - 行為完全可預測，debug 時可直接查表確認使用的模型
  - 支援環境變數覆蓋（`MODEL_ALLOYS__orient_analysis=claude-sonnet-4-20250514`）
  - 與既有 `NODE_SUMMARY_MODEL` 模式一致，團隊已有相同實踐經驗
  - 向後相容：未定義的任務類型 fallback 至 `CLAUDE_MODEL`（Opus）
- **缺點**：
  - 新增任務類型時需同步更新配置映射
  - 無法根據執行期資訊（如 prompt 長度、風險等級）動態調整
- **風險**：Low — 最壞情況為映射錯誤，但 fallback 至 Opus 保證品質不退化

### 選項 B：動態路由器 (Dynamic LLM Router)

建立 `LLMRouter` 類別，根據執行期指標（token 數量估算、風險等級、任務類型標記）自動選擇模型：

```python
class LLMRouter:
    def select_model(self, task_type: str, prompt_length: int, risk_level: str) -> str:
        if risk_level in ("high", "critical") or prompt_length > 8000:
            return "claude-opus-4-6"
        if task_type in ("fact_summary", "node_summary"):
            return "claude-haiku-35-20241022"
        return "claude-sonnet-4-20250514"
```

- **優點**：
  - 能根據執行期資訊做出最佳化選擇
  - 新增任務類型時不需手動更新映射，router 自動推斷
  - 可隨時間學習最佳路由策略（未來擴展）
- **缺點**：
  - 實作較複雜，需定義 routing 規則、閾值、fallback 邏輯
  - routing 邏輯本身需要測試和調校
  - 行為不透明，debug 時需追蹤 router 的決策路徑
  - 增加新的抽象層，偏離 KISS 原則
- **風險**：Medium — 錯誤的模型選擇可能導致戰術分析品質下降。例如，若 router 將高風險 Orient 分析錯誤路由至 Haiku，產出的 3 選項推薦可能缺乏深度推理，影響操作員決策

### 選項 C：分層 Fallback (Cascading Fallback)

從最低成本模型開始呼叫，若回應信心度低於閾值則逐級升級：

```
Haiku (fastest, cheapest)
  → confidence < 0.7? → Sonnet (balanced)
    → confidence < 0.7? → Opus (full reasoning)
```

- **優點**：
  - 理論上成本最優化 — 簡單任務只需一次 Haiku 呼叫即可完成
  - 自適應：同一任務類型在不同複雜度下自動選擇不同模型
- **缺點**：
  - 複雜任務需 2-3 次 API 呼叫，延遲翻倍甚至三倍（OODA 循環對延遲敏感）
  - 信心度評估本身不可靠 — LLM 的 self-reported confidence 與實際品質相關性低
  - 每次升級時前一次呼叫的 token 成本浪費
  - 實作和測試複雜度高，需處理升級觸發、上下文傳遞、token 重複消耗
- **風險**：High — 對 OODA 循環而言，延遲是關鍵指標。`OODA_LOOP_INTERVAL_SEC` 預設 30 秒，若單次 Orient 分析從 ~5 秒膨脹至 ~15 秒（3 次串行呼叫），將壓縮 Observe/Act 的可用時間窗口

---

## 決策（Decision）

選擇 **選項 A：任務類型靜態映射 (Static Task-to-Model Mapping)**。

### 決策理由

1. **與既有實踐一致**：`node_summarizer.py` 已透過 `NODE_SUMMARY_MODEL` 配置項實現了任務級模型分流，選項 A 將此模式系統化為統一映射表，是自然的演進而非革命性重構。

2. **風險最低**：Athena 是 C5ISR 級作戰平台，Orient 引擎的戰術建議直接影響操作員決策。靜態映射保證高風險任務（`orient_analysis`）始終使用最強模型，不存在 routing 錯誤或 cascading 延遲的可能性。

3. **實作成本極低**：
   - `config.py`：新增 `MODEL_ALLOYS` 字典（約 10 行）
   - `orient_engine.py`：`_call_llm()` 呼叫加入 `model=` 參數（1 行）
   - `node_summarizer.py`：已使用獨立模型配置，可選擇性遷移至統一映射表
   - 未來新服務：呼叫 `LLMClient.call()` 時查表即可
   - 預估工時：< 2 小時（含測試）

4. **可觀測性**：每次 LLM 呼叫已有 `model` 參數，配合現有 WebSocket 事件（`orient.thinking`）即可追蹤 per-task 模型使用量。

5. **漸進式優化路徑**：選項 A 不排斥未來演進至選項 B。當我們累積足夠的 per-task 使用數據後，可在靜態映射之上疊加動態邏輯，而非一開始就引入複雜性。

### 任務-模型映射表

| 任務類型 | 模型 | 理由 | 預估成本降低 |
|---------|------|------|-------------|
| `orient_analysis` | `claude-opus-4-6` | 戰術決策需要深度推理、Kill Chain 分析、3 選項評估。影響操作員決策，品質不可妥協 | 0%（基準線） |
| `fact_summary` | `claude-sonnet-4-20250514` | 彙整已收集的情報事實。需要理解上下文但不需複雜推理 | ~60% vs Opus |
| `node_summary` | `claude-haiku-35-20241022` | 單節點狀態摘要（攻擊面、憑證鏈、風險評估）。結構化輸入/輸出，pattern matching 為主 | ~90% vs Opus |
| `format_report` | `claude-haiku-35-20241022` | Markdown 格式化、表格產生。純語言處理任務 | ~90% vs Opus |
| `classify_vulnerability` | `claude-haiku-35-20241022` | CVE 嚴重度分類、CVSS 分數區間判定。規則明確的分類任務 | ~90% vs Opus |

### 實作方針

1. **`config.py` 新增映射表**：
   ```python
   MODEL_ALLOYS: dict[str, str] = {
       "orient_analysis": "claude-opus-4-6",
       "fact_summary": "claude-sonnet-4-20250514",
       "node_summary": "claude-haiku-35-20241022",
       "format_report": "claude-haiku-35-20241022",
       "classify_vulnerability": "claude-haiku-35-20241022",
   }
   ```
   所有值皆可透過環境變數覆蓋。

2. **`LLMClient.call()` 新增 `task_type` 參數**（向後相容）：
   ```python
   async def call(
       self, system_prompt: str, user_prompt: str, *,
       model: str | None = None,
       task_type: str | None = None,  # 新增：查詢 MODEL_ALLOYS 映射
       ...
   ) -> str:
       effective_model = model or (
           settings.MODEL_ALLOYS.get(task_type, settings.CLAUDE_MODEL)
           if task_type else settings.CLAUDE_MODEL
       )
   ```

3. **各呼叫端遷移**（漸進式）：
   - Phase 1：`orient_engine.py` 加入 `task_type="orient_analysis"`
   - Phase 2：`node_summarizer.py` 遷移至 `task_type="node_summary"`（取代 `NODE_SUMMARY_MODEL`）
   - Phase 3：未來新增的 fact summarizer、report generator 直接使用對應 `task_type`

4. **可觀測性**：在 `LLMClient.call()` 中記錄 `task_type` 和 `effective_model` 至日誌，便於追蹤成本分布。

---

## 後果（Consequences）

**正面影響：**
- LLM API 成本預估降低 40-60%（取決於 OODA 循環中各任務類型的呼叫頻率分布）
- 簡單任務（node_summary、format_report）回應延遲從 ~5 秒降至 ~1-2 秒
- 建立 per-task 模型使用追蹤基礎，為未來成本分析和動態路由提供數據
- 與既有 `NODE_SUMMARY_MODEL` 模式完全相容，遷移無破壞性
- 環境變數覆蓋機制允許操作員根據預算和品質需求即時調整

**負面影響 / 技術債：**
- `NODE_SUMMARY_MODEL` 配置項將在 Phase 2 後成為冗餘（標記 `tech-debt: deprecate-NODE_SUMMARY_MODEL`）
- 新增任務類型時需記得同步更新 `MODEL_ALLOYS` 映射表（可透過 code review checklist 強制）
- Haiku 模型在某些邊界案例（如含有大量技術專有名詞的中文摘要）可能產出品質較低的結果，需要針對性測試

**後續追蹤：**
- [ ] Phase 1：`config.py` 新增 `MODEL_ALLOYS` + `LLMClient.call()` 支援 `task_type` + `orient_engine.py` 遷移
- [ ] Phase 2：`node_summarizer.py` 遷移至統一映射、deprecate `NODE_SUMMARY_MODEL`
- [ ] Phase 3：新增 LLM 呼叫成本追蹤 logging（task_type, model, input_tokens, output_tokens）
- [ ] Phase 4：收集 2 週使用數據後，評估是否需要演進至動態路由（選項 B）

---

## 成功指標（Success Metrics）

| 指標 | 目標值 | 驗證方式 | 檢查時間 |
|------|--------|----------|----------|
| LLM API 成本降低 | > 40% | API usage tracking（per-task model 使用統計） | 部署後 2 週 |
| 戰術分析品質 | 無退化（Orient confidence >= baseline） | A/B comparison：Opus-only vs Model Alloys 各跑 10 次 OODA 循環 | 部署後 1 週 |
| Node Summary 延遲 | < 2 秒（P95） | `orient.thinking` WebSocket event latency 統計 | 部署後 1 週 |
| 測試通過率 | 100% | `make test` | 實作完成時 |
| Fallback 行為 | 未定義 task_type 時使用 CLAUDE_MODEL（Opus） | 單元測試覆蓋 | 實作完成時 |

> 若部署後 2 週內發現 Haiku 模型在 `node_summary` 或 `classify_vulnerability` 任務上品質不足（操作員回報或自動化品質檢測），應將對應任務升級至 Sonnet 並重新評估成本影響。

---

## 關聯（Relations）

- 取代：無
- 被取代：無
- 延伸：ADR-013（Orient Prompt Engineering Strategy）、ADR-005（PentestGPT Orient Engine）
- 參考：XBOW Model Alloys 技術、ADR-014（Anthropic SDK Migration）、ADR-024（MCP Architecture）
