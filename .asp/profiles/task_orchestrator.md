# Task Orchestrator — 任務協調與專案健康審計

<!-- requires: global_core, system_dev -->
<!-- optional: autonomous_dev, multi_agent, vibe_coding, design_dev, openapi, guardrail, rag_context, frontend_quality -->
<!-- conflicts: (none) -->

適用：統一任務入口，自動分類與路由任何任務類型；首次介入專案時自動審計並強制補齊缺失。
載入條件：`orchestrator: enabled` 或 `autonomous: enabled`（自動載入）

> **設計原則**：
> - 任何時候介入任何專案，都能讓該專案走回正軌
> - 先審計、後執行：確保基礎設施健全，再做功能開發
> - 每次任務完成都產出完整文件，且文件與代碼同步

---

## 統一入口

所有任務（需求、Bug、功能修改、功能移除）從這裡開始：

```
FUNCTION on_task_received(request):

  // ─── Step 0: 專案健康審計（首次介入或過期）───
  IF NOT exists(".asp-audit-baseline.json") OR audit_expired(7_days):
    health = project_health_audit()
    IF health.has_blockers:
      remediate_gaps(health)  // 先補齊 blocker 再做主任務
      // autonomous: 自動建立 remediation SPEC
      // standard:   列出 blocker，建議建立 SPEC

  // ─── Step 1: 任務分類 ───
  task_type = classify_task(request)
  PRESENT("任務分類：[{task_type}] {request.summary}")
  PRESENT("  理由：{classification_reason}")
  AWAIT human_confirm  // 即使 hitl: minimal 也確認，錯誤分類代價太高

  // ─── Step 2: 路由執行 ───
  MATCH task_type:
    NEW_FEATURE  → execute_new_feature(request)
    BUGFIX       → execute_bugfix(request)
    MODIFICATION → execute_modification(request)
    REMOVAL      → execute_removal(request)
    GENERAL      → execute_general(request)

  // ─── Step 3: 後置審計（最多 2 輪）───
  post_health = quick_audit()  // 輕量版，只檢查本次修改相關
  IF post_health.new_gaps:
    IF post_health.audit_round >= 2:
      WARN("後置審計已達上限（2 輪），剩餘 gap 記入 tech-debt")
      FOR gap IN post_health.new_gaps:
        LOG_TECH_DEBT("post-audit-overflow: {gap}")
    ELSE:
      WARN("本次修改引入新的 gap，需補齊")
      remediate_gaps(post_health, audit_round = post_health.audit_round + 1)

  // ─── Step 4: 更新基線 ───
  update_audit_baseline(post_health)
```

---

## Part A: 專案健康審計

### 觸發時機

| 條件 | 動作 |
|------|------|
| 首次介入專案（無 `.asp-audit-baseline.json`） | **自動觸發**完整審計 |
| 距上次審計 > 7 天 | **建議觸發**（autonomous: 自動 / standard: 提示） |
| `make audit-health` | **手動觸發**隨時可用 |
| 任務完成後 | **自動觸發**快速審計（只檢查本次修改相關） |

### 掃描維度（7 項）

