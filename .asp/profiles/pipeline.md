# Pipeline Profile — 6 階段品質管線

<!-- requires: global_core, system_dev, task_orchestrator -->
<!-- optional: multi_agent, autonomous_dev, reality_checker, dev_qa_loop, escalation -->
<!-- conflicts: (none) -->

適用：所有任務類型。將 task_orchestrator.md 的隱式工作流轉為顯式管線 + 品質門。
載入條件：`mode: multi-agent` 時自動載入，`mode: auto` 時按需動態載入

> **設計原則**：
> - 不重新發明流程——在既有 execute_*() Phase 之間加上品質門
> - `mode: single` 時管線邏輯由 task_orchestrator.md 的 execute_*() 內建處理，無需本 profile
> - `mode: auto` 時由 auto_select_mode() 動態判斷是否載入
> - `mode: multi-agent` 時各階段由專精角色負責

---

## 管線階段定義

```
SPECIFY ──G1──▶ PLAN ──G2──▶ FOUNDATION ──G3──▶ BUILD ──G4──▶ HARDEN ──G5──▶ DELIVER ──G6──▶ DONE
```

### 階段 ↔ Agent ↔ Gate 映射

| 階段 | 對應 execute_new_feature() Phase | 主要 Agent | 支援 Agent | 品質門 |
|------|--------------------------------|-----------|-----------|--------|
| **SPECIFY** | Phase 1: 架構影響評估 | arch, dep-analyst | — | G1 |
| **PLAN** | Phase 2: SPEC 建立 + Phase 3: Gates | spec | reality | G2 |
| **FOUNDATION** | Phase 5: TDD 測試撰寫 | tdd | qa | G3 |
| **BUILD** | Phase 6: 實作 | impl | integ | G4 |
| **HARDEN** | Phase 7: 驗證 + Phase 8: 提交前自審 | qa, sec | reality | G5 |
| **DELIVER** | Phase 9: 文件管線 + Phase 10: 完成報告 | doc | reality | G6 |

### 階段可跳過規則

非所有任務都需要完整 6 階段。根據 team_compositions.yaml 的 pipeline_phases 決定：

| 場景 | 跳過的階段 | 原因 |
|------|----------|------|
| BUGFIX_trivial | SPECIFY, PLAN, FOUNDATION, DELIVER | 快速路徑：直接 BUILD → HARDEN |
| BUGFIX_hotfix | SPECIFY, PLAN, FOUNDATION | 快速路徑：BUILD → HARDEN → DELIVER |
| MODIFICATION_L1_L2 | SPECIFY | 無架構影響 |

---

## 品質門定義

### G1: Architecture Gate（SPECIFY → PLAN）

```
FUNCTION evaluate_G1(artifacts):
  checks = []

  IF artifacts.requires_adr:
    IF NOT exists(artifacts.adr) OR artifacts.adr.status != "Accepted":
      RETURN GATE_FAIL("ADR 不存在或非 Accepted 狀態（鐵則）")
    checks.append("ADR Accepted ✅")

  IF artifacts.dependency_graph:
    IF has_cycle(artifacts.dependency_graph):
      RETURN GATE_FAIL("依賴圖存在循環")
    checks.append("依賴圖無環 ✅")

  IF NOT artifacts.requires_adr AND NOT artifacts.dependency_graph:
    checks.append("無架構影響，G1 自動通過 ✅")

  RETURN GATE_PASS(evidence=checks)
```

### G2: Specification Gate（PLAN → FOUNDATION）

