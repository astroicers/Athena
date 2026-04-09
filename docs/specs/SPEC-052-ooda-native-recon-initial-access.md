# SPEC-052：OODA-Native Recon and Initial Access

| 欄位 | 內容 |
|------|------|
| **規格 ID** | SPEC-052 |
| **關聯 ADR** | ADR-045 |
| **估算複雜度** | 高 |

---

## 🎯 目標（Goal）

> 將 Reconnaissance（TA0043）和 Initial Access（TA0001）從獨立手動操作整合為 OODA 循環的原生階段。
> Recon 成為 Observe 的自然部分（新目標自動偵察，尊重噪音預算和 Mission Profile）。
> Initial Access 由 Orient 推薦 → Decide 評估風險 → Act 執行，經過完整的 7 層風險閘門。
> 移除前端手動 RECON SCAN 按鈕、ReconBlock sentinel 過濾、ReconResultModal。

---

## ✅ 驗收標準（Done When）

- [ ] 新增目標後自動觸發 OODA cycle #1（`auto_trigger_ooda` 被呼叫）
- [ ] Observe 階段偵測 0 facts 目標 → 自動執行 `ReconEngine.scan()`
- [ ] Observe 自動偵察尊重噪音預算（SR 模式預算不足 → 跳過掃描，記錄 log）
- [ ] Observe 自動偵察使用 Mission Profile 感知閾值（SR=0, CO=2, SP=3, FA=5）
- [ ] 無 `iterationNumber === 0` sentinel 記錄（所有偵察結果為正常 OODA iteration）
- [ ] Orient 系統提示詞包含 Recon→IA 轉換指引（T1110/T1078 推薦）
- [ ] EngineRouter 正確路由 T1110/T1078 至 `InitialAccessEngine`
- [ ] Initial Access 經過 DecisionEngine 7 層風險閘門評估
- [ ] C2 Agent 部署在 Act 階段由 EngineRouter 觸發（非 Recon 副作用）
- [ ] `recon.py` 移除 `enable_initial_access` 參數及相關邏輯
- [ ] `recon.py` 移除 recon 完成後的 `auto_trigger_ooda`
- [ ] ISR 域健康度包含偵察覆蓋率指標
- [ ] 前端移除：RECON SCAN 按鈕、ReconBlock.tsx、ReconResultModal.tsx
- [ ] 前端移除：`iterationNumber === 0` 過濾邏輯
- [ ] i18n keys 同步更新（en.json + zh-TW.json）
- [ ] `technique_rules.yaml` 包含 T1046（TA0043）和 T1078.001（TA0001）規則
- [ ] `make test` 通過，無回歸
- [ ] README、CHANGELOG、DESIGN_MAP、UIUX_SPEC 更新完成
- [ ] 相關 SPEC（007, 008, 019, 040, 047）追溯性更新

---

## 🔗 副作用與連動（Side Effects）

- `POST /recon/scan` 降級為內部 API（OODAController 內部呼叫）
- `POST /recon/initial-access` 標記為 deprecated
- ReconBlock.tsx、ReconResultModal.tsx 被刪除
- Orient 系統提示詞新增 Rule 8（Recon→IA 轉換）

---

## 🧪 測試矩陣（Test Matrix）

### 新增測試

| 測試 | 檔案 | 驗證內容 |
|------|------|---------|
| `test_target_creation_auto_triggers_ooda` | `test_ooda_recon_integration.py` | 建立目標 → auto_trigger_ooda 被呼叫 |
| `test_observe_auto_recon_zero_facts` | `test_ooda_recon_integration.py` | 0 facts → ReconEngine.scan() 被呼叫 |
| `test_observe_auto_recon_respects_noise_budget` | `test_ooda_recon_integration.py` | SR + 預算不足 → 跳過掃描 |
| `test_observe_auto_recon_mission_profile_threshold` | `test_ooda_recon_integration.py` | SR/CO/SP/FA 不同閾值 |
| `test_no_iteration_zero_sentinel` | `test_ooda_recon_integration.py` | 無 iterationNumber === 0 |
| `test_orient_recommends_t1110_after_recon` | `test_initial_access_ooda.py` | SSH 開放 → T1110 推薦 |
| `test_initial_access_through_decide_act` | `test_initial_access_ooda.py` | T1110 經 Decide → Act |
| `test_engine_router_routes_t1110_to_initial_access` | `test_initial_access_ooda.py` | T1110 → InitialAccessEngine |
| `test_c2_bootstrap_only_in_act_phase` | `test_initial_access_ooda.py` | C2 部署僅在 Act |

