# Coding Style Profile — 通用編碼風格規範

<!-- requires: (none — standalone) -->
<!-- optional: (none) -->

適用：需要統一程式碼風格的系統開發專案。
載入條件：`coding_style: enabled`

> **設計原則**：一致性優先於個人偏好。
> 既有 codebase 的慣例優先於本 profile 的建議——先觀察再修改，不要強加風格。

---

## 命名慣例

| 對象 | 規則 | 範例 |
|------|------|------|
| 變數 / 函式 | 依語言慣例（Go: camelCase, Python: snake_case, JS/TS: camelCase） | `getUserName`, `get_user_name` |
| 常數 | UPPER_SNAKE_CASE | `MAX_RETRY_COUNT` |
| 類別 / 型別 | PascalCase | `UserRepository` |
| 布林值 | is / has / can / should 前綴 | `isActive`, `hasPermission` |
| 檔名 | snake_case 或 kebab-case（依語言慣例） | `user_service.go`, `user-service.ts` |
| 私有成員 | 依語言慣例（Go: unexported, Python: `_prefix`, JS/TS: `#prefix` 或 `_prefix`） | `_internal_cache` |

---

## 函式設計

- **單一職責**：一個函式只做一件事，函式名稱即說明用途
- **長度**：函式體 ≤ 40 行為佳，超過時考慮拆分
- **參數**：≤ 4 個為佳，超過時使用 options object / struct
- **巢狀**：避免超過 3 層縮排——用 early return、guard clause 降低巢狀
- **回傳值**：避免回傳 null/nil 作為正常流程的一部分，優先使用明確的錯誤型別

---

## 檔案結構

- 每個檔案單一職責，檔名反映內容
- import / require 排序：`stdlib → 外部套件 → 內部模組`，群組間空一行
- 檔案內部排序建議：`type/interface → constants → constructor → public methods → private methods`

---

## 註解風格

- 解釋 **why**，不解釋 **what**——程式碼本身應該說明 what
- 公開 API / 匯出函式需 docstring（Go: godoc, Python: docstring, TS: JSDoc）
- TODO 格式：`// TODO(owner): description`
- 過時註解比沒有註解更糟——修改邏輯時同步更新註解

---

## 錯誤處理

- 不吞掉 error（禁止空 catch / 忽略 err）
- 不用 generic catch-all（如 `catch (Exception e)`）——捕捉具體的錯誤型別
- 錯誤訊息包含上下文：`failed to create user: {reason}`，不只是 `error occurred`
- 區分可恢復錯誤與不可恢復錯誤——不可恢復的應 fail fast

---

## 穩定度導向編碼規則

### 系統邊界驗證

- 所有外部輸入（HTTP request、CLI 參數、檔案內容、環境變數）在進入系統邊界時驗證
- 驗證邏輯集中在 handler / controller 層，不分散在業務邏輯中
- 驗證失敗時回傳明確錯誤，不靜默使用預設值

### Fail-Fast 與 Graceful Degradation

| 情境 | 策略 |
|------|------|
| 不可恢復（config missing、DB connection failed） | fail fast + 明確錯誤訊息 |
| 可恢復（外部 API timeout、cache miss） | graceful degradation + 日誌記錄 |

- 禁止用 panic / os.Exit / process.exit 處理可恢復錯誤

### 冪等性

- 所有可能被重試的操作（API endpoint、message handler、background job）必須冪等
- 使用 idempotency key 或 upsert 語義確保重試安全
- 在 SPEC 的 Edge Cases 中明確列出「重試行為」

### Timeout 與資源限制

- 所有外部呼叫必須有 timeout 設定，禁止使用預設無限 timeout
- 禁止在記憶體中無上限累積資料（unbounded queue / channel / list）
- 長時間操作必須支援 context cancellation / abort signal

---

## 安全編碼基線

### SQL / NoSQL

- 禁止字串拼接查詢，一律使用 parameterized query / prepared statement
- ORM 的 raw query 功能同樣適用此規則

### 使用者輸入與輸出

- 所有使用者輸入在輸出時進行 context-aware escaping
  - HTML context → HTML escape；URL context → URL encode；JS context → JS escape
- 禁止使用 `dangerouslySetInnerHTML` / `v-html` / `{!! !!}` 等 raw HTML 注入（除非有明確的 sanitization 並在註解中說明）

### 認證與授權

- 密碼儲存使用 bcrypt / argon2，禁止 MD5 / SHA1
- JWT secret、API key 從環境變數讀取，禁止硬編碼
- API endpoint 預設需要認證，公開 endpoint 需明確標記並說明理由

### 禁止提交的檔案模式

`*.pem`, `*.key`, `.env`（非 `.example`）, `credentials.*`, `*_secret*`

---

## 風格審查決策流程

```
FUNCTION review_code_style(file, codebase_conventions):

  // ─── 不可違反的約束 ───
  INVARIANT: 一致性優先於個人偏好
  INVARIANT: 既有 codebase 的慣例優先於本 profile 的建議

  // ─── 第 1 步：識別既有慣例 ───
  existing = detect_conventions(codebase_conventions)
  // 既有 codebase 的命名、縮排、import 風格

  // ─── 第 2 步：遵循既有慣例 ───
  IF file.style CONFLICTS_WITH existing:
    RETURN follow_existing(
      reason = "一致性優先。此 codebase 使用 {existing.convention}，應保持一致。"
    )

  // ─── 第 3 步：檢查本 profile 規則 ───
  violations = []

  IF any_function.line_count > 40:
    violations.append("函式 {name} 超過 40 行，建議拆分")

  IF any_function.param_count > 4:
    violations.append("函式 {name} 參數超過 4 個，建議使用 options object")

  IF any_block.nesting_depth > 3:
    violations.append("巢狀超過 3 層，建議用 early return 降低")

  IF imports NOT sorted_by(stdlib, external, internal):
    violations.append("import 順序不符慣例")

  // ─── 第 4 步：穩定度與安全檢查 ───
  IF any_external_call.has_no_timeout():
    violations.append("穩定度：外部呼叫缺少 timeout 設定")

  IF code.has_string_concatenation_in_query():
    violations.append("安全：禁止字串拼接 SQL 查詢，使用 parameterized query")

  IF code.has_raw_html_injection():
    violations.append("安全：禁止未經 sanitize 的 raw HTML 注入")

  IF code.has_hardcoded_secret_pattern():
    violations.append("安全：疑似硬編碼 credentials，應使用環境變數")

  IF violations:
    RETURN suggest_improvements(violations)
  ELSE:
    RETURN approve()
```
