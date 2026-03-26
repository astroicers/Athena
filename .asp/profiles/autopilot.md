# Autopilot Profile — Roadmap 驅動持續執行

<!-- requires: global_core, system_dev, autonomous_dev, task_orchestrator -->
<!-- optional: multi_agent, vibe_coding, design_dev, openapi, frontend_quality, coding_style, rag_context -->
<!-- conflicts: (none) -->

適用：AI 讀取 ROADMAP.yaml 持續執行任務，直到全部完成或 context 預算耗盡。
載入條件：`.ai_profile` 中 `autopilot: enabled`

> **設計原則**：Autopilot 是外層迴圈，不重新發明內層邏輯。
> 每個任務仍走 `task_orchestrator.on_task_received()` 的完整流程（ADR → SPEC → TDD → 實作 → 文件）。
> Autopilot 只負責：讀 Roadmap → 排序 → 逐一餵入 → 管理跨 session 狀態。

---

## 啟用前提

必須同時滿足：
1. `.ai_profile` 設定 `autopilot: enabled`
2. 專案根目錄存在 `ROADMAP.yaml`（可透過 `make autopilot-init` 建立）
3. `autonomous_dev.md` 和 `task_orchestrator.md` 已載入（自動載入）

---

## 前置文件動態探測

Autopilot 根據 ROADMAP.yaml 的 `stack` 和 `requires` 欄位自動判斷哪些前置文件是必要的：

```
FUNCTION detect_required_documents(roadmap):

  required = ["ROADMAP.yaml", roadmap.documents.srs]  // SRS 永遠必要

  IF roadmap.stack.backend != "none" OR roadmap.stack.database != "none":
    required.append(roadmap.documents.sds)  // 後端/資料層需 SDS

  IF roadmap.requires.uiux OR roadmap.stack.frontend != "none":
    required.append(roadmap.documents.uiux_spec)  // 前端需 UI/UX Spec

  IF roadmap.requires.api:
    IF roadmap.documents.sds NOT IN required:
      required.append(roadmap.documents.sds)  // API 需 SDS 的合約段落

  IF roadmap.stack.infra != "none":
    required.append(roadmap.documents.deploy_spec)  // 部署需 Deploy Spec

  missing = [doc FOR doc IN required IF NOT exists(doc)]
  IF missing:
    PRESENT("📝 自動建立缺失的前置文件：")
    FOR doc IN missing:
      reason = infer_reason(doc, roadmap)
      PRESENT("  - {doc}（原因：{reason}）")
      auto_create(doc)  // make srs-new / sds-new / uiux-spec-new / deploy-spec-new
    LOG("自動建立了 {LEN(missing)} 個前置文件模板")

  RETURN required
```

---

## CLAUDE.md 專案描述自動產生

Autopilot 從 ROADMAP.yaml + `.ai_profile` + SRS 自動產生 CLAUDE.md 的「專案概覽」區塊。
觸發時機：`make autopilot-validate`（驗證通過後）及 autopilot 每次啟動（Phase 1.5）。

```
FUNCTION ensure_project_description():
  // 由 .asp/scripts/update-project-description.py 實作

  IF NOT exists("CLAUDE.md") OR NOT exists("ROADMAP.yaml"):
    LOG("⚠️ 缺少必要檔案，跳過專案描述產生")
    RETURN

  IF "ASP-AUTO-PROJECT-DESCRIPTION: START" NOT IN READ("CLAUDE.md"):
    LOG("⚠️ CLAUDE.md 缺少標記，跳過")
    RETURN

  roadmap = PARSE("ROADMAP.yaml")
  profile = PARSE(".ai_profile")
  srs_summary = extract_first_paragraph(roadmap.documents.srs)

  new_desc = FORMAT("""
    專案名稱 / 類型 / 模式 / 工作流
    技術棧（frontend / backend / database / infra / 架構 / API / 認證）
    開發規範（命名 / commit / 分支 / 錯誤處理 / 語言）
    專案簡述（來自 SRS 第一段）
  """)

  existing = extract_between("CLAUDE.md", START_MARKER, END_MARKER)
  IF existing == new_desc:
    LOG("ℹ️ CLAUDE.md 專案描述已是最新")
  ELSE:
    replace_between("CLAUDE.md", START_MARKER, END_MARKER, new_desc)
    LOG("🔄 CLAUDE.md 專案描述已更新")
```

