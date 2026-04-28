# Multi-Agent Orchestration Profile

<!-- requires: global_core, system_dev -->
<!-- optional: guardrail, autonomous_dev -->
<!-- conflicts: (none) -->

適用：並行任務分治、大型功能拆解、自動化 CI/CD 整合。
載入條件：`mode: multi-agent`

> **與 committee 模式的區別**：
> - `multi-agent`：實作期使用。需求已確定，拆分為並行子任務加速執行。
> - `committee`：決策期使用。需求模糊或風險高，多角色辯論後才進入實作。

---

## v3.0 角色制與協作協議

> **v3.0 升級**：通用 Worker 升級為 10 個專精角色（4 部門）。
> 角色定義見 `.asp/agents/*.yaml`，團隊組成見 `.asp/agents/team_compositions.yaml`。
>
> **Context 全量傳遞**：agent 間交接使用結構化交接單（`.asp/templates/handoff/`），
> 不摘要、不壓縮，確保新 agent 取得完整上下文。

### 角色分派

Orchestrator 根據 `team_compositions.yaml` 選擇角色，取代通用 Worker-a/Worker-b：

```
FUNCTION assign_roles(task_type, complexity, current_depth=0):
  scenario = match_scenario(task_type, complexity)  // from team_compositions.yaml
  team = scenario.agents
  FOR role IN team:
    role_def = LOAD(".asp/agents/{role}.yaml")
    VALIDATE role_def.scope_constraints
    enforce_spawn_depth(role_def, current_depth)  // 深度超限時拋出 STOP
  RETURN team

// Workers 呼叫 assign_roles 時必須傳入 current_depth + 1
// Orchestrator 頂層呼叫傳 current_depth=0（不受限制）
// Worker 頂層呼叫傳 current_depth=1 → enforce_spawn_depth 攔截再次派生
```

---

## Orchestrator 職責

開始並行任務前，必須完成：

```
1. 讀取 docs/architecture.md 與 docs/adr/ 確認現況
2. 將需求拆解為低耦合子任務
3. 為每個子任務定義 Task Manifest（見下）
4. 建立 .agent-lock.yaml 登記文件鎖定
5. 指派 Worker，設定 Done Definition（呼叫 assign_roles(type, complexity, current_depth=0)）
```

> **深度追蹤規則**：Orchestrator 是唯一以 `current_depth=0` 呼叫 `assign_roles` 的角色。
> Worker 若需派生子 agent（如 impl 呼叫 Task 工具），必須以 `current_depth=1` 呼叫，
> `enforce_spawn_depth` 會在此層攔截並要求上報 Orchestrator，而非繼續遞迴。

### Task Manifest 格式

```yaml
task_id: TASK-001
agent: worker-a
scope:
  allow:  [src/store/, src/api/routes.go]
  forbid: [src/auth/, src/config/]
input:
  - docs/specs/SPEC-XXX.md
output:
  - src/store/feature_x.go
  - tests/store/feature_x_test.go
done_when: "make test-filter FILTER=feature_x 全數通過"
    agent_role: impl          # NEW: role from .asp/agents/
    track: A                  # NEW: parallel track identifier
    level: 0                  # NEW: topological level (0=independent)
```

---

## 文件鎖定（防衝突）

Orchestrator 維護 `.agent-lock.yaml`，Worker 修改任何檔案前必須確認未被鎖定。

```yaml
# .agent-lock.yaml
locked_files:
  src/store/user.go:
    by: worker-a
    task: TASK-001
    since: 2025-01-15T10:00:00Z
    expires: 2025-01-15T12:00:00Z   # 超時自動解鎖
    track: A              # NEW: 軌道標識
    level: 0              # NEW: 拓撲層級
    lock_type: exclusive  # NEW: exclusive | shared-read
```

```bash
make agent-unlock FILE=src/store/user.go   # 正常完成後解鎖
make agent-lock-gc                          # 清理逾時鎖定（> 2 小時視為異常）
```

### Lock GC 自動化

在 `Makefile` 中加入自動觸發：

