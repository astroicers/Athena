# SPEC-064：Orient Engine 分析規則完整規格

| 欄位 | 內容 |
|------|------|
| **規格 ID** | SPEC-064 |
| **關聯 ADR** | ADR-005（OODA 架構）、ADR-013（Prompt Engineering）、ADR-039（Mission Profile）、ADR-045（OODA-native recon） |
| **估算複雜度** | 中 |
| **建議模型** | Sonnet |
| **HITL 等級** | standard |
| **狀態** | ✅ 已實作（補文件） |
| **完成日期** | 2026-05-02 |

---

## 🎯 目標

記錄 `orient_engine.py` 系統提示中 14 條分析規則的完整規格，以及配套機制：
- Mission Profile 噪音過濾（`_filter_options_by_noise`）
- Skill 動態注入（`skill_loader`）
- Operator Directive 一次性消費
- Section 7.10 Feasible Techniques（Rule #3 資料來源）

這份 SPEC 補全了「規則存在於程式碼但無文件記錄」的缺口，確保未來修改規則時有規格可對照。

---

## 背景

Orient Engine（`backend/app/services/orient_engine.py`）是 Athena OODA 循環的「Orient」階段，負責：
1. 從資料庫查詢 17 個動態 context sections（Q1–Q17）
2. 組合系統提示 + 使用者提示送給 LLM
3. 解析 LLM 的 JSON 回應（3 個技術選項 + 信心值）
4. 過濾超出任務噪音限制的選項
5. 將推薦結果持久化至 DB 並廣播 WebSocket 事件

---

## 規格

### 1. 系統提示架構

系統提示（`_ORIENT_SYSTEM_PROMPT`）包含 14 條規則，格式為 `### N. 規則名稱`：

| 規則 | 名稱 | 核心行為 | 資料來源 |
|------|------|---------|---------|
| #1 | Kill Chain Position | 參照 Section 3 判斷當前 ATT&CK 階段；不得跳過 | Section 3（server 端預計算） |
| #2 | Dead Branch Pruning | 技術失敗時排除同前提的兄弟技術，推薦不同 tactic | Section 7 failed_techniques + failure_category |
| #3 | Prerequisite Verification | 只推薦 Section 7.10 列出的可行技術 | Section 7.10 Feasible Techniques |
| #4 | Engine Routing | 優先推薦 Section 7.6 Playbook 中的技術 | Section 7.6/7.8/7.8.1 |
| #5 | Risk Calibration | 以偵測可能性而非影響力評估風險 | — |
| #6 | No Redundant Recommendations | 禁止推薦 Section 7 中已完成的技術 | Section 7 completed_techniques |
| #7 | Attack Graph Awareness | 優先推薦 Section 10 recommended_path 上的技術 | Section 10 |
| #7.5 | Prerequisite Sequencing (SPEC-058) | 不得在同 cycle 同時推薦 T1046 及依賴其結果的技術 | Section 6 categorized_facts |
| #8 | Recon-to-Initial Access Transition (SPEC-052/053) | 有開放埠但無憑證時推薦 IA 技術 | Section 6/7 |
| #9 | IA Exhausted → Exploit Pivot (SPEC-053/054/056) | auth_failure 後轉推 T1190 或多協議噴灑 | Section 7 failed_techniques |
| #10 | SSRF-to-IMDS Cloud Pivot (ADR-048) | SSRF 指標 + 雲端環境 → T1190 engine=mcp | Section 6/8 |
| #11 | Cloud Credential Lateral Movement (ADR-048) | cloud.aws.iam_credential 存在後推薦橫向移動 | Section 6 |
| #12 | AD Enumeration Chain | BloodHound 資料存在時優先 AD 攻擊路徑 | Section 7.8.2 |
| #13 | Kerberos Ticket Forge Priority | 根據哈希類型推薦最優 Kerberos 技術 | Section 7.8.2/7.5 |
| #14 | AD Persistence Timing | 僅在 is_compromised + 提權確認後推薦 AD 持久化 | Section 7 targets |

### 2. 使用者提示 Sections（Q10.5 新增）

