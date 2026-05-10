# Athena 2.0

軍事等級 C5ISR + OODA 網路作戰平台（全 Rust 重寫）

> **Branch**: `athena-2.0` (orphan — 與 v1.x main branch 完全隔離)
> **狀態**: 2.0-alpha（`cargo build --workspace` 通過，k3s postgres 就緒）

## 快速開始

```bash
# 1. 複製設定範本
cp athena.toml.example athena.toml   # 填入 DB 連線字串
# 或直接設定環境變數
export ATHENA__DATABASE__URL="postgres://athena:password@192.168.0.27:30543/athena"

# 2. 執行資料庫 migration
make db-migrate

# 3. 啟動
cargo run -p athena-workspace

# 4. 驗證
curl http://localhost:58000/api/health
```

## 架構

```
外部 AI Agent (Claude)
    │ MCP 協定
    ▼
athena-mcp-server          ← Athena 對外暴露的 MCP Server
    │
    ▼
Athena Core
    ├── DecisionEngine      ← 可抽換（OODA / Kill Chain / Manual）
    │   ├── ObservePhase
    │   ├── OrientPhase     ← Claude LLM 分析
    │   ├── DecidePhase     ← 風險矩陣決策
    │   └── ActPhase        ← 執行引擎路由
    ├── athena-events       ← 型別化事件總線
    └── athena-api          ← axum HTTP API (port 58000)
         │
         ▼
k3s (192.168.0.27)
    ├── athena-system/postgres    ← PostgreSQL 16
    └── athena-tools/             ← 24 個 MCP 工具容器（beta2）
```

## Workspace 結構

```
crates/
├── athena-types/          # 零依賴領域型別（Layer 0）
├── athena-config/         # figment 設定載入
├── athena-telemetry/      # tracing + Prometheus
├── athena-db/             # sqlx PostgreSQL + migrations
├── athena-events/         # 型別化 broadcast 事件總線
├── athena-knowledge/      # YAML 知識庫載入器
├── athena-llm-client/     # Anthropic / OpenAI / Mock
├── athena-observe/        # OODA 觀察階段 trait
├── athena-orient/         # OODA 定向階段 trait
├── athena-decide/         # OODA 決策階段 trait
├── athena-act/            # OODA 行動階段 trait
├── athena-engine-ooda/    # DecisionEngine 實作
├── athena-api/            # axum HTTP server
├── athena-mcp-server/     # MCP Server（2.0-rc）
└── ...（共 41 個 crate）
athena-workspace/          # 主程式 binary（DI wiring）
```

## Make 指令

```bash
make build              # cargo build --workspace
make test               # cargo test --workspace
make fmt                # cargo fmt --all
make clippy             # cargo clippy -D warnings
make autopilot-status   # 查看 ROADMAP 進度
make k3s-status         # 查看 k3s pod 狀態
make db-migrate         # 執行 sqlx migrations
```

## 實作階段

| 階段 | 狀態 | 驗收條件 |
|------|------|---------|
| 2.0-alpha | **進行中** | `cargo build --workspace` ✅，k3s postgres ✅ |
| 2.0-beta1 | 待開始 | MOCK_LLM=true 完整 OODA 循環 |
| 2.0-beta2 | 待開始 | SSH + MCP 工具完整執行 |
| 2.0-beta3 | 待開始 | 知識庫可查詢，報告可產生 |
| 2.0-rc | 待開始 | 外部 Claude 透過 MCP 呼叫 Athena |

## ADR 索引

| ADR | 決策 | 狀態 |
|-----|------|------|
| ADR-100 | Rust + Cargo Workspace | Accepted |
| ADR-101 | 每個能力一個 crate | Accepted |
| ADR-102 | Headless API-only | Accepted |
| ADR-103 | Bearer Token 認證 | Accepted |
| ADR-104 | Anthropic via reqwest | Accepted |
| ADR-105 | tokio OODA scheduler | Accepted |
| ADR-106 | 型別化事件總線 | Accepted |
| ADR-107 | Orphan branch 策略 | Accepted |
| ADR-108 | Constructor injection | Accepted |
| ADR-109 | Arc\<dyn Trait\> 熱插拔 | Accepted |
| ADR-110 | russh SSH 後端 | Accepted |
| ADR-111 | sqlx 編譯期檢查延至 rc | Accepted |
| ADR-112 | DecisionEngine trait | Accepted |

完整架構說明：[docs/ATHENA-2.0-架構設計.md](docs/ATHENA-2.0-架構設計.md)
