# System Development Profile

<!-- requires: global_core -->
<!-- optional: design_dev, openapi, coding_style, autonomous_dev -->

> 載入條件：`type: system` 或 `type: architecture`

適用：後端服務、微服務、Kubernetes、Docker、API 開發。

---

## ADR 工作流

### 何時必須建立/更新 ADR

| 情境 | 必要性 |
|------|--------|
| 新增微服務或模組 | 🔴 必須 |
| 更換技術棧（DB、框架、協議） | 🔴 必須 |
| 調整核心架構（Auth、API Gateway） | 🔴 必須 |
| 效能優化方向決策 | 🟡 建議 |
| 單一函數邏輯修改 | ⚪ 豁免 |

### ADR 狀態

```
Draft → Proposed → Accepted → Deprecated / Superseded by ADR-XXX
```

### 執行規則

- 提議方案前，先 `make adr-list` 確認是否與現有決策衝突
- ADR 狀態為 `Draft` 時，禁止撰寫對應的生產代碼（鐵則）
- `Accepted` ADR 被推翻時，必須建立新 ADR 說明原因，不可直接修改舊 ADR
- ADR 進入 `Deprecated` / `Superseded` 時，`grep -r "ADR-NNN"` 掃描所有引用它的 SPEC 和程式碼：
  - 引用的 SPEC → 更新「關聯 ADR」欄位指向新 ADR，或標記 `tech-debt: adr-deprecated`
  - 引用的程式碼註解 → 更新或移除

### 批次 ADR 預審（Autonomous 模式專用）

當多個功能需要同時進入自主開發時，可使用批次預審流程：

```
FUNCTION batch_adr_review(adr_list):

  // 1. AI 一次性建立所有 ADR（狀態為 Draft）
  FOR adr IN adr_list:
    CREATE adr_from_template(adr)
    adr.status = "Draft"

  // 2. 暫停 — 人類一次性審核所有 ADR
  PAUSE("請審核以下 ADR 並決定是否 Accept：")
  PRESENT(adr_list)

  // 3. 人類審核完畢
  FOR adr IN adr_list:
    IF human_approves(adr):
      adr.status = "Accepted"
    ELSE:
      adr.status = "Rejected"
      REMOVE from autonomous_queue(adr.related_features)

  // 4. 所有 Accepted ADR → AI 進入自主開發，不再暫停
  RETURN accepted_adrs
```

**使用時機**：
- 版本升級（多功能同步開發）
- 人類希望一次審核、一次放行，AI 不間斷執行

**限制**：
- 批次預審不適用於跨版本的架構變更
- 每個 ADR 仍須獨立評估，不可因批次而降低審核標準

---

## 標準開發流程

```
ADR（為什麼）→ [Design Gate] → [OpenAPI Gate] → SDD（如何設計）→ TDD（驗證標準）→ BDD（業務確認）→ 實作 → 文件
               ↑ design: enabled    ↑ openapi: enabled
```

**Bug 修復流程：**

| Bug 類型 | 流程 |
|----------|------|
| 非 trivial（跨模組、邏輯修正、行為變更） | `make spec-new TITLE="BUG-..."` → 分析 → TDD → 實作 → 文件 |
| trivial（單行修復、typo、配置錯誤） | 直接修復，但需在回覆中說明豁免理由 |
| 涉及架構決策 | 同上 + 補 ADR |

**TDD 場景區分：**

| 場景 | TDD 要求 |
|------|----------|
| 新功能（含商業邏輯） | 🔴 必須測試先於代碼 |
| Bug 修復 | 🟡 可跳過，需標記 `tech-debt: test-pending` |
| 原型驗證 | 🟡 可跳過，需標記 `tech-debt: test-pending` |
| UI/樣式調整（CSS、排版、純視覺） | ⚪ 豁免，以人工視覺驗收為準 |
| 文件/配置變更 | ⚪ 豁免 |

**其他允許的簡化路徑（需在回覆中說明）：**

- 明確小功能：可跳過 BDD，直接 TDD

---

## Pre-Implementation Gate

修改原始碼（非 trivial）前，執行此檢查：

