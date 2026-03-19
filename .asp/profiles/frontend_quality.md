# Frontend Quality — 前端工程品質驗證

<!-- requires: global_core -->
<!-- optional: design_dev -->

適用：具有前端介面的專案，確保程式碼層級的 UI 品質。不需要設計稿，只需要工程紀律。
載入條件：`design: enabled` 時自動載入，或手動設定 `frontend_quality: enabled`

> 本 profile 與 `design_dev.md` 分工如下（無重疊）：
>
> | 職責 | 主管 profile |
> |------|-------------|
> | 設計稿存在性、設計確認流程 | `design_dev.md` |
> | Design Token 定義與 token ↔ 設計稿一致性 | `design_dev.md` |
> | Token ↔ CSS 變數雙向同步（`verify_token_sync`） | `design_dev.md` |
> | **元件三態程式碼驗證** | **本 profile** |
> | **i18n 硬編碼偵測** | **本 profile** |
> | **硬編碼顏色值偵測** | **本 profile** |
> | **Accessibility 自動化驗證** | **本 profile** |
>
> 衝突時以 `design_dev.md` 為準（設計即規格）。

### 前置讀取（design: enabled 時）

當與 `design_dev.md` 同時載入時，以下讀取由 `system_dev.md` Step 4a 統一觸發。
此為冗餘宣告，確保 profile 自文檔化：

```
PRE_IMPLEMENTATION（design: enabled 時）:
  IF exists("frontend/DESIGN_MAP.md"):
    READ("frontend/DESIGN_MAP.md")   // route ↔ 元件對應、Frame ID、元件尺寸
  FOR spec IN glob("docs/specs/SPEC-*-design-*.md"):
    READ(spec)                       // 禁止的 anti-pattern、token 速查
```

---

## 適用範圍

本 profile 的所有規則在以下情境皆生效：
- `design: enabled` — 自動載入（與 design_dev.md 一起）
- `frontend_quality: enabled` — 手動啟用（不需要 design_dev.md）
- `design: disabled` 時 — `system_dev.md` Pre-Implementation Gate 的 ui_baseline_rules 引用本 profile

> 這些規則不需要設計稿，只需要工程紀律。

---

## 驗證觸發時機

| 函數 | 觸發時機 | 觸發方式 |
|------|---------|---------|
| `verify_component_states()` | 修改/新增前端元件時 | 提交前自審「前端元件完整性」自動呼叫 |
| `verify_i18n()` | 修改含使用者可見文字的檔案時 | 提交前自審「清潔度」自動呼叫 |
| `verify_color_usage()` | 修改含樣式的前端檔案時 | 提交前自審「清潔度」自動呼叫 |
| `verify_a11y()` | 修改含互動元件的前端檔案時 | 提交前自審「完整性」自動呼叫 |

> 所有驗證函數回傳 FAIL 時，對應的提交前自審項目為 🔴，阻擋提交。

---

## Error/Loading/Empty 標準化

| 狀態 | 標準做法 | 規則 |
|------|---------|------|
| Loading | 統一 Spinner 或 Skeleton | 頁面級用 Skeleton，元件級用 Spinner |
| Empty | 統一 EmptyState 元件 | 🔴 必須使用 i18n，視覺風格與 design system 一致 |
| Error | Toast（全域）/ Inline（表單） | ❌ 禁止在非表單場景使用 inline error |

**規則**：
- 每個資料驅動元件必須明確處理三態，不可只渲染 success
- Empty State 必須提供引導文字（告訴使用者如何產生資料）
- Error 訊息必須通過 i18n，禁止硬編碼錯誤文字
- Loading 態超過 3 秒建議顯示進度指示或可取消操作

> 三態驗證 pseudocode 見下方「元件三態驗證」。
> 元件狀態的 YAML 定義見 `design_dev.md`「元件狀態清單」。

---

## 元件三態驗證

```
FUNCTION verify_component_states(component):

  IF component.fetches_data OR component.receives_async_props:
    required_states = [loading, empty, error, success]
  ELSE IF component.has_form:
    required_states = [pristine, dirty, valid, invalid, submitting]
  ELSE IF component.is_interactive:
    required_states = [default, hover, active, focus, disabled]
  ELSE:
    RETURN PASS  // 靜態展示元件免驗

  FOR state IN required_states:
    IF state NOT handled_in(component):
      FAIL("元件 '{component.name}' 缺少 '{state}' 狀態處理")

  INVARIANT: 資料驅動元件必須覆蓋 loading / empty / error 三態
```

---

## i18n 工程規範

> 補充 `design_dev.md` 設計禁止事項中「❌ 硬編碼文字字串（需支援 i18n 結構）」的具體驗證機制。

