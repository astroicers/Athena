# SPEC-037：OODA Access Recovery & Credential Invalidation

> 結構完整的規格書讓 AI 零確認直接執行。

| 欄位 | 內容 |
|------|------|
| **規格 ID** | SPEC-037 |
| **關聯 ADR** | ADR-033 |
| **估算複雜度** | 中 |

---

## 🎯 目標（Goal）

> 當 OODA Act 階段的 SSH 執行因認證失敗而失敗時，系統自動偵測存取中斷、標記憑證為失效、回退目標狀態，使後續迭代能正確切換至替代攻入路徑。

---

## 📥 輸入規格（Inputs）

| 參數名稱 | 型別 | 來源 | 限制條件 |
|----------|------|------|----------|
| result.error | string | ExecutionResult | SSH/MCP executor 回傳的錯誤訊息 |
| target_id | string (UUID) | technique_executions | 執行對象的 target ID |
| operation_id | string (UUID) | operations | 當前 operation ID |

**認證失敗關鍵字清單（觸發條件）：**

```python
_AUTH_FAILURE_KEYWORDS = [
    "authentication failed",
    "permission denied",
    "login incorrect",
    "access denied",
    "invalid credentials",
    "connection refused",
    "no route to host",
    "connection timed out",
    "host unreachable",
]
```

比對方式：`any(kw in (result.error or "").lower() for kw in _AUTH_FAILURE_KEYWORDS)`

---

## 📤 輸出規格（Expected Output）

**觸發 `_handle_access_lost()` 後的狀態變動：**

| 資料表 | 欄位 | 變更前 | 變更後 |
|--------|------|--------|--------|
| targets | is_compromised | 1 | 0 |
| targets | access_status | 'active' / 'unknown' | 'lost' |
| targets | privilege_level | 'User' / 'root' | NULL |
| facts | trait (credential) | 'credential.ssh' | 'credential.ssh.invalidated' |
| facts | (new row) | — | trait='access.lost', value='ssh_auth_failed:{target_ip}' |

**Orient Prompt 格式變更：**

```
# Before:
- target-001 (192.168.0.23) [server] OS=Linux COMPROMISED User

# After (access lost):
- target-001 (192.168.0.23) [server] OS=Linux ACCESS_LOST (was: User)
  ⚠ WARNING: Access lost — credential invalidated. Prioritize re-entry via alternative services.

# After (normal compromised):
- target-001 (192.168.0.23) [server] OS=Linux COMPROMISED(ACTIVE) User
```

---

## 🔗 副作用與連動（Side Effects）

| 說明 | 觸發條件 | 受影響模組 | 驗證方式 |
|------|---------|-----------|---------|
| targets.is_compromised 重設為 0 | SSH 認證失敗觸發 `_handle_access_lost()` | DecisionEngine target 選擇 | 確認 DecisionEngine 不再優先選擇 access_lost target |
| targets.access_status 設為 'lost' | SSH 認證失敗觸發 `_handle_access_lost()` | Orient prompt targets 區塊 | Orient prompt 顯示 ACCESS_LOST + 警告 |
| credential trait 改為 invalidated | SSH 認證失敗觸發 `_handle_access_lost()` | engine_router 憑證查詢、Attack Graph fact_traits | 確認 invalidated credential 被排除、依賴節點回退 UNREACHABLE |
| credential trait 改為 invalidated | SSH 認證失敗觸發 `_handle_access_lost()` | Orient categorized facts | 已失效 credential 不出現在 CREDENTIAL INTELLIGENCE |
| access.lost fact 插入 facts 表 | SSH 認證失敗觸發 `_handle_access_lost()` | Orient observe_summary | 確認 LLM 收到 access lost 事件 |
| access_status 恢復為 'active' | 重新取得存取（如 Metasploit exploit） | ooda_controller swarm/single 成功路徑 | 確認 `_mark_target_compromised` 正確恢復狀態 |

---

