# Athena

> **AI 驅動的 C5ISR 網路作戰指揮平台**
>
> AI-Powered C5ISR Cyber Operations Command Platform

Athena 將滲透測試從戰術工具操作提升至戰略軍事指揮。基於 C5ISR（Command, Control, Communications, Computers, Cyber, Intelligence, Surveillance, Reconnaissance）框架，Athena 橋接 MITRE Caldera 的執行能力與 AI 輔助決策，實現真正的指揮官視角作戰管理。

---

## 為何選擇 Athena？

傳統滲透測試工具聚焦於**「如何滲透」**。
Athena 聚焦於**「如何指揮」**。

| 傳統工具 | Athena |
|---------|--------|
| 操作員控制台 | 指揮官儀表板 |
| 技術執行 | 戰略決策 |
| 靜態腳本 | 動態 OODA 循環 |
| 以工具為中心 | 以框架為中心 |

- **不是工具** — 而是指揮與控制決策平台
- **不是腳本** — 而是軍事作戰框架（C5ISR）
- **不是靜態** — OODA 循環驅動的動態調適
- **不只技術** — 戰略 + 戰術整合，AI 輔助決策

---

## 架構

```
┌─────────────────────────────────────────────────────┐
│              指揮官介面                              │
│   Next.js 14 + React 18 + Tailwind v4               │
│                                                      │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌─────────┐     │
│  │ C5ISR  │ │ MITRE  │ │ Mission│ │ Battle  │     │
│  │ Board  │ │Navigator│ │Planner │ │Monitor  │     │
│  └────────┘ └────────┘ └────────┘ └─────────┘     │
└───────────────────────┬─────────────────────────────┘
                        ↓
┌───────────────────────────────────────────────────  ┐
│         C5ISR 決策引擎（核心創新）                  │
│                                                      │
│    MITRE ATT&CK 映射  │  OODA 循環控制器            │
│    ───────────────────────────────────────────      │
│    PentestGPT 戰術情報（Orient 階段 AI 分析）        │
└───────────────────────┬─────────────────────────────┘
                        ↓
          ┌─────────────┴──────────────┐
          ↓                            ↓
┌──────────────────┐         ┌──────────────────┐
│  MITRE Caldera   │         │    Shannon       │
│  標準執行引擎    │         │  AI 自適應執行   │
│  Apache 2.0      │         │  AGPL-3.0（選用）│
└──────────────────┘         └──────────────────┘
```

---

## 功能亮點

### OODA 循環引擎
完整實作軍事決策循環：**Observe（觀察）→ Orient（導向）→ Decide（決策）→ Act（行動）**。每次作戰迭代皆透過 OODA 框架驅動，實現動態戰術調適而非線性腳本執行。

### C5ISR 六域健康監控
即時監控六大作戰域狀態：**Command（指揮）**、**Control（控制）**、**Communications（通訊）**、**Computers（電腦）**、**Cyber（網路）**、**ISR（情報/監視/偵察）**。作戰全局一目了然。

### PentestGPT 戰術情報
核心差異化元件。在 OODA 的 Orient 階段，PentestGPT 分析當前態勢、考量已完成技術與失敗因素，產生附帶推理的多選項戰術建議，並推薦最佳執行路徑。指揮官做決策，AI 提供依據。

### 半自動模式（依風險等級控制）
可切換的執行控制模式，依技術風險等級自動決定是否需要人工審核：

| 風險等級 | 行為 |
|---------|------|
| LOW | 自動執行 |
| MEDIUM | 自動排隊，需指揮官批准 |
| HIGH | 強制確認對話框（HexConfirmModal） |
| CRITICAL | 永遠手動，不可自動化 |

---

## 快速啟動

```bash
# 1. 取得專案
git clone https://github.com/astroicers/Athena && cd Athena

# 2. 設定環境變數（加入 ANTHROPIC_API_KEY）
cp .env.example .env

# 3. 啟動所有服務
make up
# 或：docker-compose up --build -d
```

啟動後存取：

| 服務 | 網址 |
|-----|------|
| Athena UI | http://localhost:3000 |
| API 健康檢查 | http://localhost:8000/api/health |
| Swagger 文件 | http://localhost:8000/docs |

> 詳細安裝步驟請參閱 [安裝指南](docs/GETTING_STARTED.md)

---

## 螢幕截圖

### C5ISR Board — 作戰態勢總覽
<!-- TODO: 加入截圖 — docs/screenshots/c5isr-board.png -->

### MITRE Navigator — 技術矩陣視覺化
<!-- TODO: 加入截圖 — docs/screenshots/mitre-navigator.png -->

### Mission Planner — 任務規劃與 OODA 循環
<!-- TODO: 加入截圖 — docs/screenshots/mission-planner.png -->

### Battle Monitor — 3D 拓樸即時監控
<!-- TODO: 加入截圖 — docs/screenshots/battle-monitor.png -->

---

## 技術棧

| 層級 | 技術 |
|------|------|
| 後端 | Python 3.11 + FastAPI + Pydantic + SQLite |
| 前端 | Next.js 14 + React 18 + Tailwind CSS v4 |
| 3D 拓樸 | react-force-graph-3d + Three.js |
| 設計 | Pencil.dev（56 元件 + 32 設計變數） |
| 執行引擎 | MITRE Caldera（Apache 2.0）/ Shannon（選用） |
| AI 情報 | PentestGPT + Claude Opus / GPT-4 |
| 容器化 | Docker + docker-compose |

---

## 目前進度

```
Phase 0 ████████████████████ 完成 — 設計與架構
Phase 1 ████████████████████ 完成 — 專案骨架
Phase 2 ████████████████████ 完成 — 後端基礎
Phase 3 ████████████████████ 完成 — 前端基礎
Phase 4 ████████████████████ 完成 — 畫面實作
Phase 5 ████████████████████ 完成 — OODA 循環引擎
Phase 6 ████████████████████ 完成 — 整合與 Docker
Phase 7 ██████░░░░░░░░░░░░░░ 進行中 — 文件
Phase 8 ░░░░░░░░░░░░░░░░░░░░ 未來 — 進階增強
```

---

## 文件

| 文件 | 說明 |
|-----|------|
| [安裝指南](docs/GETTING_STARTED.md) | 環境需求、安裝步驟、常見問題 |
| [Demo 演練](docs/DEMO_WALKTHROUGH.md) | 「奪取 Domain Admin」完整 Demo 場景 |
| [系統架構](docs/architecture.md) | 高層架構、資料流、元件關係 |
| [開發路線圖](docs/ROADMAP.md) | Phase 0-8 完整計畫 |
| [資料架構](docs/architecture/data-architecture.md) | 模型、Schema、REST API、種子資料 |
| [專案結構](docs/architecture/project-structure.md) | 目錄佈局、各層職責 |
| [AI 上下文](CLAUDE.md) | 完整專案上下文（供 AI 助手參閱） |

---

## 目標使用者

- **軍方/政府** — 任務級網路戰模擬與指揮演練
- **紅隊** — 戰略規劃結合 AI 輔助戰術執行
- **資安顧問** — 指揮官視角的滲透測試管理平台
- **研究人員** — 軍事 C5ISR 框架應用於攻擊性資安領域

---

## 授權

授權條款選定中（暫定 Apache 2.0）

- Athena 核心：暫定 Apache 2.0
- PentestGPT 整合：MIT（安全匯入）
- MITRE Caldera：Apache 2.0（API 整合）
- Shannon（選用）：AGPL-3.0（僅 API，授權隔離）

---

*版本：0.4.0-poc | 階段：POC（PentestGPT + Caldera）| 最後更新：2026-02-26*
