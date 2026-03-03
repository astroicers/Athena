# Design Development Profile — UI/UX 設計治理

<!-- requires: global_core, system_dev -->
<!-- optional: openapi -->

適用：具有使用者介面的系統開發專案，確保設計決策可量化、可驗證、一致。
載入條件：`design: enabled`

> **設計原則**：UI 設計是需求的視覺化規格。
> 設計不是裝飾，是程式碼的前置規格——先設計畫面再定義 API，介面決定資料契約。

---

## 設計原則

### 1. 設計即規格 (Design as Specification)

每個視覺決策都必須可量化：

```
❌ 「看起來不錯的間距」
✅ 「spacing-4（16px），基於 4px grid system」
```

### 2. 一致性優先 (Consistency Over Creativity)

同一類型的元件在所有頁面表現一致。色彩語意固定、間距遵循統一 scale，不出現任意數值。

### 3. 漸進式揭露 (Progressive Disclosure)

資訊密度高的介面必須分層展示：

- Level 1：總覽（5 秒掌握狀態）
- Level 2：分類列表（30 秒找到目標）
- Level 3：詳細設定（完整操作）

### 4. 可驗證的設計

每個設計決策必須可追溯：

```
設計決策 → 對應的 Design Token → 可檢查的 CSS 屬性
「主按鈕用品牌色」→ --color-primary → button.primary { background: var(--color-primary) }
```

### 5. 元件三態必備

所有資料驅動的元件必須處理 loading / empty / error 三態，不可只做 success 狀態。

---

## 設計檔組織

| 規則 | 說明 |
|------|------|
| 設計檔存放位置 | `docs/designs/` |
| 命名慣例 | kebab-case：`user-dashboard`、`login-flow` |
| 一個設計檔 = 一個功能模組 | 不要把整個應用塞在一個檔案 |
| Design System 獨立管理 | `docs/designs/design-system` |

---

## Design Token 管理

- Token 命名使用 semantic naming：`color-primary`、`spacing-md`、`font-heading`
- 所有畫面共用同一套 Token，確保一致性
- Token 變更時須同步更新所有引用的設計檔和程式碼
- 在元件中禁止寫 magic number——必須用 token

---

## 元件設計慣例

| 對象 | 慣例 | 範例 |
|------|------|------|
| 元件名稱 | PascalCase | `NavBar`、`UserCard`、`LoginForm` |
| 畫面名稱 | 功能描述 | `Dashboard - Overview`、`Settings - Profile` |
| 狀態變體 | 名稱後綴 | `Button - Default`、`Button - Hover`、`Button - Disabled` |
| 響應式斷點 | 獨立區分 | `Dashboard - Desktop`、`Dashboard - Mobile` |

---

## 元件狀態清單

```yaml
component-states:
  interactive: [default, hover, active, focus, disabled]
  data: [loading, empty, error, success]
  form: [pristine, dirty, valid, invalid, submitting]
```

所有 UI 元件必須根據類型覆蓋對應的狀態集合。

---

## 設計禁止事項

### 工程禁止

- ❌ magic number 間距（必須用 design token）
- ❌ inline style（必須用 class 系統或 Tailwind）
- ❌ 忽略 loading / error / empty 三態
- ❌ 硬編碼文字字串（需支援 i18n 結構）
- ❌ 跳過 dark mode 支援（若專案有 dark mode 需求）

### 視覺禁止

- ❌ 未定義在 design tokens 中的顏色值
- ❌ 無功能目的的純裝飾性動畫
- ❌ 不遵循 grid system 的任意間距

---

## Design-First Gate

> 此流程已整合至 `system_dev.md` Pre-Implementation Gate 步驟 4。
> 以下 pseudocode 描述 Gate 觸發後的具體執行邏輯。

```
FUNCTION design_gate(requirement, designs_dir = "docs/designs/"):

  // ─── 由 Pre-Implementation Gate 步驟 4 觸發 ───
  // 前置條件：SPEC 已確認、ADR 已確認（若需要）

  // ─── 第 0 步：讀取所有相關 ADR ───
  adrs = list_files("docs/adr/")
  relevant_adrs = filter(adrs, relates_to(requirement))
  IF relevant_adrs:
    FOR adr IN relevant_adrs:
      read(adr)  // 理解架構約束（前端框架、元件庫、技術限制等）

  // ─── 第 1 步：讀取 Design System（若存在）───
  IF exists("design-system/MASTER.md"):
    READ("design-system/MASTER.md")
  IF exists("design-system/tokens.yaml"):
    READ("design-system/tokens.yaml")

  // ─── 第 2 步：確認是否已有對應畫面設計 ───
  design_file = find_design(designs_dir, requirement)
  IF design_file EXISTS AND is_current(design_file, requirement):
    PASS  // 設計已存在且與需求一致 → 繼續

  // ─── 第 3 步：建立或更新畫面設計 ───
  ELSE:
    IF design_file NOT_EXISTS:
      design_file = create_new_design(designs_dir, requirement)
    // 使用專案的設計工具（MCP、Figma、手動等）完成設計

    RETURN ask_human(
      title   = "畫面設計已完成，請確認",
      action  = "確認後進入 SDD/API 設計"
    )

  // ─── 第 4 步：頁面級覆寫 ───
  IF exists("design-system/pages/{current_page}.md"):
    READ("design-system/pages/{current_page}.md")
    // 頁面級規則優先於 MASTER.md

  // ─── 第 5 步：更新設計變更紀錄 ───
  update_design_changelog(designs_dir + "design-changelog.md", requirement)

  // ─── 不可違反的約束 ───
  INVARIANT: ADR 中的技術約束必須反映在設計選擇中
  INVARIANT: 設計確認前不開始 SDD/API 設計
  INVARIANT: 設計變更必須通過人類確認
```

