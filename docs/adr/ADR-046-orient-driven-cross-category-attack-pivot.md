# [ADR-046]: Orient-Driven Cross-Category Attack Pivot

| 欄位 | 內容 |
|------|------|
| **狀態** | `Accepted` |
| **日期** | 2026-04-09 |
| **決策者** | Athena Core Team |

---

## 背景（Context）

Athena 的 OODA 循環在 Initial Access 階段的「攻擊路徑碰壁時自主切換」能力存在架構缺口。metasploitable2 demo 壓測時，使用者故意把 SSH 密碼改成不可猜值以驗證系統能否自主 pivot，實際結果：系統在 T1110.001（SSH brute force）失敗後反覆重推同一技術，沒有能力改走 exploit-based 路徑，即使該目標同時暴露了 vsftpd 2.3.4、Samba、UnrealIRCd、distccd 等已知可利用服務。

### 既有架構的三個具體限制

**1. Engine fallback chain 只支援同類別切換（ADR-037）**

`backend/app/services/engine_router.py` L53-63 定義：

```python
_FALLBACK_CHAIN: dict[str, list[str]] = {
    "mcp_ssh":    ["c2"],
    "metasploit": [],     # 無任何 fallback
    "c2":         ["mcp_ssh"],
    "mcp_recon":  [],
}
```

這是 credential/access-based 引擎之間的相互 fallback（mcp_ssh ↔ c2），是 SPEC-040（ADR-037 實作）刻意保留的「同類別」保守策略。跨類別（credential → exploit）從未納入設計。

**2. Orient 的失敗感知是 stateless plain-text**

`backend/app/services/orient_engine.py:600-608` 抓失敗技術時只：

```python
failed = await db.fetch(
    "SELECT te.technique_id, te.error_message "
    "FROM technique_executions te WHERE te.operation_id = $1 AND te.status = 'failed'",
    operation_id,
)
failed_str = "\n".join(
    f"- {r['technique_id']}: {r['error_message'] or 'failed'}" for r in failed
) or "None"
```

沒有 `failure_category`、沒有 target 對應、沒有 JOIN facts。傳給 LLM 的只是 plain text `"T1110.001: All SSH credentials failed"`。

ADR-013 Rule #2「Dead Branch Pruning」在 Orient system prompt 中聲明過「當技術失敗時推論原因並消除 sibling、推薦來自不同 tactic 的替代」——但實作上 LLM 收到的資訊量不足以做這種結構化推論，等於**紙上規則從未真正生效**。

**3. Rule #8（Recon→IA Transition）對 T1190 的觸發條件過窄**

`orient_engine.py` L176-188：

```
### 8. Recon-to-Initial Access Transition (SPEC-052)
When the intelligence shows:
- service.open_port facts with SSH (port 22), RDP (port 3389), WinRM (port 5985/5986), or FTP (port 21)
- No credential facts yet exist for those services
- Kill chain position is at TA0043 (Reconnaissance) or TA0007 (Discovery)
Then you SHOULD recommend Initial Access techniques as the natural next step:
- T1110.001 for SSH/RDP/WinRM
- T1078.001 if default credentials are likely
- T1190 for HTTP services with known vulnerabilities (CVE facts present)
```

T1190 的觸發條件被窄化到「HTTP services with known vulnerabilities (CVE facts present)」。但 Athena 目前沒有做主動 CVE 比對——vsftpd 2.3.4 banner 會寫入 `service.open_port` fact，但不會衍生 `vuln.cve` fact。結果 Rule #8 在 metasploitable2 場景**永遠不會推 T1190**，只會反覆推 T1110.001。

### 既有能力存在但沒被串起來

以下能力已經存在，沒被用上：

- `backend/app/data/exploitable_banners.yaml` 內含 vsftpd_2.3.4、UnrealIRCd、samba 3.0、distccd 的 banner signature
- `backend/app/services/engine_router.py:1083-1104` `_infer_exploitable_service()` 能從 `service.open_port` fact 用 lowercase substring 比對這些 signature
- `backend/app/clients/metasploit_client.py:36-41` `_EXPLOIT_MAP` 有 vsftpd / unrealircd / samba / winrm 的 module mapping
- `backend/app/services/engine_router.py:1174-1197` `_execute_metasploit` 成功後會寫 `credential.root_shell` fact 並升級 compromise

但這些能力只在 Orient 明確推薦 `engine="metasploit"` 時才會被觸發。Orient 不推、執行層就摸不到這條路。

### 相關現存決策的範圍界定

