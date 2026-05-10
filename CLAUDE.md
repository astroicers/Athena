# Athena — AI 行為設定

> ASP v4.0 | 讀取順序：本檔案 → `.ai_profile` → `~/.claude/CLAUDE.md`（user-level 鐵則）
> Profile 邏輯與 ASP skills 詳見 `~/.claude/asp/profiles/` 與 `~/.claude/skills/asp/`

## 專案說明

Athena 2.0 是軍事等級 C5ISR + OODA 網路作戰平台，以全 Rust 重寫。
架構為 Cargo workspace（41 個 crate），實現決策引擎熱插拔、雙向 MCP、知識庫工具化、k3s 容器編排。

- **Branch**：`athena-2.0`（orphan，與 main 完全隔離）
- **入口**：`athena-workspace/src/main.rs`（DI wiring）
- **核心 API**：`GET /api/health`（port 58000）
- **資料庫**：k3s postgres（192.168.0.27:30543，見 `athena.toml`，已 gitignore）
- **架構文件**：`docs/ATHENA-2.0-架構設計.md`
- **ADR**：`docs/adr/ADR-100` ～ `ADR-112`（全部 Accepted）
- **ROADMAP**：`ROADMAP.yaml`（alpha-01 completed，其餘 pending）

## 特殊規則

- `athena.toml` 包含資料庫密碼，禁止 commit
- `.env` 已 gitignore，禁止 commit
- 執行引擎 crate 不能互相依賴（ADR-101 鐵律）
- 所有 SQL 只在 `athena-db` crate 中（ADR-101 鐵律）
- Draft ADR 狀態下禁止寫對應生產代碼（user-level 鐵則）
