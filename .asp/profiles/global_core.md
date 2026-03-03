# Global Core — 全域行為準則

<!-- requires: (none — always loaded) -->
<!-- optional: guardrail, rag_context -->

所有專案類型通用。定義溝通方式與核心安全邊界。

---

## 溝通規範

- 精簡直接，省略開場白，進入技術核心
- 多步驟任務前，先提供 Step-by-Step 計畫供確認
- 修改原始碼前，先確認對應 SPEC 存在（詳見 system_dev.md「Pre-Implementation Gate」）
- 副作用操作前，主動說明「等待確認」

---

## 破壞性操作防護

以下操作由 Claude Code 內建權限系統確認，`git push` 前另需列出變更摘要並等待人類明確同意：

```
git rebase          # 內建權限系統確認（SessionStart hook 清理 allow list）
docker push/deploy  # 內建權限系統確認（SessionStart hook 清理 allow list）
rm -r* / find -delete  # 內建權限系統確認（SessionStart hook 清理 allow list）
git push            # 內建權限系統確認 + 必須先列出變更摘要並等待人類同意
```

> **技術執行**：Claude Code 內建權限系統對不在 allow list 的指令彈出「Allow this bash command?」確認框。
> SessionStart hook（`clean-allow-list.sh`）每次 session 啟動時自動清理 allow list 中的危險規則。

---

## 迴歸預防協議

### 修復前

- **非 trivial Bug**（跨模組、邏輯修正、行為變更）→ 先 `make spec-new TITLE="BUG-..."` 建立 SPEC
- **trivial Bug**（單行修復、typo、配置錯誤）→ 可直接修復，但需說明豁免理由

1. **根因記錄**：修復前以一句話記錄根因，寫在 SPEC 或 commit message 中
   - 格式：「根因：{module} 的 {function} 未處理 {edge_case}，導致 {symptom}」

2. **重現測試**（非 trivial Bug 必須，trivial 可豁免）：
   - 先撰寫能重現此 Bug 的測試
   - 修復前此測試必須 FAIL，修復後必須 PASS
   - 此測試永久保留，作為迴歸防護（regression guard）

### 修復後

3. **全專案掃描**：所有 Bug 修復後一律 `grep -r` 全專案，找出相似位置一次修復，無豁免
   - 回覆格式：
     - 「已掃描全專案，共 N 處相同模式：{file1:line, file2:line}，已全部修復」
     - 「已掃描全專案，無其他相同模式」
   - 發現但無法在本次修復 → 標記 `tech-debt` 並說明

4. **狀態依賴掃描**：若 Bug 屬於「狀態變動後依賴方未更新」類型，額外檢查：
   - 同系統中是否有其他狀態-依賴關係存在相同遺漏模式
   - 回覆格式：
     - 「已檢查全專案狀態依賴，共 N 處相同模式：{file1:line, file2:line}，已全部修復」
     - 「已檢查全專案狀態依賴，無其他相同問題」

5. **下游影響驗證**：修復涉及共用模組（被多處 import 的檔案）時
   - 列出使用此模組的下游消費者
   - 執行 `make test`（全量，非 `test-filter`）確認下游測試仍通過

6. **Bug 分類標記**：commit message 中標記分類，便於事後分析模式
   - `[bug:logic]` 邏輯錯誤
   - `[bug:boundary]` 邊界條件未處理
   - `[bug:concurrency]` 並發問題
   - `[bug:integration]` 整合/介面不匹配
   - `[bug:config]` 配置錯誤

---

## Postmortem 觸發條件

以下情況發生時，必須建立 Postmortem（`make postmortem-new TITLE="..."`）：

| 觸發條件 | 理由 |
|----------|------|
| Bug 影響 production 環境 | 使用者已受影響，需記錄防止重演 |
| Bug 修復重試超過 3 次（auto_fix_loop 耗盡） | 修復困難度高，需根因分析 |
| 發生資料遺失或資料不一致 | 不可逆影響，需完整時間線 |
| 需要 rollback（revert deploy / migration DOWN） | 變更未如預期，需分析為何測試未攔截 |

Postmortem 不是懲罰，是學習工具。重點是「系統為什麼沒有防住」而非「誰犯了錯」。

---

## 需求變更回溯協議

需求（SPEC / ADR / 產品方向）在實作過程中發生變更時，依變更規模選擇對應流程：

### 等級判定

