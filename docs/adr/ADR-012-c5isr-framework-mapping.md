# [ADR-012]: C5ISR 框架映射架構

| 欄位 | 內容 |
|------|------|
| **狀態** | `Accepted` |
| **日期** | 2026-02-23 |
| **決策者** | 專案負責人 |

---

## 背景（Context）

C5ISR（Command, Control, Communications, Computers, Cyber, Intelligence/Surveillance/Reconnaissance）是 Athena 的**核心組織框架**——CLAUDE.md 明確宣告「所有功能必須映射至此」。它將軍事 C5ISR 作戰框架應用於網路戰，是 Athena 與一般滲透測試工具的根本差異。

需記錄以下架構決策：

1. 為何採用軍事 C5ISR 六域分類（而非自定義分類或無框架）
2. 六域如何映射至 Athena 的功能模組
3. `health_pct` 0-100 健康度聚合邏輯
4. C5ISR 與 OODA 循環的關係（橫切關注 vs 第五階段）
5. `/c5isr` 作為主儀表板的 UI 定位
6. 8 種 `C5ISRDomainStatus` 的語義定義

---

## 評估選項（Options Considered）

### 選項 A：軍事 C5ISR 六域框架

將 Athena 所有功能映射至軍事標準 C5ISR 六域：

```
C5ISR Domain          Athena 功能映射               資料來源
─────────────────   ───────────────────────────   ──────────────────────
Command（指揮）      OODA 決策引擎                  Operation.current_ooda_phase
                     指揮官審批流程                  Operation.automation_mode
Control（管制）      Agent 管理與心跳               Agent.status（alive/dead）
                     作戰執行狀態                    TechniqueExecution.status
Comms（通訊）        WebSocket 即時通訊              WS 連線狀態
                     API 通訊健康度                  Backend health check
Computers（資訊）    目標主機清單與狀態              Target[] + 探測結果
                     基礎設施健康                    Docker service status
Cyber（網路戰）      Caldera/Shannon 執行            TechniqueExecution（引擎回報）
                     MITRE ATT&CK 技術覆蓋          techniques_executed
ISR（情偵監）        PentestGPT 情報分析              PentestGPTRecommendation
                     情報收集（Observe）             Fact[] 情報庫
```

- **優點**：
  - 軍事 C5ISR 為成熟的作戰框架，目標使用者（10+ 年紅隊軍事顧問）天然熟悉
  - 六域涵蓋作戰系統所有面向，不會遺漏關鍵功能
  - 提供統一的組織語言——API、UI、文件全部以 C5ISR 六域為座標
  - 強化「指揮平台」定位，與一般滲透測試工具形成鮮明差異
- **缺點**：需為每個功能判斷歸屬域（個別邊界案例需討論）
- **風險**：軍事 C5ISR 原為物理作戰設計，映射至網路戰需合理詮釋（透過明確映射表緩解）

### 選項 B：自定義分類（按技術棧分域）

按 Athena 技術棧分類：Frontend / Backend / Database / AI / Execution。

- **優點**：技術人員直覺理解
- **缺點**：失去軍事框架的差異化；與「指揮平台」定位不符；目標使用者不以技術棧思考
- **風險**：Athena 退化為「又一個技術監控儀表板」

### 選項 C：不使用框架（純功能性儀表板）

直接展示 Agent 數量、執行狀態、日誌等，不做分域組織。

- **優點**：最簡單、無映射成本
- **缺點**：無結構化的全域態勢感知；指揮官無法一眼掌握六域健康度；失去 C5ISR 核心賣點
- **風險**：Athena 與 Metasploit Console 無本質區別

---

## 決策（Decision）

我們選擇 **選項 A：軍事 C5ISR 六域框架**，因為：

1. **核心差異化**：C5ISR 框架是 Athena 從「工具」提升為「指揮平台」的關鍵
2. **使用者契合**：軍事顧問天然以 C5ISR 思考作戰系統健康度
3. **完備覆蓋**：六域涵蓋指揮、管制、通訊、資訊、網路戰、情報——無遺漏
4. **組織統一**：從 API 端點（`/c5isr`）到 UI 元件（`C5ISRStatusBoard`）到後端服務（`c5isr_mapper.py`）全面對齊

### C5ISR 與 OODA 的關係

C5ISR 是**橫切關注（cross-cutting concern）**，而非 OODA 的第五個階段：

