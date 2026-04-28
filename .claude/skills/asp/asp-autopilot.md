---
name: asp-autopilot
description: |
  Use when executing ROADMAP-driven tasks autonomously or resuming a paused session.
  Handles fresh start, auto-resume, task execution loop, and cross-session handoff.
  Triggers: autopilot, run roadmap, auto run, resume, continue roadmap,
  自動執行, 跑 roadmap, 續接, 繼續, 開始 autopilot, 繼續執行, 自動跑,
  start autopilot, execute roadmap, resume session, pick up where we left off.
---

# ASP Autopilot — ROADMAP 驅動自動執行

## 適用場景

ROADMAP.yaml 驅動的持續任務執行。跨 session 自動續接，無需人工重新說明上下文。

---

## Phase 0：判斷是否續接

```bash
cat .asp-autopilot-state.json 2>/dev/null || echo "NOT_FOUND"
```

### 若 status == "in_progress" → 自動續接

```
🔄 發現進行中的 Autopilot Session
================================
上次中斷任務：[task_id] [task_title]
已完成任務數：[N]
剩餘任務數：[M]

自動續接中...（無需確認）
```

跳至 **Phase 2：執行迴圈**。

### 若不存在或 status != "in_progress" → 新建執行

進入 **Phase 1：新建執行**。

---

## Phase 1：新建執行前提驗證

### 1a. 確認 ROADMAP.yaml 存在

```bash
ls ROADMAP.yaml 2>/dev/null || echo "NOT_FOUND"
```

若不存在：
```
❌ 找不到 ROADMAP.yaml
建議：make autopilot-init 建立範本，填入任務後再啟動
```
停止執行。

### 1b. 驗證 ROADMAP + 更新 CLAUDE.md

```bash
make autopilot-validate
```

驗證內容：
- ROADMAP.yaml 格式正確
- 所有任務的 SPEC 存在（或標記為 spec-pending）
- Draft ADR 不阻擋非依賴任務
- 更新 CLAUDE.md 的「專案概覽」區塊

### 1c. 顯示任務佇列

```bash
make autopilot-status
```

```
📋 Autopilot 任務佇列
================================
✅ 已完成（N 個）
▶️  待執行（M 個）：
  1. [task_id] [title] — SPEC: [spec_ref]
  2. [task_id] [title] — SPEC: [spec_ref]
  ...

開始執行第一個待執行任務...
```

---

## Phase 2：執行迴圈

對每個待執行任務：

### on_task_received(task)

**2a. 前置檢查**

| 條件 | 處理 |
|------|------|
| 對應 ADR 為 Draft | 標記 `blocked`，跳過，繼續下一任務 |
| 缺少 SPEC | 自動建立：`make spec-new TITLE="[task title]"` |
| 依賴任務未完成 | 標記 `blocked`，跳過 |

**2b. 更新狀態**

```bash
# 更新 .asp-autopilot-state.json 中此任務的狀態
# status: "in_progress"
```

**2c. 執行任務**

遵循 ASP 標準工作流：
1. 閱讀對應 SPEC（Goal / Done When / Rollback Plan）
2. TDD：先寫測試（讓它 FAIL）
3. 實作直到測試 PASS
4. 文件同步

**2d. 驗證完成**

```bash
make test-filter FILTER=[task_keyword]
```

測試全 PASS → 標記任務完成。
測試 FAIL → 自行修復（最多 3 次嘗試），仍失敗 → 標記 `failed`，繼續下一任務。

**2e. 更新狀態**

```bash
make agent-done TASK=[task_id] STATUS=success
```

---

## Phase 3：Context 管理

### 60% Context — 預防性存檔

```bash
make session-checkpoint NEXT="繼續執行 [next_task_id]: [next_task_title]"
```

繼續執行，但存檔點已建立。

### 75% Context — 主動退出

```
⚠️  Context 使用率已達 75%，主動暫停以防止截斷

已完成任務：[清單]
下一個任務：[task_id] [title]

Session 交接指令：
  新 Session → 說「開始 autopilot」或 /asp-autopilot
  → 將自動讀取 .asp-autopilot-state.json 並續接

正在儲存狀態...
```

```bash
make session-checkpoint NEXT="[next_task_id]: [next_task_title]"
```

退出，等待新 session。

---

## Phase 4：全部完成

```bash
make autopilot-status
```

```
🎉 Autopilot 執行完畢
================================
已完成：[N] 個任務
跳過（blocked）：[M] 個任務
失敗：[K] 個任務

📋 需要人工處理：
  Blocked 任務（等待 ADR Accept）：
    - [task_id]: [說明]

  Failed 任務（需人工介入）：
    - [task_id]: [失敗原因]

================================
建議下一步：
1. make audit-quick — 確認無新增 blocker
2. 審核上方 blocked/failed 任務
3. make autopilot-reset — 清除狀態（完成後）
```

---

## 零確認策略

Autopilot 模式下，以下情況**不暫停詢問**（自動處理）：

| 情況 | 自動處理 |
|------|---------|
| 缺少 SPEC | 自動 `make spec-new` |
| 測試失敗（≤3 次）| 自動修復後重試 |
| Draft ADR 阻擋 | 自動標記 blocked，跳至下一任務 |
| Context 達 60% | 自動存檔，繼續執行 |
| Context 達 75% | 自動存檔，主動退出 |

**以下情況仍需暫停：**
- `git push`（鐵則）
- `docker push / deploy`（鐵則）
- 任務失敗超過 3 次

---

## 常用指令

```bash
make autopilot-init       # 建立 ROADMAP.yaml 範本
make autopilot-validate   # 驗證並更新 CLAUDE.md
make autopilot-status     # 查看當前進度
make autopilot-reset      # 清除狀態（全部完成後）
make session-checkpoint NEXT="..."  # 手動儲存斷點
```