| 等級 | 觸發條件 | 範例 |
|------|----------|------|
| **L1 — 細節修改** | SPEC 的 Inputs/Output/Edge Cases 局部調整，Goal 不變 | 追加一個 optional 欄位、修改錯誤碼 |
| **L2 — SPEC 推翻** | SPEC 的 Goal 被推翻，或開發中的 SPEC 被廢棄 | 功能方向改變、半成品需清理 |
| **L3 — ADR 推翻** | Accepted ADR 被外部因素推翻，技術方向要換 | 換 DB、換協議、換認證方案 |
| **L4 — 方向 Pivot** | 多個 SPEC / ADR 同時廢棄，產品方向大幅改變 | 砍掉整個模組、轉換商業模式 |

### L1 — 細節修改

```
1. 直接修改 SPEC（保留修改記錄：在 SPEC 底部追加「變更記錄」）
2. 評估已寫的程式碼和測試是否受影響
   ├── 不受影響 → 繼續開發
   └── 受影響 → 列出需修改的檔案，更新後重跑 make test
3. 無需新建 ADR / SPEC
```

### L2 — SPEC 推翻（開發中）

```
1. 將 SPEC 標記為 Cancelled（在 header 加 `| **狀態** | Cancelled — 原因：... |`）
2. 盤點半成品：
   ├── 已提交的程式碼 → revert commit 或建立清理 SPEC
   ├── 已寫但未提交的程式碼 → git stash 或刪除，說明處置方式
   └── 已寫的測試 → 若測試本身有價值（測基礎設施）可保留，否則隨程式碼一起清理
3. 檢查 Side Effects 表：該 SPEC 的狀態變動是否已影響其他模組
   └── 已影響 → 建立清理 SPEC 處理殘留狀態
4. 更新 CHANGELOG：記錄「SPEC-NNN 已取消，原因：...」
```

### L3 — ADR 推翻

```
1. 建立新 ADR（make adr-new TITLE="..."），狀態為 Draft
   └── 新 ADR 的「背景」說明為什麼舊 ADR 被推翻
2. 舊 ADR 標記為 Superseded by ADR-NNN
3. 觸發反向掃描（見「文件原子化 — 反向」）：
   └── grep -r "ADR-舊NNN" → 找出所有引用的 SPEC 和程式碼
4. 受影響的 SPEC 逐個處理：
   ├── 仍有效（技術方向變但功能需求不變）→ 更新「關聯 ADR」指向新 ADR
   └── 不再有效 → 按 L2 流程處理
5. 新 ADR Accepted 後，才能開始基於新方向的實作
```

### L4 — 方向 Pivot

```
1. 暫停所有進行中的 SPEC 開發
2. 建立 Pivot ADR（make adr-new TITLE="PIVOT-..."）
   └── 記錄：舊方向、新方向、推翻原因、影響範圍評估
3. 批次盤點：
   ├── make spec-list → 逐個標記 Active / Cancelled / Needs-Revision
   ├── make adr-list → 逐個標記 Active / Deprecated
   └── 輸出摘要表供人類確認（不可 AI 自行決定哪些要廢）
4. 人類確認後：
   ├── Cancelled 的 SPEC → 按 L2 批次清理
   ├── Deprecated 的 ADR → 按 L3 批次處理
   └── Needs-Revision 的 SPEC → 更新 Goal，重新走 Pre-Implementation Gate
5. 建立 session-checkpoint 記錄 pivot 決策，確保跨 session 不丟失
```

### 共通規則

- 所有等級的變更記錄都寫入 `CHANGELOG.md`
- L2 以上必須暫停並等待人類確認（即使 `hitl: minimal`）
- 不可因為「反正要改」而跳過清理——殘留的半成品比缺少的功能更危險

---

## 文件原子化

### 正向（程式碼 → 文件）

代碼邏輯變動 **必須** 同步更新（緊急修復可延後，但同一 session 結束前必須補齊）：

- 架構異動 → `docs/architecture.md`
- 技術決策 → `docs/adr/ADR-XXX.md`
- 版本紀錄 → `CHANGELOG.md`
- 使用方式異動 → `README.md`

### 反向（文件 / 決策變更 → 掃描下游產物）

決策層產物變更時，必須反向掃描其下游是否過時：

- ADR 狀態變更（Deprecated / Superseded）→ `grep -r "ADR-NNN"` 找出所有引用該 ADR 的 SPEC，標記為待更新或確認仍有效
- 設計稿變更（已有對應實作時）→ 列出受影響的元件/頁面，標記為 `tech-debt: design-drift` 或同步修改
- OpenAPI spec 變更 → 列出受影響的前端呼叫點與後端實作，確認是否需同步修改
- 若反向掃描發現需修改但無法在本次處理 → 標記 `tech-debt` 並說明

---

## Token 節約

- Shell 指令超過 3 行 → 移入 Makefile，只輸出 `make xxx`
- 重複性操作 → 禁止每次重新輸出完整指令
- `type: content` 的專案 → 跳過所有 Docker、測試、CI/CD 邏輯
