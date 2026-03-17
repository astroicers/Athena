# 軟體需求規格書 (Software Requirements Specification)

> **使用說明**：複製此模板至專案 `docs/SRS.md`，依各節指引填寫。標記 `<!-- TODO -->` 的欄位為必填項目。

---

| 欄位 | 內容 |
|------|------|
| **專案名稱** | <!-- TODO: 填入專案名稱 --> |
| **版本** | v0.1.0 |
| **最後更新** | <!-- TODO: YYYY-MM-DD --> |
| **狀態** | Draft / Review / Accepted |
| **作者** | <!-- TODO: 填入作者 --> |
| **審閱者** | <!-- TODO: 填入審閱者 --> |

---

## 1. 目的與範圍（Purpose & Scope）

### 1.1 文件目的

本文件描述 `[專案名稱]` 的完整軟體需求，作為開發、測試與驗收的基準依據。所有功能需求、非功能需求及使用者故事均應可追溯至本文件。

### 1.2 專案範圍

<!-- TODO: 描述系統邊界，說明哪些功能在範圍內、哪些明確排除 -->

**範圍內（In Scope）：**

- 使用者認證與授權管理
- 核心業務功能 A
- 核心業務功能 B
- 管理後台基本功能

**範圍外（Out of Scope）：**

- 第三方 ERP 系統整合（Phase 2）
- 行動裝置原生 App（另立專案）
- 即時通訊功能

### 1.3 定義與縮寫

| 術語 | 定義 |
|------|------|
| SRS | Software Requirements Specification，軟體需求規格書 |
| FR | Functional Requirement，功能需求 |
| NFR | Non-Functional Requirement，非功能需求 |
| US | User Story，使用者故事 |
| UC | Use Case，使用案例 |
| HITL | Human-in-the-Loop，人工介入點 |
| <!-- TODO --> | <!-- TODO: 加入專案特定術語 --> |

---

## 2. 利害關係人（Stakeholders）

| 角色 | 代表人 | 職責 | 參與階段 |
|------|--------|------|----------|
| 產品負責人（PO） | <!-- TODO: 姓名 --> | 定義需求優先級、驗收功能 | 全程 |
| 技術負責人（TL） | <!-- TODO: 姓名 --> | 架構決策、技術評審 | 設計、實作 |
| 前端開發 | <!-- TODO: 姓名/團隊 --> | UI 實作與整合 | 實作、測試 |
| 後端開發 | <!-- TODO: 姓名/團隊 --> | API 設計與業務邏輯 | 設計、實作 |
| QA 工程師 | <!-- TODO: 姓名 --> | 測試計畫、缺陷追蹤 | 測試、上線 |
| 終端使用者代表 | <!-- TODO: 姓名/部門 --> | 使用者訪談、UAT 驗收 | 需求、驗收 |
| 資訊安全 | <!-- TODO: 姓名/部門 --> | 安全審查、合規確認 | 設計、上線前 |
| 維運/SRE | <!-- TODO: 姓名/團隊 --> | 部署、監控、SLA 維護 | 上線、維護 |

---

## 3. 功能需求（Functional Requirements）

> 命名規則：`FR-NNN`，三位數字，按模組分段（FR-100 系列為認證模組，FR-200 系列為核心功能，依此類推）

### 3.1 認證與授權模組（FR-100）

| ID | 需求描述 | 優先級 | 對應 SPEC | 對應 ROADMAP | 驗收標準 |
|----|----------|--------|-----------|--------------|----------|
| FR-101 | 系統應支援電子郵件 + 密碼登入 | Must Have | SPEC-AUTH-001 | M1 | 正確憑證登入成功率 100%；錯誤憑證返回 401 |
| FR-102 | 系統應支援 OAuth 2.0 第三方登入（Google） | Should Have | SPEC-AUTH-002 | M2 | OAuth flow 完整可用；token 正確存儲 |
| FR-103 | 登入失敗 5 次後應鎖定帳號 15 分鐘 | Must Have | SPEC-AUTH-001 | M1 | 第 6 次嘗試返回 429；15 分鐘後自動解鎖 |
| FR-104 | 系統應支援角色型存取控制（RBAC） | Must Have | SPEC-AUTH-003 | M1 | 未授權角色存取返回 403；權限矩陣完整覆蓋 |
| <!-- FR-1xx --> | <!-- TODO: 補充需求 --> | | | | |

### 3.2 核心業務模組（FR-200）

| ID | 需求描述 | 優先級 | 對應 SPEC | 對應 ROADMAP | 驗收標準 |
|----|----------|--------|-----------|--------------|----------|
| FR-201 | <!-- TODO: 描述核心功能 1 --> | Must Have | <!-- TODO --> | M1 | <!-- TODO: 可量測的驗收標準 --> |
| FR-202 | <!-- TODO: 描述核心功能 2 --> | Should Have | <!-- TODO --> | M2 | <!-- TODO --> |
| FR-203 | <!-- TODO: 描述核心功能 3 --> | Nice to Have | <!-- TODO --> | M3 | <!-- TODO --> |

