# [ADR-101]: 每個能力一個 Crate + 依賴規則

| 欄位 | 內容 |
|------|------|
| **狀態** | `Accepted` |
| **日期** | 2026-05-10 |
| **決策者** | Athena Team |

## 背景

需要明確的模組邊界以防止循環依賴、god-object、以及跨層呼叫問題。

## 決策

- 每個功能能力對應一個獨立 crate
- 10 層依賴階層，嚴格單向（低層 → 高層，禁止反向）
- 每個 crate 對外只暴露一個 `pub trait` 作為公開合約

## 鐵律

```
❌ 決策引擎層 不能依賴 athena-api / athena-mcp-server
❌ 基礎層 不能依賴任何業務 crate
❌ 執行引擎 crate 不能互相依賴
❌ 除 athena-db 外，任何 crate 不能直接寫 SQL
```

## 關聯

- 取代：ADR-002（隱含）
- 參考：docs/ATHENA-2.0-架構設計.md §十三
