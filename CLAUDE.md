# AI-SOP-Protocol (ASP) — 行為憲法

> 本專案遵循 ASP 協議。讀取順序：本區塊 → `.ai_profile` → 對應 `.asp/profiles/`（按需）
> 鐵則與 Profile 對應表請見：.asp/profiles/global_core.md

---

## 啟動程序

1. 讀取 `.ai_profile`，依欄位載入對應 profile
2. **RAG 已啟用時**：回答任何專案架構/規格問題前，先執行 `make rag-search Q="..."`
3. 無 `.ai_profile` 時：只套用本檔案鐵則，詢問使用者專案類型

```yaml
# .ai_profile 完整欄位參考
type:      system | content | architecture   # 必填
mode:      single | multi-agent | committee  # 預設 single
workflow:  standard | vibe-coding            # 預設 standard
rag:       enabled | disabled               # 預設 disabled
guardrail: enabled | disabled               # 預設 disabled
hitl:      minimal | standard | strict      # 預設 standard
name:      your-project-name
```

**Profile 對應表：**

| 欄位值 | 載入的 Profile |
|--------|----------------|
| `type: system` | `.asp/profiles/global_core.md` + `.asp/profiles/system_dev.md` |
| `type: content` | `.asp/profiles/global_core.md` + `.asp/profiles/content_creative.md` |
| `type: architecture` | `.asp/profiles/global_core.md` + `.asp/profiles/system_dev.md` |
| `mode: multi-agent` | + `.asp/profiles/multi_agent.md` |
| `mode: committee` | + `.asp/profiles/committee.md` |
| `workflow: vibe-coding` | + `.asp/profiles/vibe_coding.md` |
| `rag: enabled` | + `.asp/profiles/rag_context.md` |
| `guardrail: enabled` | + `.asp/profiles/guardrail.md` |

---

## 🔴 鐵則（不可覆蓋）

以下規則在任何情況下不得繞過：

| 鐵則 | 說明 |
|------|------|
| **副作用防護** | `deploy / rm -rf / merge / rebase` 由 Hooks 技術強制攔截；`git push` 由內建權限系統確認 |
| **不擅自推版** | 禁止未經人類明確同意執行 `git push`；必須先列出變更摘要並等待人類確認 |
| **敏感資訊保護** | 禁止輸出任何 API Key、密碼、憑證，無論何種包裝方式 |
| **Makefile 優先** | 有對應 make 目標時，禁止輸出原生長指令 |

---

## 🟡 預設行為（有充分理由可調整，但必須說明）

| 預設行為 | 可跳過的條件 |
|----------|-------------|
| ADR 優先於實作 | 修改範圍僅限單一函數，且無架構影響 |
| TDD：測試先於代碼 | 原型驗證階段，需標記 `tech-debt: test-pending` |
| 非 trivial Bug 修復需建 SPEC | trivial（單行/typo/配置）可豁免，需說明理由 |
| 文件同步更新 | 緊急修復可延後，但必須在 24h 內補文件 |
| SPEC 先於原始碼修改 | trivial（單行/typo/配置）可豁免，需說明理由（由 Hook 技術提醒） |
| Bug 修復後 grep 全專案 | 確認為單點配置錯誤時可豁免 |

---

## 標準工作流

```
需求 → [ADR 建立] → SDD 設計 → TDD 測試 → 實作 → 文件同步 → 確認後部署
         ↑ 架構影響時必須        ↑ 預設行為，可調整
```

---

## Makefile 速查

| 動作 | 指令 |
|------|------|
| 建立 Image | `make build` |
| 清理環境 | `make clean` |
| 重新部署 | `make deploy` |
| 執行測試 | `make test` |
| 局部測試 | `make test-filter FILTER=xxx` |
| 新增 ADR | `make adr-new TITLE="..."` |
| 新增規格書 | `make spec-new TITLE="..."` |
| 查詢知識庫 | `make rag-search Q="..."` |
| Agent 完成回報 | `make agent-done TASK=xxx STATUS=success` |
| 儲存 Session | `make session-checkpoint NEXT="..."` |

> 以上為常用指令，完整列表請執行 `make help`

---

## 技術執行層（Hooks）

ASP 使用 Claude Code Hooks 技術強制執行鐵則，不依賴 AI 自律：