```
1. SPEC 確認
   └── make spec-list
       ├── 有對應 SPEC → 確認理解 Goal 和 Done When
       └── 無對應 SPEC → make spec-new TITLE="..."
           └── 至少填寫：Goal、Inputs、Expected Output、Done When（含測試條件）、Edge Cases

2. ADR 確認（僅架構變更時）
   └── make adr-list → 有相關 ADR 且為 Accepted → 繼續
       └── 無相關 ADR → make adr-new TITLE="..."

3. ADR↔SPEC 連動（僅涉及架構變更時）
   └── ADR 狀態為 Accepted → 才能建立對應 SPEC
       ├── SPEC「關聯 ADR」欄位必須填入 ADR-NNN
       └── ADR 為 Draft → 先完成 ADR 審議，不建 SPEC、不寫生產代碼

4. Design Gate（僅 design: enabled 時）
   └── 需求涉及 UI → CALL design_gate(requirement)
       ├── 設計已存在且與需求一致 → 繼續
       └── 設計不存在或不一致 → 建立/更新設計 → 等待人類確認
       └── 純後端需求 → 豁免（需說明理由）
       └── design_dev profile 未載入 → WARN("design: enabled 未設定，跳過 Design Gate") → 繼續

5. OpenAPI Gate（僅 openapi: enabled 時）
   └── 需求涉及 API → CALL openapi_gate(requirement)
       ├── spec 已存在且與需求一致 → 繼續
       └── spec 不存在或不一致 → 建立/更新 spec → 等待人類確認
       └── 純前端需求（不涉及 API） → 豁免（需說明理由）
       └── openapi profile 未載入 → WARN("openapi: enabled 未設定，跳過 OpenAPI Gate") → 繼續

6. 歷史教訓查詢（僅 rag: enabled 時）
   └── make rag-search Q="SPEC 相關關鍵字"
       ├── 有匹配的 Postmortem → 檢查其「預防措施」是否已反映在本 SPEC 的 Edge Cases 中
       ├── 有匹配的既有 SPEC → 確認是否有可複用的 Side Effects 分析
       └── rag 未啟用 → 跳過

7. 回覆格式：
   「SPEC-NNN（關聯 ADR-NNN）已確認/已建立，開始實作。」
   或
   「SPEC-NNN 已確認/已建立，無架構影響，開始實作。」
   或
   「trivial 修改，豁免 SPEC，理由：...」
```

**豁免路徑**（需在回覆中明確說明）：
- trivial（單行/typo/配置）→ 直接修復，說明理由
- 原型驗證 → 標記 `tech-debt: spec-pending`，24h 內補 SPEC
- autonomous 模式既有架構延伸 → 可由 AI 建立 SPEC 後直接實作，前提是對應 ADR 已 Accepted

> 此規則依賴 AI 自律執行，無 Hook 技術強制。

---

## 環境管理

以下動作統一使用 Makefile，禁止輸出原生指令：

```
make build    建立 Docker Image
make clean    清理暫存與未使用資源
make deploy   重新部署（需確認）
make test     執行測試套件
make diagram  更新架構圖
make adr-new  建立新 ADR
make spec-new 建立新規格書
```

---

## 變更影響評估

Pre-Implementation Gate 確認「要不要做」，此步驟評估「怎麼做最安全」。在 SPEC 建立後、TDD 之前執行。

```
FUNCTION assess_change_impact(spec):

  // 1. 估算影響範圍
  affected_files = grep_for_affected_files(spec.modules)

  IF LEN(affected_files) > 10:
    WARN("影響超過 10 個檔案，建議評估替代方案")
    PRESENT alternatives:
      A. 局部修改（限縮範圍，僅改必要處）
      B. 漸進遷移（分多個 SPEC 逐步完成）
      C. 完整重構（一次改到位，風險最高）
    PAUSE("請選擇方案或確認繼續")

  // 2. 偵測共用模組
  FOR file IN affected_files:
    importers = find_importers(file)
    IF LEN(importers) > 3:
      WARN("共用模組 {file} 被 {LEN(importers)} 處引用：{importers}")
      // 修改後必須全量測試（make test，非 test-filter）

  // 3. 輸出評估結果
  RETURN {
    affected_files: affected_files,
    shared_modules: [files with >3 importers],
    risk_level: LOW | MEDIUM | HIGH,
    recommendation: selected_approach
  }
```

---

## 穩定狀態驗證

實作完成後、文件更新前的品質門檻。確保修改不引入副作用。

