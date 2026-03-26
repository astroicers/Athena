# 部署規格書 (Deployment Specification)

---

| 欄位 | 內容 |
|------|------|
| **專案名稱** | Athena — AI 驅動 C5ISR 網路作戰指揮平台 |
| **版本** | v0.1.0 |
| **最後更新** | 2026-03-25 |
| **狀態** | Accepted |
| **作者** | Athena 開發團隊 |
| **審閱者** | 技術負責人 |

---

## 1. 環境定義

### 1.1 環境清單

| 環境 | 用途 | URL | 部署觸發 | 資料重置 |
|------|------|-----|----------|----------|
| `local` | 本地開發與整合測試 | `http://localhost:58080`（前端）/ `http://localhost:58000`（API） | 手動 `docker compose up -d` | 隨時 |
| `dev` | **尚未建立** — 計畫於 v0.2.0 導入 | — | — | — |
| `staging` | **尚未建立** — 計畫於 v0.3.0 導入 | — | — | — |
| `prod` | **尚未建立** — 計畫於 v0.4.0 導入 | — | — | — |

> **現況**：目前僅有 `local` 環境，所有開發與測試均在本地 Docker Compose 進行。

### 1.2 環境差異對照

| 項目 | Local（現行） | Dev（計畫） | Staging（計畫） | Prod（計畫） |
|------|--------------|------------|----------------|-------------|
| 資料庫 | Docker PostgreSQL 16-alpine | 待定 | 待定 | 待定 |
| API 實例數 | 1 | 1 | 2 | 待定 |
| Log Level | INFO（可透過 `.env` 調整） | DEBUG | INFO | WARN |
| Mock 模式 | 可切換（`make mock-mode` / `make real-mode`） | 部分 Mock | 全部真實 | 全部真實 |
| MCP 工具 | 選用（`--profile mcp`） | 啟用 | 啟用 | 啟用 |
| C2 引擎 | 選用（`--profile c2`） | 啟用 | 啟用 | 啟用 |
| Metasploit | 選用（`--profile msf`） | 依需 | 依需 | 受控啟用 |

### 1.3 環境變數清單

> **安全規則**：所有敏感值（API Key、密碼）禁止硬編碼，透過 `.env` 檔注入。`.env` 已被 `.gitignore` 排除。

#### LLM 與 AI 設定

| 變數名 | 類型 | 必填 | 預設值 | 說明 |
|--------|------|------|--------|------|
| `LLM_BACKEND` | string | 否 | `auto` | LLM 後端模式：`auto`/`anthropic`/`openai` |
| `ANTHROPIC_API_KEY` | string | 是 | （空） | Anthropic API Key（Orient AI 核心所需） |
| `OPENAI_API_KEY` | string | 否 | （空） | OpenAI API Key（備選 LLM） |
| `MOCK_LLM` | boolean | 否 | `false` | `true` 時使用 Mock LLM，不需真實 API Key |

#### 資料庫

| 變數名 | 類型 | 必填 | 預設值 | 說明 |
|--------|------|------|--------|------|
| `DATABASE_URL` | string | 是 | `sqlite:///backend/data/athena.db`（本地）<br>`postgresql://athena:...@postgres:5432/athena`（Docker） | 資料庫連線字串 |
| `POSTGRES_PASSWORD` | string | 否 | `athena_secret` | PostgreSQL 密碼（Docker Compose 使用） |

#### 前端

| 變數名 | 類型 | 必填 | 預設值 | 說明 |
|--------|------|------|--------|------|
| `NEXT_PUBLIC_API_URL` | string | 是 | `http://localhost:58000/api` | 後端 API 位址（前端呼叫用） |
| `NEXT_PUBLIC_WS_URL` | string | 是 | `ws://localhost:58000/ws` | WebSocket 位址（即時通訊） |

#### C2 攻擊執行引擎（Caldera）