| 前提 ADR/SPEC | 涵蓋範圍 | 與本 ADR 的關係 |
|--------------|---------|----------------|
| **ADR-013** Orient Prompt Engineering | Dead-branch pruning 的概念與規則文字 | 本 ADR 把 ADR-013 聲明過但未實作的規則落地 |
| **ADR-037** Composite Confidence + Engine Fallback Chain | 同類別引擎 fallback（mcp_ssh ↔ c2） | 本 ADR 補足**跨類別 pivot**（credential → exploit） |
| **ADR-045 / SPEC-052** OODA-Native Recon and Initial Access | Recon 與 IA 搬進 OODA 循環 | 本 ADR 繼承 SPEC-052 路徑，並強化「IA 失敗後」的行為 |
| **ADR-020** Non-SSH Initial Access | Metasploit 作為獨立 IA 引擎的基礎 | 本 ADR 不改 metasploit 的能力邊界，只改觸發條件 |
| **ADR-033 / SPEC-037** Access Recovery and Credential Invalidation | credential 失效後的 re-entry 機制 | 本 ADR 的「IA exhausted → exploit」與 access recovery 語義相通：當一條路不通時改找另一條 |
| **SPEC-041** Metasploit Stabilization | metasploit 運行穩定度修復 | 本 ADR 的實作 SPEC-053 繼續在此基礎上把執行模式從 persistent session 改 one-shot |

### 使用者的明確期望

這個決策背後的需求來自 demo 敘事。演講 2026-05-07 要呈現的核心賣點是「AI 指揮官在攻擊受阻時自主切換武器」——這必須在 War Room Timeline 上可見：OODA #N 推 T1110 fail → OODA #N+1 Orient 看到失敗 + banner → **主動推 T1190**。如果 pivot 發生在執行層（`engine_router` 私下幫你換路徑），Timeline 看起來會像系統隨機換技術、Orient 的 Decide 階段沒有反應、C5ISR 儀表板沒有變化——**就失去演講的敘事**。

---

## 評估選項（Options Considered）

### 選項 A：執行層 Auto-Pivot

在 `engine_router._execute_single` 的 Initial Access 失敗分支後，直接呼叫 `_infer_exploitable_service()` + `_execute_metasploit()`，Orient 完全不知情。

- **優點**：
  - 實作成本最低（~30 行改動）
  - 不動 DB schema、不動 Orient prompt、不動 LLM context
  - 保證 metasploitable2 能端到端跑通
- **缺點**：
  - Timeline 上看起來像系統「越過 AI 做決策」——Orient Decide 階段沒有反應，C5ISR 沒有變化
  - 演講敘事徹底崩盤：我們要呈現的是 AI 指揮官的判斷，不是工程師預先埋好的 fallback
  - Orient 永遠學不到「這條路不通要換路」——每次都交給執行層處理
  - 隱藏了系統的真實決策能力缺口
- **風險**：
  - 一旦未來有更複雜的 pivot 需求（例如必須結合 credential harvesting），執行層 hardcode 會完全不夠用
  - 違反 OODA「Decide 階段才是決策中樞」的架構原則

### 選項 B：Orient-Driven Pivot + 結構化 Failure Awareness（推薦）

改 DB schema 新增 `technique_executions.failure_category` 欄位；Orient 查失敗技術時 JOIN targets、包含 failure_category；system prompt 的 Rule #8 放寬 T1190 觸發條件、新增 Rule #9「IA Exhausted → Exploit Pivot」明確規則；metasploit 執行改為 one-shot exploit-and-release mode 以符合「不維持 persistent shell」的意圖。

- **優點**：
  - Timeline 完整呈現「AI 看到失敗 → 讀情報 → 切換武器」敘事，直接對應演講賣點
  - 結構化 failure context 成為 first-class 能力——未來所有 pivot 規則都可以用 prompt 擴充
  - 正式落實 ADR-013 Rule #2 Dead-Branch Pruning（先前只停留在 prompt 文字）
  - Orient decision 仍然是 first-class 決策層，符合 OODA 架構原則
  - Metasploit one-shot mode 同時修掉 `SPEC-041` 遺留的 session 管理複雜度
- **缺點**：
  - 需要 DB schema migration（`failure_category` 欄位 + partial index）
  - Orient prompt 長度增加約 500 tokens（Rule #9 + structured failure 示例）——LLM 成本小幅上升
  - 需要維護 `_classify_failure()` 分類規則（字串 heuristic）
  - metasploit_client 重構涉及 `terminal.py` MSF 路徑的連動修改
