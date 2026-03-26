# Agent Memory Profile — Agent 學習記憶

<!-- requires: global_core -->
<!-- optional: multi_agent, autopilot -->
<!-- conflicts: (none) -->

適用：跨 session 保留修復策略、團隊有效性、常見失敗模式。
載入條件：`mode: multi-agent` 或 `autopilot: enabled` 時自動載入

> **設計原則**：
> - 解決「Worker N+1 不知道 Worker N 嘗試過什麼」的問題
> - 兩層記憶：Session Memory（短期）+ Project Memory（永久）
> - Task Memory 已由交接單 artifacts 承擔，不需額外機制

---

## 記憶層級

| 層級 | 儲存位置 | 生命週期 | 用途 |
|------|----------|----------|------|
| **Task Memory** | 交接單 artifacts | 任務完成後可清理 | 單一任務的完整 context（由 handoff 模板承擔） |
| **Session Memory** | `.asp-agent-session.json` | 單一 session，結束時歸檔 | agent 分派狀態、活躍軌道、待處理交接單 |
| **Project Memory** | `.asp-agent-memory.yaml` | 永久，定期修剪 | 修復策略成功率、團隊有效性、常見失敗模式 |

---

## Session Memory 格式

```json
// .asp-agent-session.json（加入 .gitignore）
{
  "session_id": "session-20260324-1000",
  "started_at": "2026-03-24T10:00:00Z",
  "team_composition": {
    "scenario": "NEW_FEATURE_complex",
    "agents": ["arch", "spec", "dep-analyst", "tdd", "impl", "qa", "doc"]
  },
  "active_tracks": [
    { "id": "A", "task": "TASK-001", "agent": "impl-1", "status": "in_progress" },
    { "id": "B", "task": "TASK-002", "agent": "impl-2", "status": "completed" }
  ],
  "pending_handoffs": ["HANDOFF-20260324-003"],
  "current_pipeline_phase": "BUILD",
  "last_gate_passed": "G3",
  "escalations": []
}
```

---

## Project Memory 格式

```yaml
# .asp-agent-memory.yaml（加入 .gitignore）
version: 1

fix_strategies:
  - pattern: "null check missing"
    module: "src/auth/"
    domain: "null_safety"               # v3.1: 根因領域
    root_cause_class: "null_deref"      # v3.1: 根因細分
    strategy: "Add null guard + grep for similar unchecked paths"
    success_count: 3
    fail_count: 1
    recommended_agents: ["impl", "qa"]  # v3.1: 成功時的團隊
    last_used: "2026-03-25"

  - pattern: "race condition in cache"
    module: "src/store/"
    domain: "concurrency"               # v3.1: 根因領域
    root_cause_class: "race_condition"   # v3.1: 根因細分
    strategy: "Use mutex + verify with concurrent test"
    success_count: 1
    fail_count: 0
    recommended_agents: ["impl", "qa"]  # v3.1: 成功時的團隊
    last_used: "2026-03-20"

team_effectiveness:
  - scenario: "NEW_FEATURE_complex"
    team_used: ["arch", "spec", "tdd", "impl", "qa", "sec", "doc"]
    adjustments_made: ["added sec at G4 due to auth concern"]
    domains_encountered: ["auth", "null_safety"]  # v3.1: 遇到的領域
    outcome: "success"
    total_gate_retries: 1

common_failures:
  - module: "src/auth/"
    failure_type: "null_check"
    domain: "null_safety"               # v3.1: 根因領域
    frequency: 5
    last_occurrence: "2026-03-25"
    mitigation: "Always verify nullable fields before DB operations"
```

---

## 記憶讀寫規則

### 何時讀取

```
FUNCTION load_memory():
  // ─── Session 啟動時 ───
  IF exists(".asp-agent-session.json"):
    session = LOAD(".asp-agent-session.json")
    // 恢復 agent 分派狀態
    RESTORE(session.active_tracks)
    RESTORE(session.pending_handoffs)

  // ─── Project memory ───
  IF exists(".asp-agent-memory.yaml"):
    memory = LOAD(".asp-agent-memory.yaml")
    // 可用於 reassignment hint
    RETURN memory
  ELSE:
    RETURN empty_memory()
```

### 何時寫入

```
FUNCTION update_memory(event):

  MATCH event.type:

    "fix_applied":
      // 記錄修復策略結果
      strategy = find_or_create_strategy(event.pattern, event.module)
      strategy.domain = event.domain                    // v3.1
      strategy.root_cause_class = event.root_cause      // v3.1
      IF event.success:
        strategy.success_count += 1
        strategy.recommended_agents = event.team        // v3.1
      ELSE:
        strategy.fail_count += 1
      strategy.last_used = NOW()

    "task_completed":
      // 記錄團隊有效性
      record = {
        scenario: event.scenario,
        team_used: event.team,
        adjustments_made: event.dynamic_adjustments,
        domains_encountered: event.domains,             // v3.1
        outcome: event.outcome,
        total_gate_retries: event.gate_retries
      }
      memory.team_effectiveness.append(record)

    "failure_pattern":
      // 記錄常見失敗
      pattern = find_or_create_pattern(event.module, event.failure_type)
      pattern.domain = event.domain                     // v3.1
      pattern.frequency += 1
      pattern.last_occurrence = NOW()
      IF event.mitigation:
        pattern.mitigation = event.mitigation

  SAVE(".asp-agent-memory.yaml", memory)
```