### Phase 6.5: README.md 產生/修訂

Autopilot 完成所有任務後，自動產生或修訂 README.md：

```
FUNCTION ensure_project_readme():
  // ─── 收集資訊來源 ───
  roadmap = READ("ROADMAP.yaml")
  changelog = READ("CHANGELOG.md") IF EXISTS
  srs = READ("docs/specs/SRS.md") IF EXISTS
  ai_profile = READ(".ai_profile")
  makefile = READ("Makefile") IF EXISTS

  IF NOT EXISTS("README.md"):
    // ─── 全新產生 ───
    GENERATE "README.md" with sections:
      - 專案名稱 + 簡介（from roadmap.description OR srs 第一段）
      - 功能列表（from roadmap completed milestones/tasks）
      - 安裝方式（from Dockerfile / requirements.txt / package.json / Makefile）
      - 使用方式（from CLI entry points / API endpoints / 程式碼分析）
      - 開發指引（make test, make lint, make build 等常用指令）
      - 架構概覽（link to docs/architecture.md if exists）
      - License（if LICENSE file exists）
    LOG("📝 README.md 已自動產生")

  ELSE:
    // ─── 修訂現有 README ───
    existing_readme = READ("README.md")
    REVIEW and UPDATE:
      - 功能列表是否反映最新 ROADMAP 完成項
      - 安裝/使用方式是否與當前程式碼一致
      - 是否有過時或不正確的描述
      - 是否遺漏重要的新功能
    PRESERVE: 手動撰寫的客製化內容（不覆蓋使用者特意編寫的段落）
    LOG("📝 README.md 已修訂更新")
```

---

## Profile 自動載入

Autopilot 根據 ROADMAP.yaml 的 `requires` 欄位補充載入 profile：

```
FUNCTION auto_configure_profiles(roadmap):

  IF roadmap.requires.uiux:
    ENSURE_LOADED("design_dev")
    ENSURE_LOADED("frontend_quality")

  IF roadmap.requires.api:
    ENSURE_LOADED("openapi")

  IF roadmap.requires.multi_agent:
    ENSURE_LOADED("multi_agent")

  IF roadmap.requires.rag:
    ENSURE_LOADED("rag_context")

  IF roadmap.requires.coding_style:
    ENSURE_LOADED("coding_style")

  LOG("Auto-loaded profiles: {newly_loaded_profiles}")
```

> `ENSURE_LOADED` 檢查 profile 是否已由 `.ai_profile` 載入，若未載入則動態載入。
> 這讓 ROADMAP.yaml 的 `requires` 欄位能補充 `.ai_profile` 未設定的 profile。

---

## 核心流程