- **風險**：
  - Orient 若誤判可能進入「連續推 T1190 fail 又推 T1190」的死循環——以 constraint_engine 的 noise budget + failed technique 計數作為既有 circuit breaker 緩解
  - `_classify_failure()` 的字串 heuristic 可能在某些 edge case 分類錯誤——以 `"unknown"` 作為安全 fallback

### 選項 C：混合（Orient 優先 + 執行層 Safety Net）

主路徑同選項 B，但增加「連續 N 輪 Orient 推不出能成功的技術」的偵測機制，觸發時 `engine_router` 自動找 banner 打 exploit，Timeline 標 `[system safety net]`。

- **優點**：
  - 平衡了「真 AI 決策」與「demo 保證能跑完」兩個目標
  - 在 Orient prompt 設計還不成熟時提供保險
- **缺點**：
  - 複雜度顯著高於選項 B（要定義「N 輪」、要判斷「能成功」、要維護兩套 pivot 路徑）
  - 測試矩陣膨脹（Orient 正常 vs Orient 無效 vs safety net 觸發三種路徑）
  - 本次演講 demo 的壓力測試場景很窄，safety net 幾乎不會被觸發——為低機率情境付出高維護成本
- **風險**：
  - 兩條 pivot 路徑並存會讓 Timeline 有時顯示 AI 決策、有時顯示 system safety net，敘事不一致
  - Safety net 反而可能掩蓋 Orient prompt 的真實缺陷，延後架構成熟

---

## 決策（Decision）

我們選擇 **選項 B：Orient-Driven Pivot + 結構化 Failure Awareness**。

具體實作範圍由 **SPEC-053** 定義，涵蓋：

1. **DB Schema**：`technique_executions` 表新增 `failure_category TEXT` 欄位 + partial index（migration 004）
2. **Engine Router**：新增 `_classify_failure()` helper，將所有執行路徑的失敗 error text 分類為 8 種 category，寫入 `technique_executions.failure_category`
3. **Orient Query**：`orient_engine.py:600-608` 改為 JOIN targets，讓 LLM context 看得到 `<technique> on <hostname> [<category>]: <error>` 格式
4. **Orient System Prompt**：
   - **Rule #8 放寬**：T1190 觸發條件從「HTTP services with known vulnerabilities (CVE facts present)」改為「any service matching known exploitable banner signature (CVE fact not required)」
   - **新增 Rule #9「Initial Access Exhausted → Exploit Pivot」**：明確描述「當 Section 7 Failed Techniques 有 `[auth_failure]` 類別的 T1110/T1078 on target X，且 facts 包含可利用 banner，你 MUST 推 T1190 on target X with engine=metasploit」。明確聲明為 Rule #6（No Redundant Recommendations）的 exception。
5. **Metasploit Client One-Shot Mode**：
   - 移除 `_run_exploit` 的 session reuse 邏輯
   - 30 秒 hardcoded poll 改為 `settings.METASPLOIT_SESSION_WAIT_SEC`（預設 60）
   - 成功取得 session 後立即執行 probe command、讀 output、`shell.stop()` 釋放
6. **Terminal Router**：偵測到 `credential.root_shell` fact 時重新呼叫對應 exploit 建立新 session 供 websocket 使用；websocket 關閉時再釋放
7. **OODA Pivot WebSocket Event**：`ooda_controller` 在偵測到跨類別 pivot 時 broadcast `ooda.pivot` 事件（含 from/to/reason），前端 Timeline 可消費顯示 pivot badge

**範圍外的決策**：
- Reverse shell 類 exploit 的 LHOST 自動偵測（samba usermap_script / UnrealIRCd 需要）——列為後續 ADR
- Attack graph dead-branch pruning 整合進 Orient 推薦——列為後續 ADR
- Constraint engine 使用結構化 failure 做決策——本 ADR 只讓 Orient 消費，constraint engine 暫不動
- 把密碼加入 `default_credentials.yaml`——明確**拒絕**，違反使用者「壓測 OODA 自主找路」的意圖

---

## 後果（Consequences）

**正面影響：**

- Demo 敘事骨幹完整：演講 Timeline 能清晰呈現「AI 碰壁 → 換武器」的決策過程
- Orient 失敗感知成為 first-class 能力：未來新的失敗類型只需要擴充 `_classify_failure` heuristic 和 prompt Rule，不需要改 DB schema 或 pipeline
- ADR-013 Rule #2 Dead-Branch Pruning 從紙上規則落地為可驗證的行為
- Metasploit one-shot mode 順便解決 SPEC-041 遺留的 session 管理問題——符合使用者「需要 shell 時重新建立」的意圖
- 跨類別 pivot 的擴充點從 hardcode 變成 prompt + heuristic，未來新增 pivot 規則成本低
- `failure_category` 欄位可直接用於監控儀表板、tech-debt 追蹤、root cause 分析

