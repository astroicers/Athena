# SPEC: alpha-03 — athena-config

| 欄位 | 內容 |
|------|------|
| **狀態** | `Completed` |
| **ADR** | ADR-108 |
| **ROADMAP task** | alpha-03 |

## Goal

實作設定載入器，支援 TOML 檔案 + 環境變數覆蓋，提供型別安全的 `AthenaConfig` struct。

## Done When

- [x] `AthenaConfig::load()` 從 `athena.toml` + `ATHENA__*` 環境變數讀取設定
- [x] `ServerConfig`、`DatabaseConfig`、`LlmConfig`、`McpConfig` 四個子結構
- [x] `load_or_default()` fallback（mock_mode = true）
- [ ] 單元測試：從環境變數覆蓋設定

## Rollback Plan

無副作用，直接 revert。