## ⚠️ 邊界條件（Edge Cases）

- **Case 1**：同一 target 有多組 credential（ssh + winrm）— 只 invalidate 失敗的 trait 類型
- **Case 2**：網路暫時中斷（非密碼更改）— `connection refused` / `timed out` 也觸發 access_lost，但後續迭代重新取得存取時會自動恢復（`_mark_target_compromised` 會重設 is_compromised=1）
- **Case 3**：Swarm 並行執行中多個 task 同時認證失敗 — `_handle_access_lost` 需要冪等（多次呼叫結果相同）
- **Case 4**：target 重新取得存取（例如透過 vsftpd backdoor 拿到 root shell）— 現有 `_mark_target_compromised()` 會設回 `is_compromised=1`，需同時更新 `access_status='active'`

### Rollback Plan

| 項目 | 內容 |
|------|------|
| **回退步驟** | 1. Revert commit(s) 2. `access_status` 欄位有 DEFAULT 值，DROP 後不影響既有資料 |
| **資料影響** | 回退後已 invalidated 的 credential trait 不會自動恢復；可透過 `UPDATE facts SET trait = REPLACE(trait, '.invalidated', '') WHERE trait LIKE '%.invalidated'` 手動修正 |
| **驗證方式** | `make test` 通過 + OODA 迭代不觸發 access recovery 邏輯 |
| **已測試** | 是（26/26 access recovery 測試通過 + 實機 Metasploitable2 驗證） |

---

## 🧪 測試矩陣（Test Matrix）

| ID | 類型 | 場景 | 預期結果 | 參考場景 |
|----|------|------|---------|---------|
| P1 | 正向 | SSH 認證失敗觸發 access recovery | targets.is_compromised=0, access_status='lost', credential invalidated | S1 |
| P2 | 正向 | Metasploit fallback 成功取回 root shell | access_status 恢復為 'active', privilege_level='Root' | S2 |
| P3 | 正向 | Terminal 透過 Metasploit session 下指令 | WebSocket 回傳正確 shell 輸出 | S2 |
| N1 | 負向 | 非認證失敗的錯誤（如語法錯誤） | 不觸發 access recovery | S1 |
| N2 | 負向 | invalidated credential 被 engine_router 排除 | _execute_via_mcp_executor 跳過 invalidated credential | S1 |
| B1 | 邊界 | 同一 target 多組 credential（SSH + WinRM） | 只 invalidate 失敗的 trait 類型 | S1 |
| B2 | 邊界 | Swarm 並行多 task 同時認證失敗 | `_handle_access_lost` 冪等執行，結果一致 | S1 |
| B3 | 邊界 | 所有 facts INSERT 為 INSERT OR IGNORE | 重複插入不拋 IntegrityError | S1, S2 |

---

## 🎬 驗收場景（Acceptance Scenarios）

```gherkin
Feature: OODA Access Recovery 與 Credential Invalidation
  Background:
    Given 存在一個活躍的 operation
    And 目標 192.168.0.23 已標記為 compromised（access_status='active'）
    And 存在有效的 SSH credential fact（trait='credential.ssh'）

  Scenario: SSH 認證失敗觸發 access lost 並 invalidate credential
    When OODA Act 階段的 SSH 執行回傳 "authentication failed"
    Then _handle_access_lost() 被觸發
    And targets.is_compromised 設為 0
    And targets.access_status 設為 'lost'
    And credential fact trait 改為 'credential.ssh.invalidated'
    And facts 表新增 trait='access.lost' 記錄
    And Orient prompt 顯示 ACCESS_LOST 狀態與警告訊息

  Scenario: Metasploit fallback 成功恢復存取
    Given 目標 access_status 為 'lost' 且 SSH credential 已 invalidated
    And 目標有 vsftpd 服務可被 Metasploit exploit
    When OODA 迭代透過 Metasploit engine 執行 vsftpd exploit
    Then exploit 成功取得 root shell
    And targets.is_compromised 設為 1
    And targets.access_status 恢復為 'active'
    And targets.privilege_level 設為 'Root'
    And facts 表新增 credential.root_shell fact

  Scenario: Terminal WebSocket 支援 Metasploit session fallback
    Given 目標透過 Metasploit 取得 shell session
    When 使用者透過 Terminal WebSocket 送出指令 "id"
    Then 回傳包含 "uid=0(root)" 的輸出
```

