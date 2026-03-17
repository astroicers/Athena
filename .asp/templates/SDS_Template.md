# 軟體設計規格書 (Software Design Specification)

> **使用說明**：複製此模板至專案 `docs/SDS.md`，依各節指引填寫。本文件須在 ADR 進入 Accepted 狀態後方可撰寫對應實作規格。

---

| 欄位 | 內容 |
|------|------|
| **專案名稱** | <!-- TODO: 填入專案名稱 --> |
| **版本** | v0.1.0 |
| **最後更新** | <!-- TODO: YYYY-MM-DD --> |
| **狀態** | Draft / Review / Accepted |
| **依據 SRS** | <!-- TODO: SRS 版本號 --> |
| **作者** | <!-- TODO: 填入作者 --> |
| **審閱者** | <!-- TODO: 技術負責人 --> |

---

## 1. 系統架構概覽

### 1.1 架構風格

<!-- TODO: 描述採用的架構風格，例如：分層架構、微服務、CQRS 等 -->

本系統採用 **分層架構（Layered Architecture）** 結合 **RESTful API**，主要原因：

- 團隊熟悉度高，降低學習曲線
- 業務複雜度尚未需要微服務級別的隔離
- 支援後續演進至服務導向架構（ADR-001 記錄決策過程）

**架構原則：**

1. 依賴方向單向向下（Presentation → Business → Data）
2. 跨層通訊僅透過定義好的介面（Interface Segregation）
3. 外部依賴（資料庫、第三方 API）僅於 Infrastructure 層存取

### 1.2 分層架構說明

```
┌─────────────────────────────────────────────┐
│         Presentation Layer（表現層）          │
│   React SPA / Next.js  ←→  REST API          │
│   路由、表單驗證、狀態管理（Zustand/Redux）    │
├─────────────────────────────────────────────┤
│         Application Layer（應用層）           │
│   Controllers / Handlers                     │
│   DTO 轉換、請求驗證、授權檢查                │
├─────────────────────────────────────────────┤
│         Business Logic Layer（業務層）        │
│   Services / Domain Models / Policies        │
│   業務規則、工作流、領域事件                   │
├─────────────────────────────────────────────┤
│         Infrastructure Layer（基礎設施層）    │
│   Repositories / External APIs / Queue       │
│   資料庫操作、快取、訊息佇列、第三方服務       │
└─────────────────────────────────────────────┘
```

### 1.3 部署架構

```
Internet
    │
    ▼
[CDN / CloudFront]          ← 靜態資源、前端 SPA
    │
    ▼
[Load Balancer / ALB]       ← SSL Termination, Health Check
    │
    ├──────────────┐
    ▼              ▼
[API Server 1]  [API Server 2]   ← <!-- TODO: 框架，如 Node.js / FastAPI -->
    │
    ├──────────────────────┐
    ▼                      ▼
[PostgreSQL Primary]   [Redis Cluster]   ← 主資料庫 / 快取+Session
    │
    ▼
[PostgreSQL Replica]                     ← 讀取副本（報表查詢）
```

**基礎設施選擇：**

| 元件 | 服務 | 理由 |
|------|------|------|
| 雲端平台 | <!-- TODO: AWS / GCP / Azure --> | <!-- TODO --> |
| 容器編排 | <!-- TODO: ECS / EKS / K8s --> | <!-- TODO --> |
| 資料庫 | PostgreSQL 15 | ACID、JSON 支援、成熟生態 |
| 快取 | Redis 7 | Session 存儲、API 快取 |
| 訊息佇列 | <!-- TODO: SQS / RabbitMQ --> | <!-- TODO --> |
| 物件儲存 | <!-- TODO: S3 / GCS --> | 媒體檔案、備份 |
| 監控 | <!-- TODO: Datadog / Prometheus + Grafana --> | <!-- TODO --> |

---

## 2. 模組設計

### 2.1 後端模組清單

| 模組名稱 | 職責 | 主要介面 | 內部依賴 | 外部依賴 |
|----------|------|----------|----------|----------|
| `AuthModule` | 認證、授權、Token 管理 | `AuthService`, `JwtGuard` | `UserModule` | JWT lib, bcrypt |
| `UserModule` | 使用者 CRUD、角色管理 | `UserService`, `UserRepo` | — | PostgreSQL |
| `NotificationModule` | Email/站內通知發送 | `NotificationService` | `UserModule` | SendGrid, Redis |
| `AuditModule` | 稽核日誌記錄與查詢 | `AuditService`, `AuditRepo` | — | PostgreSQL |
| <!-- TODO --> | <!-- TODO: 業務核心模組 --> | <!-- TODO --> | <!-- TODO --> | <!-- TODO --> |

### 2.2 各模組詳細設計

#### AuthModule