```
FUNCTION project_health_audit():

  report = { blockers: [], warnings: [], info: [] }

  // ─── 1. 測試覆蓋 ───
  source_files = find_source_files()  // *.go, *.ts, *.py, etc.
  test_files = find_test_files()      // *_test.go, *.test.ts, test_*.py, etc.
  FOR file IN source_files:
    IF NOT has_corresponding_test(file, test_files):
      // 核心模組（auth, payment, data）無測試 → BLOCKER
      // 其他模組 → WARNING
      severity = is_core_module(file) ? BLOCKER : WARNING
      report.add(severity, "無測試覆蓋：{file}")

  // ─── 2. SPEC 覆蓋 ───
  specs = list_specs()  // make spec-list
  modules = identify_major_modules()  // src/ 下的一級目錄
  FOR module IN modules:
    IF NOT any_spec_covers(module, specs):
      report.add(WARNING, "模組 {module} 無對應 SPEC")

  // ─── 3. ADR 覆蓋 ───
  adrs = list_adrs()  // make adr-list
  // 檢查核心架構組件是否有 ADR
  FOR adr IN adrs:
    IF adr.status == "Draft" AND has_implementation_code(adr):
      report.add(BLOCKER, "ADR-{adr.id} 狀態為 Draft 但已有實作代碼（鐵則違反）")

  // ─── 4. 文件完整性 ───
  required_docs = ["README.md", "CHANGELOG.md"]
  optional_docs = ["docs/architecture.md"]
  FOR doc IN required_docs:
    IF NOT exists(doc):
      report.add(WARNING, "缺少 {doc}")
    ELIF file_age(doc) > 90_days:
      report.add(INFO, "{doc} 超過 90 天未更新")
  FOR doc IN optional_docs:
    IF NOT exists(doc) AND project_type == "system":
      report.add(WARNING, "缺少 {doc}（系統專案建議有架構文件）")

  // ─── 5. 程式碼衛生 ───
  // grep 全專案
  deprecated_count = count_pattern("DEPRECATED|@deprecated")
  todo_no_owner = count_pattern("TODO[^(]|TODO$")  // TODO 後無 (owner)
  fixme_count = count_pattern("FIXME")
  tech_debt_count = count_pattern("tech-debt:")
  IF deprecated_count > 0:
    report.add(WARNING, "{deprecated_count} 個 DEPRECATED 標記待清理")
  IF todo_no_owner > 0:
    report.add(WARNING, "{todo_no_owner} 個 TODO 無 owner")
  IF tech_debt_count > 0:
    report.add(INFO, "{tech_debt_count} 個 tech-debt 標記")

  // ─── 6. 依賴健康 ───
  IF has_package_manager():
    IF NOT exists(lock_file):
      report.add(WARNING, "缺少 lock file（{expected_lock_file}）")
    IF has_loose_versions():
      report.add(INFO, "存在未鎖定版本（* 或 latest）")
  IF NOT exists(".env.example") AND uses_env_vars():
    report.add(INFO, "缺少 .env.example")

  // ─── 7. 文件新鮮度 ───
  IF specs.count > 0 AND NOT any(spec.has_traceability FOR spec IN specs):
    report.add(WARNING, "所有 SPEC 均無 Traceability 資料，無法驗證文件新鮮度。建議回填。")
  ELSE:
    FOR spec IN specs:
      IF spec.has_traceability:
        FOR impl_file IN spec.traceability.impl_files:
          IF git_modified_date(impl_file) > spec.last_verified_date:
            report.add(WARNING, "SPEC-{spec.id} 的實作檔案已更新但 SPEC 未同步（doc-stale）")

  RETURN report
```

### 分級標準

| 等級 | 判定條件 | 處理 |
|------|----------|------|
| 🔴 **Blocker** | ADR Draft 有實作代碼；核心模組無測試 | 必須先修復才能做主任務 |
| 🟡 **Warning** | 模組無 SPEC；無 lock file；DEPRECATED 未清理；文件過期 | 主任務完成後處理 |
| 🟢 **Info** | 缺 .env.example；tech-debt 標記；文件 > 90 天未更新 | 建議改善 |

### 強制補齊流程

```
FUNCTION remediate_gaps(health_report):

  blockers = health_report.blockers
  warnings = health_report.warnings

  IF blockers.not_empty:
    PRESENT("🔴 發現 {LEN(blockers)} 個 blocker，必須先修復：")
    FOR gap IN blockers:
      PRESENT("  - {gap.description}")

    IF autonomous_enabled:
      // 自動建立 remediation SPEC
      FOR gap IN blockers:
        spec = EXECUTE("make spec-new TITLE=\"AUDIT-{NNN}: {gap.summary}\"")
        FILL spec:
          Goal: "補齊 {gap.description}"
          Done_When: gap.resolution_criteria
      PAUSE("已建立 {LEN(blockers)} 個修復 SPEC，請確認是否立即執行補齊")
    ELSE:
      PAUSE("請決定處理順序，或執行 make spec-new 建立修復 SPEC")

  IF warnings.not_empty:
    LOG("🟡 {LEN(warnings)} 個 warning 排入佇列，將在主任務完成後處理")
```

### 審計基線

審計完成後產生 `.asp-audit-baseline.json`（加入 `.gitignore`）：

```json
{
  "last_audit": "2026-03-11T10:00:00Z",
  "test_coverage_ratio": 0.65,
  "spec_count": 12,
  "adr_count": 5,
  "blockers": 2,
  "warnings": 8,
  "info": 3
}
```

用途：追蹤改善趨勢，下次審計時比對。

---

## Part B: 任務分類

### 分類決策樹

