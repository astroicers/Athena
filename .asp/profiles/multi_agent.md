# Multi-Agent Orchestration Profile

適用：並行任務分治、大型功能拆解、自動化 CI/CD 整合。
載入條件：`mode: multi-agent`

> **與 committee 模式的區別**：
> - `multi-agent`：實作期使用。需求已確定，拆分為並行子任務加速執行。
> - `committee`：決策期使用。需求模糊或風險高，多角色辯論後才進入實作。

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

### 解鎖規則

```bash
make agent-unlock FILE=src/store/user.go   # 正常完成後解鎖
make agent-lock-gc                          # 清理逾時鎖定（> 2 小時視為異常）
```

**死鎖處理**：若 Worker crash 導致鎖未釋放，超過 `expires` 時間後 Orchestrator 自動執行 `agent-lock-gc`。

---

## 事件 Hook

Worker 完成任務後，**禁止靜默完成**，必須觸發 Hook：

```bash
make agent-done TASK=TASK-001 STATUS=success
make agent-done TASK=TASK-001 STATUS=failed REASON="測試未通過：TestUserCreate"
```

Orchestrator 輪詢 `.agent-events/completed.jsonl`（每分鐘一次），收到事件後獨立驗證：

```
收到 Worker Done 事件
  ↓
make test-filter FILTER=<task_scope>   # 不信任 Worker 自報
  ├── 通過 → 解鎖文件 → 合併（需人工確認）
  └── 失敗 → 重新指派 / escalate 給人類
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
