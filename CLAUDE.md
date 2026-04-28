# AI-SOP-Protocol (ASP) — 行為憲法

> 讀取順序：本檔案 → `.ai_profile` → 對應 `.asp/profiles/`（按需）

---

## 專案概覽

<!-- ASP-AUTO-PROJECT-DESCRIPTION: START -->
> **AI-SOP-Protocol (ASP)** — 軟體開發流程治理框架。
> 把開發文化（ADR 先於實作、測試先於代碼、部署必須確認）寫成機器可讀的約束，讓 AI 自動遵守。
> 20 個 Profile 分層載入、10 個 Claude Code 原生 Skill、7 維度健康審計、Autopilot 持續執行。
> 詳見 README.md。
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

  // ─── mode: auto 支援 ───
  IF loaded.mode == "auto":
    LOG("mode: auto — multi-agent profiles 將按需動態載入")

  // ─── multi-agent 依賴保證 ───
  IF "multi_agent" IN loaded.profiles AND "task_orchestrator" NOT IN loaded.profiles:
    AUTO_LOAD("task_orchestrator.md")
    LOG("mode: multi-agent → 自動載入 task_orchestrator.md")
```

```yaml
# .ai_profile 完整欄位參考
type:         system | content | architecture   # 必填
level:        1 | 2 | 3 | 4 | 5                # 預設 1 — ASP 成熟度等級（見下方 Maturity Levels）
mode:         auto | single | multi-agent | committee  # 預設 auto（AI 自動判斷是否並行）
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
| `mode: auto`（預設） | 不預載 multi-agent profiles，由 `auto_select_mode()` 動態判斷 |
| `mode: multi-agent` | + `.asp/profiles/multi_agent.md` + `.asp/profiles/task_orchestrator.md`（自動）+ `.asp/profiles/pipeline.md` + `.asp/profiles/escalation.md` |
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
| `mode: multi-agent` + `autonomous: enabled` | + 上述 + `.asp/profiles/reality_checker.md` + `.asp/profiles/dev_qa_loop.md` + `.asp/profiles/agent_memory.md` |

---

## 🎯 Maturity Levels（v3.5 新增）

ASP 採用 **5 級成熟度模型**，讓使用者從 L1 開始逐級升級，不必一次面對 20 個 profile 的組合爆炸。等級定義在 `.asp/levels/level-N.yaml`。

| Level | 名稱 | 核心能力 | 適用場景 |
|-------|------|---------|---------|
| **L1** | Starter | ADR + SPEC + 測試（最小治理） | 剛採用 ASP、個人/小型專案 |
| **L2** | Disciplined | + guardrail + coding_style | 熟悉 ADR 流程、想自動化品質護欄 |
| **L3** | Test-First | + pipeline gates G1-G6 | 測試文化成熟、需要可觀測證據 |
| **L4** | Collaborative | + multi-agent + reality-checker | 中大型專案、跨模組、獨立 QA 需求 |
| **L5** | Autonomous | + autopilot + RAG | ROADMAP 驅動、跨 session 續接 |

### 等級管理

- `.ai_profile` 的 `level:` 欄位決定當前等級（預設 `1`）
- `make asp-level-check` — 查詢目前等級與 graduation 進度
- `make asp-level-upgrade` — 準備升級（需先通過 graduation_checklist）
- `make asp-level-list` — 列出所有等級概覽
- `/asp-level` skill — 逐項驗證 graduation 條件、執行升級/降級

### 等級推斷規則（legacy 相容）

當 `.ai_profile` 無 `level` 欄位時，AI 根據已啟用的 profile 推斷：

| 已啟用 profile | 推斷等級 |
|---------------|---------|
| 只有 global_core + system_dev | L1 |
| + guardrail 或 coding_style | L2 |
| + pipeline 或 openapi | L3 |
| + mode: multi-agent | L4 |
| + autopilot: enabled 或 autonomous: enabled | L5 |

推斷結果僅供參考，建議執行 `make asp-level-check` 後手動確認並補上 `level:` 欄位。

---

## 🔴 鐵則（不可覆蓋）

以下規則在任何情況下不得繞過：

| 鐵則 | 說明 |
|------|------|
| **破壞性操作防護** | `rebase / rm -rf / docker push / git push` 等危險操作由 Claude Code 內建權限系統確認（SessionStart hook 自動清理 allow list）；`git push` 前必須先列出變更摘要並等待人類明確同意 |
| **敏感資訊保護** | 禁止輸出任何 API Key、密碼、憑證，無論何種包裝方式。`asp-ship` Step 9 掃描硬編碼密碼 |
| **ADR 未定案禁止實作** | ADR 狀態為 Draft 時，禁止撰寫對應的生產代碼；必須等 ADR 進入 Accepted 狀態。**v3.4 硬性執行**：`session-audit.sh` 動態注入 `git commit` deny，VSCode 會彈出阻擋對話框。解除方式：`make asp-unlock-commit` |
| **外部事實驗證防護（v3.7）** | 涉及第三方版本/API/法規時，必須先執行 Fact Verification Gate，驗證結果記錄在 `.asp-fact-check.md`。禁止以訓練資料記憶偽裝為當下事實。見 `global_core.md`「外部事實驗證閘」節 |

---

## 🔒 強制力架構（v3.4）

ASP 採用 4 層混合強制力架構，在 VSCode 插件限制下實現最大覆蓋：

