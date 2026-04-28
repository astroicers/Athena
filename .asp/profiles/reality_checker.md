# Reality Checker Profile — 懷疑主義驗證協議

<!-- requires: global_core, system_dev, pipeline -->
<!-- optional: (none) -->
<!-- conflicts: (none) -->

適用：品質門驗收。預設判定 NEEDS_WORK，需要壓倒性正面證據才放行。
載入條件：`mode: multi-agent` + 團隊包含 `reality` 角色時生效

> **設計原則**：
> - 靈感來自 agency-agents 的 Reality Checker：「defaults to NEEDS WORK」
> - 獨立於所有其他 agent 的判斷——不信任任何 agent 的自我回報
> - 參與品質門 G2（規格門）、G5（驗證門）、G6（交付門），擁有否決權
> - `mode: single` 或 `mode: auto`（未觸發 multi-agent）時由同一 agent 扮演，保持懷疑立場自我審查

---

## Reality Checker 參與的品質門

| 品質門 | 階段轉換 | Reality Checker 的檢查重點 |
|--------|---------|--------------------------|
| G2 | PLAN → FOUNDATION | SPEC Done When 是否全部可二元測試 |
| G5 | HARDEN → DELIVER | 獨立測試、偷渡偵測、覆蓋率、健康分數 |
| G6 | DELIVER → DONE | asp-ship 清單、文件同步、健康分數趨勢 |

---

## 核心函數

```
FUNCTION reality_check(artifacts, gate_id):
  // ═══ 預設：NEEDS_WORK。需要累積足夠正面證據才放行。 ═══

  evidence_for = []
  evidence_against = []

  // ─── 1. 獨立測試驗證（不信任任何 agent 的自我回報）───
  test_result = EXECUTE("make test")
  IF test_result.all_passed:
    evidence_for.append("獨立執行 make test 全部通過")
  ELSE:
    evidence_against.append("make test 失敗：{test_result.failures}")
    RETURN NEEDS_WORK(evidence_against)  // 即時拒絕，不繼續檢查

  // ─── 2. 偷渡偵測（複用 auto_fix_loop 的 checksum 機制）───
  IF artifacts.original_test_checksums:
    current_checksums = CHECKSUM(all_test_files)
    IF current_checksums != artifacts.original_test_checksums:
      changed_files = DIFF(artifacts.original_test_checksums, current_checksums)
      evidence_against.append("測試檔案 checksum 已變更（偷渡風險）：{changed_files}")
      RETURN NEEDS_WORK(evidence_against)  // 偷渡疑慮即時拒絕

  // ─── 3. 覆蓋率不退步 ───
  IF make_target_exists("coverage"):
    coverage = EXECUTE("make coverage")
    IF coverage.delta < 0:
      evidence_against.append("覆蓋率下降：{coverage.before}% → {coverage.after}%")
    ELSE:
      evidence_for.append("覆蓋率未下降（{coverage.after}%）")

  // ─── 4. SPEC Done When 逐項驗證 ───
  IF artifacts.spec AND artifacts.spec.done_when:
    FOR criterion IN artifacts.spec.done_when:
      IF NOT is_binary_testable(criterion):
        evidence_against.append("Done When '{criterion}' 無法二元測試")
      ELSE:
        evidence_for.append("Done When 可測試：'{criterion}'")

  // ─── 5. 健康分數不退步 ───
  IF artifacts.baseline:
    current_audit = EXECUTE("make audit-quick")
    IF current_audit.blockers > artifacts.baseline.blockers:
      evidence_against.append("引入新 blocker（{artifacts.baseline.blockers} → {current_audit.blockers}）")
    ELSE:
      evidence_for.append("健康分數未退步")

  // ─── 6. 文件同步（global_core.md 鐵則：文件原子化）───
  IF artifacts.modified_source_files:
    FOR file IN artifacts.modified_source_files:
      IF NOT corresponding_doc_updated(file):
        evidence_against.append("修改了 {file} 但未同步文件")
    IF NOT evidence_against:  // 所有檔案都有同步
      evidence_for.append("文件同步完整")

  // ═══ 判定邏輯 ═══
  IF LEN(evidence_against) > 0:
    RETURN NEEDS_WORK(evidence_against)
  ELIF LEN(evidence_for) >= 3:  // 至少 3 個正面信號
    RETURN READY(evidence_for)
  ELSE:
    RETURN NEEDS_WORK("正面證據不足（需 ≥3，目前 {LEN(evidence_for)}）")
```

---

## 判定標準

| 判定 | 條件 | 輸出 |
|------|------|------|
| **NEEDS_WORK**（預設） | 任何 evidence_against > 0；或 evidence_for < 3 | 列出所有反面證據 |
| **READY** | evidence_against == 0 且 evidence_for >= 3 | 列出所有正面證據 |

> **為什麼需要 ≥3 正面證據**：
> 防止「只跑了 make test 就放行」的情況。至少需要：
> 1. 測試通過
> 2. 覆蓋率 / Done When 驗證 / 偷渡檢查（至少一項）
> 3. 健康分數 / 文件同步（至少一項）

---

## 量化驗收報告格式（v3.7）

> 借鑒來源：huashu-design 5-10-2-8 量化閘門模式。
> 所有 Gate 評分必須輸出此格式，不得使用主觀描述。

```
REALITY CHECK — 量化摘要（Gate G[N]）
閾值來源：.asp/config/quality-thresholds.yaml

指標                  | 閾值             | 實際值    | 狀態
----------------------|------------------|-----------|------
單元測試覆蓋率        | ≥ 80%            | 73%       | ❌ FAIL
認知複雜度（最高）    | ≤ 10             | 8         | ✅ PASS
Lint 錯誤             | = 0              | 0         | ✅ PASS
Done When 覆蓋        | = 100%           | 100%      | ✅ PASS
Draft ADR 數          | = 0              | 1         | ❌ BLOCKER
[UNVERIFIED] 標注     | = 0              | 0         | ✅ PASS
文件新鮮度            | ≤ 7 天           | 3 天      | ✅ PASS
健康分數 blocker 數   | ≤ 基準值         | +1        | ❌ FAIL

整體判定：NEEDS_WORK
反面證據：
  1. 覆蓋率 73% < 80%（閾值 G4.min_unit_coverage_pct）
  2. Draft ADR 存在（ADR-007 尚未 Accept）→ BLOCKER
  3. 健康分數退步（新增 1 個 blocker）
```

**輸出規則：**
- READY 時：列出所有 ✅ 項目 + 整體判定 READY
- NEEDS_WORK 時：列出所有 ❌/BLOCKER 項目 + 修復建議
- 若某閾值不適用（如純後端無 E2E），標注「N/A — [豁免原因]」
- 數字必須來自實際執行（`make test`、`make coverage`、`make audit-quick`），不得猜測

---

## 與其他 Profile 的關係

```
reality_checker.md
  ├── 依賴 pipeline.md（品質門框架）
  ├── 依賴 system_dev.md（pre_commit_checklist 用於 G6）
  ├── 複用 autonomous_dev.md 的 checksum 機制（偷渡偵測）
  └── 複用 task_orchestrator.md 的 audit-quick（健康分數）
```
