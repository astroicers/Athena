# SPEC-001：專案骨架與設定檔

> 建立 Athena Monorepo 目錄結構、根設定檔與設計資產搬移。

| 欄位 | 內容 |
|------|------|
| **規格 ID** | SPEC-001 |
| **關聯 ADR** | ADR-001（技術棧選擇）、ADR-002（Monorepo 結構）、ADR-010（Docker Compose 部署拓樸） |
| **估算複雜度** | 低 |
| **建議模型** | Haiku |
| **HITL 等級** | minimal |

---

## 🎯 目標（Goal）

> 建立 Athena 的完整 Monorepo 目錄骨架、根設定檔（docker-compose.yml、pyproject.toml、package.json 等），並將 `.pen` 設計資產搬入 `design/` 目錄，為 Phase 2-6 提供可直接開發的專案結構。

---

## 📥 輸入規格（Inputs）

| 參數名稱 | 型別 | 來源 | 限制條件 |
|----------|------|------|----------|
| 目錄佈局 | 文件 | `docs/architecture/project-structure.md` Section「完整目錄樹」 | 嚴格遵循已定義的路徑 |
| Docker Compose 拓樸 | 文件 | ADR-010 決策 | 內部服務 backend+frontend，外部引擎 Caldera/Shannon |
| 環境變數 | 文件 | `.env.example`（已存在） | 不修改現有 `.env.example` |
| .pen 設計檔 | 檔案 | `design/athena-*.pen`（6 個） | 已搬入 `design/` |

---

## 📤 輸出規格（Expected Output）

**成功情境：**

### 1. 目錄結構

```
Athena/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── models/
│   │   │   └── __init__.py
│   │   ├── routers/
│   │   │   └── __init__.py
│   │   ├── services/
│   │   │   └── __init__.py
│   │   ├── clients/
│   │   │   └── __init__.py
│   │   └── seed/
│   │       └── __init__.py
│   ├── data/
│   │   └── .gitkeep
│   ├── tests/
│   │   ├── __init__.py
│   │   └── conftest.py
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   ├── components/
│   │   ├── types/
│   │   ├── hooks/
│   │   ├── lib/
│   │   └── styles/
│   ├── package.json
│   ├── next.config.js
│   ├── tailwind.config.ts
│   └── tsconfig.json
├── design/
│   ├── athena-design-system.pen
│   ├── athena-shell.pen
│   ├── athena-c5isr-board.pen
│   ├── athena-mitre-navigator.pen
│   ├── athena-mission-planner.pen
│   └── athena-battle-monitor.pen
├── infra/
│   ├── caldera/
│   │   └── local.yml
│   └── shannon/
│       └── .gitkeep
├── docker-compose.yml
└── (existing: CLAUDE.md, .env.example, .gitignore, Makefile, docs/)
```

### 2. docker-compose.yml

```yaml
version: "3.8"

services:
  backend:
    build: ./backend
    ports:
      - "127.0.0.1:8000:8000"
    volumes:
      - ./backend/data:/app/data
    env_file:
      - .env
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  frontend:
    build: ./frontend
    ports:
      - "127.0.0.1:3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://backend:8000/api
      - NEXT_PUBLIC_WS_URL=ws://backend:8000/ws
    depends_on:
      - backend
```

注意：`127.0.0.1` 綁定遵循 ADR-011（POC 不暴露至公開網路）。

### 3. backend/pyproject.toml

```toml
[project]
name = "athena-backend"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.109.0",
    "uvicorn[standard]>=0.27.0",
    "pydantic>=2.5.0",
    "pydantic-settings>=2.1.0",
    "aiosqlite>=0.19.0",
    "httpx>=0.26.0",
    "websockets>=12.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-asyncio>=0.23.0",
    "httpx>=0.26.0",
]
```

### 4. frontend/package.json