| 變數名 | 類型 | 必填 | 預設值 | 說明 |
|--------|------|------|--------|------|
| `CALDERA_URL` | string | 否 | `http://caldera:8888` | Caldera 引擎 URL |
| `CALDERA_AGENT_CALLBACK_URL` | string | 否 | — | 靶機可達的 Caldera 外部 URL |
| `CALDERA_API_KEY` | string | 否 | — | Caldera API Key |
| `C2_ENGINE_URL` | string | 否 | `http://c2-engine:8888` | Docker 內部 C2 引擎 URL |
| `C2_ENGINE_API_KEY` | string | 否 | `ADMIN123456` | C2 引擎 API Key |
| `MOCK_C2_ENGINE` | boolean | 否 | `false` | `true` 時使用 Mock C2 引擎 |

#### Metasploit RPC

| 變數名 | 類型 | 必填 | 預設值 | 說明 |
|--------|------|------|--------|------|
| `MSF_RPC_HOST` | string | 否 | `127.0.0.1`（本地）/ `msf-rpc`（Docker） | Metasploit RPC 主機 |
| `MSF_RPC_PORT` | number | 否 | `55553` | Metasploit RPC 埠號 |
| `MSF_RPC_USER` | string | 否 | `msf` | Metasploit RPC 使用者名稱 |
| `MSF_RPC_PASSWORD` | string | 否 | `msf_password` | Metasploit RPC 密碼 |
| `MOCK_METASPLOIT` | boolean | 否 | `false` | `true` 時使用 Mock Metasploit |

#### MCP 工具伺服器

| 變數名 | 類型 | 必填 | 預設值 | 說明 |
|--------|------|------|--------|------|
| `MCP_ENABLED` | boolean | 否 | `true` | 是否啟用 MCP 工具整合 |
| `NVD_API_KEY` | string | 否 | （空） | NVD 漏洞資料庫 API Key（mcp-vuln 使用） |
| `SESSION_IDLE_TIMEOUT_SEC` | number | 否 | `300` | 攻擊執行器 session 閒置逾時（秒） |
| `NUCLEI_TEMPLATES_DIR` | string | 否 | `/opt/nuclei-templates` | Nuclei 掃描模板目錄 |
| `SCAN_RATE_LIMIT` | number | 否 | `100` | Web Scanner 速率限制 |
| `SCAN_TIMEOUT_SEC` | number | 否 | `300` | Web Scanner 逾時（秒） |
| `FUZZ_RATE_LIMIT` | number | 否 | `50` | API Fuzzer 速率限制 |
| `FUZZ_TIMEOUT_SEC` | number | 否 | `180` | API Fuzzer 逾時（秒） |
| `MAX_ENDPOINTS` | number | 否 | `500` | API Fuzzer 最大端點數 |

#### 自動化與日誌

| 變數名 | 類型 | 必填 | 預設值 | 說明 |
|--------|------|------|--------|------|
| `AUTOMATION_MODE` | string | 否 | `semi_auto` | 自動化模式：`manual` / `semi_auto` |
| `RISK_THRESHOLD` | string | 否 | `medium` | 風險閾值：`low` / `medium` / `high` / `critical` |
| `LOG_LEVEL` | string | 否 | `INFO` | 日誌等級：`DEBUG` / `INFO` / `WARNING` / `ERROR` |
| `SHANNON_URL` | string | 否 | （空） | Shannon 引擎 URL（選用，留空停用） |

---

## 2. Container 規格

### 2.1 服務架構總覽

```
                    ┌──────────────────────────────────────────────────┐
                    │                Docker Compose                    │
                    │                                                  │
  :58080 ─────────▶ │  ┌───────────┐     ┌───────────┐     ┌────────┐ │
  (前端)            │  │ frontend  │────▶│ backend   │────▶│postgres│ │
                    │  │ Next.js   │     │ FastAPI   │     │ PG 16  │ │
  :58000 ─────────▶ │  │ :3000     │     │ :8000     │     │ :5432  │ │
  (API)             │  └───────────┘     └─────┬─────┘     └────────┘ │
                    │                          │                       │
                    │         ┌────────────────┼────────────────┐      │
                    │         ▼                ▼                ▼      │
                    │  ┌────────────┐  ┌────────────┐  ┌───────────┐  │
                    │  │ c2-engine  │  │  msf-rpc   │  │ MCP Tools │  │
                    │  │ (Caldera)  │  │(Metasploit)│  │ (7 servers)│ │
                    │  │ :58888     │  │ :55553     │  │ :58091-97 │  │
                    │  │ profile:c2 │  │ profile:msf│  │ profile:mcp│ │
                    │  └────────────┘  └────────────┘  └───────────┘  │
                    └──────────────────────────────────────────────────┘
```

