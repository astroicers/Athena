# OpenAPI Profile — API 設計規範與 API-First 工作流

<!-- requires: global_core, system_dev -->
<!-- optional: design_dev -->

適用：提供 RESTful API 的系統開發專案。
載入條件：`openapi: enabled`

> **設計原則**：OpenAPI spec 是 API 的 single source of truth。
> 先寫 spec 再寫 code，實作與 spec 不一致就是 bug。

---

## API 設計原則

### 資源命名

| 規則 | 正確 | 錯誤 |
|------|------|------|
| 使用複數名詞 | `/users`, `/orders` | `/user`, `/getOrders` |
| 路徑用 kebab-case | `/user-profiles` | `/user_profiles`, `/userProfiles` |
| 資源巢狀表示從屬 | `/users/{id}/orders` | `/getUserOrders` |
| 動作用 HTTP method 表達 | `POST /users` | `POST /createUser` |

### HTTP Method 語意

| Method | 語意 | 冪等 | 回應碼 |
|--------|------|------|--------|
| GET | 讀取資源 | 是 | 200 / 404 |
| POST | 建立資源 | 否 | 201 / 400 / 409 |
| PUT | 完整更新 | 是 | 200 / 404 |
| PATCH | 部分更新 | 否 | 200 / 404 |
| DELETE | 刪除資源 | 是 | 204 / 404 |

### 狀態碼使用規範

- 2xx 成功：`200 OK`, `201 Created`, `204 No Content`
- 4xx 客戶端錯誤：`400 Bad Request`, `401 Unauthorized`, `403 Forbidden`, `404 Not Found`, `409 Conflict`, `422 Unprocessable Entity`
- 5xx 伺服器錯誤：`500 Internal Server Error`, `503 Service Unavailable`
- 禁止所有錯誤都回 200 + error body

### 統一錯誤格式

```json
{
  "error": "VALIDATION_ERROR",
  "message": "Email format is invalid",
  "details": [
    { "field": "email", "reason": "must be a valid email address" }
  ]
}
```

- `error`：機器可讀的錯誤代碼（UPPER_SNAKE_CASE）
- `message`：人類可讀的說明
- `details`：可選，提供欄位級別的錯誤資訊

### 版本策略

- 優先使用 URL path 版本：`/api/v1/users`
- 大版本號遞增（v1 → v2）僅在 breaking change 時
- 舊版本提供明確的 deprecation 時程

---

## OpenAPI Spec 撰寫規範

### 結構要求

- 所有 endpoint 必須有 `summary`（一句話）+ `description`（詳細說明）
- 所有 request body 和 response 都要有 `example`
- 必填欄位必須標記 `required`
- Schema 使用 `$ref` 引用 `components/schemas`，避免重複定義
- Enum 值必須有說明

### 命名慣例

| 對象 | 慣例 | 範例 |
|------|------|------|
| Schema 名稱 | PascalCase | `UserProfile`, `OrderItem` |
| 屬性名稱 | camelCase | `firstName`, `createdAt` |
| Enum 值 | UPPER_SNAKE_CASE | `PENDING`, `IN_PROGRESS` |
| operationId | camelCase 動詞 + 名詞 | `listUsers`, `createOrder` |

### Spec 檔案位置

- 主檔案：`docs/openapi.yaml`（或 `docs/openapi/openapi.yaml`）
- 大型 API 可拆分：`docs/openapi/paths/`, `docs/openapi/schemas/`

---

## API-First 工作流

> 此流程已整合至 `system_dev.md` Pre-Implementation Gate 步驟 5。
> 以下 pseudocode 描述 Gate 觸發後的具體執行邏輯。