**職責：** 處理所有身份驗證與授權邏輯，包含 JWT 生命週期管理

**核心介面：**

```typescript
interface AuthService {
  login(dto: LoginDto): Promise<TokenPair>;
  logout(userId: string, refreshToken: string): Promise<void>;
  refresh(refreshToken: string): Promise<TokenPair>;
  validateToken(token: string): Promise<JwtPayload>;
}

interface TokenPair {
  accessToken: string;   // 有效期 15 分鐘
  refreshToken: string;  // 有效期 7 天，單次使用
}
```

**決策說明：** Refresh Token Rotation 策略（詳見 ADR-002）—每次 refresh 產生新 token pair 並廢棄舊的，降低 token 竊取風險。

---

#### <!-- TODO: 業務核心模組 -->

**職責：** <!-- TODO -->

**核心介面：**

```typescript
// TODO: 定義模組的主要 Service 介面
interface <!-- TODO -->Service {
  // TODO: 列出主要方法
}
```

### 2.3 前端模組結構

```
src/
├── app/                    # 路由與頁面（Next.js App Router）
│   ├── (auth)/             # 認證相關頁面群組
│   │   ├── login/
│   │   └── register/
│   ├── dashboard/
│   └── admin/
├── components/
│   ├── ui/                 # 基礎 UI 元件（來自 Design System）
│   ├── features/           # 功能型元件（含業務邏輯）
│   └── layouts/            # 版面配置元件
├── hooks/                  # 自定義 React Hooks
├── stores/                 # 全域狀態管理（Zustand）
├── services/               # API 呼叫層
│   └── api/                # 依模組分類的 API 函數
├── types/                  # TypeScript 型別定義
└── utils/                  # 通用工具函數
```

---

## 3. 資料設計

### 3.1 ER Diagram 描述

```
users (1) ──< (N) sessions
  │
  └──< (N) audit_logs
  │
  >──< (N) roles  [透過 user_roles 關聯表]

<!-- TODO: 補充業務核心實體關係 -->
```

### 3.2 資料表結構

**`users` 資料表：**

```sql
CREATE TABLE users (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email       VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255),               -- OAuth 使用者可為 NULL
    display_name VARCHAR(100) NOT NULL,
    status      VARCHAR(20) NOT NULL DEFAULT 'pending',
                -- CHECK (status IN ('pending', 'active', 'suspended', 'locked', 'deleted'))
    failed_login_count INT NOT NULL DEFAULT 0,
    locked_until TIMESTAMPTZ,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at  TIMESTAMPTZ                   -- Soft delete
);

CREATE INDEX idx_users_email ON users(email) WHERE deleted_at IS NULL;
```

**`sessions` 資料表：**

```sql
CREATE TABLE sessions (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    refresh_token_hash  VARCHAR(255) UNIQUE NOT NULL,
    expires_at          TIMESTAMPTZ NOT NULL,
    ip_address          VARCHAR(45),
    user_agent          TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_sessions_user_id_expires ON sessions(user_id, expires_at);
```

**`audit_logs` 資料表：**

```sql
CREATE TABLE audit_logs (
    id          BIGSERIAL PRIMARY KEY,          -- 使用 BIGSERIAL 優化寫入
    user_id     UUID REFERENCES users(id),      -- 可為 NULL（系統操作）
    action      VARCHAR(100) NOT NULL,          -- e.g., 'user.login', 'user.role_changed'
    resource    VARCHAR(100),                   -- e.g., 'user:uuid-xxx'
    ip_address  VARCHAR(45),
    detail      JSONB,                          -- 彈性儲存額外細節
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 分區策略：按月分區（audit_logs 為高寫入資料表）
-- CREATE TABLE audit_logs_2024_01 PARTITION OF audit_logs
--     FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');
```

### 3.3 Migration 計畫

| Migration 版本 | 說明 | 預計時間 | 停機需求 |
|----------------|------|----------|----------|
| V001 | 初始化 schema（users, sessions, roles） | 上線前 | 否 |
| V002 | 建立 audit_logs 資料表 | 上線前 | 否 |
| V003 | <!-- TODO: 業務核心資料表 --> | M1 | 否 |
| V004 | 加入全文搜尋索引 | M2 | 維護窗口 |

**Migration 原則：**
- 使用工具：<!-- TODO: Flyway / Liquibase / Prisma Migrate -->
- 必須向前相容（支援 rolling deployment）
- 大型資料表欄位新增使用 `ALTER TABLE ... ADD COLUMN ... DEFAULT NULL` 再更新
- 禁止在 migration 中撰寫業務邏輯

---

## 4. API 合約

### 4.1 基本規範

- **Base URL：** `https://api.{domain}/v1`
- **認證：** `Authorization: Bearer {access_token}`
- **內容類型：** `Content-Type: application/json`
- **時間格式：** ISO 8601（`2024-01-15T10:30:00Z`）
- **ID 格式：** UUID v4

