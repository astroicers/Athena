# [ADR-021]: Agent Capability Matching for C2 Execution

| 欄位 | 內容 |
|------|------|
| **狀態** | `Accepted` |
| **日期** | 2026-03-03 |
| **決策者** | Athena Engineering Team |

---

## 背景（Context）

`_execute_caldera()` currently uses `SELECT paw FROM agents ... LIMIT 1`, picking any alive agent regardless of privilege or platform. When multiple agents coexist on a target (e.g., one User-privilege and one SYSTEM), the wrong agent may be selected, causing technique execution to silently fail (e.g., T1003.001 LSASS dump requires SYSTEM privilege).

---

## 評估選項（Options Considered）

### 選項 A：Add `AgentCapabilityMatcher` service (Selected)

Select the highest-privilege agent matching the technique's required platform sourced from `technique_playbooks.platform`. Uses existing `agents.privilege` and `agents.platform` fields — no schema changes required.

- **優點**：No DB migration needed; reuses existing fields; explicit failure on no-match instead of silent wrong-agent execution
- **缺點**：Requires refactoring `_execute_caldera()` call site
- **風險**：Low — purely additive service layer

### 選項 B：Add a `capabilities JSON` column to agents table

Store richer capability metadata directly on the agent row.

- **優點**：More extensible for future capability dimensions
- **缺點**：Requires DB migration; over-engineered for v0.2.0 scope where privilege+platform fields already capture the needed signal
- **風險**：Migration risk; added complexity for minimal gain at this stage

---

## 決策（Decision）

We choose **Option A**. Add `AgentCapabilityMatcher` service that selects the highest-privilege agent matching the technique's required platform (sourced from `technique_playbooks.platform`).

Privilege priority: SYSTEM(3) > Admin(2) > User(1). If no playbook entry exists for a technique, the platform filter is skipped. No new DB columns or tables are required — the implementation uses existing `agents.privilege` and `agents.platform` fields.

---

## 後果（Consequences）

**正面影響：**
- No DB migration needed
- Engine router selects best-fit agent deterministically
- No-match returns explicit `failed` status instead of silent wrong-agent execution
- Platform filter is case-insensitive, reducing fragile string matching

**負面影響 / 技術債：**
- `_execute_caldera()` call site must be updated to use matcher
- Privilege priority ordering is hard-coded; may need revisiting if finer-grained roles are introduced

**後續追蹤：**
- [ ] Implement `AgentCapabilityMatcher.select_agent_for_technique()`
- [ ] Update `engine_router._execute_caldera()` to use matcher
- [ ] Write 15 unit test scenarios covering all edge cases (see SPEC-022)

---

## 成功指標（Success Metrics）

| 指標 | 目標值 | 驗證方式 | 檢查時間 |
|------|--------|----------|----------|
| `select_agent_for_technique()` unit tests | 15 scenarios pass | `make test-filter FILTER=capability_matcher` | 實作完成時 |
| Existing test suite | 187 tests continue to pass | `make test` | 實作完成時 |
| Wrong-agent silent failures | 0 occurrences | Integration test with mixed-privilege agents | QA 驗收時 |

---

## 關聯（Relations）

- 取代：（無）
- 被取代：（無）
- 參考：SPEC-022 (Agent Capability Matching implementation spec)
