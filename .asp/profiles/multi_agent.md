# Multi-Agent Orchestration Profile

適用：並行任務分治、大型功能拆解、自動化 CI/CD 整合。
載入條件：`mode: multi-agent`

> **與 committee 模式的區別**：
> - `multi-agent`：實作期使用。需求已確定，拆分為並行子任務加速執行。
> - `committee`：決策期使用。需求模糊或風險高，多角色辯論後才進入實作。

---

## Token 成本意識

Multi-agent 模式的 token 消耗約為單 agent 的 **15 倍**。分拆前先確認：

- sub-agent 存在的核心理由是 **context 隔離**，不是角色擬人化——如果單一 agent 的 context 能裝下，就不要拆
- **電話遊戲問題**：Orchestrator 轉述 Worker 回應時會失真。Worker 完成後應直接輸出結構化結果（Done Checklist），Orchestrator 原樣轉交人類，不重新改寫

---

## Orchestrator 職責

開始並行任務前，必須完成：

```
1. 讀取 docs/architecture.md 與 docs/adr/ 確認現況
2. 將需求拆解為低耦合子任務
3. 為每個子任務定義 Task Manifest（見下）
4. 建立 .agent-lock.yaml 登記文件鎖定
5. 指派 Worker，設定 Done Definition
```

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
```

```bash
make agent-unlock FILE=src/store/user.go   # 正常完成後解鎖
make agent-lock-gc                          # 清理逾時鎖定（> 2 小時視為異常）
```

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
    NOTIFY orchestrator("✅ {task} 驗證通過，待人工確認合併")
    AWAIT human_confirm("merge")
  ELSE:
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
