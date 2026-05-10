# [ADR-109]: `Arc<dyn Trait>` 熱插拔機制

| 欄位 | 內容 |
|------|------|
| **狀態** | `Accepted` |
| **日期** | 2026-05-10 |
| **決策者** | Athena Team |

## 背景

架構要求所有核心能力可在不重新編譯其他 crate 的情況下替換實作。需要一個 Rust idiom 來實現這點。

## 決策

使用 `Arc<dyn Trait>` + `async-trait` 作為熱插拔合約。每個可替換能力定義一個 `pub trait`，所有引用點持有 `Arc<dyn Trait>`。替換實作只需在 `athena-workspace/src/main.rs` 中修改一行 `Arc::new(ConcreteImpl)`，其餘代碼不變。

不使用 `dylib` / `.so` 動態連結，避免 ABI 不穩定問題。

## 後果

- 換一個實作 = 改 main.rs 一行
- 測試可用 `MockXxx` 替換任何依賴
- 靜態分發（`Arc<dyn Trait>`）有微小 vtable 開銷，可接受
