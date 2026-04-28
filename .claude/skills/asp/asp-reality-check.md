---
name: asp-reality-check
description: |
  Skeptical verification — defaults to NEEDS_WORK, requires overwhelming evidence to PASS.
  Triggers: reality check, 夠了嗎, is this ready, 能交了嗎, final check
---

# ASP Reality Check — 懷疑主義驗收

## 核心原則

> **預設判定：NEEDS_WORK。** 需要累積 ≥3 個正面證據、0 個反面證據才放行。

## 工作流

### Step 1: 獨立測試驗證

**不信任任何 agent 的自我回報。**

```bash
make test
```

- 全部通過 → +1 正面證據
- 任何失敗 → **立即 NEEDS_WORK**（不繼續檢查）

### Step 2: 偷渡偵測

比較測試檔案的 checksum（修改前 vs 現在）：
- 未變更 → +1 正面證據
- 已變更 → **立即 NEEDS_WORK**

### Step 3: 覆蓋率趨勢

```bash
make coverage  # 如果目標存在
```

- 覆蓋率未下降 → +1 正面證據
- 覆蓋率下降 → +1 反面證據

### Step 4: SPEC Done When 逐項驗證

逐項檢查 SPEC 的 Done When 條件：
- 每個條件都是二元可測試的 → +1 正面證據
- 有模糊條件 → +1 反面證據

### Step 5: 健康分數

```bash
make audit-quick
```

- 未引入新 blocker → +1 正面證據
- 引入新 blocker → +1 反面證據

### Step 6: 文件同步

檢查每個修改的 source file 是否有對應的文件更新：
- 全部同步 → +1 正面證據
- 有遺漏 → +1 反面證據

### Step 7: 判定

| 判定 | 條件 |
|------|------|
| **READY** ✅ | 反面證據 = 0 且 正面證據 ≥ 3 |
| **NEEDS_WORK** 🔴 | 反面證據 > 0 或 正面證據 < 3 |

輸出完整證據清單（正面 + 反面）。

## Common Rationalizations（AI 繞過時必讀）

> **執行此 skill 時，AI 必須先檢視此表。Reality Check 的本質是懷疑，任何試圖降低證據門檻都違反 skill 精神。**

| 藉口 | 反駁 |
|------|------|
| 「只有 2 個正面證據，但覆蓋率很高，應該放行」 | 不可。門檻是 ≥3 正面 + 0 反面。「覆蓋率高」是單一維度，不能替代獨立維度的驗證。 |
| 「測試 checksum 變了但我確認沒有竄改意圖」 | 「意圖」不可驗證。checksum 變動即 NEEDS_WORK，改回原樣或在 SPEC 中明確記錄測試重構理由。 |
| 「SPEC 的 Done When 本來就有點模糊，那是 SPEC 的問題不是我的問題」 | 模糊 Done When = +1 反面證據。發現模糊時應該回到 `/asp-plan` 修 SPEC，而非在 reality check 時放行。 |
| 「agent 回報測試通過了，不需要我再跑一次」 | 本 skill 第一條原則：**不信任任何 agent 的自我回報**。必須獨立執行 `make test`。 |
| 「健康分數只降了 1 分，算在誤差範圍內」 | baseline 比對沒有誤差範圍。降了就是反面證據。若認為 baseline 過嚴，應先重建 baseline。 |
| 「文件同步是 docs team 的事，不算在這次驗證」 | Step 6 明確要求修改的 source file 對應文件已同步。沒同步 = 反面證據，無豁免。 |
| 「只有 1 個反面證據，其他全正面，綜合起來 READY 吧」 | 反面證據 > 0 即 NEEDS_WORK。這不是加權平均，是 veto 制度。 |

---

## 參考

- Reality Checker 角色定義：`.asp/agents/reality.yaml`
- 驗證協議：`.asp/profiles/reality_checker.md`
- 品質門參與：G2, G5, G6（`.asp/profiles/pipeline.md`）
