# [ADR-035]: C5ISR 域評估報告架構

| 欄位 | 內容 |
|------|------|
| **狀態** | `Accepted` |
| **日期** | 2026-03-08 |
| **決策者** | Athena Core Team |

---

## 背景（Context）

ADR-012 建立了 Athena 的 C5ISR 框架對應，將 OODA 循環的各階段產出映射至六個軍事 C5ISR 域（Command、Control、Comms、Computers、Cyber、ISR）。然而，代碼審計發現目前的實作產出的是虛榮指標（vanity metrics），而非真正的態勢感知：

1. **Command 域**：`min(100, 80 + ooda_count * 5)` — 5 次迭代（約 2.5 分鐘）後自動膨脹至 100%，與實際指揮權威無關
2. **Comms 域**：硬編碼為 60%（`# simplified for POC`）
3. **Cyber 域**：單純的 success/total 比率，未區分偵察成功與攻擊成功
4. **ISR 域**：僅取最近一次建議的信心度，無趨勢或覆蓋率指標

真正的軍事 C5ISR 系統提供的是每個域的結構化態勢報告，而非單純的儀表百分比。目標使用者（具備 10 年以上軍事紅隊顧問經驗的操作員）期望看到域評估報告，而非百分比數字。

---

## 評估選項（Options Considered）

### 選項 A：增強百分比計算（最小變更）

- **優點**：前端變更最小、向後相容
- **缺點**：仍然只是數字 — 無法傳達戰術脈絡
- **風險**：低 — 但根本問題（缺乏結構化報告）未解決

做法：保留六角儀表 UI，僅修正計算公式。每個域使用 2-3 個加權信號，從真實 DB 資料計算。

### 選項 B：域評估報告（建議採用）

- **優點**：符合軍事 C5ISR 準則、對操作員大幅提升實用性、health_pct 保留作為摘要指標
- **缺點**：變更較大（後端與前端皆需修改）、資料組裝更複雜
- **風險**：中 — 需要 c5isr_mapper.py 全面重寫，但 DB schema 不需變更

做法：每個域產出結構化報告，包含 Executive Summary、Key Metrics（含 health_pct）、Asset Roster、Tactical Assessment、Risk Vectors、Recommended Actions、Cross-Domain Impact。`c5isr_statuses` 的 `detail` 欄位儲存 JSON 報告取代單行文字。前端 DomainCard 新增展開/收合功能 — 收合時顯示六角儀表 + 摘要，展開時顯示完整報告。

### 選項 C：LLM 生成敘事報告

- **優點**：最自然的語言輸出、格式靈活
- **缺點**：每次 OODA 迭代增加 API 成本、額外延遲、操作資料可能產生幻覺
- **風險**：高 — 成本與可靠性問題

做法：每個 OODA 迭代使用 Claude API 產生自然語言 C5ISR 報告。

---

## 決策（Decision）

我們選擇 **選項 B（域評估報告）**，因為：

1. 結構化報告符合軍事 C5ISR 準則，提供真正的態勢感知
2. 無額外 LLM 成本（從 DB 資料確定性組裝）
3. 向後相容（health_pct 保留作為摘要指標供儀表顯示）
4. DB schema 不需變更（`detail` 欄位已為 TEXT 型別，改為儲存 JSON）

### 域報告結構

每個域產出 `DomainReport` dataclass，包含以下欄位：

| 欄位 | 型別 | 說明 |
|------|------|------|
| `executive_summary` | `str` | 一句話態勢判斷 |
| `health_pct` | `float` | 保留供儀表顯示的健康百分比 |
| `status` | `C5ISRDomainStatus` | 語義狀態（OPTIMAL / DEGRADED / CRITICAL 等） |
| `metrics` | `list[DomainMetric]` | 2-3 個加權指標，每個包含 name、value、weight、numerator、denominator |
| `asset_roster` | `list[dict]` | 結構化資產清單（agents / targets / tools） |
| `tactical_assessment` | `str` | 戰術分析段落 |
| `risk_vectors` | `list[RiskVector]` | 風險項目，包含 severity（CRIT / WARN / INFO）與 message |
| `recommended_actions` | `list[str]` | 建議的下一步行動 |
| `cross_domain_impacts` | `list[str]` | 對其他域的影響 |

### 各域 health_pct 加權公式

每個域的 health_pct 由加權指標計算，所有信號皆可退化（健康度可以下降）：

| 域 | 指標 | 權重 | 退化機制 |
|----|------|------|----------|
| **Command** | decision_throughput | 0.40 | 停滯懲罰（stall penalty） |
| | acceptance_rate | 0.35 | |
| | directive_consumption | 0.25 | |
| **Control** | agent_liveness | 0.50 | 過時 agent 懲罰（stale agent penalty） |
| | access_stability | 0.30 | |
| | beacon_freshness | 0.20 | |
| **Comms** | ws_connections | 0.40 | |
| | mcp_availability | 0.30 | |
| | broadcast_success | 0.30 | |
| **Computers** | compromise_rate | 0.40 | |
| | privilege_depth | 0.35 | |
| | killchain_advancement | 0.25 | |
| **Cyber** | recon_success | 0.25 | 下降趨勢偵測（declining trend detection） |
| | exploit_success | 0.45 | |
| | recent_trend | 0.30 | |
| **ISR** | confidence_trend | 0.35 | |
| | fact_coverage | 0.35 | |
| | graph_coverage | 0.30 | |

### 前端變更

DomainCard 元件新增展開/收合功能：
- **收合狀態**：顯示六角儀表 + executive_summary
- **展開狀態**：顯示完整報告，包含所有結構化區段

---

## 後果（Consequences）

**正面影響：**
- 提供真正的態勢感知，操作員可從每個域獲得可行動的情報
- 符合軍事 C5ISR 準則，滿足目標使用者（資深軍事紅隊顧問）的期望
- 健康度可退化，Command 域不再能在無真實決策活動下達到 100%
- Comms 域反映真實通訊健康狀態，不再硬編碼

**負面影響 / 技術債：**
- 後端 `c5isr_mapper.py` 需全面重寫（約 400 行）
- 前端 DomainCard 需實作展開/收合機制與報告渲染
- 每次 OODA 迭代的 DB 查詢數增加（8-10 次 vs 目前 5 次）

**後續追蹤：**
- [ ] 建立對應 SPEC 並完成實作
- [ ] 驗證所有 6 個域皆產出完整結構化報告
- [ ] 效能測試：確認增加的 DB 查詢不影響 OODA 迭代速度

---

## 成功指標（Success Metrics）

| 指標 | 目標值 | 驗證方式 | 檢查時間 |
|------|--------|----------|----------|
| 域報告完整性 | 所有 6 個域產出結構化報告，每個至少 3 個區段有內容 | 整合測試 | 實作完成時 |
| Command 域無自動膨脹 | 無真實決策活動時不可達到 100% | 單元測試 | 實作完成時 |
| Comms 域反映真實狀態 | 非硬編碼值，與實際通訊健康相關 | 單元測試 | 實作完成時 |
| health_pct 準確度 | 與加權指標計算結果誤差 <= 1% | 單元測試 | 實作完成時 |
| 既有測試通過率 | 100% | `make test` | 實作完成時 |

---

## 關聯（Relations）

- 取代（部分）：ADR-012（僅健康度計算公式；框架映射保留）
- 被取代：無
- 參考：ADR-003（OODA loop 架構）、ADR-012（C5ISR 框架映射）、SPEC-007（OODA loop engine）
