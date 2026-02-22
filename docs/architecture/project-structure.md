# Athena — 專案目錄結構

> 版本：v0.1.0 | 更新日期：2026-02-22
> 參照：[data-architecture.md](./data-architecture.md)

---

## 概述

Athena 採用 **Monorepo** 結構，前後端分離但共存於同一 Git 倉庫。
設計資產（.pen 檔）獨立存放於 `design/` 目錄，與程式碼分離。

**技術棧**：
- 後端：Python 3.11 + FastAPI + SQLite + Pydantic
- 前端：Next.js 14 (App Router) + React 18 + Tailwind CSS v4
- 容器化：Docker + docker-compose
- 設計：Pencil.dev (.pen)

---

## 完整目錄樹

```
Athena/
├── CLAUDE.md                              # AI 上下文文件（保留根目錄）
├── README.md                              # 專案說明
├── .gitignore                             # 版控排除規則
├── .env.example                           # 環境變數範本
├── docker-compose.yml                     # 容器編排（backend + frontend）
├── Makefile                               # 開發指令集
│
├── docs/                                  # 專案文件
│   └── architecture/
│       ├── data-architecture.md           # 資料架構設計
│       └── project-structure.md           # 本文件
│
├── design/                                # 設計資產
│   ├── athena-design-system.pen           # 設計系統（56 組件 + 32 變數）
│   ├── athena-shell.pen                   # App Shell（共用框架）
│   ├── athena-c5isr-board.pen             # C5ISR 指揮看板
│   ├── athena-battle-monitor.pen          # 戰場監控畫面
│   ├── athena-mitre-navigator.pen         # MITRE ATT&CK 導航
│   └── athena-mission-planner.pen         # 任務規劃畫面
│
├── backend/                               # Python FastAPI 後端
│   ├── Dockerfile
│   ├── pyproject.toml                     # 依賴管理 + 專案配置
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                        # FastAPI 入口點
│   │   ├── config.py                      # 環境變數配置
│   │   ├── database.py                    # SQLite 連線管理
│   │   │
│   │   ├── models/                        # 資料模型層
│   │   │   ├── __init__.py                # 匯出所有 models
│   │   │   ├── enums.py                   # 共用列舉定義（13 個）
│   │   │   ├── operation.py               # 作戰行動
│   │   │   ├── target.py                  # 目標主機
│   │   │   ├── agent.py                   # Caldera Agent
│   │   │   ├── technique.py               # MITRE ATT&CK 技術
│   │   │   ├── technique_execution.py     # 技術執行紀錄
│   │   │   ├── fact.py                    # 情報資料
│   │   │   ├── ooda.py                    # OODA 循環迭代
│   │   │   ├── recommendation.py          # PentestGPT 戰術建議
│   │   │   ├── mission.py                 # 任務步驟
│   │   │   ├── c5isr.py                   # C5ISR 六域狀態
│   │   │   ├── log_entry.py               # 系統日誌
│   │   │   └── user.py                    # 操作員
│   │   │
│   │   ├── routers/                       # API 路由層
│   │   │   ├── __init__.py
│   │   │   ├── operations.py              # /api/operations
│   │   │   ├── ooda.py                    # /api/operations/{id}/ooda
│   │   │   ├── techniques.py              # /api/techniques
│   │   │   ├── missions.py                # /api/operations/{id}/mission
│   │   │   ├── targets.py                 # /api/operations/{id}/targets
│   │   │   ├── agents.py                  # /api/operations/{id}/agents
│   │   │   ├── c5isr.py                   # /api/operations/{id}/c5isr
│   │   │   ├── logs.py                    # /api/operations/{id}/logs
│   │   │   └── ws.py                      # WebSocket /ws/{operation_id}
│   │   │
│   │   ├── services/                      # 業務邏輯層
│   │   │   ├── __init__.py
│   │   │   ├── ooda_controller.py         # OODA 循環狀態機
│   │   │   ├── orient_engine.py           # PentestGPT 整合
│   │   │   ├── decision_engine.py         # 技術選擇邏輯
│   │   │   ├── engine_router.py           # Caldera/Shannon 路由
│   │   │   ├── c5isr_mapper.py            # C5ISR 狀態聚合
│   │   │   └── fact_collector.py          # 情報收集標準化
│   │   │
│   │   ├── clients/                       # 外部 API 客戶端
│   │   │   ├── __init__.py
│   │   │   ├── caldera_client.py          # MITRE Caldera REST API
│   │   │   └── shannon_client.py          # Shannon AI 引擎 API
│   │   │
│   │   └── seed/                          # 示範資料
│   │       ├── __init__.py
│   │       └── demo_scenario.py           # OP-2024-017 "Obtain Domain Admin"
│   │
│   ├── data/                              # SQLite 資料庫檔案
│   │   └── .gitkeep                       # 保留空目錄（.db 由 .gitignore 排除）
│   │
│   └── tests/                             # 後端測試
│       ├── __init__.py
│       ├── test_ooda.py                   # OODA 循環測試
│       ├── test_operations.py             # 作戰 API 測試
│       └── conftest.py                    # pytest fixtures
│
├── frontend/                              # Next.js React 前端
│   ├── Dockerfile
│   ├── package.json
│   ├── next.config.js
│   ├── tailwind.config.ts                 # Athena 主題 token 配置
│   ├── tsconfig.json
│   │
│   └── src/
│       ├── app/                           # Next.js App Router 頁面
│       │   ├── layout.tsx                 # Root Layout（Shell + Sidebar）
│       │   ├── page.tsx                   # 首頁 → redirect /c5isr
│       │   ├── c5isr/
│       │   │   └── page.tsx               # C5ISR 指揮看板
│       │   ├── navigator/
│       │   │   └── page.tsx               # MITRE ATT&CK 導航
│       │   ├── planner/
│       │   │   └── page.tsx               # 任務規劃器
│       │   └── monitor/
│       │       └── page.tsx               # 戰場監控
│       │
│       ├── components/                    # UI 組件（對應設計系統）
│       │   ├── layout/                    # 佈局組件
│       │   │   ├── Sidebar.tsx            # 側邊導航欄
│       │   │   ├── PageHeader.tsx         # 頁面標題列
│       │   │   ├── AlertBanner.tsx        # 全域警報橫幅
│       │   │   └── CommandInput.tsx       # 底部指令輸入
│       │   │
│       │   ├── atoms/                     # 原子組件
│       │   │   ├── Button.tsx
│       │   │   ├── Badge.tsx              # 狀態標籤
│       │   │   ├── StatusDot.tsx          # 狀態指示燈
│       │   │   ├── Toggle.tsx             # 開關切換
│       │   │   ├── ProgressBar.tsx
│       │   │   └── HexIcon.tsx            # 六角形圖示
│       │   │
│       │   ├── cards/                     # 卡片組件
│       │   │   ├── MetricCard.tsx         # KPI 數據卡
│       │   │   ├── HostNodeCard.tsx       # 主機節點卡
│       │   │   ├── TechniqueCard.tsx      # 技術詳情卡
│       │   │   └── RecommendCard.tsx      # PentestGPT 建議卡
│       │   │
│       │   ├── data/                      # 資料展示組件
│       │   │   ├── DataTable.tsx          # 通用資料表格
│       │   │   ├── LogEntry.tsx           # 日誌條目
│       │   │   ├── AgentBeacon.tsx        # Agent 心跳指示
│       │   │   └── TrafficStream.tsx      # 流量串流視覺化
│       │   │
│       │   ├── mitre/                     # MITRE 相關組件
│       │   │   ├── MITRECell.tsx          # ATT&CK 矩陣格
│       │   │   └── KillChainIndicator.tsx # Kill Chain 進度
│       │   │
│       │   ├── ooda/                      # OODA 循環組件
│       │   │   ├── OODAIndicator.tsx      # 四階段指示器
│       │   │   └── OODATimelineEntry.tsx  # 時間軸條目
│       │   │
│       │   ├── c5isr/                     # C5ISR 組件
│       │   │   ├── C5ISRStatusBoard.tsx   # 六域狀態面板
│       │   │   └── DomainCard.tsx         # 單域狀態卡
│       │   │
│       │   ├── topology/                  # 拓樸圖組件
│       │   │   ├── AttackNode.tsx         # 攻擊路徑節點
│       │   │   ├── AttackVectorLine.tsx   # 攻擊向量連線
│       │   │   ├── NetworkTopology.tsx    # 網路拓樸全圖
│       │   │   └── ThreatLevelGauge.tsx   # 威脅等級儀表
│       │   │
│       │   ├── modal/                     # 對話框組件
│       │   │   └── HexConfirmModal.tsx    # 六角形確認對話框
│       │   │
│       │   └── nav/                       # 導航組件
│       │       ├── NavItem.tsx            # 側邊欄項目
│       │       └── TabBar.tsx             # 頁簽列
│       │
│       ├── types/                         # TypeScript 型別定義
│       │   ├── index.ts                   # 統一匯出
│       │   ├── enums.ts                   # 對應後端 13 個列舉
│       │   ├── operation.ts
│       │   ├── target.ts
│       │   ├── agent.ts
│       │   ├── technique.ts
│       │   ├── fact.ts
│       │   ├── ooda.ts
│       │   ├── recommendation.ts
│       │   ├── mission.ts
│       │   ├── c5isr.ts
│       │   ├── log.ts
│       │   └── api.ts                     # API 回應包裝型別
│       │
│       ├── hooks/                         # React Hooks
│       │   ├── useOperation.ts            # 作戰資料管理
│       │   ├── useWebSocket.ts            # WebSocket 連線
│       │   ├── useOODA.ts                 # OODA 狀態訂閱
│       │   └── useLiveLog.ts              # 即時日誌串流
│       │
│       ├── lib/                           # 工具函式
│       │   ├── api.ts                     # Fetch 封裝（base URL + error handling）
│       │   └── constants.ts               # 靜態常數
│       │
│       └── styles/
│           └── globals.css                # 全域樣式 + Tailwind 指令
│
└── infra/                                 # 基礎設施配置
    ├── caldera/
    │   └── local.yml                      # Caldera 本地開發配置
    └── shannon/
        └── .gitkeep                       # Shannon 配置預留
```