### 3.3 通知模組（FR-300）

| ID | 需求描述 | 優先級 | 對應 SPEC | 對應 ROADMAP | 驗收標準 |
|----|----------|--------|-----------|--------------|----------|
| FR-301 | 系統應於關鍵操作完成後發送 Email 通知 | Must Have | SPEC-NOTIFY-001 | M2 | Email 送達率 > 99%；延遲 < 30 秒 |
| FR-302 | 系統應支援站內通知（In-App Notification） | Should Have | SPEC-NOTIFY-002 | M2 | 即時推送；未讀數正確顯示 |

> **優先級定義：**
> - **Must Have**：MVP 必須實作，否則無法上線
> - **Should Have**：重要功能，應在初版完成
> - **Nice to Have**：有餘力時實作，可延至後續版本
> - **Won't Have (this time)**：明確排除於本版本

---

## 4. 非功能需求（Non-Functional Requirements）

| 類別 | 需求 | 目標值 | 驗證方式 |
|------|------|--------|----------|
| **效能** | API 回應時間（P95） | < 200ms | 負載測試（k6）：500 concurrent users |
| **效能** | 頁面首次內容繪製（FCP） | < 1.5s | Lighthouse CI 自動化檢測 |
| **效能** | 系統吞吐量 | > 1,000 RPS | 壓力測試報告 |
| **可用性** | 服務正常運行時間（SLA） | 99.9%（月計） | 監控儀表板 + 月度報告 |
| **可用性** | 計畫性停機窗口 | < 4 小時/月 | 維護日誌 |
| **安全性** | 密碼儲存 | bcrypt cost ≥ 12 | 程式碼審查 |
| **安全性** | 傳輸加密 | TLS 1.2+ | SSL Labs 評級 A |
| **安全性** | OWASP Top 10 合規 | 全項目通過 | 安全掃描報告（每季） |
| **可維護性** | 測試覆蓋率 | > 80%（核心模組 > 90%） | `make coverage` 報告 |
| **可維護性** | 程式碼複雜度（Cyclomatic） | < 10 | Lint 規則強制執行 |
| **擴展性** | 水平擴展 | 無狀態架構，支援多實例 | 多節點部署驗證 |
| **合規性** | 個資保護 | <!-- TODO: 填入適用法規 --> | 法務審查 |
| <!-- TODO --> | <!-- TODO: 補充 NFR --> | | |

---

## 5. 使用者故事（User Stories）

> 格式：`US-NNN: As a [角色], I want [功能], so that [目標]`

### 5.1 訪客（Guest）

---

**US-101: 使用者註冊**

- **As a** 訪客
- **I want** 使用電子郵件建立帳號
- **So that** 我可以存取系統功能

**Acceptance Criteria:**

- [ ] 電子郵件格式驗證通過才能提交
- [ ] 密碼強度需符合：至少 8 字元、含大小寫字母及數字
- [ ] 註冊成功後發送驗證信
- [ ] 重複電子郵件返回明確錯誤訊息
- [ ] 整個流程在 3 步驟內完成

**Maps to:** FR-101 | SPEC-AUTH-001 | Task: M1-T001

---

**US-102: 忘記密碼**

- **As a** 已註冊使用者
- **I want** 透過電子郵件重設密碼
- **So that** 我在忘記密碼時仍可存取帳號

**Acceptance Criteria:**

- [ ] 輸入已註冊 Email 後收到重設連結（< 60 秒）
- [ ] 重設連結有效期 24 小時
- [ ] 連結使用後立即失效
- [ ] 未註冊 Email 不揭露「帳號不存在」（防列舉攻擊）

**Maps to:** FR-101 | SPEC-AUTH-001 | Task: M1-T002

---

### 5.2 一般使用者（User）

---

**US-201: <!-- TODO: 功能名稱 -->**

- **As a** 一般使用者
- **I want** <!-- TODO -->
- **So that** <!-- TODO -->

**Acceptance Criteria:**

- [ ] <!-- TODO: 具體且可測試的驗收條件 -->
- [ ] <!-- TODO -->

**Maps to:** <!-- TODO: FR-xxx --> | <!-- SPEC-xxx --> | Task: <!-- M?-T??? -->

---

### 5.3 管理員（Admin）

---

**US-301: 使用者管理**

- **As a** 系統管理員
- **I want** 檢視與管理所有使用者帳號
- **So that** 我可以維護系統安全與使用者存取控制

**Acceptance Criteria:**