```
FUNCTION autopilot_main():

  // ═══ Phase 0: Resume or Fresh Start ═══
  state = LOAD_FILE(".asp-autopilot-state.json")

  IF state AND state.status == "in_progress":
    PRESENT("🤖 Autopilot 偵測到未完成的執行")
    PRESENT("  已完成: {LEN(state.completed)}/{state.total_tasks}")
    PRESENT("  中斷於: {state.current_task}（{state.exit_reason}）")
    PRESENT("  剩餘: {state.total_tasks - LEN(state.completed)} 個任務")
    state.session_count += 1
    LOG("🤖 Autopilot 自動續接 session #{state.session_count}")
    // 重讀檔案系統，不信任上個 session 的 context
    VALIDATE_ENVIRONMENT()
  ELSE:
    state = {
      version: 1,
      status: "init",
      started_at: NOW(),
      session_count: 1,
      completed: [],
      failed: [],
      blocked: []
    }

  // ═══ Phase 0.5: Load Agent Memory（v3.0）═══
  IF exists(".asp-agent-memory.yaml"):
    agent_memory = LOAD(".asp-agent-memory.yaml")
    LOG("📚 Agent memory 已載入（{LEN(agent_memory.fix_strategies)} 個修復策略，{LEN(agent_memory.common_failures)} 個常見失敗模式）")
  ELSE:
    agent_memory = { version: 1, fix_strategies: [], team_effectiveness: [], common_failures: [] }
    LOG("📚 Agent memory 為空（首次執行）")

  IF exists(".asp-agent-session.json"):
    agent_session = LOAD(".asp-agent-session.json")
    LOG("📋 上次 session agent 狀態已載入（團隊：{agent_session.team_composition.scenario}）")

  // ═══ Phase 1: Load ROADMAP & Auto-Configure ═══
  roadmap = PARSE("ROADMAP.yaml")

  // 自動載入 profile
  auto_configure_profiles(roadmap)

  // 記錄技術棧資訊（供後續任務使用）
  LOG("Tech stack: {roadmap.stack}")
  LOG("Conventions: {roadmap.conventions}")
  LOG("Architecture: {roadmap.architecture}")

  // ═══ Phase 1.5: Update CLAUDE.md Project Description ═══
  IF exists(".asp/scripts/update-project-description.py"):
    ensure_project_description()
  ELSE:
    WARN("Script .asp/scripts/update-project-description.py 不存在，跳過專案描述更新")

  // ═══ Phase 2: Validate Prerequisites ═══
  errors = []

  // 驗證前置文件（自動建立缺少的模板）
  IF exists("Makefile") AND make_target_exists("autopilot-validate"):
    detect_required_documents(roadmap)
  ELSE:
    WARN("detect_required_documents 無法執行（Makefile 或 target 不存在），跳過前置文件檢查")

  // ─── 強制為所有任務建立 SPEC（提前至 Phase 2）───
  FOR task IN roadmap.all_tasks():
    IF task.spec == null:
      spec = EXECUTE("make spec-new TITLE=\"{task.title}\"")
      IF task.srs_ref AND exists(roadmap.documents.srs):
        srs_content = READ(roadmap.documents.srs)
        fr = extract_fr(srs_content, task.srs_ref)
        FILL spec.goal FROM fr.description
        FILL spec.done_when FROM fr.acceptance_criteria
      ELSE:
        FILL spec FROM task.description
      task.spec = spec.id
      UPDATE_ROADMAP(task)
      LOG("📋 Task {task.id}: SPEC 已自動建立 → {spec.id}")

  // ─── 驗證 ADR 狀態 + 智能評估架構影響 ───
  blocked_by_adr = []
  FOR task IN roadmap.all_tasks():
    IF task.adr:
      // 明確指定 ADR 的 task：驗證 ADR 是否存在且已 Accepted
      adr = FIND_ADR(task.adr)
      IF NOT adr:
        LOG("Task {task.id}: ADR {task.adr} 不存在 → 自動建立 Draft ADR")
        EXECUTE("make adr-new TITLE=\"{task.adr}\"")
        blocked_by_adr.append(task.id)  // Draft ADR → 無法實作，標記 blocked
      ELIF adr.status != "Accepted":
        LOG("Task {task.id}: {task.adr} 狀態為 {adr.status} → 標記 blocked")
        blocked_by_adr.append(task.id)
    ELSE:
      // adr: null 的 task：智能評估是否需要 ADR
      impact = assess_architecture_impact(task)  // 呼叫 task_orchestrator.md 的函式
      IF impact.requires_adr:
        adr_title = "ADR: {task.title}"
        EXECUTE("make adr-new TITLE=\"{adr_title}\"")
        task.adr = adr_title
        UPDATE_ROADMAP(task)
        blocked_by_adr.append(task.id)
        LOG("🏗️ Task {task.id}: 架構影響評估需要 ADR（{impact.reasons}）→ 自動建立 Draft，標記 blocked")

  // 驗證依賴圖無環
  cycle_tasks = []
  IF has_cycle(roadmap.dependency_graph()):
    cycle_tasks = find_cycle_participants(roadmap.dependency_graph())
    LOG("⚠️ 依賴循環涉及: {cycle_tasks} → 標記 blocked")

  // 標記所有受阻任務（含依賴受阻任務的下游任務）
  blocked_tasks = blocked_by_adr + cycle_tasks
  blocked_tasks = expand_dependents(blocked_tasks, roadmap)  // 遞迴展開下游
  FOR task_id IN blocked_tasks:
    task = roadmap.get_task(task_id)
    task.status = "blocked"
    state.blocked.append(task_id)
    UPDATE_ROADMAP(task)

  IF blocked_tasks:
    PRESENT("⚠️ {LEN(blocked_tasks)} 個任務因 ADR/依賴問題被標記 blocked，繼續執行其他獨立任務")

  IF errors:
    PRESENT("⚠️ 前置驗證有問題（已自動處理）：")
    FOR err IN errors:
      PRESENT("  - {err}")

  // ═══ Phase 3: Build Task Queue ═══
  pending = roadmap.all_tasks().filter(t => t.status IN ["pending", "blocked"])
  queue = topological_sort(pending, key=(depends_on, priority))
  state.total_tasks = LEN(roadmap.all_tasks())

  IF queue.empty:
    PRESENT("✅ 所有任務已完成！")
    state.status = "completed"
    SAVE_STATE(state)
    RETURN

  PRESENT("🤖 Autopilot 任務佇列（{LEN(queue)} 個待執行）：")
  FOR task IN queue:
    deps = task.depends_on or "none"
    PRESENT("  {task.id}: [{task.type}] {task.title} (deps: {deps})")

  IF state.status == "init":
    LOG("🤖 開始自動執行 {LEN(queue)} 個任務")

  // ═══ Phase 4: Health Audit ═══
  health = project_health_audit()  // 複用 task_orchestrator
  IF health.has_blockers:
    remediate_gaps(health)

  // ═══ Phase 5: Execute Loop ═══
  state.status = "in_progress"
  SAVE_STATE(state)

  FOR task IN queue:

    // ─── Context 預算檢查 ───
    IF context_usage() > 75%:
      state.exit_reason = "context_budget"
      state.exit_detail = "Context 使用率 {context_usage()}%"
      SAVE_STATE(state)
      UPDATE_ROADMAP_STATUSES(roadmap)
      PRESENT("⏸️ Context 預算達上限，已儲存 checkpoint")
      PRESENT("  開新 session 後 autopilot 會自動提示續接")
      RETURN

    // ─── 依賴檢查 ───
    unmet = [d FOR d IN task.depends_on IF d NOT IN state.completed]
    IF unmet:
      task.status = "blocked"
      state.blocked.append(task.id)
      UPDATE_ROADMAP(task)
      LOG("Task {task.id} blocked by: {unmet}")
      CONTINUE

    // ─── 確認 SPEC 存在（Phase 2 已建立）───
    IF task.spec == null:
      // 防禦性：不應發生（Phase 2 已強制建立），但以防萬一
      LOG("⚠️ Task {task.id}: SPEC 缺失（應在 Phase 2 建立），自動補建")
      spec = EXECUTE("make spec-new TITLE=\"{task.title}\"")
      FILL spec FROM task.description
      task.spec = spec.id
      UPDATE_ROADMAP(task)

    // ─── 執行任務 ───
    state.current_task = task.id
    task.status = "in_progress"
    state.last_updated = NOW()
    UPDATE_ROADMAP(task)
    SAVE_STATE(state)

    LOG("═══ Executing: {task.id} [{task.type}] {task.title} ═══")

    // 建構 task_orchestrator 的輸入
    request = {
      title:       task.title,
      type:        task.type,
      spec:        task.spec,
      description: task.description,
      stack:       roadmap.stack,
      conventions: roadmap.conventions,
      architecture: roadmap.architecture
    }

    // 透過 task_orchestrator 入口執行
    result = on_task_received(request)

    IF result.success:
      task.status = "completed"
      state.completed.append(task.id)
      UPDATE_ROADMAP(task)
      SAVE_STATE(state)
      LOG("✅ Task {task.id} completed ({LEN(state.completed)}/{state.total_tasks})")

      // 更新 milestone 狀態
      milestone = get_milestone(task, roadmap)
      IF all_tasks_completed(milestone):
        milestone.status = "completed"
        UPDATE_ROADMAP(milestone)

    ELSE IF result.needs_human:
      task.status = "blocked"
      state.blocked.append(task.id)
      state.exit_reason = "human_intervention"
      state.exit_detail = result.pause_reason
      SAVE_STATE(state)
      UPDATE_ROADMAP(task)
      PRESENT("⏸️ Task {task.id} 需要人類介入: {result.pause_reason}")
      PRESENT("  處理完成後開新 session，autopilot 會自動續接")
      RETURN

    ELSE IF result.failed:
      task.status = "failed"
      state.failed.append(task.id)
      UPDATE_ROADMAP(task)
      SAVE_STATE(state)
      LOG("❌ Task {task.id} failed, continuing to next independent task")
      // 不中斷，繼續下一個不依賴此 task 的任務

    // ─── 階段性 Context 品質自檢 ───
    IF context_usage() > 60%:
      SAVE_STATE(state)  // 預防性 checkpoint

  // ═══ Phase 6: Completion ═══
  state.status = "completed"
  state.exit_reason = "all_done"
  state.last_updated = NOW()
  SAVE_STATE(state)

  EXECUTE("make audit-health")

  // ═══ Phase 6.5: README.md 產生/修訂 ═══
  ensure_project_readme()

  PRESENT("═══════════════════════════════════════")
  PRESENT("  🤖 Autopilot 執行完成")
  PRESENT("═══════════════════════════════════════")
  PRESENT("  總任務: {state.total_tasks}")
  PRESENT("  完成:   {LEN(state.completed)}")
  PRESENT("  失敗:   {LEN(state.failed)}")
  PRESENT("  阻塞:   {LEN(state.blocked)}")
  PRESENT("  Sessions: {state.session_count}")
  PRESENT("═══════════════════════════════════════")
```