| Hook | 攔截對象 | 行為 |
|------|---------|------|
| `enforce-side-effects.sh` | deploy, rm -rf, merge, rebase, kubectl, docker push | deny 阻止執行，告知原因 |
| `enforce-workflow.sh` | 原始碼修改（Edit/Write） | 依 HITL 等級 deny 攔截 + SPEC 存在性檢查 |

> Hooks 使用 `permissionDecision: "deny"` + `exit 2` 雙保險攔截（[GitHub #3514](https://github.com/anthropics/claude-code/issues/3514)）。
> `git push` 不由 hook 攔截，改由 Claude Code 內建權限系統處理（VSCode 中顯示 GUI 確認框）。
> 原因：hook `"ask"` 在 VSCode 中被忽略（[#13339](https://github.com/anthropics/claude-code/issues/13339)），`"deny"` 會截斷對話。
> 設定檔位於 `.claude/settings.json`，hook 腳本位於 `.asp/hooks/`。

---

# Athena — 專案上下文

> **狀態**：POC 階段 — Phase 0~6 完成，Phase 7 文件撰寫進行中
> **核心棧**：PentestGPT（情報）+ Caldera（執行）

## 專案定位

Athena 是 AI 驅動的 **C5ISR 網路作戰指揮平台**。不是滲透測試工具，而是軍事級指揮與決策平台。
目標使用者：10+ 年紅隊經驗的軍事顧問 — 假設具備 MITRE ATT&CK 專業知識。

## 三層智慧架構

| 層級 | 元件 | 角色 | OODA 階段 |
|------|------|------|-----------|
| 戰略智慧 | PentestGPT (MIT) | 思考、分析、建議 | **Orient** — 核心創新 |
| 決策智慧 | Athena 引擎 | 路由、編排、排序 | Decide |
| 執行智慧 | Caldera (Apache 2.0) | 執行 MITRE 技術 | Act |
| 執行智慧（選用） | Shannon (AGPL-3.0, **僅 API**) | AI 自適應執行 | Act |

**關鍵**：PentestGPT 是必要的（核心差異化），Shannon 是 POC 選用的。兩者都用 AI 但層級不同。

## 技術棧

- **後端**：Python 3.11 + FastAPI + SQLite + Pydantic
- **前端**：Next.js 14 + React 18 + Tailwind v4
- **3D 拓樸**：react-force-graph-3d + Three.js
- **容器化**：Docker + docker-compose
- **LLM**：Claude（主要）/ GPT-4（備用），預設 `MOCK_LLM=True`

## 自動化模式

半自動 + 手動覆寫。風險等級決定行為：
- LOW → 自動執行 | MEDIUM → 排隊待批 | HIGH → HexConfirmModal | CRITICAL → 手動

## 授權邊界（鐵則）

- Athena 核心：Apache 2.0
- PentestGPT：MIT — **可安全 import**
- Caldera：Apache 2.0 — API 整合
- Shannon：AGPL-3.0 — **僅限 API 呼叫，禁止 import 程式碼**

## 詳細文件指引

| 需要瞭解… | 請讀… |
|-----------|-------|
| 完整架構圖 | `docs/architecture.md` |
| 資料模型 / Schema / API | `docs/architecture/data-architecture.md` |
| 目錄結構 / 各層職責 | `docs/architecture/project-structure.md` |
| 開發路線圖 / Phase 進度 | `docs/ROADMAP.md` |
| Demo 操作手冊 | `docs/DEMO_WALKTHROUGH.md` |
| 安裝設定 | `docs/GETTING_STARTED.md` |
| 版本歷史 | `CHANGELOG.md` |
| SPEC 規格書列表 | `make spec-list` |
| ADR 決策記錄列表 | `make adr-list` |

## AI 助手關鍵提醒

1. **說中文** — 使用者以繁體中文溝通
2. **PentestGPT 是核心** — Orient 階段是 Athena 創造價值之處
3. **POC 範圍紀律** — 不過度設計，聚焦核心概念驗證
4. **授權意識** — Shannon AGPL 僅 API 隔離，絕不 import
5. **C5ISR 框架** — 所有功能映射至 Command/Control/Comms/Computers/Cyber/ISR
6. **MITRE ATT&CK** — 共通語言，假設使用者已具備知識
