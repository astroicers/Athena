# [ADR-100]: Rust + Cargo Workspace 作為主要技術棧

| 欄位 | 內容 |
|------|------|
| **狀態** | `Accepted` |
| **日期** | 2026-05-10 |
| **決策者** | Athena Team |
| **取代** | ADR-001 |

## 背景

Athena 1.x 以 Python + FastAPI 建構，累積了 runtime 型別錯誤、模組邊界模糊、效能瓶頸等問題。需要一個能在編譯期就捕捉多數 bug 的技術棧。

## 決策

採用 **Rust**（edition 2021）+ **Cargo Workspace**（resolver = "2"）作為 Athena 2.0 的唯一實作語言。不引入 Python、Node.js 或任何其他語言。

## 理由

- Rust 型別系統在編譯期捕捉 90%+ 的 runtime 錯誤
- Cargo Workspace 提供清晰的 crate 邊界，強制模組隔離
- `tokio` 非同步執行時效能優於 Python asyncio
- 無 GC 暫停，適合低延遲的 OODA 決策循環

## 後果

- **正面**：零 runtime 型別錯誤、明確模組邊界、編譯時依賴圖
- **負面**：Rust 學習曲線陡、編譯時間較長
- **技術債**：部分 2.1 crate 目前為 stub，需後續實作

## 成功指標

| 指標 | 目標 | 驗證方式 |
|------|------|---------|
| cargo build --workspace | 全通過 | CI |
| Runtime panic 率 | < 0.1% | 生產監控 |

## 關聯

- 取代：ADR-001
- 參考：docs/ATHENA-2.0-架構設計.md §十五