---

## Session Bridge 狀態檔

檔案：`.asp-autopilot-state.json`（加入 `.gitignore`）

```json
{
  "version": 1,
  "status": "in_progress",
  "started_at": "2026-03-12T10:00:00Z",
  "last_updated": "2026-03-12T14:30:00Z",
  "session_count": 3,
  "total_tasks": 8,
  "roadmap_file": "ROADMAP.yaml",
  "current_task": "T003",
  "completed": ["T001", "T002"],
  "failed": [],
  "blocked": [],
  "exit_reason": "context_budget",
  "exit_detail": "Context at 78% after T002 completion"
}
```

**與現有 session-checkpoint 的差異**：
- 固定 schema，機器可解析（非 narrative markdown）
- 包含確切的 task ID，可精準續接
- ROADMAP.yaml 的 status 變更會 commit（團隊可見），state 檔不 commit（session 暫存）

---

## ROADMAP 更新規則

```
FUNCTION UPDATE_ROADMAP(item):
  // 原地更新 ROADMAP.yaml 中的 task/milestone status
  // 只更新 status 欄位，不修改 task 的定義（title/type/description/depends_on）
  READ "ROADMAP.yaml"
  UPDATE item.status
  WRITE "ROADMAP.yaml"

FUNCTION UPDATE_ROADMAP_STATUSES(roadmap):
  // 批次更新所有 task 的 status
  // 用於 checkpoint 存檔前確保 ROADMAP 與 state 同步
  FOR task IN roadmap.all_tasks():
    IF task.id IN state.completed: task.status = "completed"
    IF task.id IN state.failed: task.status = "failed"
    IF task.id IN state.blocked: task.status = "blocked"
  WRITE "ROADMAP.yaml"
```

