---
name: asp-review
description: |
  Use when reviewing code, PRs, or specific changes for quality and compliance.
  Covers ADR compliance, test coverage, bug taxonomy, tech-debt, and doc sync.
  Triggers: review, code review, pr review, 審查, 幫我看, 程式碼審查, 看一下這段,
  check my code, review this, review PR, 幫我審查, 審核代碼, 這樣寫對嗎.
---

# ASP Review — 程式碼審查

## 適用場景

用戶提交代碼、PR 或特定變更，需要系統性審查。也適用於偷渡偵測的人工判斷場景。

---

## 審查前：確認範圍

詢問（或從上下文推斷）：
- **審查目標**：特定檔案？PR？整個 branch？
- **審查重點**：全面審查 或 特定面向（如只看安全性）

```bash
git diff main...HEAD --stat   # 若審查 branch
git show --stat               # 若審查最新 commit
```

---

## 6 個審查面向

### 面向 1：ADR 合規性

對照 `make adr-list` 的 Accepted ADR：

- 變更是否違反任何已接受的架構決策？
- 是否有 Draft ADR 對應的生產代碼被加入？（鐵則，直接 BLOCK）
- 若引入新的架構決策 → 提醒應先建立 ADR

**輸出格式：**
```
[ADR 合規] ✅ 無違反 / 🔴 BLOCK: 違反 ADR-NNN（說明）
```

---

### 面向 2：測試覆蓋

- 新功能是否有對應測試？
- 修復的 bug 是否有回歸測試（先 FAIL 後 PASS）？
- 測試是否測到了邊界條件和錯誤路徑？

**標記格式（若不足）：**
```
# tech-debt: HIGH test-pending [模組名] 缺少回歸測試 (DUE: YYYY-MM-DD)
```

**輸出格式：**
```
[測試覆蓋] ✅ 充足 / 🟡 不足：缺少 [具體描述]
```

---

### 面向 3：Bug 分類

發現 bug 時，使用標準分類標籤：

| 標籤 | 說明 | 範例 |
|------|------|------|
| `[bug:logic]` | 業務邏輯錯誤 | 條件判斷反向、計算公式錯誤 |
| `[bug:boundary]` | 邊界條件未處理 | 空值、空陣列、最大值溢出 |
| `[bug:race]` | 並發/競態條件 | 共享狀態無鎖、async 順序依賴 |
| `[bug:security]` | 安全漏洞 | SQL injection、未授權存取 |
| `[bug:perf]` | 效能問題 | N+1 查詢、記憶體洩漏 |
| `[bug:contract]` | API/介面合約破壞 | 回傳型別改變、欄位移除 |

**ASP 鐵則：發現任何 bug → 強制 grep 全專案找相同模式**

```bash
grep -r "相同 pattern" . --include="*.go"  # 或對應語言
```

**輸出格式：**
```
[Bug 分類] 🔴 發現 [bug:security] 於 path/to/file.go:42
  描述：[說明]
  全專案掃描：grep -r "pattern" .
  → 發現 N 處相同模式
```

---

### 面向 4：DEPRECATED 掃描

```bash
grep -r "DEPRECATED\|@deprecated\|// TODO: remove\|// FIXME" . --include="*.go"
```

- 新代碼是否使用了已標記廢棄的 API？
- 是否新增了 DEPRECATED 標記但未建立 tech-debt？

**輸出格式：**
```
[DEPRECATED] ✅ 無使用廢棄 API / 🟡 使用了廢棄 API：[說明]
```

---

### 面向 5：Tech Debt 標記品質

檢查此次變更新增的 `tech-debt:` 標記：

- 格式是否正確：`# tech-debt: [HIGH|MED|LOW] [CATEGORY] description (DUE: YYYY-MM-DD)`
- HIGH 是否有 DUE 日期？
- CATEGORY 是否使用標準值（test-pending, adr-pending, spec-pending, doc-stale, deprecated-cleanup, refactor, perf, security）？

**輸出格式：**
```
[Tech Debt] ✅ 格式正確 / 🟡 格式問題：[具體說明]
```

---

### 面向 6：文件同步

- 公開 API、CLI 介面、配置欄位是否已更新文件？
- CHANGELOG 是否記錄了用戶可見的變更？
- 相關 SPEC 的 `Implementation` 欄位是否已填入？

**輸出格式：**
```
[文件同步] ✅ 已同步 / 🟡 待補：[說明]
```

---

## 偷渡偵測的人工判斷

若審計工具（`autonomous_dev.md`）觸發偷渡偵測警告，需人工判斷：

**排除誤報的條件（全部滿足才算正常重構）：**
1. 測試邏輯未改變（只改了結構，沒有移除/修改 assertion）
2. 測試數量未減少
3. 覆蓋的業務場景集合未縮小

若以上皆滿足 → 誤報，繼續。
若任一不滿足 → 真正的偷渡，需回滾測試改動。

---

## 審查結論

```
📋 程式碼審查結論
================================

[ADR 合規]   ✅/🔴/🟡
[測試覆蓋]   ✅/🔴/🟡
[Bug 分類]   ✅/🔴/🟡  (N 個 bug 發現)
[DEPRECATED] ✅/🔴/🟡
[Tech Debt]  ✅/🔴/🟡
[文件同步]   ✅/🔴/🟡

================================
結論：✅ APPROVED
     或
結論：🔴 CHANGES REQUIRED
     必須修復：
     1. [問題]
     2. [問題]

     建議修復（非阻擋）：
     1. [建議]
```

---

## 審查後的強制動作

**發現 bug → 必須執行：**
```bash
grep -r "[相同模式]" . --include="*.[ext]"
```

ASP 鐵則：Bug 修復後 grep 全專案找相同模式，**無豁免**。