---

## 各層職責說明

### 1. `design/` — 設計資產層

存放所有 Pencil.dev 設計檔案，與程式碼完全分離。

| 檔案 | 內容 | 對應畫面 |
|------|------|---------|
| `athena-design-system.pen` | 56 個可重用組件 + 32 個設計變數 | 全域設計語言 |
| `athena-shell.pen` | App Shell（Sidebar + AlertBanner + ContentSlot） | 共用框架 |
| `athena-c5isr-board.pen` | C5ISR 指揮看板 | `/c5isr` |
| `athena-battle-monitor.pen` | 戰場監控 | `/monitor` |
| `athena-mitre-navigator.pen` | MITRE ATT&CK 導航 | `/navigator` |
| `athena-mission-planner.pen` | 任務規劃 | `/planner` |

> 設計檔目前位於根目錄，待實作時搬入 `design/`。

### 2. `backend/` — 後端服務層

採用 FastAPI 標準分層架構：

```
請求流程：
Client → Router → Service → Client(外部) / DB
                     ↓
              Models (Pydantic)
```

| 子目錄 | 職責 | 備註 |
|--------|------|------|
| `models/` | Pydantic 資料模型 + Enum 定義 | 12 個實體 + 13 個列舉 |
| `routers/` | HTTP 路由 + 請求驗證 | RESTful + WebSocket |
| `services/` | 業務邏輯（OODA 編排、AI 整合） | 核心領域邏輯 |
| `clients/` | 外部 API 封裝（Caldera、Shannon） | HTTP 客戶端 |
| `seed/` | 示範情境資料 | OP-2024-017 完整場景 |
| `data/` | SQLite 資料庫檔案 | .gitignore 排除 .db |
| `tests/` | pytest 單元/整合測試 | 以 OODA 循環為重點 |