---

## Design System 讀取規則

```
FUNCTION before_ui_work():

  // 1. 讀取專案級 design system（如果存在）
  IF exists("design-system/MASTER.md"):
    READ("design-system/MASTER.md")
  IF exists("design-system/tokens.yaml"):
    READ("design-system/tokens.yaml")

  // 2. 頁面級覆寫優先
  IF exists("design-system/pages/{current_page}.md"):
    READ("design-system/pages/{current_page}.md")

  // 3. 無 design system 時
  IF NOT exists("design-system/"):
    SUGGEST("建議使用 UI/UX Skill 產生 design system，或手動建立 design-system/MASTER.md")
```

> Design system 檔案由各專案自行維護，ASP 只規範讀取順序和覆寫規則。

---

## 與 ADR / SPEC 連動

| 情境 | 需要 ADR | 需要設計 |
|------|---------|---------|
| 新增 UI 功能模組 | 視架構影響 | 是 |
| 修改現有畫面佈局 | 否 | 是 |
| 純後端功能（無 UI） | 視架構影響 | 否（豁免） |
| 修改 Design Token | 否 | 是（影響全域） |
| UI Bug 修復 | 否 | trivial 可豁免 |
| 新增響應式斷點 | 視架構影響 | 是 |

### SPEC 整合

當 `design: enabled` 時，SPEC 的 Done When 應包含設計相關驗收條件：

```
- [ ] 畫面設計已完成且經人類確認（docs/designs/xxx）
- [ ] 實作與設計稿一致（visual regression 或人工比對）
- [ ] Design Token 與實作 CSS 變數一致
```

---

## Design-to-Code Handoff

設計確認後，進入實作階段時：

1. **提取 Design Token** → 對應到 CSS 變數或 Tailwind config
2. **提取元件結構** → 對應到前端元件清單
3. **提取佈局資訊** → 對應到 CSS layout（flex/grid）

### 與 openapi 連動（design + openapi 同時啟用時）

> **執行順序**：由 `system_dev.md` Pre-Implementation Gate 統一驅動。
> Design Gate（步驟 4）先執行，OpenAPI Gate（步驟 5）後執行。
> 本段描述的是 Design Gate 確認後，資料需求如何推導至 API 契約。

設計稿中的資料需求自動推導 API 契約：

```
畫面元素       → 資料需求          → OpenAPI Schema
用戶列表       → GET /users        → User[]
表單提交       → POST /users       → CreateUserRequest
詳情頁面       → GET /users/{id}   → User
刪除按鈕       → DELETE /users/{id} → 204 No Content
```

流程：設計確認 → 提取資料需求 → openapi_gate() → SDD → TDD → 實作

---

## 設計變更紀錄

### 檔案位置

| 檔案 | 職責 |
|------|------|
| `docs/designs/design-changelog.md` | 設計變更的完整歷史紀錄 |

### 變更分類

| 分類 | 說明 |
|------|------|
| **Added** | 新增畫面或元件 |
| **Changed** | 修改既有畫面佈局或互動流程 |
| **Deprecated** | 即將移除的畫面或元件 |
| **Removed** | 已移除的畫面或元件 |
| **Fixed** | UI Bug 修正 |

### 記錄格式範例

```markdown
# Design Changelog

所有設計相關變更紀錄。

## [2025-03-15] Dashboard 改版

### Changed
- 側邊欄改為可收合式設計
- 統計卡片從 3 欄改為 4 欄

### Added
- 新增使用者偏好設定頁面

## [2025-03-01] 初始設計

### Added
- 建立 Design System（Button、Input、Card、Nav）
- 首頁儀表板
- 登入/註冊流程
```

---

## 設計 Review 檢查清單

設計完成後，對照以下清單 review：

### 一致性

- [ ] 色彩/間距符合 design tokens 定義
- [ ] 字型使用正確的 family / size / weight
- [ ] 圓角使用定義的 scale

### 完整性

- [ ] 互動狀態完整（hover, focus, active, disabled）
- [ ] 資料狀態完整（loading, empty, error, success）
- [ ] 包含 dark mode（若適用）

### 安全性

- [ ] 危險操作有確認流程（刪除、修改等不可逆操作）
- [ ] 敏感資訊有適當遮罩

### 可用性

- [ ] 資訊層級清晰（5 秒法則：能否快速掌握重點）
- [ ] 操作路徑直覺（3 步內完成常見操作）
- [ ] Accessibility 基本合規（ARIA label、keyboard navigation）

---

## 與現有 ASP 流程的整合

設計階段嵌入 ADR → TDD 流程之間：

```
ADR（為什麼）
  ↓ 架構影響時必須
Design（設計階段）← design: enabled 時
  ↓ 確認畫面設計
SDD（如何設計）
  ↓ 規格定義
TDD（測試先行）
  ↓ 根據設計規格撰寫測試
實作
  ↓ 讓測試通過
```

> 設計階段不是必經流程。純後端、CLI、基礎設施等無 UI 的任務可跳過。