### 2.2 Core Services

#### PostgreSQL

```yaml
# postgres:16-alpine
# Port: 127.0.0.1:55432 → 5432（僅本機可存取）
# Volume: pgdata（持久化）
# Health: pg_isready -U athena（interval: 10s, timeout: 5s, retries: 5）
```

- 資料庫名：`athena`、使用者：`athena`
- 密碼透過 `POSTGRES_PASSWORD` 環境變數注入（預設 `athena_secret`）
- 啟動期等待 10 秒後開始健康檢查

#### Backend — FastAPI

```dockerfile
FROM python:3.12-slim
# 系統依賴：nmap（python-nmap 掃描所需）+ curl（健康檢查）
RUN apt-get update && apt-get install -y --no-install-recommends nmap curl
# 依賴安裝：pip install from pyproject.toml
# 應用程式：app/ + alembic/（DB migration）
# 資料目錄：/app/data
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -sf http://localhost:8000/api/health || exit 1
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--loop", "uvloop"]
```

- Port 映射：`0.0.0.0:58000 → 8000`
- Volume 掛載：`backend-data:/app/data`、Claude 憑證（唯讀）、MCP 伺服器設定（唯讀）
- 啟動順序：等待 PostgreSQL 健康後啟動
- 重啟策略：`unless-stopped`

#### Frontend — Next.js

```dockerfile
# Stage 1: Build
FROM node:20-alpine AS builder
RUN npm ci && npm run build

# Stage 2: Production（standalone output）
FROM node:20-alpine AS runner
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public
COPY --from=builder /app/messages ./messages    # i18n 訊息檔
ENV NODE_ENV=production
EXPOSE 3000
CMD ["node", "server.js"]
```

- Port 映射：`0.0.0.0:58080 → 3000`
- Multi-stage build：最終映像僅含 standalone 產出
- 啟動順序：等待 Backend 健康後啟動
- 重啟策略：`unless-stopped`

### 2.3 Optional Services（Profile 啟用）

#### C2 引擎（Caldera）— profile: `c2`

| 項目 | 規格 |
|------|------|
| 映像 | `ghcr.io/mitre/caldera:latest` |
| Port | `0.0.0.0:58888 → 8888` |
| Volume | `infra/c2-engine/local.yml`（設定）、`c2-engine-data`（資料） |
| 啟用方式 | `docker compose --profile c2 up -d` |
| 授權 | Apache 2.0 |

#### Metasploit RPC — profile: `msf`

| 項目 | 規格 |
|------|------|
| 映像 | `metasploitframework/metasploit-framework:latest` |
| Port | `127.0.0.1:55553 → 55553`（僅本機） |
| 啟用方式 | `docker compose --profile msf up -d` |
| 啟動指令 | `msfrpcd` 帶帳號密碼參數、SSL 啟用 |

#### MCP 工具伺服器（7 台）— profile: `mcp`

| 服務名稱 | 工具用途 | Port | 特殊設定 |
|----------|----------|------|----------|
| `mcp-nmap` | 網路掃描 | `127.0.0.1:58091` | `host.docker.internal` |
| `mcp-osint` | 開源情報偵察 | `127.0.0.1:58092` | — |
| `mcp-vuln` | 漏洞查詢（NVD） | `127.0.0.1:58093` | `NVD_API_KEY` |
| `mcp-credential-checker` | 憑證檢查 | `127.0.0.1:58094` | `host.docker.internal` |
| `mcp-attack-executor` | 攻擊執行 | `127.0.0.1:58095` | `SESSION_IDLE_TIMEOUT_SEC`、`host.docker.internal` |
| `mcp-web-scanner` | Web 漏洞掃描（Nuclei） | `127.0.0.1:58096` | `NUCLEI_TEMPLATES_DIR`、`SCAN_RATE_LIMIT`、`host.docker.internal` |
| `mcp-api-fuzzer` | API 模糊測試 | `127.0.0.1:58097` | `FUZZ_RATE_LIMIT`、`MAX_ENDPOINTS`、`host.docker.internal` |

