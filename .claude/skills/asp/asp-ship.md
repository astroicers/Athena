---
name: asp-ship
description: |
  Use before every git commit to run the pre-commit checklist.
  Executes 10 ordered checks and outputs a Go/No-Go report.
  Triggers: ship, commit, pre-commit, ready to commit, 提交, 準備提交, 提交前, 送出,
  commit check, before commit, 我要提交, 可以 commit 了嗎.
---

# ASP Ship — 提交前檢查（v3.4 Enforcement 強化版）

## 適用場景

用戶準備提交代碼（git commit）前，執行完整的 10 步驟驗證。任何一步失敗即 **BLOCK**，禁止提交。

---

## 10 步驟有序檢查

### Step 0：Session Briefing 檢查（v3.4 新增）

讀取 `.asp-session-briefing.json`（由 SessionStart hook 產生）：

**判斷：**
- 檔案存在且 `blockers` 不為空 → 🔴 **BLOCK** — 列出所有 BLOCKER，必須先解決
- 檔案不存在 → 🟡 **WARN** — 建議執行 `make asp-refresh` 產生 briefing
- 無 BLOCKER → 繼續

---

### Step 1：執行全量測試

```bash
make test
```

**判斷：**
- PASS → 繼續
- FAIL → 🔴 **BLOCK** — 列出失敗的測試，停止後續步驟

---

### Step 2：確認變更範圍

```bash
git status
git diff --stat
```

**判斷：**
- 檢查是否有意外的變更（不屬於此次 commit 的檔案）
- 若有未暫存的相關變更 → 提醒用戶是否要一起加入
- 若有敏感檔案（`.env`, `*.key`, `credentials*`）→ 🔴 **BLOCK**

---

### Step 3：確認 CHANGELOG.md 已更新

```bash
git diff HEAD -- CHANGELOG.md
```

**判斷：**
- 有本次變更的記錄 → 繼續
- 無更新且此次有用戶可見的功能變更 → 🟡 **WARN**，提醒補充後繼續
- 若專案無 CHANGELOG.md → 跳過此步，備註

---

### Step 4：確認 README.md 是否需要更新

對照 `git diff --stat`，判斷此次變更是否影響：
- 公開 API 或 CLI 介面
- 安裝/設定流程
- 功能清單或使用說明

**判斷：**
- 有影響但 README 未更新 → 🟡 **WARN**，提醒用戶確認
- 無影響 → 繼續

---

### Step 5：確認 SPEC Traceability 已更新

若此次 commit 實作了某個 SPEC 中的功能：

```bash
make spec-list
```

查看相關 SPEC 的 `Implementation` 或 `Traceability` 欄位是否填入：
- 實作檔案路徑
- 對應 commit hash（可在 commit 後補填）

**判斷：**
- 有對應 SPEC 但 Traceability 空白 → 🟡 **WARN**
- 無對應 SPEC（trivial 變更）→ 跳過

---

### Step 6：Tech Debt 標記確認

```bash
make tech-debt-list
```

**判斷：**
- 此次新增了 `tech-debt:` 標記 → 確認已記錄格式正確（`[HIGH|MED|LOW] [CATEGORY] description (DUE: YYYY-MM-DD)`）
- HIGH 標記無 DUE 日期 → 🟡 **WARN**
- 發現過期的 HIGH tech-debt（DUE 日期已過）→ 🟡 **WARN**，建議優先處理

---

### Step 7：ADR 合規確認

```bash
make adr-list
```

**判斷：**
- 所有 `Accepted` ADR 的決策是否在此次變更中被遵守
- 是否有 `Draft` ADR 對應的生產代碼被加入 → 🔴 **BLOCK**（鐵則）
- 無違反 → 繼續

---

### Step 8：程式碼品質檢查（v3.4 新增）

```bash
make lint
```

**判斷：**
- PASS（或無 lint target）→ 繼續
- FAIL → 🔴 **BLOCK** — 列出 lint 錯誤

同時掃描 `git diff --cached` 中是否包含：
- `console.log(` / `fmt.Print(` / `print(` — debug 語句 → 🟡 **WARN**
- 未使用的 import → 🟡 **WARN**

---

### Step 9：安全掃描（v3.4 新增）

掃描 `git diff --cached` 中是否包含：

| 模式 | 嚴重度 |
|------|--------|
| `password=`, `api_key=`, `secret=`（硬編碼值） | 🔴 **BLOCK** |
| `*.pem`, `*.key`, `.env` 被 staged | 🔴 **BLOCK** |
| SQL 字串拼接（`"SELECT * FROM " +`） | 🔴 **BLOCK** |
| `dangerouslySetInnerHTML`, `v-html` 無 sanitize 註解 | 🟡 **WARN** |

---

### Step 10：記錄結果 + Bypass 事件（v3.5 強化）

**10a. 記錄測試結果**

如果 Step 1 測試通過，寫入 `.asp-test-result.json`：

```json
{
  "passed": true,
  "timestamp": "<ISO 8601>",
  "test_command": "make test"
}
```

此檔案供 `session-audit.sh` 讀取，用於判斷是否需要動態阻擋 `git commit`。

**10b. 記錄 Bypass 事件（v3.5 新增）**

