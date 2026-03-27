# SPEC-022：Agent Capability Matching

> 結構完整的規格書讓 AI 零確認直接執行。

| 欄位 | 內容 |
|------|------|
| **規格 ID** | SPEC-022 |
| **關聯 ADR** | ADR-021 (Agent Capability Matching for C2 Execution) |
| **估算複雜度** | 中 |
| **建議模型** | Sonnet |
| **HITL 等級** | standard |

---

## 🎯 目標（Goal）

Replace the `LIMIT 1` agent lookup in `_execute_caldera()` with capability-aware selection that matches technique platform requirements and prefers the highest-privilege agent, eliminating silent wrong-agent execution failures.

---

## 📥 輸入規格（Inputs）

| 參數名稱 | 型別 | 來源 | 限制條件 |
|----------|------|------|----------|
| `db` | `aiosqlite.Connection` | Caller (engine router) | Active connection required |
| `operation_id` | `str` | Engine router context | Non-empty |
| `target_id` | `str` | Engine router context | Must reference a valid target row |
| `technique_id` | `str` | Technique execution request | e.g. `"T1003.001"` |

---

## 📤 輸出規格（Expected Output）

**成功情境：**

Returns `agent_paw: str` — the paw of the best-fit alive agent on the target, selected by highest privilege score among agents whose platform matches the technique's playbook platform requirement.

```
"abc123paw"
```

**失敗情境（returns `None`)：**

| 情境 | 回傳值 | 呼叫方處理方式 |
|------|--------|----------------|
| No agents registered on target | `None` | `_execute_caldera()` returns `failed` status |
| All agents on target are dead | `None` | `_execute_caldera()` returns `failed` status |
| No agent matches required platform | `None` | `_execute_caldera()` returns `failed` status |

---

## 🔗 副作用與連動（Side Effects）

| 副作用 | 觸發條件 | 影響模組 | 驗證方式 |
|--------|----------|----------|----------|
| `_execute_caldera()` agent selection 邏輯替換 | 任何 technique execution 呼叫 | `backend/app/services/engine_router.py` | pytest `test_agent_capability_matcher.py` 15 scenarios |
| 無 DB schema 變更 | — | `agents` 表既有查詢不受影響 | 既有測試全通過 |
| Agent 選擇失敗回傳 `None` | 無匹配 agent 時 | `_execute_caldera()` 回傳 `failed` status | Unit test 覆蓋 no_agent / all_dead / platform_mismatch |

---

## ⚠️ 邊界條件（Edge Cases）

- **No agents on target**: `select_agent_for_technique()` returns `None`
- **All agents dead**: Only alive agents (last_seen within threshold) are considered; returns `None` if none qualify
- **Multiple agents, same privilege**: Return any one deterministically (e.g., first by paw alphabetically or row insertion order)
- **No playbook entry for technique**: Skip platform filter entirely; return highest-privilege alive agent
- **Platform case-insensitive match**: `"Windows"` matches `"windows"`, `"WINDOWS"`, etc.

### 回退方案（Rollback Plan）

| 回滾步驟 | 資料影響 | 回滾驗證 | 回滾已測試 |
|----------|----------|----------|-----------|
| 1. Revert `AgentCapabilityMatcher` 及 `_execute_caldera()` 整合 commit | 無 DB schema 變動，無資料遺失 | `_execute_caldera()` 恢復為 `LIMIT 1` 查詢 | ✅ 可直接 revert |
| 2. 驗證 engine_router 正常執行 | 無不可逆變更 | `make test` 通過，technique 執行正常 | ✅ |

---

## 🧪 測試矩陣（Test Matrix）

| ID | 類型 | 場景 | 預期結果 | 場景參考 |
|----|------|------|----------|----------|
| P1 | 正向 | Target 有 2 個 alive agents（Admin + User），technique 需 windows 平台 | 選中 Admin agent（highest privilege） | Scenario: 多 agent 權限優先選擇 |
| P2 | 正向 | Target 有 1 個 alive agent，平台匹配 | 回傳該 agent paw | — |
| N1 | 負向 | Target 無任何 agent 註冊 | 回傳 `None`，`_execute_caldera()` 回傳 `failed` | Scenario: 無可用 agent |
| N2 | 負向 | 所有 agent 皆 dead（last_seen 過期） | 回傳 `None`，`_execute_caldera()` 回傳 `failed` | — |
| N3 | 負向 | Agent 平台與 technique 需求不匹配 | 回傳 `None` | — |
| B1 | 邊界 | 多個 agent 同權限等級 | 確定性回傳其中一個（按 paw 排序） | Scenario: 同權限 agent 確定性選擇 |
| B2 | 邊界 | Technique 無 playbook entry | 跳過平台 filter，回傳最高權限 alive agent | — |
| B3 | 邊界 | 平台大小寫不一致（"Windows" vs "windows"） | 正確匹配（case-insensitive） | — |

