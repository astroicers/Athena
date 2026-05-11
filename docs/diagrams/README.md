# Athena 2.0 — 設計圖索引

所有圖以 Mermaid 語法撰寫，可在 GitHub、VSCode（Markdown Preview Mermaid Support 擴充）、Obsidian 直接渲染。

| 檔案 | 內容 | 主要圖型 |
|------|------|---------|
| [ooda-pipeline-phase-context.md](ooda-pipeline-phase-context.md) | OODA 管道資料流、Operator Override 路徑、PhaseContext 結構、三層緩解計劃狀態 | Sequence / Graph / Gantt |
| [crate-dependency-map.md](crate-dependency-map.md) | 41 個 crate 依賴關係、ADR-101 鐵律視覺化、main.rs DI wiring 順序、MCP 協議流程、Circuit Breaker 狀態機 | Graph / Flowchart / Sequence / State |
| [api-routes-map.md](api-routes-map.md) | 所有 API 路由速查、POST /operations 參數、典型操作流程、認證說明 | Mindmap / Flowchart |

## 快速查閱指引

**「這個 fact 是怎麼進來的？」** → `ooda-pipeline-phase-context.md` 圖 1/2

**「operator_override 走哪條路？」** → `ooda-pipeline-phase-context.md` 圖 2

**「某個 crate 依賴什麼？」** → `crate-dependency-map.md` 圖 1

**「哪些 Crate 不能互相依賴？」** → `crate-dependency-map.md` 圖 2

**「main.rs 的初始化順序？」** → `crate-dependency-map.md` 圖 3

**「MCP 容器怎麼被呼叫的？」** → `crate-dependency-map.md` 圖 4

**「Circuit breaker 什麼時候開？」** → `crate-dependency-map.md` 圖 5

**「有哪些 API？」** → `api-routes-map.md`
