# 安裝與設定指南

> **Athena** C5ISR 網路作戰指揮平台 — 從零開始安裝
>
> **版本**：v0.4.0-poc
> **更新日期**：2026-02-26

---

## 目錄

1. [前提條件](#前提條件)
2. [Docker 快速啟動（推薦）](#docker-快速啟動推薦)
3. [本機開發模式](#本機開發模式)
4. [驗證安裝](#驗證安裝)
5. [環境變數說明](#環境變數說明)
6. [Mock 模式說明](#mock-模式說明)
7. [常見問題](#常見問題)
8. [Makefile 指令速查](#makefile-指令速查)
9. [下一步](#下一步)

---

## 前提條件

### 必要軟體

| 軟體 | 最低版本 | 安裝指引 |
|------|----------|----------|
| Docker | 20.10+ | https://docs.docker.com/get-docker/ |
| Docker Compose | v2 (內建於 Docker Desktop) | https://docs.docker.com/compose/install/ |
| Git | 2.30+ | https://git-scm.com/downloads |

確認版本：

```bash
docker --version        # Docker version 20.10.x 或更新
docker compose version  # Docker Compose version v2.x.x
git --version           # git version 2.x.x
```

### 可選軟體（本機開發用）

| 軟體 | 最低版本 | 用途 |
|------|----------|------|
| Python | 3.11+ | 後端本機開發 |
| Node.js | 20+ | 前端本機開發 |

> **注意**：若只使用 Docker 模式，不需要安裝 Python 或 Node.js。

### 系統資源需求

```
CPU：至少 4 核心
RAM：至少 4 GB（建議 8 GB）
磁碟：至少 10 GB 可用空間
網路：穩定連線（若 MOCK_LLM=false 則需連接 LLM API）
```

---

## Docker 快速啟動（推薦）

這是最簡單的啟動方式，適合快速體驗與 Demo 展示。

### 步驟 1：取得程式碼

```bash
git clone https://github.com/astroicers/Athena
cd Athena
```

### 步驟 2：設定環境變數

```bash
cp .env.example .env
```

> **POC 預設值**：`.env.example` 已預設 `MOCK_LLM=true` 和 `MOCK_CALDERA=true`，
> 無需 API 金鑰即可立即啟動並體驗完整功能。

若需要真實 LLM 分析，編輯 `.env`：

```bash
# 加入你的 Claude API 金鑰
ANTHROPIC_API_KEY=sk-ant-...
MOCK_LLM=false
```

### 步驟 3：啟動服務

```bash
make up
```

此指令會在背景啟動 backend 和 frontend 容器。

### 步驟 4：等待後端健康檢查通過

```bash
# 觀察日誌直到看到 "Application startup complete"
make logs
```

或直接輪詢健康端點：

```bash
# 等待 backend 就緒（通常約 15-30 秒）
until curl -sf http://localhost:8000/api/health > /dev/null; do
  echo "Waiting for backend..."
  sleep 3
done
echo "Backend is ready!"
```

### 步驟 5：開啟瀏覽器

```
http://localhost:3000
```

你應該看到 Athena C5ISR Board — 指揮官主儀表板。

---

## 本機開發模式

適合需要修改程式碼並即時熱載入的開發工作流程。

### 後端（FastAPI）

```bash
cd backend
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
```

或使用 Makefile 捷徑：

```bash
make dev-backend
```

後端啟動後可存取：
- API 服務：http://localhost:8000
- Swagger UI：http://localhost:8000/docs
- ReDoc：http://localhost:8000/redoc

### 前端（Next.js）

```bash
cd frontend
npm install
npm run dev
```

或使用 Makefile 捷徑：

```bash
make dev-frontend
```

前端啟動後可存取：
- 主介面：http://localhost:3000

### 同時啟動前後端

```bash
make dev
```

> **注意**：本機開發模式下，前後端分開執行，
> 前端預設透過 `http://localhost:8000` 連接後端 API。
> 若後端 port 不同，請調整 `.env` 中的 `NEXT_PUBLIC_API_URL`。

---

## 驗證安裝

安裝完成後，執行以下指令確認各服務正常運作。

### 1. 後端健康檢查

```bash
curl http://localhost:8000/api/health
```

預期回應：

```json
{
  "status": "healthy",
  "version": "0.4.0-poc",
  "mock_llm": true,
  "mock_caldera": true
}
```

### 2. 確認種子資料載入

```bash
curl http://localhost:8000/api/operations
```

預期回應：回傳包含種子作戰資料的 JSON 陣列，
應包含「奪取 Domain Admin」示範作戰。

### 3. 瀏覽器介面確認

開啟 http://localhost:3000，確認以下畫面可正常載入：

- **C5ISR Board**：指揮官主儀表板（首頁）
- **MITRE Navigator**：ATT&CK 技術矩陣
- **Mission Planner**：任務規劃介面
- **Battle Monitor**：即時作戰監控（含 3D 拓樸）

### 4. API 文件

開啟 http://localhost:8000/docs 確認 Swagger UI 正常顯示所有 API 端點。

---

## 環境變數說明

所有設定均透過 `.env` 檔管理。以下為完整變數說明：

### 核心設定

| 變數 | 說明 | 預設值 |
|------|------|--------|
| `MOCK_LLM` | 使用模擬 LLM（無需 API key） | `true` |
| `MOCK_CALDERA` | 使用模擬 Caldera | `true` |

### LLM API 金鑰

| 變數 | 說明 | 預設值 |
|------|------|--------|
| `ANTHROPIC_API_KEY` | Claude API key（`MOCK_LLM=false` 時需要） | （空） |
| `OPENAI_API_KEY` | GPT-4 API key（備用 LLM） | （空） |

### 執行引擎

| 變數 | 說明 | 預設值 |
|------|------|--------|
| `CALDERA_URL` | Caldera API URL | `http://localhost:8888` |
| `CALDERA_API_KEY` | Caldera 身份驗證 key | （空） |
| `SHANNON_URL` | Shannon API URL（選用） | （空） |

### 資料庫

| 變數 | 說明 | 預設值 |
|------|------|--------|
| `DATABASE_URL` | SQLite 資料庫路徑 | `sqlite:///backend/data/athena.db` |

### 自動化模式

| 變數 | 說明 | 預設值 |
|------|------|--------|
| `AUTOMATION_MODE` | 自動化模式（`manual` / `semi_auto`） | `semi_auto` |
| `RISK_THRESHOLD` | 風險閾值（`low` / `medium` / `high`） | `medium` |

### 前端連線

| 變數 | 說明 | 預設值 |
|------|------|--------|
| `NEXT_PUBLIC_API_URL` | 前端呼叫後端 API 的 URL | `http://localhost:8000/api` |
| `NEXT_PUBLIC_WS_URL` | WebSocket URL（即時更新） | `ws://localhost:8000/ws` |

### 日誌

| 變數 | 說明 | 預設值 |
|------|------|--------|
| `LOG_LEVEL` | 日誌等級（`DEBUG` / `INFO` / `WARNING`） | `INFO` |

---

## Mock 模式說明

Athena 提供兩個獨立的 Mock 開關，讓你無需外部服務即可體驗完整功能。

### MOCK_LLM=true（預設啟用）

**作用**：Orient 階段使用預錄的回應，不呼叫 Claude 或 GPT-4 API。

```
使用者輸入戰略意圖
       ↓
PentestGPT（Mock）— 回傳預錄的戰術建議
       ↓
指揮官看到 AI 分析結果（與真實 LLM 格式相同）
```

**優點**：
- 不需要 API 金鑰
- 零 API 費用
- 回應速度快（無網路延遲）
- 適合 Demo 和開發測試

**切換至真實 LLM**：
```bash
MOCK_LLM=false
ANTHROPIC_API_KEY=sk-ant-...
```

### MOCK_CALDERA=true（預設啟用）

**作用**：Act 階段使用模擬執行結果，不需要真實 Caldera 實例。

```
Athena 決策引擎下達執行指令
       ↓
Caldera Client（Mock）— 回傳模擬攻擊結果
       ↓
Battle Monitor 顯示執行狀態（與真實執行格式相同）
```

**優點**：
- 不需要安裝和設定 Caldera
- 不需要測試環境和 Agent
- 適合展示指揮平台概念

**切換至真實 Caldera**：
```bash
MOCK_CALDERA=false
CALDERA_URL=http://your-caldera-host:8888
CALDERA_API_KEY=your-api-key
```

### 混合使用

兩個開關完全獨立，可依需求混合：

```bash
# 真實 LLM 分析 + 模擬執行（最常見的開發模式）
MOCK_LLM=false
MOCK_CALDERA=true
ANTHROPIC_API_KEY=sk-ant-...

# 完整真實模式（需要 Caldera 環境）
MOCK_LLM=false
MOCK_CALDERA=false
```

---

## 常見問題

### Port 8000 或 3000 已被佔用

**症狀**：`Error: listen EADDRINUSE: address already in use :::8000`

**解法**：找出並終止佔用程序

```bash
# 找出佔用 port 8000 的程序
lsof -i :8000

# 或使用 fuser
fuser 8000/tcp

# 終止程序（替換 PID）
kill -9 <PID>
```

或修改 `.env` 和 `docker-compose.yml` 使用其他 port。

### Docker 記憶體不足

**症狀**：容器啟動後立即退出，日誌顯示 OOM（Out of Memory）

**解法**：調整 Docker Desktop 記憶體設定

1. 開啟 Docker Desktop
2. 前往 Settings → Resources
3. 將 Memory 調整至至少 **4 GB**（建議 8 GB）
4. 點擊 Apply & Restart

### 前端 SSR 錯誤（window is not defined）

**症狀**：Next.js 建置或啟動時出現 `ReferenceError: window is not defined`

**原因**：3D 拓樸元件（react-force-graph-3d / Three.js）使用了瀏覽器 API，
不能在 SSR 環境中直接執行。

**解法**：確認 3D 元件檔案頂部有 `"use client"` 指令

```tsx
"use client";  // 必須在檔案第一行

import dynamic from "next/dynamic";
const ForceGraph3D = dynamic(() => import("react-force-graph-3d"), {
  ssr: false,
});
```

### SQLite 資料庫鎖定

**症狀**：API 回傳 `database is locked` 錯誤

**原因**：多個 backend 實例同時存取同一個 SQLite 檔案。

**解法**：確認只有一個 backend 在運行

```bash
# 查看所有 backend 相關程序
ps aux | grep uvicorn

# 若使用 Docker，確認只有一個 backend 容器
docker ps | grep athena-backend

# 重啟 backend 以解除鎖定
make down && make up
```

---

## Makefile 指令速查

| 指令 | 說明 |
|------|------|
| `make up` | 以 Docker 啟動所有服務（背景執行） |
| `make down` | 停止並移除所有 Docker 容器 |
| `make logs` | 查看即時日誌（所有服務） |
| `make dev` | 開發模式啟動（前景，含熱載入） |
| `make dev-backend` | 僅啟動後端開發伺服器 |
| `make dev-frontend` | 僅啟動前端開發伺服器 |
| `make seed` | 載入 Demo 種子資料到資料庫 |
| `make clean` | 清除建置產物（`__pycache__`、`.next` 等） |
| `make docker-clean` | 清除 Docker image 和 volume（完整重置） |

完整指令說明：

```bash
# 查看所有可用指令
make help
```

---

## 下一步

安裝完成後，建議依序閱讀：

1. **[Demo 演練](DEMO_WALKTHROUGH.md)** — 跟著「奪取 Domain Admin」場景，
   體驗完整 OODA 循環：從戰略意圖輸入到 PentestGPT 分析到 Caldera 執行。

2. **[資料架構](architecture/data-architecture.md)** — 了解 13 個核心 Enum、
   12 個 Model、SQLite Schema 和 REST API 設計。

3. **[專案結構](architecture/project-structure.md)** — 了解 Monorepo 目錄佈局
   和各層職責分工。

4. **[開發路線圖](ROADMAP.md)** — 了解 Phase 0-8 完整計畫和 POC 成功標準。

---

> **提示**：初次體驗建議保持預設 Mock 模式（`MOCK_LLM=true`、`MOCK_CALDERA=true`），
> 先熟悉 C5ISR 指揮平台的操作流程，再連接真實的 LLM 和 Caldera 服務。

---

*Athena GETTING_STARTED.md v1.0*
*隸屬於 Phase 7.1 文件計畫*
