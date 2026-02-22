# [ADR-001]: 初始技術棧選型

| 欄位 | 內容 |
|------|------|
| **狀態** | `Accepted` |
| **日期** | 2026-02-22 |
| **決策者** | 專案負責人（軍事顧問 / 單人 POC） |

---

## 背景（Context）

Athena 是一套 AI 驅動的 C5ISR 網路作戰指揮平台，定位為軍事級指揮與決策系統。POC 階段目標：以最低資源驗證「PentestGPT 情報 + Caldera 執行 + OODA 循環」的核心指揮概念。

關鍵限制條件：

- **單人開發**：個人部署，無團隊協作需求
- **POC 預算**：LLM API 成本 < $20，無基礎設施支出
- **授權合規**：核心平台必須商業友善（Apache 2.0），第三方元件需授權隔離
- **展示導向**：需在 Demo 中直觀呈現 C5ISR、OODA、MITRE ATT&CK 概念
- **硬體限制**：4 CPU / 8 GB RAM 最低配置

需決策 6 個技術領域：後端框架、前端框架、資料庫、AI/ML 情報層、執行引擎、3D 視覺化。

---

## 評估選項（Options Considered）

### 後端框架

#### 選項 A：Python 3.11 + FastAPI + Pydantic

- **優點**：async 原生、自動 OpenAPI 文件、Pydantic 型別安全、PentestGPT 為 Python 生態（可直接 import）
- **缺點**：相較 Go 運行效能較低
- **風險**：SQLite + async 需注意 aiosqlite 連線管理

#### 選項 B：Go + Gin/Echo

- **優點**：高效能、低記憶體、單一二進位部署
- **缺點**：PentestGPT 為 Python，需跨語言 IPC；Go 生態中 LLM 整合工具較少
- **風險**：增加整合複雜度，POC 開發速度較慢

#### 選項 C：Node.js + Express/Fastify

- **優點**：前後端同語言（JavaScript/TypeScript）
- **缺點**：PentestGPT 為 Python，需 subprocess 或 API 橋接；型別安全不如 Pydantic
- **風險**：AI/ML 生態偏 Python，長期維護成本高

### 前端框架

#### 選項 A：Next.js 14 (App Router) + React 18 + Tailwind CSS v4

- **優點**：App Router 支援 Server Components、Tailwind 與 Pencil.dev 設計 Token 無縫整合、React 生態龐大
- **缺點**：App Router 較新，部分套件相容性待驗證
- **風險**：3D 拓樸需 client-only component（react-force-graph-3d 不支援 SSR）

#### 選項 B：Vite + React 18 + Tailwind

- **優點**：更輕量、建置更快
- **缺點**：無 SSR（SEO 非需求，可接受）、路由需額外配置
- **風險**：POC 可行，但未來擴展至正式版缺少 Next.js 的 full-stack 能力

### 資料庫

#### 選項 A：SQLite（檔案式）

- **優點**：零配置、無需獨立服務、備份即複製檔案、輕量 POC 完美選擇
- **缺點**：無並發寫入、無網路存取
- **風險**：POC 規模完全足夠；正式版需遷移至 PostgreSQL

#### 選項 B：PostgreSQL

- **優點**：正式環境就緒、並發支援、進階查詢
- **缺點**：需額外 Docker 容器（+200MB RAM）、配置複雜度增加
- **風險**：POC 過度設計

### AI/ML 情報層

#### 選項 A：PentestGPT（MIT 授權）+ Claude API（主要）+ GPT-4（備用）

- **優點**：PentestGPT 為 MIT 可安全直接 import、Claude 推理能力卓越（200K 上下文）、雙 LLM 容錯
- **缺點**：依賴外部 LLM API、成本按使用量計算
- **風險**：LLM API 可用性；透過備用 LLM 降低風險

> Orient 引擎整合架構（輸出 schema、3 選項設計、confidence 分數）詳見 ADR-005。

#### 選項 B：本地 LLM（Ollama + Llama 3）

