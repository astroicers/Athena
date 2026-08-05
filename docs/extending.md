# 擴充教學

Athena 對外提供**兩個**公開擴充點，讓你不改核心就能加東西：

1. **自訂決策 scorer**——用 [`athena-sdk`](https://github.com/astroicers/athena-sdk) 的契約 trait，插一段自己的評分邏輯進「打哪招」的選擇層。
2. **自訂工具 catalog**——用 [`athena-tools`](https://github.com/astroicers/athena-tools) 的 manifest 規格，發布一個 MCP 工具讓 Athena 自動調度。

> 對外公開擴充點**就這兩個**。深入指南分別住在兩個 companion repo（本文交叉連結），這裡只給最短可用路徑。

---

## Hook 1 — 自訂決策 scorer（`athena-sdk`）

Athena 在挑「下一步用哪個攻擊能力」時，會把所有候選丟給一串 **scorer** 評分、加總後排序。你可以實作契約 trait `CapabilityScorer`，把自己的偏好（例如「偏好安靜、否決會回連的吵雜手法」）加進這串評分器——**不需核心源碼**。

### 契約

```rust
pub trait CapabilityScorer: Send + Sync {
    /// 給 trace 用的穩定名稱（如 "match_specificity"）。
    fn name(&self) -> &str;

    /// 對一個候選能力評分。純函式、確定性。
    fn score(&self, cap: &AttackCapability, ctx: &SelectionContext) -> ScoreContribution;
}
```

`score()` 回傳一個 `ScoreContribution`：

```rust
pub struct ScoreContribution {
    pub weight: f64,     // 加成權重（可正可負）
    pub veto:   bool,    // 硬排除——不是負權重，是直接淘汰
    pub reason: String,  // 人類可讀理由，會進 trace
}
```

### 可跑範例

以下範例**只依賴 `athena-sdk`**（零核心 crate），否決任何需要吵雜 reverse 回連的能力：

```rust
use athena_sdk::{AttackCapability, CapabilityScorer, ScoreContribution, SelectionContext};

/// 偏好「安靜」的能力：否決任何需要吵雜 reverse 回連通道的手法。
struct QuietPreference;

impl CapabilityScorer for QuietPreference {
    fn name(&self) -> &str {
        "quiet_preference"
    }

    fn score(&self, cap: &AttackCapability, _ctx: &SelectionContext) -> ScoreContribution {
        ScoreContribution {
            weight: 0.0,
            veto: cap.needs_channel,
            reason: if cap.needs_channel {
                "vetoed: needs a noisy reverse channel".into()
            } else {
                "kept: quiet (no reverse channel)".into()
            },
        }
    }
}
```

`athena-sdk` repo 內附這支範例的完整可執行版本（含 `main()`）：

```bash
cargo run --example quiet_scorer
```

### 整合

你的 scorer 只依賴公開的 `athena-sdk`（`CapabilityScorer` 契約）就能寫完、單獨編譯。要把它接進 Athena 的選擇層，走**信任夥伴 / in-repo 註冊**流程：把你的 scorer 交給 Athena 的 wiring，由它**附加**在內建評分器之上（opt-in，不會自動汙染預設選擇鏈）。這個合成步驟在 Athena 端完成——你**不需要**持有核心源碼，只要交付一個實作了公開契約 trait 的 scorer 即可。

> ℹ️ 上線前請**自行 clamp 第三方 scorer 的 `weight`**，避免單一評分器壓過其餘、扭曲決策。

📖 **深入教學**（型別語意、契約穩定性、更多範例）→ [`athena-sdk` repo](https://github.com/astroicers/athena-sdk)（scorer 貢獻指南）。

---

## Hook 2 — 自訂工具 catalog（`athena-tools`）

Athena 的偵查 / 執行工具是一組 MCP 容器。你可以**加自己的工具而不改核心**：寫一份 manifest 描述工具的能力，Athena 啟動時把它併進工具登錄表，之後由 ORIENT 階段自動發現與調度。

### Manifest 格式（`athena-tool.toml`）

```toml
manifest_version = "1"

tool_name   = "example_query"
container   = "example-osint"
port        = 9130
techniques  = ["T1596"]          # 真實 MITRE ATT&CK ID
description = "Targetless OSINT lookup (example community tool)"
phase       = "observe"          # observe | act | both
os_hint     = "any"              # linux | windows | any（選填）
params_hint = "domain=<name>"    # 選填
```

- `techniques`：真實 MITRE ATT&CK ID（能力映射）。
- `phase`：ORIENT 的提示——`observe`（偵查 / 列舉 / 查詢）、`act`（執行）、或 `both`。
- 範例容器（`Dockerfile` + `server.py`，MCP 回 `{"facts":[…]}`）見 `athena-tools` repo 的 `examples/my-tool/`。
- 本 repo 也附一份會通過 schema 驗證的 manifest：[`examples/my-tool/athena-tool.toml`](../examples/my-tool/athena-tool.toml)（CI 會對它跑 schema 驗證）。

### 載入

把你部署好的 manifest 目錄，指給設定欄位 `tool_manifest_dirs`（一組目錄字串）：

```toml
# athena.toml
[mcp]
tool_manifest_dirs = ["/opt/athena/my-tools"]
```

- **空陣列 = no-op**：不列任何目錄時，工具登錄表與內建版本完全一致。
- 併入時以 `tool_name` 為鍵；與內建工具同名者會被拒絕（內建優先），壞掉的 manifest 會被跳過並記警告（fail-closed）。
- 這是 **operator opt-in**：工具只有在你明確把目錄列進設定後才會被載入。

📖 **深入教學**（schema 驗證 CI、`docker build` + 起 MCP、per-tool 審核流程）→ [`athena-tools` repo](https://github.com/astroicers/athena-tools)（工具貢獻指南）。

---

## 就這兩個

以上兩個是 Athena 目前對外的公開擴充點，教學也只涵蓋這兩個。核心的自主 OODA 引擎、合規閘、決策實作維持私有商業授權，不在公開擴充面。
