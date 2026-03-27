# Athena

[![Star on GitHub](https://img.shields.io/github/stars/astroicers/Athena?style=social)](https://github.com/astroicers/Athena)
[![License](https://img.shields.io/badge/license-BSL%201.1-blue.svg)](LICENSE)

> **C5ISR + OODA — AI 驅動的網路作戰指揮平台**
>
> Military-Grade Cyber Command Framework — C5ISR Situational Awareness × OODA Decision Loop

Athena 以軍事 C5ISR 框架實現網路作戰的態勢感知，以 OODA 循環驅動動態決策，
以 AI 輔助指揮官從觀察到行動的每一步判斷。輸入任何授權的 IPv4、IPv6 或域名，
系統在 C5ISR 六域監控下自動完成完整 Kill Chain：
**OSINT → Recon → CVE 關聯 → 初始存取 → OODA 循環 → 結構化報告**。

---

## 為何選擇 Athena？

傳統滲透測試工具聚焦於**「如何滲透」**。Athena 聚焦於**「如何指揮」**。

| 傳統工具 | Athena |
|---------|--------|
| 操作員控制台 | 指揮官儀表板 |
| 靜態腳本 | 動態 OODA 循環 |
| 以工具為中心 | 以框架為中心（C5ISR） |
| IP 限定輸入 | IPv4 / IPv6 / 域名通用輸入 |
| 手動每步驟 | OSINT → Recon → 存取 → OODA 全自動 |

---

## Cyber Kill Chain × Athena

Athena 的自動化管線對應 Lockheed Martin Cyber Kill Chain 七階段：

| # | Kill Chain 階段 | Athena 模組 |
|---|----------------|-------------|
| 1 | **Reconnaissance** | ReconEngine (nmap) + OSINTEngine (DNS/SSL/crt.sh) |
| 2 | **Weaponization** | OrientEngine AI 分析 + Playbook 劇本選擇 |
| 3 | **Delivery** | InitialAccessEngine (SSH brute-force / exploit) |
| 4 | **Exploitation** | DirectSSHClient / C2Client 執行 exploit |
| 5 | **Installation** | Agent 部署（beacon 建立） |
| 6 | **Command & Control** | DirectSSHEngine (預設) / Caldera C2 (選用) |
| 7 | **Actions on Objectives** | OODA 持續執行 → FactCollector 情報收集 → ReportGenerator |

### 但 Athena 不只是 Kill Chain

傳統 Kill Chain 是**線性單次**的。Athena 在此之上疊加三層：

```
┌─────────────────────────────────────────────────────┐
│            C5ISR 態勢感知（持續監控）                   │
│            六域健康狀態即時儀表板                        │
└────────────────────────┬────────────────────────────┘
                         │
  ┌──────────────────────┼──────────────────────────┐
  │                 OODA 循環（迭代決策）               │
  │                                                    │
  │   Observe → Orient(AI) → Decide(Risk Gate) → Act  │
  │      ↑                                        │    │
  │      └────────────────────────────────────────┘    │
  │                                                    │
  │   Kill Chain 不是跑一次就結束，                      │
  │   每一輪 OODA 都觸發新的 Kill Chain 階段             │
  └──────────────────────┬──────────────────────────┘
                         │
┌────────────────────────┴────────────────────────────┐
│            Compliance 合規層                          │
│            ScopeValidator (RoE) + DecisionEngine     │
│            風險門檻 + 授權範圍控制                      │
└─────────────────────────────────────────────────────┘
```

> **Kill Chain 是骨幹，OODA 讓它循環，C5ISR 讓它有態勢感知，Compliance 讓它不失控。**

---

## 架構

```
┌─────────────────────────────────────────────────────┐
│                    通用目標輸入                        │
│             IPv4  │  IPv6  │  Domain Name            │
└────────────────────────┬────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────┐
│              前期管線                                 │
│  ScopeValidator → OSINTEngine → ReconEngine          │
│  → VulnLookup → InitialAccessEngine                  │
└────────────────────────┬────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────┐
│              C5ISR 決策引擎                           │
│  MITRE ATT&CK 映射 │ OODA 循環控制器                  │
│  OrientEngine (AI)  │ Playbook 知識庫                 │
│  APScheduler 自動循環 │ Attack Path Timeline           │
│  Tool Registry      │ Engagement 管理                 │
└────────────────────────┬────────────────────────────┘
                         ↓
    ┌────────────┬───────┴────────┬──────────────┐
    ↓            ↓                ↓              ↓
┌────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐
│Persist.│ │ Direct   │ │C2 Engine │ │  Mock  │
│SSH Pool│ │SSH Engine│ │ (選用)   │ │(CI/Dev)│
└────────┘ └──────────┘ └──────────┘ └────────┘
                         ↓
┌─────────────────────────────────────────────────────┐
│       指揮官介面（Next.js 14 + Tailwind v4 + i18n）   │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐       │
│  │ C5ISR  │ │ MITRE  │ │Mission │ │Battle  │       │
│  │ Board  │ │Navigat.│ │Planner │ │Monitor │       │
│  └────────┘ └────────┘ └────────┘ └────────┘       │
│  ┌────────┐ ┌─────────────┐ ┌──────────────────┐   │
│  │ Tool   │ │Web Terminal │ │ Attack Situation │   │
│  │Registry│ │(SSH console)│ │     Diagram      │   │
│  └────────┘ └─────────────┘ └──────────────────┘   │
└─────────────────────────────────────────────────────┘
```

---

## 功能亮點

**決策引擎**
- **OODA 循環** — Observe → Orient → Decide → Act，APScheduler 自動迭代，WebSocket 即時廣播
- **OrientEngine** — Claude API 驅動，分析態勢產生多選項戰術建議，LLM 即時監控（latency、backend 狀態）
- **C5ISR 六域監控** — Command / Control / Comms / Computers / Cyber / ISR 即時健康儀表板
- **Attack Situation Diagram** — 純 SVG 即時攻擊情勢圖，整合 Kill Chain 進度 + OODA 環形指示器 + C5ISR 健康條

**偵察與存取**
- **ReconEngine** — nmap port scan + OS/service 偵測
- **OSINTEngine** — crt.sh 憑證透明度 + subfinder 子域名枚舉 + DNS 解析
- **VulnLookup** — NVD NIST API CVE 關聯（28 種 CPE 映射 + 24h 快取）
- **InitialAccessEngine** — SSH brute-force + 動態 exploit 選擇 + 憑證回流

**執行引擎**
- **PersistentSSHEngine** — 連線池 + TOCTOU 安全鎖，生產級
- **DirectSSHEngine** — asyncssh 單次連線，輕量預設
- **C2EngineClient** — 選用外部 C2 整合，API 隔離
- **EngineRouter** — 統一路由到四種引擎
- **Tool Registry** — 集中式工具/引擎註冊中心，CRUD REST API + 前端管理頁面（10 個預設種子工具）

**合規與報告**
- **ScopeValidator** — RoE 白/黑名單範圍驗證，防止誤掃
- **DecisionEngine** — 依風險等級控制自動化（LOW 自動 → CRITICAL 永遠手動）
- **ReportGenerator** — PentestReport JSON + Markdown，含執行摘要與攻擊時序
- **Playbook 知識庫** — 13 個 Linux technique + CRUD API + 動態 output_parser

**指揮官介面**
- **可收合側邊欄** — 展開 224px / 收合 64px，icon-only 模式
- **Web Terminal** — 對已入侵目標建立 SSH 連線，互動式命令執行，安全黑名單防護
- **Topology Tab** — 獨立拓撲頁籤，節點詳情面板（IP / OS / 角色 / Kill Chain 進度 / Facts）
- **Recommendation History** — 右側抽屜完整 AI 建議歷史，含態勢評估展開
- **國際化 (i18n)** — 繁體中文 / English 雙語切換（next-intl）
- **批次目標匯入** — 支援 CIDR / IP / 域名批次匯入（最多 512 筆）

---

## 快速啟動

```bash
git clone https://github.com/astroicers/Athena && cd Athena
cp .env.example .env    # 編輯 .env 設定 ANTHROPIC_API_KEY 或使用 claude login (OAuth)
make up                 # docker-compose up --build -d
```

| 服務 | 網址 |
|-----|------|
| Athena UI | http://localhost:58080 |
| API 健康檢查 | http://localhost:58000/api/health |
| API 文件 (Swagger) | http://localhost:58000/docs |

> 詳細環境變數與安裝步驟請參閱 [安裝指南](docs/GETTING_STARTED.md)

---

## 螢幕截圖

### C5ISR Board — 作戰態勢總覽
<!-- TODO: docs/screenshots/c5isr-board.png -->

### MITRE Navigator — 技術矩陣視覺化
<!-- TODO: docs/screenshots/mitre-navigator.png -->

### Mission Planner — 任務規劃與 OODA 循環
<!-- TODO: docs/screenshots/mission-planner.png -->

### Battle Monitor — 拓撲即時監控 + 攻擊情勢圖
<!-- TODO: docs/screenshots/battle-monitor.png -->

### Tool Registry — 工具/引擎管理
<!-- TODO: docs/screenshots/tool-registry.png -->

---

## 技術棧

| 層級 | 技術 |
|------|------|
| 後端 | Python 3.12 + FastAPI + Pydantic v2 + PostgreSQL 16 (asyncpg) |
| 前端 | Next.js 14 + React 18 + Tailwind CSS v4 + next-intl |
| 3D 拓樸 | react-force-graph-3d + Three.js |
| AI 決策 | OrientEngine + Claude API (api_key / oauth / auto) |
| SSH 執行 | PersistentSSHEngine (連線池) / DirectSSHEngine (單次) |
| OSINT | crt.sh + subfinder + dnspython |
| 漏洞情報 | NVD NIST API v2 + PostgreSQL 24h 快取 |
| 排程 | APScheduler |
| 容器化 | Docker + docker-compose |
| 測試 | pytest (370+) + Vitest (63+) + Playwright E2E (158+) |

---

## 文件

| 文件 | 說明 |
|-----|------|
| [安裝指南](docs/GETTING_STARTED.md) | 環境需求、安裝步驟、常見問題 |
| [Demo 演練](docs/DEMO_WALKTHROUGH.md) | 完整 Demo 場景演練 |
| [系統架構](docs/architecture.md) | 高層架構、資料流、元件關係 |
| [開發路線圖](docs/ROADMAP.md) | 完整開發計畫與 Phase 進度 |
| [資料架構](docs/architecture/data-architecture.md) | DB Schema、API Schema、種子資料 |
| [專案結構](docs/architecture/project-structure.md) | 目錄佈局、各層職責 |
| [變更紀錄](CHANGELOG.md) | 完整版本歷史 |

---

## 目標使用者

- **軍方/政府** — 任務級網路戰模擬與指揮演練
- **紅隊** — 戰略規劃結合 AI 輔助戰術執行
- **資安顧問** — 指揮官視角的滲透測試管理平台
- **企業安全團隊** — 從域名到完整滲透測試報告的端對端自動化
- **研究人員** — 軍事 C5ISR 框架應用於攻擊性資安領域

---

## 授權

Athena 核心程式碼採用 **Business Source License 1.1 (BSL 1.1)** 授權。

- **非商業用途免費** — 個人使用、學術研究、教育用途、CTF 競賽皆可自由使用
- **商業用途** — 需另行取得商業授權，請聯繫 azz093093.830330@gmail.com
- **自動開源** — 每個版本發佈 4 年後自動轉為 Apache License 2.0
- MITRE ATT&CK 知識庫：CC BY 4.0（僅引用，不分發）

詳見 [LICENSE](LICENSE) 檔案。
