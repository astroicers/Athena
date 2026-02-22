# [ADR-003]: OODA 循環引擎架構

| 欄位 | 內容 |
|------|------|
| **狀態** | `Accepted` |
| **日期** | 2026-02-23 |
| **決策者** | 專案負責人 |

---

## 背景（Context）

Athena 的核心創新在於將軍事 OODA 循環（Observe → Orient → Decide → Act）應用於網路作戰指揮。Phase 5 需實作 OODA 引擎，該引擎必須：

1. 管理四個階段的狀態轉換
2. 在 Orient 階段整合 PentestGPT 的 AI 戰術分析
3. 在 Decide 階段支援半自動化（依風險等級決定人工/自動）
4. 在 Act 階段路由至 Caldera 或 Shannon 執行引擎
5. 將執行結果回饋至 Observe，形成持續循環

需決定 OODA 引擎的內部架構：是一個單體控制器，還是分拆為多個專職服務。

---

## 評估選項（Options Considered）

### 選項 A：六服務分層架構

將 OODA 引擎拆為 6 個專職服務，每個服務對映一個明確職責：

```
ooda_controller.py   — 狀態機（階段轉換 + 迭代管理）
fact_collector.py    — Observe（標準化執行結果為情報）
orient_engine.py     — Orient（PentestGPT API 整合）
decision_engine.py   — Decide（風險評估 + 自動化控制）
engine_router.py     — Act（路由至 Caldera / Shannon）
c5isr_mapper.py      — 橫切（聚合 C5ISR 六域健康度）
```

- **優點**：每個服務單一職責，可獨立測試；Orient 引擎可替換 LLM 後端不影響其他服務；新增執行引擎只需修改 `engine_router.py`
- **缺點**：6 個檔案的跨服務呼叫需清晰介面定義
- **風險**：過度拆分導致簡單操作需跨多層呼叫（POC 中可接受）

### 選項 B：單體 OODA 控制器

所有邏輯放在單一 `ooda_engine.py`：

- **優點**：簡單直接，單一檔案掌控全局
- **缺點**：檔案膨脹（預估 800+ 行）；PentestGPT 整合、風險評估、引擎路由邏輯耦合；測試需 mock 全部外部依賴
- **風險**：隨功能增長變得難以維護；難以獨立替換 Orient 或 Act 的實作

### 選項 C：事件驅動架構（Event Bus）

各階段透過事件匯流排解耦：

- **優點**：極度解耦；易於加入新的事件消費者
- **缺點**：POC 複雜度過高；需引入 Redis/RabbitMQ 等訊息佇列；除錯困難
- **風險**：過度設計，不符合 POC 輕量化原則

---

## 決策（Decision）

我們選擇 **選項 A：六服務分層架構**，因為：

1. **單一職責**：每個服務對映 OODA 一個階段或橫切關注，職責清晰
2. **可測試性**：`orient_engine.py` 可獨立 mock LLM 測試；`engine_router.py` 可 mock Caldera API 測試
3. **可擴展性**：新增執行引擎（如未來的 Cobalt Strike 連接器）只需修改 `engine_router.py`
4. **符合 CLAUDE.md 設計**：已定義的三層智慧架構（Strategic / Decision / Execution）自然映射至此分層

服務呼叫流：

```
ooda_controller
  ├── Observe: fact_collector.collect()
  ├── Orient:  orient_engine.analyze()      → PentestGPT → LLM
  ├── Decide:  decision_engine.evaluate()   → 風險 + 自動化
  ├── Act:     engine_router.execute()      → Caldera / Shannon
  └── 橫切:    c5isr_mapper.update()        → 六域健康度
```

---

## 後果（Consequences）

**正面影響：**

- 各服務獨立開發、獨立測試，可按 Phase 5 子任務逐步交付
- Orient 引擎切換 LLM 後端（Claude → GPT-4）只需修改 `orient_engine.py`
- `ooda_controller.py` 作為編排器保持精簡，只負責狀態轉換
- C5ISR 映射作為橫切關注，不與 OODA 主流程耦合

**負面影響 / 技術債：**

- 6 個服務間的介面需在 Phase 5 初期明確定義（Pydantic schema）
- 跨服務除錯需追蹤多個檔案（可透過結構化 logging 緩解）

**後續追蹤：**

- [ ] Phase 5.1：定義 6 個服務的 Pydantic 輸入/輸出 schema
- [ ] Phase 5：為每個服務撰寫獨立單元測試
- [ ] Phase 6：端對端測試驗證完整 OODA 循環

---

## 關聯（Relations）

- 取代：（無）
- 被取代：（無）
- 參考：ADR-001（技術棧）、ADR-004（Decide 階段半自動化邏輯）、ADR-005（Orient 引擎 PentestGPT 整合）、ADR-006（Act 階段執行引擎抽象層）、ADR-007（OODA 事件透過 WebSocket 推送至前端）、ADR-012（c5isr_mapper 為六服務之一的 C5ISR 框架映射）
