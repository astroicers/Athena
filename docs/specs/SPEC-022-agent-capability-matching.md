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

| 本功能的狀態變動 | 受影響的既有功能 | 預期行為 |
|-----------------|----------------|---------|
| `_execute_caldera()` agent selection logic replaced | Engine router execution flow | Best-fit agent paw passed to Caldera API; explicit None triggers failed status |
| No DB schema changes | All existing queries against `agents` table | Unaffected |

---

## ⚠️ 邊界條件（Edge Cases）

- **No agents on target**: `select_agent_for_technique()` returns `None`
- **All agents dead**: Only alive agents (last_seen within threshold) are considered; returns `None` if none qualify
- **Multiple agents, same privilege**: Return any one deterministically (e.g., first by paw alphabetically or row insertion order)
- **No playbook entry for technique**: Skip platform filter entirely; return highest-privilege alive agent
- **Platform case-insensitive match**: `"Windows"` matches `"windows"`, `"WINDOWS"`, etc.

### 回退方案（Rollback Plan）

- **回退方式**：Revert the commit that introduces `AgentCapabilityMatcher` and updates `_execute_caldera()`. The previous `SELECT paw FROM agents ... LIMIT 1` query is restored.
- **不可逆評估**：No irreversible changes — no DB migrations, no external side effects.
- **資料影響**：None. No user data is altered by this change.

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