```
FUNCTION classify_task(request):

  signals = extract_signals(request)

  // 優先匹配明確意圖
  IF signals.match("remove", "delete", "deprecate", "drop", "cleanup",
                   "移除", "刪除", "廢棄", "拿掉", "砍掉"):
    RETURN { type: TASK_REMOVAL, reason: "包含移除/刪除意圖" }

  IF signals.match("bug", "fix", "broken", "error", "crash", "regression",
                   "修復", "修 bug", "錯誤", "壞了", "不正常", "hotfix"):
    RETURN { type: TASK_BUGFIX, reason: "包含修復/錯誤意圖" }

  IF signals.match("modify", "change", "update", "refactor", "adjust", "optimize",
                   "修改", "調整", "重構", "優化", "改善"):
    IF target_exists_in_codebase(signals.target):
      RETURN { type: TASK_MODIFICATION, reason: "修改既有功能 {signals.target}" }
    ELSE:
      RETURN { type: TASK_NEW_FEATURE, reason: "目標不存在，視為新增功能" }

  IF signals.match("add", "create", "implement", "build", "new",
                   "新增", "建立", "實作", "開發"):
    RETURN { type: TASK_NEW_FEATURE, reason: "包含新增/建立意圖" }

  // 複合需求或無明確信號
  RETURN { type: TASK_GENERAL, reason: "複合需求，需進一步分解" }
```

**重要**：分類結果必須向人類確認。即使 `hitl: minimal`，這是唯一在任務開始前的確認點。

---

## Part C: 架構影響評估

```
FUNCTION assess_architecture_impact(request):

  impact = { requires_adr: false, reasons: [] }

  // 根據 system_dev.md ADR 必要性表格
  IF request.adds_new_module_or_service:
    impact.requires_adr = true
    impact.reasons.append("新增模組/服務")

  IF request.changes_tech_stack:
    impact.requires_adr = true
    impact.reasons.append("更換技術棧（DB、框架、協議）")

  IF request.modifies_core_architecture:
    // Auth, API Gateway, DB schema (high risk)
    impact.requires_adr = true
    impact.reasons.append("調整核心架構")

  IF request.adds_new_db_table:
    impact.requires_adr = true
    impact.reasons.append("新增資料表")

  // 啟發式：影響檔案數
  affected = grep_for_affected_files(request.target_modules)
  IF LEN(affected) > 15:
    impact.requires_adr = true
    impact.reasons.append("影響超過 15 個檔案")

  IF impact.requires_adr:
    LOG("架構影響評估：需要 ADR — {impact.reasons}")
  ELSE:
    LOG("架構影響評估：無架構影響，跳過 ADR")

  RETURN impact
```

---

## Part D: 五種任務工作流

### D1. TASK_NEW_FEATURE（新增功能）

```
FUNCTION execute_new_feature(request):

  // Phase 1: 架構影響評估
  impact = assess_architecture_impact(request)

  IF impact.requires_adr:
    adr = EXECUTE("make adr-new TITLE=\"{request.title}\"")
    FILL adr from request context
    PAUSE("ADR 需要人類審核（AI 不可自行 Accept ADR — 鐵則）")
    WAIT_UNTIL adr.status == "Accepted" OR timeout(30_minutes):
      ON_TIMEOUT:
        PRESENT("⚠️ ADR-{adr.id} 等待超過 30 分鐘仍為 Draft。")
        PRESENT("  (1) 繼續等待  (2) 暫存進度並終止  (3) 跳過（標記 tech-debt: adr-pending）")
        choice = AWAIT human_choice
        IF choice == 3: LOG_TECH_DEBT("adr-pending: ADR-{adr.id}")

  // Phase 2: SPEC 建立
  spec = EXECUTE("make spec-new TITLE=\"{request.title}\"")
  FILL spec:
    Goal, Inputs, Outputs, Side Effects, Edge Cases, Rollback Plan,
    Done When (含測試條件), NFR (若適用), Traceability (預留)
  IF impact.requires_adr:
    spec.related_adr = adr.id

  // Phase 3: Gates（條件觸發，含 profile 載入檢查）
  IF design_enabled:
    IF NOT profile_loaded("design_dev"):
      WARN("design: enabled 但 profile 未載入，跳過 Design Gate")
      LOG_TECH_DEBT("design-gate-skipped")
    ELSE:
      CALL design_gate(spec)
  IF openapi_enabled:
    IF NOT profile_loaded("openapi"):
      WARN("openapi: enabled 但 profile 未載入，跳過 OpenAPI Gate")
      LOG_TECH_DEBT("openapi-gate-skipped")
    ELSE:
      CALL openapi_gate(spec)
  IF rag_enabled:      EXECUTE("make rag-search Q=\"{spec.keywords}\"")

  // Phase 4: 變更影響評估
  CALL assess_change_impact(spec)  // from system_dev.md

  // Phase 5: TDD
  WRITE test_files  // 所有測試應 FAIL
  EXECUTE("make test-filter FILTER={spec.filter}")  // 確認 FAIL

  // Phase 6: 實作
  IMPLEMENT source_files

  // Phase 7: 驗證（含 autonomous 三重防護）
  IF autonomous_enabled:
    result = CALL auto_fix_loop("make test")  // from autonomous_dev.md
    IF result.guard_triggered:  // oscillation / cascade / smuggling
      PAUSE("auto_fix_loop 防護觸發：{result.guard_type}，需人類介入")
      // 不繼續文件管線，等待人類決定
  ELSE:
    EXECUTE("make test")
  CALL verify_stable_state(spec)   // from system_dev.md

  // Phase 8: 提交前自審
  EXECUTE pre_commit_checklist()    // from system_dev.md

  // Phase 9: 文件管線
  CALL documentation_pipeline(spec, task_type=NEW_FEATURE)

  // Phase 10: 完成報告
  RETURN completion_report(spec)
```