```json
{
  "name": "athena-frontend",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "next dev --port 3000",
    "build": "next build",
    "start": "next start",
    "lint": "next lint"
  },
  "dependencies": {
    "next": "^14.1.0",
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-force-graph-3d": "^1.21.0",
    "three": "^0.161.0"
  },
  "devDependencies": {
    "@types/node": "^20.11.0",
    "@types/react": "^18.2.0",
    "@types/three": "^0.161.0",
    "typescript": "^5.3.0",
    "tailwindcss": "^4.0.0",
    "@tailwindcss/postcss": "^4.0.0",
    "postcss": "^8.4.0"
  }
}
```

### 5. 其他設定檔

- `frontend/next.config.js` — 基本配置 + transpilePackages for three.js
- `frontend/tsconfig.json` — strict mode + path aliases (`@/` → `src/`)
- `frontend/tailwind.config.ts` — 空 Athena 主題 token 佔位
- `frontend/src/styles/globals.css` — Tailwind 指令 + CSS 變數佔位
- `backend/tests/conftest.py` — pytest fixtures 佔位
- `infra/caldera/local.yml` — Caldera 本地開發配置佔位

**失敗情境：**

| 錯誤類型 | 處理方式 |
|----------|----------|
| .pen 檔案不存在 | 跳過搬移，輸出警告 |
| 目錄已存在 | 跳過建立（冪等操作） |

---

## ⚠️ 邊界條件（Edge Cases）

- `.pen` 檔案可能已在 `design/` 中（冪等處理：已存在則跳過）
- `backend/data/` 目錄中 `.db` 檔被 `.gitignore` 排除，僅保留 `.gitkeep`
- `__init__.py` 檔案內容為空，僅用於 Python 模組識別
- `docker-compose.yml` 中 backend port 使用 `127.0.0.1:8000:8000` 限制本機存取

---

## ✅ 驗收標準（Done When）

- [x] `ls backend/app/models backend/app/routers backend/app/services backend/app/clients backend/app/seed` — 全部存在
- [x] `ls frontend/src/app frontend/src/components frontend/src/types frontend/src/hooks frontend/src/lib` — 全部存在
- [x] `ls design/athena-*.pen | wc -l` — 6 個檔案
- [x] `docker-compose config` — 無錯誤
- [x] `cat backend/pyproject.toml | grep fastapi` — 確認依賴列表
- [x] `cat frontend/package.json | grep next` — 確認依賴列表
- [x] `python -c "import backend"` 不報錯（`__init__.py` 正確）— ⚠️ 模組入口為 `from app.main import app`，非頂層 `backend` package（設計決策，視為通過）
- [x] `ls infra/caldera/local.yml infra/shannon/.gitkeep` — 全部存在

---

## 🚫 禁止事項（Out of Scope）

- 不要安裝依賴（`pip install` / `npm install`）—— 僅建立設定檔
- 不要實作任何業務邏輯（models、routers、services 的 `__init__.py` 為空）
- 不要修改現有的 `.env.example`、`.gitignore`、`Makefile`、`CLAUDE.md`
- 不要建立 `backend/Dockerfile` 或 `frontend/Dockerfile`（Phase 6 / SPEC-010 範圍）
- 不要引入 Tailwind v3 語法——必須使用 Tailwind v4

---

## 📎 參考資料（References）

- ADR-002：[Monorepo 專案結構](../adr/ADR-002-monorepo-project-structure.md)
- ADR-010：[Docker Compose 部署拓樸](../adr/ADR-010-docker-compose-deployment.md)
- ADR-011：[POC 不實作身份驗證](../adr/ADR-011-no-auth-for-poc.md)（127.0.0.1 綁定）
- 專案結構：[project-structure.md](../architecture/project-structure.md)

<!-- tech-debt: scenario-pending — v3.2 upgrade: needs test matrix + Gherkin scenarios -->
<!-- tech-debt: observability-pending — v3.3 upgrade: needs observability section -->
