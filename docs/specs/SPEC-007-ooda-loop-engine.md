# SPEC-007：OODA 循環引擎（6 服務）

> 實作 OODA 控制器 + 5 個專職服務，驅動 Observe → Orient → Decide → Act 完整循環。

| 欄位 | 內容 |
|------|------|
| **規格 ID** | SPEC-007 |
| **關聯 ADR** | ADR-003（OODA 引擎架構）、ADR-004（半自動化）、ADR-005（PentestGPT Orient） |
| **估算複雜度** | 高 |
| **建議模型** | Opus |
| **HITL 等級** | strict |

---

## 🎯 目標（Goal）

> 實作 Athena 的核心智慧循環——6 個服務分層的 OODA 引擎，使 PentestGPT 情報分析驅動戰術決策，經風險評估後路由至 Caldera/Shannon 執行，並將結果回饋至下一次 Observe，形成持續循環。

---

## 📥 輸入規格（Inputs）

| 參數名稱 | 型別 | 來源 | 限制條件 |
|----------|------|------|----------|
| 六服務架構 | ADR | ADR-003 決策 | 嚴格遵循 6 個服務的職責劃分 |
| Orient 輸出結構 | ADR | ADR-005 決策 | `PentestGPTRecommendation` 含 3 個 `TacticalOption` |
| 風險閾值規則 | ADR | ADR-004 決策 | LOW=自動、MEDIUM=排隊、HIGH=確認、CRITICAL=手動 |
| 引擎路由優先順序 | ADR | ADR-006 決策 | 5 級優先順序 |
| C5ISR 聚合公式 | ADR | ADR-012 決策 | 6 域各自的計算邏輯 |
| Pydantic Models | SPEC | SPEC-002 輸出 | 使用已定義的 Model |
| Database 層 | SPEC | SPEC-003 輸出 | 使用 get_db() |
| API 路由 | SPEC | SPEC-004 輸出 | `POST /ooda/trigger` 觸發 |
| 執行引擎客戶端 | SPEC | SPEC-008 輸出 | `CalderaClient` / `ShannonClient` |

---

## 📤 輸出規格（Expected Output）

**成功情境：**

### 1. `services/ooda_controller.py` — OODA 狀態機

```python
class OODAController:
    """
    OODA 循環編排器 — 管理 Observe → Orient → Decide → Act 狀態轉換。
    不包含業務邏輯，僅協調 5 個專職服務。
    """

    async def trigger_cycle(self, operation_id: str) -> OODAIteration:
        """
        觸發一次完整 OODA 迭代：
        1. Observe: fact_collector.collect()
        2. Orient:  orient_engine.analyze()
        3. Decide:  decision_engine.evaluate()
        4. Act:     engine_router.execute()
        5. 橫切:    c5isr_mapper.update()
        每個階段完成後透過 WebSocket 推送 ooda.phase 事件。
        """

    async def advance_phase(self, operation_id: str, phase: OODAPhase):
        """手動推進階段（指揮官覆寫）"""

    async def get_current(self, operation_id: str) -> OODAIteration:
        """取得當前迭代狀態"""
```

### 2. `services/fact_collector.py` — Observe 階段

```python
class FactCollector:
    """
    Observe 階段 — 從執行結果中標準化萃取情報。
    """

    async def collect(self, operation_id: str) -> list[Fact]:
        """
        從 TechniqueExecution 結果中萃取 Fact：
        - credential 類型：帳號密碼、hash
        - host 類型：主機資訊、服務
        - network 類型：網段、連線
        回傳：新收集的 Fact 列表
        """

    async def summarize(self, operation_id: str) -> str:
        """產生 Observe 階段摘要（供 Orient 使用）"""
```

### 3. `services/orient_engine.py` — Orient 階段（核心創新）

```python
class OrientEngine:
    """
    Orient 階段 — PentestGPT 整合，Athena 的核心價值所在。
    """

    async def analyze(
        self, operation_id: str, facts: list[Fact], observe_summary: str
    ) -> PentestGPTRecommendation:
        """
        呼叫 PentestGPT → LLM API 產生戰術分析：
        1. 建構 prompt（作戰歷史 + 最新情報 + MITRE 技術庫）
        2. 呼叫 Claude API（主要）或 GPT-4（fallback）
        3. 解析 LLM 回應為 PentestGPTRecommendation
           - situation_assessment: str
           - options: 3 個 TacticalOption
           - recommended_technique_id: str
           - confidence: 0.0 - 1.0
        4. 儲存至 DB + 推送 WebSocket "recommendation" 事件
        """

    async def _call_llm(self, prompt: str) -> str:
        """
        LLM API 呼叫（雙後端切換）：
        - MOCK_LLM=true → 回傳預錄回應
        - 主要：Anthropic Claude API
        - 備用：OpenAI GPT-4 API
        """
```