### D2. TASK_BUGFIX（修復 Bug）

```
FUNCTION execute_bugfix(request):

  // Phase 1: 判斷是否為 Hotfix
  IF request.is_production_incident:
    CALL execute_hotfix(request)  // 走 system_dev.md Hotfix 流程
    RETURN

  // Phase 2: 嚴重度判斷
  severity = assess_severity(request)

  IF severity == TRIVIAL:
    // 快速路徑
    LOG("trivial bug，豁免 SPEC，理由：{reason}")
    FIX the_bug
    EXECUTE("make test")
    CALL grep_full_project(bug_pattern)  // mandatory，無豁免
    UPDATE "CHANGELOG.md"
    RETURN completion_report_lite()

  // Phase 3: Non-trivial Bug
  IF involves_architecture_decision(request):
    adr = EXECUTE("make adr-new TITLE=\"{request.title}\"")
    PAUSE("涉及架構決策，需先完成 ADR")

  // Phase 4: SPEC
  spec = EXECUTE("make spec-new TITLE=\"BUG-{request.summary}\"")
  FILL spec:
    Goal: "修復 {symptom}，根因：{root_cause_hypothesis}"
    Done When: 含重現測試條件

  // Phase 5: 重現（Reproduce）
  WRITE reproduction_test  // 必須 FAIL
  VERIFY reproduction_test FAILS

  // Phase 6: 修復
  IMPLEMENT fix

  // Phase 7: 驗證（含 autonomous 三重防護）
  VERIFY reproduction_test PASSES
  IF autonomous_enabled:
    result = CALL auto_fix_loop("make test")
    IF result.guard_triggered:
      PAUSE("auto_fix_loop 防護觸發：{result.guard_type}，需人類介入")
  ELSE:
    EXECUTE("make test")

  // Phase 8: 全專案掃描（mandatory — global_core.md 鐵則）
  CALL grep_full_project(bug_pattern)
  // 回覆格式：「已掃描全專案，共 N 處相同模式，已全部修復」或「無其他相同模式」
  IF bug_type == STATE_DEPENDENCY:
    CALL scan_state_dependencies()

  // Phase 9: 下游驗證（共用模組）
  IF modified_file.is_shared_module:
    EXECUTE("make test")  // 全量，非 test-filter
    LIST downstream_consumers

  // Phase 10: Postmortem 評估
  IF meets_postmortem_criteria(severity, retry_count):
    EXECUTE("make postmortem-new TITLE=\"{request.summary}\"")

  // Phase 11: 文件管線
  CALL documentation_pipeline(spec, task_type=BUGFIX)
  // commit message 含 bug 分類標籤：[bug:logic] / [bug:boundary] / etc.

  RETURN completion_report(spec)
```

### D3. TASK_MODIFICATION（修改功能）

