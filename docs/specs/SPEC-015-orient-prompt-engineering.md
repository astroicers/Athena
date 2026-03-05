# SPEC-015：Orient Prompt 工程升級

> 借鏡 PentestGPT、hackingBuddyGPT、autopentest-ai、AttackGen、PentAGI 等開源專案的 prompt 工程模式，升級 `orient_engine.py` 的 LLM prompt 結構，提升戰術分析深度。

| 欄位 | 內容 |
|------|------|
| **規格 ID** | SPEC-015 |
| **關聯 ADR** | ADR-013（Orient Prompt 策略）、ADR-005（PentestGPT Orient 引擎） |
| **估算複雜度** | 中 |
| **建議模型** | Sonnet |
| **HITL 等級** | standard |

---

## 🎯 目標（Goal）

> 將 `orient_engine.py` 的 40 行單一 prompt 升級為結構化的 system + user 雙 prompt 架構，融入 5 個開源 prompt 工程模式：(1) 任務樹注入、(2) system/user 分離與角色合約、(3) Kill Chain 戰術推理、(4) 輕量三層記憶、(5) 分類情報注入。外部介面 `analyze()` 回傳結構不變，`MOCK_LLM=true` 路徑不受影響。

---

## 📥 輸入規格（Inputs）

| 參數名稱 | 型別 | 來源 | 限制條件 |
|----------|------|------|----------|
| `operation_id` | str | caller | 已存在的作戰 ID |
| `observe_summary` | str | `fact_collector.summarize()` | <= 1000 chars |
| `MOCK_LLM` | bool | config | true = 直接回傳 `_MOCK_RECOMMENDATION`，不呼叫 `_build_prompt()` |

**新增查詢的 DB 表（全部已存在於 `database.py`）：**

| 表 | 使用欄位 | 用途 | Pattern |
|----|----------|------|---------|
| `mission_steps` | step_number, technique_name, status, technique_id, engine, target_label | 任務樹注入 | 1 |
| `ooda_iterations` | iteration_number, observe_summary, act_summary, completed_at | 工作記憶（近 3 輪） | 5 |
| `recommendations` | situation_assessment, recommended_technique_id, reasoning_text | 情節記憶（前 2 次） | 5 |
| `techniques` | tactic, tactic_id（JOIN technique_executions） | Kill Chain 戰術進程 | 4 |
| `facts` | category, trait, value | 分類情報 | 2 |

---

## 📤 輸出規格（Expected Output）

### 1. `_ORIENT_SYSTEM_PROMPT`（靜態常數，~200 tokens）

角色合約 + 5 個分析框架指令：

```
You are the Orient phase intelligence advisor for Athena C5ISR cyber operations platform.
Your role: analyze the current operational situation and produce actionable tactical
recommendations for the commander.

Your analytical framework:

1. KILL CHAIN PROGRESSION — reason through MITRE ATT&CK tactic stages in order:
   TA0001 (Initial Access) → TA0002 (Execution) → TA0003 (Persistence) →
   TA0004 (Privilege Escalation) → TA0005 (Defense Evasion) →
   TA0006 (Credential Access) → TA0007 (Discovery) →
   TA0008 (Lateral Movement) → TA0009 (Collection) → TA0010 (Exfiltration)
   Ask: "What stage are we at? What is the logical next stage?"

2. NEGATIVE BRANCH PRUNING — when a technique has failed, infer WHY and eliminate
   the entire sub-branch. Example: if T1003.001 (LSASS) failed, consider that EDR
   may be active — avoid other memory-access techniques; pivot to token manipulation
   or living-off-the-land.

3. PREREQUISITE VERIFICATION — only recommend techniques whose prerequisites are
   confirmed by the collected intelligence (credentials, privilege level, compromised hosts).

4. ENGINE ROUTING — prefer Caldera for standard MITRE techniques with known ability IDs;
   recommend Shannon only for adaptive execution in unknown defensive environments.

5. RISK CALIBRATION — assign risk_level based on detection likelihood, not just impact:
   low = living-off-the-land, medium = known-bad tools (Mimikatz),
   high = noisy lateral movement, critical = destructive/exfiltration operations.

Output format: respond with ONLY valid JSON matching the specified schema.
No markdown, no explanation outside the JSON.
```

