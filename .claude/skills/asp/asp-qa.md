---
name: asp-qa
description: |
  QA verification — independent testing, smuggling detection, coverage analysis.
  Triggers: verify, qa, 驗證, 品質, quality check
---

# ASP QA — 獨立品質驗證

## 前置條件

- 已收到 impl agent 的 TASK_COMPLETE 交接單
- 或直接由使用者觸發對指定範圍的品質驗證

## 核心原則

> **不信任任何 agent 的自我回報。** 所有結果必須獨立驗證。

## 工作流

### Step 1: 讀取交接單

讀取 `.agent-events/handoffs/` 中最新的 TASK_COMPLETE：
- 取得 impl agent 的 claimed_test_output
- 取得 original test checksums
- 取得修改的檔案清單

```bash
make agent-handoff-list
```

### Step 2: 獨立測試執行

```bash
make test-filter FILTER={scope}
```

比對 impl 的 claimed_test_output：
- 結果一致 ✅
- 結果不一致 🔴 → 記錄差異

### Step 3: 偷渡偵測

計算當前測試檔案的 checksum，與交接單中的 original checksums 比對：
- 未變更 ✅
- 已變更 🔴 → 列出被修改的測試檔案

### Step 4: 覆蓋率檢查

```bash
make coverage  # 如果目標存在
```

- 覆蓋率未下降 ✅
- 覆蓋率下降 🟡 → 記錄 delta

### Step 5: 全專案 grep（Bug 修復時）

如果是 BUGFIX 任務：

```bash
grep -r "{bug_pattern}" --include="*.{ext}" .
```

- 無其他相同模式 ✅
- 發現 N 處 🔴 → 列出位置

### Step 6: 產生判定

根據證據產生 QA_PASS 或 QA_FAIL：

| 判定 | 條件 |
|------|------|
| **QA_PASS** | Step 2-5 全部 ✅ 或 🟡 |
| **QA_FAIL** | 任何 Step 有 🔴 |

產生交接單：`make agent-handoff TEMPLATE=TASK_COMPLETE STATUS={pass|fail}`

## 參考

- QA 角色定義：`.asp/agents/qa.yaml`
- 偷渡偵測機制：`autonomous_dev.md` auto_fix_loop
- Dev↔QA 迴路：`.asp/profiles/dev_qa_loop.md`
