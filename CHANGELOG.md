# Changelog

本專案遵循 [Keep a Changelog](https://keepachangelog.com/zh-TW/1.1.0/) 格式，
版本號遵循 [Semantic Versioning](https://semver.org/lang/zh-TW/)。

---

## [Unreleased]

### UI 整併 + 工具頁面 Container 化 + 掃描修復（2026-03-05）

#### Added
- **War Room 頁面**：整併 Monitor + C5ISR + Navigator 為統一 War Room（`/warroom`）
- **Recon 掃描進度事件**：真實 nmap 掃描模式新增 `recon.progress` 階段事件（nmap_scan → initial_access → finalizing）
- **`ooda.completed` WebSocket 事件**：OODA 迴圈完成後廣播，確保前端在 DB 更新後刷新
- **msf-rpc 健康檢查**：`/api/health` 新增 msf-rpc 容器 TCP 連線偵測（`MOCK_METASPLOIT=false` 時）
- **OODA trigger service**：`backend/app/services/ooda_trigger.py`
- **AD playbook 測試**：`backend/tests/test_ad_playbooks.py`
- **Lateral topology 測試**：`backend/tests/test_lateral_topology.py`

#### Changed
- **5 頁面 → 3 頁面**：移除 `/monitor`、`/c5isr`、`/navigator`，整併至 `/warroom`
- **Tools 頁面 MCP → Container**：欄名 MCP Status → Container，移除 MCP summary bar，簡化為 ONLINE/OFFLINE/N/A 三態
- **Seed 工具 container 映射**：所有 seed 工具設定 `config_json.mcp_server`（ssh→credential-checker, persistent_ssh→attack-executor, winrm→credential-checker, metasploit→msf-rpc）
- **Recon 掃描 UI 修復**：真實掃描模式不再卡在「掃描中」，target 正確顯示 compromised 狀態
- **Planner 頁面**：訂閱 `ooda.completed` 事件以即時刷新數據
- **MCP client manager**：MCP-only 架構（Phase 7），移除直接工具執行路徑
- **Credential checker MCP**：擴充支援 WinRM 協定
- **Initial access engine**：強化 MCP 路由與 fallback 邏輯

#### Deprecated
- **C2 (Caldera) 工具**：從工具註冊表移除，engine routing 保留供未來替代方案

#### Removed
- **MCPServerStatusPanel 元件**：功能整併至 ToolRegistryTable
- **TopologyView 元件**：由 NetworkTopology 取代
- **AlertBanner 元件**：不再使用
- **3 個獨立頁面元件**：`c5isr/page.tsx`、`monitor/page.tsx`、`navigator/page.tsx`
- **11 個 MCP i18n key**：替換為 4 個 Container key

#### Metrics
- pytest: 297 passed, 0 failed
- TypeScript: `next build` clean
- 影響檔案：70+

### ASP 合規補齊 + 文件同步（2026-03-05）

#### Added
- **ADR-024**：MCP Architecture and Tool Server Integration — 補齊 MCP 架構決策文件
- **Makefile `postmortem-new` / `postmortem-list`**：新增事後分析管理指令
- **`docs/postmortems/`**：建立 Postmortem 目錄

#### Changed
- **Makefile `spec-list`**：增強為顯示狀態（優先讀 `**狀態**` 欄位，fallback 用 checklist 推算）
- **Makefile `help`**：新增 Postmortem 行
- **SPEC-015** Orient Prompt：13 項 Done When 全部標記為完成
- **SPEC-017** Anthropic SDK Migration：10 項全部標記為完成
- **SPEC-019** Recon & Initial Access：7 項全部標記為完成
- **SPEC-022** Agent Capability Matching：5 項全部標記為完成
- **SPEC-024** Phase F UX Terminal Topology：18 項全部標記為完成
- **SPEC-001/003/006/010**：補齊最後 1 項未勾選項目（附說明）

### UI Optimization Phases 1-5（SPEC-027）（2026-03-04）

#### Added
- **SlidePanel 元件**：`frontend/src/components/ui/SlidePanel.tsx` — 右側抽屜（sm/md/lg 三種寬度、backdrop blur、ESC 關閉、aria-modal）
- **VirtualList 元件**：`frontend/src/components/ui/VirtualList.tsx` — 泛型虛擬捲動（viewport windowing、auto-scroll-to-bottom）
- **SidebarContext**：`frontend/src/contexts/SidebarContext.tsx` — 側邊欄 expanded/collapsed 狀態管理
- **SectionHeader 元件**：`frontend/src/components/atoms/SectionHeader.tsx` — 統一 page/card 兩級 section header
- **Skeleton 元件**：`frontend/src/components/ui/Skeleton.tsx` — 8 個 skeleton 變體取代全頁掃描線
- **SVG NavIcons**：`frontend/src/components/atoms/NavIcons.tsx` — 5 個 SVG 導航圖示取代 Unicode 字元
- **MetricCard SVG 圓弧** + trend 指示器（gauge/trend props）
- **DomainCard SVG 六角邊框**（healthPct strokeDasharray）
- **HostNodeCard SVG 狀態圖示**（盾牌/雷達/破盾）
- **Button icon prop** + Planner 按鈕 SVG 圖示
- **MITRE Matrix compact mode** toggle（w-28 ↔ w-20）

#### Changed
- **Primary Button**：`bg-athena-accent/20` → `bg-athena-accent text-athena-bg font-bold`（實心填充）
- **全域 Focus 指示器**：新增 `:focus-visible` 規則（1px accent outline）
- **Modal backdrop**：4 個 Modal 改為 `bg-athena-bg/80 backdrop-blur-sm`（半透明毛玻璃）
- **最小字型底線**：`text-[8px]`/`text-[9px]` → `text-[10px]`（~28 個元件）
- **空狀態改善**：虛線邊框 + 引導文字（DataTable、Monitor、Planner、Navigator）
- **響應式斷點**：4 頁面加入 `lg:` 響應式前綴（grid-cols-2 lg:grid-cols-4 等）
- **Monitor 佈局重組**：從 6 層垂直堆疊改為固定高度 2x2 dashboard grid
- **可收合側邊欄**：expanded 224px ↔ collapsed 64px，icon-only + tooltip
- **Recommendation History**：從 inline accordion 移入 SlidePanel 右側抽屜
- **Live Log Stream**：改用 VirtualList 虛擬捲動
- **15+ inline header** 統一改用 SectionHeader 元件
- **4 頁面 PageLoading** 改用對應 Skeleton 元件
- **NetworkTopology** Canvas 節點加入角色圖示（DC/Server/Workstation/Router）

#### Metrics
- vitest: 27 files, 63 passed (0 regression)
- TypeScript: `next build` clean
- 影響檔案：40+ 前端元件

---

### Phase F：UX 精修 + LLM 監控 + Web Terminal + Topology Tab（2026-03-04）

#### Added
- **LLM 即時監控**：`backend/app/services/orient_engine.py` 在 LLM 呼叫前後廣播 `orient.thinking` WebSocket 事件（含 `status`、`backend`、`latency_ms` 欄位）
- **AIDecisionPanel LLM 狀態列**：`frontend/src/components/topology/AIDecisionPanel.tsx` 新增 `llmThinking`、`llmBackend`、`llmLatencyMs` 可選 props；AI 分析中顯示 `● ANALYZING...`，完成後顯示 latency
- **Recommendation History API**：`backend/app/routers/recommendations.py` 新增 `GET /operations/{op_id}/recommendations?limit=N` 端點（支援 1–100 筆分頁）
- **Recommendation History 面板**：`frontend/src/app/monitor/page.tsx` 在 RecommendationPanel 下方加可摺疊歷史列表（最多 20 筆，每筆可展開 situationAssessment）
- **Web Terminal 後端**：`backend/app/routers/terminal.py` 新增 WebSocket 端點 `ws://{op_id}/targets/{target_id}/terminal`，對已 compromised 目標建立 SSH 連線（asyncssh），支援互動式命令執行；安全黑名單防止破壞性指令
- **Web Terminal 前端 Hook**：`frontend/src/hooks/useTerminal.ts` WebSocket terminal hook，管理連線、entries、prompt、sendCommand
- **Web Terminal UI**：`frontend/src/components/terminal/TerminalPanel.tsx` 全螢幕 modal terminal，含輸入歷史（↑↓ 導航，最多 100 筆）、輸入/輸出/錯誤/系統 entry 色彩區分
- **TERMINAL 按鈕**：`frontend/src/app/planner/page.tsx` 在已 compromised 的 HostNodeCard 下方加 `▶ Terminal` 按鈕，點擊開啟 TerminalPanel modal
- **Topology Tab**：`frontend/src/app/monitor/page.tsx` 新增 `[OVERVIEW]` / `[TOPOLOGY]` Tab 切換（使用現有 `TabBar` 元件）
- **TopologyView 元件**：`frontend/src/components/topology/TopologyView.tsx` 全頁拓撲佈局（拓撲圖 3/4 + 節點詳情 1/4，Kill Chain 條貼底），高度動態計算填滿剩餘視窗
- **NodeDetailPanel 元件**：`frontend/src/components/topology/NodeDetailPanel.tsx` 點擊節點顯示 IP、OS、角色、Compromised 狀態、Kill Chain 進度條（7 階段彩色方塊）、已收集 Facts 清單
- **NetworkTopology 可互動性**：新增 `onNodeClick?: (nodeId: string) => void` 和 `nodeSizeMultiplier?: number` props；`height` 也可外部覆寫

#### Changed
- **OODA Timeline 重寫**：`frontend/src/components/ooda/OODATimeline.tsx` — 依 iterationNumber 分組、可摺疊（預設展開最新 1 個）、ORIENT 文字截斷（>150 字元 + [展開]）、phase filter chips（ALL/OBS/ORI/DEC/ACT）、預設顯示最新 3 個 iteration
- **移除 ACCEPT RECOMMENDATION 按鈕**：`frontend/src/components/ooda/RecommendationPanel.tsx` 移除 `handleAccept()`、ACCEPT 按鈕、`operationId`/`onAccepted` props（ACT 永遠自動執行，ACCEPT 只寫 DB 標記無功能意義）
- **Modal 背景不透明**：AddTargetModal、ReconResultModal、HexConfirmModal、TerminalPanel overlay 從 `bg-black/60`/`bg-black/70` 改為 `bg-black`（純黑背景，視覺清晰）
- **無目標時禁用操作按鈕**：`frontend/src/app/planner/page.tsx` OODA CYCLE、EXPORT、EXECUTE MISSION 三個按鈕在 `targets.length === 0` 時自動 disabled
- **網路拓撲節點縮小**：NetworkTopology 節點尺寸大幅縮小（DC: 16→3、compromised: 12→2、預設: 8→1.5），glow 層從 3 層改為 2 層，乘數從 6 改為 3，避免單節點填滿整個圖

#### Fixed
- **Web Terminal "Could not parse host"**：`terminal.py` credential 查詢未依 `source_target_id` 篩選，可能取得錯誤目標的憑證；credential 不含 `@host:port` 時未 fallback 至 target IP。修正：加入 `source_target_id` 篩選 + `host` 為空時使用 `target["ip_address"]`

#### Metrics
- pytest: 237 passed（0 regression）
- TypeScript: `tsc --noEmit` clean
- 影響檔案：10+ 前端元件、2 後端 router、1 後端 service

---

### Phase E Rev 2：第三方識別符深度去識別化（Deep De-branding）（2026-03-04）

#### Added
- `docs/adr/ADR-019-third-party-debranding.md` Rev 2 — 深度去識別化修訂（Enum 值替換 + DB 遷移 + Shannon 完全刪除）

#### Changed
- **ExecutionEngine Enum 值全面替換**（Rev 1 僅改名不改值 → Rev 2 值也替換）：
  - `"caldera"` → `"c2"`、`"shannon"` → 移除；新增 `"ssh"`、`"persistent_ssh"`、`"mock"`、`"metasploit"`、`"winrm"` 六個實際引擎值
  - Python enum（`backend/app/models/enums.py`）+ TypeScript enum（`frontend/src/types/enums.ts`）同步
- **DB Schema 遷移**（冪等 `try/except pass`）：
  - `ALTER TABLE techniques RENAME COLUMN caldera_ability_id TO c2_ability_id`
  - `UPDATE techniques/technique_executions/mission_steps SET engine='ssh' WHERE engine='caldera'`
  - `engine DEFAULT 'ssh'`（原 `'caldera'`）
- **EngineRouter 簡化**：移除 `adaptive_engine` 參數；`_execute_caldera()` → `_execute_c2()`；移除 Shannon 分支
- **OrientEngine**：mock 推薦 engine `"caldera"` → `"ssh"`、`"shannon"` → `"c2"`；系統提示詞 engine routing 段落重寫
- **DecisionEngine**：fallback default `"caldera"` → `"ssh"`
- **InitialAccessEngine**：`bootstrap_caldera_agent()` → `bootstrap_c2_agent()`
- **Router 更新**：`/techniques/sync-caldera` → `/techniques/sync-c2`；agents log message `"Caldera"` → `"C2 engine"`
- **Health API**：`ai_engine` 狀態區塊完全移除（非僅 key 重命名）
- **OODAController**：移除 AiEngineClient import、更新 EngineRouter 建構
- **Seed data**：`caldera_ability_id` → `c2_ability_id`、mission_steps engine `"caldera"` → `"ssh"`
- **API schemas**：`caldera_ability_id` → `c2_ability_id`（TechniqueCreate + TechniqueWithStatus）
- **Config**：移除 `AI_ENGINE_URL` 設定
- **Frontend types**：`calderaAbilityId` → `c2AbilityId`（technique.ts）
- **.env.example**：更新註解 `"caldera"` → `"c2"`、移除 `AI_ENGINE_URL=`
- **10+ 測試檔案**同步更新（test_spec_004/007/008、test_e2e_ooda、test_integration、test_playbook_crud、test_lateral_movement、AIDecisionPanel.test、TechniqueCard.test、useExecutionUpdate.test、LogEntryRow.test）

#### Removed
- `backend/app/clients/ai_engine_client.py` — Shannon client 完全刪除（非重命名保留）

#### Metrics
- pytest: 224 passed（0 regression）
- Vitest: 63 passed, 27 suites（0 regression）
- TypeScript: `tsc --noEmit` clean
- 影響 30+ 檔案

### UI 改善（2026-03-04）

#### Changed
- **AddTargetModal**：合併 HOSTNAME 與 IP/HOSTNAME/DOMAIN 為單一 TARGET 欄位；新增 `deriveHostname()` 自動推導 hostname
- **Sidebar 底部**：移除裝飾性 "System Operational" StatusDot + "VIPER-1 / Commander" 區塊，替換為 [GitHub](https://github.com/astroicers/Athena) 連結 + Apache-2.0 授權資訊

### Phase A：企業化外部滲透測試基礎建設（2026-03-01）

#### Added
- `backend/app/services/scope_validator.py` — `ScopeValidator`：ROE 範圍驗證，支援 IP、CIDR、域名、wildcard domain
- `backend/app/models/engagement.py` — `Engagement` 領域模型
- `backend/app/routers/engagements.py` — Engagement CRUD + activate/suspend 狀態機（4 個 endpoint）
- `backend/app/services/osint_engine.py` — `OSINTEngine`：crt.sh 被動枚舉 + subfinder + dnspython 解析，自動建立 Target 記錄
- `backend/app/models/osint.py` — `SubdomainInfo`, `OSINTResult`
- `backend/app/services/vuln_lookup.py` — `VulnLookupService`：NVD NIST API v2 + SQLite 24h 快取，將服務 banner 關聯至已知 CVE
- `backend/app/models/vuln.py` — `VulnFinding`
- `backend/app/models/enums.py` — `FactCategory.OSINT = "osint"` 新類別
- `backend/tests/test_scope_validator.py` — 7 個 ScopeValidator 單元測試
- `backend/tests/test_osint_engine.py` — 5 個 OSINTEngine 單元測試
- `backend/tests/test_vuln_lookup.py` — 6 個 VulnLookupService 單元測試
- `backend/tests/test_initial_access_engine.py` — 新增 2 個憑證鏈接測試
- `backend/app/models/report.py` — `Finding`, `AttackStep`, `PentestReport` 報告模型
- `backend/app/services/report_generator.py` — `ReportGenerator`：從 DB 組裝客戶可交付滲透測試報告（JSON + Markdown）
- `backend/tests/test_report_generator.py` — 6 個 ReportGenerator 單元測試

#### Changed
- `backend/app/database.py` — 新增 `engagements`、`vuln_cache` 2 個表（`CREATE TABLE IF NOT EXISTS`）
- `backend/app/config.py` — 新增 6 個設定：`OSINT_MAX_SUBDOMAINS`、`SUBFINDER_ENABLED`、`OSINT_REQUEST_TIMEOUT_SEC`、`NVD_API_KEY`、`NVD_CACHE_TTL_HOURS`、`VULN_LOOKUP_ENABLED`
- `backend/app/models/api_schemas.py` — 新增 `EngagementCreate` schema
- `backend/app/routers/recon.py` — 新增 `POST /osint/discover` endpoint；整合 `OSINTEngine`
- `backend/app/routers/reports.py` — 新增 `GET /report/structured`（PentestReport JSON）和 `GET /report/markdown`（text/markdown 下載）
- `backend/app/services/recon_engine.py` — Step 1b scope 驗證（graceful fallback）；Step 8 CVE 關聯呼叫（graceful fallback）
- `backend/app/services/initial_access_engine.py` — `_load_harvested_creds()`：先試已知憑證再嘗試預設清單（憑證鏈接）
- `backend/app/services/orient_engine.py` — Q11 查詢已收集憑證；Section 7.5 HARVESTED CREDENTIALS 加入提示詞
- `backend/app/main.py` — 載入 `engagements` router
- `backend/pyproject.toml` — 新增 `dnspython>=2.4.0`
- `CLAUDE.md` — Athena 核心定位段落（任意 IP/域名通用設計原則）
- `docs/architecture.md` — 核心展示目標段落、Phase A 模組清單

#### Metrics
- 後端：95 pytest passed, 6 skipped（+26 個新測試，0 regression）

---

### Phase 13：前端 UI 支援 Recon 測試流程（2026-02-28）

#### Added
- `frontend/src/types/recon.ts` — `ServiceInfo`, `InitialAccessResult`, `ReconScanResult` TypeScript 型別
- `frontend/src/components/modal/AddTargetModal.tsx` — 新增 Target 表單 Modal（hostname / IP / role / OS / network_segment）
- `frontend/src/components/modal/ReconResultModal.tsx` — Recon 掃描結果顯示 Modal（services、OS、initial access、agent status、TRIGGER OODA 按鈕）

#### Changed
- `frontend/src/components/cards/HostNodeCard.tsx` — 新增 `onScan` / `isScanning` prop；卡片底部顯示 [RECON SCAN] 按鈕
- `frontend/src/app/planner/page.tsx` — Target Hosts 側欄加入 [+ ADD] 按鈕 + `handleReconScan` 整合 + `ReconResultModal` 結果顯示

#### Metrics
- 前端：63 Vitest passed（0 TypeScript errors）
- 後端：69 pytest passed + 6 skipped

---

### Phase 13（Monitor UI）：Kill Chain 態勢感知（2026-02-28）

#### Added
- `frontend/src/hooks/useExecutionUpdate.ts` — 訂閱 `execution.update` WS 事件
- `frontend/src/hooks/__tests__/useExecutionUpdate.test.ts` — 4 tests
- `frontend/src/components/topology/AIDecisionPanel.tsx` — AI 決策面板（技術 ID / Kill Chain 階段 / 引擎 / 信心值）
- `frontend/src/components/topology/__tests__/AIDecisionPanel.test.tsx` — 5 tests

#### Changed
- `frontend/src/components/topology/NetworkTopology.tsx` — 匯出 `KILL_CHAIN_COLORS`；節點依 Kill Chain 階段繪製彩色環形邊框
- `frontend/src/app/monitor/page.tsx` — 新增 `KillChainIndicator`（7 段進度條）+ `AIDecisionPanel`（右側欄）

---

### Phase 12：Recon + Initial Access — Kill Chain 前半段補完（2026-02-28）

#### Added
- `backend/app/models/recon.py` — Pydantic models：`ServiceInfo`, `ReconResult`, `InitialAccessResult`, `ReconScanResult`
- `backend/app/services/recon_engine.py` — `ReconEngine`：nmap 掃描 + facts 寫入 + WS 廣播；含 mock 模式
- `backend/app/services/initial_access_engine.py` — `InitialAccessEngine`：asyncssh SSH credential 嘗試 + Caldera agent bootstrap
- `backend/app/routers/recon.py` — `POST /api/operations/{op_id}/recon/scan`、`GET .../recon/status`
- `backend/tests/test_recon_engine.py` — 3 tests
- `backend/tests/test_initial_access_engine.py` — 4 tests
- `docs/adr/ADR-015-recon--initial-access----kill-chain-.md` — Accepted
- `docs/specs/SPEC-019-phase-12-recon--initial-access--kill-chain-.md`

#### Changed
- `backend/pyproject.toml` — 新增 `python-nmap>=0.7.1`, `asyncssh>=2.14.0`, `cryptography>=42.0.0`
- `backend/app/database.py` — 新增第 13 張表 `recon_scans`
- `backend/app/main.py` — 掛載 `recon` router
- `backend/app/seed/demo_scenario.py` — 新增 T1592、T1595.002、T1110.003 種子資料

---

### SPEC-018：Tech-Debt 清償（2026-02-27）

#### Added
- 24 個新測試覆蓋 Phase 11 新模組
  - `backend/tests/test_reports.py`（5 tests）— 報告 API 10 段落、seed data、404
  - `backend/tests/test_admin.py`（5 tests）— Reset 204、WS broadcast、資料清除、狀態歸零、404
  - `frontend/src/contexts/__tests__/ToastContext.test.tsx`（4 tests）— provider 隔離、add/remove、auto-dismiss
  - `frontend/src/components/ui/__tests__/Toast.test.tsx`（3 tests）— 空狀態、severity labels、click dismiss
  - `frontend/src/components/ui/__tests__/PageLoading.test.tsx`（2 tests）— 文字、動畫點數
  - `frontend/src/components/ooda/__tests__/RecommendationPanel.test.tsx`（5 tests）— null、選項、展開、API accept、badge

#### Fixed
- `OODAIndicator.test.tsx` — Tailwind opacity class 斷言修正（`bg-athena-accent` → `bg-athena-accent/20`）

#### Changed
- 5 個模組移除 `tech-debt: test-pending` 標記
- `docs/specs/SPEC-018-phase11-demo-ready.md` — 全部 10 項 Done When ✅
- `docs/architecture.md` — tech-debt 條目標記已完成

#### Metrics
- 後端：61 pytest passed + 6 skipped
- 前端：54 Vitest passed
- 總計：115 個測試

### Phase 11：Demo 就緒 — UI/UX 精修 + OODA 資料完整性

#### Added
- `backend/app/routers/reports.py` — 報告匯出 API（GET `/operations/{op_id}/report`，含 10 段落 JSON）
- `backend/app/routers/admin.py` — 管理 API（POST `/operations/{op_id}/reset`，重置全部作戰資料）
- `frontend/src/contexts/ToastContext.tsx` — 全域 Toast 通知 Context + Provider
- `frontend/src/components/ui/Toast.tsx` — 堆疊式 Toast 元件（4 種 severity，3 秒自動消失）
- `frontend/src/components/ui/PageLoading.tsx` — 軍事風格掃描動畫 Loading 覆蓋層
- `frontend/src/components/ooda/RecommendationPanel.tsx` — OODA 建議面板元件

#### Changed
- `backend/app/services/ooda_controller.py` — OODA 四階段 side-effects：寫入 `log_entries`、推進 `mission_steps`、標記 `targets.is_compromised`、啟動 `agents`、更新 `operations` 計數器
- `backend/app/main.py` — 註冊 `reports` + `admin` 路由
- `frontend/src/app/c5isr/page.tsx` — 加入 `useWebSocket` 監聽 `c5isr.update`、Loading 狀態、Toast 錯誤處理
- `frontend/src/app/navigator/page.tsx` — 加入 `useWebSocket` 監聽 `execution.update`、Loading 狀態、Toast 錯誤處理
- `frontend/src/app/planner/page.tsx` — 加入多事件 WebSocket 監聽、自動刷新、Loading 狀態、Toast 錯誤處理、EXPORT 按鈕
- `frontend/src/app/monitor/page.tsx` — Loading 狀態、Toast 錯誤處理
- `frontend/src/components/layout/client-shell.tsx` — 掛載 ToastProvider、移除 CommandInput
- `frontend/src/lib/api.ts` — 新增 `createApiHelpers`（`fetchSafe` / `postSafe` 封裝）

#### Fixed
- `ooda_controller.py` — OODA 觸發後 `mission_steps` 不再永遠 QUEUED
- `ooda_controller.py` — OODA 觸發後 `log_entries` 不再永遠空白
- `ooda_controller.py` — 成功執行後 `targets.is_compromised` 正確更新
- `ooda_controller.py` — Agent status 從 pending 變 alive
- 四頁面 15 個靜默 `.catch(() => {})` 替換為 Toast 錯誤通知
- `.env` — `MOCK_CALDERA=false` → `true`、`CALDERA_URL` 修正為 Docker 內部位址 `http://caldera:8888`
- UI 對比度修復：C5ISR 域卡片、Navigator MITRE 矩陣、Monitor OODA 指示器、Sidebar 圖示

#### Removed
- `frontend/src/components/layout/CommandInput.tsx` — 從 `client-shell` 移除渲染（無後端 endpoint 的裝飾品）

### Phase 10：Orient Prompt 工程升級（SPEC-015）

#### Added
- `docs/adr/ADR-013-orient-prompt-engineering-strategy.md` — Orient prompt 策略決策記錄（借鏡 PentestGPT/hackingBuddyGPT/autopentest-ai/AttackGen/PentAGI 等 5 個開源專案）
- `docs/specs/SPEC-015-orient-prompt-engineering.md` — Orient prompt 工程實作規格
- `orient_engine.py` — 新增 `_ORIENT_SYSTEM_PROMPT`（靜態角色合約 + 5 個分析框架指令）
- `orient_engine.py` — 新增 `_ORIENT_USER_PROMPT_TEMPLATE`（動態 8 段落上下文模板）
- `orient_engine.py` — 新增 `_KILL_CHAIN_STAGES` MITRE ATT&CK 戰術進程常數
- `orient_engine.py` — 新增 5 個 helper 方法：`_format_task_tree`、`_format_ooda_history`、`_format_previous_assessments`、`_format_categorized_facts`、`_infer_kill_chain_stage`
- `test_spec_007_ooda_services.py` — 5 個新 prompt 結構測試：tuple 回傳、任務樹、OODA 歷史、分類情報、Claude system 參數

#### Changed
- `orient_engine.py` — `_build_prompt()` 回傳 `tuple[str, str]`（system + user），新增 5 個 SQL 查詢（mission_steps、ooda_iterations、recommendations、techniques tactic、facts）
- `orient_engine.py` — `_call_claude()` 使用 Anthropic API `system` 參數（不再嵌入 user message）
- `orient_engine.py` — `_call_openai()` 前置 `{"role": "system", ...}` message
- `orient_engine.py` — `_call_llm()` 簽章更新為 `(system_prompt, user_prompt)`

#### Removed
- `orient_engine.py` — 移除舊 `_ORIENT_PROMPT_TEMPLATE`（40 行單一 user message）

#### Prompt Engineering Patterns Adopted
| 模式 | 來源 | 授權 |
|------|------|------|
| 任務樹 / PTT | PentestGPT | MIT |
| Action + Reflection 雙 prompt | hackingBuddyGPT | MIT |
| 角色合約 | autopentest-ai | Apache 2.0 |
| MITRE ATT&CK 接地 | AttackGen / Threats2MITRE | 研究參考 |
| 三層記憶（輕量版） | PentAGI | MIT |

#### Metrics
- 25 個 SPEC-007 測試全數通過（20 existing + 5 new）
- 51 個 pytest 測試全數通過

### Phase 9.0：Caldera + LLM 真實整合修復

#### Fixed
- `orient_engine.py` — Anthropic API 版本從 `2023-06-01` 更新至 `2024-10-22`
- `orient_engine.py` — OpenAI 模型從已棄用的 `gpt-4-turbo-preview` 改為 `gpt-4-turbo`（可設定）
- `orient_engine.py` — Claude/OpenAI 回應空陣列安全存取（防止 IndexError）
- `orient_engine.py` — LLM 回傳 markdown 包裹 JSON（\`\`\`json...\`\`\`）時自動剝離
- `orient_engine.py` — LLM 回應缺少必要欄位時 fallback 至 mock（而非後續 dict 存取出錯）
- `.env` — 新增 `MOCK_CALDERA=true` 和 `MOCK_LLM=true`（之前缺少導致 `make real-mode` 的 sed 無效）
- `.env` — 移除從未被讀取的孤兒設定 `PENTESTGPT_API_URL` 和 `PENTESTGPT_MODEL`
- `Makefile` — `real-mode` / `mock-mode` targets 改用 `grep -q + sed || echo append` 確保即使 `.env` 缺少行也能切換

#### Added
- `backend/app/config.py` — 新增 `OPENAI_MODEL` 設定（預設 `gpt-4-turbo`）
- `backend/tests/test_integration_real_mode.py` — 8 個整合測試（4 LLM + 4 Caldera），無 API key 時自動跳過

### Phase 8.5：前端測試套件（SPEC-014）

#### Added
- `docs/specs/SPEC-014-frontend-test-suite.md` — 前端測試套件規格書
- `frontend/vitest.config.ts` — Vitest 配置（jsdom + react plugin + tsconfig paths）
- `frontend/src/test/setup.ts` — @testing-library/jest-dom 全域設定
- `frontend/src/lib/__tests__/api.test.ts` — 7 個 API 工具函式測試（toSnakeCase、fromApiResponse、api.get）
- `frontend/src/components/atoms/__tests__/*.test.tsx` — 12 個原子元件測試（Button 3 + Toggle 3 + Badge 2 + StatusDot 1 + ProgressBar 2 + HexIcon 1）
- `frontend/src/components/cards/__tests__/*.test.tsx` — 4 個卡片元件測試（MetricCard 2 + TechniqueCard 1 + RecommendCard 1）
- `frontend/src/components/data/__tests__/*.test.tsx` — 4 個資料元件測試（DataTable 3 + LogEntryRow 1）
- `frontend/src/components/modal/__tests__/HexConfirmModal.test.tsx` — 3 個模態元件測試（hidden/visible/critical double confirm）
- `frontend/src/components/ooda/__tests__/*.test.tsx` — 2 個 OODA 元件測試（OODAIndicator 1 + OODATimeline 1）
- `frontend/src/components/mitre/__tests__/MITRECell.test.tsx` — 1 個 MITRE 元件測試
- `frontend/src/components/c5isr/__tests__/DomainCard.test.tsx` — 1 個 C5ISR 元件測試
- `frontend/src/components/nav/__tests__/TabBar.test.tsx` — 1 個導覽元件測試
- `frontend/src/hooks/__tests__/*.test.ts` — 5 個 Hook 測試（useOperation 2 + useOODA 2 + useLiveLog 1）

#### Changed
- `frontend/package.json` — 新增 8 個 devDependencies（vitest、@vitest/coverage-v8、jsdom、@testing-library/react、@testing-library/jest-dom、@testing-library/user-event、vite-tsconfig-paths、@vitejs/plugin-react）+ test scripts
- `docs/specs/SPEC-005-frontend-foundation.md` — Done When 加入 `npm test` 要求
- `docs/specs/SPEC-006-four-screens.md` — Done When 加入 `npm test` 要求
- `.github/workflows/ci.yml` — frontend job 加入 `npm test` 步驟

#### Metrics
- 40 個 Vitest 測試全數通過（1.55s）
- 21 個測試檔案覆蓋 API utils + 6 原子元件 + 3 卡片 + 2 資料 + 1 模態 + 2 OODA + 1 MITRE + 1 C5ISR + 1 導覽 + 3 Hooks

---

### Phase 8：後端測試套件（SPEC-013）

#### Added
- `docs/specs/SPEC-013-backend-test-suite.md` — 後端測試套件規格書
- `backend/tests/conftest.py` — 測試基礎設施（in-memory SQLite + 4 個 fixtures）
- `backend/tests/test_spec_004_api.py` — 15 個 API smoke tests（health、operations CRUD、techniques、agents、C5ISR、logs、recommendations）
- `backend/tests/test_spec_007_ooda_services.py` — 20 個 OODA 服務單元測試（DecisionEngine 7 + OrientEngine 3 + FactCollector 3 + C5ISRMapper 4 + OODAController 3）
- `backend/tests/test_spec_008_clients.py` — 9 個執行引擎客戶端測試（MockCalderaClient 5 + ShannonClient 3 + CalderaClient 1）
- `backend/pyproject.toml` — 新增 `pytest-cov` 依賴 + pytest asyncio_mode=auto 配置

#### Changed
- `docs/specs/SPEC-004-rest-api-routes.md` — Done When 加入 `make test-filter FILTER=spec_004`
- `docs/specs/SPEC-007-ooda-loop-engine.md` — Done When 加入 `make test-filter FILTER=spec_007`
- `docs/specs/SPEC-008-execution-engine-clients.md` — Done When 加入 `make test-filter FILTER=spec_008`

#### Metrics
- 44 個 pytest 測試全數通過（0.21s）
- 程式碼覆蓋率：60%（`app/` 套件）

---

## [0.2.0] — 2026-03-02

### Added
- **Attack Path Timeline**：Navigator 頁新增 14 欄水平 MITRE ATT&CK 時序視圖（SPEC-021）
  - `GET /api/operations/{op_id}/attack-path` 新 endpoint（SQL JOIN technique_executions + techniques + targets）
  - `AttackPathEntry`、`AttackPathResponse` Pydantic models（`api_schemas.py`）
  - `frontend/src/types/attackPath.ts` TypeScript 型別
  - `frontend/src/components/mitre/AttackPathTimeline.tsx` — 14 欄水平時序元件（14 tactics, status pills, hover tooltip, highest-tactic accent border）
- **DirectSSHEngine**：SSH 直接執行引擎，取代 Caldera C2 為預設執行後端（ADR-017）
  - `backend/app/clients/direct_ssh_client.py`（新）— 實作 `BaseEngineClient` 介面
  - 13 個 MITRE technique → Shell 命令映射（初始 playbook）
  - SSH 登入成功後自動建立 agent 記錄（`_register_ssh_agent()`，paw=`SSH-{ip}`）
  - `CALDERA_MOCK_BEACON` 設定：跳過 30s beacon wait（供 CI 測試）
- **Technique Playbook DB 表**：`technique_playbooks`（13 個種子 technique）（ADR-018）
- **ADR-017**：DirectSSHEngine 架構決策記錄
- **ADR-018**：Technique Playbook 知識庫架構決策記錄
- **SPEC-021**：Attack Path Timeline 功能規格書

### Changed
- `EXECUTION_ENGINE` 新設定預設為 `"ssh"`（`caldera` 向後相容，`mock` 供測試）
- `engine_router.py`：三軌路由（ssh/caldera/mock），ssh 路徑移除 alive agent 硬性要求
- `initial_access_engine.py`：SSH 登入成功後自動呼叫 `_register_ssh_agent()`；`bootstrap_caldera_agent()` 僅在 `EXECUTION_ENGINE=caldera` 時呼叫
- `README.md`：架構圖、技術棧、功能描述全面更新反映新架構（v0.2.0）
- `ADR-001/005/006/015`：加入修訂記錄說明 PentestGPT/Caldera/Shannon 的實際狀態
- `frontend/src/app/navigator/page.tsx`：Attack Path Timeline 整合於 ATT&CK 矩陣上方
- `frontend/src/lib/api.ts`：新增 `getAttackPath()` API call

### Deprecated
- `shannon_client.py`：標記 `DEPRECATED`，保留程式碼但無啟用路徑（`SHANNON_URL` 預設空）
- `bootstrap_caldera_agent()`：僅在 `EXECUTION_ENGINE=caldera` 時呼叫

### Metrics
- pytest: 95 passed, 6 skipped（0 regression）
- Vitest: 63 passed（0 regression）
- 新增 technique_playbooks 種子資料：13 techniques（Linux）
- 新增 API endpoint：`GET /attack-path`
- 新增前端元件：`AttackPathTimeline`（14-column horizontal timeline）

---

## [0.7.0] — 2026-02-26

### Phase 7：文件與開源發佈（SPEC-011 / SPEC-012）

#### 7.1 文件撰寫

- 重寫 `README.md`：專案首頁含架構圖、快速啟動、功能亮點、進度追蹤
- 新增 `docs/GETTING_STARTED.md`：從零開始的安裝與開發指南
- 新增 `docs/DEMO_WALKTHROUGH.md`：6 步 OODA 循環 Demo 操作手冊
- 更新 `CHANGELOG.md`：補齊 Phase 1~6 所有變更紀錄

#### 7.1.5 Vendor 整合（SPEC-012）

- 新增 `infra/caldera/docker-compose.caldera.yml` — 獨立 Caldera Docker 配置
- 新增 `infra/README.md` — 基礎設施管理指南（Caldera 操作、備份、版本相容性）
- 新增 `infra/pentestgpt/README.md` — PentestGPT 研究參考說明
- 修正 `health.py` — 真實 Caldera 連線檢查（G2）
- 實作 `agents.py` sync — 真實 Agent 同步（G3 + G8）
- 加入 `caldera_client.py` retry 邏輯 + 版本檢查（G4 + G7）
- 清理 `config.py` — 移除未使用的 PentestGPT 設定（G9）
- Makefile 新增 9 個 vendor 管理 targets

#### 7.2 開源合規

- 新增 `LICENSE` — Apache License 2.0 全文
- 所有 48 個 Python 原始碼檔加入 14 行 Apache 2.0 License Header
- 所有 54 個 TypeScript/TSX 原始碼檔加入 Apache 2.0 License Header
- 新增 `CONTRIBUTING.md` — 貢獻指南（開發設定、程式碼規範、PR 流程）
- 新增 `SECURITY.md` — 安全政策（漏洞揭露流程、範圍、時間表）
- 更新 `backend/pyproject.toml` — 加入 license、description 欄位
- 更新 `frontend/package.json` — 加入 license、description、repository 欄位
- Shannon AGPL-3.0 合規驗證通過（僅 HTTP API 呼叫，無程式碼匯入）

#### 7.3 GitHub Repository

- 新增 `.github/workflows/ci.yml` — GitHub Actions CI（ruff lint + pytest + npm lint + build + docker）
- 新增 `.github/ISSUE_TEMPLATE/bug_report.yml` — Bug 回報模板（YAML 表單）
- 新增 `.github/ISSUE_TEMPLATE/feature_request.yml` — 功能請求模板
- 新增 `.github/PULL_REQUEST_TEMPLATE.md` — PR 模板含 Checklist
- 新增 `frontend/.eslintrc.json` — ESLint 配置（next/core-web-vitals）
- Ruff lint 配置 + 自動修正 18 處 import 排序問題
- Dockerfile 加入 OCI image labels（title、description、license、version）

#### 7.4 首次發佈

- 標記 `v0.1.0` — Athena POC Release
- 新增 `scripts/add_license_headers.py` — License Header 批次新增工具

---

## [0.6.0] — 2026-02-26

### Phase 6：整合與 Docker 部署（SPEC-009 / SPEC-010）

#### Added
- `backend/app/seed/demo_runner.py` — 自動化 6 步 OODA Demo 腳本（支援 `DEMO_STEP_DELAY` 與 retry 邏輯）
- `backend/Dockerfile` — Python 3.11-slim 容器映像，含 HEALTHCHECK
- `backend/.dockerignore` — 排除 `__pycache__/`、`.venv/`、`tests/`、`data/*.db`
- `frontend/Dockerfile` — 多階段 Node 20-alpine 建構，standalone 輸出
- `frontend/.dockerignore` — 排除 `node_modules/`、`.next/`、`out/`
- `docker-compose.yml` — 完整服務編排：healthcheck、named volume、`service_healthy` 依賴
- Makefile 新增 `up`、`down`、`docker-clean` targets

#### Changed
- `/api/health` 增強：回報 `mock`/`connected`/`disabled`/`active`/`claude`/`openai`/`unavailable` 等動態狀態
- `frontend/next.config.js` 加入 `output: "standalone"` 支援容器化部署

---

## [0.5.0] — 2026-02-26

### Phase 5：OODA 循環引擎（SPEC-007 / SPEC-008）

#### Added
- `backend/app/services/ooda_controller.py` — OODA 循環控制器（trigger/advance/get_state）
- `backend/app/services/pentestgpt_client.py` — PentestGPT 情報客戶端（Mock + 真實模式）
- `backend/app/services/caldera_client.py` — Caldera 執行引擎客戶端（Mock + 真實模式）
- `backend/app/services/shannon_client.py` — Shannon 執行引擎客戶端（Mock + 真實模式）
- `backend/app/routers/ooda.py` — OODA API 路由（trigger、advance、get state）

#### Fixed
- 程式碼審查修正：2 個 Critical + 6 個 Important + 4 個 Minor 問題（`a6beec4`）
- 提取 `_activate_if_planning()` 輔助方法，移除 7 個重複的狀態檢查區塊（`7e6b2bf`）

---

## [0.4.0] — 2026-02-26

### Phase 4：畫面實作（SPEC-006）

#### Added
- 4 個核心畫面：C5ISR Board、MITRE Navigator、Mission Planner、Battle Monitor
- 15 個 React 元件實作
- 3D 拓樸視覺化整合（react-force-graph-3d + Three.js）

#### Fixed
- `HexIcon` 的 `bg-current` 與 `Toggle` 的 `translate-x` 修正（`38dc16a`）

---

## [0.3.0] — 2026-02-26

### Phase 3：前端基礎（SPEC-005）

#### Added
- TypeScript 型別定義（對應後端 13 個 Enum + 12 個 Model）
- Next.js App Router 佈局（`layout.tsx`、`page.tsx`）
- 自訂 Hooks：`useWebSocket`、`useApi`
- 原子元件：`HexButton`、`HexIcon`、`StatusBadge`、`Toggle`、`KPICard`

---

## [0.2.0] — 2026-02-25

### Phase 2：後端基礎（SPEC-002 / SPEC-003 / SPEC-004）

#### Added
- Pydantic v2 模型與 13 個 Enum（`SPEC-002`）
- SQLite 資料庫層 + aiosqlite 非同步存取（`SPEC-003`）
- PHANTOM-EYE 種子資料（OP-2024-017 完整作戰場景）
- FastAPI 進入點 + CORS 中介層（`SPEC-004`）
- REST API 路由：operations、techniques、c5isr、missions
- WebSocket 管理器（即時事件推播）

#### Fixed
- Pydantic V2 棄用警告修正：`config.py` 改用 `model_config`（`8fea392`）
- `get_db()` 回傳型別標註修正為 async generator（`129cebc`）
- `_ensure_operation` 去重複 + `C5ISRUpdate` schema 搬遷（`7c2b86e`）
- Pydantic model 預設值對齊 SQL schema（`c566fe3`）

---

## [0.1.1] — 2026-02-25

### Phase 1：專案骨架（SPEC-001）

#### Added
- Monorepo 專案結構（`backend/`、`frontend/`）
- `backend/pyproject.toml` — Python 依賴宣告（FastAPI、uvicorn、aiosqlite、httpx）
- `frontend/package.json` — Next.js 14 + React 18 + Tailwind CSS v4
- `frontend/tsconfig.json`、`tailwind.config.ts`、`postcss.config.mjs`
- `backend/app/config.py` — Pydantic Settings 環境變數管理
- `.gitkeep` 檔案確保空目錄版本追蹤

#### Changed
- ASP 框架升級至 v1.2.0：hooks、精簡 CLAUDE.md（`cef2123`）

---

## [0.1.0] — 2026-02-25

### Phase 0：設計與架構（Design & Architecture）

#### Added
- 6 個 `.pen` 設計稿（Design System、Shell、C5ISR Board、MITRE Navigator、Mission Planner、Battle Monitor）
- 資料架構文件（13 Enum、12 Model、12 張 SQL Schema、35+ REST API、7 種 WebSocket 事件、種子資料）
- 專案結構文件（Monorepo 佈局、前後端分層職責）
- 開發路線圖（ROADMAP.md — Phase 0-8）
- 12 份 ADR（ADR-001 ~ ADR-012），涵蓋技術棧、OODA 引擎、授權隔離、前端架構等關鍵決策
- 10 份 SPEC（SPEC-001 ~ SPEC-010），涵蓋 Phase 1-6 全部實作規格
- ASP 框架（v1.2.0）整合：profiles、hooks、templates、Makefile targets
- CLAUDE.md v4（AI 助手完整上下文文件）
- `.env.example`（環境變數範本）
- `.gitignore`（Python、Node.js、SQLite、憑證檔排除）

#### Changed
- `.pen` 設計檔從根目錄搬入 `design/`
- `data-architecture.md` 反向更新：Technique.description、User seed data、ON DELETE CASCADE、/health endpoint
- `project-structure.md` 修正：TrafficStream.tsx 歸屬 topology/、設計檔路徑更新

---

[Unreleased]: https://github.com/astroicers/Athena/compare/v0.7.0...HEAD
[0.7.0]: https://github.com/astroicers/Athena/compare/v0.6.0...v0.7.0
[0.6.0]: https://github.com/astroicers/Athena/compare/v0.5.0...v0.6.0
[0.5.0]: https://github.com/astroicers/Athena/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/astroicers/Athena/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/astroicers/Athena/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/astroicers/Athena/compare/v0.1.1...v0.2.0
[0.1.1]: https://github.com/astroicers/Athena/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/astroicers/Athena/releases/tag/v0.1.0
