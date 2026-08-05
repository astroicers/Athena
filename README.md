```
 █████╗ ████████╗██╗  ██╗███████╗███╗   ██╗ █████╗
██╔══██╗╚══██╔══╝██║  ██║██╔════╝████╗  ██║██╔══██╗
███████║   ██║   ███████║█████╗  ██╔██╗ ██║███████║
██╔══██║   ██║   ██╔══██║██╔══╝  ██║╚██╗██║██╔══██║
██║  ██║   ██║   ██║  ██║███████╗██║ ╚████║██║  ██║
╚═╝  ╚═╝   ╚═╝   ╚═╝  ╚═╝╚══════╝╚═╝  ╚═══╝╚═╝  ╚═╝
        C5ISR · OODA · Autonomous Cyber Operations
```

# Athena

[![Core License](https://img.shields.io/badge/core-BSL%201.1-blue.svg)](#授權與使用限制)
[![SDK & Tools](https://img.shields.io/badge/sdk%20%26%20tools-Apache--2.0-green.svg)](#生態系open-core)
[![Star on GitHub](https://img.shields.io/github/stars/astroicers/Athena?style=social)](https://github.com/astroicers/Athena)

> **C5ISR + OODA — 會自己想的自主網路作戰平台**
>
> Military-Grade Autonomous Cyber Operations — C5ISR Situational Awareness × OODA Decision Loop

Athena 是一套以 **OODA 決策迴圈**驅動的自主攻擊平台。在 scope / opsec / RoE 三重合規閘下，它自主完成偵查 → 突破 → 拿 shell → 提權 → 橫移 → 全網域淪陷——**下一步打哪台、用哪招，是迴圈自己決定的，不是人工逐步下令**。外部 AI（如 Claude）可經 MCP 指揮它；決策腦可換成地端本地 LLM，整套可 **air-gap** 部署。

> ⚠️ **授權使用限制**：Athena 是**攻擊性**網路作戰平台，**僅限**用於你擁有、或已取得書面授權的系統（授權紅隊演練 / CTF / 授權靶場 / 學術研究 / 資安教育）。未經授權對第三方系統使用屬違法。詳見文末〈授權與使用限制〉。

---

## 文件導覽

| 文件 | 內容 |
|------|------|
| [HTTP API 參考](docs/http-api.md) | 對外穩定端點：operations / OODA phases / scheduler / facts / kb / vuln / campaign / report / status |
| [LLM 配置指南](docs/llm-config.md) | 三種可選後端（hosted / 本地 / mock）與環境變數選擇 |
| [擴充教學](docs/extending.md) | 兩個公開擴充點：自訂決策 scorer、自訂工具 catalog |
| [Demo Walkthrough](docs/demo-walkthrough.md) | 端到端跑一次自主 OODA 迭代（授權範圍） |

---

## 一次「自主 OODA 迭代」長怎樣

<!-- demo 影片/gif 待後補到 assets/；下方為去識別化的概念流程，非真實環境值。 -->

```
Observe   偵查到某主機開 445/tcp、samba 3.0.20                    ← 態勢感知
Orient    AI 研判：該版本有 usermap_script RCE，建議 exploit      ← 決策腦（LLM，逾時有確定性 fallback）
          並產出風險評分與 opsec 噪音估計
Decide    合規閘：目標在 scope 內、opsec 預算夠、RoE 允許 → 放行  ← 三重硬閘（界外一律擋）
Act       執行 → 拿到 shell → 抽取新 fact（是否 root？有無憑證？）  ← 執行 + 觀測回饋
  ↺       迴圈用「新 fact」決定下一台打哪、下一招用什麼——人沒有逐步下令
```

**重點不是「會用某個 exploit」，而是「下一步是迴圈自己決定的」。** 這是 Athena 與傳統逐步下令工具的根本差異。→ 想實際跑一遍見 [Demo Walkthrough](docs/demo-walkthrough.md)。

---

## 生態系（open-core）

Athena 走**開放核心**——自主決策核心為商業授權（私有），周邊接口與工具開源：

| 專案 | 是什麼 | 你能做什麼 · 從哪開始 | 授權 |
|------|--------|----------------------|------|
| **Athena**（本 repo） | 產品門面 · 生態入口 · 文件 | 了解定位與功能、找到上手入口 | — |
| [**athena-sdk**](https://github.com/astroicers/athena-sdk) | 模組契約 trait——用你的方式實作熱插拔模組（評分器 / 選擇器 / 可換的 AI 後端），**不需核心源碼** | 寫一個決策模組 → 見 [擴充教學](docs/extending.md) | Apache-2.0 |
| [**athena-tools**](https://github.com/astroicers/athena-tools) | 工具 catalog + manifest 規格 + 範例容器——發布 MCP 工具給 Athena **自動調度、加工具不改核心** | 加一個工具 → 見 [擴充教學](docs/extending.md) | Apache-2.0 |
| **athena-core** | 自主 OODA 商業引擎（模組化 Rust workspace）· **私有，洽談取得** | POC / 商業評估 → 洽談 | BSL 1.1 |

> 🗺️ `athena-sdk` / `athena-tools` 已公開發佈、可獨立編譯；核心的自主 OODA 引擎維持私有商業授權。

---

## 上手（Quickstart）

開源周邊可以直接動手；核心走洽談。完整教學見 [擴充教學](docs/extending.md)。

### ① 用 `athena-sdk` 寫一個決策模組

實作契約 trait，就能把你的決策邏輯插進 Athena 的選擇層——**不需核心源碼**：

```rust
use athena_sdk::{AttackCapability, CapabilityScorer, ScoreContribution, SelectionContext};

/// 偏好「安靜」——否決任何需要吵雜 reverse 回連的攻擊能力。
struct QuietPreference;

impl CapabilityScorer for QuietPreference {
    fn name(&self) -> &str { "quiet_preference" }

    // 純函式、確定性——契約要求
    fn score(&self, cap: &AttackCapability, _ctx: &SelectionContext) -> ScoreContribution {
        ScoreContribution {
            weight: 0.0,
            veto: cap.needs_channel,               // 需要回連的（較吵）直接否決
            reason: "prefer quiet capabilities".into(),
        }
    }
}
```

→ 可跑範例與貢獻指南見 [`athena-sdk`](https://github.com/astroicers/athena-sdk)（`cargo run --example quiet_scorer`）。

### ② 用 `athena-tools` 加一個工具

寫一份 manifest，Athena 就能**自動調度你的 MCP 工具、加工具不改核心**：

```toml
# my-tool/athena-tool.toml
manifest_version = "1"
tool_name   = "example_query"
container   = "example-osint"
port        = 9130
techniques  = ["T1596"]          # MITRE ATT&CK
description = "Targetless OSINT lookup"
phase       = "observe"
```

流程：**發布（PR）→ 審核（manifest + 容器）→ operator opt-in 部署 → ORIENT 自動發現/調度**。→ schema 與範例容器見 [`athena-tools`](https://github.com/astroicers/athena-tools)。

### ③ 試 `athena-core`

核心為商業授權；POC 試點 / 授權靶場實測 / 合作 → 見〈如何取得 / 洽談〉。

---

## 為何選擇 Athena？

傳統工具聚焦「**如何滲透**」；Athena 聚焦「**如何自主指揮**」。

| 傳統工具（Cobalt Strike / Metasploit …） | Athena |
|---|---|
| 操作員逐步下令 | **OODA 迴圈自主決定下一步** |
| 靜態腳本 / playbook | 動態迭代決策（Orient 由 LLM 驅動 + 逾時確定性 fallback） |
| 以工具為中心 | 以 C5ISR 框架 + 決策為中心 |
| 靠流程規範控管 | **三重合規閘焊進執行路徑，界外一律擋** |
| 多依賴雲 | 本地 LLM + 地端部署，**可 air-gap** |

---

## 能力

- **自主 OODA 攻擊迴圈** — 從偵查到全網域淪陷，全程迴圈自決、人不逐步下令；可觀測、可打斷、可重試。
- **雙向 MCP** — 對外當 MCP server 受外部 AI 指揮；對內驅動資安工具容器。
- **三重合規閘 + HITL** — scope（CIDR 硬閘）/ opsec（噪音預算）/ policy（RoE）焊進執行路徑；高風險 / 可疑蜜罐強制人類審核。
- **全程 redaction** — 憑證 / 密碼以型別系統強制不落 log、不落 DB。
- **決策引擎熱插拔 · 知識庫工具化 (RAG) · 多智能體 campaign 編排 · 自主多主機 pivot**。
- **air-gap 主權** — 地端本地 LLM 當決策腦，不依賴外部雲。

> 能力於**授權靶場**經 live 端到端驗證（含完整網域淪陷）。商業評估與 POC 可安排實測；細節洽談取得。

---

## 架構（概念）

```
        C5ISR 態勢感知（持續監控）
                  │
   OODA 迴圈（迭代決策）
   Observe → Orient(AI) → Decide(風險閘) → Act  ↺
                  │
   Compliance 合規層（scope / opsec / policy 硬閘 · HITL）
```

- **模組化 Rust workspace**：每個能力一個 crate、對外只暴露一個 trait 契約（契約與實作分離）——這也是 `athena-sdk` 能把契約開源、實作留私有的基礎。
- **雙向 MCP + 決策引擎熱插拔**：可被上游指揮系統納管、也能納管你的工具；換戰法不重寫。
- **治理即型別**：三閘與 Secret 遮蔽是編譯期 / 建構期焊死的守衛，非事後稽核。

---

## 如何取得 / 洽談

- **商業授權 / POC 試點 / 合作**：`azz093093.830330@gmail.com`
- **開源周邊**（SDK / 工具 catalog）：[`athena-sdk`](https://github.com/astroicers/athena-sdk) · [`athena-tools`](https://github.com/astroicers/athena-tools)。

---

## v1.x（歷史）

本專案 v1.x 為 **Python PoC**（C5ISR + OODA 的概念驗證），已封存於 [`v1-archive`](https://github.com/astroicers/Athena/tree/v1-archive) 分支。目前產品為 **v2 全 Rust 自主核心**（`athena-core`，私有）。

---

## 授權與使用限制

### 授權
- **核心（athena-core）**：Business Source License 1.1 — 非商業（個人 / 學術 / 教育 / CTF）免費、商業需另行取得授權、Change Date 後自動轉 Apache License 2.0。
- **周邊（athena-sdk / athena-tools）**：Apache License 2.0。

### Authorized Use Only
本軟體為**攻擊性**資安工具，**僅供**：你**擁有**的系統，或已取得資產所有者**書面授權**（Statement of Work / Rules of Engagement）的紅隊演練；以及 CTF / 授權靶場 / 學術研究 / 資安教育。**嚴禁**未經授權對任何第三方系統、網路或資料進行掃描、入侵、橫移或資料外洩。使用者須自負遵守其所在司法管轄區法律之全部責任。作者與授權人對任何未經授權或違法之使用**不承擔任何責任**。

### Dual-Use / Export Control
本軟體具**雙用途（dual-use）**性質，可能受各國出口管制與制裁法規（例如美國 EAR、Wassenaar Arrangement 之「入侵軟體 intrusion software」條款，及當地等同法規）規範。**取得、使用、再散布或跨境傳輸前，使用者須自行確認並遵守適用之出口管制與制裁法規。**

### 免責
軟體按「現狀（AS IS）」提供，不含任何明示或默示之擔保（包含但不限於適售性、特定用途適用性、非侵權）。
