# [ADR-002]: Monorepo 專案結構

| 欄位 | 內容 |
|------|------|
| **狀態** | `Accepted` |
| **日期** | 2026-02-23 |
| **決策者** | 專案負責人 |

---

## 背景（Context）

Athena 包含三個主要技術層：Python 後端（FastAPI）、Next.js 前端、以及 Pencil.dev 設計資產（`.pen` 檔）。Phase 1 需決定程式碼倉庫的組織方式，這將影響整個開發週期的依賴管理、CI/CD 配置、版本控制與部署流程。

限制條件：
- **單人開發**：無需跨團隊權限隔離
- **共用型別**：前後端需同步 13 個 Enum 與 12 個 Model 定義
- **設計資產**：6 個 `.pen` 檔需與程式碼版本一致
- **Docker Compose**：前後端透過同一編排檔部署

---

## 評估選項（Options Considered）

### 選項 A：Monorepo（單一倉庫）

- **優點**：一次 `git clone` 取得全部；前後端型別同步無延遲；`docker-compose.yml` 直接引用相對路徑；設計稿與程式碼版本一致；單人開發零協調成本
- **缺點**：倉庫體積隨設計資產增長；未來多團隊需更細緻的 CODEOWNERS 設定
- **風險**：`.pen` 二進位檔案增大 Git history（可透過 `.gitattributes` 或 Git LFS 緩解）

### 選項 B：Polyrepo（多倉庫：backend / frontend / design）

- **優點**：各倉庫獨立版本；團隊可獨立部署
- **缺點**：共用型別需額外 npm/PyPI 套件或 Git submodule；`docker-compose.yml` 需跨倉庫引用；版本同步成本高
- **風險**：單人開發維護 3 個倉庫的 overhead 過高；型別不同步導致 runtime 錯誤

---

## 決策（Decision）

我們選擇 **選項 A：Monorepo**，因為：

1. 單人 POC 開發不需要 polyrepo 的團隊隔離優勢
2. 前後端共用 Enum/Model 定義可透過同倉庫目錄直接對照，消除同步延遲
3. `docker-compose.yml` 直接使用 `./backend` 和 `./frontend` 相對路徑建置
4. 設計稿（`.pen`）與程式碼版本永遠一致

目錄佈局：

```
Athena/
├── backend/       # Python 3.11 + FastAPI
├── frontend/      # Next.js 14 + React 18
├── design/        # 6 個 .pen 設計資產
├── docs/          # 架構文件 + ADR
├── infra/         # Docker 配置
└── docker-compose.yml
```

---

## 後果（Consequences）

**正面影響：**

- `git clone` + `docker-compose up` 即可啟動全環境
- 型別定義變更在同一 commit 內同步前後端
- CI/CD 流水線可一次執行 backend + frontend 測試

**負面影響 / 技術債：**

- `.pen` 檔案為二進位格式，增大倉庫體積（POC 可接受，正式版考慮 Git LFS）
- 未來多團隊開發需建立 CODEOWNERS 與路徑級權限

**後續追蹤：**

- [ ] Phase 1：建立完整目錄骨架並搬移 `.pen` 檔至 `design/`
- [ ] Phase 7：評估 `.pen` 檔是否需要 Git LFS

---

## 關聯（Relations）

- 取代：（無）
- 被取代：（無）
- 參考：ADR-001（技術棧決定了 monorepo 內的子目錄結構）、ADR-007（WebSocket 通訊架構）、ADR-010（Docker Compose 部署拓樸）