| Section | 欄位名 | 內容 | 對應 DB 查詢 |
|---------|--------|------|------------|
| 1 | OPERATION BRIEF | 任務元資料 | Q1 |
| 2 | MISSION TASK TREE | 任務步驟樹 | Q6 |
| 3 | KILL CHAIN POSITION | 已執行 tactics + 當前/下一階段 | Q9 |
| 4 | OPERATIONAL HISTORY | 最近 3 次 OODA 摘要 | Q7 |
| 5 | PREVIOUS ASSESSMENTS | 最近 2 次 LLM 推薦 | Q8 |
| 6 | CATEGORIZED INTELLIGENCE | 事實庫（限 30 筆，5/類） | Q10 |
| 7 | ASSET STATUS | 目標/完成/失敗技術/Agent | Q2-Q5 |
| 7.5 | HARVESTED CREDENTIALS | 已收集憑證（限 10 筆） | Q11 |
| 7.6 | AVAILABLE TECHNIQUE PLAYBOOKS | 平台可執行技術清單 | Q12.1 |
| 7.7 | LATERAL MOVEMENT OPPORTUNITIES | 橫向移動機會 | Q12.2-Q12.3 |
| 7.8 | AVAILABLE MCP TOOLS | MCP 工具清單 | Q13 |
| 7.8.1 | AD DOMAIN INTELLIGENCE TOOLS | AD MCP 路由表 | Q12.4 |
| 7.8.2 | AD DOMAIN INTELLIGENCE SUMMARY | AD 事實彙總 | Q12.5 |
| 7.9 | INFRASTRUCTURE | relay_available + LHOST | 靜態（settings.RELAY_IP） |
| **7.10** | **FEASIBLE TECHNIQUES** | **Rule #3 前置條件已滿足的技術清單** | **Q10.5（attack_graph_engine.get_feasible_techniques）** |
| 8 | LATEST OBSERVE SUMMARY | 本次觀察摘要 | 傳入參數 |
| 8.5 | SECURITY SKILLS | 上次推薦技術對應的 Skill 內容 | Q16（skill_loader） |
| 8.9 | OPSEC STATUS | 偵測風險/噪音預算/暴露次數 | Q14（opsec_monitor） |
| 9 | OPERATOR DIRECTIVE | 操作者一次性指令（消費後標記） | Q17 |
| 10 | ATTACK GRAPH STATUS | 攻擊圖摘要 | rebuild() 回傳 |
| 11 | KNOWN VULNERABILITIES | 已確認 CVE | Q15 |

### 3. Mission Profile 噪音過濾（`_filter_options_by_noise`）

- 觸發時機：`analyze()` 回傳前，對 LLM 選項進行後處理
- 過濾邏輯：`NOISE_RANKS[tech_noise] <= NOISE_RANKS[max_noise]`
  - `NOISE_RANKS = {"low": 1, "medium": 2, "high": 3}`
  - `max_noise = "all"` 時跳過過濾（FA 任務模式）
- 邊際情況：若所有選項都被過濾，選噪音最低的一個並設 `noise_override: True`

### 4. Section 7.10 Feasible Techniques（Rule #3 資料來源）

- 呼叫：`AttackGraphEngine.get_feasible_techniques(current_fact_traits)`
- 邏輯：對 `_RULE_BY_TECHNIQUE`（technique_rules.yaml 載入）中每個 rule，若 `required_facts ⊆ current_facts`，則該技術可行
- 輸出格式：逗號分隔技術 ID 清單，或「none」提示
- 目的：讓 Rule #3 有具體資料支撐，而非依賴 LLM 訓練知識猜測

### 5. LLM 輸出合約

```json
{
  "situation_assessment": "string",
  "recommended_technique_id": "TXXXX.XXX",
  "confidence": 0.0,
  "reasoning_text": "string",
  "options": [
    {
      "technique_id": "TXXXX.XXX",
      "technique_name": "string",
      "reasoning": "string",
      "risk_level": "low|medium|high|critical",
      "recommended_engine": "ssh|c2|mcp|metasploit",
      "confidence": 0.0,
      "prerequisites": ["string"]
    }
  ]
}
```

- 固定 3 個 options，按 confidence 降序
- 每次呼叫 LLM 前後各 1 次噪音過濾

---

## 測試矩陣

| 場景 | 驗證方式 | 通過條件 |
|------|---------|---------|
| 無 facts 時 Section 7.10 | 模擬空 facts | 輸出「none — run T1595.001 first」 |
| 有 network.host.ip 時 | facts = {network.host.ip} | T1595.001, T1046, T1187 等出現在 Section 7.10 |
| CO 任務過濾 | max_noise=low，LLM 推薦 high 技術 | _filter_options_by_noise 排除 high 選項 |
| Rule #1 壓縮 | 讀取系統提示 | Rule #1 < 120 chars |
| SPEC-054 relay 壓縮 | 讀取系統提示 | relay block < 250 chars |

---

## 相依性

- `attack_graph_engine.py` → `get_feasible_techniques()` 靜態方法
- `technique_rules.yaml` → 72+ 條規則的 required_facts
- `mission_profile_loader.py` → `get_profile()`, `NOISE_RANKS`
- `skill_loader.py` → `load_skills()`
- `opsec_monitor.py` → `compute_status()`

---

## 風險

| 風險 | 說明 | 緩解 |
|------|------|------|
| Section 7.10 過長 | 若 facts 充足，feasible 清單可能數十個技術 | 未來可限制清單長度，或只列出 top-N by information_gain |
| Rule #3 過度嚴格 | LLM 可能被禁止推薦實際合理的技術（YAML 規則不完整） | YAML 持續維護；Rule #3 說明「有充分理由可偏離」 |

---

## 驗收條件

- [ ] `orient_engine.py` 系統提示 Rule #1 < 120 chars
- [ ] `orient_engine.py` SPEC-054 relay block < 250 chars  
- [ ] `_build_prompt()` 注入 Section 7.10（feasible_techniques_str）
- [ ] `attack_graph_engine.get_feasible_techniques()` 為公開靜態方法
- [ ] 空 facts → Section 7.10 回傳「none」提示