- [ ] 可搜尋、篩選使用者清單
- [ ] 可啟用/停用帳號（立即生效）
- [ ] 可變更使用者角色
- [ ] 所有操作記錄至稽核日誌

**Maps to:** FR-104 | SPEC-AUTH-003 | Task: M1-T010

---

## 6. 使用場景（Use Cases）

> 命名規則：`UC-NNN`

### UC-101: 使用者登入

**參與者：** 使用者、認證服務、資料庫

**前置條件：** 使用者已完成帳號驗證

**後置條件：** 使用者取得有效 Session/Token

#### 主要流程（Main Flow）

1. 使用者於登入頁輸入 Email 與密碼
2. 系統驗證 Email 格式
3. 系統於資料庫查詢使用者記錄
4. 系統驗證密碼雜湊
5. 系統產生 JWT Access Token（15 分鐘）與 Refresh Token（7 天）
6. 系統記錄登入事件（IP、時間戳）
7. 系統將使用者導向首頁

#### 替代流程（Alternative Flow）

- **A1 - OAuth 登入：** 使用者選擇「以 Google 登入」→ 導向 OAuth Provider → 回調並建立/連結帳號 → 繼續步驟 5

#### 異常流程（Exception Flow）

- **E1 - 密碼錯誤：** 步驟 4 失敗 → 記錄失敗次數 → 返回「Email 或密碼錯誤」（不區分）→ 若累計 ≥ 5 次，鎖定帳號並發送警告 Email
- **E2 - 帳號已鎖定：** 步驟 3 發現鎖定狀態 → 返回「帳號暫時鎖定」並提示解鎖時間
- **E3 - 資料庫連線失敗：** 任意步驟 → 返回 503 → 觸發告警通知維運團隊

---

### UC-201: <!-- TODO: 使用場景名稱 -->

**參與者：** <!-- TODO -->

**前置條件：** <!-- TODO -->

**後置條件：** <!-- TODO -->

#### 主要流程

1. <!-- TODO -->
2. <!-- TODO -->

#### 替代流程

- **A1 -** <!-- TODO -->

#### 異常流程

- **E1 -** <!-- TODO -->

---

## 7. 資料模型概覽（Data Model）

### 7.1 核心實體（Entities）

| 實體 | 說明 | 主要屬性 | 關聯 |
|------|------|----------|------|
| `User` | 系統使用者 | id, email, password_hash, role, status, created_at | 1:N → Session, 1:N → AuditLog |
| `Session` | 使用者登入 Session | id, user_id, refresh_token_hash, expires_at, ip, user_agent | N:1 → User |
| `Role` | 角色定義 | id, name, permissions (JSON) | N:N → User |
| `AuditLog` | 稽核日誌 | id, user_id, action, resource, ip, timestamp, detail | N:1 → User |
| <!-- TODO --> | <!-- TODO: 業務核心實體 --> | <!-- TODO --> | <!-- TODO --> |

### 7.2 狀態機（State Machine）

**User 帳號狀態：**

```
[Pending] --email_verified--> [Active]
[Active]  --admin_suspend-->  [Suspended]
[Active]  --5x_fail_login-->  [Locked]
[Locked]  --timeout/admin-->  [Active]
[Suspended] --admin_restore-> [Active]
[Active]  --user_delete-->    [Deleted]  (soft delete)
```

**<!-- TODO: 業務核心實體 --> 狀態：**

```
<!-- TODO: 描述業務實體的狀態機 -->
[Draft] --> [Submitted] --> [Approved] --> [Published]
                        \-> [Rejected] --> [Draft]
```

### 7.3 重要索引策略

| 資料表 | 索引欄位 | 類型 | 理由 |
|--------|----------|------|------|
| `users` | `email` | UNIQUE | 登入查詢唯一性 |
| `sessions` | `user_id`, `expires_at` | Composite | 清理過期 Session |
| `audit_logs` | `user_id`, `timestamp` | Composite | 使用者活動查詢 |
| <!-- TODO --> | <!-- TODO --> | | |

---

## 8. 介面規格（Interface Spec）

> **注意：** 當專案設定 `requires.uiux: true` 時，本節為必填項目。請同時維護 `UIUX_SPEC.md` 作為詳細規格。

### 8.1 頁面清單

| 路由 | 頁面名稱 | 存取權限 | 對應 US |
|------|----------|----------|---------|
| `/` | 首頁/Landing | Public | US-101 |
| `/login` | 登入頁 | Guest only | US-101 |
| `/register` | 註冊頁 | Guest only | US-101 |
| `/dashboard` | 儀表板 | Authenticated | US-201 |
| `/admin` | 管理後台 | Admin | US-301 |
| `/admin/users` | 使用者管理 | Admin | US-301 |
| `/profile` | 個人設定 | Authenticated | <!-- TODO --> |
| <!-- TODO --> | <!-- TODO --> | | |

