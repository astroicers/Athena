# SPEC-010：Docker 部署與一行啟動

> backend + frontend Dockerfile + docker-compose 更新，實現一行啟動完整 Demo。

| 欄位 | 內容 |
|------|------|
| **規格 ID** | SPEC-010 |
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

## ✅ 驗收標準（Done When）

- [ ] `docker-compose up --build` — 30 秒內啟動成功
- [ ] `curl http://localhost:8000/api/health` — 回傳 `{"status": "ok"}`
- [ ] `curl http://localhost:8000/api/operations` — 回傳種子資料
- [ ] 瀏覽器開啟 `http://localhost:3000` — 顯示 Athena C5ISR Board
- [ ] `docker-compose down && docker-compose up` — 資料持久化（volume）
- [ ] `docker images | grep athena` — backend 映像 < 500MB，frontend 映像 < 200MB
- [ ] `docker-compose ps` — 兩個服務均為 healthy
- [ ] `make up` / `make down` — Makefile 指令正常運作

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