---

## 📎 追溯性（Traceability）

| 類型 | 路徑 | 說明 | 日期 |
|------|------|------|------|
| 後端實作 | `backend/app/services/engine_router.py` | 路由邏輯、`_handle_access_lost()`、Metasploit fallback、banner inference | 2026-03-26 |
| 後端實作 | `backend/app/services/orient_engine.py` | ACCESS_LOST prompt 修改、engine 選項 | 2026-03-26 |
| 後端實作 | `backend/app/services/attack_graph_engine.py` | invalidated fact 排除 | 2026-03-26 |
| 後端實作 | `backend/app/services/ooda_controller.py` | swarm 成功路徑 access_status / privilege_level 同步 | 2026-03-26 |
| 後端實作 | `backend/app/services/fact_collector.py` | INSERT OR IGNORE 修正 | 2026-03-26 |
| 後端實作 | `backend/app/clients/metasploit_client.py` | exploit 執行、session reuse | 2026-03-26 |
| 後端實作 | `backend/app/routers/terminal.py` | Terminal WebSocket Metasploit fallback | 2026-03-26 |
| 後端實作 | `backend/app/database/manager.py` | DB migration（access_status 欄位） | 2026-03-26 |
| 基礎設施 | `docker-compose.yml` | msfrpcd flag 修正 | 2026-03-26 |
| 後端測試 | `backend/tests/test_access_recovery.py` | 26 個 access recovery 測試 | 2026-03-26 |
| 後端測試 | `backend/tests/test_access_recovery_phases.py` | 多階段 recovery 測試 | 2026-03-26 |
| 後端測試 | `backend/tests/test_terminal.py` | Terminal Metasploit fallback 測試 | 2026-03-26 |
| 後端測試 | `backend/tests/test_metasploit_shell.py` | Metasploit shell session 測試 | 2026-03-26 |
| E2E 測試 | `frontend/e2e/full-workflow.spec.ts` | 完整紅隊工作流 | 2026-03-26 |
| E2E 測試 | `frontend/e2e/sit-ooda-lifecycle.spec.ts` | OODA 生命週期 SIT 測試 | 2026-03-26 |

---

## 📊 可觀測性（Observability）

| 層級 | 項目 | 說明 |
|------|------|------|
| 後端 Metrics | `access_lost_events_total` | access lost 事件累計次數（per operation） |
| 後端 Metrics | `credential_invalidation_total` | credential invalidation 累計次數 |
| 後端 Metrics | `metasploit_fallback_success_rate` | Metasploit fallback 成功率 |
| 後端 Logs | `WARNING: Access lost for target {target_id}` | access lost 觸發 log |
| 後端 Logs | `INFO: Credential invalidated: {trait}` | credential invalidation log |
| 後端 Logs | `INFO: Metasploit fallback succeeded for {target_id}` | fallback 成功 log |
| 後端 Alerts | 同一 operation 連續 3+ 次 access lost | 可能的系統性認證問題 |
| 後端故障偵測 | `_handle_access_lost()` 拋出未預期 exception | 監控 error log，確保冪等性 |
| 前端 | N/A | 前端透過 Orient prompt 被動接收狀態變更 |

---

## ✅ 驗收標準（Done When）

### Phase 1 — 被動偵測與 Access Lost（commit f6f7e7f）