若前 9 步中**任何一步**被 WARN-GO 或 SKIPPED 放行（非 BLOCK），針對每次略過呼叫：

```bash
make asp-bypass-record SKILL=asp-ship STEP=StepN REASON="使用者說明或 trivial 理由"
```

此記錄寫入 `.asp-bypass-log.json`（append-only）。`make asp-bypass-review` 可檢視歷史。若 3 次以上同一 step 被略過 → 下次 `asp-audit` 會觸發 blocker。

---

## Evidence-Based Output（v3.5 新增）

> 每一步的結果**必須附帶可觀測證據**。空洞的「✅ lint 通過」不可接受。

每個 Step 回報時需包含：

- **執行的指令**（若有）：如 `make test`、`git diff --stat`
- **exit code** 與 **關鍵輸出片段**（≤5 行）：摘錄 stdout 或 stderr
- **若 SKIP**：必須說明理由並寫入 bypass log（見 Step 10b）

### 預設摘要模式 vs Verbose 模式

- **預設**：每 Step 一行 evidence 摘要
  ```
  Step 1  測試  ✅ PASS  (make test → exit 0, 23 tests passed in 4.2s)
  ```
- **Verbose**（使用者要求詳情時）：顯示完整 stdout 片段 + 每個子檢查的證據

---

## 輸出：Go / No-Go 報告

```
📋 Pre-Commit Checklist 結果
================================

Step 0  Session 審計   ✅ 無 BLOCKER（或 🔴 BLOCK）
Step 1  測試           ✅ PASS（或 🔴 FAIL）
Step 2  變更範圍       ✅ 確認（或 ⚠️  警告）
Step 3  CHANGELOG      ✅ 已更新（或 ⚠️  未更新）
Step 4  README         ✅ 無需更新（或 ⚠️  建議更新）
Step 5  SPEC 追蹤      ✅ 已記錄（或 ⚠️  待補）
Step 6  Tech Debt      ✅ 格式正確（或 ⚠️  警告）
Step 7  ADR 合規       ✅ 無違反（或 🔴 BLOCK）
Step 8  程式碼品質     ✅ lint PASS（或 🔴 FAIL）
Step 9  安全掃描       ✅ 無風險（或 🔴 BLOCK）
Step 10 記錄結果       ✅ .asp-test-result.json 已更新

================================
結論：✅ GO — 可以提交
     或
結論：🔴 NO-GO — 阻擋原因：[說明]
     或
結論：⚠️  WARN-GO — 有警告但可提交，建議：[說明]
```

---

## Common Rationalizations（AI 繞過時必讀）

> **執行此 skill 時，AI 必須先檢視此表。** 若使用者或 AI 自己提出下列藉口，引用對應反駁，不可直接照辦。任何 skip 都必須記錄到 `.asp-bypass-log.json`（由 Step 10 處理）。

| 藉口 | 反駁 |
|------|------|
| 「這只是小修改，不需要跑完 10 步」 | trivial 判定必須**顯式宣告並記錄理由**。未宣告就是降低標準。Step 1（測試）、Step 7（ADR）、Step 9（安全）對 trivial 也無豁免。 |
| 「測試暫時 skip，下個 commit 補上」 | tech-debt 必須即時寫入 `tech-debt.md`（含 DUE 日期），且 Step 6 會檢查格式。未記錄的「下次補上」等於遺忘。 |
| 「CHANGELOG 等 release 時一次寫」 | CHANGELOG 的 `## Unreleased` 段落正是為了隨時追加。延後等於資訊遺失。 |
| 「lint warning 不會真的 break，先跳過」 | Step 8 區分 error（BLOCK）與 warning（WARN），warning 允許通過。若 lint error 被當 warning 處理，就是在隱藏問題。 |
| 「Draft ADR 還在討論，先把對應代碼 push 上去」 | 🔴 鐵則違反。Draft ADR 對應的生產代碼是專案憲法禁止項，不論時間壓力。解除方式：完成 ADR 審核或 `make asp-unlock-commit`（需人類批准）。 |
| 「硬編碼 API key 只是暫時本地測試」 | Step 9 一律 BLOCK。即使只是暫時，git 歷史會永久保留。改用環境變數或 `.env`（並確認在 `.gitignore`）。 |
| 「SPEC Traceability 之後再補」 | Step 5 允許 WARN-GO 但會進入 `.asp-bypass-log.json`。連續 3 次以上會在下次 audit 觸發 blocker。 |
| 「Session briefing 不存在，直接開始 commit」 | Step 0 BLOCK。briefing 不存在代表 SessionStart hook 未執行或被跳過，這時你不知道有哪些動態 deny。先 `make asp-refresh`。 |

## 快速修復指引

| 問題 | 修復方式 |
|------|---------|
| 測試失敗 | 修復後重新執行 `make test` |
| 敏感檔案 | 加入 `.gitignore` 並從 staging 移除 |
| CHANGELOG 未更新 | 在 `## Unreleased` 下新增條目 |
| Draft ADR 對應生產代碼 | 等 ADR Accept 後再提交，或移除對應代碼 |
| Tech Debt 格式錯誤 | 修正為 `# tech-debt: HIGH test-pending desc (DUE: YYYY-MM-DD)` |
