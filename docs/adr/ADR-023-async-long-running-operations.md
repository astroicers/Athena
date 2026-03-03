# [ADR-023]: 非同步長時間操作架構 — 202 Accepted + WebSocket 進度推送

| 欄位 | 內容 |
|------|------|
| **狀態** | `Accepted` |
| **日期** | 2026-03-03 |
| **決策者** | 專案負責人 |

## 背景（Context）

Athena 有多個 API endpoint 在 HTTP request 期間執行耗時操作，導致 Next.js proxy (`rewrites`) 超時並回傳 `ECONNRESET`，前端顯示 `Internal Server Error`。

已確認的問題 endpoint：

| Endpoint | 耗時估算 | 嚴重度 | 阻塞原因 |
|----------|---------|--------|---------|
| `POST /operations/{op_id}/recon/scan` | 28–60 秒 | 🔴 Critical | nmap + SSH 試驗 + agent bootstrap |
| `POST /operations/{op_id}/ooda/trigger` | 30–120 秒 | 🔴 Critical | Observe + LLM (60s) + Decide + Act |
| `POST /operations/{op_id}/osint/discover` | 10–20 秒 | 🟡 High | crt.sh + subfinder + DNS 解析 |
| `POST /operations/{op_id}/agents/sync` | 5–10 秒 | 🟡 High | C2 engine API 呼叫 |
| `POST /techniques/sync-caldera` | 3–8 秒 | 🟡 High | Caldera ability list API |

根本原因：
- Next.js `rewrites` proxy 無法設定 timeout，預設約 10–15 秒
- 所有長時間操作都在同步 HTTP request 中完成
- 前端 `api.ts` 的 `request()` 無 AbortController，無超時保護

另一問題：WebSocket 訂閱缺口 — 後端廣播 `fact.new`（5 個廣播點）和 `recommendation`（2 個廣播點），但前端無對應頁面訂閱，使用者無法即時看到掃描結果和 AI 推薦。

## 決策（Decision）

統一採用 **202 Accepted + `asyncio.create_task` + WebSocket 進度推送** 模式：

```
舊模式：POST → 阻塞 30s → 回傳結果
新模式：POST → 立即回傳 {job_id, status:"queued"} → asyncio.create_task(實際工作) → WebSocket 推送進度
```

### 後台執行規則

1. **後台任務**：`asyncio.create_task()` + 獨立 `aiosqlite.connect(_DB_FILE)` — 不共享 HTTP request 的 DB connection
2. **進度廣播**：在關鍵節點呼叫 `ws_manager.broadcast(op_id, "event.type", data)`
3. **DB status**：長時間操作的 DB 記錄 status ∈ {queued, running, completed, failed}，成為前端狀態的唯一真相來源
4. **前端更新**：訂閱 WebSocket 事件觸發 UI 刷新，取代同步等待

### 新增 WebSocket 事件類型

| 事件 | 觸發時機 | data 欄位 |
|------|---------|---------|
| `recon.started` | 後台任務開始、status 改為 running | `{scan_id, target_id, operation_id}` |
| `recon.progress` | nmap 完成、進入 initial_access 階段 | `{scan_id, phase, services_found}` |
| `recon.completed` | 掃描全部完成 | `{scan_id, facts_written, credential_found, services_found}` |
| `recon.failed` | 掃描失敗 | `{scan_id, error}` |
| `osint.completed` | OSINT 發現完成 | `{job_id, subdomains_found, facts_written}` |

### 前端 WebSocket 訂閱補齊

- `fact.new`：Battle Monitor 頁面即時新增 fact 條目
- `recommendation`：Battle Monitor 頁面即時顯示最新 AI 推薦

### 前端 API timeout 保護

`api.ts` 的 `request()` 加入 AbortController，預設 30 秒 timeout（足以接收 202 回傳）。

## 候選方案回顧

### 選項 A：202 Accepted + asyncio.create_task ✅ 選定
- 無外部依賴，使用現有 asyncio 事件迴圈
- `asyncio.create_task` 模式已在 `PersistenceEngine`（`engine_router.py:221`）驗證
- WebSocket 機制已建立（`ws_manager.broadcast`）

### 選項 B：Celery / RQ task queue ❌ 否決
- 需要 Redis broker，增加外部依賴
- Docker Compose 需要新增 worker service
- 複雜度過高，現有規模不需要

### 選項 C：APScheduler 一次性 job ❌ 否決
- APScheduler 設計用於週期性任務（OODA auto loop）
- 一次性任務用 `asyncio.create_task` 更直接

## 後果（Consequences）

**正面影響：**
- 所有耗時操作 HTTP 回應 <100ms，Next.js proxy timeout 問題消除
- 前端 UI 不再卡頓，SCANNING... 狀態由 WebSocket 事件驅動
- `fact.new` 和 `recommendation` 事件補齊後，使用者可即時看到掃描結果和 AI 推薦
- 現有 WebSocket 基礎設施（`ws_manager`、`useWebSocket` hook）無需改動

**負面影響：**
- POST endpoint 回傳語義從「結果」改為「已排隊」，HTTP status 從 200 改為 202
- 前端需要訂閱 WebSocket 事件才能得知操作結果（非同步模式）
- 測試需要 mock WebSocket 廣播，而非直接斷言回傳值

**技術債：**
- `GET /operations/{op_id}/recon/scans/{scan_id}` 輪詢 endpoint 未實作（前端依賴 WebSocket，若 WS 斷線無法得知掃描結果）— 留待下個 phase

## 參考

- [ADR-007](ADR-007-websocket-realtime-communication.md)：WebSocket 即時通訊架構
- [ADR-015](ADR-015-recon--initial-access----kill-chain-.md)：Recon & Initial Access（本 ADR 修復其同步阻塞技術債）
- `backend/app/services/engine_router.py:221`：asyncio.create_task 後台執行範例（PersistenceEngine）
