# Athena

> **AI 驅動的 C5ISR 網路作戰指揮平台**

Athena 將滲透測試從戰術工具操作提升至戰略軍事指揮。基於 C5ISR（Command, Control, Communications, Computers, Cyber, Intelligence, Surveillance, Reconnaissance）框架，Athena 橋接 MITRE Caldera 的執行能力與 AI 輔助決策。

## 為何選擇 Athena？

傳統滲透測試工具聚焦於**「如何滲透」**。
Athena 聚焦於**「如何指揮」**。

- **不是工具** — 而是指揮與控制決策平台
- **不是腳本** — 而是軍事作戰框架
- **不是靜態** — OODA 循環驅動的動態調適
- **不只技術** — 戰略 + 戰術整合

## 架構
```
指揮官介面（Pencil.dev 設計 → Next.js 14 + React 18 + Tailwind v4）
         ↓
C5ISR 決策引擎（核心創新）
    ├─ MITRE ATT&CK 映射
    ├─ PentestGPT 戰術情報（Orient 階段）
    └─ OODA 循環控制器
         ↓
執行平台
    ├─ MITRE Caldera（標準執行）
    └─ Shannon（AI 自適應執行，選用）
```

## 目標使用者

- **軍方/政府**：任務級網路戰模擬
- **紅隊**：戰略規劃結合戰術執行
- **資安顧問**：指揮官級滲透測試管理
- **研究人員**：軍事框架應用於攻擊性資安

## 目前進度

**Phase 0：設計與架構** — 已完成

| 交付物 | 說明 |
|--------|------|
| 設計系統 | 56 個元件 + 32 個設計變數 |
| UI 設計 | 5 個畫面 + 1 個 3D 拓樸 Demo |
| 資料架構 | 13 Enum、12 Model、SQLite Schema、REST API |
| 專案結構 | Monorepo 佈局、各層職責 |

## 技術棧

| 層級 | 技術 |
|------|------|
| 後端 | Python 3.11 + FastAPI + Pydantic + SQLite |
| 前端 | Next.js 14 + React 18 + Tailwind CSS v4 |
| 3D 拓樸 | react-force-graph-3d + Three.js |
| 設計 | Pencil.dev（.pen） |
| 執行引擎 | MITRE Caldera（Apache 2.0） |
| AI 情報 | PentestGPT + Claude / GPT-4 |
| 容器化 | Docker + docker-compose |

## 文件

- [開發路線圖](docs/ROADMAP.md) — Phase 0-8 完整計畫
- [資料架構](docs/architecture/data-architecture.md) — 模型、Schema、API、種子資料
- [專案結構](docs/architecture/project-structure.md) — 目錄佈局、各層職責
- [AI 上下文](CLAUDE.md) — 完整專案上下文文件