```
FUNCTION evaluate_G2(artifacts):
  checks = []
  issues = []

  // SPEC 七欄位完整性
  required_fields = ["Goal", "Inputs", "Expected Output", "Side Effects",
                     "Edge Cases", "Done When", "Traceability"]
  FOR field IN required_fields:
    IF NOT artifacts.spec.has(field):
      issues.append("SPEC 缺少欄位：{field}")

  // Done When 可二元測試
  FOR criterion IN artifacts.spec.done_when:
    IF NOT is_binary_testable(criterion):
      issues.append("Done When '{criterion}' 無法二元測試")

  IF issues:
    RETURN GATE_FAIL(issues)

  checks.append("SPEC 七欄位完整 ✅")
  checks.append("Done When 全部可二元測試 ✅")

  // Reality Checker 參與（如果 team 包含 reality）
  IF "reality" IN current_team:
    reality_verdict = reality_check(artifacts, "G2")
    IF reality_verdict.status == "NEEDS_WORK":
      RETURN GATE_FAIL(reality_verdict.evidence)
    checks.append("Reality Checker 通過 ✅")

  // v3.2: Gherkin 場景強制驗證
  IF severity != TRIVIAL:
    // 測試矩陣必須存在
    IF NOT spec.has_test_matrix:
      issues.append("🔴 缺少測試矩陣（非 trivial 任務必須填寫）")
    ELSE:
      positive_count = count(row FOR row IN spec.test_matrix IF row.type == "正向")
      negative_count = count(row FOR row IN spec.test_matrix IF row.type == "負向")
      IF positive_count == 0:
        issues.append("🔴 測試矩陣缺少正向案例（至少 1 個）")
      IF negative_count == 0:
        issues.append("🔴 測試矩陣缺少負向案例（至少 1 個）")

    // Gherkin 場景必須存在（config_only 豁免）
    IF NOT config_only AND NOT spec.has_scenarios:
      issues.append("🔴 缺少 Gherkin 驗收場景（非 trivial 任務必須撰寫）")

    IF spec.has_scenarios:
      // 矩陣 ↔ 場景引用一致性
      FOR row IN spec.test_matrix:
        IF row.scenario_ref AND row.scenario_ref NOT IN spec.scenario_ids:
          issues.append("矩陣 {row.id} 引用場景 {row.scenario_ref} 不存在")

      // Bug 修復必須有重現場景
      IF task_type == "BUGFIX":
        has_repro = any(s.name CONTAINS "重現" OR s.name CONTAINS "reproduce" OR s.name CONTAINS "N1" FOR s IN spec.scenarios)
        IF NOT has_repro:
          issues.append("🔴 Bug 修復缺少重現場景")

      // 場景品質檢查（攔截敷衍場景）
      FOR scenario IN spec.scenarios:
        IF LEN(scenario.then_clauses) < 1:
          issues.append("場景 {scenario.id} 沒有 Then 斷言（敷衍場景）")
        IF scenario.given_clauses IS EMPTY AND scenario.background IS EMPTY:
          issues.append("場景 {scenario.id} 缺少 Given 前置條件")
        IF scenario.name MATCHES "it works|正常運作|成功|OK|works fine":
          issues.append("場景 {scenario.id} 名稱過於模糊：'{scenario.name}'")

  // v3.3: Observability 驗證（使用者面向功能必填）
  IF spec.is_user_facing OR spec.is_backend_api OR spec.is_data_processing:
    IF NOT spec.has_observability:
      issues.append("🔴 使用者面向功能缺少可觀測性定義（Observability 區塊）")
    ELSE:
      checks.append("Observability 已定義 ✅")

  RETURN GATE_PASS(evidence=checks)
```

### G3: Test Readiness Gate（FOUNDATION → BUILD）

```
FUNCTION evaluate_G3(artifacts):
  checks = []
  issues = []

  // 每個 Done When 有對應測試
  FOR criterion IN artifacts.spec.done_when:
    IF NOT has_test_for(criterion, artifacts.test_files):
      issues.append("Done When '{criterion}' 無對應測試")

  // 測試全部 FAIL（證明它們在測試東西）
  test_result = EXECUTE("make test-filter FILTER={artifacts.spec.filter}")
  IF test_result.all_passed:
    issues.append("測試在實作前就全部通過——測試可能沒有在測東西")
  ELIF test_result.compilation_error:
    issues.append("測試編譯失敗：{test_result.error}")

  // v3.3: 測試品質檢查（防止空測試）
  FOR test_file IN artifacts.test_files:
    assertion_count = count_assertions(test_file)
    // count_assertions 依語言：
    //   Go: count("assert", "require.")  Python: count("assert")  TS/JS: count("expect(")
    IF assertion_count == 0:
      issues.append("測試檔案 {test_file} 沒有任何 assertion（空測試）")

  IF spec.has_scenarios:
    total_assertions = sum(count_assertions(f) FOR f IN artifacts.test_files)
    IF total_assertions < LEN(spec.scenarios):
      issues.append("assertion 總數（{total_assertions}）少於場景數（{LEN(spec.scenarios)}）")

  IF issues:
    RETURN GATE_FAIL(issues)

  checks.append("所有 Done When 有對應測試 ✅")
  checks.append("測試全部 FAIL（預期行為）✅")

  // v3.2: 場景 ↔ 測試映射驗證
  IF spec.has_scenarios:
    FOR scenario IN spec.scenarios:
      IF NOT has_test_for_scenario(scenario.id, artifacts.test_files):
        issues.append("場景 {scenario.id}（{scenario.name}）無對應測試")

    scenario_count = LEN(spec.scenarios)
    test_count = count_test_cases_for_spec(spec.id, artifacts.test_files)
    IF test_count < scenario_count:
      issues.append("測試數量（{test_count}）少於場景數量（{scenario_count}）")

  RETURN GATE_PASS(evidence=checks)
```

### G4: Implementation Gate（BUILD → HARDEN）