### 4.2 通用回應格式

**成功回應：**

```json
{
  "data": { ... },
  "meta": {
    "timestamp": "2024-01-15T10:30:00Z",
    "requestId": "req_abc123"
  }
}
```

**分頁回應：**

```json
{
  "data": [ ... ],
  "meta": {
    "total": 100,
    "page": 1,
    "pageSize": 20,
    "totalPages": 5
  }
}
```

**錯誤回應：**

```json
{
  "error": {
    "code": "AUTH_INVALID_CREDENTIALS",
    "message": "Email 或密碼錯誤",
    "details": []
  },
  "meta": {
    "timestamp": "2024-01-15T10:30:00Z",
    "requestId": "req_abc123"
  }
}
```

### 4.3 認證 API

#### `POST /auth/login`

**Request：**

```json
{
  "email": "user@example.com",
  "password": "SecurePass123!"
}
```

**Response 200：**

```json
{
  "data": {
    "accessToken": "eyJhbGciOiJSUzI1NiJ9...",
    "refreshToken": "rt_...",
    "expiresIn": 900,
    "user": {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "email": "user@example.com",
      "displayName": "王小明",
      "role": "user"
    }
  }
}
```

**Error Codes：**

| Code | HTTP Status | 說明 |
|------|-------------|------|
| `AUTH_INVALID_CREDENTIALS` | 401 | Email 或密碼錯誤 |
| `AUTH_ACCOUNT_LOCKED` | 403 | 帳號已鎖定 |
| `AUTH_ACCOUNT_SUSPENDED` | 403 | 帳號已停用 |
| `VALIDATION_ERROR` | 422 | 請求格式錯誤 |

---

#### `POST /auth/refresh`

**Request：**

```json
{
  "refreshToken": "rt_..."
}
```

**Response 200：** 同 `/auth/login` 的 Token 結構（Refresh Token Rotation）

**Error Codes：**

| Code | HTTP Status | 說明 |
|------|-------------|------|
| `AUTH_TOKEN_INVALID` | 401 | Token 無效或已使用 |
| `AUTH_TOKEN_EXPIRED` | 401 | Token 已過期 |

---

#### `POST /auth/logout`

**Header：** `Authorization: Bearer {access_token}`

**Response 204：** No Content

---

### 4.4 使用者 API

#### `GET /users/me`

**Response 200：**

```json
{
  "data": {
    "id": "550e8400-...",
    "email": "user@example.com",
    "displayName": "王小明",
    "role": "user",
    "status": "active",
    "createdAt": "2024-01-01T00:00:00Z"
  }
}
```

#### `GET /admin/users` (Admin only)

**Query Parameters：**

| 參數 | 類型 | 必填 | 說明 |
|------|------|------|------|
| `page` | integer | 否 | 頁碼，預設 1 |
| `pageSize` | integer | 否 | 每頁筆數，最大 100，預設 20 |
| `status` | string | 否 | 篩選狀態：`active`, `suspended`, `locked` |
| `search` | string | 否 | 搜尋 email 或顯示名稱 |

---

### 4.5 全域錯誤碼

| Code | HTTP Status | 說明 |
|------|-------------|------|
| `UNAUTHORIZED` | 401 | 未提供或無效的 Token |
| `FORBIDDEN` | 403 | 無操作權限 |
| `NOT_FOUND` | 404 | 資源不存在 |
| `CONFLICT` | 409 | 資源衝突（如重複 email） |
| `VALIDATION_ERROR` | 422 | 請求驗證失敗 |
| `RATE_LIMIT_EXCEEDED` | 429 | 超過速率限制 |
| `INTERNAL_ERROR` | 500 | 伺服器內部錯誤 |
| `SERVICE_UNAVAILABLE` | 503 | 服務暫時不可用 |

---

## 5. 安全設計

### 5.1 認證與授權流程

```
Client                API Server              DB / Redis
  │                       │                       │
  │── POST /auth/login ──>│                       │
  │                       │── query user ────────>│
  │                       │<── user record ────────│
  │                       │── verify bcrypt        │
  │                       │── generate JWT pair    │
  │                       │── store refresh hash ─>│ (Redis, TTL 7d)
  │<── 200 TokenPair ─────│                       │
  │                       │                       │
  │── GET /api/resource ─>│                       │
  │  [Bearer accessToken] │── verify JWT sig       │
  │                       │── check permissions    │
  │<── 200 data ──────────│                       │
```

### 5.2 加密策略

