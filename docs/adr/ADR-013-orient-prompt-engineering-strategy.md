# [ADR-013]: Orient Prompt 工程策略 — 借鏡開源滲透測試 AI 專案

| 欄位 | 內容 |
|------|------|
| **狀態** | `Accepted` |
| **日期** | 2026-02-26 |
| **決策者** | 專案負責人 |

---

## 背景（Context）

Phase 5.1 實作的 `orient_engine.py` 使用 40 行 `_ORIENT_PROMPT_TEMPLATE` 作為 LLM prompt，功能上可運作但戰術分析深度不足。研究 15+ 個開源滲透測試 AI 專案後，識別出 6 個可借鏡的 prompt 工程模式。

**現有 prompt 的 5 個結構性缺陷：**

1. **無任務樹**——`mission_steps` 表已存在但未被查詢注入 prompt，LLM 無法看見整體任務進度
2. **無跨迭代記憶**——每次 Orient 呼叫重建 prompt，LLM 不知道前幾輪建議了什麼、為什麼
3. **無 Kill Chain 推理指令**——未指示 LLM 依 MITRE ATT&CK 戰術進程（TA0001→TA0010）推理
4. **無分支修剪指令**——失敗技術以平面列表呈現，未指示 LLM 推斷防禦態勢並消除同類技術
5. **無 System Message**——角色設定與情境資料混在同一個 user message 中，未利用 Anthropic API 的 `system` 參數

**研究的 6 個開源 Prompt 工程模式：**

| # | 模式 | 來源專案 | 授權 | 核心概念 |
|---|------|----------|------|----------|
| 1 | 任務樹 / PTT | PentestGPT | MIT | 階層式任務追蹤 + 死分支修剪 |
| 2 | Action + Reflection 雙 prompt | hackingBuddyGPT | MIT | system/user 分離 + 事實列表狀態反思 |
| 3 | 角色合約 | autopentest-ai | Apache 2.0 | 明確工具邊界、輸入輸出合約、反模式列表 |
| 4 | MITRE ATT&CK 接地 | AttackGen / Threats2MITRE | GPL-3.0 / MIT | Kill chain 推理、戰術進程映射 |
| 5 | 三層記憶 | PentAGI | MIT | 長期記憶 + 工作記憶 + 情節記憶 |
| 6 | 圖驅動推理 | RedAmon | MIT | Neo4j 知識圖譜查詢注入 prompt context |

---

## 評估選項（Options Considered）

### 選項 A：全部 6 模式 + 新基礎設施

導入全部 6 個模式，包含 Pattern 6 的 Neo4j 圖資料庫和 Pattern 5 的 LLM 摘要壓縮器。

- **優點**：最大化推理深度；圖驅動推理可發現攻擊路徑中的隱性關聯
- **缺點**：需新增 Neo4j / pgvector 依賴；需多次 LLM 呼叫（壓縮器）；違反 SPEC-007 禁止事項（不加 LangChain / 複雜 RAG 管道）
- **風險**：開發時間 3-5 倍；架構複雜度大幅增加；POC 過度工程

### 選項 B：採用 5 模式（1, 2, 3, 4, 5 輕量版），純 SQL + prompt 改寫

僅借鏡 Pattern 1-5 的概念，全部用現有 SQLite 資料實現。Pattern 5 簡化為「近 3 輪 OODA 歷史 + 前 2 次建議」的 SQL 查詢，不需要 LLM 壓縮器或 vector store。

- **優點**：
  - 所有改動局限在 `orient_engine.py` 的 `_build_prompt()` + `_call_claude()` + `_call_openai()`
  - 零新依賴；利用 DB 已有的 `mission_steps`、`ooda_iterations`、`recommendations`、`techniques`、`facts` 表
  - `analyze()` 回傳格式不變，下游 `decision_engine.py` 和所有測試不受影響
  - 單次 LLM 呼叫（不增加 API 成本或延遲）
- **缺點**：無 Pattern 6 圖驅動推理（攻擊路徑關聯需人工推斷）
- **風險**：`_build_prompt()` 從 4 個 SQL 查詢增至 9 個，但 POC 規模（<20 OODA 迭代）下可忽略

### 選項 C：僅 system/user 分離 + 分類情報

最小化改動——只加 system message 和 facts 分類。

- **優點**：改動極小（~20 行）
- **缺點**：不解決任務樹、跨迭代記憶、kill chain 推理等核心缺陷；改善有限
- **風險**：戰術分析品質提升不明顯

---

## 決策（Decision）

我們選擇 **選項 B：採用 5 模式，純 SQL + prompt 改寫**，因為：

1. **Pattern 1（任務樹）** — `mission_steps` 表已存在，一個 `SELECT ... ORDER BY step_number` 即可注入
2. **Pattern 2（system/user 分離）** — `_call_claude()` 已支援 Anthropic Messages API，加 `"system"` key 只需 2 行
3. **Pattern 3（角色合約）** — 寫入 `_ORIENT_SYSTEM_PROMPT` 靜態常數，定義 5 個分析框架規則
4. **Pattern 4（MITRE 接地）** — `techniques` 表有 `tactic` 和 `tactic_id` 欄位，一個 JOIN 即可
5. **Pattern 5（輕量記憶）** — `ooda_iterations` LIMIT 3 + `recommendations` LIMIT 2，純 SQL

Pattern 6（圖驅動推理）延後至正式版——需要 Neo4j 或 SQLite 圖模擬層，超出 POC 範圍。

---

## 後果（Consequences）

**正面影響：**

- Orient 輸出獲得戰略連續性——LLM 看見作戰全局（過去→現在→未來）而非孤立快照
- Kill chain 推理指令強制 LLM 沿 TA0001→TA0010 進程思考，避免跳躍式建議
- 死分支修剪指令防止 LLM 在已知有 EDR 的環境重複推薦記憶體存取類技術
- 分類情報（credential / network / host）讓 LLM 優先考慮憑證類情報
- 前次建議注入防止 LLM 重複推薦剛失敗的相同戰術
- System message 分離穩定角色設定，不受動態 context 長度影響

**負面影響 / 技術債：**

- `_build_prompt()` 從 4 個 SQL 查詢增至 9 個（POC 規模可忽略）
- System prompt ~200 tokens 固定消耗（Claude 200K 上下文下微不足道）
- `_call_claude()` 和 `_call_openai()` 簽章變更（但僅 `_call_llm()` 呼叫它們，影響範圍小）
- Pattern 6 延後意味著攻擊路徑的隱性關聯（如 T1003.001 → T1558.003 pivot）需依賴 LLM 自行推斷

**後續追蹤：**

- [ ] SPEC-015：實作 prompt 升級的完整規格
- [ ] 未來 ADR：Pattern 6 圖驅動推理的正式版評估

---

## 關聯（Relations）

- 補充：ADR-005（PentestGPT Orient 引擎）——不取代，在其基礎上升級 prompt 品質
- 遵守：SPEC-007 禁止事項（不加 LangChain、不建複雜 RAG 管道）
- 參考：ADR-001（Claude 為主要 LLM）、ADR-003（Orient 在 OODA 引擎中的位置）
- 實作：SPEC-015（Orient Prompt 工程規格）
