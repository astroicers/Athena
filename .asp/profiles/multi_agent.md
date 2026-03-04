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