### 更新現有測試

| 測試檔案 | 變更 |
|----------|------|
| `test_recon_router.py` | 移除 `enable_initial_access` 參數測試 |
| `test_ooda_auto_loop.py` | 更新 auto-recon 行為驗證 |

---

## 🎬 驗收場景（Acceptance Scenarios）

### Scenario 1: 新目標自動偵察

```gherkin
Given 一個 active 狀態的 Operation（mission_profile=SP）
When 使用者新增一個目標（IP: 192.168.1.100）
Then 系統在 2 秒後自動觸發 OODA cycle
And Observe 階段偵測目標有 0 facts
And 自動執行 nmap 掃描
And 掃描結果以 iterationNumber >= 1 儲存
And Timeline 顯示 Observe 階段包含偵察結果
```

### Scenario 2: SR 模式噪音預算保護

```gherkin
Given 一個 SR 模式的 Operation（噪音預算剩餘 1 點）
And nmap 掃描消耗 2 噪音點
When OODA Observe 階段偵測到 0 facts 目標
Then 跳過自動掃描
And 記錄 log "Auto-recon deferred: noise budget insufficient"
And Observe 階段以空情報完成
And Orient 收到空情報上下文
```

### Scenario 3: Initial Access 經風險閘門

```gherkin
Given 一個 SP 模式的 Operation
And 目標有 service.open_port 包含 SSH(22)
When Orient 分析情報
Then 推薦 T1110.001（Brute Force: Password Guessing）作為選項之一
And DecisionEngine 評估 T1110.001 風險為 MEDIUM
And 複合信心值 >= 0.5
Then Act 階段由 EngineRouter 路由至 InitialAccessEngine
And InitialAccessEngine 嘗試 SSH 認證
```

### Scenario 4: C2 Agent 部署在 Act 階段

```gherkin
Given Initial Access 成功取得 SSH 認證
And C2_BOOTSTRAP_ENABLED = true
When EngineRouter 執行 T1110.001 成功
Then 在同一 Act 階段呼叫 bootstrap_c2_agent()
And C2 Agent 部署結果寫入 technique_execution
And 不是由 recon.py 觸發
```

---

## 📊 可觀測性（Observability）

| 指標 | 來源 | 說明 |
|------|------|------|
| `ooda.observe.auto_recon.triggered` | OODAController | 自動偵察觸發次數 |
| `ooda.observe.auto_recon.deferred` | OODAController | 因噪音預算延遲的次數 |
| `ooda.observe.auto_recon.completed` | OODAController | 成功完成的自動偵察次數 |
| `c5isr.isr.recon_coverage_pct` | C5ISRMapper | 偵察覆蓋率百分比 |
| `engine_router.initial_access.routed` | EngineRouter | T1110/T1078 路由至 IA 引擎次數 |

---

## 🔗 追溯性（Traceability）

| 實作檔案 | 測試檔案 | 最後驗證日期 |
|----------|----------|-------------|
| `backend/app/routers/targets.py` | `backend/tests/test_ooda_recon_integration.py` | — |
| `backend/app/services/ooda_controller.py` | `backend/tests/test_ooda_recon_integration.py` | — |
| `backend/app/services/orient_engine.py` | `backend/tests/test_initial_access_ooda.py` | — |
| `backend/app/services/engine_router.py` | `backend/tests/test_initial_access_ooda.py` | — |
| `backend/app/routers/recon.py` | `backend/tests/test_recon_router.py` | — |
| `backend/app/services/c5isr_mapper.py` | `backend/tests/test_c5isr_mapper.py` | — |
| `backend/app/data/technique_rules.yaml` | `backend/tests/test_attack_graph.py` | — |
| `frontend/src/app/warroom/page.tsx` | — | — |
| `frontend/src/components/warroom/TargetDetailPanel.tsx` | — | — |
