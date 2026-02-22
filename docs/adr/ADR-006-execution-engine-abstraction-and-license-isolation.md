# [ADR-006]: 執行引擎抽象層與授權隔離

| 欄位 | 內容 |
|------|------|
| **狀態** | `Accepted` |
| **日期** | 2026-02-23 |
| **決策者** | 專案負責人 |

---

## 背景（Context）

Athena OODA Act 階段需透過外部執行引擎執行 MITRE ATT&CK 技術。Phase 5.3 需實作 `engine_router.py`、`caldera_client.py` 和 `shannon_client.py`。

核心挑戰：

1. **雙引擎路由**：Caldera（標準技術）和 Shannon（AI 自適應），需統一介面
2. **授權隔離**：Caldera 為 Apache 2.0（安全），Shannon 為 AGPL-3.0（有病毒式特性）
3. **可選性**：Shannon 為 POC 選用元件，系統在僅有 Caldera 時必須完全可運作
4. **可擴展性**：未來可能新增其他執行引擎（BloodHound、Cobalt Strike 等）

---

## 評估選項（Options Considered）

### 選項 A：統一 Client 介面 + API-Only 隔離 + 路由器模式

```
engine_router.py          — 決策「用哪個引擎」
├── caldera_client.py     — Caldera REST API 封裝
└── shannon_client.py     — Shannon REST API 封裝（選用）

所有客戶端實作統一介面：
  execute(technique_id, target, params) → ExecutionResult
  get_status(execution_id) → Status
  list_abilities() → List[Ability]
```

- **優點**：
  - 統一介面使 OODA 引擎不需知道底層引擎差異
  - Shannon 僅透過 HTTP API 呼叫，不 import 任何 AGPL 程式碼
  - `engine_router.py` 封裝路由邏輯（信心度、技術可用性、隱蔽需求）
  - Shannon 不可用時自動 fallback 至 Caldera
- **缺點**：需維護兩套客戶端的回應標準化邏輯
- **風險**：Caldera 和 Shannon API 格式差異需仔細對齊

### 選項 B：僅 Caldera（移除 Shannon 抽象）

- **優點**：最簡單；無授權風險；POC 完全足夠
- **缺點**：失去雙引擎編排展示能力；無法展示 AI 自適應執行
- **風險**：若未來需加入 Shannon，需重構 Act 層

### 選項 C：直接嵌入 Shannon 程式碼

- **優點**：更深度整合；避免網路延遲
- **缺點**：AGPL-3.0 病毒式授權將迫使 Athena 整體改為 AGPL
- **風險**：**授權污染**——核心平台的 Apache 2.0 授權被破壞，阻斷商業化路徑

---

## 決策（Decision）

我們選擇 **選項 A：統一 Client 介面 + API-Only 隔離 + 路由器模式**，因為：

1. **授權安全**：Shannon 僅透過 HTTP API 呼叫，Athena 不包含任何 AGPL 程式碼
2. **POC 靈活性**：Shannon 可選——`SHANNON_URL` 環境變數為空時系統自動跳過
3. **統一介面**：新增引擎只需實作 `execute()` / `get_status()` / `list_abilities()`
4. **路由邏輯集中**：`engine_router.py` 封裝所有引擎選擇決策

路由優先順序：

```python
def select_engine(technique, context, gpt_recommendation):
    # 1. 高信心度 PentestGPT 建議 → 信任其引擎選擇
    # 2. Caldera 有對應 ability → Caldera
    # 3. 未知環境 + Shannon 可用 → Shannon
    # 4. 高隱蔽需求 + Shannon 可用 → Shannon
    # 5. 預設 → Caldera
```

授權邊界：

```
┌────────────────────────────────┐
│ Athena 核心 (Apache 2.0)      │
│ ├─ engine_router.py           │
│ ├─ caldera_client.py          │  ← HTTP API 呼叫
│ └─ shannon_client.py          │  ← HTTP API 呼叫（僅此）
└────────────┬───────────────────┘
             │ HTTP REST API（授權防火牆）
     ┌───────┴───────┐
     ↓               ↓
  Caldera         Shannon
  Apache 2.0      AGPL-3.0
```

---

## 後果（Consequences）

**正面影響：**

- Athena 核心授權維持 Apache 2.0，商業化路徑不受影響
- 新增執行引擎（如 Phase 8 的 Cobalt Strike 連接器）只需新增一個 `*_client.py`
- Shannon 不可用時系統零降級——Caldera 處理所有標準 MITRE 技術
- Demo 可選擇性展示雙引擎編排

**負面影響 / 技術債：**

- Caldera 和 Shannon 的 API 回應格式不同，`ExecutionResult` 標準化需額外程式碼
- Shannon 獨立部署增加 ~2GB RAM（僅在啟用時）
- 需持續確保不意外 import Shannon 套件（程式碼審查 + lint 規則）

**後續追蹤：**

- [ ] Phase 5.3：實作 `caldera_client.py`（Caldera REST API v2 封裝）
- [ ] Phase 5.3：實作 `shannon_client.py`（選用，Shannon API 封裝）
- [ ] Phase 5.3：實作 `engine_router.py`（路由邏輯 + fallback）
- [ ] Phase 7.2：驗證 Shannon API 隔離合規性（無 AGPL import）
- [ ] Phase 8.5：新增 BloodHound / Cobalt Strike 連接器時複用此架構

---

## 關聯（Relations）

- 取代：（無）
- 被取代：（無）
- 參考：ADR-001（授權策略）、ADR-003（OODA 引擎 Act 階段）、ADR-005（Orient 引擎的 recommended_engine 欄位）、ADR-007（執行結果透過 WebSocket 推送）、ADR-010（Shannon 外部部署拓樸）