| 資料類型 | 加密方式 | 金鑰管理 |
|----------|----------|----------|
| 密碼 | bcrypt（cost=12） | N/A（單向雜湊） |
| JWT 簽章 | RS256（非對稱） | 私鑰存於 AWS Secrets Manager |
| Refresh Token | SHA-256 雜湊後存 DB | N/A（雜湊） |
| 敏感欄位（如身分證字號） | AES-256-GCM | AWS KMS 管理金鑰 |
| 傳輸層 | TLS 1.3（最低 1.2） | ACM 憑證自動更新 |

### 5.3 JWT Token 生命週期

| Token 類型 | 有效期 | 儲存位置 | 更新策略 |
|------------|--------|----------|----------|
| Access Token | 15 分鐘 | 記憶體（不存 localStorage） | 自動 refresh |
| Refresh Token | 7 天 | HTTPOnly Cookie | Rotation（使用一次即廢棄） |

**安全決策：**
- Access Token 不存 localStorage（防 XSS 竊取）
- Refresh Token 用 HTTPOnly Cookie（防 JS 存取）
- CSRF 防護：Refresh Token 請求需附 `X-Requested-With` header

### 5.4 安全標頭

```
Content-Security-Policy: default-src 'self'; script-src 'self' 'nonce-{random}'
X-Frame-Options: DENY
X-Content-Type-Options: nosniff
Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: geolocation=(), microphone=(), camera=()
```

### 5.5 速率限制規則

| 端點 | 限制 | 視窗 | 超限行為 |
|------|------|------|----------|
| `POST /auth/login` | 10 次 | 15 分鐘 per IP | 429 + Retry-After header |
| `POST /auth/refresh` | 30 次 | 1 小時 per user | 429 |
| 一般 API | 1000 次 | 1 小時 per user | 429 |
| 管理 API | 200 次 | 1 小時 per admin | 429 |

---

## 6. 效能設計

### 6.1 快取策略

| 快取項目 | 儲存位置 | TTL | 失效策略 |
|----------|----------|-----|----------|
| Session 有效性驗證 | Redis | 15 分鐘 | Token 過期自動清除 |
| 使用者基本資料 | Redis | 5 分鐘 | 資料更新時主動失效 |
| 權限列表（RBAC） | Redis | 30 分鐘 | 角色變更時主動失效 |
| API 回應快取（讀取密集） | Redis | 1 分鐘 | TTL 過期自動更新 |
| <!-- TODO --> | <!-- TODO --> | | |

**快取命名規則：** `{service}:{entity}:{id}:{version}`
範例：`auth:user:550e8400-...:v1`

### 6.2 查詢優化

- **N+1 防護：** 列表 API 統一使用 JOIN 或 DataLoader（GraphQL）
- **分頁策略：** 游標分頁（Cursor-based）優先於偏移分頁，避免深度分頁效能問題
- **慢查詢監控：** 記錄所有 > 100ms 的查詢，每日報告
- **讀寫分離：** 報表查詢導向 Read Replica，降低主庫壓力

### 6.3 併發處理

- **無狀態設計：** API Server 不儲存 Session 狀態（存於 Redis），支援水平擴展
- **資料庫連線池：** 每個 API 實例最大 20 個連線（`pgBouncer` 統一管理）
- **背景任務：** Email 發送、報表生成等耗時操作透過訊息佇列非同步處理
- **樂觀鎖定：** 高競爭資料更新使用 `version` 欄位實作樂觀鎖，避免遺失更新

---

## 7. ADR 交叉引用

| ADR ID | 標題 | 影響的設計決策 |
|--------|------|----------------|
| ADR-001 | 採用分層架構而非微服務 | 第 1.1 節架構風格 |
| ADR-002 | JWT + Refresh Token Rotation 認證策略 | 第 5.1, 5.3 節 |
| ADR-003 | PostgreSQL 作為主要資料庫 | 第 3 節資料設計 |
| ADR-004 | Redis 用於快取與 Session 存儲 | 第 6.1 節快取策略 |
| <!-- TODO --> | <!-- TODO --> | <!-- TODO --> |

> 所有 ADR 狀態必須為 **Accepted** 後，對應設計方案才可進入實作階段。

---

## 附錄

### A. 技術債追蹤

| 項目 | 說明 | 優先級 | 預計解決版本 |
|------|------|--------|--------------|
| <!-- TODO --> | <!-- TODO --> | High / Medium / Low | vX.X |

### B. 變更歷史

| 版本 | 日期 | 變更摘要 | 作者 |
|------|------|----------|------|
| v0.1.0 | <!-- TODO: YYYY-MM-DD --> | 初版建立 | <!-- TODO --> |

### C. 相關文件

- [`SRS.md`](./SRS.md) — 軟體需求規格書
- [`UIUX_SPEC.md`](./UIUX_SPEC.md) — UI/UX 規格書
- [`DEPLOY_SPEC.md`](./DEPLOY_SPEC.md) — 部署規格書
- [`docs/adr/`](./docs/adr/) — 架構決策記錄