```bash
# Makefile 新增
agent-lock-gc:
	@echo "清理逾時 agent locks..."
	@python3 -c " \
	import yaml, datetime; \
	data = yaml.safe_load(open('.agent-lock.yaml')) or {}; \
	now = datetime.datetime.now(datetime.timezone.utc); \
	expired = [f for f, v in (data.get('locked_files') or {}).items() \
	           if datetime.datetime.fromisoformat(v['expires']) < now]; \
	[data['locked_files'].pop(f) for f in expired]; \
	yaml.dump(data, open('.agent-lock.yaml', 'w')); \
	print(f'  已清理 {len(expired)} 個逾時鎖定') if expired else print('  無逾時鎖定')"
```

**自動觸發時機**：
- Orchestrator 每次輪詢 `completed.jsonl` 時，同時執行 `make agent-lock-gc`
- SessionStart hook 可選擇性加入 lock GC

---

## 事件 Hook 與驗證流程

Worker 完成任務後，**禁止靜默完成**，必須觸發 Hook：

```bash
make agent-done TASK=TASK-001 STATUS=success
make agent-done TASK=TASK-001 STATUS=failed REASON="測試未通過：TestUserCreate"
```

Orchestrator 輪詢 `.agent-events/completed.jsonl`（每分鐘一次），收到事件後執行：

```
FUNCTION on_worker_done(event, lock_registry):
  MAX_RETRIES = 2

  task   = event.task_id
  scope  = task.manifest.scope

  // 獨立驗證 — 不信任 Worker 自報
  test_result = EXECUTE("make test-filter FILTER={scope.filter}")

  IF test_result.passed:
    lock_registry.unlock(task.locked_files)
    IF autonomous_enabled:
      LOG("✅ {task} 驗證通過，自動合併至工作分支")
      // autonomous 模式：Orchestrator 可自主合併到工作分支（非主分支）
    ELSE:
      NOTIFY orchestrator("✅ {task} 驗證通過，待人工確認合併")
      AWAIT human_confirm("merge")
  ELSE:
    // autonomous 模式下 Worker 應已自行 auto_fix_loop
    // 到此表示 Worker 已耗盡重試
    IF task.retry_count < MAX_RETRIES:
      task.retry_count += 1
      reassign(task, reason = test_result.failures)
    ELSE:
      escalate_to_human(task,
        reason  = "重試 {MAX_RETRIES} 次仍失敗",
        details = test_result.failures)

  // 死鎖處理：鎖超過 expires 時間 → 自動 gc
  IF lock_registry.has_expired_locks():
    EXECUTE("make agent-lock-gc")
```

---

## 交接協議（v3.0）

> **取代** `completed.jsonl` 的 3 欄位格式。Worker 完成後產生結構化交接單。

Worker 完成任務後，除了 `make agent-done`（向後相容），還必須產生交接單：

```
FUNCTION on_task_complete(worker, task, result):
  // 1. 向後相容：寫入 completed.jsonl
  EXECUTE("make agent-done TASK={task.id} STATUS={result.status}")

  // 2. v3.0：產生結構化交接單
  handoff = create_handoff(TASK_COMPLETE,
    task_id = task.id,
    from_agent = { role: worker.role, task_manifest: task.manifest },
    status = result.status,  // success | failed | needs_review
    artifacts = {
      files_modified: result.files_modified,
      diff_summary: result.diff,
      test_output: result.test_output,
      test_checksums: result.test_checksums
    },
    failure_context = result.failure_context,  // if failed
    success_context = result.success_context   // if success
  )

  SAVE(".agent-events/handoffs/HANDOFF-{timestamp}-{seq}.yaml", handoff)
```

Orchestrator 驗證流程升級：