| Layer | 機制 | 強制力等級 | 覆蓋範圍 |
|-------|------|-----------|---------|
| **L1: Smart SessionStart** | `session-audit.sh` — 專案審計 + briefing | 硬（session 啟動時輸出） | Profile 驗證、檔案結構、ADR 狀態、Tech Debt |
| **L2: Dynamic Deny List** | 根據專案狀態動態阻擋 `git commit` | **硬**（VSCode deny dialog） | ADR 鐵則、機密防護、測試未通過 |
| **L3: Skill-Enforced Gates** | `asp-ship`（10 步）+ `asp-gate`（G1-G6） | 結構化軟性 | Pipeline 全生命週期品質門檻 |
| **L4: Subagent Verification** | `reality-checker` 獨立 subagent | 中等 | 測試竄改偵測、邊界案例覆蓋 |

### 啟動行為

1. Session 啟動時，`session-audit.sh` 自動執行並產生 `.asp-session-briefing.json`
2. **AI 必須讀取 `.asp-session-briefing.json`**，向使用者報告任何 BLOCKER
3. 如有 Draft ADR，`git commit` 已被動態阻擋（deny list），使用者需 `make asp-unlock-commit` 解除

### 強制 Skill 調用點

以下 skill 在指定時機**必須**被調用。跳過時必須輸出繞過警告。

| 時機 | 必須調用的 Skill | 阻擋級別 |
|------|-----------------|----------|
| 非 trivial 任務開始前（v3.7） | 輸出 Assumption Checkpoint（見 `global_core.md`） | 必須等使用者確認假設才繼續 |
| 涉及外部事實的任務前（v3.7） | 執行 Fact Verification Gate，記錄至 `.asp-fact-check.md` | 必須完成才能進入 G1 |
| 開始實作前 | `/asp-gate G1,G2` | 必須通過才能寫 production code |
| 測試寫完、實作前 | `/asp-gate G3` | 必須確認測試 FAIL |
| 實作完成、提交前 | `/asp-gate G4` + `/asp-ship` | 必須通過才能 commit |
| 驗證階段 | `/asp-gate G5` + `/asp-reality-check` | 必須通過 |
| 交付前 | `/asp-gate G6` | 必須通過才能標記完成 |
| Bug 修復後 | `/asp-qa`（含 grep 全專案） | 必須執行 |
| 任何 git commit 前 | `/asp-ship` | 必須通過（10 步驟） |

### 繞過警告

如使用者要求跳過任何強制 skill，AI **必須**輸出：

```
⚠️ ASP BYPASS: 跳過 [skill name]，違反規則 [rule ID]。
原因：[使用者提供的理由]
此繞過已記錄，但不建議。
```

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
| Gherkin 場景先於測試 | 非 trivial 功能必須先寫測試矩陣 + Gherkin 場景，再寫測試代碼 | trivial（單行/typo/配置）或 config-only 可豁免，需標記 `tech-debt: scenario-pending` |
| 使用者面向功能須定義可觀測性 | API / 資料處理 / 排程任務必須填寫 Observability 欄位 | 純 UI 或 config 變更可標注 N/A |

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
| Runbook 列表 | `make runbook-list` |
| 查閱 Runbook | `make runbook-view SCENARIO=...` |
| Agent 交接單清單 | `make agent-handoff-list` |
| Agent 交接單檢視 | `make agent-handoff-view ID=...` |
| Agent 並行軌道 | `make agent-tracks` |
| Agent 升級歷史 | `make agent-escalation-log` |
| Agent 記憶 | `make agent-memory-show` |
| Agent 記憶修剪 | `make agent-memory-prune AGE=90` |
| Agent 團隊推薦 | `make agent-team-recommend TYPE=... COMPLEXITY=...` |
| 解除動態 commit 阻擋 | `make asp-unlock-commit` |
| 重新執行 session 審計 | `make asp-refresh` |
| 強制力狀態 | `make asp-enforcement-status` |
| 成熟度等級檢查 | `make asp-level-check` |
| 成熟度等級列表 | `make asp-level-list` |
| 升級等級 | `make asp-level-upgrade` |
| Bypass log 檢視 | `make asp-bypass-review` |
| 手動記錄 bypass | `make asp-bypass-record SKILL=... STEP=... REASON="..."` |

> 以上為常用指令，完整列表請執行 `make help`

---

## 技術執行層（Hooks + 內建權限）

ASP 採用「全開放 + 黑名單」策略：預設允許所有 Bash 指令，僅禁止危險操作。

| 機制 | 說明 |
|------|------|
| **Allow: `Bash(*)`** | 所有 Bash 指令預設允許，autopilot/autonomous 模式不會被無害指令中斷 |
| **Deny 黑名單（靜態）** | 危險指令由 `.asp/hooks/denied-commands.json` 定義，Claude Code 自動阻擋 |
| **Deny 黑名單（動態）** | `session-audit.sh` 根據專案狀態（Draft ADR、測試未通過）動態注入額外 deny 規則 |
| **SessionStart Hook 1** | `clean-allow-list.sh` — 清理 allow list + 清理上次 session 的動態 deny |
| **SessionStart Hook 2** | `session-audit.sh` — 專案審計 + 產生 briefing + 注入動態 deny |

**被禁止的危險指令（deny list）：**

| 指令 | 原因 |
|------|------|
| `git push` | 鐵則：推送前必須人工確認 |
| `git rebase` | 鐵則：禁止改寫歷史 |
| `docker push / deploy` | 鐵則：部署需人工確認 |
| `rm -rf / rm -r` | 破壞性刪除 |

> 設定檔位於 `.claude/settings.json`，deny 規則位於 `.asp/hooks/denied-commands.json`，hook 腳本位於 `.asp/hooks/`。
> 如需新增禁止指令，編輯 `denied-commands.json` 即可，下次 session 自動生效。
