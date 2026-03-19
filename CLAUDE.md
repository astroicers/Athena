# AI-SOP-Protocol (ASP) — 行為憲法

> 讀取順序：本檔案 → `.ai_profile` → 對應 `.asp/profiles/`（按需）

---

## 專案概覽

<!-- ASP-AUTO-PROJECT-DESCRIPTION: START -->
> 此區塊由 autopilot 自動產生（`make autopilot-validate` 或 autopilot 啟動時），請勿手動編輯。
> 若需更新，修改 ROADMAP.yaml 後重新執行 `make autopilot-validate`。

（尚未產生 — 執行 `make autopilot-validate` 或啟動 autopilot 時會自動填入）
<!-- ASP-AUTO-PROJECT-DESCRIPTION: END -->

---

## 啟動程序

1. 讀取 `.ai_profile`，依欄位載入對應 profile
2. **Profile 依賴與衝突驗證**：CALL `validate_profile_config()`（見下方），確認依賴已載入、衝突 Profile 未同時啟用
3. **自動載入規則**：`design: enabled` 時自動載入 `frontend_quality.md`（不需額外設定）
4. **若 `autonomous: enabled`，或 `workflow: vibe-coding` + `hitl: minimal`**：額外載入 `autonomous_dev.md`（同時確保 `vibe_coding.md` 已載入，未設定時自動補載）。若同時 `mode: multi-agent`，autonomous 規則分層套用（見 `autonomous_dev.md`「Multi-Agent 整合」）
4a. **若 `orchestrator: enabled`，或 `autonomous: enabled`**：額外載入 `task_orchestrator.md`。首次介入專案時自動執行專案健康審計（`project_health_audit()`），偵測缺失的測試、SPEC、ADR、文件並強制補齊
4b. **若 `autopilot: enabled`**：額外載入 `autopilot.md`（自動確保 `autonomous_dev.md` + `task_orchestrator.md` 已載入）。Session 啟動時檢查 `.asp-autopilot-state.json`——若存在且 status == "in_progress"，自動續接（零確認）
5. **RAG 已啟用時**：回答任何專案架構/規格問題前，先執行 `make rag-search Q="..."`
6. 無 `.ai_profile` 時：只套用本檔案鐵則，詢問使用者專案類型

```
FUNCTION validate_profile_config(ai_profile):
  loaded = parse_ai_profile(ai_profile)

  // ─── 依賴檢查 ───
  FOR profile IN loaded.profiles:
    requires = parse_requires_comment(profile)  // <!-- requires: ... -->
    FOR dep IN requires:
      IF dep NOT IN loaded.profiles:
        WARN("Profile '{profile.name}' 依賴 '{dep}' 但未載入。建議在 .ai_profile 中啟用。")

  // ─── 衝突檢查 ───
  FOR profile IN loaded.profiles:
    conflicts = parse_conflicts_comment(profile)  // <!-- conflicts: ... -->
    FOR conflict IN conflicts:
      IF conflict IN loaded.profiles:
        WARN("Profile '{profile.name}' 與 '{conflict}' 互斥，不可同時啟用。停用其中一個。")

  // ─── 自動載入規則驗證 ───
  IF loaded.design == "enabled" AND "frontend_quality" NOT IN loaded.profiles:
    AUTO_LOAD("frontend_quality.md")
    LOG("design: enabled → 自動載入 frontend_quality.md")
```