### 2. `_ORIENT_USER_PROMPT_TEMPLATE`（動態，per-call 組裝）— 8 段落

```
## OPERATION BRIEF
Code: {op_code} | Codename: {op_codename}
Strategic Intent: {strategic_intent}
Status: {status} | Threat Level: {threat_level} | Iteration: {iteration_count}

## MISSION TASK TREE
{mission_task_tree}

## KILL CHAIN POSITION
Tactics completed: {executed_tactics}
Current stage: {current_stage}

## OPERATIONAL HISTORY (last 3 cycles)
{ooda_history}

## PREVIOUS ORIENT ASSESSMENTS (last 2)
{previous_assessments}

## CURRENT INTELLIGENCE
CREDENTIAL INTELLIGENCE:
{credential_facts}

NETWORK INTELLIGENCE:
{network_facts}

HOST INTELLIGENCE:
{host_facts}

SERVICE INTELLIGENCE:
{service_facts}

## ASSET STATUS
Targets:
{targets}

Active Agents:
{agents}

## LATEST OBSERVE SUMMARY
{observe_summary}

## COMPLETED TECHNIQUES
{completed_techniques}

## FAILED TECHNIQUES (infer defensive posture from these)
{failed_techniques}

## REQUIRED OUTPUT
Provide exactly 3 tactical options as JSON:
{{
  "situation_assessment": "2-3 sentence tactical summary",
  "recommended_technique_id": "TXXXX.XXX",
  "confidence": 0.0-1.0,
  "reasoning_text": "chain-of-thought: why this technique NOW given history and pruned branches",
  "options": [
    {{
      "technique_id": "TXXXX.XXX",
      "technique_name": "Full MITRE Name",
      "reasoning": "why this option fits current kill chain stage",
      "risk_level": "low|medium|high|critical",
      "recommended_engine": "caldera|shannon",
      "confidence": 0.0-1.0,
      "prerequisites": ["confirmed prerequisites from intelligence"]
    }}
  ]
}}
Order by confidence descending.
```

### 3. 簽章變更

```python
# _build_prompt 回傳 tuple
async def _build_prompt(self, db, operation_id, observe_summary) -> tuple[str, str]

# _call_* 接收雙參數
async def _call_llm(self, system_prompt: str, user_prompt: str) -> str
async def _call_claude(self, system_prompt: str, user_prompt: str) -> str
async def _call_openai(self, system_prompt: str, user_prompt: str) -> str
```

### 4. API 呼叫變更

Claude — 新增 `system` 參數：
```python
json={
    "model": settings.CLAUDE_MODEL,
    "max_tokens": 4000,
    "temperature": 0.7,
    "system": system_prompt,
    "messages": [{"role": "user", "content": user_prompt}],
}
```

OpenAI — system message 前置：
```python
"messages": [
    {"role": "system", "content": system_prompt},
    {"role": "user", "content": user_prompt},
]
```

---

## ⚠️ 邊界條件（Edge Cases）

| 情況 | 處理方式 |
|------|----------|
| `MOCK_LLM=true` | `analyze()` 提前返回 `_MOCK_RECOMMENDATION`，不呼叫 `_build_prompt()` — 無影響 |
| 第一次 OODA 迭代（無歷史） | 歷史段落 = 「No prior cycles — first iteration.」 |
| `mission_steps` 為空 | 任務樹段落 = 「No mission steps defined.」 |
| `techniques` JOIN 無結果 | 戰術進程 = 「None yet — initial reconnaissance stage.」 |
| `facts` 為空 | 各分類情報 = 「No intelligence collected.」 |
| Token 預算 | 歷史 LIMIT 3、建議 LIMIT 2、情報每類 LIMIT 5，總計 ~1500 tokens user prompt + ~200 tokens system |
| LLM 回傳缺少欄位 | 現有 Phase 9.0 schema 驗證邏輯不變（fallback 至 `_MOCK_RECOMMENDATION`） |
| `_call_openai()` system message | OpenAI Chat Completions 原生支援 `role: "system"` — 無 API 變更 |
| `analyze()` 回傳格式 | **完全不變** — 下游 `decision_engine.py`、`ooda_controller.py` 不受影響 |

