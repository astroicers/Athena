---
name: asp-impact
description: |
  Dependency and impact analysis — build dependency graph, risk scoring, parallel markers.
  Triggers: impact, impact analysis, 影響, 影響分析, what does this affect
---

# ASP Impact — 依賴影響分析

## 前置條件

- 有明確的修改目標（模組、函數、API）
- 或由 Orchestrator 觸發作為 task decomposition 的一部分

## 工作流

### Step 1: 識別修改目標

確認要分析的修改範圍：
- 模組名稱
- 涉及的檔案路徑
- API endpoint（如適用）

### Step 2: 全專案掃描

```bash
# 程式碼引用
grep -rn "{target}" --include="*.{go,ts,py,java}" .

# 測試引用
grep -rn "{target}" tests/ test/ __tests__/

# 文件引用
grep -rn "{target}" docs/

# 設定引用
grep -rn "{target}" *.yaml *.yml *.json *.toml *.ini
```

### Step 3: 建立依賴圖

```
依賴方向：A → B 表示 A 依賴 B

{target_module}
  ├── 被依賴者（upstream）：{target} 依賴什麼
  └── 依賴者（downstream）：什麼依賴 {target}
```

### Step 4: 標記並行化

| 標記 | 意義 | 條件 |
|------|------|------|
| `[P]` | 可並行 | 無共享檔案、無 import 依賴 |
| `[S]` | 必須序列 | 有共享檔案或 import 依賴 |

### Step 5: 風險評分

| 風險等級 | 條件 |
|---------|------|
| 🔴 高 | 影響 >15 檔案、跨 3+ 模組、涉及 auth/payment/data |
| 🟡 中 | 影響 5-15 檔案、跨 2 模組 |
| 🟢 低 | 影響 <5 檔案、單一模組 |

### Step 6: 輸出報告

```markdown
## 影響分析報告

| 指標 | 值 |
|------|-----|
| 影響檔案數 | N |
| 影響模組數 | M |
| 風險等級 | 🔴/🟡/🟢 |
| 建議並行度 | K 軌 |

### 依賴圖
(Mermaid 或文字格式)

### 並行規劃
- Level 0 [P]: Task A, Task B
- Level 1 [S]: Task C (depends on A)
```

## 參考

- Dep Analyst 角色定義：`.asp/agents/dep-analyst.yaml`
- 依賴分析函數：`task_orchestrator.md` analyze_requirement(), decompose()
- 並行規劃：`multi_agent.md` plan_parallel_execution()