```
OODA 循環（縱向流程）        C5ISR（橫向態勢）
═══════════════════       ═══════════════════
Observe → Orient →        每個 OODA 階段都更新
Decide → Act → loop       C5ISR 六域健康度

ooda_controller.py         c5isr_mapper.py
├── fact_collector          ├── 從 Agent 心跳更新 Control 域
├── orient_engine           ├── 從 WS 連線更新 Comms 域
├── decision_engine         ├── 從 Execution 更新 Cyber 域
└── engine_router           └── 從 PentestGPT 更新 ISR 域

c5isr_mapper.update() 在 OODA 每次迭代的 Observe 階段呼叫，
聚合最新狀態後透過 WebSocket "c5isr.update" 事件推送至前端。
```

### 健康度模型

每個 C5ISR 域維護 `health_pct`（0-100 float）和 `C5ISRDomainStatus`（8 種語義狀態）：

```python
# C5ISRDomainStatus 語義定義
class C5ISRDomainStatus(str, Enum):
    OPERATIONAL = "operational"   # health >= 95 — 完全運作
    ACTIVE      = "active"       # health >= 85 — 主動作業中
    NOMINAL     = "nominal"      # health >= 75 — 正常運作
    ENGAGED     = "engaged"      # health >= 65 — 交戰/執行中
    SCANNING    = "scanning"     # health >= 50 — 偵察/掃描中
    DEGRADED    = "degraded"     # health >= 30 — 功能降級
    OFFLINE     = "offline"      # health >= 1  — 離線
    CRITICAL    = "critical"     # health < 1   — 嚴重故障
```

聚合邏輯（`c5isr_mapper.py`）：

```
Domain       聚合公式
─────────   ──────────────────────────────────────────────
Command     基於 OODA 迭代進度 + 指揮官回應時間
Control     alive_agents / total_agents * 100
Comms       WebSocket 連線正常 ? 100 : (降級計算)
Computers   alive_targets / total_targets * 100
Cyber       successful_executions / total_executions * 100
ISR         latest_recommendation.confidence * 100
```

### UI 定位

`/c5isr` 為指揮官首頁（主儀表板），非 `/monitor`：

```
/          → redirect → /c5isr
/c5isr     → C5ISR 指揮看板（六域健康度 + KPI + OODA 指示器 + 推薦卡）
/navigator → MITRE ATT&CK 矩陣導航
/planner   → Mission 任務規劃
/monitor   → Battle Monitor（3D 拓樸 + 日誌串流）
```

理由：指揮官開啟 Athena 首先需要的是**全域態勢感知**，C5ISR 六域健康度正是此目的的最佳呈現——先掌握態勢，再深入特定功能。

---

## 後果（Consequences）

**正面影響：**

- 指揮官一眼掌握六域健康度，快速識別哪個域需要關注
- C5ISR 六域映射自然驅動 API 設計（`GET /operations/{id}/c5isr`）
- `c5isr_mapper.py` 作為橫切服務，不與 OODA 主流程耦合，可獨立演進
- Seed data 中 6 筆 `c5isr_statuses` 展示完整六域狀態差異（operational → degraded）
- 強化 Demo 的軍事指揮系統視覺衝擊力

**負面影響 / 技術債：**

- `c5isr_mapper.py` 需為每個域撰寫專屬聚合邏輯（6 套公式）
- 健康度計算依賴多個資料來源（agents、executions、WS 狀態），需確保一致性
- `C5ISRDomainStatus` 的 8 種狀態到 `health_pct` 區間的映射需在前端和後端同步

**後續追蹤：**

- [ ] Phase 2.1：實作 `C5ISRDomain` + `C5ISRDomainStatus` Enum
- [ ] Phase 2.2：建立 `c5isr_statuses` 資料表
- [ ] Phase 2.3：載入 6 筆 seed data（每域一筆）
- [ ] Phase 4.1：實作 `C5ISRStatusBoard` + `DomainCard` 前端元件
- [ ] Phase 5.4：實作 `c5isr_mapper.py`（六域聚合邏輯）
- [ ] Phase 6.2：驗證 `c5isr.update` WebSocket 事件推送至 `/c5isr` 畫面

---

## 關聯（Relations）

- 取代：（無）
- 被取代：（無）
- 參考：ADR-003（`c5isr_mapper.py` 為 OODA 六服務之一）、ADR-007（`c5isr.update` WebSocket 事件）、ADR-008（`c5isr_statuses` 表的 `UNIQUE(operation_id, domain)` 約束）、ADR-009（`c5isr/` 前端元件目錄）