### 硬編碼偵測

- 🔴 所有面向使用者的字串必須通過 i18n 函數（`t()`, `$t()`, `useTranslations()`, `intl.formatMessage()` 等）
- 🔴 JSX/TSX/Vue 中的可見文字（含 HTML attribute `title="..."`, `placeholder="..."`, `alt="..."`）一律走 i18n
- ⚪ 例外：技術性字串（CSS class、HTML tag、`aria-role`、`data-testid`、enum 值）

### 語系一致性

- 新增/修改 i18n key 後，必須同步所有語系檔案
- 提交前驗證：所有語系檔案的 key 數量一致（`make i18n-check`）
- 缺少翻譯的 key → 標記 `tech-debt: i18n-missing` + 填入 fallback 語言文字

### 驗證 Pseudocode

```
FUNCTION verify_i18n(changed_files, locale_dir):

  // 1. 硬編碼偵測
  FOR file IN changed_files:
    IF file.extension IN [.jsx, .tsx, .vue, .svelte]:
      strings = extract_visible_strings(file)
      FOR str IN strings:
        IF str NOT wrapped_in_i18n_function AND NOT is_technical_string(str):
          FAIL("'{file}:{line}' 包含硬編碼文字：'{str}'")

  // 2. 語系一致性
  locale_files = list_files(locale_dir)
  base_keys = extract_keys(locale_files[0])
  FOR locale IN locale_files[1:]:
    current_keys = extract_keys(locale)
    missing = base_keys - current_keys
    extra = current_keys - base_keys
    IF missing:
      FAIL("語系 '{locale}' 缺少 keys：{missing}")
    IF extra:
      WARN("語系 '{locale}' 有多餘 keys：{extra}")

  INVARIANT: 所有語系檔案的 key 集合必須一致
```

> `make i18n-check` 執行語系一致性驗證。
> `system_dev.md` 提交前自審的清潔度項目引用此規範。

---

## 顏色值驗證

> 補充 `design_dev.md` 設計禁止事項中「❌ 未定義在 design tokens 中的顏色值」的具體驗證機制。

### 提交前自審項目

```
□ 設計一致性
  ├── 無硬編碼顏色值（grep: #[0-9a-fA-F]{3,8} 在元件檔中）
  ├── 所有顏色使用 CSS 變數 var(--*) 或 Tailwind semantic class
  └── 例外：canvas/SVG 動態繪製（需註解說明對應的 design token）
```

### 驗證 Pseudocode

```
FUNCTION verify_color_usage(changed_files):

  FOR file IN changed_files:
    IF file.extension IN [.jsx, .tsx, .vue, .css, .scss, .module.css]:
      hardcoded = grep(file, "#[0-9a-fA-F]{3,8}")
      FOR match IN hardcoded:
        IF match NOT in_comment AND NOT in_svg_dynamic_context:
          FAIL("'{file}:{line}' 包含硬編碼顏色值：'{match}'")

      rgb_matches = grep(file, "rgb\(|rgba\(|hsl\(|hsla\(")
      FOR match IN rgb_matches:
        IF match NOT wrapped_in_css_var:
          FAIL("'{file}:{line}' 包含硬編碼顏色函數：'{match}'")

  INVARIANT: 元件檔中所有顏色必須引用 design token
```

> `system_dev.md` 提交前自審的清潔度項目引用此規範。

---

## Accessibility 自動化驗證

```
FUNCTION verify_a11y(changed_files):

  FOR file IN changed_files:
    IF file.extension IN [.jsx, .tsx, .vue, .svelte]:
      // 圖片 alt 檢查
      imgs = grep(file, "<img|<Image")
      FOR img IN imgs:
        IF NOT has_attribute(img, "alt"):
          FAIL("'{file}:{line}' <img> 缺少 alt 屬性")

      // 表單 label 檢查
      inputs = grep(file, "<input|<select|<textarea")
      FOR input IN inputs:
        IF NOT has_associated_label(input) AND NOT has_attribute(input, "aria-label"):
          FAIL("'{file}:{line}' 表單元素缺少 label")

      // 互動元素 keyboard 檢查
      clickables = grep(file, "onClick=")
      FOR el IN clickables:
        IF el.tag NOT IN [button, a, input, select] AND NOT has_attribute(el, "role"):
          WARN("'{file}:{line}' 非語意元素上的 onClick 缺少 role 和 keyboard handler")

  INVARIANT: Accessibility 是設計規格的一部分，不是功能完成後的附加物
```

> 人工 review checklist（ARIA label、keyboard navigation 等）見 `design_dev.md`「設計 Review 檢查清單 > 可用性」。