```
FUNCTION verify_stable_state(spec):

  // ─── 快速通道 ───
  IF spec.single_file AND NOT spec.modifies_shared_module:
    EXECUTE("make test-filter FILTER={spec.filter}")
    IF passed → 繼續至全量驗證（commit 前必須）

  // ─── 全量驗證（commit 前必須） ───
  baseline_warnings = COUNT_WARNINGS("make test" 修改前輸出)
  result = EXECUTE("make test")

  IF result.failed:
    RETURN FAIL → 進入 auto_fix_loop

  current_warnings = COUNT_WARNINGS(result.output)

  IF current_warnings > baseline_warnings:
    WARN("新增 {current_warnings - baseline_warnings} 個 warning")
    // 不阻擋，但必須在回覆中列出新 warning 並說明是否需處理

  RETURN PASS
```

**規則**：
- `make test`（全量）是提交前的最低門檻，不可只用 `test-filter`
- 開發過程中可用 `test-filter` 加速迭代，但最終驗證必須全量
- warning 增加不阻擋提交，但必須可見——隱藏 warning 比 warning 本身更危險

---

## Schema 變更治理

資料庫結構變更的風險分級與流程要求。

| 風險等級 | 範例 | 流程要求 |
|----------|------|----------|
| 🟢 低 | 新增 nullable column、新增 index | SPEC + migration |
| 🟡 中 | 新增 NOT NULL column、修改 column type | SPEC + migration（必須有 default 值或資料回填計畫） |
| 🔴 高 | DROP column/table、RENAME column/table | ADR + SPEC + 多步 migration |

**規則**：
- Migration 必須同時包含 UP（套用）和 DOWN（回退）
- 禁止無 backup 計畫的 DROP 操作
- Schema 變更的 SPEC Edge Cases 必須包含「回退方案」

### API Breaking Change 定義

以下變更為 breaking change，需版本化（URL path 或 header）：

- 移除現有 response 欄位
- 新增必填 request 欄位
- 修改欄位型別
- 變更 HTTP method 或 URL path

非 breaking（可直接變更）：新增 optional request 欄位、新增 response 欄位、新增 endpoint。

---

## 提交前自審

每次提交前（`git add` 之前），執行此 checklist。與 Done When 互補——Done When 驗功能完整性，此 checklist 驗程式碼清潔度。

```
□ 清潔度
  ├── 無 debug print / console.log（搜尋 print\(|console\.log|fmt\.Print）
  ├── 無未使用的 import / variable
  ├── 無註解掉的程式碼區塊（>3 行）
  └── 無 TODO 未標注 owner（格式：TODO(owner): description）

□ 一致性
  ├── 錯誤處理風格與 codebase 既有模式一致
  ├── 命名遵循 coding_style.md 慣例
  └── import 排序：stdlib → 外部 → 內部

□ 安全性
  ├── 無硬編碼 credentials（grep: password|secret|api_key|token 等 literal 值）
  ├── 新增 API endpoint 有認證（或明確標記為公開 + 理由）
  └── 使用者輸入有適當 escaping

□ 完整性
  ├── 新增 public function / method 有 docstring
  ├── CHANGELOG.md 已更新（非 trivial 變更）
  └── 相關文件已同步（architecture.md、README 等）
```

---

## 依賴管理規範

### 新增依賴評估

AI 提議新增外部依賴時（autonomous 模式：暫停點），必須提供以下資訊：

| 評估項目 | 必須回答 |
|----------|----------|
| **用途** | 這個依賴解決什麼問題？ |
| **替代方案** | 標準庫 / 既有依賴能否替代？ |
| **維護狀態** | 最近 commit 時間、star 數、issue 回應速度 |
| **授權** | License 類型是否與專案相容？ |

### 優先序

```
標準庫 > 專案既有依賴的子功能 > 成熟外部依賴（>1000 stars, 活躍維護）> 新依賴
```

### 版本規則

- lock file（package-lock.json / poetry.lock 等）必須提交至版本控制
- 禁止使用 `latest` / `*` / 無版本約束
- major 版本升級（breaking change）需建立 SPEC 評估影響

---

## 部署前檢查清單

```
□ 環境變數完整（對照 .env.example）
□ 所有測試通過（make test）
□ ADR 已標記 Accepted
□ architecture.md 與當前代碼一致
□ Dockerfile 無明顯優化缺失
```

---

## 架構圖維護

- Mermaid 格式，存放於 `docs/architecture.md`
- 核心邏輯變動後必須更新
- 架構圖與代碼不一致 = 技術債，本次任務結束前修正
