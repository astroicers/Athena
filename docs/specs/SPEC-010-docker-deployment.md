# SPEC-010：Docker 部署與一行啟動

> backend + frontend Dockerfile + docker-compose 更新，實現一行啟動完整 Demo。

| 欄位 | 內容 |
|------|------|
| **規格 ID** | SPEC-010 |
| **狀態** | Accepted |
| **關聯 ADR** | ADR-010（Docker Compose 部署拓樸） |
| **估算複雜度** | 低 |
| **建議模型** | Sonnet |
| **HITL 等級** | minimal |

---

## 🎯 目標（Goal）

> 建立 backend 和 frontend 的 Dockerfile，更新 docker-compose.yml 以支援完整建置，實現 `docker-compose up --build` 一行指令在 30 秒內啟動 Athena，`localhost:3000` 可直接存取完整 Demo。

---

## 📥 輸入規格（Inputs）

| 參數名稱 | 型別 | 來源 | 限制條件 |
|----------|------|------|----------|
| 部署拓樸 | ADR | ADR-010 決策 | 內部服務 backend+frontend |
| 後端依賴 | 檔案 | `backend/pyproject.toml` | Python 3.11 + FastAPI |
| 前端依賴 | 檔案 | `frontend/package.json` | Node 20 + Next.js 14 |
| 安全限制 | ADR | ADR-011 | 127.0.0.1 綁定 |
| 環境變數 | 檔案 | `.env.example` | 全部變數列表 |
| docker-compose.yml | SPEC | SPEC-001 輸出 | 基礎結構已建立 |

---

## 📤 輸出規格（Expected Output）

**成功情境：**

### 1. `backend/Dockerfile`

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安裝依賴
COPY pyproject.toml .
RUN pip install --no-cache-dir .

# 複製原始碼
COPY app/ ./app/

# 建立資料目錄
RUN mkdir -p /app/data

# 健康檢查
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python -c "import httpx; httpx.get('http://localhost:8000/api/health')" || exit 1

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

特點：
- 使用 `python:3.11-slim`（最小化映像）
- 兩階段 COPY（先依賴再原始碼，利用 Docker cache）
- 不複製 `tests/`、`data/*.db` 至映像
- 健康檢查端點 `/api/health`

### 2. `frontend/Dockerfile`

```dockerfile
FROM node:20-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci

COPY . .
RUN npm run build

FROM node:20-alpine AS runner

WORKDIR /app

COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public

EXPOSE 3000

CMD ["node", "server.js"]
```

特點：
- Multi-stage build（builder + runner）
- 使用 Next.js standalone 輸出（最小化映像）
- 需在 `next.config.js` 中啟用 `output: "standalone"`
- `node:20-alpine`（最小化基礎映像）

### 3. `docker-compose.yml`（更新版）

```yaml
version: "3.8"

services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "127.0.0.1:8000:8000"
    volumes:
      - backend-data:/app/data
    env_file:
      - .env
    environment:
      - DATABASE_URL=sqlite:///app/data/athena.db
    healthcheck:
      test: ["CMD", "python", "-c", "import httpx; httpx.get('http://localhost:8000/api/health')"]
      interval: 30s
      timeout: 5s
      retries: 3
    restart: unless-stopped

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "127.0.0.1:3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://backend:8000/api
      - NEXT_PUBLIC_WS_URL=ws://backend:8000/ws
    depends_on:
      backend:
        condition: service_healthy
    restart: unless-stopped

volumes:
  backend-data:
    driver: local
```

變更重點：
- `127.0.0.1` port binding（ADR-011）
- named volume `backend-data`（SQLite 持久化）
- frontend `depends_on` 使用 `service_healthy` 條件
- `DATABASE_URL` 覆寫為容器內路徑
- `restart: unless-stopped`

### 4. `.dockerignore`

#### `backend/.dockerignore`

```
__pycache__/
*.pyc
*.pyo
.venv/
tests/
data/*.db
data/*.db-*
.env
.env.*
```

#### `frontend/.dockerignore`

```
node_modules/
.next/
out/
.env
.env.*
```

### 5. `next.config.js` 更新

```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",  // 新增：Docker standalone 模式
  // ... 其他已有配置
};

module.exports = nextConfig;
```

### 6. Makefile 更新

新增/更新 Docker 相關 target：

```makefile
# Docker 完整啟動
up:
	docker-compose up --build -d

# Docker 停止
down:
	docker-compose down

# Docker 日誌
logs:
	docker-compose logs -f

# Docker 清除（含 volume）
docker-clean:
	docker-compose down -v --rmi local
```

**失敗情境：**

