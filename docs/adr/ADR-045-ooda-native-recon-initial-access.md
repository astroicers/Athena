# [ADR-045]: OODA-Native Recon and Initial Access

| 欄位 | 內容 |
|------|------|
| **狀態** | `Accepted` |
| **日期** | 2026-04-01 |
| **決策者** | System Architect |

---

## 背景（Context）

Athena 的 OODA 循環引擎（ADR-003）定義了 Observe → Orient → Decide → Act 四階段決策流程。然而，Reconnaissance（TA0043）和 Initial Access（TA0001）目前被實作為 OODA 循環外的獨立手動操作：

1. **手動 Recon 流程**：使用者必須在 War Room 點擊 `[RECON SCAN]` 按鈕觸發 `POST /recon/scan`，掃描結果以 `iterationNumber === 0`（sentinel 值）儲存，與 OODA 時間線視覺割裂
2. **Initial Access 綁定在 Recon**：`enable_initial_access: true` 參數讓認證嘗試自動跟隨 Recon 執行，跳過 DecisionEngine 的 7 層風險閘門和噪音預算檢查
3. **C2 Agent 部署是 Recon 副作用**：`bootstrap_c2_agent()` 在 `recon.py:_run_scan_background()` 中被呼叫，不經過 OODA Act 階段
4. **雞生蛋問題**：OODA 的 FactCollector 依賴成功執行的技術來提取情報，但第一次偵察不在 OODA 循環內，導致使用者必須手動操作才能啟動 OODA
5. **重複路徑**：`ReconEngine.scan()` 被兩條路徑呼叫（手動按鈕 + OODAController Observe 階段的 sparse target 自動偵察），造成維護負擔

這違反 OODA 的基本定義：Recon **就是** Observe（情報收集），Initial Access **就是** Orient→Decide→Act 的自然流程。

---

## 評估選項（Options Considered）

### 選項 A：保留手動按鈕，改善 OODA 自動偵察

- **優點**：最小變更，使用者保留直接控制
- **缺點**：仍有兩條路徑、sentinel 割裂、IA 仍跳過風險閘門
- **風險**：架構矛盾持續存在

### 選項 B：完全整合 — Recon 成為 Observe，IA 成為 Orient→Decide→Act

- **優點**：架構一致；IA 經過完整風險評估；移除重複路徑；使用者流程簡化為 ADD TARGET → OODA 自動啟動
- **缺點**：前端重構（移除按鈕、modal、sentinel 過濾）；Orient 系統提示詞需增強
- **風險**：冷啟動（0 facts）場景需妥善處理；SR 模式下自動掃描可能消耗噪音預算

### 選項 C：保留按鈕但內部改為觸發 OODA cycle

- **優點**：使用者習慣不變
- **缺點**：仍有特殊路徑，不是真正的統一

---

## 決策（Decision）

選擇 **選項 B**：完全整合 Recon 和 Initial Access 為 OODA 原生階段。

具體決策：

1. **Recon 成為 OODA Observe 階段的自然部分**：OODAController 的 Observe 階段偵測到 0 facts 或 stale facts 的目標時，自動執行 `ReconEngine.scan()`，尊重噪音預算和 Mission Profile 閾值
2. **Initial Access 解耦為 Orient→Decide→Act 標準流程**：Orient 分析開放端口後推薦 T1110/T1078 技術；DecisionEngine 7 層閘門正常評估風險；EngineRouter 新增路由將 T1110/T1078 導向 `InitialAccessEngine`
3. **移除 `iterationNumber === 0` sentinel**：所有偵察結果作為正常 OODA iteration 記錄
4. **新增目標自動觸發 OODA**：`create_target()` 完成後自動呼叫 `auto_trigger_ooda()`
5. **移除前端手動操作**：移除 RECON SCAN 按鈕、ReconResultModal 的 TRIGGER OODA 按鈕、ReconBlock sentinel 過濾
6. **C2 Agent 部署移至 Act 階段**：`bootstrap_c2_agent()` 由 EngineRouter 在 Act 階段執行
7. **Recon API 降級為內部服務**：`POST /recon/scan` 保留供 OODAController 內部呼叫，不再面向使用者

---

## 後果（Consequences）

**正面影響：**
- OODA 循環完整性：Observe = 偵察、Orient = 分析、Decide = 風險評估、Act = 執行，無例外
- Initial Access 經過完整的複合信心值評估和噪音預算檢查
- 使用者流程簡化：ADD TARGET → 系統自動處理一切
- C5ISR ISR 域自然反映偵察覆蓋率
- 移除重複路徑，減少維護負擔
- Mission Profile 感知偵察（SR 模式保守、FA 模式激進）

**負面影響 / 技術債：**
- 使用者無法直接「手動掃描特定目標」— 需透過 Directive 指示 OODA 重新偵察（可接受，因 Directive 機制已存在）
- Orient 系統提示詞需增強以涵蓋 TA0043→TA0001 轉換邏輯
- 需更新多個 SPEC（SPEC-007、SPEC-008、SPEC-019、SPEC-040、SPEC-047）的追溯性

**受影響的 ADR：**
- ADR-003（OODA Engine）— Observe 階段職責擴展
- ADR-006（Execution Engine Routing）— 新增 T1110/T1078 路由
- ADR-040（C5ISR Reverse Influence）— ISR 域新增偵察覆蓋率指標
