---
name: asp-plan
description: |
  Use when planning new features, making architecture decisions, or creating ADRs and SPECs.
  Activates full planning workflow: architecture impact assessment → ADR (if needed) → SPEC creation.
  Triggers: plan, new feature, design, architecture, SPEC, ADR, feature planning, technical decision,
  計劃, 新功能, 設計, 架構, 規格, 建立 SPEC, 建立 ADR, 需要規格, 技術決策, 我想做.
---

# ASP Plan — 功能規劃模式

## 適用場景

用戶描述新功能、系統變更、或技術決策，需要在實作前建立規劃文件（ADR / SPEC）。

---

## Step 1：確認現有決策

```bash
make adr-list
```

檢查是否有與本次請求衝突或相關的現有 ADR。若有相關 ADR → 確認其狀態（Accepted / Draft / Deprecated）。

---

## Step 2：評估架構影響

對以下 5 個問題逐一判斷：

| 問題 | 範例 |
|------|------|
| 1. 這個變更會跨越模組邊界嗎？ | 呼叫另一個服務的 API、修改 shared library |
| 2. 會引入新的外部依賴嗎？ | 新增 npm/pip/go module、外部 API |
| 3. 會改變資料庫 schema 或 API 合約嗎？ | 新增欄位、改 endpoint 路由 |
| 4. 會影響超過 3 個檔案或跨越多個團隊嗎？ | 橫切功能、基礎設施變更 |
| 5. 有安全性、效能、或合規影響嗎？ | 認證機制、資料加密、GDPR |

**若任一 YES → 需要 ADR（進入 Step 3）**
**若全部 NO → 跳過 ADR，直接 Step 4**

---

## Step 3：建立 ADR（架構決策記錄）

```bash
make adr-list   # 確認下一個編號
make adr-new TITLE="[以祈使句描述決策，例：Use PostgreSQL for primary storage]"
```

填寫 ADR 模板的必填欄位：

- **Status**：`Draft`（⚠️ 永遠以 Draft 開始，AI 不可自行改為 Accepted）
- **Context**：為什麼現在需要做這個決定？外部驅動因素是什麼？
- **Decision**：確切決定了什麼，明確陳述
- **Consequences**：接受的 trade-off、引入的風險、後續工作
- **Alternatives Considered**：至少 2 個替代方案，說明為何未選

### 下游影響掃描（若此 ADR 更新現有決策）

```bash
grep -r "ADR-舊編號" docs/
```

找出引用舊 ADR 的所有 SPEC，更新其「關聯 ADR」欄位。

### 🛑 關鍵鐵則

**ADR 必須保持 Draft 狀態，直到人類明確審核並改為 Accepted。**
**AI 不可自行將 ADR 從 Draft 改為 Accepted。**
**Draft ADR 存在時，不可撰寫對應的生產代碼。**

等待人類 Accept ADR 後，再繼續 Step 4。

---

## Step 4：建立 SPEC

```bash
make spec-new TITLE="[功能名稱]"
```

填寫 SPEC 的 7 個必填欄位（缺一不可）：

| 欄位 | 說明 | 注意 |
|------|------|------|
| **Goal** | 一句話：這個功能建了什麼 | 不是「如何」，是「什麼」 |
| **Inputs** | 什麼資料/事件進入系統 | 包含來源和格式 |
| **Outputs** | 系統產生什麼輸出 | 包含成功和失敗路徑 |
| **Side Effects** | 狀態變更、外部呼叫、通知 | 資料庫寫入、發送訊息 |
| **Edge Cases** | 錯誤條件、邊界輸入、race condition | 空值、超時、並發 |
| **Done When** | 可測試的驗收條件（binary）| 「當…時通過」，不是「完成時」 |
| **Rollback Plan** | 部署失敗如何回滾 | feature flag / migration down |

### SPEC 關聯
- 若有 ADR → 在 SPEC 的「關聯 ADR」填入 ADR 編號
- 若有 SRS → 在 SPEC 的「SRS 參考」填入需求 ID

---

## Step 5：呈現並確認

將完成的 SPEC（以及 ADR 若有建立）摘要呈現給用戶，格式如下：

```
✅ 規劃完成

ADR：docs/adr/ADR-NNN-[title].md
     狀態：Draft — 等待人類審核後改為 Accepted
     阻擋：實作必須等 ADR Accepted

SPEC：docs/specs/SPEC-NNN-[title].md
     Goal：[一句話]
     Done When：[驗收條件]

下一步（人類需要做）：
1. 審核並接受 ADR（若有）
2. 確認 SPEC 內容無誤
3. 告訴我開始實作
```

**等待用戶明確確認後，才建議進入實作階段。**

---

## Common Rationalizations（AI 繞過時必讀）

> **執行此 skill 時，AI 必須先檢視此表。** 若以下藉口出現，引用反駁，不可直接照辦。

| 藉口 | 反駁 |
|------|------|
| 「這個變更很小，不需要 ADR」 | Step 2 有 5 個問題清單。任一 YES 就必須 ADR。不可用「感覺很小」代替清單判斷。若全部 NO，在回覆中明確列出 5 題各自的答案，留下審計軌跡。 |
| 「先寫代碼確認可行，SPEC 之後補」 | 反了。SPEC 的 Done When 才是驗收條件，沒有 Done When 的代碼等於沒有驗收。先代碼後 SPEC = Trace post-hoc rationalization。 |
| 「ADR 我自己改成 Accepted，這樣就可以繼續實作」 | 🔴 鐵則違反。ADR Status 由 Draft → Accepted **只能由人類執行**。AI 自行更改視為繞過治理。 |
| 「Alternatives Considered 想不出來，寫一個就好」 | ADR 要求至少 2 個替代方案。若真的只有一個選項，那就不需要 ADR（不是決策而是強制約束）。寫 1 個代表偷懶。 |
| 「Done When 寫『功能完成』就好」 | 不可。Done When 必須是二元可測試條件（「API 回傳 200 且 body.status == ok」）。「完成」不是驗收條件。 |
| 「Rollback Plan 暫不填，之後補」 | 有 schema / migration / feature flag 的 SPEC，Rollback Plan 是必填。沒有回滾計畫就上線 = 單向門。 |
| 「這個 ADR 影響的檔案很少，Consequences 留空」 | Consequences 不是檔案清單，是 trade-off 與引入風險。空白代表你沒有評估負面影響。 |

## 常用指令參考

```bash
make adr-new TITLE="..."    # 建立新 ADR
make adr-list               # 列出所有 ADR
make spec-new TITLE="..."   # 建立新 SPEC
make spec-list              # 列出所有 SPEC
make audit-quick            # 快速確認無 blocker
```