| 錯誤類型 | 處理方式 |
|----------|----------|
| port 已被佔用 | docker-compose 報錯，使用者需釋放 port |
| .env 不存在 | backend 使用預設值啟動（SQLite 預設路徑） |
| 前端建置失敗 | Docker build 中止，輸出 npm 錯誤訊息 |
| 後端健康檢查失敗 | frontend 不啟動（depends_on condition） |

---

## ⚠️ 邊界條件（Edge Cases）

- SQLite 資料庫透過 Docker named volume 持久化——容器重建不遺失資料
- `NEXT_PUBLIC_API_URL` 在 Docker 容器間使用 `http://backend:8000`（Docker DNS）
- 瀏覽器端的 WebSocket URL 仍為 `ws://localhost:8000/ws`（前端 `.env` 中的 `NEXT_PUBLIC_WS_URL`）
- `frontend` 的環境變數為 build-time（Next.js `NEXT_PUBLIC_*`），需在 Dockerfile 中處理
- Docker Compose v2 不需 `version: "3.8"` 聲明（但保留向後相容）
- `backend` 首次啟動需自動 `init_db()` + 載入種子資料（在 `main.py` lifespan 中）
- Caldera 為外部服務，不在 docker-compose 中（ADR-010）
- backend Dockerfile 的 `pip install --no-cache-dir .` 已包含 `httpx` 依賴（`pyproject.toml` 中宣告），HEALTHCHECK 的 `import httpx` 可正常運行

---

## 🔗 副作用與連動（Side Effects）

| 副作用 | 觸發條件 | 影響的系統/模組 | 驗證方式 |
|--------|---------|----------------|----------|
| SQLite DB 持久化 | `docker-compose up` 建立 named volume | `backend-data` Docker volume → `athena.db` | `docker-compose down && docker-compose up` 後資料仍存在 |
| Port 綁定 127.0.0.1 | docker-compose 啟動 | 主機 8000（backend）、3000（frontend）port | `curl http://localhost:8000/api/health` 成功；外部 IP 不可存取 |
| Next.js standalone 輸出 | `next.config.js` 設定 `output: "standalone"` | frontend build 產出結構、Docker image 大小 | `docker images | grep athena` frontend < 200MB |
| 自動初始化 DB + 種子資料 | backend 首次啟動 lifespan | `init_db()` + seed data 載入 | `curl http://localhost:8000/api/operations` 回傳種子資料 |

### 🔄 Rollback Plan

| 項目 | 說明 |
|------|------|
| **回滾步驟** | `git revert` 移除 `backend/Dockerfile`、`frontend/Dockerfile`、`backend/.dockerignore`、`frontend/.dockerignore`；還原 `docker-compose.yml` 至 SPEC-001 版本；還原 `next.config.js` 移除 `output: "standalone"` |
| **資料影響** | `docker-compose down -v` 清除 named volume 中的 SQLite 資料庫；開發環境資料不受影響 |
| **回滾驗證** | `docker-compose up` 使用舊配置正常啟動（或回到本地開發模式）；`make up` / `make down` 指令移除 |
| **回滾已測試** | ☐ 是 / ☑ 否（Docker 配置為獨立基礎設施層，回滾不影響應用程式碼） |

## 🧪 測試矩陣（Test Matrix）

| # | 類型 | 輸入條件 | 預期結果 | 對應場景 |
|---|------|---------|---------|---------|
| P1 | ✅ 正向 | `docker-compose up --build` | 30 秒內啟動，backend healthy、frontend running | S1 |
| P2 | ✅ 正向 | `curl http://localhost:8000/api/health` | `{"status":"ok"}` 含所有服務狀態 | S1 |
| P3 | ✅ 正向 | 瀏覽器開啟 `http://localhost:3000` | 顯示 Athena C5ISR Board，種子資料渲染 | S1 |
| N1 | ❌ 負向 | Port 8000 或 3000 已被佔用 | docker-compose 報錯明確指出 port conflict | S2 |
| N2 | ❌ 負向 | `.env` 不存在 | backend 使用預設值啟動（SQLite 預設路徑），不 crash | S2 |
| N3 | ❌ 負向 | frontend build 失敗（npm error） | Docker build 中止，輸出清晰的 npm 錯誤訊息 | S2 |
| B1 | 🔶 邊界 | `docker-compose down && docker-compose up`（無 -v） | 資料持久化，種子資料不重複載入 | S3 |
| B2 | 🔶 邊界 | `docker-compose down -v && docker-compose up --build` | Volume 清除後重新初始化 DB + 種子資料 | S3 |

## 🎬 驗收場景（Acceptance Scenarios）