```
FUNCTION execute_modification(request):

  // Phase 1: 找到既有 artifacts
  existing_spec = find_related_spec(request.target)
  existing_adr = find_related_adr(request.target)

  // Phase 2: 影響分析
  affected_files = grep_for_affected_files(request.target_modules)

  // Phase 3: 變更等級判定（from global_core.md L1-L4）
  level = determine_change_level(request, existing_spec, existing_adr)

  // Phase 4: 依等級路由
  MATCH level:
    L1:  // 細節修改
      UPDATE existing_spec  // 底部追加「變更記錄」
      LOG("L1 變更：更新既有 SPEC")

    L2:  // SPEC 推翻
      CANCEL existing_spec  // 標記 Cancelled + 原因
      spec = EXECUTE("make spec-new TITLE=\"{request.title}\"")
      PAUSE("L2 變更：舊 SPEC 已取消，新 SPEC 需確認")

    L3:  // ADR 推翻
      adr = EXECUTE("make adr-new TITLE=\"{request.title}\"")
      PAUSE("L3 變更：需要新 ADR（即使 hitl: minimal 也暫停）")
      UPDATE existing_adr.status = "Superseded by {adr.id}"
      // grep -r 掃描所有引用舊 ADR 的 SPEC
      CALL reverse_scan_adr(existing_adr.id)

    L4:  // 方向 Pivot
      PAUSE("L4 方向 Pivot：暫停所有進行中的 SPEC 開發")
      PRESENT full_impact_assessment
      AWAIT human_direction

  // Phase 5: 更新測試
  IDENTIFY affected_tests
  UPDATE or ADD tests to reflect new behavior
  EXECUTE("make test-filter FILTER={spec.filter}")

  // Phase 6: 實作
  IMPLEMENT changes

  // Phase 7: 驗證（含 autonomous 三重防護）
  IF autonomous_enabled:
    result = CALL auto_fix_loop("make test")
    IF result.guard_triggered:
      PAUSE("auto_fix_loop 防護觸發：{result.guard_type}，需人類介入")
  ELSE:
    EXECUTE("make test")
  CALL verify_stable_state(spec)

  // Phase 8: 文件管線
  CALL documentation_pipeline(spec, task_type=MODIFICATION)

  RETURN completion_report(spec)
```

### D4. TASK_REMOVAL（移除功能）

> 全新工作流。移除比新增更危險——殘留比缺少更有害。

```
FUNCTION execute_removal(request):

  // Phase 1: 識別移除範圍
  target = identify_removal_target(request)

  // Phase 2: 依賴分析（最關鍵的步驟）
  dependents = {
    code_refs:    grep -r "{target}" --include="*.{go,ts,py,java,...}",
    test_refs:    grep -r "{target}" in test directories,
    doc_refs:     grep -r "{target}" in docs/,
    config_refs:  grep -r "{target}" in config files,
    spec_refs:    grep -r "{target}" in docs/specs/,
    adr_refs:     grep -r "{target}" in docs/adr/
  }

  PRESENT("移除影響分析：")
  PRESENT("  程式碼引用：{LEN(dependents.code_refs)} 處")
  PRESENT("  測試引用：  {LEN(dependents.test_refs)} 處")
  PRESENT("  文件引用：  {LEN(dependents.doc_refs)} 處")
  PRESENT("  設定引用：  {LEN(dependents.config_refs)} 處")

  IF LEN(dependents.code_refs) > 0:
    PAUSE("以下模組依賴即將移除的功能，請確認移除策略")

  // Phase 3: 外部消費者評估
  IF target.has_external_consumers OR target.is_public_api:
    PRESENT("⚠️ 外部消費者存在，建議分階段移除：")
    PRESENT("  Phase 1: 標記 DEPRECATED + 設定清理期限")
    PRESENT("  Phase 2: 到期後執行移除")
    MARK target as DEPRECATED
    PAUSE("請決定：立即移除 or 分階段 deprecation")

  // Phase 4: 架構評估
  IF target.is_module OR target.is_service OR target.is_api_endpoint:
    adr = EXECUTE("make adr-new TITLE=\"REMOVE-{target.name}\"")
    adr.context = "為什麼移除 {target.name}"
    PAUSE("架構級移除，需 ADR 審核")

  // Phase 5: SPEC
  spec = EXECUTE("make spec-new TITLE=\"REMOVE-{target.name}\"")
  FILL spec:
    Goal: "安全移除 {target.name} 及所有引用"
    Side Effects: dependents list
    Edge Cases:
      Rollback Plan: 如何還原
      Data Impact: 使用者資料是否受影響
      API Breaking Change: 是否影響外部消費者
    Done When:
      - grep -r "{target}" returns 0 results（排除 docs/adr/、CHANGELOG）
      - make test 通過
      - 無孤立 imports / configs

  // Phase 6: 執行移除（順序重要）
  // 6a: 先更新依賴方（移除引用、更新 imports）
  FOR dep IN dependents.code_refs:
    UPDATE dep to remove dependency on target

  // 6b: 清理測試
  REMOVE tests that ONLY test the removed target
  UPDATE tests that reference the target alongside other features

  // 6c: 移除目標代碼
  REMOVE target files
  // 注意：檔案刪除在 autonomous 模式仍需 PAUSE（鐵則）

  // 6d: 清理設定
  REMOVE config entries referencing target
  REMOVE environment variables specific to target

  // Phase 7: 驗證
  EXECUTE("make test")  // 全套
  result = EXECUTE("grep -r \"{target.identifiers}\"")
  IF result.has_matches:
    // 排除合理殘留（CHANGELOG 歷史記錄、ADR 記錄）
    unexpected = filter_out_acceptable(result, ["CHANGELOG", "docs/adr/"])
    IF unexpected.not_empty:
      WARN("仍有殘留引用：{unexpected}")
      FIX unexpected references

  // Phase 8: 文件管線
  CALL documentation_pipeline(spec, task_type=REMOVAL)

  RETURN completion_report(spec)
```

