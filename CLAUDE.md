# AI-SOP-Protocol (ASP) — 行為憲法

> 讀取順序：本檔案 → `.ai_profile` → 對應 `.asp/profiles/`（按需）

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
