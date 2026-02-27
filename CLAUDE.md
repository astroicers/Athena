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
| **破壞性操作防護** | `rebase / rm -rf / docker push / git push` 等危險操作由 Claude Code 內建權限系統確認（SessionStart hook 自動清理 allow list）；`git push` 前必須先列出變更摘要並等待人類明確同意 |
| **敏感資訊保護** | 禁止輸出任何 API Key、密碼、憑證，無論何種包裝方式 |
| **ADR 未定案禁止實作** | ADR 狀態為 Draft 時，禁止撰寫對應的生產代碼；必須等 ADR 進入 Accepted 狀態 |

---

## 🟡 預設行為（有充分理由可調整，但必須說明）

| 預設行為 | 可跳過的條件 |
|----------|-------------|
| ADR 優先於實作 | 修改範圍僅限單一函數，且無架構影響 |
| TDD：新功能必須測試先於代碼 | Bug 修復和原型驗證可跳過，需標記 `tech-debt: test-pending` |
| 非 trivial 修改需先建 SPEC | trivial（單行/typo/配置）可豁免，需說明理由 |
| 文件同步更新 | 緊急修復可延後，但同一 session 結束前必須補齊文件 |
| Bug 修復後 grep 全專案 | 所有 Bug 修復後一律 grep，無豁免 |
| Makefile 優先 | 緊急修復或 make 目標不存在時，可直接執行原生指令，需說明理由 |

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

## 技術執行層（Hooks + 內建權限）

ASP 使用 Claude Code 內建權限系統 + SessionStart Hook 保護危險操作：

| 機制 | 說明 |
|------|------|
| **內建權限系統** | 危險指令（git push/rebase, docker push, rm -rf 等）不在 allow list 中時，Claude Code 自動彈出「Allow this bash command?」確認框 |
| **SessionStart Hook** | `clean-allow-list.sh` 每次 session 啟動時自動清理 allow list 中的危險規則，確保內建權限系統持續生效 |

> 設定檔位於 `.claude/settings.json`，hook 腳本位於 `.asp/hooks/`。
> 使用者可在確認框中選擇 "Allow"（一次性）或 "Always allow"（永久），但後者會在下次 session 啟動時被自動清理。