### Reassignment 時查詢

```
FUNCTION get_memory_hint(task, failure_context):
  memory = load_memory()

  // 查找類似的修復策略
  similar = memory.fix_strategies.filter(
    s => s.module MATCHES task.scope AND
         s.pattern MATCHES failure_context.root_cause
  )

  IF similar:
    // 按成功率排序
    // Guard against division by zero (new strategy with no history)
    rate = LAMBDA s: s.success_count / (s.success_count + s.fail_count) IF (s.success_count + s.fail_count) > 0 ELSE 0.5
    best = similar.sort_by(rate).first
    RETURN {
      strategy: best.strategy,
      success_rate: best.success_count / (best.success_count + best.fail_count) IF (best.success_count + best.fail_count) > 0 ELSE 0.5,
      note: "From project memory — used {best.success_count} times successfully"
    }
  ELSE:
    RETURN { strategy: null, note: "No similar pattern in project memory" }
```

### 主動記憶檢查（v3.1）

> 在任務開始**之前**查詢記憶，而非僅在失敗時。由 `execute_bugfix()` Phase 2.7 呼叫。

```
FUNCTION proactive_memory_check(task_type, domain, module):
  memory = load_memory()

  result = {
    warnings: [],
    suggested_strategy: null,
    additional_agents: [],
    pre_scan_targets: []
  }

  // ─── 1. 模組歷史：這個 module 常出什麼問題？───
  module_failures = memory.common_failures.filter(
    f => f.module MATCHES module
  )
  IF module_failures:
    top = module_failures.sort_by(f => f.frequency, descending).first
    result.warnings.append(
      "⚠️ {module} 歷史上最常見：{top.failure_type}（{top.frequency} 次）— {top.mitigation}"
    )
    result.pre_scan_targets.append({
      pattern: top.failure_type,
      module: module,
      reason: "歷史高頻問題，修復前先確認是否仍存在"
    })

  // ─── 2. 領域策略：這類 bug 怎麼修最有效？───
  domain_strategies = memory.fix_strategies.filter(
    s => s.domain == domain AND (s.success_count + s.fail_count) > 0
  )
  IF domain_strategies:
    rate = LAMBDA s: s.success_count / (s.success_count + s.fail_count) IF (s.success_count + s.fail_count) > 0 ELSE 0.5
    best = domain_strategies.sort_by(rate, descending).first
    result.suggested_strategy = {
      strategy: best.strategy,
      success_rate: ROUND(rate(best) * 100),
      source: "歷史上對 [{domain}] 類問題的最佳策略"
    }
    // 低成功率警告
    avg_rate = AVG(rate(s) FOR s IN domain_strategies)
    IF avg_rate < 0.5:
      result.warnings.append(
        "🔴 [{domain}] 類問題的歷史成功率僅 {ROUND(avg_rate*100)}%，建議分配更多驗證資源"
      )

  // ─── 3. 團隊有效性：什麼團隊對這個領域最有效？───
  relevant_teams = memory.team_effectiveness.filter(
    t => t.scenario CONTAINS task_type AND domain IN (t.domains_encountered OR [])
  )
  IF relevant_teams:
    successful = relevant_teams.filter(t => t.outcome == "success")
    IF successful:
      all_agents = flatten(t.team_used FOR t IN successful)
      agent_freq = counter(all_agents)
      current_team = get_current_team()
      FOR agent, count IN agent_freq:
        IF count / LEN(successful) > 0.5 AND agent NOT IN current_team:
          result.additional_agents.append(agent)
    IF result.additional_agents:
      result.warnings.append(
        "📊 歷史數據顯示加入 {result.additional_agents} 後成功率更高"
      )

  RETURN result
```

---

## 記憶修剪

```
FUNCTION prune_memory(max_age_days=90):
  memory = load_memory()

  // 修剪過期的修復策略
  memory.fix_strategies = memory.fix_strategies.filter(
    s => days_since(s.last_used) < max_age_days
  )

  // 修剪過期的失敗模式
  memory.common_failures = memory.common_failures.filter(
    f => days_since(f.last_occurrence) < max_age_days
  )

  // team_effectiveness 永久保留（用於長期趨勢分析）

  SAVE(".asp-agent-memory.yaml", memory)
```

---

## 與其他 Profile 的關係

```
agent_memory.md
  ├── 整合 multi_agent.md（reassign 時查詢 fix_strategies）
  ├── 整合 autopilot.md（Phase 0 載入 memory）
  ├── 整合 escalation.md（P2 重新分派時提供 memory hint）
  └── 記錄來自 pipeline.md（品質門重試次數）
```