---

## 安全邊界

Autopilot 繼承 `autonomous_dev.md` 的所有安全邊界，並增加以下限制：

### 可自主執行（不暫停）

| 類別 | 範圍 | 條件 |
|------|------|------|
| **讀取 ROADMAP** | 解析任務佇列 | 永遠 |
| **自動建立 SPEC** | `make spec-new` + 填寫 | task.spec 為 null 時 |
| **更新 ROADMAP status** | 修改 task/milestone 狀態 | 任務完成/失敗/阻塞時 |
| **更新 state 檔** | 寫入 `.asp-autopilot-state.json` | 每次任務開始/完成時 |
| **動態載入 profile** | `ENSURE_LOADED()` | ROADMAP requires 欄位 |
| **跳過 blocked task** | 繼續下一個獨立任務 | 依賴未滿足時 |

### Autopilot 自主處理策略（零確認）

Autopilot 模式下不暫停人類，所有情境自動處理：

| 原暫停項 | Autopilot 自動行為 |
|---------|-------------------|
| **首次啟動** | 直接開始執行，輸出任務佇列 LOG |
| **續接** | 自動續接，輸出 LOG |
| **前置文件缺失** | 自動執行 `make srs-new` 等指令建立模板 |
| **ADR 不存在** | 自動建立 Draft ADR，標記相關 task 為 blocked 並跳過 |
| **ADR 未 Accepted** | 標記相關 task 為 blocked 並跳過（不違反鐵則） |
| **依賴循環** | 標記涉及的 tasks 為 blocked，繼續其他獨立 task |
| **git push** | 不 push，僅 commit。結束時報告 "N commits ready to push" |
| **git rebase** | 禁止。使用 merge |
| **docker push / deploy** | 跳過，記錄 post-autopilot 待辦 |
| **刪除檔案** | SPEC 範圍內暫存檔可刪；其他檔案備份（.bak）後刪 |
| **範圍超出** | 記錄 `tech-debt` 標記，繼續當前 task |
| **新增外部依賴** | ROADMAP stack 定義的標準依賴自動允許；非標準記 tech-debt |
| **DB Schema 變更** | SPEC 指定時自動執行；未指定記 tech-debt |
| **auto_fix 失敗** | task 標記 failed，跳過，繼續下一個獨立 task |