```
FUNCTION openapi_gate(requirement, openapi_spec_path = "docs/openapi.yaml"):

  // ─── 由 Pre-Implementation Gate 步驟 5 觸發 ───
  // 前置條件：SPEC 已確認、ADR 已確認（若需要）

  // ─── 第 1 步：檢查 spec 是否存在對應 endpoint ───
  IF NOT file_exists(openapi_spec_path):
    spec = write_openapi_spec(requirement)
    // 至少包含：paths, schemas, examples, error responses
    RETURN ask_human(
      title   = "OpenAPI spec 已建立，請確認 API 設計",
      content = spec.summary(),
      action  = "確認後開始實作"
    )

  existing_spec = read(openapi_spec_path)
  IF requirement.endpoints NOT_IN existing_spec:
    updated_spec = update_openapi_spec(existing_spec, requirement)
    RETURN ask_human(
      title   = "OpenAPI spec 已更新，請確認變更",
      content = updated_spec.diff(),
      action  = "確認後開始實作"
    )

  // ─── 第 2 步：確認 spec 與需求一致 ───
  IF existing_spec INCONSISTENT_WITH requirement:
    RETURN fix_spec_first(
      reason = "spec 與需求不一致，先更新 spec 再實作"
    )

  // spec 已存在且一致 → 繼續實作

  // ─── 第 3 步：實作完成後同步驗證 ───
  // （在實作階段結束時執行）
  IF implementation DIVERGES_FROM spec:
    RETURN fix(
      priority = "spec 為準，修正實作",
      fallback = "若 spec 有誤，先更新 spec 再修正實作"
    )

  // ─── 第 3b 步：Breaking Change 偵測 ───
  IF change.removes_endpoint OR change.removes_field OR change.changes_field_type
     OR change.changes_required_status OR change.changes_method_or_status_semantics:
    BLOCK("Breaking change 偵測到，必須完成以下 4 項才可繼續：")
    //   1. 遞增 major version（v1 → v2）
    //   2. 在 api-changelog.md 標記 ⚠️ BREAKING
    //   3. 更新 openapi.yaml info.version
    //   4. 若有舊版 endpoint，提供 deprecation 時程

  // ─── 第 4 步：更新變更紀錄 ───
  update_api_changelog("docs/api-changelog.md", requirement)
  update_openapi_info(openapi_spec_path, latest_change_summary)
  // openapi.yaml info 區塊只保留最新一筆更新摘要

  // ─── 不可違反的約束 ───
  INVARIANT: OpenAPI spec 是 single source of truth
  INVARIANT: 實作與 spec 不一致 = bug，不是 feature
  INVARIANT: 新增或修改 endpoint 前，先更新 spec
```

---

## 與 ADR / SPEC 連動

| 情境 | 需要 ADR | 需要 SPEC |
|------|---------|----------|
| 新增 API endpoint | 否（除非涉及架構變更） | 是，Done When 含 spec 驗證 |
| 修改 API 行為（breaking change） | 是（版本策略決策） | 是 |
| 修改 API 回應格式 | 視影響範圍 | 是 |
| 新增 API 版本（v1 → v2） | 是 | 是 |
| 修正 API bug（非 breaking） | 否 | trivial 可豁免 |

---

## API 變更紀錄規則

### 檔案位置與職責

| 檔案 | 職責 |
|------|------|
| `docs/api-changelog.md` | API 專屬變更的完整歷史紀錄（獨立於專案 CHANGELOG.md） |
| `docs/openapi.yaml` info 區塊 | 只保留最新一筆更新摘要 |

- 只記錄 API 相關變更（endpoint 新增/修改/移除、request/response 格式、錯誤碼等）
- 專案內部重構、非 API 的 bug 修復等不需要記錄

### 變更分類

| 分類 | 說明 |
|------|------|
| **Added** | 新增 endpoint 或參數 |
| **Changed** | 修改既有行為（含 request/response 格式變更） |
| **Deprecated** | 即將移除的 endpoint 或參數（標明預計移除時程） |
| **Removed** | 已移除的 endpoint 或參數 |
| **Fixed** | API bug 修正 |

### Breaking Change 標記

Breaking change 必須在版本標題加上醒目標記，格式：

```
## [v1.2.0] - 2025-03-15 ⚠️ BREAKING
```

Breaking change 的定義：
- 移除或重新命名 endpoint
- 移除或重新命名 request/response 欄位
- 變更欄位型別或必填狀態
- 變更 HTTP method 或狀態碼語意

### 記錄格式範例

`docs/api-changelog.md` 格式：

```markdown
# API Changelog

所有 API 相關變更紀錄。格式依循 [Keep a Changelog](https://keepachangelog.com/)。

## [v1.2.0] - 2025-03-15 ⚠️ BREAKING

### Changed
- `PATCH /users/{id}` — email 欄位改為必填

### Added
- `GET /users/{id}/preferences` — 新增使用者偏好設定查詢

## [v1.1.0] - 2025-03-01

### Added
- `POST /orders/{id}/refund` — 新增退款 endpoint

### Fixed
- `GET /orders` — 修正分頁參數 offset 計算錯誤
```

`docs/openapi.yaml` info 區塊（只保留最新一筆）：

```yaml
info:
  title: Your API
  version: "1.2.0"
  description: |
    最近更新（v1.2.0, 2025-03-15）⚠️ BREAKING:
    - PATCH /users/{id} email 欄位改為必填
    - 新增 GET /users/{id}/preferences
    完整變更紀錄見 docs/api-changelog.md
```
