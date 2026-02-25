# Changelog

本專案遵循 [Keep a Changelog](https://keepachangelog.com/zh-TW/1.1.0/) 格式，
版本號遵循 [Semantic Versioning](https://semver.org/lang/zh-TW/)。

---

## [Unreleased]

> Phase 1–6 實作將記錄於此。

---

## [0.1.0] — 2026-02-25

### Phase 0：設計與架構（Design & Architecture）

#### Added
- 6 個 `.pen` 設計稿（Design System、Shell、C5ISR Board、MITRE Navigator、Mission Planner、Battle Monitor）
- 資料架構文件（13 Enum、12 Model、12 張 SQL Schema、35+ REST API、7 種 WebSocket 事件、種子資料）
- 專案結構文件（Monorepo 佈局、前後端分層職責）
- 開發路線圖（ROADMAP.md — Phase 0–8）
- 12 份 ADR（ADR-001 ~ ADR-012），涵蓋技術棧、OODA 引擎、授權隔離、前端架構等關鍵決策
- 10 份 SPEC（SPEC-001 ~ SPEC-010），涵蓋 Phase 1–6 全部實作規格
- ASP 框架（v1.2.0）整合：profiles、hooks、templates、Makefile targets
- CLAUDE.md v4（AI 助手完整上下文文件）
- `.env.example`（環境變數範本）
- `.gitignore`（Python、Node.js、SQLite、憑證檔排除）

#### Changed
- `.pen` 設計檔從根目錄搬入 `design/`
- `data-architecture.md` 反向更新：Technique.description、User seed data、ON DELETE CASCADE、/health endpoint
- `project-structure.md` 修正：TrafficStream.tsx 歸屬 topology/、設計檔路徑更新

---

[Unreleased]: https://github.com/astroicers/Athena/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/astroicers/Athena/releases/tag/v0.1.0
