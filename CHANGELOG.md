# Changelog

本專案遵循 [Keep a Changelog](https://keepachangelog.com/zh-TW/1.1.0/) 格式，
版本號遵循 [Semantic Versioning](https://semver.org/lang/zh-TW/)。

---

## [Unreleased]

> Phase 7.1 文件撰寫進行中。

### Added
- 重寫 `README.md`：專案首頁含架構圖、快速啟動、功能亮點、進度追蹤
- 新增 `docs/GETTING_STARTED.md`：從零開始的安裝與開發指南
- 新增 `docs/DEMO_WALKTHROUGH.md`：6 步 OODA 循環 Demo 操作手冊
- 更新 `CHANGELOG.md`：補齊 Phase 1~6 所有變更紀錄

---

## [0.6.0] — 2026-02-26

### Phase 6：整合與 Docker 部署（SPEC-009 / SPEC-010）

#### Added
- `backend/app/seed/demo_runner.py` — 自動化 6 步 OODA Demo 腳本（支援 `DEMO_STEP_DELAY` 與 retry 邏輯）
- `backend/Dockerfile` — Python 3.11-slim 容器映像，含 HEALTHCHECK
- `backend/.dockerignore` — 排除 `__pycache__/`、`.venv/`、`tests/`、`data/*.db`
- `frontend/Dockerfile` — 多階段 Node 20-alpine 建構，standalone 輸出
- `frontend/.dockerignore` — 排除 `node_modules/`、`.next/`、`out/`
- `docker-compose.yml` — 完整服務編排：healthcheck、named volume、`service_healthy` 依賴
- Makefile 新增 `up`、`down`、`docker-clean` targets

#### Changed
- `/api/health` 增強：回報 `mock`/`connected`/`disabled`/`active`/`claude`/`openai`/`unavailable` 等動態狀態
- `frontend/next.config.js` 加入 `output: "standalone"` 支援容器化部署

---

## [0.5.0] — 2026-02-26

### Phase 5：OODA 循環引擎（SPEC-007 / SPEC-008）

#### Added
- `backend/app/services/ooda_controller.py` — OODA 循環控制器（trigger/advance/get_state）
- `backend/app/services/pentestgpt_client.py` — PentestGPT 情報客戶端（Mock + 真實模式）
- `backend/app/services/caldera_client.py` — Caldera 執行引擎客戶端（Mock + 真實模式）
- `backend/app/services/shannon_client.py` — Shannon 執行引擎客戶端（Mock + 真實模式）
- `backend/app/routers/ooda.py` — OODA API 路由（trigger、advance、get state）

#### Fixed
- 程式碼審查修正：2 個 Critical + 6 個 Important + 4 個 Minor 問題（`a6beec4`）
- 提取 `_activate_if_planning()` 輔助方法，移除 7 個重複的狀態檢查區塊（`7e6b2bf`）

---

## [0.4.0] — 2026-02-26

### Phase 4：畫面實作（SPEC-006）

#### Added
- 4 個核心畫面：C5ISR Board、MITRE Navigator、Mission Planner、Battle Monitor
- 15 個 React 元件實作
- 3D 拓樸視覺化整合（react-force-graph-3d + Three.js）

#### Fixed
- `HexIcon` 的 `bg-current` 與 `Toggle` 的 `translate-x` 修正（`38dc16a`）

---

## [0.3.0] — 2026-02-26

### Phase 3：前端基礎（SPEC-005）

#### Added
- TypeScript 型別定義（對應後端 13 個 Enum + 12 個 Model）
- Next.js App Router 佈局（`layout.tsx`、`page.tsx`）
- 自訂 Hooks：`useWebSocket`、`useApi`
- 原子元件：`HexButton`、`HexIcon`、`StatusBadge`、`Toggle`、`KPICard`

---

## [0.2.0] — 2026-02-25

### Phase 2：後端基礎（SPEC-002 / SPEC-003 / SPEC-004）

#### Added
- Pydantic v2 模型與 13 個 Enum（`SPEC-002`）
- SQLite 資料庫層 + aiosqlite 非同步存取（`SPEC-003`）
- PHANTOM-EYE 種子資料（OP-2024-017 完整作戰場景）
- FastAPI 進入點 + CORS 中介層（`SPEC-004`）
- REST API 路由：operations、techniques、c5isr、missions
- WebSocket 管理器（即時事件推播）

#### Fixed
- Pydantic V2 棄用警告修正：`config.py` 改用 `model_config`（`8fea392`）
- `get_db()` 回傳型別標註修正為 async generator（`129cebc`）
- `_ensure_operation` 去重複 + `C5ISRUpdate` schema 搬遷（`7c2b86e`）
- Pydantic model 預設值對齊 SQL schema（`c566fe3`）

---

## [0.1.1] — 2026-02-25

### Phase 1：專案骨架（SPEC-001）

#### Added
- Monorepo 專案結構（`backend/`、`frontend/`）
- `backend/pyproject.toml` — Python 依賴宣告（FastAPI、uvicorn、aiosqlite、httpx）
- `frontend/package.json` — Next.js 14 + React 18 + Tailwind CSS v4
- `frontend/tsconfig.json`、`tailwind.config.ts`、`postcss.config.mjs`
- `backend/app/config.py` — Pydantic Settings 環境變數管理
- `.gitkeep` 檔案確保空目錄版本追蹤

#### Changed
- ASP 框架升級至 v1.2.0：hooks、精簡 CLAUDE.md（`cef2123`）

---

## [0.1.0] — 2026-02-25

### Phase 0：設計與架構（Design & Architecture）

#### Added
- 6 個 `.pen` 設計稿（Design System、Shell、C5ISR Board、MITRE Navigator、Mission Planner、Battle Monitor）
- 資料架構文件（13 Enum、12 Model、12 張 SQL Schema、35+ REST API、7 種 WebSocket 事件、種子資料）
- 專案結構文件（Monorepo 佈局、前後端分層職責）
- 開發路線圖（ROADMAP.md — Phase 0-8）
- 12 份 ADR（ADR-001 ~ ADR-012），涵蓋技術棧、OODA 引擎、授權隔離、前端架構等關鍵決策
- 10 份 SPEC（SPEC-001 ~ SPEC-010），涵蓋 Phase 1-6 全部實作規格
- ASP 框架（v1.2.0）整合：profiles、hooks、templates、Makefile targets
- CLAUDE.md v4（AI 助手完整上下文文件）
- `.env.example`（環境變數範本）
- `.gitignore`（Python、Node.js、SQLite、憑證檔排除）

#### Changed
- `.pen` 設計檔從根目錄搬入 `design/`
- `data-architecture.md` 反向更新：Technique.description、User seed data、ON DELETE CASCADE、/health endpoint
- `project-structure.md` 修正：TrafficStream.tsx 歸屬 topology/、設計檔路徑更新

---

[Unreleased]: https://github.com/astroicers/Athena/compare/v0.6.0...HEAD
[0.6.0]: https://github.com/astroicers/Athena/compare/v0.5.0...v0.6.0
[0.5.0]: https://github.com/astroicers/Athena/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/astroicers/Athena/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/astroicers/Athena/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/astroicers/Athena/compare/v0.1.1...v0.2.0
[0.1.1]: https://github.com/astroicers/Athena/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/astroicers/Athena/releases/tag/v0.1.0
