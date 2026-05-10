# SPEC: beta1-04 — athena-facts

| 欄位 | 內容 |
|------|------|
| **狀態** | `Pending` |
| **ADR** | ADR-101, ADR-111 |
| **ROADMAP task** | beta1-04 |

## Goal

實作 Fact 儲存庫，支援 CRUD 操作，使用 `(operation_id, trait_name, fact_value)` 唯一約束去重複。

## Done When

- [ ] `FactRepository` trait（`insert`, `list`, `exists`）
- [ ] `SqlxFactRepository` — sqlx 實作，使用 `INSERT ... ON CONFLICT DO NOTHING`
- [ ] `InMemoryFactRepository` — HashMap 實作，用於單元測試
- [ ] 單元測試：insert + list + deduplication（使用 InMemory 實作）
- [ ] 整合測試：`SqlxFactRepository` 對 k3s postgres

## Rollback Plan

`DELETE FROM facts WHERE operation_id = ?` 清除測試資料。
