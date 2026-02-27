# Athena 生態系全盤評估

> **日期**：2026-02-26
> **狀態**：評估完成，供未來整合決策參考
> **範圍**：Athena 現有外部依賴 + 3 個候選擴充專案

---

## 1. 評估背景

Athena 是 C5ISR 網路作戰**指揮平台**，外部專案以**武器/裝備**身份掛載到 OODA 指揮鏈。
本評估起因：考慮替換或補強 PentestGPT（Orient 層），同時全盤檢視生態系健康度。

---

## 2. 現有生態系盤點

### Athena 專案現狀

- **進度**：Phase 0~6 完成，Phase 7（文件）進行中
- **外部整合**：全部為 mock / prompt 模擬，**無真實連線**
- **技術棧**：Python 3.11 + FastAPI + SQLite + Next.js 14

### 現有外部專案

| 專案 | Stars | 授權 | 最新版本 | OODA 角色 | 整合程度 | 健康度 |
|------|-------|------|---------|----------|---------|--------|
| **PentestGPT** | 11.8k | MIT | v1.0.0 (2025/12) | Orient | Prompt 模擬 | ✅ 活躍 |
| **Caldera** | 6.8k | Apache 2.0 | v5.3.0 (2025/04) | Act | Mock client | ✅ 活躍 |
| **Shannon** | 25.2k | AGPL-3.0 | 活躍 | Act (選用) | API 骨架 | ✅ 活躍 |

### 重要發現：PentestGPT 並未老舊

- v1.0.0 (2025/12) 重大升級：自主 Agent 管線 + Session 持久化 + Docker 部署
- 11.8k stars — 比三個候選都多
- USENIX Security 2024 學術論文
- 23 contributors、302 commits
- **結論**：「老舊」印象可能來自早期版本，v1.0.0 是質變升級

---

## 3. 候選專案評估

### 3.1 PentAGI (8.2k⭐, MIT, Go + React)

**定位**：全自主多 Agent 滲透測試系統

**優勢**：
- GitHub Trending #1 (2026/02)，社群最活躍
- 多 Agent：Researcher → Developer → Executor
- Neo4j 知識圖 + pgvector 語義記憶
- 20+ 安全工具在隔離 Docker 容器
- Claude token caching 支援（省 40-70%）
- REST/GraphQL API + JWT 認證
- v1.2.0 穩定版

**劣勢**：
- Go 後端 — 與 Athena (Python) 跨語言整合
- 架構最重（PostgreSQL + Neo4j + Redis + 監控堆疊）
- 有自己的 Orchestrator 指揮鏈 → **指揮權衝突風險高**
- 與 Caldera 功能高度重疊

**OODA 位置**：主要 Act 層，Research Agent 部分覆蓋 Orient
**整合方式**：純 REST API 呼叫，降級為「特種任務執行單元」

### 3.2 PentestAgent (1.7k⭐, MIT, Python)

**定位**：三模式（顧問/自主/多Agent）滲透測試框架

**優勢**：
- **Assist 模式**：純顧問角色，零指揮衝突
- Python 原生，與 Athena 技術棧一致
- MCP 協定支援 — 透過 HexStrike 整合 150+ 工具
- 攻擊 Playbook — 結構化方法論
- Shadow Graph 知識圖譜（Crew 模式）
- Docker：Base (500MB) / Kali (2GB)
- 最新更新 2026/02/26