### 8.2 導航結構

```
首頁 (/)
├── 登入 (/login)
├── 註冊 (/register)
└── [已登入]
    ├── 儀表板 (/dashboard)
    │   ├── 功能區塊 A
    │   └── 功能區塊 B
    ├── 個人設定 (/profile)
    └── [Admin only]
        └── 管理後台 (/admin)
            ├── 使用者管理 (/admin/users)
            └── 系統設定 (/admin/settings)
```

### 8.3 關鍵畫面描述

**登入頁（/login）：**
- 中央卡片式佈局，最大寬度 400px
- 欄位：Email input、Password input（含顯示/隱藏切換）
- 按鈕：「登入」（Primary）、「忘記密碼」（Link）
- 社群登入：Google OAuth 按鈕
- 錯誤訊息：行內顯示於對應欄位下方

**儀表板（/dashboard）：**
- 頂部 Navbar：Logo、主導航、通知鈴、使用者 Avatar + 下拉選單
- 左側 Sidebar（可收合）：功能模組導航
- 主內容區：<!-- TODO: 描述儀表板主要內容 -->

---

## 9. 限制與假設（Constraints & Assumptions）

### 9.1 技術限制

- **語言/框架**：前端 React 18+、後端 <!-- TODO: 填入技術棧 -->
- **資料庫**：<!-- TODO: e.g., PostgreSQL 15+ -->
- **瀏覽器支援**：最新兩個版本的 Chrome、Firefox、Safari、Edge（不支援 IE）
- **最低網路條件**：4G 行動網路（約 10 Mbps）

### 9.2 業務限制

- 初版上線日期：<!-- TODO: YYYY-MM-DD -->
- 開發人力：<!-- TODO: e.g., 2 前端 + 2 後端 + 1 QA -->
- 預算上限：<!-- TODO -->
- 法規合規：<!-- TODO: e.g., GDPR、個資法 -->

### 9.3 假設

- 假設使用者具備基本的網路使用能力，無需特殊技術背景
- 假設第三方服務（Email 服務、OAuth Provider）的可用性達 99.9% 以上
- 假設資料庫資料量在初版上線後一年內不超過 <!-- TODO: 數量 --> 筆記錄
- <!-- TODO: 補充其他關鍵假設 -->

### 9.4 依賴項目

| 外部依賴 | 用途 | 備用方案 |
|----------|------|----------|
| SendGrid / AWS SES | Email 發送 | <!-- TODO --> |
| Google OAuth | 社群登入 | 可降級為僅 Email 登入 |
| <!-- TODO --> | <!-- TODO --> | <!-- TODO --> |

---

## 10. 追溯矩陣（Traceability Matrix）

> 確保每個功能需求都有對應的使用者故事、規格書、ADR 及 Roadmap 任務。

| FR ID | 描述 | US ID | SPEC ID | ADR ID | ROADMAP Task |
|-------|------|-------|---------|--------|--------------|
| FR-101 | Email 密碼登入 | US-101 | SPEC-AUTH-001 | ADR-002 | M1-T001 |
| FR-102 | Google OAuth 登入 | US-101 | SPEC-AUTH-002 | ADR-002 | M2-T005 |
| FR-103 | 帳號鎖定機制 | US-101 | SPEC-AUTH-001 | ADR-002 | M1-T003 |
| FR-104 | RBAC 存取控制 | US-301 | SPEC-AUTH-003 | ADR-003 | M1-T010 |
| FR-201 | <!-- TODO --> | US-201 | <!-- TODO --> | <!-- TODO --> | <!-- TODO --> |
| FR-202 | <!-- TODO --> | <!-- TODO --> | <!-- TODO --> | <!-- TODO --> | <!-- TODO --> |
| FR-301 | Email 通知 | US-201 | SPEC-NOTIFY-001 | — | M2-T020 |
| FR-302 | 站內通知 | US-201 | SPEC-NOTIFY-002 | — | M2-T021 |

---

## 附錄

### A. 變更歷史

| 版本 | 日期 | 變更摘要 | 作者 |
|------|------|----------|------|
| v0.1.0 | <!-- TODO: YYYY-MM-DD --> | 初版建立 | <!-- TODO --> |

### B. 相關文件

- [`SDS.md`](./SDS.md) — 軟體設計規格書
- [`UIUX_SPEC.md`](./UIUX_SPEC.md) — UI/UX 規格書
- [`DEPLOY_SPEC.md`](./DEPLOY_SPEC.md) — 部署規格書
- [`docs/adr/`](./docs/adr/) — 架構決策記錄
- [`ROADMAP.md`](./ROADMAP.md) — 專案路線圖