```
FUNCTION on_worker_done_v3(handoff):
  // 讀取結構化交接單（而非 completed.jsonl）
  task = handoff.task_id
  scope = task.manifest.scope

  // 獨立驗證（不變）
  test_result = EXECUTE("make test-filter FILTER={scope.filter}")

  IF test_result.passed:
    // 產生 PHASE_GATE 交接單（如果在管線中）
    IF pipeline_active:
      gate_result = evaluate_gate(current_gate, artifacts, gate_agents)
      // ... pipeline.md 的門檻邏輯
    lock_registry.unlock(task.locked_files)
  ELSE:
    // 走升級協議（取代硬編碼的 escalate_to_human）
    IF escalation_loaded:
      IF task.retry_count < MAX_RETRIES(2):
        // 產生 REASSIGNMENT 交接單（含 memory hint）
        memory_hint = get_memory_hint(task, handoff.failure_context)
        reassignment = create_handoff(REASSIGNMENT,
          previous_diagnosis = handoff.failure_context,
          orchestrator_hint = memory_hint.strategy,
          memory_ref = memory_hint)
        reassign(task, reassignment)
      ELSE:
        escalate(severity="P1", reason="Worker auto_fix + Orchestrator 重派皆耗盡", task_id=task.id, context={task, failures: handoff.failure_context})
    ELSE:
      // fallback: 原有行為
      escalate_to_human(task, details=test_result.failures)
```

---

## 並行軌道（v3.0）

> **升級** 扁平鎖定為多軌並行。

```
FUNCTION plan_parallel_execution(sub_tasks):
  graph = build_dependency_graph(sub_tasks)
  levels = topological_levels(graph)

  execution_plan = []
  FOR level_num, tasks IN levels:
    track_group = {
      level: level_num,
      tracks: [],
      marker: "[P]" if LEN(tasks) > 1 else "[S]"
    }
    FOR task IN tasks:
      track = {
        task: task,
        assigned_role: select_role(task),
        locked_files: task.scope.allow,
        track_id: NEXT_TRACK_ID()
      }
      track_group.tracks.append(track)
    execution_plan.append(track_group)

  // 鎖衝突偵測
  FOR group IN execution_plan:
    all_locks = flatten(t.locked_files FOR t IN group.tracks)
    IF has_duplicates(all_locks):
      // 解法 1：移到下一層
      // 解法 2：指派 integ agent
      resolve_lock_conflicts(group)

  RETURN execution_plan


FUNCTION converge_tracks(completed_tracks, integ_agent):
  handoffs = [track.final_handoff FOR track IN completed_tracks]
  conflicts = integ_agent.detect_conflicts(handoffs)
  IF conflicts:
    FOR conflict IN conflicts:
      IF conflict.resolvable:
        integ_agent.resolve(conflict)
      ELSE:
        escalate(severity="P1", reason="並行軌道不可解衝突", context={conflict})
  // 整合測試
  result = EXECUTE("make test")
  IF result.failed:
    dev_qa_loop(integration_task, integ_agent, qa_agent)
```

---

## Sub-Agent 深度限制（max_spawn_depth）

> **設計原則**（來自 Claude Code 架構分析）：控制迴圈越簡單，Debug 越容易。多層 agent 遞迴是最常見的「可運作但無法除錯」陷阱。

**規則：所有 Worker agent 的 `max_spawn_depth: 1`**

```
FUNCTION enforce_spawn_depth(agent, current_depth):
  IF current_depth >= agent.max_spawn_depth:
    STOP — 不得再派生子 agent
    改為：上報 Orchestrator（escalation_target）
  ELSE:
    可產生最多一層子 agent（Task 工具呼叫）
    子 agent 繼承 max_spawn_depth = 0（不可再派生）
```

- Orchestrator 本身不受此限制（負責分派整個 DAG）
- Worker 遇到超出能力的子問題 → 上報 escalation_target，由 Orchestrator 重新分派
- 子 agent 的結果注入主迴圈為 tool response，不建立新的 message history 分支

---

## MCP 安全邊界

Worker Agent 可自行執行：
- filesystem MCP：讀寫自己 scope 內的文件
- bash MCP：`make test-filter`、`make lint`

需要 Orchestrator 審核才能執行：
- git push / git merge
- 刪除操作（rm、DROP TABLE）
- 外部 API 的寫入操作
- 環境變數修改
- Docker image 推送

---

## Autonomous 模式整合（autonomous: enabled 時生效）

> **Canonical source**: Worker 基礎規則定義於本檔案。Autonomous Worker 擴展規則見 `autonomous_dev.md`「Multi-Agent 整合」。任務 dispatch 路由見 `task_orchestrator.md` Part G。

搭配 autonomous_dev 使用時，Worker 具備自主修復能力：

### Worker 自主能力

