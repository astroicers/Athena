---
name: asp-dispatch
description: |
  Multi-agent task dispatch — classify task, recommend team, plan parallel execution.
  Triggers: dispatch, assign, 分派, 指派, 組隊
---

# ASP Dispatch — 多 Agent 任務分派

## 前置條件

- `.ai_profile` 已設定 `mode: multi-agent`
- `task_orchestrator.md` + `multi_agent.md` 已載入

## 工作流

### Step 1: 讀取任務

讀取使用者需求，確認上下文完整。

### Step 2: 分類任務

執行 `classify_task(request)` (task_orchestrator.md Part B)：
- NEW_FEATURE / BUGFIX / MODIFICATION / REMOVAL / GENERAL

向使用者確認分類結果。

### Step 3: 推薦團隊

根據 `.asp/agents/team_compositions.yaml` 的場景表：

```bash
# 查看可用場景
cat .asp/agents/team_compositions.yaml
```

選擇匹配的場景，列出建議的 agent 角色清單。

### Step 4: 依賴分析（如 parallel: true）

如果場景標記 `parallel: true`：
1. 執行 `analyze_requirement()` 識別模組
2. 執行 `decompose()` 拆分子任務
3. 執行 `plan_parallel_execution()` 產生軌道規劃：
   - Level 0: 獨立根（完全並行）
   - Level 1+: 依賴前層（層內並行）
4. 檢查鎖衝突

### Step 5: 產生 Task Manifest

為每個子任務建立 Task Manifest（multi_agent.md 格式）：

```yaml
task_id: TASK-{NNN}
agent: {role_id}
scope:
  allow: [...]
  forbid: [...]
input:
  - docs/specs/SPEC-{NNN}.md
output:
  - {expected output files}
done_when: "{testable condition}"
track: {A|B|C|...}     # if parallel
level: {0|1|2|...}     # topological level
```

### Step 6: 分派

向使用者確認分派計劃，然後：
1. 鎖定 `.agent-lock.yaml`
2. 記錄到 `.asp-agent-session.json`
3. 輸出各 Worker 的啟動指引

## 參考

- 角色定義：`.asp/agents/*.yaml`
- 團隊組成：`.asp/agents/team_compositions.yaml`
- 管線階段：`.asp/profiles/pipeline.md`
- 任務分類：`.asp/profiles/task_orchestrator.md` Part B