### D5. TASK_GENERAL（複合需求）

```
FUNCTION execute_general(request):

  // Phase 1: 深度分析
  analysis = analyze_requirement(request)

  // Phase 2: 分解為子任務
  sub_tasks = decompose(analysis)
  FOR sub_task IN sub_tasks:
    sub_task.type = classify_task(sub_task)

  // Phase 3: 向人類確認拆解
  PRESENT("需求分析結果：")
  FOR sub_task IN sub_tasks:
    PRESENT("  {sub_task.id}: [{sub_task.type}] {sub_task.description}")
  PAUSE("請確認任務拆解是否正確")

  // Phase 4: 執行
  IF mode == multi-agent AND LEN(sub_tasks) > 1:
    // 多 Agent 並行（需符合 multi_agent.md 的低耦合要求）
    CALL multi_agent_dispatch(sub_tasks)
  ELSE:
    FOR sub_task IN sub_tasks:
      MATCH sub_task.type:
        NEW_FEATURE:   execute_new_feature(sub_task)
        BUGFIX:        execute_bugfix(sub_task)
        MODIFICATION:  execute_modification(sub_task)
        REMOVAL:       execute_removal(sub_task)

  // Phase 5: 跨任務整合驗證
  EXECUTE("make test")  // 全套

  // Phase 6: 統一文件管線
  CALL documentation_pipeline(sub_tasks, task_type=GENERAL)

  RETURN completion_report(sub_tasks)
```

---

## Part E: 文件產出管線

所有任務類型共用，確保文件產出的一致性與完整性。

```
FUNCTION documentation_pipeline(spec_or_tasks, task_type):

  artifacts = []

  // ─── 1. CHANGELOG.md ───
  IF NOT trivial:
    section = MATCH task_type:
      NEW_FEATURE  → "### Added"
      BUGFIX       → "### Fixed"
      MODIFICATION → "### Changed"
      REMOVAL      → "### Removed"
      GENERAL      → 依各子任務分別歸類
    UPDATE "CHANGELOG.md" with section entry:
      "- {description} (SPEC-NNN)"
    artifacts.append("CHANGELOG.md")

  // ─── 2. README.md ───
  IF spec.changes_user_facing_behavior:
    UPDATE "README.md" affected sections
    artifacts.append("README.md")

  // ─── 3. docs/architecture.md ───
  IF spec.related_adr OR task_type == REMOVAL:
    UPDATE "docs/architecture.md"
    artifacts.append("docs/architecture.md")

  // ─── 4. OpenAPI spec ───
  IF openapi_enabled AND spec.changes_api:
    UPDATE openapi spec file
    artifacts.append("openapi spec")

  // ─── 5. ADR 狀態 ───
  IF task_type == REMOVAL AND spec.related_adr:
    UPDATE adr.status = "Deprecated"
    EXECUTE("grep -r \"ADR-{adr.id}\"")  // 反向掃描

  // ─── 6. SPEC 完成更新 ───
  UPDATE spec:
    Done When: 所有項目打勾 ✅
    Traceability: 回填實作檔案 + 測試檔案 + 最後驗證日期（今天）
    // 在 SPEC 底部追加完成時間戳：
    // | **完成時間** | YYYY-MM-DD HH:MM |

  // ─── 7. Session checkpoint ───
  EXECUTE("make session-checkpoint NEXT=\"{next_task_or_done}\"")

  LOG("文件管線完成，已更新 {LEN(artifacts)} 個文件")
  RETURN artifacts
```

---

## Part F: 完成報告