每個 Worker 在 Task Manifest scope 內運用 autonomous_dev 的規則：
- auto_fix_loop：測試失敗自動修復，含振盪/級聯/偷渡偵測
- 自主命名與 pattern 決策
- scope 內文件更新

### 不搭配 autonomous 時（原有行為）

Worker 完成任務 → 觸發 agent-done → Orchestrator 驗證 → 人類確認合併。
Worker 遇到問題 → 直接上報 Orchestrator。

### 搭配 autonomous 時

Worker 遇到測試失敗 → 先 auto_fix_loop（最多 3 次） → 仍失敗才上報 Orchestrator。
Orchestrator 驗證通過 → 可自動合併到工作分支（git push 到主分支仍需人類確認）。

### 升級協議整合（v3.0）

Worker 的 auto_fix_loop 失敗不再直接 `PAUSE_AND_REPORT`，而是走升級協議：

```
FUNCTION on_worker_auto_fix_exhausted_v3(worker, task, failures):
  IF escalation_loaded:
    IF orchestrator.retry_count(task) < MAX_RETRIES(2):
      // 查詢 project memory
      memory_hint = get_memory_hint(task, failures)
      reassignment = create_handoff(REASSIGNMENT,
        previous_diagnosis = failures,
        memory_ref = memory_hint)
      orchestrator.reassign(task, reassignment)
    ELSE:
      escalate(severity="P1", reason="Worker auto_fix + Orchestrator 重派皆耗盡", task_id=task.id, context={task, failures})
  ELSE:
    // fallback: 原有行為
    PAUSE_AND_REPORT_TO_HUMAN(reason="Worker auto_fix + Orchestrator 重派皆耗盡")
```

---

## 交接單類型參考（v3.1）

五種既有類型 + 一種新增的 Sprint 層級彙總：

| 類型 | 用途 | 產生方 |
|------|------|--------|
| `TASK_COMPLETE` | Worker 完成單一任務 | Worker |
| `REASSIGNMENT` | Orchestrator 重派任務（含 memory hint） | Orchestrator |
| `PHASE_GATE` | Pipeline 階段轉換（G1-G6 通過） | Orchestrator |
| `ESCALATION` | 重試耗盡，升級至人類 | Orchestrator |
| `SESSION_BRIDGE` | 跨 session 上下文保留 | Orchestrator |
| `SPRINT_SUMMARY` | Sprint 邊界彙總（autopilot 跨 session 用） | Orchestrator |

### SPRINT_SUMMARY 交接單格式

autopilot 模式下，每個 sprint 結束時 Orchestrator 產生此交接單，供下個 session 量化續接：

```yaml
handoff_type: SPRINT_SUMMARY
sprint_id: "SPRINT-{N}"
timestamp: "{ISO8601}"
from_agent: orchestrator
to_agent: orchestrator

velocity:
  planned: {int}          # 計劃完成的任務數
  actual: {int}           # 實際完成的任務數

quality_metrics:
  first_pass_qa_rate: {percentage}   # 首次 QA 通過率（反映 impl 品質）
  avg_retries: {float}               # 平均重派次數（< 1.0 為健康）
  escalations: {int}                 # 升級至人類的次數

completed:
  - task_id: "{TASK-XXX}"
    done_when_verified: true         # Done When 是否全數通過
    qa_attempts: {int}

carried_over:
  - task_id: "{TASK-XXX}"
    reason: "{未完成原因}"
    priority: "HIGH|MED|LOW"

retrospective:
  went_well: "{本 sprint 成功之處}"
  improve: "{下個 sprint 改進方向}"

next_sprint_goal: "{下個 sprint 的核心目標}"
```

> SPRINT_SUMMARY 存入 `.agent-events/handoffs/SPRINT-{N}-SUMMARY.yaml`，供 `make session-checkpoint` 讀取。

---

## Done Definition（完成標準）

Worker 自我驗收清單：

```
□ make test-filter FILTER=<scope> 全數通過
□ make lint 無 error
□ 無新增 TODO/FIXME/hack 標記（有則需說明）
□ 已更新對應 docs/ 文件
□ 已解鎖占用的文件
□ 已觸發 agent-done hook
```
