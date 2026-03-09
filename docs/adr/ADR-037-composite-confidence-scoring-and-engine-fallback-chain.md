# [ADR-037]: 複合信心評分與引擎回退鏈

| 欄位 | 內容 |
|------|------|
| **狀態** | `Accepted` |
| **日期** | 2026-03-08 |
| **決策者** | Athena Core Team |

---

## 背景（Context）

在 Athena 決策與執行管線的審計中發現兩個相關問題：

### 問題一：Decision Engine 的單一來源信心評分

`decision_engine.py` 第 61 行：`confidence = recommendation.get("confidence", 0.0)` -- 信心分數 100% 來自 LLM 輸出，缺乏任何經驗性驗證。LLM 可能對不合理的情境回傳高信心值，例如對 Linux 目標回傳 T1003.001（LSASS dump）信心 0.87。

現有風險等級為全域性的 per-technique 設定，未考慮上下文差異：T1003.001 在所有環境皆為 "medium"，但在部署 EDR 的 Domain Controller 上應為 "critical"。整個風險閘控系統（ADR-004）依賴此單一不可靠信號做出放行/阻擋決策。

### 問題二：引擎失敗時無回退機制

`engine_router.py`：當 MCP 執行器失敗（第 265 行）時，錯誤為終端性 -- 不會回退至 Metasploit 或 SSH。當 Metasploit 失敗時，同樣不會串接至 MCP/C2。結果是單一引擎失敗即阻斷整個 Act 階段，即使替代引擎能夠成功執行。

---

## 評估選項（Options Considered）

### 信心評分問題

#### 選項 A：維持 LLM-only，加入 prompt 防護

- **優點**：無需程式碼變更
- **缺點**：LLM 防護本質上不可靠，無法補足缺失的歷史/經驗數據
- **風險**：高 -- prompt 注入或 LLM 幻覺可繞過防護

#### 選項 B：四來源複合信心評分（推薦）

計算公式：`composite = 0.30 * llm + 0.30 * historical + 0.25 * graph + 0.15 * target_state`

- **Historical（歷史成功率）**：從 `technique_executions` 表取得該技術的實際成功率
- **Graph（攻擊圖節點信心）**：基於先決條件滿足程度的確定性評分
- **Target state（目標狀態）**：`is_compromised`（+0.2）、`has_root`（+0.15）、`has_edr`（-0.2）、`stale_access`（-0.1）

權重設計理由：
- 0.30 LLM：具備策略性上下文理解能力，但幻覺風險使其不宜超過 30%
- 0.30 Historical：來自實際執行的地面真相，作為經驗性對照權重與 LLM 相等
- 0.25 Graph：確定性的先決條件滿足度計算，可靠度高
- 0.15 Target state：重要但資料常不完整

- **優點**：以經驗為基礎、LLM 影響受限、多信號交叉驗證
- **缺點**：每次決策增加更多 DB 查詢、權重需調校
- **風險**：低 -- 歷史數據不足時可回退至均等權重

#### 選項 C：Kill Chain 強制器（與選項 B 互補）

軟性強制：當推薦技術跳過 Kill Chain 階段時，施加信心懲罰。

- 懲罰值：每跳過一個必要階段扣 0.05，最高扣 0.25
- 可跳過階段：TA0042（Resource Development）、TA0003（Persistence）、TA0005（Defense Evasion）、TA0011（C2）
- **優點**：防止不合理推薦（例如未取得 Initial Access 即嘗試 Lateral Movement）
- **缺點**：某些創造性攻擊路徑確實會跳過階段 -- 採用軟性懲罰（非阻擋）處理此情況
- **風險**：低 -- 懲罰值有上限且為軟性

### 引擎回退問題

#### 選項 D：重試相同引擎

- **優點**：實作簡單
- **缺點**：相同引擎極可能因相同原因再次失敗
- **風險**：高 -- 浪費 Act 階段時間

#### 選項 E：引擎回退鏈（推薦）

定義回退優先順序：`{"mcp_ssh": ["metasploit", "c2"], "metasploit": ["mcp_ssh", "c2"], "c2": ["mcp_ssh"]}`

- 終端性錯誤不觸發回退：範圍違規（scope violation）、平台不匹配（platform mismatch）、RoE 阻擋
- 每次回退嘗試透過 WebSocket 廣播 `execution.fallback` 事件
- 將現有 `execute()` 重命名為 `_execute_single()`，新 `execute()` 包裝回退邏輯