- 所有 MCP 工具使用 Streamable HTTP 傳輸（`--transport streamable-http --port 8080`）
- 共用基礎映像 `athena-mcp-base:latest`（需先 `make build-mcp-base`）
- 啟用方式：`docker compose --profile mcp up -d`

### 2.4 Health Check 端點

**`GET /api/health`（Backend 存活探針）：**

```
HTTP 200
# 確認 FastAPI 進程存活與基本運作
```

- Docker Compose 中透過 `curl -sf http://localhost:8000/api/health` 檢查
- 間隔 30 秒、逾時 5 秒、重試 3 次、啟動等待 10 秒

**PostgreSQL（存活探針）：**

```
pg_isready -U athena
# 確認 PostgreSQL 可接受連線
```

- 間隔 10 秒、逾時 5 秒、重試 5 次、啟動等待 10 秒

**Frontend（Next.js）：**

- 使用 Next.js 內建的健康機制，無額外探針設定

### 2.5 Volumes

| Volume 名稱 | 用途 | 驅動程式 |
|-------------|------|----------|
| `pgdata` | PostgreSQL 資料持久化 | local |
| `backend-data` | 後端應用程式資料（`/app/data`） | local |
| `c2-engine-data` | Caldera 引擎資料 | local |

### 2.6 Resource Limits

> **現況**：本地 Docker Compose 未設定資源限制。待雲端環境建立後補充 K8s resource requests/limits。

---

## 3. 網路架構

### 3.1 Port 映射

| 外部 Port | 對應服務 | 綁定介面 | 說明 |
|-----------|----------|----------|------|
| `55432` | PostgreSQL | `127.0.0.1` | 僅本機——防止外部直接存取資料庫 |
| `58000` | Backend (FastAPI) | `0.0.0.0` | API + WebSocket |
| `58080` | Frontend (Next.js) | `0.0.0.0` | Web UI |
| `58888` | C2 引擎 (Caldera) | `0.0.0.0` | 需靶機回連，故綁 0.0.0.0 |
| `55553` | Metasploit RPC | `127.0.0.1` | 僅本機——安全考量 |
| `58091-58097` | MCP 工具伺服器 | `127.0.0.1` | 僅本機——後端透過 Docker 網路存取 |

> Port 統一使用 `5xxxx` 範圍，避免與常見服務衝突。

### 3.2 CORS 設定

- Backend 允許來源：`localhost:3000`、`localhost:58080`
- 所有服務共用 Docker Compose 預設 bridge 網路
- 服務間透過 Docker DNS 名稱互通（如 `postgres`、`backend`、`c2-engine`）

---

## 4. CI/CD Pipeline

> **現況**：CI/CD 尚未建立。以下為計畫架構。

### 4.1 Pipeline 架構（計畫）

```
PR 建立
│
├── [計畫] CI Pipeline
│   ├── Stage 1: Code Quality
│   │   ├── Lint（Ruff — 後端、ESLint — 前端）
│   │   ├── Type Check（mypy — 後端、TypeScript — 前端）
│   │   └── Security Scan（pip-audit、npm audit、Trivy）
│   │
│   ├── Stage 2: Testing
│   │   ├── Backend Unit Tests（pytest，370+ 測試）
│   │   ├── Frontend Unit Tests（Vitest，230 測試）
│   │   ├── E2E Tests（Playwright，8 specs）
│   │   └── Coverage Report
│   │
│   └── Stage 3: Build Verification
│       ├── Docker Build（backend + frontend）
│       └── Docker Image Scan（Trivy）
│
PR 合併至 main
│
└── [計畫] CD Pipeline
    ├── Build & Push Image
    ├── Deploy to Staging
    └── Smoke Tests
```

### 4.2 現行測試執行方式

