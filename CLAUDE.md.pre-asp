# CLAUDE.md — Athena 專案 v4

> **AI 助手專案上下文文件**
>
> 本文件為 AI 助手（Claude、ChatGPT 等）提供 Athena 專案的完整上下文，
> 涵蓋架構、設計哲學與技術決策。
>
> **狀態**：POC 階段 — 個人部署，軍事顧問定位
> **核心棧**：PentestGPT（情報）+ Caldera（執行）

---

## 目錄

1. [專案概覽](#專案概覽)
2. [核心哲學](#核心哲學)
3. [架構](#架構)
4. [元件角色](#元件角色)
5. [授權策略](#授權策略)
6. [技術棧](#技術棧)
7. [整合策略](#整合策略)
8. [自動化模式](#自動化模式)
9. [開發路線圖](#開發路線圖)
10. [關鍵概念](#關鍵概念)
11. [POC 階段限制](#poc-階段限制)
12. [AI 助手指南](#ai-助手指南)

---

## 專案概覽

### Athena 是什麼？

**Athena** 是一套 AI 驅動的 C5ISR（Command, Control, Communications, Computers, Cyber, Intelligence, Surveillance, Reconnaissance）網路作戰指揮平台。它**不是**又一個滲透測試工具——而是一套**軍事級指揮與決策平台**，以 AI 輔助的戰術規劃來編排執行引擎。

### 定位
```
傳統工具                    Athena
─────────────────         ────────────────────
「如何滲透」           →     「如何指揮」
操作員控制台           →     指揮官儀表板
技術執行               →     戰略決策
靜態腳本               →     動態 OODA 循環
以工具為中心           →     以框架為中心
```

### 核心差異化

- **不是工具，而是指揮平台**：將滲透測試從戰術操作提升至戰略指揮
- **C5ISR 框架**：將軍事作戰框架應用於網路戰
- **MITRE ATT&CK 原生**：基於 MITRE Caldera 深度整合
- **AI 輔助決策**：整合 PentestGPT 提供戰術情報（Orient 階段）
- **OODA 驅動**：透過 Observe → Orient → Decide → Act 循環動態調適
- **多引擎支援**：指揮 Caldera（標準）和選用 Shannon（AI 自適應）

---

## 核心哲學

### 軍事類比
```
Athena 之於滲透測試，就如同空軍指揮中心之於戰鬥機。

PentestGPT = 軍事情報官（分析、建議）
Caldera    = F-16 戰鬥機中隊（成熟、標準化、可靠）
Shannon    = F-35 戰鬥機（先進、AI 能力、自適應）— 選用
Athena     = 指揮中心（決定戰略及部署哪些資產）
```

### 設計原則

1. **指揮官視角**：使用者以戰略意圖思考，而非技術指令
2. **框架優先於工具**：C5ISR 提供結構，工具提供能力
3. **決策優先於執行**：聚焦「做什麼」而非「怎麼做」
4. **人機協作**：AI 輔助（PentestGPT）、人類決策（指揮官）、引擎執行（Caldera/Shannon）
5. **動態調適**：OODA 循環實現即時戰術調整

### 三層智慧架構
```
┌─────────────────────────────────────────────────┐
│  戰略智慧（Strategic Intelligence）             │
│  └─ PentestGPT：「為什麼選這個戰術？」          │
│     角色：思考、分析、建議                       │
│     輸出：附帶推理的戰術選項                     │
└─────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────┐
│  決策智慧（Decision Intelligence）              │
│  └─ Athena 引擎：「該用哪個執行引擎？」         │
│     角色：路由、編排、排序                       │
│     輸出：執行計畫                               │
└─────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────┐
│  執行智慧（Execution Intelligence）             │
│  ├─ Caldera：標準 MITRE 技術                     │
│  └─ Shannon：AI 自適應執行（選用）               │
│     角色：執行、回報                             │
│     輸出：攻擊結果                               │
└─────────────────────────────────────────────────┘
```

---

## 架構

### 高層架構（POC 配置）
```
┌─────────────────────────────────────────────────────┐
│              Pencil.dev UI 層                       │
│  （指揮官介面 — 視覺化指揮儀表板）                  │
│                                                      │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌─────────┐     │
│  │ C5ISR  │ │ MITRE  │ │ Mission│ │ Battle  │     │
│  │ Board  │ │Navigator│ │Planner │ │Monitor  │     │
│  └────────┘ └────────┘ └────────┘ └─────────┘     │
└───────────────────────┬─────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────┐
│         Athena 指揮與情報層                         │
│         （核心創新 — 你的智慧財產）                  │
│                                                      │
│  ┌──────────────────────────────────────────────┐  │
│  │  戰略決策引擎                                │  │
│  │  ├─ C5ISR 框架映射器                         │  │
│  │  ├─ MITRE ATT&CK 編排器                      │  │
│  │  ├─ OODA 循環控制器                          │  │
│  │  └─ 任務優先順序管理器                       │  │
│  └──────────────────────────────────────────────┘  │
│                                                      │
│  ┌──────────────────────────────────────────────┐  │
│  │  PentestGPT 情報層（核心）                    │  │
│  │  ════════════════════════════════════════    │  │
│  │  角色：OODA Orient 階段                       │  │
│  │  授權：MIT（安全整合）                        │  │
│  │                                               │  │
│  │  ├─ 態勢分析                                 │  │
│  │  ├─ MITRE 技術推薦                            │  │
│  │  ├─ 戰術推理                                 │  │
│  │  ├─ 風險評估                                 │  │
│  │  └─ 多選項方案產生                           │  │
│  │                                               │  │
│  │  LLM 後端：                                   │  │
│  │  ├─ 主要：Claude（Anthropic）— 推理能力      │  │
│  │  └─ 備用：GPT-4（OpenAI）                    │  │
│  └──────────────────────────────────────────────┘  │
│                                                      │
│  ┌──────────────────────────────────────────────┐  │
│  │  執行引擎抽象層                              │  │
│  │  ├─ 任務路由邏輯                             │  │
│  │  ├─ Caldera 客戶端（API 呼叫）✅ 核心        │  │
│  │  ├─ Shannon 客戶端（API 呼叫）⚠️ 選用        │  │
│  │  └─ 結果聚合與標準化                         │  │
│  └──────────────────────────────────────────────┘  │
└───────────────────────┬─────────────────────────────┘
                        │
                  API 邊界
                （授權隔離防火牆）
                        │
          ┌─────────────┴──────────────┐
          ↓                            ↓
┌──────────────────┐         ┌──────────────────┐
│ ✅ Caldera       │         │ ⚠️ Shannon       │
│  （POC 核心）    │         │  （選用）        │
│                  │         │                  │
│  Apache 2.0      │         │  AGPL-3.0        │
│  （MITRE 官方）  │         │  （獨立運行）    │
│                  │         │                  │
│  - MITRE 原生    │         │  - AI 推理       │
│  - 標準化        │         │  - 自主執行      │
│  - 可靠          │         │  - 自適應        │
│  - POC 就緒      │         │  - 進階展示      │
└──────────────────┘         └──────────────────┘
```

### 資料流（OODA 循環與 PentestGPT）
```
┌─────────────────────────────────────────┐
│         Observe（觀察）                 │
│  ├─ 使用者輸入戰略意圖                 │
│  ├─ Caldera Agent 回報結果             │
│  ├─ 情報資料庫更新                     │
│  └─ 環境狀態變化                       │
└──────────────┬──────────────────────────┘
               ↓
┌──────────────▼──────────────────────────┐
│         Orient（導向）⭐ PentestGPT     │
│  ════════════════════════════════════   │
│  PentestGPT 在此發揮核心價值：          │
│                                          │
│  1. 分析當前態勢                        │
│  2. 考量已完成的技術                    │
│  3. 評估失敗與障礙                      │
│  4. 產生 3 個戰術選項                   │
│  5. 解釋每個選項的推理                  │
│  6. 推薦最佳路徑                        │
│                                          │
│  輸出範例：                              │
│  ┌────────────────────────────────────┐ │
│  │ 「當前：已取得初始存取              │ │
│  │                                    │ │
│  │ 選項 1：T1003.001（LSASS）        │ │
│  │   推理：已有 Admin 權限            │ │
│  │   風險：中（EDR 可能偵測）         │ │
│  │   引擎：Caldera（標準）            │ │
│  │                                    │ │
│  │ 選項 2：T1134（Token 操作）        │ │
│  │   推理：較隱蔽的方法              │ │
│  │   風險：低                         │ │
│  │   引擎：Shannon（自適應）          │ │
│  │                                    │ │
│  │ 推薦：選項 1」                     │ │
│  └────────────────────────────────────┘ │
└──────────────┬──────────────────────────┘
               ↓
┌──────────────▼──────────────────────────┐
│         Decide（決策）                   │
│  ├─ Athena 評估 PentestGPT 建議        │
│  ├─ 考量作戰限制條件                    │
│  ├─ 選擇技術                            │
│  ├─ 路由至執行引擎：                    │
│  │   ├─ Caldera（標準技術）             │
│  │   └─ Shannon（複雜場景）             │
│  └─ 更新作戰計畫                        │
└──────────────┬──────────────────────────┘
               ↓
┌──────────────▼──────────────────────────┐
│         Act（行動）                      │
│  ├─ Caldera/Shannon 透過 API 執行       │
│  ├─ Agent 執行攻擊操作                  │
│  ├─ 結果收集至情報資料庫                │
│  └─ 回饋循環回到 Observe ──────────────┘
```

---

## 元件角色

### 關鍵：理解 PentestGPT vs Shannon vs Caldera
```
┌──────────────────────────────────────────────────────────┐
│  元件比較矩陣                                            │
├──────────────────────────────────────────────────────────┤
│                                                           │
│  PentestGPT（情報層）                                    │
│  ═══════════════════════════════════                     │
│  功能：         思考、分析、建議                          │
│  輸出：         文字建議與推理                            │
│  C5ISR 角色：   情報（Intelligence）                     │
│  OODA 角色：    Orient（關鍵階段）                       │
│  執行攻擊：     ❌ 否（純顧問角色）                      │
│  授權：         MIT ✅ 可安全整合                         │
│  資源需求：     極少（僅 LLM API 呼叫）                  │
│  POC 狀態：     ✅ 必要 — 核心差異化元件                  │
│                                                           │
│  互動範例：                                              │
│  輸入：「透過 T1068 提權失敗」                           │
│  輸出：「可能有 EDR。建議：                              │
│         1. T1548.002（UAC 繞過）— 較低噪音               │
│         2. T1134（Token 操作）— 需要 SeDebug             │
│         建議：先透過 Caldera 嘗試方案 1」                │
│                                                           │
├──────────────────────────────────────────────────────────┤
│                                                           │
│  Caldera（標準執行引擎）                                 │
│  ════════════════════════════════════                    │
│  功能：         執行 MITRE 技術                           │
│  輸出：         攻擊結果、收集的情報                      │
│  C5ISR 角色：   Cyber（執行）                            │
│  OODA 角色：    Act                                      │
│  執行攻擊：     ✅ 是（預定義的 abilities）               │
│  授權：         Apache 2.0 ✅ MITRE 官方                  │
│  資源需求：     ~2GB RAM, 2 CPU cores                     │
│  POC 狀態：     ✅ 必要 — 主要執行器                      │
│                                                           │
├──────────────────────────────────────────────────────────┤
│                                                           │
│  Shannon（AI 驅動執行引擎）                              │
│  ══════════════════════════════════════                 │
│  功能：         AI 驅動的自適應執行                       │
│  輸出：         攻擊結果 + AI 推理                        │
│  C5ISR 角色：   Cyber（進階執行）                        │
│  OODA 角色：    Act（含內部 Orient）                     │
│  執行攻擊：     ✅ 是（自主 + 自適應）                    │
│  授權：         AGPL-3.0 ⚠️ 僅 API 整合                  │
│  資源需求：     ~2GB RAM, 2 CPU cores                     │
│  POC 狀態：     ⚠️ 選用 — 進階功能                       │
│                                                           │
│  注意：seed data 中 Mission Step #4 使用 Shannon 作為    │
│  demo placeholder，實際 POC 可 fallback 到 Caldera。     │
│                                                           │
└──────────────────────────────────────────────────────────┘
```

### 何時使用哪個元件
```
場景導向選擇指南：

┌─────────────────────────────────────────────────────────┐
│  場景 1：規劃攻擊策略                                   │
├─────────────────────────────────────────────────────────┤
│  使用：PentestGPT                                        │
│  原因：需要戰術分析與建議                                │
│                                                          │
│  使用者：「如何取得 Domain Admin？」                     │
│  PentestGPT：「分析當前態勢...                          │
│               建議 TA0006 → TA0004 → TA0008             │
│               從 T1003.001 開始，因為...」              │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│  場景 2：標準 MITRE 技術執行                             │
├─────────────────────────────────────────────────────────┤
│  使用：Caldera                                           │
│  原因：已知環境、標準技術                                │
│                                                          │
│  Athena：對 192.168.1.10 執行 T1003.001                 │
│  Caldera：[執行標準 LSASS dump ability]                 │
│           回傳：萃取 10 組憑證                           │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│  場景 3：自適應執行（未知防禦）                          │
├─────────────────────────────────────────────────────────┤
│  使用：Shannon（若可用）                                 │
│  原因：需要 AI 適應未知防禦                              │
│                                                          │
│  Athena：提權（環境未知）                                │
│  Shannon：[AI 分析] → 偵測到 EDR                        │
│           [自適應] → 改用 LOLBAS 技術                    │
│           回傳：透過替代方法成功                          │
└─────────────────────────────────────────────────────────┘
```

### 關鍵洞察：PentestGPT 無法被取代
```
❌ 錯誤心智模型：
「Shannon 是 AI，所以可以取代 PentestGPT」

✅ 正確理解：
PentestGPT = 戰略顧問（解釋「為什麼」）
Shannon    = 精銳士兵（找出「如何做」）

兩者都使用 AI，但層級不同：
├─ PentestGPT：後設層級戰術推理
│   「根據這些情報，最佳方法是什麼？」
│   可被質疑：「為什麼推薦這個？」
│   提供多個選項供人類選擇
│
└─ Shannon：執行層級自適應
    「這個防禦擋住我了，換另一種方法」
    黑箱操作
    自主做出決策

類比：
├─ PentestGPT = 將軍的參謀長（戰略建議）
└─ Shannon = 特種部隊（戰術執行）

Athena 的價值主張需要兩個層級！
```

---

## 授權策略

### 關鍵：授權隔離架構

**問題**：Shannon 使用 AGPL-3.0 授權，具有「病毒式」特性，若整合不當可能迫使 Athena 也必須採用 AGPL-3.0。

**解法**：嚴格的 API 整合，明確的授權邊界。

### 授權邊界
```
┌─────────────────────────────────────────┐
│  Athena 核心平台                        │
│  授權：Apache 2.0                       │
│                                          │
│  ✅ 商業友善                            │
│  ✅ 專利保護                            │
│  ✅ 企業可接受                          │
│                                          │
│  包含：                                  │
│  ├─ 所有決策引擎邏輯                    │
│  ├─ C5ISR 框架實作                      │
│  ├─ MITRE 編排                          │
│  ├─ OODA 循環控制器                     │
│  ├─ PentestGPT 整合（MIT）              │
│  └─ UI/UX 層                            │
└──────────────┬──────────────────────────┘
               │
          API 邊界
        （授權防火牆）
               │
      ┌────────┴────────┐
      ↓                 ↓
┌──────────┐      ┌──────────┐
│ Caldera  │      │ Shannon  │
│          │      │（選用）  │
│ Apache   │      │ AGPL-3.0 │
│ 2.0      │      │          │
└──────────┘      └──────────┘
```

### 第三方元件與授權
```
元件             授權         整合方式       必要性    來源
─────────────  ──────────   ─────────────  ────────  ────────────────────
Athena Core    Apache 2.0   -              ✅ 是     本專案
PentestGPT     MIT          程式庫匯入     ✅ 是     github.com/GreyDGL/PentestGPT
Caldera        Apache 2.0   API            ✅ 是     github.com/mitre/caldera
Shannon        AGPL-3.0     API（隔離）    ⚠️ 否     github.com/KeygraphHQ/shannon
```

### 安全整合實務

#### ✅ 允許（授權安全）
```python
# ✅ PentestGPT — MIT 授權（可安全直接匯入）
from pentestgpt import PentestGPTClient

class AthenaIntelligence:
    def __init__(self):
        # 直接匯入安全 — MIT 授權
        self.gpt_client = PentestGPTClient(
            api_key=os.getenv("ANTHROPIC_API_KEY"),
            model="claude-opus-4-20250514"
        )

# ✅ Caldera — Apache 2.0（API 整合）
class CalderaClient:
    def execute_ability(self, ability_id: str):
        # HTTP API 呼叫 — 授權安全
        response = requests.post(
            f"{self.caldera_url}/api/v2/abilities/{ability_id}",
            json={...}
        )

# ✅ Shannon — AGPL-3.0（僅 API，隔離）
class ShannonClient:
    def execute_task(self, task: dict):
        # 僅 HTTP API 呼叫 — 無程式碼匯入
        response = requests.post(
            f"{self.shannon_url}/execute",
            json=task
        )
```

#### ❌ 禁止（授權污染風險）
```python
# ❌ 不要這樣做 — 匯入 Shannon 程式碼
from shannon import ShannonEngine  # AGPL 污染！

# ❌ 不要這樣做 — 複製 Shannon 原始碼
# 將 Shannon 模組複製到 Athena 倉庫中

# ❌ 不要這樣做 — 靜態連結
# 將 Shannon 二進位檔包含在 Athena 中
```

---

## 技術棧

### 核心技術
```
前端（UI 層）：
├─ Pencil.dev（視覺設計與原型）
├─ Next.js 14 + React 18（框架）
└─ Tailwind CSS v4（樣式）

後端（決策引擎）：
├─ Python 3.11+（核心語言）
├─ FastAPI（API 框架）
├─ SQLite（POC 階段 — 簡單、檔案式）
└─ Pydantic（資料驗證）

AI/ML 元件：
├─ ⭐ PentestGPT（MIT 授權）— 核心元件
│   ├─ GitHub: https://github.com/GreyDGL/PentestGPT
│   ├─ 整合方式：直接程式庫匯入（MIT 安全）
│   └─ 用途：OODA Orient 階段情報
│
├─ LLM API：
│   ├─ 主要：Claude（Anthropic）
│   │   └─ 模型：claude-opus-4-20250514
│   │   └─ 原因：卓越的推理能力，適合戰術分析
│   │   └─ 上下文：200K tokens（可容納整個作戰歷史）
│   │
│   └─ 備用：GPT-4 Turbo（OpenAI）
│       └─ 模型：gpt-4-turbo-preview
│       └─ 成本：比 Claude 便宜約 50%
│
└─ LangChain（選用 — 進階提示工程）

執行引擎：
├─ ✅ Caldera（MITRE 官方 — POC 核心）
│   └─ Apache 2.0 授權
│   └─ 角色：主要執行引擎
│
└─ ⚠️ Shannon（AI Agent — 選用）
    └─ AGPL-3.0 授權（API 隔離）
    └─ 角色：進階 AI 自適應執行

3D 拓樸視覺化：
├─ react-force-graph-3d + Three.js（MIT）
└─ 用途：Battle Monitor 即時網路拓樸

基礎設施（POC）：
├─ Docker + Docker Compose（本機部署）
├─ SQLite（檔案式資料庫）
└─ .env 環境變數設定
```

### LLM 整合策略
```python
# 彈性 LLM 配置，透過 PentestGPT 驅動

class LLMConfig:
    """
    Athena 情報層的 LLM 配置
    由 PentestGPT 驅動
    """

    # 主要 LLM（Athena 推薦）
    PRIMARY_PROVIDER = "claude"
    CLAUDE_MODEL = "claude-opus-4-20250514"

    # 選擇 Claude 作為主要的原因：
    # 1. 卓越的推理能力，適合複雜戰術分析
    # 2. 200K 上下文窗口（可容納整個作戰歷史）
    # 3. 擅長結構化思考（MITRE 映射）
    # 4. 較保守/對齊的輸出（適合軍事用途）
    # 5. 擅長解釋推理（Orient 階段關鍵）

    # 備用 LLM
    FALLBACK_PROVIDER = "openai"
    OPENAI_MODEL = "gpt-4-turbo-preview"

    # API 金鑰（從 .env 載入）
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

    # 產生參數
    MAX_TOKENS = 4000
    TEMPERATURE = 0.7  # 平衡創造力與一致性
```

---

## 整合策略

### PentestGPT：情報核心

**PentestGPT** 是 Athena 情報層的基石。它驅動 OODA Orient 階段，提供 AI 輔助的戰術推理。

```
PentestGPT 為何不可或缺：

1. 戰略分析
   └─ 分析複雜的作戰情境
   └─ 考量多重因素（環境、失敗、目標）
   └─ 產生多選項建議

2. MITRE ATT&CK 原生
   └─ 理解 MITRE 戰術與技術
   └─ 將態勢映射至適當技術
   └─ 解釋技術選擇的推理

3. 以人為本
   └─ 為人機協作而設計
   └─ 提供解釋，而非僅有答案
   └─ 呈現選項供人類決策

4. 授權友善
   └─ MIT 授權 — 可安全直接整合
   └─ 無病毒式授權顧慮
   └─ 可依需求修改

5. 成本效益
   └─ 使用 LLM API（無需本地運算）
   └─ POC 測試：約 $5-15 / 20-30 次作戰
   └─ 按使用付費模式
```

### 執行引擎選擇
```python
class EngineRouter:
    """
    將任務路由至適當的執行引擎

    決策邏輯：
    1. PentestGPT 建議（若信心度高）
    2. 技術標準化（MITRE 原生 → Caldera）
    3. 環境複雜度（未知 → Shannon）
    4. 隱蔽需求（高 → Shannon）
    5. 預設：Caldera（穩定、可靠）
    """

    def select_engine(
        self,
        technique: str,
        context: dict,
        gpt_recommendation: str = None
    ) -> str:
        """
        回傳："caldera" 或 "shannon"
        """

        # 優先 1：信任高信心度的 PentestGPT 建議
        if gpt_recommendation and self._is_high_confidence(gpt_recommendation):
            return gpt_recommendation

        # 優先 2：標準 MITRE → Caldera
        if self.caldera.has_ability(technique):
            return "caldera"

        # 優先 3：未知環境 → Shannon（若可用）
        if context.get("environment") == "unknown" and self.shannon.available():
            return "shannon"

        # 優先 4：高隱蔽需求 → Shannon
        if context.get("stealth_level") == "maximum" and self.shannon.available():
            return "shannon"

        # 預設：Caldera（最可靠）
        return "caldera"
```

---

## 自動化模式

### 半自動 + 手動覆寫（Semi-Auto with Manual Override）

基於軍方紅隊顧問定位 + 開源 + PTLR 產品化考量，Athena 採用**可切換的半自動模式**。

### 模式切換
```
UI 上提供兩種模式：
○ MANUAL      — 每步都需指揮官批准
● SEMI-AUTO   — 根據風險等級自動/手動（預設）
```

### 風險閾值規則（Semi-Auto 模式）
```
風險等級          行為                     範例
─────────────   ─────────────────────   ─────────────────────
RiskLevel.LOW      自動執行               偵察、掃描
RiskLevel.MEDIUM   自動排入 queue，        LSASS dump
                   需指揮官 approve
RiskLevel.HIGH     強制 HexConfirmModal   橫向移動
                   確認對話框
RiskLevel.CRITICAL 永遠手動               資料竊取、破壞性操作
```

### 相關 Model 欄位
```python
# Operation 模型
automation_mode: AutomationMode   # "manual" | "semi_auto"
risk_threshold: RiskLevel         # Semi-Auto 模式下的閾值

# Technique 模型
risk_level: RiskLevel             # 每個技術的固有風險等級
```

### HexConfirmModal
當風險等級為 HIGH 時，前端會彈出 HexConfirmModal 確認對話框，指揮官必須明確批准才能執行。這確保高風險操作不會在無人監督下進行。

---

## 開發路線圖

### 總覽（9 個階段）

```
Phase 0 ████████████████████ 完成 — 設計與架構
Phase 1 ░░░░░░░░░░░░░░░░░░░░ 待辦 — 專案骨架
Phase 2 ░░░░░░░░░░░░░░░░░░░░ 待辦 — 後端基礎
Phase 3 ░░░░░░░░░░░░░░░░░░░░ 待辦 — 前端基礎（可與 Phase 2 並行）
Phase 4 ░░░░░░░░░░░░░░░░░░░░ 待辦 — 畫面實作
Phase 5 ░░░░░░░░░░░░░░░░░░░░ 待辦 — OODA 循環引擎
Phase 6 ░░░░░░░░░░░░░░░░░░░░ 待辦 — 整合與 Demo
Phase 7 ░░░░░░░░░░░░░░░░░░░░ 待辦 — 文件與開源發佈
Phase 8 ░░░░░░░░░░░░░░░░░░░░ 未來 — 進階增強
```

### Phase 0：設計與架構 `完成`

已交付：
- 6 個 .pen 設計檔（56 元件 + 32 變數 + 5 畫面 + 1 個 3D 拓樸 Demo）
- 資料架構文件（13 Enum、12 Model、SQLite Schema、REST API）
- 專案結構文件（Monorepo 佈局、各層職責）
- 本文件（CLAUDE.md — AI 上下文）
- 開發路線圖（ROADMAP.md）

### POC 成功標準
```
✅ 必須達成（POC 核心）：
├─ PentestGPT 提供戰術建議
├─ Caldera 執行 MITRE 技術
├─ 至少一次完整 OODA 循環迭代
├─ C5ISR 框架在 UI 中可見
├─ Demo 場景順暢運行
└─ 可供展示的文件

⚠️ 加分項（若有時間）：
├─ Shannon 整合
├─ 多次 OODA 迭代
├─ 進階 UI 功能
└─ 3D 拓樸即時互動

❌ 不在範圍內（POC）：
├─ 正式環境部署
├─ 多使用者支援
├─ 進階安全
├─ 合規功能
└─ 完整測試
```

> 詳細路線圖請參閱 [docs/ROADMAP.md](docs/ROADMAP.md)

---

## 關鍵概念

### AI 助手必須理解的概念

#### 1. 三層智慧架構
```
協助 Athena 開發的 AI 助手必須理解：

PentestGPT（思考）≠ Shannon（執行）

PentestGPT：
├─ 角色：軍事情報分析師
├─ 功能：分析、推理、建議
├─ 輸出：「我建議 X，因為 Y 和 Z」
├─ 互動對象：人類（指揮官）
├─ 可被質疑：「為什麼是 X 而非 Y？」
└─ POC 狀態：必要

Shannon：
├─ 角色：特種作戰士兵
├─ 功能：執行、自適應、回報
├─ 輸出：「我執行了 X，結果如下」
├─ 互動對象：目標系統
├─ 黑箱操作（較難解釋）
└─ POC 狀態：選用

兩者都使用 AI，但：
└─ PentestGPT = 後設認知 AI（思考戰術）
└─ Shannon = 自主 AI（執行戰術）

Athena 需要 PentestGPT 才能具備智慧。
Shannon 只是一個更強的執行器。
```

#### 2. PentestGPT 驅動 Orient 階段
```
OODA 循環分解：

Observe：資料收集
  └─ 這是直觀的

Orient：⭐ 關鍵 — PentestGPT 的領域
  └─ 這是 Athena 創造價值之處
  └─ 「根據情報，我們該怎麼做？」
  └─ PentestGPT 分析並建議
  └─ 沒有這個，Athena 只是自動化工具

Decide：人機協作
  └─ 指揮官考量 PentestGPT 的建議
  └─ Athena 引擎協助結構化決策

Act：執行（Caldera/Shannon）
  └─ 這是商品化能力
  └─ 任何人都能執行技術
```

#### 3. 目標使用者
```
使用者：10+ 年紅隊經驗、軍事顧問

這意味著：
✅ 假設具備 MITRE ATT&CK 知識
✅ 自然使用軍事術語
✅ 不解釋基本滲透測試概念
✅ 聚焦戰略價值，而非執行細節
❌ 不要用過度簡化的解釋
❌ 不要聚焦「自動化」 — 他們自己能自動化
✅ 聚焦「決策支援」 — 這才是價值

當 PentestGPT 建議時：
└─ 不要解釋 T1003.001 是什麼
└─ 要解釋為什麼「現在」它是最佳選擇
```

#### 4. POC 範圍管理
```
當使用者要求功能時：

總是問：
1. 「這是 POC 還是未來正式版的？」
2. 「這有助於證明核心概念嗎？」
3. 「這能展示 Athena 的獨特價值嗎？」

核心價值 = PentestGPT + C5ISR + OODA
非核心 = 其他一切

範例：
使用者：「可以加多使用者支援嗎？」
不好：「好的，我們來加 RBAC...」
好的：「這是正式版功能。POC 階段讓我們
      聚焦在證明決策引擎可行。
      我們可以記下多使用者為未來增強。」
```

---

## POC 階段限制

### 資源需求
```
最低配置（PentestGPT + Caldera）：
──────────────────────────────────────────────

服務              CPU    記憶體   必要
────────────────  ─────  ───────  ────────
backend           1.0    1 GB     ✅ 是
frontend          0.5    512 MB   ✅ 是
caldera（外部）   2.0    2 GB     ✅ 是
────────────────  ─────  ───────  ────────
總計              3.5    3.5 GB

主機需求：
├─ CPU：最少 4 核心
├─ RAM：8 GB（建議 16 GB）
├─ 儲存：20 GB
└─ 網路：穩定（LLM API 需要）

完整配置（+ Shannon）：
──────────────────────────────────────────────
shannon（選用）    2.0   2 GB     ⚠️ 否
────────────────  ─────  ───────  ────────
含 Shannon 總計   5.5   5.5 GB

建議：先不加 Shannon
```

### 成本估算（POC 階段）
```
一次性設定：
└─ $0（所有元件皆開源）

持續成本（LLM API）：
├─ Claude Opus：~$15 / 1M 輸入 tokens
├─ 每次 OODA 迭代：~2,000-4,000 tokens
├─ 每個作戰：10-20 次迭代
├─ 每個作戰成本：~$0.10 - $0.50
└─ POC 測試（20-30 次作戰）：$5 - $15

POC 總預算：< $20
```

### 安全態勢（POC）
```
POC 可接受：
✅ 以 .env 檔管理 API 金鑰（已加入 .gitignore）
✅ 僅本機部署
✅ 自簽憑證即可
✅ 最低限度身份驗證
✅ 基本日誌

不可接受：
❌ 將機密提交到 Git
❌ 暴露至公開網路
❌ 在程式碼中儲存憑證
❌ 以 root 身份運行

原則：「安全到不會自傷，但不要為 POC 過度設計」
```

---

## AI 助手指南

### 關鍵理解清單

協助 Athena 開發前，AI 助手必須理解：

- [ ] PentestGPT（思考）vs Shannon（執行）的區別
- [ ] PentestGPT 是必要的，Shannon 是 POC 選用的
- [ ] Orient 階段是核心創新
- [ ] 目標使用者是資深軍事顧問
- [ ] C5ISR 框架是組織原則
- [ ] MITRE ATT&CK 是共通語言
- [ ] POC 範圍是刻意受限的
- [ ] 授權邊界（PentestGPT MIT, Shannon AGPL）
- [ ] 半自動模式的風險閾值規則

### 程式碼風格指南
```python
# ✅ 好的：清楚的層級分離 + PentestGPT 整合

class AthenaOrientPhase:
    """
    情報層 — 使用 PentestGPT 進行分析。
    這是 Athena 價值的核心。
    """
    def __init__(self):
        from pentestgpt import PentestGPTClient
        self.gpt = PentestGPTClient(...)

    async def analyze(self, facts: Facts) -> Recommendations:
        # PentestGPT 推理邏輯
        pass

class CalderaExecutor:
    """
    執行層 — 僅發送 API 呼叫。
    此處不含決策邏輯。
    """
    def execute_ability(self, ability_id: str):
        # 純 API 呼叫
        pass

# ❌ 不好的：混合職責

class AthenaEngine:
    def exploit_smb(self, target):  # 不！這是執行
        # 滲透程式碼不屬於 Athena 核心
```

### 建議功能時的決策樹
```
決策樹：

是否涉及 PentestGPT 或 Orient 階段？
├─ 是 → 可能是 POC 核心
└─ 否 → 是 Command/Control 層嗎？
         ├─ 是 → 可能有價值
         └─ 否 → 大概延後到正式版

是執行能力嗎？
├─ 是 → 屬於 Caldera/Shannon，不屬於 Athena
└─ 否 → 繼續評估

需要 Shannon 參與嗎？
├─ 使用者明確提到 AI 自適應執行 → 也許
├─ 標準 MITRE 技術 → 否，用 Caldera
└─ 不確定 → 問清楚

是 POC 範圍嗎？
├─ 證明核心概念 → 是，納入
├─ 正式版功能 → 否，延後
└─ 加分項 → 記下，日後再說
```

---

## 環境設定

### 必要的 API 金鑰
```bash
# .env 檔（絕對不要提交到 Git）

# ════════════════════════════════════════════════
# LLM API（至少需要一個）
# ════════════════════════════════════════════════
ANTHROPIC_API_KEY=sk-ant-...    # 推薦（Claude）
OPENAI_API_KEY=sk-...           # 備用（GPT-4）

# ════════════════════════════════════════════════
# PentestGPT
# ════════════════════════════════════════════════
PENTESTGPT_API_URL=http://localhost:8080
PENTESTGPT_MODEL=gpt-4

# ════════════════════════════════════════════════
# 執行引擎
# ════════════════════════════════════════════════
CALDERA_URL=http://localhost:8888
CALDERA_API_KEY=...             # 若 Caldera 需要身份驗證

# Shannon（選用 — 不用時註解掉）
# SHANNON_URL=http://localhost:9000

# ════════════════════════════════════════════════
# 資料庫
# ════════════════════════════════════════════════
DATABASE_URL=sqlite:///backend/data/athena.db

# ════════════════════════════════════════════════
# 自動化模式
# ════════════════════════════════════════════════
AUTOMATION_MODE=semi_auto
RISK_THRESHOLD=medium

# ════════════════════════════════════════════════
# 前端
# ════════════════════════════════════════════════
NEXT_PUBLIC_API_URL=http://localhost:8000/api
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws

# ════════════════════════════════════════════════
# 日誌
# ════════════════════════════════════════════════
LOG_LEVEL=INFO
```

### 快速啟動指令
```bash
# ════════════════════════════════════════════════
# POC 設定（PentestGPT + Caldera）
# ════════════════════════════════════════════════

# 1. 複製倉庫
git clone https://github.com/astroicers/Athena
cd Athena

# 2. 設定環境
cp .env.example .env
nano .env  # 加入你的 ANTHROPIC_API_KEY

# 3. 啟動核心服務
docker-compose up -d backend frontend

# 4. 驗證服務
docker-compose ps
docker-compose logs -f backend

# 5. 存取 Athena
# - Athena UI：http://localhost:3000
# - Athena API：http://localhost:8000/docs
# - Caldera：http://localhost:8888（需另行啟動）

# ════════════════════════════════════════════════
# 選用：稍後加入 Shannon
# ════════════════════════════════════════════════

# 取消 docker-compose.yml 中 shannon 的註解
# 然後：
# docker-compose up -d shannon
```

---

## 常見問題

### 「為什麼有 Shannon 還需要 PentestGPT？」
```
回答：它們在不同層級服務不同目的。

PentestGPT = 戰略思考
「根據當前態勢，什麼戰術有意義？」
「為什麼 T1003.001 現在比 T1110 好？」

Shannon = 戰術執行
「執行這個攻擊，如果防禦擋住就自適應」

類比：
├─ PentestGPT = 軍事戰略家（規劃戰役）
└─ Shannon = 特種部隊操作員（贏得戰鬥）

兩者都需要。PentestGPT 告訴你「做什麼」。
Shannon 幫助你在複雜環境中「完成它」。
```

### 「Shannon 能取代 PentestGPT 嗎？」
```
回答：不能。不同角色，不同層級。

Shannon 是：
├─ 黑箱（難以解釋其推理）
├─ 以執行為中心（非戰略性）
├─ 自主（不與人類協作）

PentestGPT 是：
├─ 可解釋（可以說明建議的理由）
├─ 以策略為中心（後設層級推理）
├─ 協作式（為人機互動而設計）

Athena 的價值 = 指揮層 + AI 建議。
Shannon 無法提供這些 — 它是執行器。
```

### 「POC 需要 Shannon 嗎？」
```
回答：不需要。PentestGPT + Caldera 即足夠。

POC 目標：證明 Athena 的指揮平台概念

為此所需：
✅ AI 輔助戰術規劃（PentestGPT）
✅ MITRE 技術執行（Caldera）
✅ OODA 循環（PentestGPT + Caldera）
✅ C5ISR 框架視覺化

Shannon 增加的：
⚠️ 雙引擎編排展示
⚠️ AI 自適應執行展示
⚠️ 但增加複雜度與風險

建議：先不加 Shannon。
若 POC 成功且想展示進階編排再加入。
```

### 「為什麼選 Claude 而非 GPT-4？」
```
回答：卓越的推理能力，適合戰術分析。

Claude 優勢：
✅ 複雜推理鏈表現更佳
✅ 200K 上下文（整個作戰歷史）
✅ 較保守/對齊（軍事用途更安全）
✅ 擅長解釋推理（Orient 關鍵能力）

GPT-4 優勢：
✅ 較便宜（約 50%）
✅ API 回應速度較快
✅ PentestGPT 原本為其設計

建議：Claude 為主要，GPT-4 為備用。
POC 的成本差異極小（總計約 $10-15）。
```

---

## 專案目標

### 近期（POC — 2 個月）
- [ ] PentestGPT + Caldera 整合運作
- [ ] AI 驅動的戰術建議（Orient 階段）
- [ ] 完整 OODA 循環（至少 1 次迭代）
- [ ] C5ISR 框架視覺化
- [ ] Demo 場景：「奪取 Domain Admin」
- [ ] 可供展示的文件

### 未來（若繼續發展）
- [ ] Shannon 整合（雙引擎編排）
- [ ] 增強 AI 推理（多輪規劃）
- [ ] 完整 MITRE ATT&CK 覆蓋
- [ ] 正式環境部署考量
- [ ] 潛在商業化路徑

---

## AI 助手的關鍵提醒

1. **PentestGPT 是核心** — 非選用、Shannon 無法取代
2. **Shannon 是選用** — POC 不需要它
3. **Orient 階段是關鍵** — Athena 在此創造價值
4. **POC 範圍紀律** — 不要過度設計
5. **授權意識** — PentestGPT MIT（安全）、Shannon AGPL（小心）
6. **目標使用者水準** — 資深軍事顧問，假設具備專業知識
7. **C5ISR 框架** — 所有功能必須映射至此
8. **MITRE ATT&CK** — 戰術的共通語言
9. **半自動模式** — 風險閾值規則決定自動/手動行為

---

*最後更新：2026-02-22*
*版本：0.4.0-poc*
*階段：早期開發 — POC（PentestGPT + Caldera）*

---

## 附錄：快速參考

### 元件清單
- [ ] PentestGPT（情報）✅ 必要
- [ ] Caldera（執行）✅ 必要
- [ ] Shannon（進階執行）⚠️ 選用
- [ ] Athena UI ✅ 必要
- [ ] Athena Backend ✅ 必要

### OODA 清單
- [ ] Observe：情報收集 ✅
- [ ] Orient：PentestGPT 分析 ✅ **核心**
- [ ] Decide：Athena 決策引擎 ✅
- [ ] Act：Caldera/Shannon 執行 ✅

### 授權合規
- [ ] Athena 核心：Apache 2.0 ✅
- [ ] PentestGPT：MIT（安全匯入）✅
- [ ] Caldera：Apache 2.0（API）✅
- [ ] Shannon：AGPL-3.0（僅 API）⚠️
- [ ] 無授權污染 ✅

### POC 成功指標
- [ ] PentestGPT 提供建議
- [ ] 建議可操作
- [ ] Caldera 執行技術
- [ ] 一次完整 OODA 迭代
- [ ] Demo 場景可運行
- [ ] 可供展示

---

## 相關文件

- [開發路線圖](docs/ROADMAP.md) — Phase 0-8 完整計畫
- [資料架構](docs/architecture/data-architecture.md) — 模型、Schema、API、種子資料
- [專案結構](docs/architecture/project-structure.md) — 目錄佈局、各層職責

---

**CLAUDE.md v4 結束**