---

## ✅ 驗收標準（Done When）

- [x] `_ORIENT_SYSTEM_PROMPT` 常數定義，含 5 個分析框架指令
- [x] `_ORIENT_USER_PROMPT_TEMPLATE` 取代 `_ORIENT_PROMPT_TEMPLATE`，含 8 個段落
- [x] `_build_prompt()` 回傳 `tuple[str, str]`
- [x] `_build_prompt()` 查詢 `mission_steps`（任務樹）
- [x] `_build_prompt()` 查詢 `ooda_iterations` LIMIT 3（工作記憶）
- [x] `_build_prompt()` 查詢 `recommendations` LIMIT 2（情節記憶）
- [x] `_build_prompt()` 查詢 `techniques` JOIN `technique_executions`（Kill Chain 進程）
- [x] `_build_prompt()` 查詢 `facts` 並按 `category` 分組
- [x] `_call_claude()` 使用 Anthropic API `system` 參數
- [x] `_call_openai()` 前置 `{"role": "system", ...}` message
- [x] `MOCK_LLM=true` 路徑不受影響 — 現有 SPEC-007 測試全過
- [x] 新增 5 個 prompt 結構測試（`test_spec_007_ooda_services.py`）
- [x] `make lint` 無錯誤

---

## 🚫 禁止事項（Out of Scope）

- 不加 LangChain — 遵守 SPEC-007 禁止事項
- 不加 Neo4j 或圖資料庫 — Pattern 6 延後至正式版
- 不改 `analyze()` 回傳 dict 結構 — 下游不變
- 不改 `_MOCK_RECOMMENDATION` — SPEC-007 測試依賴此常數
- 不改 `database.py` — 不新增 table 或 column
- 不實作多輪 LLM 對話 — 維持單次呼叫（每次 Orient 一次 API call）
- 不實作 LLM 摘要壓縮器 — 用 SQL LIMIT 代替

---

## 📎 參考資料（References）

- ADR-013：[Orient Prompt 工程策略](../adr/ADR-013-orient-prompt-engineering-strategy.md)
- ADR-005：[PentestGPT Orient 引擎](../adr/ADR-005-pentestgpt-orient-engine.md)
- ADR-003：[OODA 引擎架構](../adr/ADR-003-ooda-loop-engine-architecture.md)
- SPEC-007：[OODA 循環引擎](SPEC-007-ooda-loop-engine.md)

**借鏡開源專案：**

| 專案 | 授權 | 借鏡模式 |
|------|------|----------|
| [PentestGPT](https://github.com/GreyDGL/PentestGPT) | MIT | Pattern 1: 任務樹 / PTT |
| [hackingBuddyGPT](https://github.com/ipa-lab/hackingBuddyGPT) | MIT | Pattern 2: Action + Reflection |
| [autopentest-ai](https://github.com/bhavsec/autopentest-ai) | Apache 2.0 | Pattern 3: 角色合約 |
| [AttackGen](https://github.com/mrwadams/attackgen) | GPL-3.0 | Pattern 4: MITRE 接地（研究參考） |
| [Threats2MITRE](https://github.com/LiuYuancheng/Threats_2_MITRE_AI_Mapper) | MIT | Pattern 4: Kill Chain 映射 |
| [PentAGI](https://github.com/vxcontrol/pentagi) | MIT | Pattern 5: 三層記憶 |
