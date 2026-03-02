# Design Development Profile

適用：UI/UX 設計治理，確保設計決策可量化、可驗證、一致。
載入條件：`design: enabled`

---

## 設計原則

### 1. 設計即規格 (Design as Specification)

設計不是裝飾，是程式碼的前置規格。每個視覺決策都必須可量化：

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

每個設計決策必須可追溯，對應 ASP 的驗證原則：

```
設計決策 → 對應的 Design Token → 可檢查的 CSS 屬性
```

### 5. 元件三態必備

所有資料驅動的元件必須處理 loading / empty / error 三態，不可只做 success 狀態。

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

設計階段嵌入 SDD → TDD 流程之間：

```
SDD（規格定義）
  ↓ 確認需要哪些頁面/元件
Design（設計階段）
  ↓ 產出視覺設計 / 確認符合 design system
TDD（測試先行）
  ↓ 根據設計規格撰寫測試
實作
  ↓ 讓測試通過
```

> 設計階段不是必經流程。純後端、CLI、基礎設施等無 UI 的任務可跳過。
