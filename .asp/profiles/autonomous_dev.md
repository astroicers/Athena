# Autonomous Development Profile

<!-- requires: global_core, system_dev, vibe_coding -->
<!-- optional: guardrail, multi_agent -->
<!-- conflicts: (none) -->

適用：AI 全自動開發，人類僅在關鍵節點審核。
載入條件：`.ai_profile` 中 `autonomous: enabled`
          或 `workflow: vibe-coding` + `hitl: minimal`（後相容）

> **設計原則**：用明確規則取代模糊的「信任 AI 判斷」。
> AI 不是「自由行動」，而是在精確定義的邊界內自主決策。

---

## 啟用前提

必須同時滿足：
1. `.ai_profile` 設定 `autonomous: enabled`（或同時設 `workflow: vibe-coding` + `hitl: minimal`）
2. 所有待實作功能的 ADR 已為 `Accepted` 狀態（可透過「批次預審」一次完成）
3. 每個功能有對應的 SPEC（AI 可自行建立，但必須遵循 SPEC_Template.md）

---

## AI 自主決策邊界

### 可自主執行（不暫停）

| 類別 | 範圍 | 條件 |
|------|------|------|
| **檔案建立** | 新增程式碼 / 設定 / 文件檔案 | 在 SPEC 範圍內 |
| **檔案修改** | 編輯既有程式碼 | 在 SPEC 範圍內 |
| **SPEC 建立** | `make spec-new` + 填寫內容 | 對應 ADR 已 Accepted |
| **測試撰寫** | 新增 / 修改測試檔案 | TDD 流程的一部分 |
| **文件更新** | 更新 ROADMAP / README / CHANGELOG | 功能完成後同步 |
| **Bug 自動修復** | `make test` 失敗 → 讀錯誤 → 修 → 重跑 | 最多 3 次重試 |
| **命名決策** | 變數 / 函數 / 檔案命名 | 跟隨既有 codebase 慣例 |
| **Pattern 選擇** | 選擇實作 pattern | 優先複用既有 pattern |

### 必須暫停（等待人類確認）

| 類別 | 觸發條件 |
|------|----------|
| **git push** | 鐵則，所有情況 |
| **git rebase** | 鐵則，所有情況 |
| **docker push / deploy** | 鐵則，所有情況 |
| **刪除檔案** | `rm` 任何非暫存檔案 |
| **範圍超出** | 實作中發現需求超出當前 SPEC / 版本範圍 |
| **新增外部依賴** | pyproject.toml / package.json 等新增 dependency |
| **DB Schema 變更** | 新增/修改資料庫結構（除非 SPEC 明確指定） |
| **Bug 修復失敗** | 重試 3 次仍失敗、振盪偵測（相同失敗重複）、級聯偵測（失敗增加）、偷渡偵測（測試被改） |

### 禁止（即使 autonomous 模式也不可）

| 類別 | 說明 |
|------|------|
| **ADR 狀態變更** | AI 不可自行將 ADR 從 Draft 改為 Accepted |
| **跳過 TDD** | 新功能必須測試先於代碼，autonomous 模式不豁免 |
| **跳過 SPEC** | 非 trivial 功能必須有 SPEC 再實作 |
| **環境硬編碼** | 禁止針對特定環境或目標的硬編碼邏輯（如寫死 IP、主機名、資料庫端點等） |

---

## 自動修復循環

```
FUNCTION auto_fix_loop(test_command, max_retries=3):

  // ─── 初始快照：記錄修復前的基線 ───
  original_test_checksums = CHECKSUM(all_test_files)
  previous_failures = NULL
  previous_fix_descriptions = []

  FOR attempt IN 1..max_retries:
    result = EXECUTE(test_command)

    // ─── 偷渡偵測：測試檔案被修改導致「假通過」 ───
    current_test_checksums = CHECKSUM(all_test_files)
    IF current_test_checksums != original_test_checksums:
      changed_tests = DIFF(original_test_checksums, current_test_checksums)
      WARN("⚠️ 測試檔案被修改：{changed_tests}")
      PAUSE_AND_REPORT(
        reason = "smuggling_detected",
        detail = "測試通過但測試檔案已被修改。請人類審核修改是否合理（新增測試 OK、修改 assertion 需審核）。",
        changed_files = changed_tests
      )
      RETURN NEEDS_REVIEW

    IF result.passed:
      LOG("測試通過（第 {attempt} 次）")
      RETURN SUCCESS

    // 分析失敗原因
    current_failures = parse_test_failures(result.output)

    // ─── 振盪偵測：相同失敗重複出現，修復策略無效 ───
    IF previous_failures != NULL
       AND SET(current_failures) == SET(previous_failures):
      PAUSE_AND_REPORT(
        reason = "oscillation_detected",
        detail = "第 {attempt} 次修復後失敗模式與前一次相同。目前策略無效，需人類介入。",
        failures = current_failures,
        attempted_fixes = previous_fix_descriptions
      )
      RETURN FAILURE

    // ─── 級聯偵測：修復導致更多失敗 ───
    IF previous_failures != NULL
       AND LEN(current_failures) > LEN(previous_failures):
      REVERT_LAST_FIX()
      PAUSE_AND_REPORT(
        reason = "cascade_detected",
        detail = "修復導致失敗數量增加（{LEN(previous_failures)} → {LEN(current_failures)}）。已回退上一次修改。",
        before = previous_failures,
        after = current_failures
      )
      RETURN FAILURE

    // 套用修復
    current_fix_descriptions = []
    FOR error IN current_failures:
      fix = diagnose_and_fix(error)
      APPLY(fix)
      current_fix_descriptions.append(fix.description)

    previous_failures = current_failures
    previous_fix_descriptions = current_fix_descriptions
    LOG("第 {attempt} 次修復完成，重新測試...")

  // 超過重試次數
  LOG("重試 {max_retries} 次仍失敗")
  PAUSE_AND_REPORT(
    reason = "max_retries_exceeded",
    detail = "已嘗試 {max_retries} 次修復，仍有失敗。",
    failures = current_failures,
    attempted_fixes = previous_fix_descriptions
  )
  RETURN FAILURE
```