```yaml
# .ai_profile 完整欄位參考
type:         system | content | architecture   # 必填
mode:         single | multi-agent | committee  # 預設 single
workflow:     standard | vibe-coding            # 預設 standard
rag:          enabled | disabled               # 預設 disabled
guardrail:    enabled | disabled               # 預設 disabled
hitl:         minimal | standard | strict      # 預設 standard
autonomous:   enabled | disabled               # 預設 disabled（AI 全自動開發模式）
orchestrator: enabled | disabled               # 預設 disabled（autonomous: enabled 時自動載入）
design:       enabled | disabled               # 預設 disabled
frontend_quality: enabled | disabled           # 預設 disabled（design: enabled 時自動載入）
coding_style: enabled | disabled               # 預設 disabled
openapi:      enabled | disabled               # 預設 disabled
autopilot:    enabled | disabled               # 預設 disabled（roadmap 驅動持續執行）
name:         your-project-name
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
| `design: enabled` | + `.asp/profiles/design_dev.md` |
| `coding_style: enabled` | + `.asp/profiles/coding_style.md` |
| `openapi: enabled` | + `.asp/profiles/openapi.md` |
| `autonomous: enabled` | + `.asp/profiles/autonomous_dev.md` + `.asp/profiles/task_orchestrator.md`（自動） |
| `orchestrator: enabled` | + `.asp/profiles/task_orchestrator.md` |
| `frontend_quality: enabled` | + `.asp/profiles/frontend_quality.md` |
| `design: enabled`（自動） | + `.asp/profiles/frontend_quality.md` |
| `workflow: vibe-coding` + `hitl: minimal` | + `.asp/profiles/autonomous_dev.md` |
| `autopilot: enabled` | + `.asp/profiles/autopilot.md` + `autonomous_dev.md` + `task_orchestrator.md`（自動） |

---

## 🔴 鐵則（不可覆蓋）

以下規則在任何情況下不得繞過：

| 鐵則 | 說明 |
|------|------|
| **破壞性操作防護** | `rebase / rm -rf / docker push / git push` 等危險操作由 Claude Code 內建權限系統確認（SessionStart hook 自動清理 allow list）；`git push` 前必須先列出變更摘要並等待人類明確同意 |
| **敏感資訊保護** | 禁止輸出任何 API Key、密碼、憑證，無論何種包裝方式 |
| **ADR 未定案禁止實作** | ADR 狀態為 Draft 時，禁止撰寫對應的生產代碼；必須等 ADR 進入 Accepted 狀態。autopilot 模式下不暫停詢問，而是自動將該 task 標記 blocked 並跳過 |

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
| 測試覆蓋率 | `make coverage` |
| 程式碼檢查 | `make lint` |
| i18n 檢查 | `make i18n-check` |
| 架構圖 | `make diagram` |
| 新增 ADR | `make adr-new TITLE="..."` |
| ADR 列表 | `make adr-list` |
| 新增規格書 | `make spec-new TITLE="..."` |
| SPEC 列表 | `make spec-list` |
| 新增事後分析 | `make postmortem-new TITLE="..."` |
| Agent 完成回報 | `make agent-done TASK=xxx STATUS=success` |
| Agent 狀態 | `make agent-status` / `make agent-locks` |
| Agent 鎖定管理 | `make agent-unlock FILE=...` / `make agent-lock-gc` |
| 儲存 Session | `make session-checkpoint NEXT="..."` |
| 查詢知識庫 | `make rag-search Q="..."` |
| RAG 統計 | `make rag-stats` / `make rag-index` / `make rag-rebuild` |
| 護欄紀錄 | `make guardrail-log` / `make guardrail-reset` |
| 專案健康審計 | `make audit-health`（完整 7 維度） |
| 快速審計 | `make audit-quick`（僅 blocker） |
| 文件新鮮度 | `make doc-audit` |
| Tech Debt 彙總 | `make tech-debt-list` |
| 記錄任務 | `make task-start DESC="..."` |
| 任務狀態 | `make task-status` |
| 任務統計 | `make task-report` |
| Autopilot 初始化 | `make autopilot-init` |
| Autopilot 驗證 | `make autopilot-validate` |
| Autopilot 狀態 | `make autopilot-status` |
| Autopilot 重置 | `make autopilot-reset` |
| 建立 SRS | `make srs-new` |
| 建立 SDS | `make sds-new` |
| 建立 UI/UX Spec | `make uiux-spec-new` |
| 建立 Deploy Spec | `make deploy-spec-new` |

> 以上為常用指令，完整列表請執行 `make help`

---

## 技術執行層（Hooks + 內建權限）

ASP 採用「全開放 + 黑名單」策略：預設允許所有 Bash 指令，僅禁止危險操作。

| 機制 | 說明 |
|------|------|
| **Allow: `Bash(*)`** | 所有 Bash 指令預設允許，autopilot/autonomous 模式不會被無害指令中斷 |
| **Deny 黑名單** | 危險指令由 `.asp/hooks/denied-commands.json` 定義，Claude Code 自動阻擋 |
| **SessionStart Hook** | `clean-allow-list.sh` 每次 session 啟動時確保 allow + deny 規則正確，防止手動繞過 |

**被禁止的危險指令（deny list）：**

| 指令 | 原因 |
|------|------|
| `git push` | 鐵則：推送前必須人工確認 |
| `git rebase` | 鐵則：禁止改寫歷史 |
| `docker push / deploy` | 鐵則：部署需人工確認 |
| `rm -rf / rm -r` | 破壞性刪除 |

> 設定檔位於 `.claude/settings.json`，deny 規則位於 `.asp/hooks/denied-commands.json`，hook 腳本位於 `.asp/hooks/`。
> 如需新增禁止指令，編輯 `denied-commands.json` 即可，下次 session 自動生效。