- **優點**：最大化執行成功率、操作員透過 WS 事件獲得可視性
- **缺點**：序列式回退嘗試可能增加執行時間
- **風險**：低 -- 終端性錯誤已排除回退

---

## 決策（Decision）

我們選擇 **選項 B + 選項 C + 選項 E** 的組合方案，因為三者互補：

1. **選項 B（四來源複合信心評分）** 為 Decide 階段提供更可靠的信心評分，將 LLM 的影響力限制在 30%，並引入歷史成功率、攻擊圖先決條件、目標狀態三個經驗性信號進行交叉驗證
2. **選項 C（Kill Chain 強制器）** 為信心評分加入 Kill Chain 感知能力，對跳過必要攻擊階段的推薦施加懲罰，防止不合邏輯的技術推薦
3. **選項 E（引擎回退鏈）** 確保 Act 階段更具韌性，單一引擎失敗不再阻斷執行流程

### 關鍵實作細節

複合信心計算（`decision_engine.py`）：

```python
async def _compute_composite_confidence(self, db, operation_id, recommendation, raw_confidence):
    hist_rate = await self._get_historical_success_rate(db, technique_id)
    graph_conf = await self._get_graph_node_confidence(db, operation_id, technique_id, target_id)
    target_score = await self._get_target_state_score(db, target_id)
    kc_penalty, kc_warning = await self._enforcer.evaluate_skip(db, operation_id, tactic_id, target_id)

    composite = 0.30*raw_confidence + 0.30*hist_rate + 0.25*graph_conf + 0.15*target_score - kc_penalty
    return max(0.0, min(1.0, composite))
```

引擎回退鏈（`engine_router.py`）：

```python
async def execute(self, ...):
    result = await self._execute_single(...)
    if result["status"] == "success" or _is_terminal_error(result.get("error")):
        return result
    for fallback_engine in _FALLBACK_CHAIN.get(engine, []):
        await self._ws.broadcast(operation_id, "execution.fallback", {...})
        result = await self._execute_single(..., engine=fallback_engine)
        if result["status"] == "success" or _is_terminal_error(result.get("error")):
            return result
    return result
```

---

## 後果（Consequences）

**正面影響：**
- 信心評分基於多重信號交叉驗證，降低 LLM 幻覺導致錯誤決策的風險
- Act 階段具備韌性，單一引擎失敗可自動切換至替代引擎
- Kill Chain 感知防止不合邏輯的技術推薦（如未取得 Initial Access 即嘗試 Lateral Movement）
- 操作員透過 `execution.fallback` WebSocket 事件即時了解回退狀況

**負面影響 / 技術債：**
- 每次決策週期增加約 4 次額外 DB 查詢（歷史成功率、攻擊圖信心、目標狀態、Kill Chain 評估）
- 引擎回退延長 Act 階段持續時間（序列式嘗試）
- 新增 `KillChainEnforcer` 模組需持續維護
- 複合信心權重需依實際運行數據進行調校

**後續追蹤：**
- [ ] 建立對應 SPEC 進行實作
- [ ] 複合信心權重調校（基於實際運行數據）
- [ ] 端對端驗證：引擎回退場景測試

---

## 成功指標（Success Metrics）

| 指標 | 目標值 | 驗證方式 | 檢查時間 |
|------|--------|----------|----------|
| 複合信心與原始 LLM 信心差異率 | >= 50% 的案例出現差異 | 單元測試 + 整合測試 | 實作完成時 |
| 歷史成功率正確反映過往執行結果 | 100% 準確 | 單元測試 | 實作完成時 |
| Kill Chain 跳階懲罰正確施加 | 跳過必要階段時觸發 | 單元測試 | 實作完成時 |
| 引擎回退於主引擎非終端性失敗時觸發 | 100% 觸發 | 整合測試 | 實作完成時 |
| 終端性錯誤不觸發回退 | 100% 不觸發 | 單元測試 | 實作完成時 |
| 既有決策引擎與引擎路由測試通過率 | 100% | `make test` | 實作完成時 |

---

## 關聯（Relations）

- 取代：無
- 被取代：無
- 延伸：ADR-004（semi-auto with manual override -- 強化信心來源）、ADR-006（execution engine abstraction -- 加入回退路由）
- 參考：ADR-003（OODA loop）、ADR-028（attack graph）、ADR-033（access recovery）
