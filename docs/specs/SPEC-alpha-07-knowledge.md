# SPEC: alpha-07 — athena-knowledge

| 欄位 | 內容 |
|------|------|
| **狀態** | `Completed` |
| **ADR** | ADR-101 |
| **ROADMAP task** | alpha-07 |

## Goal

提供從 `data/*.yaml` 載入技術庫和操作限制的功能，供 orient/decide 階段使用。

## Done When

- [x] `TechniqueLibrary::load(data_dir)` 從 YAML 目錄載入
- [x] `TechniqueEntry` 結構（id, name, category, mcp_tool, risk_level）
- [x] `OperationalConstraints` 結構（noise_level, allowed/denied_techniques）
- [x] `load_yaml_dir<T>` 泛型 helper
- [ ] 單元測試：空目錄不 panic，YAML 解析正確

## Rollback Plan

唯讀操作，直接 revert。