**劣勢**：
- v0.2.0 早期版本，穩定性存疑
- 5 人小團隊
- MCP 連線問題 (Issue #29 未解)
- Crew 模式文件不完整
- Stars 最少 (1.7k)

**OODA 位置**：Assist = Orient, Agent = Act, Crew = Decide+Act
**整合方式**：subprocess 或 Docker 微服務

### 3.3 RedAmon (1.3k⭐, MIT, Python + Next.js)

**定位**：AI 驅動的偵察 + 攻擊面圖譜

**優勢**：
- **六階段自動偵察管線**（最系統化的 Observe 實作）
- Neo4j 攻擊面圖：17+ 節點類型、20+ 關係
- **EvoGraph** — 跨 Session 進化式攻擊鏈追蹤（獨特）
- LangGraph Agent (ReAct 模式)
- 30+ 安全工具整合
- FastAPI 後端 — 與 Athena 技術棧一致
- v2.0.0 功能成熟
- 180+ 可配置參數

**劣勢**：
- 主要 1 人開發 (bus factor 高)
- Docker build 問題 (Issue #19)
- 偏重偵察，主動利用能力較弱
- 完整堆疊需 8-16GB RAM

**OODA 位置**：Observe (六階段偵察) + Orient (LangGraph Think)
**整合方式**：FastAPI API 對接（技術棧最相容）

---

## 4. 全部 6 個專案的 OODA 位置圖

```
OODA 階段    現有（mock 整合）          候選（待評估）
─────────────────────────────────────────────────────
OBSERVE      FactCollector (內建)      RedAmon (偵察管線)
ORIENT       PentestGPT (prompt)      PentestAgent (Assist)
DECIDE       DecisionEngine (內建)     — 無候選碰此層 —
ACT          Caldera (mock)           PentAGI (執行)
             Shannon (API 骨架)
```

### 重疊與互補矩陣

| 組合 | 關係 | 說明 |
|------|------|------|
| PentestGPT ↔ PentestAgent | **競爭** | 都在 Orient，PentestGPT 更成熟 (11.8k vs 1.7k) |
| Caldera ↔ PentAGI | **競爭** | 都在 Act，PentAGI 更自主但 Caldera 更專注 ATT&CK |
| Caldera ↔ Shannon | **互補** | 已設計好路由機制 (ADR-006) |
| FactCollector ↔ RedAmon | **互補** | RedAmon 補強偵察深度 |
| PentestGPT ↔ RedAmon | **互補** | RedAmon 偵察 → PentestGPT 分析 |
| PentestAgent ↔ RedAmon | **互補** | 可共存於 Orient，交叉比對建議 |

---

## 5. 指揮鏈衝突分析

| 專案 | 自有指揮鏈 | 衝突風險 | 降級策略 |
|------|-----------|---------|---------|
| PentestGPT | 無（被 prompt 呼叫） | **無** | 維持現狀 |
| Caldera | 有 C2 server | **低** | API 呼叫，Athena 發指令 |
| Shannon | 有自主 Agent | **低** | API 隔離 (AGPL + 設計) |
| PentAGI | ⚠️ Orchestrator | **中高** | 只 REST API 提交單一任務 |
| PentestAgent | ⚠️ Crew Orchestrator | **中** | 只用 Assist 模式（顧問） |
| RedAmon | ⚠️ LangGraph Agent | **中** | 只用偵察管線，Agent 由 Athena 控制 |

**關鍵原則**：Athena 的 Decide 層（`DecisionEngine`）永遠不被外部專案替換。

---

## 6. 失焦風險評估

| 風險 | 嚴重度 | 說明 |
|------|--------|------|
| **範圍膨脹** | 高 | Phase 7 未完成就引入多專案 = 提前進入 Phase 8+ |
| **指揮權稀釋** | 中 | 候選專案都帶自有指揮邏輯，降級需額外工程 |
| **整合複雜度** | 高 | 6 個外部系統 x 不同語言/API/部署 = 維護惡夢 |
| **POC 偏移** | 高 | POC 驗證「指揮架構」，不是驗證「武器數量」 |
| **Mock 未拆完** | 中 | 連 Caldera/Shannon 都還沒真正連線 |
| **資源分散** | 高 | 同時對接 6 個外部系統不現實 |

---

## 7. 建議策略：先完成現有，再逐步擴展

### Step 0：修正認知（立即）
- PentestGPT v1.0.0 (11.8k stars) 不需要被「替換」
- 可研究其 v1.0.0 新功能來升級 Orient prompt

### Step 1：完成 Phase 7 + 發布 v0.1.0
- 文件 (7.2~7.4)、CI、Release

### Step 2：拆除 Mock，真正連線現有依賴
- `MockCalderaClient` → 對接 Caldera v5.3.0
- Shannon API client 跑通
- 升級 `orient_engine.py` prompt，參考 PentestGPT v1.0.0

### Step 3：根據最弱 OODA 環節，加一個（最多一個）
- **Observe 最弱** → RedAmon（偵察管線）
- **Orient 需升級** → PentestAgent Assist 或直接升級 PentestGPT prompt
- **Act 需擴展** → PentAGI（確認 Caldera 真的不夠用時）

---

## 8. 現有可複用的架構模式

Athena 的插件架構已足夠成熟，未來整合不需大改：

| 模式 | 位置 | 說明 |
|------|------|------|
| `BaseEngineClient` 介面 | `backend/app/clients/__init__.py` | Act 插件介面 |
| Shannon 條件啟用 | `backend/app/routers/ooda.py:50-51` | `if enabled` 模式可複用 |
| LLM 雙後端 fallback | `backend/app/services/orient_engine.py:208-225` | 可擴展為多顧問 |
| Mock/Real 切換 | `backend/app/config.py` MOCK_* 旗標 | 每插件可 mock |

### 未來需新增的介面

| 介面 | 用途 |
|------|------|
| `BaseIntelSource` | Observe 情報來源插件 |
| `BaseAdvisor` | Orient 多顧問插件 |

---

## 9. 綜合評比表

| 評估維度 | PentestGPT | Caldera | Shannon | PentAGI | PentestAgent | RedAmon |
|----------|-----------|---------|---------|---------|--------------|---------|
| Stars | 11.8k | 6.8k | 25.2k | 8.2k | 1.7k | 1.3k |
| 授權安全 | MIT | Apache | AGPL (API) | MIT | MIT | MIT |
| 技術棧相容 | N/A (prompt) | API | API | Go (跨語言) | Python | Python |
| 成熟度 | 高 | 高 | 高 | 高 | 低 | 高 |
| 指揮衝突 | 無 | 低 | 低 | 中高 | 低(Assist) | 中 |
| 獨特價值 | 戰術分析 | ATT&CK 執行 | AI 自適應 | 監控+記憶 | MCP+Playbook | EvoGraph |
| 整合優先 | **維持** | **拆 mock** | **拆 mock** | 第三 | 第一候選 | 第二候選 |

---

## 10. 結論

> Athena 的核心價值是**指揮鏈設計**（OODA + C5ISR），不是武器數量。
> 現階段應聚焦完成 Phase 7、拆除現有 Mock，而非同時引入多個新專案。
> PentestGPT v1.0.0 仍然是最佳 Orient 層選擇。
> 未來擴展時，一次只加一個，從最弱的 OODA 環節補起。