### 禁止（即使 autopilot 模式也不可）

| 類別 | 說明 |
|------|------|
| **修改 ROADMAP task 定義** | 不可修改 title/type/description/depends_on/priority |
| **新增非 ROADMAP 任務** | 不可自行新增 ROADMAP 中不存在的任務 |
| **跳過 SPEC 建立** | 每個 task 必須有對應 SPEC |
| **ADR 狀態變更** | 繼承 autonomous_dev 鐵則 |
| **跳過 TDD** | 繼承 autonomous_dev 鐵則 |

---

## Context 管理

Autopilot session 通常很長，context 管理尤其重要：

| 觸發條件 | 動作 |
|----------|------|
| 完成一個 task | 輸出 task 完成摘要（修改了哪些檔案、測試結果） |
| context > 60% | 預防性存檔 state |
| context > 75% | 存檔 checkpoint + ROADMAP 更新 + 優雅退出 |
| 偵測到 context decay 信號 | 停止開發，存檔，建議新 session |

---

## 與其他 Profile 的關係

```
autopilot.md
  ├── 依賴 autonomous_dev.md（安全邊界 + auto_fix_loop）
  ├── 依賴 task_orchestrator.md（on_task_received() 入口 + 健康審計）
  ├── 依賴 system_dev.md（ADR/SPEC/TDD 流程）
  ├── 依賴 global_core.md（鐵則 + 連帶修復）
  ├── 可選 multi_agent.md（並行任務執行，由 ROADMAP.requires 觸發）
  ├── 可選 vibe_coding.md（context 衰退偵測）
  ├── 可選 design_dev.md（Design Gate，由 ROADMAP.requires.uiux 觸發）
  ├── 可選 openapi.md（OpenAPI Gate，由 ROADMAP.requires.api 觸發）
  ├── 可選 frontend_quality.md（前端品質，由 ROADMAP.requires.uiux 觸發）
  ├── 可選 coding_style.md（程式碼風格，由 ROADMAP.requires.coding_style 觸發）
  └── 可選 rag_context.md（知識庫查詢，由 ROADMAP.requires.rag 觸發）
```

Autopilot 是最外層的調度 profile，包裹所有其他 profile 的功能。
不啟用 autopilot 時，所有既有行為完全不變。