```gherkin
Feature: SPEC-010 Docker 部署與一行啟動
  作為 Athena 平台開發者
  我想要 docker-compose up --build 一行啟動完整 Demo
  以便 30 秒內在 localhost:3000 存取 Athena

  Background:
    Given Docker 和 docker-compose 已安裝
    And Port 8000 和 3000 未被佔用

  Scenario: S1 - 一行啟動完整環境
    Given .env 檔案已設定（或使用預設值）
    When docker-compose up --build
    Then backend 服務在 30 秒內啟動且 healthcheck 通過
    And frontend 服務啟動且依賴 backend healthy
    And curl http://localhost:8000/api/health 回傳 {"status":"ok"}
    And 瀏覽器開啟 http://localhost:3000 顯示 C5ISR Board

  Scenario: S2 - Port 衝突明確報錯
    Given Port 8000 已被其他程序佔用
    When docker-compose up --build
    Then docker-compose 輸出 port binding 錯誤訊息
    And 不產生 silent failure

  Scenario: S3 - 資料持久化跨容器重建
    Given docker-compose up 已執行且 Demo 產生了 OODA 記錄
    When docker-compose down（不加 -v）
    And docker-compose up
    Then 先前的 OODA 記錄仍存在（named volume 持久化）
    And 種子資料不重複載入

  Scenario: S4 - 127.0.0.1 安全綁定
    Given docker-compose up 已執行
    When 從外部 IP 嘗試存取 8000/3000 port
    Then 連線被拒絕（僅 localhost 可存取）
```

## 🔍 追溯性（Traceability）

| 類型 | 檔案路徑 |
|------|---------|
| 實作 — Backend Dockerfile | `backend/Dockerfile` |
| 實作 — Frontend Dockerfile | `frontend/Dockerfile` |
| 實作 — Docker Compose | `docker-compose.yml` |
| 實作 — Docker Compose Override | `docker-compose.override.yml` |
| 實作 — Backend .dockerignore | `backend/.dockerignore` |
| 實作 — Frontend .dockerignore | `frontend/.dockerignore` |
| 實作 — Health 端點 | `backend/app/routers/health.py` |
| 實作 — Main lifespan（init_db） | `backend/app/main.py` |
| 參考 — C2 Engine Compose | `infra/c2-engine/docker-compose.c2-engine.yml` |

## 👁️ 可觀測性（Observability）

| 項目 | 說明 |
|------|------|
| **關鍵指標** | 容器啟動時間、image 大小（backend < 500MB、frontend < 200MB）、healthcheck 間隔 30s |
| **日誌** | `docker-compose logs -f` 查看 backend uvicorn 日誌 + frontend Node.js 日誌 |
| **錯誤追蹤** | healthcheck 失敗 → container restart（`restart: unless-stopped`）；frontend depends_on 確保 backend 先就緒 |
| **健康檢查** | backend: `GET /api/health` 每 30s（timeout 5s, retries 3）；frontend: depends_on service_healthy |

---

## ✅ 驗收標準（Done When）

- [x] `docker-compose up --build` — 30 秒內啟動成功
- [x] `curl http://localhost:8000/api/health` — 回傳 `{"status": "ok"}`
- [x] `curl http://localhost:8000/api/operations` — 回傳種子資料
- [x] 瀏覽器開啟 `http://localhost:3000` — 顯示 Athena C5ISR Board
- [x] `docker-compose down && docker-compose up` — 資料持久化（volume）
- [x] `docker images | grep athena` — backend 映像 < 500MB，frontend 映像 < 200MB（multi-stage build 已配置，python:3.11-slim + node:20-alpine）
- [x] `docker-compose ps` — 兩個服務均為 healthy
- [x] `make up` / `make down` — Makefile 指令正常運作

---

## 🚫 禁止事項（Out of Scope）

- 不要在 docker-compose 中加入 Caldera 或 Shannon——外部服務（ADR-010）
- 不要加入 nginx 反向代理——POC 直連（Phase 8 考慮）
- 不要加入 SSL/TLS 設定——POC 使用 HTTP
- 不要建立 CI/CD pipeline（GitHub Actions）——Phase 7 範圍
- 不要建立 Helm Chart——Phase 8 範圍
- 不要使用 docker-compose profiles——保持簡單

---

## 📎 參考資料（References）

- ADR-010：[Docker Compose 部署拓樸](../adr/ADR-010-docker-compose-deployment.md)
- ADR-011：[POC 無身份驗證](../adr/ADR-011-no-auth-for-poc.md)（127.0.0.1 綁定）
- SPEC-001：專案骨架（依賴——docker-compose.yml 基礎結構）
- SPEC-004：REST API（依賴——`/api/health` 端點）