### 4. `services/decision_engine.py` — Decide 階段

```python
class DecisionEngine:
    """
    Decide 階段 — 基於 AI 建議 + 風險等級 + 自動化模式選擇技術。
    """

    async def evaluate(
        self, operation_id: str, recommendation: PentestGPTRecommendation
    ) -> dict:
        """
        決策邏輯：
        1. 取得作戰的 automation_mode 和 risk_threshold
        2. 取得推薦技術的 risk_level
        3. 依 ADR-004 風險閾值規則：
           - LOW (< threshold)  → auto_approve=True
           - MEDIUM             → auto_approve=True, needs_queue=True
           - HIGH               → auto_approve=False, needs_confirm=True
           - CRITICAL           → auto_approve=False, needs_manual=True
        4. MANUAL 模式 → 所有決策需人工批准
        5. 回傳：{
             technique_id, target_id, engine,
             auto_approved, needs_confirmation, risk_level
           }
        """
```

### 5. `services/engine_router.py` — Act 階段

```python
class EngineRouter:
    """
    Act 階段 — 根據技術類型路由到 Caldera 或 Shannon 執行。
    """

    async def execute(
        self, technique_id: str, target_id: str,
        engine: str, operation_id: str
    ) -> TechniqueExecution:
        """
        路由優先順序（ADR-006）：
        1. PentestGPT 高信心度建議 → 信任其引擎選擇
        2. Caldera 有對應 ability → Caldera
        3. 未知環境 + Shannon 可用 → Shannon
        4. 高隱蔽需求 + Shannon 可用 → Shannon
        5. 預設 → Caldera

        執行流程：
        1. 建立 TechniqueExecution 記錄（status=running）
        2. 呼叫 CalderaClient / ShannonClient
        3. 更新 status（success/failed）
        4. 呼叫 fact_collector 萃取結果
        5. 推送 WebSocket "execution.update" 事件
        """

    def select_engine(
        self, technique_id: str, context: dict,
        gpt_recommendation: str | None
    ) -> str:
        """引擎選擇邏輯（同步）"""
```

### 6. `services/c5isr_mapper.py` — 橫切關注

```python
class C5ISRMapper:
    """
    橫切關注 — 聚合各來源的 C5ISR 六域健康度。
    在 OODA 每次迭代的 Observe 階段呼叫。
    """

    async def update(self, operation_id: str) -> list[C5ISRStatus]:
        """
        六域聚合（ADR-012）：
        - Command:   OODA 迭代進度 + 指揮官回應時間
        - Control:   alive_agents / total_agents * 100
        - Comms:     WebSocket 連線正常 ? 100 : (降級計算)
        - Computers: alive_targets / total_targets * 100
        - Cyber:     successful_executions / total_executions * 100
        - ISR:       latest_recommendation.confidence * 100

        每個域：
        1. 計算 health_pct (0-100)
        2. 映射至 C5ISRDomainStatus（8 種語義）
        3. 更新 DB + 推送 WebSocket "c5isr.update" 事件
        """

    def _health_to_status(self, health_pct: float) -> C5ISRDomainStatus:
        """
        health >= 95 → OPERATIONAL
        health >= 85 → ACTIVE
        health >= 75 → NOMINAL
        health >= 65 → ENGAGED
        health >= 50 → SCANNING
        health >= 30 → DEGRADED
        health >= 1  → OFFLINE
        health < 1   → CRITICAL
        """
```

**失敗情境：**

| 錯誤類型 | 處理方式 |
|----------|----------|
| LLM API 不可用 | `orient_engine` fallback 至 GPT-4；全部不可用 → 回傳 mock recommendation |
| Caldera 不可用 | `engine_router` 記錄 error + 標記 execution failed |
| Shannon 不可用 | 自動 fallback 至 Caldera |
| 作戰不存在 | 拋出 404 HTTPException |
| OODA 循環中斷 | 記錄當前階段，下次 trigger 從中斷點繼續 |

