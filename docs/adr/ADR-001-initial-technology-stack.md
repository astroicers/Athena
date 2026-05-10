# [ADR-001]: 初始技術棧選型（v1.x）

| 欄位 | 內容 |
|------|------|
| **狀態** | `Superseded by ADR-100` |
| **日期** | 2026-05-10 |
| **決策者** | Athena Team |

---

## 背景（Context）

Athena 1.x 採用 Python + FastAPI + Next.js 作為初始技術棧。
此 ADR 記錄該選型，但已被 Athena 2.0 的全 Rust 重寫決策取代。

---

## 決策（Decision）

Athena 1.x 選擇 Python / FastAPI / Next.js 作為快速驗證（PoC）技術棧。

---

## 後果（Consequences）

**正面影響：**
- 快速驗證 C5ISR + OODA 概念可行性
- 豐富的 Python AI/ML 生態

**負面影響 / 技術債：**
- Runtime 型別錯誤無法在編譯期捕捉
- 模組邊界模糊，WebSocket god-object 問題
- 決策引擎鎖死，無法熱插拔

**後續追蹤：**
- [x] 2026-05-10 — 已決定全 Rust 重寫（見 ADR-100）

---

## 關聯（Relations）

- 取代：（無）
- 被取代：**ADR-100**（Rust + Cargo Workspace 作為主要技術棧）
- 參考：docs/ATHENA-2.0-架構設計.md
