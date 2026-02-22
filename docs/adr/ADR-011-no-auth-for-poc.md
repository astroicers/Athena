# [ADR-011]: POC 階段不實作身份驗證

| 欄位 | 內容 |
|------|------|
| **狀態** | `Accepted` |
| **日期** | 2026-02-23 |
| **決策者** | 專案負責人 |

---

## 背景（Context）

Athena 後端提供 35+ REST API 端點與 WebSocket 連線。在 POC 階段需明確決策：是否實作身份驗證與存取控制。

限制條件：
- POC 為**單人本機部署**，不暴露至公開網路
- 目標使用者為專案負責人本人（單一指揮官）
- `users` 表已設計為最小化 stub（callsign + role，無密碼欄位）
- Phase 8.3 規劃了 JWT + RBAC 的正式身份驗證

此決策需要正式記錄，避免日後被誤判為安全疏漏。

---

## 評估選項（Options Considered）

### 選項 A：POC 不實作身份驗證

- **優點**：零開發成本；API 測試不需管理 token；Demo 演示流暢不被登入畫面中斷；FastAPI Swagger UI 可直接測試所有端點
- **缺點**：任何能存取 localhost 的程序皆可呼叫 API
- **風險**：**僅限本機部署**——若暴露至網路則所有 API 無保護（透過 CORS 限制 + 網路隔離緩解）

### 選項 B：API Key 靜態驗證

在 `.env` 中設定一組 API key，所有請求需攜帶 `X-API-Key` header。

- **優點**：最低限度保護
- **缺點**：開發時每個 API 呼叫都需附帶 header；Swagger UI 需額外配置 API key 輸入；前端需管理 key 儲存
- **風險**：API key 為靜態值，安全性有限；增加 POC 複雜度但實質保護極低

### 選項 C：JWT + RBAC 完整實作

- **優點**：正式環境就緒
- **缺點**：需實作登入頁面、token 管理、refresh 邏輯、角色權限矩陣；開發時間增加 2-3 天；偏離 POC 核心目標
- **風險**：過度設計；OODA 循環引擎才是 POC 核心，不應被身份驗證拖慢進度

---

## 決策（Decision）

我們選擇 **選項 A：POC 不實作身份驗證**，因為：

1. **POC 核心是 OODA 引擎**——身份驗證不是需要驗證的概念
2. **單人本機部署**——無多使用者場景，認證無實際作用
3. **Demo 流暢性**——登入畫面打斷「C5ISR 指揮」的展示敘事
4. **Phase 8.3 明確排程**——JWT + RBAC 為正式版功能

安全緩解措施：

| 措施 | 目的 |
|------|------|
| CORS 限制 `localhost:3000` | 僅允許 Athena 前端存取 API |
| `.env` 管理所有 API 金鑰 | 不提交機密至 Git |
| 不暴露至公開網路 | Docker 綁定 `127.0.0.1` |
| `users` 表保留 stub | Phase 8 擴充為完整身份模型 |

`users` 表 POC schema：

```sql
CREATE TABLE users (
    id TEXT PRIMARY KEY,
    callsign TEXT NOT NULL,                    -- 顯示名稱（如 "VIPER-1"）
    role TEXT DEFAULT 'Commander',             -- 單一角色 stub
    created_at TEXT DEFAULT (datetime('now'))
);
```

---

## 後果（Consequences）

**正面影響：**

- 開發速度不受身份驗證拖累，聚焦 OODA 引擎核心
- Swagger UI（`localhost:8000/docs`）可直接測試所有 API
- Demo 從 C5ISR 看板直接開始，不需登入流程

**負面影響 / 技術債：**

- Phase 8 需從零建立 JWT middleware + 登入頁面 + token refresh
- 所有 API router 需加入 `Depends(get_current_user)` 權限檢查
- WebSocket 連線需加入 token 驗證握手
- 需為 3 個角色（指揮官 / 操作員 / 觀察員）建立權限矩陣

**後續追蹤：**

- [ ] Phase 1：確認 Docker 綁定 `127.0.0.1`
- [ ] Phase 2：CORS middleware 限制 `localhost:3000`
- [ ] Phase 8.3：實作 JWT + RBAC（users 表擴充 password_hash、roles 欄位）

---

## 關聯（Relations）

- 取代：（無）
- 被取代：（未來 ADR — Phase 8.3 JWT+RBAC 實作時將取代本 ADR）
- 參考：ADR-008（users 表 stub 設計）、ADR-010（Docker 綁定 localhost）