| 測試類型 | 指令 | 測試數量 | 工具 |
|----------|------|----------|------|
| 後端單元測試 | `cd backend && pytest` | 370+ | pytest |
| 前端單元測試 | `cd frontend && npm test` | 230 | Vitest |
| E2E 測試 | `cd frontend && npx playwright test` | 8 specs | Playwright |
| 程式碼檢查 | `make lint` | — | ASP 整合 |
| 覆蓋率 | `make coverage` | — | ASP 整合 |

---

## 5. 部署操作手冊

### 5.1 首次部署（本地環境）

```bash
# 1. 複製環境變數
cp .env.example .env
# 編輯 .env，至少填入 ANTHROPIC_API_KEY

# 2. 建置並啟動核心服務
docker compose up -d
# 等同於 make deploy

# 3. 確認所有服務健康
docker compose ps
# postgres: healthy, backend: healthy, frontend: running

# 4.（選用）啟用 C2 引擎
docker compose --profile c2 up -d

# 5.（選用）啟用 Metasploit
docker compose --profile msf up -d

# 6.（選用）啟用 MCP 工具（需先建置基礎映像）
make build-mcp-base
docker compose --profile mcp up -d

# 7. 存取前端
open http://localhost:58080
```

### 5.2 常用 Makefile 指令

| 指令 | 效果 |
|------|------|
| `make build` | 建置 Docker 映像 |
| `make deploy` | `docker-compose up -d --force-recreate` + 顯示狀態 |
| `make clean` | 停止所有容器、移除映像與 volumes |
| `make logs` | 追蹤所有服務日誌（最近 100 行） |
| `make test` | 執行測試 |
| `make mock-mode` | 切換為 Mock 模式 |
| `make real-mode` | 切換為真實引擎模式 |

### 5.3 Profile 組合範例

```bash
# 核心服務（postgres + backend + frontend）
docker compose up -d

# 核心 + C2 + Metasploit
docker compose --profile c2 --profile msf up -d

# 完整環境（所有服務）
docker compose --profile c2 --profile msf --profile mcp up -d

# 僅重建後端
docker compose up -d --build backend
```

### 5.4 更新部署

```bash
# 拉取最新程式碼
git pull origin main

# 重新建置並部署
docker compose up -d --build

# 若僅更新後端
docker compose up -d --build backend

# 若僅更新前端
docker compose up -d --build frontend
```

---

## 6. 監控與告警

> **現況**：監控功能尚未實作，計畫於 v0.3.0 導入。

### 6.1 現有健康檢查

| 服務 | 檢查方式 | 間隔 | 失敗處理 |
|------|----------|------|----------|
| PostgreSQL | `pg_isready` | 10 秒 | Docker 自動重啟（`unless-stopped`） |
| Backend | `curl /api/health` | 30 秒 | Docker 自動重啟 |
| Frontend | Next.js 內建 | — | Docker 自動重啟 |

### 6.2 計畫中的監控項目（v0.3.0）

- **系統指標**：HTTP 請求數、回應時間分佈、CPU/記憶體使用率
- **業務指標**：OODA 迴圈執行次數、攻擊任務成功率、MCP 工具呼叫統計
- **資料庫指標**：連線池使用率、查詢延遲
- **告警規則**：HTTP 5xx 錯誤率 > 1%、P95 回應時間 > 500ms、容器重啟循環
- **儀表板**：Grafana 或同等工具

### 6.3 SLA 目標（計畫）

| 服務 | SLA 目標 | 說明 |
|------|----------|------|
| API 可用性 | 99.9% | 本地環境不適用，待雲端環境建立 |
| API P95 回應時間 | < 200ms | 不含 LLM 推理時間 |

---

## 7. 災難復原（Disaster Recovery）

### 7.1 Backup 策略

> **現況**：PostgreSQL WAL + 每日快照為計畫項目，尚未自動化。

| 資料來源 | 備份方式 | 頻率 | 狀態 |
|----------|----------|------|------|
| PostgreSQL（Docker Volume） | 手動 `pg_dump` | 按需 | **現行** |
| PostgreSQL WAL Archiving | 連續備份 + 時間點恢復 | 連續 | **計畫中** |
| PostgreSQL 快照 | 自動化每日快照 | 每日 | **計畫中** |
| `backend-data` Volume | 手動備份 | 按需 | **現行** |

**手動備份指令（現行）：**