```
FUNCTION evaluate_G4(artifacts):
  checks = []
  issues = []

  // 測試通過
  test_result = EXECUTE("make test")
  IF NOT test_result.all_passed:
    issues.append("make test 失敗：{test_result.failures}")

  // Lint clean
  IF make_target_exists("lint"):
    lint_result = EXECUTE("make lint")
    IF lint_result.has_errors:
      issues.append("make lint 有 error")

  // Scope 未超出
  modified_files = git_diff_files()
  allowed_files = artifacts.task_manifest.scope.allow
  out_of_scope = [f FOR f IN modified_files IF NOT matches_scope(f, allowed_files)]
  IF out_of_scope:
    issues.append("修改了 scope 外的檔案：{out_of_scope}")

  // v3.3: TODO/FIXME/HACK 標記檢查
  marker_result = EXECUTE("grep -rn \"TODO\\|FIXME\\|HACK\\|XXX\" --include=\"*.{ext}\" {modified_files}")
  IF marker_result.has_matches:
    FOR match IN marker_result.matches:
      LOG_TECH_DEBT("code-marker: {match.file}:{match.line} — {match.content}")
    checks.append("⚠️ 發現 {marker_result.count} 個 TODO/FIXME 標記（已記錄為 tech-debt）")
  ELSE:
    checks.append("無新增 TODO/FIXME 標記 ✅")

  IF issues:
    RETURN GATE_FAIL(issues)

  checks.append("make test 全部通過 ✅")
  checks.append("make lint 無 error ✅")
  checks.append("修改範圍在 scope 內 ✅")
  RETURN GATE_PASS(evidence=checks)
```

### G5: Verification Gate（HARDEN → DELIVER）

```
FUNCTION evaluate_G5(artifacts):
  checks = []
  issues = []

  // QA 獨立驗證
  qa_verdict = qa_agent.independent_verify(artifacts)
  IF qa_verdict.status == "QA_FAIL":
    issues.append("QA 獨立驗證失敗：{qa_verdict.evidence}")

  // Security 審查
  IF "sec" IN current_team:
    sec_verdict = sec_agent.review(artifacts)
    IF sec_verdict.has_findings:
      issues.append("安全審查發現：{sec_verdict.findings}")

  // v3.3: 新增 warning 檢查
  IF make_target_exists("lint"):
    lint_result = EXECUTE("make lint")
    IF lint_result.warning_count > 0:
      checks.append("⚠️ lint 產生 {lint_result.warning_count} 個 warning")
      IF artifacts.baseline AND lint_result.warning_count > artifacts.baseline.get("lint_warning_count", 0):
        new_warnings = lint_result.warning_count - artifacts.baseline.lint_warning_count
        issues.append("新增 {new_warnings} 個 lint warning")

  // 偷渡偵測
  IF test_checksums_changed(artifacts.original_checksums, artifacts.current_checksums):
    issues.append("測試檔案 checksum 已變更（偷渡風險）")

  // 全專案 grep（global_core.md 鐵則：Bug 修復後無豁免）
  IF artifacts.task_type == "BUGFIX":
    grep_result = EXECUTE("grep -r \"{artifacts.bug_pattern}\" --include=\"*.{ext}\" .")
    IF grep_result.has_matches:
      issues.append("全專案 grep 發現 {grep_result.count} 處相同模式")

  // v3.3: Side Effects 驗證
  IF spec.side_effects AND LEN(spec.side_effects) > 0:
    FOR effect IN spec.side_effects:
      IF NOT has_verification_for(effect, spec.done_when, spec.test_matrix):
        issues.append("副作用 '{effect.description}' 缺少驗證（Done When 或測試矩陣無對應）")
    IF NOT issues:
      checks.append("Side Effects 全部有驗證 ✅")

  // v3.3: Rollback 測試驗證
  IF spec.rollback_plan:
    IF task_involves_architecture_change OR task_involves_schema_change:
      IF NOT spec.rollback_plan.tested:
        issues.append("🔴 架構/Schema 變更的 Rollback Plan 未經測試")
    ELSE:
      IF NOT spec.rollback_plan.tested:
        checks.append("⚠️ Rollback Plan 未經測試（建議但不強制）")

  IF issues:
    RETURN GATE_FAIL(issues)

  checks.append("QA 獨立驗證通過 ✅")
  IF "sec" IN current_team:
    checks.append("安全審查 clear ✅")
  checks.append("偷渡偵測通過 ✅")

  // Reality Checker 否決權
  IF "reality" IN current_team:
    reality_verdict = reality_check(artifacts, "G5")
    IF reality_verdict.status == "NEEDS_WORK":
      RETURN GATE_FAIL(reality_verdict.evidence)
    checks.append("Reality Checker 通過 ✅")

  RETURN GATE_PASS(evidence=checks)
```

### G6: Delivery Gate（DELIVER → DONE）

