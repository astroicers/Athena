# [ADR-010]: Docker Compose 部署拓樸

| 欄位 | 內容 |
|------|------|
| **狀態** | `Accepted` |
| **日期** | 2026-02-23 |
| **決策者** | 專案負責人 |

---

## 背景（Context）

Phase 1 需建立 `docker-compose.yml`，Phase 6 需實現「一行指令啟動完整 Demo」。Athena 涉及 4 個服務（backend、frontend、Caldera、Shannon），需決定哪些服務納入 Docker Compose 編排，哪些作為外部服務獨立部署。

此決策與 ADR-006（授權隔離）直接相關——Shannon 的 AGPL-3.0 授權要求 API-only 隔離。

---

## 評估選項（Options Considered）

### 選項 A：內部服務（backend + frontend）+ 外部引擎（Caldera / Shannon）

```yaml
# docker-compose.yml — Athena 管理
services:
  backend:    # Python 3.11 + FastAPI, :8000
  frontend:   # Next.js 14, :3000

# 外部服務 — 使用者自行啟動
# Caldera :8888 (必要)
# Shannon :9000 (選用)
```

- **優點**：
  - 授權邊界清晰——AGPL Shannon 不在 Athena Compose 內
  - Caldera 有自己的 docker-compose.yml（MITRE 官方提供），不需重新封裝
  - `docker-compose up` 啟動 Athena 本體 < 3.5 GB RAM
  - 外部服務透過 `CALDERA_URL` / `SHANNON_URL` 環境變數連接
- **缺點**：使用者需額外啟動 Caldera（非一行指令完成全部）
- **風險**：Demo 需事先確保 Caldera 已運行（可用健康檢查 + 啟動提示緩解）

### 選項 B：全部納入 Docker Compose（4 個服務）

- **優點**：真正的一行指令啟動
- **缺點**：Shannon AGPL 原始碼會包含在 Compose context 中（潛在授權爭議）；Caldera 容器需自行維護 Dockerfile（MITRE 官方的不完全相容）；資源需求 > 5.5 GB RAM
- **風險**：授權邊界模糊；4 核 8 GB 最低配置不足

### 選項 C：全部本機裸跑（無 Docker）

- **優點**：無容器 overhead
- **缺點**：Python 虛擬環境 + Node.js 版本 + Caldera 安裝 = 環境配置地獄；無法保證可重現性
- **風險**：Demo 環境差異導致失敗

---

## 決策（Decision）

我們選擇 **選項 A：內部服務 + 外部引擎**，因為：

1. **授權安全**：Shannon 不在 Athena Compose context 內，消除 AGPL 打包爭議
2. **資源控制**：Athena 本體 ~3.5 GB RAM，留給 Caldera 2 GB（共 5.5 GB 在 8 GB 主機可行）
3. **Caldera 獨立性**：MITRE 官方提供完整的 Caldera Docker 部署方案，不需重新封裝
4. **開發靈活性**：`make dev-backend` / `make dev-frontend` 可本機裸跑前後端

部署拓樸：

```
┌─────────────────────────────────┐
│ docker-compose.yml (Athena)     │
│                                 │
│  backend (:8000)                │
│    └─ volume: ./backend/data    │
│                                 │
│  frontend (:3000)               │
│    └─ depends_on: backend       │
└──────────────┬──────────────────┘
               │ HTTP API
       ┌───────┴───────┐
       ↓               ↓
    Caldera         Shannon
    (:8888)         (:9000)
    外部服務        外部服務（選用）
```

環境變數對接：

```bash
# .env
CALDERA_URL=http://localhost:8888     # 外部 Caldera
SHANNON_URL=                           # 空 = 停用 Shannon
NEXT_PUBLIC_API_URL=http://localhost:8000/api
```

---

## 後果（Consequences）

**正面影響：**

- `docker-compose up` 在 30 秒內啟動 Athena，不需等 Caldera 建置
- SQLite 資料透過 volume mount 持久化，容器重建不遺失
- 開發模式可混用：Docker frontend + 本機 backend（或反之）

**負面影響 / 技術債：**

- Demo 前需手動確認 Caldera 已啟動（可透過 backend 健康檢查端點顯示外部服務狀態）
- 無 nginx 反向代理——前端直連 backend API（POC 可接受，Phase 8 需加入）
- container networking vs localhost 差異需在 `.env.example` 清楚說明

**後續追蹤：**

- [ ] Phase 1.2：建立 `docker-compose.yml` + `.env.example`
- [ ] Phase 2.5：backend 加入 `/health` 端點（含 Caldera 連線狀態）
- [ ] Phase 6.3：撰寫 `backend/Dockerfile` + `frontend/Dockerfile`
- [ ] Phase 8.6：考慮 Helm Chart 取代 Docker Compose

---

## 關聯（Relations）

- 取代：（無）
- 被取代：（無）
- 參考：ADR-001（Docker Compose 選型）、ADR-002（Monorepo 結構決定 build context）、ADR-006（授權隔離——Shannon 外部部署）、ADR-011（無身份驗證下以 localhost 綁定緩解）