#### 關鍵檔案說明

**`main.py`** — FastAPI 應用入口
- CORS 中介軟體配置（允許前端 localhost:3000）
- Lifespan 事件（啟動時初始化 DB + 載入種子資料）
- 掛載所有 Router

**`config.py`** — Pydantic BaseSettings
- 從 `.env` 讀取配置
- `DATABASE_URL`、`CALDERA_URL`、`SHANNON_URL`
- `AUTOMATION_MODE`、`RISK_THRESHOLD` 預設值

**`database.py`** — SQLite 連線管理
- SQLite 連線池（aiosqlite）
- Schema 初始化（CREATE TABLE IF NOT EXISTS）
- Session 管理

#### Services 核心邏輯

| Service | 對應 OODA 階段 | 功能 |
|---------|---------------|------|
| `ooda_controller.py` | 全階段 | OODA 循環狀態機，驅動 Observe→Orient→Decide→Act |
| `orient_engine.py` | Orient | 呼叫 PentestGPT API，生成戰術分析與建議 |
| `decision_engine.py` | Decide | 根據 AI 建議 + 風險等級 + 自動化模式選擇技術 |
| `engine_router.py` | Act | 根據技術類型路由到 Caldera 或 Shannon 執行 |
| `c5isr_mapper.py` | — | 從各數據源聚合 C5ISR 六域健康狀態 |
| `fact_collector.py` | Observe | 標準化各引擎回傳的情報格式 |