- **優點**：無 API 成本、離線可用
- **缺點**：推理品質遠遜 Claude/GPT-4、需 GPU（資源不足）、PentestGPT 整合需大幅修改
- **風險**：戰術分析品質不足以展示 Athena 核心價值

### 執行引擎

#### 選項 A：Caldera（Apache 2.0，必要）+ Shannon（AGPL-3.0，選用，API 隔離）

- **優點**：Caldera 為 MITRE 官方、MITRE ATT&CK 原生、Apache 2.0 授權安全；Shannon 提供 AI 自適應能力
- **缺點**：Shannon 為 AGPL-3.0 需嚴格 API 隔離
- **風險**：Shannon 授權污染（透過 API-only 隔離解決，詳見 ADR-006）

#### 選項 B：僅 Caldera

- **優點**：授權單純、複雜度低
- **缺點**：缺少 AI 自適應執行展示
- **風險**：POC 完全可行；Shannon 可後期加入

### 3D 拓樸視覺化

#### 選項 A：react-force-graph-3d + Three.js

- **優點**：MIT 授權、React 原生元件、WebGL 3D 渲染、內建粒子動畫、力導向佈局
- **缺點**：不支援 SSR（需 dynamic import）
- **風險**：低 — 已通過 Battle Monitor Demo 驗證

#### 選項 B：D3.js（2D）

- **優點**：成熟穩定、SSR 友善
- **缺點**：2D 視覺衝擊力不足，無法展示 Athena「軍事級指揮」定位
- **風險**：功能足夠但差異化不足

---

## 決策（Decision）

每個領域選擇 **選項 A**：

| 領域 | 決策 | 關鍵理由 |
|------|------|---------|
| 後端 | Python 3.11 + FastAPI + Pydantic | PentestGPT 原生生態 + 型別安全 |
| 前端 | Next.js 14 + React 18 + Tailwind v4 | Pencil.dev Token 整合 + App Router |
| 資料庫 | SQLite（POC） | 零配置、輕量、POC 完美匹配 |
| AI/ML | PentestGPT + Claude（主）+ GPT-4（備） | 推理品質 + 雙 LLM 容錯 |
| 執行引擎 | Caldera（必要）+ Shannon（選用 API 隔離） | MITRE 官方 + AI 自適應選項 |
| 3D 視覺化 | react-force-graph-3d + Three.js | WebGL 3D + React 原生 + 已驗證 |

---

## 後果（Consequences）

**正面影響：**

- PentestGPT 可直接 `import`（MIT），無需跨語言橋接
- FastAPI 自動產生 OpenAPI 文件，加速前後端整合
- SQLite 零依賴，`docker-compose up` 即可啟動全環境
- Claude 200K 上下文可容納完整作戰歷史（Orient 階段關鍵）
- Caldera Apache 2.0 + PentestGPT MIT = 核心平台授權乾淨
- 3D 拓樸具備高度視覺衝擊力，強化 Demo 效果

**負面影響 / 技術債：**

- SQLite → PostgreSQL 遷移（Phase 8 正式版）
- Shannon AGPL-3.0 需持續維護 API 隔離邊界（絕不能 import）
- Next.js App Router 部分 3D 元件需 `"use client"` + `dynamic(() => import(...), { ssr: false })`
- LLM API 依賴外部服務（離線測試需 mock）

**後續追蹤：**

- [ ] Phase 1：建立 `docker-compose.yml` 驗證完整啟動流程
- [ ] Phase 2：驗證 PentestGPT import 相容性（版本鎖定）
- [ ] Phase 5：建立 LLM mock 層供離線測試
- [ ] Phase 8：SQLite → PostgreSQL 遷移方案

---

## 關聯（Relations）

- 取代：（無 — 首次技術選型）
- 被取代：（無）
- 參考：CLAUDE.md 技術棧章節、docs/ROADMAP.md 技術棧參考表、ADR-005（PentestGPT Orient 整合架構）、ADR-006（執行引擎授權隔離）、ADR-008（SQLite Schema 設計）、ADR-009（前端元件架構）