---

## 🎬 驗收場景（Acceptance Scenarios）

```gherkin
Feature: Agent Capability Matching
  Background:
    Given 已建立作戰 "OP-BRAVO"
    And 作戰包含 target "10.0.0.5"

  Scenario: 多 agent 權限優先選擇
    Given target 上註冊了 agent-A（privilege=SYSTEM, platform=windows, alive）
    And target 上註冊了 agent-B（privilege=User, platform=windows, alive）
    When 執行 technique T1003.001（platform=windows）
    Then 選中 agent-A（SYSTEM 權限最高）
    And Caldera API 收到 agent-A 的 paw

  Scenario: 無可用 agent
    Given target 上無任何已註冊 agent
    When 執行 technique T1003.001
    Then select_agent_for_technique 回傳 None
    And _execute_caldera 回傳 status="failed"
    And 錯誤訊息包含 "no suitable agent"

  Scenario: 同權限 agent 確定性選擇
    Given target 上有 agent-X（privilege=Admin, platform=windows, alive）
    And target 上有 agent-Y（privilege=Admin, platform=windows, alive）
    When 連續執行相同 technique 兩次
    Then 兩次皆選中同一 agent（確定性排序）
```

---

## 🔍 追溯性（Traceability）

| 類型 | 檔案路徑 | 說明 |
|------|----------|------|
| 後端 Service | `backend/app/services/agent_capability_matcher.py` | `AgentCapabilityMatcher` 主邏輯 |
| 後端 整合 | `backend/app/services/engine_router.py` | `_execute_caldera()` 呼叫 matcher |
| 後端 測試 | `backend/tests/test_agent_capability_matcher.py` | 15 個 unit test scenarios |
| E2E 測試 | （待實作） | 前端無直接 UI 對應 |

> 追溯日期：2026-03-26

---

## 📊 可觀測性（Observability）

### 後端

| 指標名稱 | 類型 | 標籤 | 告警閾值 |
|----------|------|------|----------|
| `athena_agent_match_duration_seconds` | Histogram | `operation_id`, `technique_id` | P95 > 500ms |
| `athena_agent_match_result` | Counter | `result` (`matched`, `no_agent`, `all_dead`, `platform_mismatch`) | `no_agent` > 5/min |
| `athena_agent_match_privilege_level` | Counter | `privilege` (`SYSTEM`, `Admin`, `User`) | — |

### 前端

N/A（無前端 UI 元件，純後端 service）

---

## ✅ 驗收標準（Done When）

- [x] `AgentCapabilityMatcher.select_agent_for_technique()` is implemented in `backend/app/services/`
- [x] 15 unit test scenarios pass covering: no agents, all dead, single agent, multi-agent same privilege, multi-agent mixed privilege, no playbook entry, platform case-insensitive match, and SYSTEM > Admin > User priority
- [x] `engine_router._execute_caldera()` uses `AgentCapabilityMatcher` instead of raw `LIMIT 1` query
- [x] `make test` passes with 187+ tests (zero regressions)
- [x] Explicit `failed` status returned when `select_agent_for_technique()` returns `None`

---

## 🚫 禁止事項（Out of Scope）

- 不要修改：`agents` table schema — no new columns or tables required
- 不要引入新依賴：no new pip packages; use existing `aiosqlite` and standard library only
- 不要實作：fine-grained capability metadata beyond `privilege` and `platform` fields (deferred to post-v0.2.0)

---

## 📎 參考資料（References）

- 相關 ADR：ADR-021 (Agent Capability Matching for C2 Execution)
- 現有類似實作：`backend/app/services/orient_engine.py` — `_execute_caldera()` method (current `LIMIT 1` pattern to be replaced)
- 外部文件：Caldera agent paw API docs