### 3. `frontend/` — 前端應用層

Next.js 14 App Router 架構，組件結構 1:1 對應設計系統。

```
畫面路由對照：
/          → redirect → /c5isr
/c5isr     → C5ISR 指揮看板（主畫面）
/navigator → MITRE ATT&CK 導航
/planner   → 任務規劃器
/monitor   → 戰場監控
```

#### 組件分類邏輯

| 分類 | 含義 | 範例 |
|------|------|------|
| `layout/` | 頁面級佈局框架 | Sidebar, PageHeader, AlertBanner |
| `atoms/` | 最小可重用單元 | Button, Badge, StatusDot, Toggle |
| `cards/` | 資訊卡片容器 | MetricCard, HostNodeCard |
| `data/` | 資料展示組件 | DataTable, LogEntry, AgentBeacon |
| `mitre/` | MITRE 專屬組件 | MITRECell, KillChainIndicator |
| `ooda/` | OODA 專屬組件 | OODAIndicator, OODATimelineEntry |
| `c5isr/` | C5ISR 專屬組件 | C5ISRStatusBoard, DomainCard |
| `topology/` | 拓樸圖組件 | AttackNode, NetworkTopology |
| `modal/` | 對話框組件 | HexConfirmModal |
| `nav/` | 導航組件 | NavItem, TabBar |

#### Hooks 職責

| Hook | 功能 | 觸發時機 |
|------|------|---------|
| `useOperation` | 管理當前作戰的完整資料 | 頁面載入 / 操作切換 |
| `useWebSocket` | 建立 WebSocket 連線，分發事件 | 應用初始化 |
| `useOODA` | 訂閱 OODA 階段變化 | C5ISR Board / Monitor |
| `useLiveLog` | 即時日誌串流（WebSocket + 緩衝） | Battle Monitor |

### 4. `infra/` — 基礎設施層

外部依賴服務的本地開發配置。

| 服務 | 用途 | 授權 |
|------|------|------|
| Caldera | MITRE 官方紅隊執行引擎 | Apache 2.0 |
| Shannon | AI 自適應攻擊引擎（選用） | AGPL-3.0（API 隔離） |

---

## 根目錄配置檔

### `.env.example`

```env
# Athena 環境變數
DATABASE_URL=sqlite:///backend/data/athena.db

# 外部服務
CALDERA_URL=http://localhost:8888
CALDERA_API_KEY=your-caldera-key
SHANNON_URL=http://localhost:9000

# PentestGPT
PENTESTGPT_API_URL=http://localhost:8080
PENTESTGPT_MODEL=gpt-4

# 自動化模式
AUTOMATION_MODE=semi_auto
RISK_THRESHOLD=medium

# 前端
NEXT_PUBLIC_API_URL=http://localhost:8000/api
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws
```

### `Makefile`

```makefile
.PHONY: dev seed test clean

# 啟動開發環境（前後端同時）
dev:
	docker-compose up --build

# 僅啟動後端
dev-backend:
	cd backend && uvicorn app.main:app --reload --port 8000

# 僅啟動前端
dev-frontend:
	cd frontend && npm run dev

# 載入示範資料
seed:
	cd backend && python -m app.seed.demo_scenario

# 執行測試
test:
	cd backend && pytest -v
	cd frontend && npm test

# 清除資料庫
clean:
	rm -f backend/data/athena.db
```

