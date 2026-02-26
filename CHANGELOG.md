# Changelog

本專案遵循 [Keep a Changelog](https://keepachangelog.com/zh-TW/1.1.0/) 格式，
版本號遵循 [Semantic Versioning](https://semver.org/lang/zh-TW/)。

---

## [Unreleased]

### Phase 8.5：前端測試套件（SPEC-014）

#### Added
- `docs/specs/SPEC-014-frontend-test-suite.md` — 前端測試套件規格書
- `frontend/vitest.config.ts` — Vitest 配置（jsdom + react plugin + tsconfig paths）
- `frontend/src/test/setup.ts` — @testing-library/jest-dom 全域設定
- `frontend/src/lib/__tests__/api.test.ts` — 7 個 API 工具函式測試（toSnakeCase、fromApiResponse、api.get）
- `frontend/src/components/atoms/__tests__/*.test.tsx` — 12 個原子元件測試（Button 3 + Toggle 3 + Badge 2 + StatusDot 1 + ProgressBar 2 + HexIcon 1）
- `frontend/src/components/cards/__tests__/*.test.tsx` — 4 個卡片元件測試（MetricCard 2 + TechniqueCard 1 + RecommendCard 1）
- `frontend/src/components/data/__tests__/*.test.tsx` — 4 個資料元件測試（DataTable 3 + LogEntryRow 1）
- `frontend/src/components/modal/__tests__/HexConfirmModal.test.tsx` — 3 個模態元件測試（hidden/visible/critical double confirm）
- `frontend/src/components/ooda/__tests__/*.test.tsx` — 2 個 OODA 元件測試（OODAIndicator 1 + OODATimeline 1）
- `frontend/src/components/mitre/__tests__/MITRECell.test.tsx` — 1 個 MITRE 元件測試
- `frontend/src/components/c5isr/__tests__/DomainCard.test.tsx` — 1 個 C5ISR 元件測試
- `frontend/src/components/nav/__tests__/TabBar.test.tsx` — 1 個導覽元件測試
- `frontend/src/hooks/__tests__/*.test.ts` — 5 個 Hook 測試（useOperation 2 + useOODA 2 + useLiveLog 1）

#### Changed
- `frontend/package.json` — 新增 8 個 devDependencies（vitest、@vitest/coverage-v8、jsdom、@testing-library/react、@testing-library/jest-dom、@testing-library/user-event、vite-tsconfig-paths、@vitejs/plugin-react）+ test scripts
- `docs/specs/SPEC-005-frontend-foundation.md` — Done When 加入 `npm test` 要求
- `docs/specs/SPEC-006-four-screens.md` — Done When 加入 `npm test` 要求
- `.github/workflows/ci.yml` — frontend job 加入 `npm test` 步驟

#### Metrics
- 40 個 Vitest 測試全數通過（1.55s）
- 21 個測試檔案覆蓋 API utils + 6 原子元件 + 3 卡片 + 2 資料 + 1 模態 + 2 OODA + 1 MITRE + 1 C5ISR + 1 導覽 + 3 Hooks

---

### Phase 8：後端測試套件（SPEC-013）

#### Added
- `docs/specs/SPEC-013-backend-test-suite.md` — 後端測試套件規格書
- `backend/tests/conftest.py` — 測試基礎設施（in-memory SQLite + 4 個 fixtures）
- `backend/tests/test_spec_004_api.py` — 15 個 API smoke tests（health、operations CRUD、techniques、agents、C5ISR、logs、recommendations）
- `backend/tests/test_spec_007_ooda_services.py` — 20 個 OODA 服務單元測試（DecisionEngine 7 + OrientEngine 3 + FactCollector 3 + C5ISRMapper 4 + OODAController 3）
- `backend/tests/test_spec_008_clients.py` — 9 個執行引擎客戶端測試（MockCalderaClient 5 + ShannonClient 3 + CalderaClient 1）
- `backend/pyproject.toml` — 新增 `pytest-cov` 依賴 + pytest asyncio_mode=auto 配置

#### Changed
- `docs/specs/SPEC-004-rest-api-routes.md` — Done When 加入 `make test-filter FILTER=spec_004`
- `docs/specs/SPEC-007-ooda-loop-engine.md` — Done When 加入 `make test-filter FILTER=spec_007`
- `docs/specs/SPEC-008-execution-engine-clients.md` — Done When 加入 `make test-filter FILTER=spec_008`

#### Metrics
- 44 個 pytest 測試全數通過（0.21s）
- 程式碼覆蓋率：60%（`app/` 套件）

---

## [0.7.0] — 2026-02-26

### Phase 7：文件與開源發佈（SPEC-011 / SPEC-012）

#### 7.1 文件撰寫

- 重寫 `README.md`：專案首頁含架構圖、快速啟動、功能亮點、進度追蹤
- 新增 `docs/GETTING_STARTED.md`：從零開始的安裝與開發指南
- 新增 `docs/DEMO_WALKTHROUGH.md`：6 步 OODA 循環 Demo 操作手冊
- 更新 `CHANGELOG.md`：補齊 Phase 1~6 所有變更紀錄

#### 7.1.5 Vendor 整合（SPEC-012）

- 新增 `infra/caldera/docker-compose.caldera.yml` — 獨立 Caldera Docker 配置
- 新增 `infra/README.md` — 基礎設施管理指南（Caldera 操作、備份、版本相容性）
- 新增 `infra/pentestgpt/README.md` — PentestGPT 研究參考說明
- 修正 `health.py` — 真實 Caldera 連線檢查（G2）
- 實作 `agents.py` sync — 真實 Agent 同步（G3 + G8）
- 加入 `caldera_client.py` retry 邏輯 + 版本檢查（G4 + G7）
- 清理 `config.py` — 移除未使用的 PentestGPT 設定（G9）
- Makefile 新增 9 個 vendor 管理 targets

#### 7.2 開源合規

- 新增 `LICENSE` — Apache License 2.0 全文
- 所有 48 個 Python 原始碼檔加入 14 行 Apache 2.0 License Header
- 所有 54 個 TypeScript/TSX 原始碼檔加入 Apache 2.0 License Header
- 新增 `CONTRIBUTING.md` — 貢獻指南（開發設定、程式碼規範、PR 流程）
- 新增 `SECURITY.md` — 安全政策（漏洞揭露流程、範圍、時間表）
- 更新 `backend/pyproject.toml` — 加入 license、description 欄位
- 更新 `frontend/package.json` — 加入 license、description、repository 欄位
- Shannon AGPL-3.0 合規驗證通過（僅 HTTP API 呼叫，無程式碼匯入）

#### 7.3 GitHub Repository

- 新增 `.github/workflows/ci.yml` — GitHub Actions CI（ruff lint + pytest + npm lint + build + docker）
- 新增 `.github/ISSUE_TEMPLATE/bug_report.yml` — Bug 回報模板（YAML 表單）
- 新增 `.github/ISSUE_TEMPLATE/feature_request.yml` — 功能請求模板
- 新增 `.github/PULL_REQUEST_TEMPLATE.md` — PR 模板含 Checklist
- 新增 `frontend/.eslintrc.json` — ESLint 配置（next/core-web-vitals）
- Ruff lint 配置 + 自動修正 18 處 import 排序問題
- Dockerfile 加入 OCI image labels（title、description、license、version）

#### 7.4 首次發佈

- 標記 `v0.1.0` — Athena POC Release
- 新增 `scripts/add_license_headers.py` — License Header 批次新增工具

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

[Unreleased]: https://github.com/astroicers/Athena/compare/v0.7.0...HEAD
[0.7.0]: https://github.com/astroicers/Athena/compare/v0.6.0...v0.7.0
[0.6.0]: https://github.com/astroicers/Athena/compare/v0.5.0...v0.6.0
[0.5.0]: https://github.com/astroicers/Athena/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/astroicers/Athena/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/astroicers/Athena/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/astroicers/Athena/compare/v0.1.1...v0.2.0
[0.1.1]: https://github.com/astroicers/Athena/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/astroicers/Athena/releases/tag/v0.1.0
