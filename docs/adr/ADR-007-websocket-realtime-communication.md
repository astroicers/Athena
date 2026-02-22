# [ADR-007]: WebSocket 即時通訊架構

| 欄位 | 內容 |
|------|------|
| **狀態** | `Accepted` |
| **日期** | 2026-02-23 |
| **決策者** | 專案負責人 |

---

## 背景（Context）

Athena 的 4 個 UI 畫面需要即時更新——Agent 心跳、技術執行狀態、OODA 階段切換、日誌串流、PentestGPT 推薦、C5ISR 域健康度。Phase 6.2 定義了 7 種 WebSocket 事件類型。需決定前後端即時通訊的技術方案。

即時性需求：
- Agent 心跳（`agent.beacon`）：秒級更新
- 技術執行狀態（`execution.update`）：秒級更新
- OODA 階段（`ooda.phase`）：立即同步所有畫面
- 日誌串流（`log.new`）：Battle Monitor 持續滾動
- PentestGPT 推薦（`recommendation`）：Orient 完成後即時推送

---

## 評估選項（Options Considered）

### 選項 A：FastAPI 原生 WebSocket + 作戰級通道

```
WS /ws/{operation_id}

事件格式：
{
  "event": "execution.update",
  "data": { ... },
  "timestamp": "2026-02-23T10:30:00Z"
}

7 種事件：
log.new | agent.beacon | execution.update |
ooda.phase | c5isr.update | fact.new | recommendation
```

- **優點**：FastAPI 內建 WebSocket 支援，零額外依賴；以 `operation_id` 區隔通道，不同作戰不互相干擾；JSON 事件格式簡單直觀；前端 `useWebSocket` hook 統一訂閱
- **缺點**：單機 WebSocket 無法水平擴展（POC 不需要）
- **風險**：大量同時 Agent 心跳可能產生頻寬壓力（POC 規模 < 10 Agent，可忽略）

### 選項 B：Server-Sent Events（SSE）

- **優點**：HTTP 原生，無需 WebSocket 握手；自動重連
- **缺點**：單向通訊（server → client）；指揮官無法透過同一通道發送指令；需另開 REST 端點處理 client → server 訊息
- **風險**：Battle Monitor 的 3D 拓樸互動需雙向通訊，SSE 不適用

### 選項 C：WebSocket + Redis Pub/Sub

- **優點**：可水平擴展；支援多個 backend instance
- **缺點**：需額外部署 Redis（+200MB RAM）；POC 過度設計
- **風險**：增加基礎設施複雜度，不符合 POC 最小化原則

---

## 決策（Decision）

我們選擇 **選項 A：FastAPI 原生 WebSocket + 作戰級通道**，因為：

1. **零額外依賴**：FastAPI 內建 WebSocket，不需 Redis 或其他中介
2. **雙向通訊**：指揮官操作（approve、override）可透過同一連線回傳
3. **作戰隔離**：`/ws/{operation_id}` 確保不同作戰的事件不混淆
4. **POC 規模適配**：單機 WebSocket 對 < 10 Agent 完全足夠

事件流架構：

```
Backend Services                 WebSocket Manager
                                     │
ooda_controller  ──→ ooda.phase      ├──→ Frontend /c5isr
orient_engine    ──→ recommendation  ├──→ Frontend /navigator
fact_collector   ──→ fact.new        ├──→ Frontend /planner
caldera_client   ──→ execution.update├──→ Frontend /monitor
                 ──→ agent.beacon    │
                 ──→ log.new         │
c5isr_mapper     ──→ c5isr.update   │
```

前端 Hook 設計：

```typescript
// hooks/useWebSocket.ts
const { events, send } = useWebSocket(operationId);

// 各畫面按需過濾
const logs = events.filter(e => e.event === 'log.new');
const ooda = events.filter(e => e.event === 'ooda.phase');
```

---

## 後果（Consequences）

**正面影響：**

- 所有 4 個畫面共用同一 WebSocket 連線（per operation），降低連線數
- 7 種事件類型涵蓋所有即時更新需求
- 前端 `useWebSocket` hook 統一管理，各畫面只需過濾事件類型
- Demo 場景中 OODA 循環的每個階段切換立即反映在 UI

**負面影響 / 技術債：**

- 單機 WebSocket 無法水平擴展（Phase 8.6 遷移至 Redis Pub/Sub）
- 無訊息持久化——斷線期間的事件會遺失（POC 可接受）
- 需處理前端 WebSocket 斷線重連邏輯

**後續追蹤：**

- [ ] Phase 2.4：實作 `routers/ws.py`（WebSocket 路由 + 連線管理）
- [ ] Phase 3.3：實作 `hooks/useWebSocket.ts`（前端 WebSocket hook）
- [ ] Phase 6.2：驗證 7 種事件類型的端對端流通
- [ ] Phase 8.6：遷移至 Redis Pub/Sub 支援多 instance

---

## 關聯（Relations）

- 取代：（無）
- 被取代：（無）
- 參考：ADR-002（Monorepo 結構中 hooks/ 目錄配置）、ADR-003（OODA 引擎發送事件）、ADR-004（HexConfirmModal 審批需雙向 WebSocket）、ADR-006（執行引擎回報結果觸發事件）