### `docker-compose.yml`

```yaml
version: "3.8"

services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    volumes:
      - ./backend/data:/app/data
    env_file:
      - .env
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://backend:8000/api
      - NEXT_PUBLIC_WS_URL=ws://backend:8000/ws
    depends_on:
      - backend
```

### `.gitignore`

```gitignore
# Python
__pycache__/
*.pyc
*.pyo
.venv/
*.egg-info/

# Node
node_modules/
.next/
out/

# 環境
.env
.env.local

# 資料庫
*.db
*.sqlite
*.sqlite3

# IDE
.vscode/
.idea/
*.swp

# OS
.DS_Store
Thumbs.db

# 建置產物
dist/
build/
```

---

## 畫面 ↔ 目錄對照

| 畫面 | 設計檔 | 頁面路由 | 主要組件 | 資料 Hook |
|------|--------|---------|---------|----------|
| App Shell | `shell.pen` | `layout.tsx` | `Sidebar`, `AlertBanner` | `useOperation` |
| C5ISR 指揮看板 | `c5isr-board.pen` | `/c5isr` | `C5ISRStatusBoard`, `MetricCard`, `OODAIndicator`, `RecommendCard` | `useOperation`, `useOODA` |
| MITRE 導航 | `mitre-navigator.pen` | `/navigator` | `MITRECell`, `KillChainIndicator`, `TechniqueCard` | `useOperation` |
| 任務規劃 | `mission-planner.pen` | `/planner` | `DataTable`, `OODATimelineEntry`, `HostNodeCard` | `useOperation`, `useOODA` |
| 戰場監控 | `battle-monitor.pen` | `/monitor` | `NetworkTopology`, `ThreatLevelGauge`, `LogEntry`, `AgentBeacon` | `useWebSocket`, `useLiveLog` |

---

## OODA 循環 ↔ 程式碼對照

```
┌─────────────────────────────────────────────────────────┐
│                    OODA 循環                             │
├──────────┬──────────┬──────────┬──────────────────────────┤
│ OBSERVE  │ ORIENT   │ DECIDE   │ ACT                     │
├──────────┼──────────┼──────────┼──────────────────────────┤
│ Service  │ Service  │ Service  │ Service                  │
│ fact_    │ orient_  │ decision_│ engine_router.py         │
│ collector│ engine   │ engine   │ → caldera_client.py      │
│ .py      │ .py      │ .py      │ → shannon_client.py      │
├──────────┼──────────┼──────────┼──────────────────────────┤
│ 畫面     │ 畫面     │ 畫面     │ 畫面                     │
│ Monitor  │ Navigator│ C5ISR    │ Monitor                  │
│ (日誌)   │ (矩陣)   │ (建議)   │ (拓樸/Agent)             │
│          │          │ Planner  │                          │
│          │          │ (步驟)   │                          │
└──────────┴──────────┴──────────┴──────────────────────────┘
```

---

## 開發優先順序

POC 開發建議按以下順序推進：

| 階段 | 範圍 | 產出 |
|------|------|------|
| **Phase 1** | 建立目錄骨架 + 搬移設計檔 | 專案結構 |
| **Phase 2** | `backend/app/models/` 全部模型 + enum | Pydantic 可 import |
| **Phase 3** | `backend/app/database.py` + SQLite schema | DB 可初始化 |
| **Phase 4** | `backend/app/seed/demo_scenario.py` | OP-2024-017 種子資料 |
| **Phase 5** | `backend/app/routers/` 核心 API | REST 可呼叫 |
| **Phase 6** | `frontend/src/types/` TypeScript 型別 | 前端型別安全 |
| **Phase 7** | `frontend/src/components/` 核心組件 | UI 可渲染 |
| **Phase 8** | WebSocket + Hooks 整合 | 即時更新 |
| **Phase 9** | Docker + Makefile | 一鍵啟動 |

---

## 相關文件

- [data-architecture.md](./data-architecture.md) — 完整資料架構（Models、Schema、API、Seed Data）
- [CLAUDE.md](../../CLAUDE.md) — 專案 AI 上下文 + POC 需求定義