> **三道防護摘要**：
> | 防護 | 偵測條件 | 動作 |
> |------|----------|------|
> | **振盪偵測** | 本次失敗集合 == 上次失敗集合 | PAUSE（修復策略無效） |
> | **級聯偵測** | 本次失敗數量 > 上次失敗數量 | REVERT + PAUSE（修復引入新問題） |
> | **偷渡偵測** | 測試檔案 checksum 改變 | WARN + PAUSE（AI 可能改了測試而非代碼） |

---

## Stage 驅動開發流程

autonomous 模式下，開發按 Stage 推進，每個 Stage 是一個完整的功能交付單元：

```
FUNCTION execute_stage(stage):

  // 1. Pre-flight
  VERIFY adr_status(stage.adr) == "Accepted"

  // 2. SPEC
  IF NOT exists(stage.spec):
    CREATE spec_from_template(stage)

  // 3. TDD
  WRITE tests(stage.test_file)
  EXECUTE("make test-filter FILTER={stage.filter}")  // 預期：全部 FAIL

  // 4. Implementation
  IMPLEMENT(stage.source_files)

  // 5. Verification
  auto_fix_loop("make test")

  // 6. Documentation
  UPDATE docs(stage.affected_docs)

  // 7. Checkpoint
  LOG("Stage {stage.name} 完成")
  // 不暫停，繼續下一個 Stage
```

---

## Context 管理（長 session 保護）

autonomous 模式的 session 通常很長，必須主動管理 context：

| 觸發條件 | 動作 |
|----------|------|
| 完成一個 Stage | 輸出 Stage 完成摘要（修改了哪些檔案、測試結果） |
| context 使用率 > 70% | `make session-checkpoint NEXT="..."` |
| 連續 3 個檔案修改無 `make test` | 立刻執行 `make test` |
| 偵測到 context decay 信號 | 停止開發，輸出 checkpoint，建議新 session |

---

## Multi-Agent 整合（mode: multi-agent 時生效）

autonomous_dev 與 multi_agent 同時啟用時，autonomous 規則按層級套用：

### Orchestrator 層

Orchestrator 繼承 autonomous 的「自主決策邊界」，但 scope 為全專案：

| 可自主 | 必須暫停（等人類） |
|--------|-------------------|
| 建立 Task Manifest、分配任務 | git push / merge 到主分支 |
| 建立/修改 SPEC（ADR 已 Accepted） | 新增外部依賴（影響所有 Worker） |
| 獨立驗證 Worker 產出 | DB Schema 變更 |
| 解鎖文件、執行 lock GC | Worker 重派 2 次仍失敗 |
| 批次 ADR 預審流程 | 範圍超出所有已 Accepted ADR |

### Worker 層

Worker 繼承 autonomous 的「自主決策邊界」，但 scope 限縮為 Task Manifest：

| 可自主 | 必須上報 Orchestrator |
|--------|----------------------|
| scope 內檔案建立/修改 | auto_fix_loop 耗盡（3 次仍失敗） |
| TDD：scope 內測試撰寫/執行 | 發現需求超出 Task Manifest scope |
| auto_fix_loop（含三道防護） | 需要修改 scope 外的檔案 |
| 命名決策、pattern 選擇 | 需要新增外部依賴 |
| scope 內文件更新 | 偵測到振盪/級聯/偷渡 |

### 升級的 auto_fix_loop

Worker 的 auto_fix_loop 失敗 → 不直接暫停人類，而是上報 Orchestrator：

```
FUNCTION on_worker_auto_fix_exhausted(worker, task, failures):

  IF orchestrator.retry_count(task) < MAX_RETRIES(2):
    orchestrator.reassign(task, context = failures)  // Orchestrator 可自主重派
  ELSE:
    PAUSE_AND_REPORT_TO_HUMAN(
      reason  = "Worker auto_fix + Orchestrator 重派皆耗盡",
      detail  = "Worker 自修 3 次 + Orchestrator 重派 2 次仍失敗",
      failures = failures
    )
```

### Context 管理

每個 Worker 獨立執行 context 衰退偵測：
- 完成一個 sub-stage → 輸出摘要
- context > 70% → `make session-checkpoint`
- 偵測到衰退信號 → 上報 Orchestrator，由 Orchestrator 決定是否開新 Worker

---

## 與其他 Profile 的關係

```
autonomous_dev.md
  ├── 依賴 vibe_coding.md（hitl: minimal 定義）
  ├── 依賴 system_dev.md（ADR/SPEC/TDD 流程）
  ├── 依賴 global_core.md（鐵則 + 連帶修復）
  ├── 可選 guardrail.md（敏感資訊保護）
  └── 可選 multi_agent.md（多 Agent 並行，autonomous 規則分層套用）
```

單獨啟用 → AI 單 agent 全自動開發（現有行為不變）。
搭配 multi_agent → 每個 Worker 以 autonomous 規則運作，Orchestrator 負責協調。
`committee.md` 可搭配使用（決策期不衝突）。