```
FUNCTION completion_report(spec):

  report = {
    task_type:          spec.task_type,
    spec_id:            spec.id,
    related_adr:        spec.related_adr or "N/A",
    files_modified:     list_modified_files(),
    files_created:      list_created_files(),
    files_deleted:      list_deleted_files(),
    tests_added:        count_new_tests(),
    tests_result:       "make test" result summary,
    docs_updated:       list_updated_docs(),
    changelog_entry:    spec.changelog_entry,
    commit_tags:        [bug_tag or feature_tag],
    health_improvement: {
      blockers:       before → after,
      warnings:       before → after,
      test_coverage:  before% → after%
    },
    next_steps:         remaining_todos or "None"
  }

  PRESENT("═══════════════════════════════════════")
  PRESENT("  任務完成報告")
  PRESENT("═══════════════════════════════════════")
  PRESENT("  類型：{report.task_type}")
  PRESENT("  SPEC：{report.spec_id}")
  PRESENT("  修改：{LEN(report.files_modified)} 檔案")
  PRESENT("  新增：{LEN(report.files_created)} 檔案")
  PRESENT("  刪除：{LEN(report.files_deleted)} 檔案")
  PRESENT("  測試：+{report.tests_added}，{report.tests_result}")
  PRESENT("  文件：{report.docs_updated}")
  PRESENT("  健康：blockers {report.health_improvement.blockers}")
  PRESENT("═══════════════════════════════════════")

  RETURN report
```

---

## Part G: Multi-Agent 整合

> **Routing only.** Worker 基礎規則見 `multi_agent.md`，autonomous Worker 規則見 `autonomous_dev.md`「Multi-Agent 整合」。

當 `mode: multi-agent` 且 TASK_GENERAL 分解出多個獨立子任務時：

```
FUNCTION multi_agent_dispatch(sub_tasks):

  // 每個子任務建立 Task Manifest（遵循 multi_agent.md 格式）
  FOR sub_task IN sub_tasks:
    manifest = {
      task_id:   "TASK-{NNN}",
      workflow:  sub_task.type,  // NEW_FEATURE, BUGFIX, etc.
      scope:     infer_scope(sub_task),
      input:     [sub_task.spec],
      output:    infer_outputs(sub_task),
      done_when: sub_task.spec.done_when
    }

  // 遵循 multi_agent.md 的分派流程
  CALL orchestrator_dispatch(manifests)

  // 每個 Worker 內部執行對應的任務工作流
  // Worker 的 autonomous 規則由 autonomous_dev.md 的 Worker 層定義

  // 完成後：跨任務整合測試
  EXECUTE("make test")
```

---

## Part H: Helper Function 定義

> 以下定義 task_orchestrator 內部呼叫的 helper function。已在其他 Profile 定義的函數僅列交叉引用。

### 審計用函數

```
is_core_module(file):
  // 判定檔案是否屬於核心模組（核心模組無測試 → BLOCKER）
  匹配路徑模式：auth/, payment/, data/, security/, core/, api/, model/
  若專案根目錄有 .asp-audit-config.yaml → 使用自定義 patterns
  預設不確定 → 視為非核心（WARNING 而非 BLOCKER）

identify_major_modules():
  // 列出專案主要模組，用於 SPEC 覆蓋檢查
  掃描 src/（或語言慣例根目錄：cmd/, lib/, app/, packages/）下的一級目錄
  排除：vendor/, node_modules/, .venv/, test/, tests/, __pycache__, .git/
  回傳目錄名稱列表

has_corresponding_test(file, test_files):
  // 判定 source file 是否有對應測試
  語言慣例：
    Go:     {name}_test.go
    Python: test_{name}.py 或 {name}_test.py
    TS/JS:  {name}.test.ts 或 {name}.spec.ts 或 {name}.test.js
    Java:   {Name}Test.java
  匹配策略：basename 去除副檔名，在 test_files 中模糊比對
  回傳 true/false

has_implementation_code(adr):
  // 判定 ADR 是否已有對應的實作代碼（Draft + 實作 → BLOCKER）
  EXECUTE: grep -r "ADR-{adr.id}" --include="*.go" --include="*.ts" --include="*.py" --include="*.java" . | grep -v docs/ | grep -v CHANGELOG
  有結果 → true
```

### 任務分解函數

