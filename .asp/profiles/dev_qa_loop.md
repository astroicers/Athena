# Dev↔QA Loop Profile — 即時品質迴路

<!-- requires: global_core, system_dev, multi_agent -->
<!-- optional: autonomous_dev, pipeline, escalation -->
<!-- conflicts: (none) -->

適用：實作期間 QA agent 逐模組即時驗證，不等全部完成。
載入條件：`mode: multi-agent` 且團隊包含 `qa` 角色時生效

> **設計原則**：
> - 靈感來自 agency-agents 的 Dev↔QA Loop
> - 從「做完再驗」升級為「邊做邊驗」
> - 與 auto_fix_loop 互補：auto_fix_loop 是 impl agent 的內部自我修復，Dev↔QA Loop 是 impl + qa 的外部協作

---

## auto_fix_loop vs dev_qa_loop

| | auto_fix_loop | dev_qa_loop |
|---|---|---|
| **層級** | 低層（impl agent 內部） | 高層（impl + qa agent 協作） |
| **觸發者** | impl agent 自行跑測試 | qa agent 獨立驗證 |
| **信任模型** | impl 信任自己的測試結果 | qa 不信任 impl 的自我回報 |
| **防護** | 振盪/級聯/偷渡偵測 | 偷渡偵測 + 覆蓋率 + 獨立測試 |
| **定義位置** | autonomous_dev.md | 本檔案 |

---

## 核心函數

```
FUNCTION dev_qa_loop(task, impl_agent, qa_agent):

  modules = task.spec.affected_modules
  // affected_modules 來自 dep-analyst 的 analyze_requirement()
  // 如果沒有 dep-analyst（簡單任務），視整個 task 為單一 module

  FOR module IN modules:

    // ─── impl agent 寫一個模組 ───
    impl_result = impl_agent.implement(module)
    // impl 內部已跑過 auto_fix_loop（如果 autonomous: enabled）
    // impl_result 包含：
    //   - claimed_test_output: impl 自稱的測試結果
    //   - files_modified: 修改了哪些檔案
    //   - test_checksums_after: 修復後的測試檔案 checksums

    // ─── qa agent 立刻驗證這個模組 ───
    qa_result = qa_agent.verify_module(module, impl_result)

    IF qa_result.status == "QA_FAIL":
      // 即時回饋 — impl 修完這個模組才進下一個
      retry = 0
      WHILE retry < 3:
        // 產生 QA_FAIL 交接單（包含完整失敗原因）
        qa_handoff = create_handoff(TASK_COMPLETE,
          status = "failed",
          failure_context = qa_result)

        // impl 收到回饋修復
        fix_result = impl_agent.fix(module, qa_handoff)

        // qa 重新驗證
        qa_recheck = qa_agent.verify_module(module, fix_result)
        IF qa_recheck.status == "QA_PASS":
          BREAK
        retry += 1

      IF retry >= 3:
        // 模組級失敗 → 走升級協議
        IF escalation_loaded:
          escalate(severity="P2", reason="模組 {module} 在 Dev↔QA 迴路中 3 次驗證失敗", task_id=task.id, context={qa_result, impl_attempts: retry})
        ELSE:
          PAUSE_AND_REPORT("模組 {module} 在 Dev↔QA 迴路中 3 次驗證失敗")
        CONTINUE  // 跳到下一個 module，不執行下面的 QA PASS log

    LOG("模組 {module}: QA PASS（{retry} 次修復後）")

  // ─── 所有模組通過後：整合驗證 ───
  integration_result = qa_agent.verify_integration(task)
  IF integration_result.status == "QA_FAIL":
    IF escalation_loaded:
      escalate(severity="P2", reason="整合驗證失敗", task_id=task.id, context=integration_result)
    ELSE:
      PAUSE_AND_REPORT("整合驗證失敗")
```

---

## QA Agent 驗證函數

```
FUNCTION qa_verify_module(module, impl_result):
  evidence = []
  issues = []

  // 1. 獨立執行測試（不信任 impl 的 claimed_test_output）
  test_result = EXECUTE("make test-filter FILTER={module}")
  IF NOT test_result.all_passed:
    issues.append("獨立測試失敗：{test_result.failures}")

  // 2. 比對 impl 的自稱結果（信任但驗證）
  IF impl_result.claimed_test_output != test_result.output:
    issues.append("impl 自稱的測試結果與獨立驗證不符")

  // 3. 偷渡偵測
  current_checksums = CHECKSUM(test_files_for(module))
  IF current_checksums != impl_result.original_test_checksums:
    issues.append("測試檔案被修改（偷渡風險）")

  IF issues:
    RETURN QA_FAIL(issues)
  ELSE:
    evidence.append("獨立測試通過")
    evidence.append("impl 自我回報一致")
    evidence.append("偷渡偵測通過")
    RETURN QA_PASS(evidence)


FUNCTION qa_verify_integration(task):
  // 整合驗證：全套測試
  test_result = EXECUTE("make test")
  IF NOT test_result.all_passed:
    RETURN QA_FAIL(["整合測試失敗：{test_result.failures}"])
  RETURN QA_PASS(["make test 全套通過"])
```

---

## 與其他 Profile 的關係

```
dev_qa_loop.md
  ├── 依賴 multi_agent.md（需要多 agent 才有意義）
  ├── 互補 autonomous_dev.md（auto_fix_loop 是低層，dev_qa_loop 是高層）
  ├── 可選 escalation.md（模組級失敗走升級協議）
  └── 整合 pipeline.md（在 BUILD + HARDEN 階段運作）
```