```bash
# 匯出 PostgreSQL 資料
docker compose exec postgres pg_dump -U athena athena > backup_$(date +%Y%m%d).sql

# 還原
docker compose exec -T postgres psql -U athena athena < backup_20260325.sql
```

### 7.2 RTO / RPO 目標

| 情境 | RTO | RPO | 說明 |
|------|-----|-----|------|
| 單一容器故障 | < 1 分鐘 | 0 | Docker `unless-stopped` 自動重啟 |
| Docker Compose 全環境重建 | < 10 分鐘 | 取決於最近備份 | `docker compose up -d` |
| 資料庫損壞 | < 30 分鐘 | 取決於最近 `pg_dump` | 手動從備份還原 |

### 7.3 Rollback 程序

#### 應用程式版本回滾

```bash
# 1. 確認當前 Git 版本
git log --oneline -5

# 2. 回到上一個穩定版本
git checkout <stable-commit-hash>

# 3. 重新建置並部署
docker compose up -d --build

# 4. 確認服務健康
docker compose ps
```

#### 資料庫 Migration 回滾

```bash
# 查看 Alembic migration 歷史
cd backend && alembic history

# 回滾至指定版本
alembic downgrade <revision>

# 重啟後端以套用
docker compose restart backend
```

---

## 附錄

### A. 部署前檢查清單

**每次部署前確認：**

- [ ] `.env` 已正確設定所有必要變數
- [ ] `ANTHROPIC_API_KEY` 已填入（若非 Mock 模式）
- [ ] 後端測試通過：`cd backend && pytest`
- [ ] 前端測試通過：`cd frontend && npm test`
- [ ] Docker 映像建置成功：`docker compose build`
- [ ] PostgreSQL 資料已備份（如適用）
- [ ] 所有容器健康：`docker compose ps`

### B. Secret 管理

| Secret | 儲存方式 | 說明 |
|--------|----------|------|
| `ANTHROPIC_API_KEY` | `.env` 檔 | LLM API 金鑰 |
| `OPENAI_API_KEY` | `.env` 檔 | 備選 LLM API 金鑰 |
| `POSTGRES_PASSWORD` | `.env` 檔 | 資料庫密碼 |
| `CALDERA_API_KEY` | `.env` 檔 | C2 引擎 API 金鑰 |
| `C2_ENGINE_API_KEY` | `.env` 檔 | C2 引擎 API 金鑰（Docker 內部） |
| `MSF_RPC_PASSWORD` | `.env` 檔 | Metasploit RPC 密碼 |
| `NVD_API_KEY` | `.env` 檔 | NVD 漏洞資料庫 API 金鑰 |
| Claude 憑證 | `~/.claude/.credentials.json`（唯讀掛載） | Claude Code 認證 |

> **注意**：目前所有 Secret 存於 `.env` 檔。待雲端環境建立後應遷移至 Secret Manager（如 AWS Secrets Manager、HashiCorp Vault）。

### C. 容量規劃

> **現況**：本地開發環境，尚無容量數據。待監控導入後（v0.3.0）開始收集基線數據。

| 指標 | 當前值 | 說明 |
|------|--------|------|
| 後端映像大小 | ~500MB | python:3.12-slim + nmap + 依賴 |
| 前端映像大小 | ~200MB | node:20-alpine + standalone build |
| PostgreSQL 資料量 | < 100MB | 開發階段 |
| `backend-data` Volume | < 50MB | 應用程式資料 |

### D. 變更歷史

| 版本 | 日期 | 變更摘要 | 作者 |
|------|------|----------|------|
| v0.1.0 | 2026-03-25 | 初版建立——記錄本地 Docker Compose 部署規格 | Athena 開發團隊 |

### E. 相關文件

- [`docker-compose.yml`](../docker-compose.yml) — Docker Compose 編排定義
- [`backend/Dockerfile`](../backend/Dockerfile) — 後端映像建置
- [`frontend/Dockerfile`](../frontend/Dockerfile) — 前端映像建置
- [`.env`](../.env) — 環境變數範本
- [`Makefile`](../Makefile) — 建置與部署指令
- [`docs/adr/`](./adr/) — 架構決策記錄
