```
 █████╗ ████████╗██╗  ██╗███████╗███╗   ██╗ █████╗
██╔══██╗╚══██╔══╝██║  ██║██╔════╝████╗  ██║██╔══██╗
███████║   ██║   ███████║█████╗  ██╔██╗ ██║███████║
██╔══██║   ██║   ██╔══██║██╔══╝  ██║╚██╗██║██╔══██║
██║  ██║   ██║   ██║  ██║███████╗██║ ╚████║██║  ██║
╚═╝  ╚═╝   ╚═╝   ╚═╝  ╚═╝╚══════╝╚═╝  ╚═══╝╚═╝  ╚═╝
   S D K  ·  contract traits for hot-pluggable modules
```

# athena-sdk

[![License](https://img.shields.io/badge/license-Apache--2.0-green.svg)](LICENSE)
![Status](https://img.shields.io/badge/status-roadmap-orange.svg)

> 📦 **本目錄已併入 [`astroicers/Athena`](https://github.com/astroicers/Athena) 的 `sdk/` 目錄。**
> 這是 v0.1.0 的契約快照；正式版會在介面穩定後從主專案同步並發佈到 crates.io。
>
> **Athena 熱插拔模組的公開契約 SDK** — 用你的方式擴充 Athena 的決策層，**不需核心源碼**。

`athena-sdk` 是一組穩定的 Rust 契約 trait。依它實作，你就能為 [Athena](https://github.com/astroicers/Athena) 的自主 OODA 迴圈提供**可插拔模組**——而 Athena 的自主決策核心（`athena-core`）維持私有商業授權。

> 🗺️ **狀態：規劃中（roadmap）。** 契約邊界與版本策略已定案（Athena ADR-171）；本 crate 尚未發佈到 crates.io。歡迎先看設計、給回饋。
>
> ℹ️ **Phase 2（canonical）**：v0.1 契約型別**定義於本 crate**、零 `athena-*` 依賴——athena-sdk 是**可獨立編譯/發佈的葉節點**（ADR-171 D2）；`athena-types`（私有核心）反向 re-export 這些型別，核心的 `athena_types::X` 路徑不變。實際發佈（建公開 repo）仍待人類 + 法律定稿。

---

## 生態系

| 專案 | 是什麼 | 可見度 · 授權 |
|------|--------|--------------|
| [**Athena**](https://github.com/astroicers/Athena) | 產品門面 · 開源入口 | 🌐 公開 |
| **sdk/**（本目錄） | 模組契約 trait | 🌐 Apache-2.0 |
| [`tools/`](../tools/) | 工具 catalog | 🌐 Apache-2.0 |
| **athena-core** | 自主 OODA 商業引擎 · 洽談取得 | 🔒 BSL 1.1 |

---

## 你能實作哪些模組（v0.1 表面）

| 契約 trait | 你能換掉的能力 | 狀態 |
|---|---|---|
| `CapabilityScorer` | 能力/技術的評分邏輯 | ✅ v0.1 |
| `CapabilitySelector` | 從候選中選招的策略 | ✅ v0.1 |
| `DecisionEngine` | 整顆決策引擎 | v0.1（*完整整合＝roadmap*，需 WASM/MCP-over-protocol） |
| `FactExtractor` | 從工具輸出抽取 fact 的解析器 | 🗺️ roadmap（Phase 2） |
| `KnowledgeBase` | 攻防知識 / 劇本來源 | 🗺️ roadmap（Phase 2） |
| `SkillsLoader` | 技能 / playbook 載入器 | 🗺️ roadmap（Phase 2） |
| `LlmClient` | 可換的 AI 後端 | 🗺️ roadmap（Phase 2） |

roadmap 的四個 trait 目前住在核心 impl crate，需先做 contract/impl 拆分才能納入 SDK 表面。

---

## 快速開始（示意）

```toml
# Cargo.toml
[dependencies]
athena-sdk = "0.1"   # 規劃中
```

```rust
use athena_sdk::{AttackCapability, CapabilityScorer, ScoreContribution, SelectionContext};

pub struct MyScorer;

impl CapabilityScorer for MyScorer {
    fn name(&self) -> &str {
        "my_scorer"
    }

    /// 純函式、無 I/O、確定性 —— 這是 `CapabilityScorer` 契約的要求。
    fn score(&self, cap: &AttackCapability, ctx: &SelectionContext) -> ScoreContribution {
        // 你的評分邏輯。`weight` 為加權（加總）；`veto` 為硬排除；`reason` 進 selection trace。
        let _ = (cap, ctx);
        ScoreContribution {
            weight: 0.0,
            veto: false,
            reason: "my scoring logic".into(),
        }
    }
}
```

編好後，經信任夥伴流程整合進 Athena（in-repo 註冊）；`CapabilityScorer` / `CapabilitySelector` 等純函式模組未來可走 WASM 沙箱達成零核心源碼載入（roadmap）。

---

## Build / Test / Run

canonical 後 `athena-sdk` 是零 `athena-*` 依賴的獨立 crate，clone 就能編、測、跑：

```bash
cargo build                                  # 零 athena-* 依賴，獨立編譯
cargo test                                   # 契約 + 邊界(零 athena-*) + 表面見證測試
cargo run --example quiet_scorer             # 決策模組：否決「吵」的能力
cargo run --example weighted_scorer          # 多信號加權加總成單一分數
cargo run --example multi_factor_scorer      # 多因子：weight 可加總 vs veto 硬排除
cargo run --example composite_selector       # 自訂 CapabilitySelector：組合多個 scorer
cargo run --example decision_engine_concept  # DecisionEngine 契約形狀（illustrative）
```

`cargo run --example quiet_scorer` 的輸出：

```text
athena-sdk example — CapabilityScorer `quiet_preference`

  ✗ VETO  noisy_reverse_mod   vetoed: needs a noisy reverse channel
  ✓ keep  quiet_bind_mod      kept: quiet (no reverse channel)

→ 外部模組只依賴 athena-sdk（零 athena-*）就能決定「打哪個」。
```

## 三種可替換模組

依契約 trait 實作，你的模組就能替換 / 疊加進 Athena 的決策層——只依賴 `athena-sdk`、不需核心源碼。每個都有可跑的完整範例（`cargo run --example <name>`）：

| Trait | 你決定什麼 | 範例 |
|-------|-----------|------|
| `CapabilityScorer` | 單一候選的分數貢獻：`weight`（加總）、`veto`（硬排除）、`reason`（進 trace） | `quiet_scorer`、`weighted_scorer`、`multi_factor_scorer` |
| `CapabilitySelector` | 如何在候選中選一個——可組合多個 scorer、產出可解釋的 `SelectionTrace` | `composite_selector` |
| `DecisionEngine` | 整個 OODA 決策迴圈（可整體熱抽換）；完整執行整合需沙箱 / 協定化環境（roadmap） | `decision_engine_concept` |

上方「快速開始」示範了 `CapabilityScorer` 的最小實作；`composite_selector` 進一步示範第三方如何自訂整個選擇策略。編好的模組經信任夥伴流程組進選擇層（純函式 scorer/selector 未來可走 WASM 沙箱達成零核心源碼載入，roadmap）。

## 版本與相容

- **semver `0.x` 先行**：pre-1.0 期間契約可能迭代/破壞，穩定驗證後再承諾 `1.0`。
- Athena 核心 CI 對「已發布 SDK 版本」跑 **conformance 測試**——契約漂移會被抓到，保護你不被無聲破壞。

## 貢獻

歡迎 PR。合併需簽 **CLA**（讓貢獻能整合進 Athena 的商業核心）。詳見 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 授權

Apache License 2.0 — 見 [LICENSE](LICENSE)。

> ⚠️ Athena 為攻擊性資安平台；使用 SDK 建構的模組僅供**授權**用途，見 [Athena 使用限制](https://github.com/astroicers/Athena#授權與使用限制)。
