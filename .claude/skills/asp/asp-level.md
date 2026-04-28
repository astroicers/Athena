---
name: asp-level
description: |
  Evaluate and manage ASP maturity levels (L1 Starter → L5 Autonomous).
  Determines current level, checks graduation criteria, and recommends upgrade/downgrade.
  Triggers: level, maturity, asp-level, what level, upgrade level, downgrade level,
  成熟度, 等級, 升級 ASP, 我該升到哪一級, 現在是哪一級, level check, level upgrade.
---

# ASP Level — 成熟度等級評估與升級

## 核心概念

ASP 採用 **5 級成熟度模型**，使用者不必一次面對 20 個 profile 的組合爆炸，
而是從 L1 開始，滿足 graduation_checklist 後逐級升級。

| Level | 名稱 | 核心能力 |
|-------|------|---------|
| **L1** | Starter | ADR + SPEC + 測試（最小治理） |
| **L2** | Disciplined | + guardrail + coding_style（品質護欄） |
| **L3** | Test-First | + pipeline gates G1-G6（TDD 強制） |
| **L4** | Collaborative | + multi-agent（並行協作、獨立 QA） |
| **L5** | Autonomous | + autopilot + RAG（自主執行） |

---

## 使用情境

### 情境 1：查詢目前等級

使用者問「我現在是哪一級？」或「level check」時：

1. 讀取 `.ai_profile` 的 `level` 欄位
2. 若無 `level` 欄位 → 根據已啟用的 profile 推斷（見下方「Level 推斷規則」）
3. 讀取對應 `.asp/levels/level-N.yaml`
4. 顯示：目前等級、已通過的 graduation items、未通過項目

### 情境 2：評估是否可升級

使用者問「我可以升到 L3 嗎？」或「upgrade check」時：

1. 讀取 `.asp/levels/level-{current+1}.yaml`
2. 對每個 `graduation_checklist` item 執行 `check` 欄位的 shell 判斷
3. 若 item 標註 `check: "true"`（soft check），則由 AI 檢視專案狀態手動判斷並說明依據
4. 輸出：
   - 通過項目清單（✅）
   - 未通過項目清單（❌ + 修復建議）
   - 升級建議（GO / NEEDS_WORK）

### 情境 3：執行升級

使用者確認升級後：

1. 備份 `.ai_profile` → `.ai_profile.backup-L{N}`
2. 根據 `.asp/levels/level-{N+1}.yaml` 的 `ai_profile_hint` 更新 `.ai_profile`
3. 執行 `make asp-refresh` 重新跑 session audit
4. 顯示升級後差異（新增哪些 profile、新增哪些 Makefile target）

### 情境 4：降級

使用者說「降回 L2」或遇到問題需要回退：

1. 警告降級會停用某些 profile 能力
2. 備份當前 `.ai_profile`
3. 根據 `.asp/levels/level-{N-1}.yaml` 的 `ai_profile_hint` 更新

---

## Level 推斷規則

當 `.ai_profile` 無 `level` 欄位時（legacy 專案），根據已啟用的 profile 推斷：

| 已啟用 profile | 推斷等級 |
|---------------|---------|
| 只有 global_core + system_dev | L1 |
| + guardrail 或 coding_style | L2 |
| + pipeline 或 openapi | L3 |
| + mode: multi-agent | L4 |
| + autopilot: enabled 或 autonomous: enabled | L5 |

推斷結果僅供參考，建議執行 `make asp-level-check` 後手動確認並在 `.ai_profile` 中補上 `level:` 欄位。

---

## Graduation Checklist 執行

對每個 item：

```bash
# 若 check 是具體 shell
<check command>
# exit 0 → ✅ 通過
# exit 非 0 → ❌ 未通過
```

```yaml
# 若 check 是 "true"（soft check）
# AI 需要讀取相關檔案（如 .asp-bypass-log.json、commit history）並判斷
```

---

## 輸出格式

### Level Check 輸出

```
🎯 ASP Level Check
==================

Current Level: L2 (Disciplined)
Profiles loaded: global_core, system_dev, guardrail, coding_style

📋 L2 Graduation Checklist:
  ✅ lint-clean           — make lint 通過
  ✅ guardrail-log-exists — .asp/logs/ 已存在
  ✅ no-hardcoded-secrets — 近 30 commit 無洩密事件
  ❌ spec-has-done-when   — SPEC-003 缺 Done When 欄位

Ready for L3? NEEDS_WORK (1/4 items missing)

修復建議：
  - SPEC-003-auth.md：補上 Done When 欄位（可二元測試的驗收條件）

Next Level (L3 Test-First) 會新增：
  - pipeline profile（G1-G6 quality gates）
  - TDD 強制流程
```

### Level Upgrade 輸出

```
🚀 升級到 L3 (Test-First)

已備份 .ai_profile → .ai_profile.backup-L2

新增 profile：
  + pipeline

新增 Makefile targets（來自 pipeline）：
  + (無新增 target，pipeline 透過 asp-gate skill 運作)

執行 make asp-refresh 重新評估專案狀態 ...
✅ 升級完成

下一步：
  1. 跑 /asp-gate status 查看當前 gate 狀態
  2. 下個 feature 開發時，記得走完整 G1 → G6
```

---

## Common Rationalizations（AI 繞過時必讀）

| 藉口 | 反駁 |
|------|------|
| 「graduation item 有點麻煩，直接跳級」 | 不可。每級的設計假設前一級已經穩定。跳級 = 基礎不穩導致的 cascading 問題。 |
| 「使用者說要升到 L5，直接改 `.ai_profile` 就好」 | 必須先檢查 L1-L4 的 graduation_checklist。若未通過，向使用者說明缺項，讓使用者決定是否強制升級。強制升級必須寫入 `.asp-bypass-log.json`。 |
| 「legacy 專案沒有 `level` 欄位，預設就算 L5」 | 不可。無 `level` 欄位時用「Level 推斷規則」保守估計。寧可推斷低也不要誤判高。 |
| 「soft check (`check: "true"`) 直接回傳通過」 | Soft check 代表需要 AI 實際檢視專案狀態（例如讀 bypass log、commit history）並**說明判斷依據**。空白通過 = 無效審核。 |
| 「降級會丟資料，不如不要降」 | 降級不刪除檔案，只是停用 profile 載入。若專案確實不需要某級能力，降級可以減少 AI 注意力負擔。 |

---

## 相關檔案

- `.asp/levels/level-1.yaml` ~ `level-5.yaml` — 等級定義
- `.ai_profile` — 使用者當前等級與啟用設定
- `.asp-bypass-log.json` — 強制升級記錄
- `Makefile` → `make asp-level-check`、`make asp-level-upgrade`