---

## ⚠️ 邊界條件（Edge Cases）

- `MOCK_LLM=true` 時 `orient_engine` 回傳預錄的 `PentestGPTRecommendation`（含 3 個 TacticalOption）
- `automation_mode=manual` 時 `decision_engine` 永遠回傳 `auto_approved=False`
- `risk_threshold` 變更在下一次 OODA 迭代生效（不影響進行中的迭代）
- PentestGPT prompt 需包含：作戰目標、已完成技術、失敗紀錄、目標清單、Agent 狀態
- `ooda_controller` 在每個階段轉換時更新 `Operation.current_ooda_phase`
- WebSocket 事件推送失敗不阻塞 OODA 循環（fire-and-forget）
- C5ISR 六域中 Comms 域需考慮 WebSocket Manager 的連線狀態（非 DB 查詢）
- `confidence` 值影響 `decision_engine` 的自動化判斷：confidence < 0.5 → 強制人工審核
- `engine_router.execute()` 呼叫 SPEC-008 的 client 取得 `ExecutionResult` 後，建立/更新 `TechniqueExecution` DB 記錄並回傳——兩種型別的轉換在 `engine_router` 中處理
- 所有 service 透過建構式注入 `ws_manager: WebSocketManager`（SPEC-004 定義），用於 fire-and-forget 事件推送
- `MOCK_LLM=true` 時 `orient_engine` 回傳的 mock `PentestGPTRecommendation` 需包含完整結構：`situation_assessment`、3 個 `TacticalOption`（T1003.001、T1134、T1548.002）、`confidence=0.87`、`recommended_technique_id="T1003.001"`

---

## ✅ 驗收標準（Done When）

- [x] `make test-filter FILTER=spec_007` 全數通過
- [x] `POST /api/operations/{id}/ooda/trigger` → 觸發完整 OODA 循環
- [x] Orient 階段：PentestGPT 回傳含 3 個 TacticalOption 的推薦
- [x] Decide 階段：LOW 風險技術自動通過、HIGH 風險技術標記需確認
- [x] Act 階段：Caldera client 被正確呼叫（或 mock）
- [x] `GET /api/operations/{id}/ooda/current` → 回傳正確的當前迭代狀態
- [x] WebSocket 推送 `ooda.phase`、`recommendation`、`execution.update` 事件
- [x] C5ISR 六域 health 在每次 OODA 迭代後更新
- [x] `MOCK_LLM=true` 時完整循環可在無 API key 下運行
- [x] `automation_mode=manual` 時所有決策需人工批准（`auto_approved=False`）

---

## 🚫 禁止事項（Out of Scope）

- 不要實作 Caldera/Shannon 的 HTTP 客戶端——SPEC-008 範圍
- 不要實作前端的 OODA UI——SPEC-006 已定義
- 不要加入 LangChain 依賴——使用原生 httpx 呼叫 LLM API
- 不要實作多次自動 OODA 迭代——POC 為手動觸發（`POST /ooda/trigger`）
- 不要為 PentestGPT 建立複雜的 RAG 管道——直接 prompt 構建
- 不要修改 SPEC-002/003/004 已定義的 Model/Schema/API 結構

---

## 📎 參考資料（References）

- ADR-003：[OODA 引擎架構](../adr/ADR-003-ooda-loop-engine-architecture.md)
- ADR-004：[半自動化模式](../adr/ADR-004-semi-auto-with-manual-override.md)
- ADR-005：[PentestGPT Orient 引擎](../adr/ADR-005-pentestgpt-orient-engine.md)
- ADR-006：[執行引擎抽象層](../adr/ADR-006-execution-engine-abstraction-and-license-isolation.md)
- ADR-012：[C5ISR 框架映射](../adr/ADR-012-c5isr-framework-mapping.md)
- SPEC-002：Pydantic Models（依賴）
- SPEC-003：Database 層（依賴）
- SPEC-004：API 路由（依賴——`/ooda/trigger`）
- SPEC-008：執行引擎客戶端（依賴——CalderaClient/ShannonClient）

<!-- tech-debt: scenario-pending — v3.2 upgrade: needs test matrix + Gherkin scenarios -->
<!-- tech-debt: observability-pending — v3.3 upgrade: needs observability section -->