**負面影響 / 技術債：**

- DB schema 變更需要 migration，且既有環境要跑一次 `alembic upgrade head`
- Orient prompt token 成本微幅增加（估計 +500 tokens/iteration，佔整體 prompt < 5%）
- `_classify_failure()` 的字串 heuristic 是 best-effort 分類，極端 case 可能誤判為 `unknown`
- Rule #9 需要定期檢視——若 metasploitable2 的攻擊面改變，`exploitable_banners.yaml` signature 要同步更新
- `terminal.py` MSF 路徑 re-exploit 會造成每次連終端機都重打一次 exploit，對 metasploitable2 這種不穩定 lab 機器可能造成負擔
- **Tech Debt**：本 ADR 範圍未處理 constraint_engine 使用 `failure_category` 做決策——constraint_engine 仍只看 aggregate failure rate，無法做 per-technique 的死路判定

**後續追蹤：**

- [ ] SPEC-053 實作完成並通過端到端 demo 驗證
- [ ] 收集 `failure_category` 分布數據，確認 `_classify_failure` 的 heuristic 準確度（目標：`unknown` 比例 < 10%）
- [ ] 建立後續 ADR「Attack Graph Integration with Orient Recommendations」
- [ ] 建立後續 ADR「Reverse Shell LHOST Auto-Detection for Exploit Engine」
- [ ] 建立後續 ADR「Structured Failure Consumption by Constraint Engine」（把 `failure_category` 提供給 constraint_engine 的 react 邏輯使用）
- [ ] 建立後續 issue「MCP tool schema 系統化一致性框架」

---

## 成功指標（Success Metrics）

| 指標 | 目標值 | 驗證方式 | 檢查時間 |
|------|--------|----------|----------|
| SPEC-053 測試矩陣（8 個 case） | 100% pass | `make test-filter FILTER=spec053` | 實作完成時 |
| Gherkin 驗收場景（4 個） | 100% 通過 | SPEC-053 §驗收場景手動 + 自動 | 實作完成時 |
| 端到端 demo：metasploitable2 從 0 → Orient 自主推 T1190 → 拿到 root shell | 首次嘗試成功（或最多一次重試） | 手動 War Room 操作 | 實作完成時 |
| `failure_category = 'unknown'` 比例 | < 10% | SQL 彙總 `technique_executions` | 實作後一週 |
| Orient prompt token 增加量 | < 600 tokens / iteration | LLM call log | 實作完成時 |
| 端到端 demo 跑完不崩潰 | 前端無 crash、Autonomous 不回 Manual、Brief 產出 | 手動測試 | 實作完成時 |
| Rule #9 誤觸發率（沒 banner 卻推 T1190） | 0 次 | 人工審查 orient_summary | 實作後一週 |

**重新評估條件：**
- 若 `failure_category = 'unknown'` 比例持續 > 20%，代表 heuristic 不準，考慮改用 LLM 分類或結構化 error schema
- 若 Orient 連續 3 次進入 T1190 死循環（推 T1190 → fail → 又推 T1190），代表 constraint engine 的 circuit breaker 不夠——需要回來設計「per-technique 死路追蹤」
- 若演講前端到端 demo 無法穩定復現，退而採用選項 C 的 safety net 作為保險

---

## 關聯（Relations）

- **取代**：（無）
- **被取代**：（無）
- **參考**：
  - [ADR-003] OODA Loop Engine Architecture
  - [ADR-013] Orient Prompt Engineering Strategy（本 ADR 落實 Rule #2）
  - [ADR-020] Non-SSH Initial Access
  - [ADR-033] OODA Access Recovery and Credential Invalidation
  - [ADR-037] Composite Confidence Scoring and Engine Fallback Chain（本 ADR 補足跨類別 pivot）
  - [ADR-045] OODA-Native Recon and Initial Access
  - [SPEC-037] OODA Access Recovery Credential Invalidation
  - [SPEC-040] Composite Confidence Fallback Chain and Kill Chain Enforcer
  - [SPEC-041] Metasploit Stabilization and Access Recovery Completion
  - [SPEC-052] OODA-Native Recon and Initial Access
  - **[SPEC-053]** Orient-Driven Pivot and Metasploit One-Shot Exploit（本 ADR 的實作 SPEC）
  - **[SPEC-065]** failure_category 枚舉與 ooda.pivot 決策流（pivot 觸發機制完整規格）
  - **[SPEC-067]** exploitable_banners 結構與 MetasploitClient probe_cmd（exploit 選擇資料來源）