```
analyze_requirement(request):
  // 將自然語言需求結構化
  1. 關鍵字提取 → grep 全專案 → 識別涉及的檔案
  2. 從檔案路徑推導涉及模組
  3. 分析 import/require 圖 → 識別模組間依賴
  4. 回傳 {
       modules: ["auth", "api"],        // 涉及的模組
       dependencies: [("auth", "api")], // 模組間依賴邊
       estimated_files: 12,             // 預估影響檔案數
       complexity: "medium"             // low: ≤3 files, medium: 4-15, high: >15
     }

decompose(analysis):
  // 將結構化分析拆解為可獨立執行的子任務
  規則：
    - 以模組邊界分割，每個子任務的修改檔案集合不重疊
    - 有跨模組依賴 → 串行（標記 depends_on）
    - 無依賴 → 可並行
  回傳 [{
    id: "SUB-1",
    description: "...",
    modules: ["auth"],
    estimated_files: ["src/auth/handler.go", ...],
    depends_on: []  // 或 ["SUB-2"]
  }]
```

### 工作流判斷函數

```
determine_change_level(request, existing_spec, existing_adr):
  // 判定 MODIFICATION 的變更等級（L1-L4）

  // L4: 產品方向轉變（多個 SPEC/ADR 失效）
  invalidated_specs = find_specs_invalidated_by(request)
  invalidated_adrs = find_adrs_invalidated_by(request)
  IF LEN(invalidated_specs) > 2 OR LEN(invalidated_adrs) > 1:
    RETURN L4

  // L3: ADR 層級技術決策被推翻
  IF existing_adr AND request.contradicts(existing_adr.decision):
    RETURN L3

  // L2: SPEC Goal 被改變，或規模超出既有 SPEC 範圍
  IF existing_spec AND request.changes_goal(existing_spec):
    RETURN L2
  affected = grep_for_affected_files(request.target_modules)
  IF LEN(affected) > 10 AND NOT existing_spec.covers(request.scope):
    RETURN L2

  // L1: SPEC 內部調整（Goal 不變）
  RETURN L1

  // ── 判定範例 ──
  // | 場景                              | 等級 | 理由                         |
  // |-----------------------------------|------|------------------------------|
  // | 新增 optional API 欄位            | L1   | Goal 不變，edge case 追加    |
  // | 新增 OAuth Provider（已有 auth SPEC）| L2 | 新 auth flow 超出原 SPEC     |
  // | 從 REST 改 GraphQL                | L3   | ADR 層級技術棧變更           |
  // | B2C → B2B 轉型                    | L4   | 多個 SPEC/ADR 失效           |
  // 不確定時 → 視為高一級（保守原則）
```

```
meets_postmortem_criteria(severity, retry_count):
  // → 詳見 global_core.md「Postmortem 觸發條件」
  // 簡要：severity >= HIGH，或 retry_count >= 3，或影響生產環境
  RETURN severity >= HIGH OR retry_count >= 3 OR affected_production
```

### 交叉引用（已在其他 Profile 定義）

| 函數 | 定義位置 | 用途 |
|------|----------|------|
| `scan_state_dependencies()` | `global_core.md`「State Dependency Scan」 | Bug 修復後掃描狀態依賴 |
| `reverse_scan_adr(adr_id)` | `global_core.md`「ADR 反向掃描」 | L3 變更時掃描受影響 SPEC |
| `pre_commit_checklist()` | `system_dev.md`「提交前自審清單」 | 提交前最終檢查 |
| `verify_stable_state(spec)` | `system_dev.md`「穩定性驗證」 | 確認系統穩定 |
| `auto_fix_loop()` | `autonomous_dev.md`（含三重防護） | 自動修復循環（oscillation/cascade/smuggling 偵測） |
| `design_gate(spec)` | `design_dev.md`「Design Gate」 | 設計規範驗證 |
| `openapi_gate(spec)` | `openapi.md`「OpenAPI Gate」 | API 規格驗證 |

---

## 與其他 Profile 的關係

```
task_orchestrator.md
  ├── 依賴 global_core.md（鐵則 + 文件同步 + 迴歸預防）
  ├── 依賴 system_dev.md（ADR/SPEC/TDD 流程 + Gates + Hotfix）
  ├── 可選 autonomous_dev.md（auto_fix_loop + 自主決策邊界）
  ├── 可選 multi_agent.md（並行任務分派 + 文件鎖定）
  ├── 可選 vibe_coding.md（HITL 等級 + context 管理）
  ├── 可選 design_dev.md（Design Gate）
  ├── 可選 openapi.md（OpenAPI Gate）
  ├── 可選 guardrail.md（敏感資訊保護）
  └── 可選 rag_context.md（歷史教訓查詢）
```

健康審計是 task_orchestrator 的獨有功能。
任務工作流則是將既有 Profile 的規則串接成端到端流程。