```
FUNCTION evaluate_G6(artifacts):
  checks = []
  issues = []

  // asp-ship 7 步清單
  ship_result = pre_commit_checklist()  // from system_dev.md
  IF ship_result.has_blockers:
    issues.append("asp-ship 有 BLOCKER：{ship_result.blockers}")

  // 健康分數不退步
  current_audit = EXECUTE("make audit-quick")
  IF current_audit.blockers > artifacts.baseline.blockers:
    issues.append("健康審計引入新 blocker（before: {artifacts.baseline.blockers}, after: {current_audit.blockers}）")

  IF issues:
    RETURN GATE_FAIL(issues)

  checks.append("asp-ship 7 步全綠 ✅")
  checks.append("健康分數未退步 ✅")

  // v3.3: Traceability 檔案存在驗證
  IF spec.traceability:
    FOR impl_file IN spec.traceability.impl_files:
      IF NOT exists(impl_file):
        issues.append("Traceability 引用的實作檔案不存在：{impl_file}")
    FOR test_file IN spec.traceability.test_files:
      IF NOT exists(test_file):
        issues.append("Traceability 引用的測試檔案不存在：{test_file}")
    IF NOT issues:
      checks.append("Traceability 檔案全部存在 ✅")

  // Reality Checker 否決權
  IF "reality" IN current_team:
    reality_verdict = reality_check(artifacts, "G6")
    IF reality_verdict.status == "NEEDS_WORK":
      RETURN GATE_FAIL(reality_verdict.evidence)
    checks.append("Reality Checker 通過 ✅")

  RETURN GATE_PASS(evidence=checks)
```

---

## 品質門評估邏輯

```
FUNCTION evaluate_gate(gate_id, artifacts, evaluating_agents):

  verdicts = {}
  FOR agent IN evaluating_agents:
    verdicts[agent.role] = agent.evaluate(gate_id, artifacts)

  // Reality Checker 有否決權（參與 G2, G5, G6）
  IF "reality" IN evaluating_agents:
    IF verdicts["reality"].status == "NEEDS_WORK":
      handoff = create_handoff(PHASE_GATE,
        gate_id = gate_id,
        final_verdict = "FAIL",
        blocking_agent = "reality",
        evidence = verdicts["reality"].evidence)
      RETURN GATE_FAIL(handoff)

  // 其他 agent 全部 PASS 才通過
  failures = [agent FOR agent, v IN verdicts IF v.status != "PASS"]
  IF failures:
    handoff = create_handoff(PHASE_GATE,
      gate_id = gate_id,
      final_verdict = "FAIL",
      blocking_agents = failures,
      evidence = collect_evidence(verdicts))
    RETURN GATE_FAIL(handoff)

  handoff = create_handoff(PHASE_GATE,
    gate_id = gate_id,
    final_verdict = "PASS",
    evidence = collect_evidence(verdicts))
  RETURN GATE_PASS(handoff)
```

---

## 管線執行包裝

```
FUNCTION execute_pipeline(task, team, phases):
  artifacts = { spec: task.spec, baseline: load_audit_baseline() }

  FOR phase IN phases:
    // 執行階段
    MATCH phase:
      SPECIFY:    artifacts.update(run_specify(task, team))
      PLAN:       artifacts.update(run_plan(task, team))
      FOUNDATION: artifacts.update(run_foundation(task, team))
      BUILD:      artifacts.update(run_build(task, team))
      HARDEN:     artifacts.update(run_harden(task, team))
      DELIVER:    artifacts.update(run_deliver(task, team))

    // 評估品質門（除最後一個階段外）
    gate = get_gate_for_phase(phase)
    IF gate:
      gate_agents = get_gate_agents(gate, team)
      result = evaluate_gate(gate, artifacts, gate_agents)

      IF result == GATE_FAIL:
        LOG("品質門 {gate.id} 未通過：{result.evidence}")
        // 品質門失敗不直接升級——回到當前階段的 agent 修正
        // 最多重試 2 次，超過走升級協議
        IF gate.retry_count >= 2:
          escalate(severity="P2", reason="品質門 {gate.id} 重試 2 次仍未通過", task_id=task.id)
        ELSE:
          gate.retry_count += 1
          RETRY current phase

  RETURN artifacts
```

---

## 與其他 Profile 的關係

```
pipeline.md
  ├── 依賴 task_orchestrator.md（execute_*() 是管線階段的實際邏輯）
  ├── 依賴 system_dev.md（pre_commit_checklist 用於 G6）
  ├── 可選 reality_checker.md（Reality Checker 參與 G2, G5, G6）
  ├── 可選 multi_agent.md（multi-agent 時各階段由不同 agent 負責）
  ├── 可選 dev_qa_loop.md（BUILD + HARDEN 階段的 Dev↔QA 迴路）
  └── 可選 escalation.md（品質門重試耗盡時的升級路由）
```