- [x] `_handle_access_lost()` 在 SSH 認證失敗時正確觸發
- [x] 觸發後 `targets.is_compromised` = 0, `access_status` = 'lost'
- [x] 觸發後 credential trait 改為 `credential.ssh.invalidated`
- [x] `_execute_via_mcp_executor` 不使用 invalidated credential
- [x] Orient prompt 顯示 `ACCESS_LOST` 狀態與警告
- [x] Attack Graph 將依賴 invalidated credential 的節點標記為 UNREACHABLE
- [x] 重新取得存取時 `access_status` 恢復為 'active'

### Phase 2 — Metasploit Fallback Routing（commits 06e536f, e9f5325）

- [x] engine_router 尊重 `engine="metasploit"` 指定，直接走 Metasploit 路由
- [x] `_infer_exploitable_service()` 從 `service.open_port` banner 推斷可利用服務
- [x] 無有效憑證時仍寫入 `technique_executions` 記錄（Orient 可見）
- [x] ooda_controller swarm/single 成功路徑同步 `access_status='active'`
- [x] 所有 `INSERT INTO facts` 改為 `INSERT OR IGNORE`（修復 IntegrityError 導致 swarm 失敗）
- [x] Orient prompt 列出 `metasploit` engine 選項與 engine 選擇指南

### Phase 3 — Metasploit Exploit 執行與 Terminal Fallback

| Bug | 描述 | 修復 | Commit |
|-----|------|------|--------|
| Bug 12 | msfrpcd `-u` flag 設定 URI 而非 username | `-u` → `-U` (uppercase) | 853cab1 |
| Bug 13 | `exploit_vsftpd` 傳不支援的 LHOST 選項 | 移除 LHOST（bind shell 不需要） | 144449c |
| Bug 14 | `ShellSession.run_with_output()` API 不相容 | 改用 `shell.write/read` | 484797b |
| Bug 15 | vsftpd 只開一個 session，後續 exploit 找不到「新」session | 新增 session reuse（同 target_host） | 637d5b6 |
| Bug 16 | Metasploit 成功後未更新 target 為 Root | 寫入 `privilege_level='Root'` + `credential.root_shell` fact | 144449c |
| Bug 17 | ooda_controller 成功路徑覆蓋 Root → User | SQL CASE WHEN 保留 Root | bd39b62 |
| Bug 18 | Terminal WebSocket 僅支援 SSH | 新增 Metasploit shell session fallback | 1f0b58e |

- [x] `make test` 全數通過（467 passed，5 pre-existing failures）
- [x] 26/26 access recovery 測試通過
- [x] 實際 Metasploitable2 測試：vsftpd exploit → root shell → `uid=0(root)`
- [x] Terminal 可透過 Metasploit session 下指令

---

## 🚫 禁止事項（Out of Scope）

- 不要實作主動 Health Check（已在 ADR-033 決策為被動偵測）
- 不要新增 facts 表的 `is_valid` 欄位
- 不要修改 OODA 迭代間隔或 Orient 的 JSON output schema
- 不要引入新依賴

---

## 📎 參考資料（References）

- 相關 ADR：ADR-033、ADR-003、ADR-004、ADR-019（Metasploit RPC）
- 現有類似實作：`_mark_target_compromised()` in engine_router.py
- 關鍵檔案：
  - `backend/app/services/engine_router.py` — 路由邏輯、Metasploit fallback、banner inference
  - `backend/app/services/orient_engine.py` — prompt 修改、engine 選項
  - `backend/app/services/attack_graph_engine.py` — fact 排除
  - `backend/app/services/ooda_controller.py` — swarm 成功路徑 access_status / privilege_level
  - `backend/app/services/fact_collector.py` — INSERT OR IGNORE
  - `backend/app/clients/metasploit_client.py` — exploit 執行、session reuse
  - `backend/app/routers/terminal.py` — Terminal WebSocket Metasploit fallback
  - `backend/app/database.py` — DB migration
  - `docker-compose.yml` — msfrpcd flag 修正
  - `backend/tests/test_access_recovery.py` — 26 個測試

