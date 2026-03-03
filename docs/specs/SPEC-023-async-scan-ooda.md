# SPEC-023：非同步掃描與 OODA 操作規格書

> 結構完整的規格書讓 AI 零確認直接執行。

| 欄位 | 內容 |
|------|------|
| **規格 ID** | SPEC-023 |
| **狀態** | Accepted |
| **版本** | 1.0.0 |
| **作者** | Athena Contributors |
| **建立日期** | 2026-03-03 |
| **關聯 ADR** | ADR-023（非同步長時間操作架構） |
| **估算複雜度** | 高 |
| **建議模型** | Sonnet |
| **HITL 等級** | standard |

---

## 🎯 目標（Goal）

統一定義 Athena 所有長時間 API 操作的非同步合約：立即回傳 202 Accepted → WebSocket 進度推送 → DB status 欄位作為唯一真相來源。

**解決問題**：Next.js rewrites proxy 預設逾時約 15 秒，導致 nmap 掃描（28-60s）、OODA 循環（30-120s）等操作出現 ECONNRESET。透過 202-pattern，所有長時間操作在 <200ms 內回應，背景工作透過 WebSocket 持續推送進度。

---

## 📥 適用範圍（Scope）

下列 endpoint 均受本規格書約束，須遵循非同步合約：

| Endpoint | 原耗時 | 嚴重度 | 實作狀態 |
|----------|--------|--------|---------|
| `POST /operations/{op_id}/recon/scan` | 28-60s | Critical | Task 2 完成 |
| `POST /operations/{op_id}/ooda/trigger` | 30-120s | Critical | Task 3 完成 |
| `POST /operations/{op_id}/osint/discover` | 10-20s | High | Task 4 完成 |
| `POST /operations/{op_id}/agents/sync` | 5-10s | High | Task 5 完成 |
| `POST /techniques/sync-caldera` | 3-8s | High | Task 5 完成 |

---

## 📤 非同步 API 合約（Async API Contract）

### 3.1 HTTP 合約

所有上述 endpoint 均遵循以下模式：

```
POST /operations/{op_id}/recon/scan
→ 202 Accepted（立即，<200ms）
→ {
    "scan_id": "<uuid>",
    "status": "queued",
    "message": "Scan started in background"
  }

POST /operations/{op_id}/ooda/trigger
→ 202 Accepted（立即，<200ms）
→ {
    "iteration_id": "<uuid>",
    "status": "queued",
    "message": "OODA loop triggered"
  }

POST /operations/{op_id}/osint/discover
→ 202 Accepted（立即，<200ms）
→ {
    "domain": "<domain>",
    "status": "queued",
    "message": "OSINT discovery started"
  }

POST /operations/{op_id}/agents/sync
→ 202 Accepted（立即，<200ms）
→ {
    "status": "queued",
    "message": "Agent sync started"
  }

POST /techniques/sync-caldera
→ 202 Accepted（立即，<200ms）
→ {
    "status": "queued",
    "message": "Caldera technique sync started"
  }
```

### 3.2 通用後端實作模式

所有受影響 endpoint 的後端實作遵循以下四步驟：

1. **同步驗證**（<50ms）：驗證 operation / target 存在，輸入格式正確
2. **插入 DB 記錄**（若適用）：以 `status='queued'` 建立記錄，取得 ID
3. **啟動背景工作**：`asyncio.create_task(_run_*_background(...))` 立即返回
4. **回傳 202 Accepted**：攜帶 `{status: "queued", ...}` 立即回應

**背景工作原則：**

- 使用獨立 `aiosqlite.connect(_DB_FILE)` 連線，不共享 request 的 DB 連線
- 在關鍵節點廣播 WebSocket 事件（started / progress / completed / failed）
- 最終將 DB status 更新為 `completed` 或 `failed`
- 捕獲所有例外，廣播對應的 `*.failed` WebSocket 事件，確保前端不永久等待

---

## 📡 WebSocket 事件清單（Event Catalogue）

| 事件類型 | 觸發時機 | Payload 欄位 |
|----------|----------|-------------|
| `recon.started` | nmap 掃描開始 | `scan_id`, `target_id` |
| `recon.progress` | nmap 完成，進入 initial access 階段 | `scan_id`, `phase` |
| `recon.completed` | 掃描全部完成 | `scan_id`, `target_id`, `facts_written`, `credential_found`, `services_found` |
| `recon.failed` | 掃描失敗（任何階段） | `scan_id`, `target_id`, `error` |
| `ooda.failed` | OODA 循環失敗 | `iteration_id`, `error` |
| `osint.completed` | OSINT 發現完成 | `domain`, `subdomains_found` |
| `osint.failed` | OSINT 失敗 | `domain`, `error` |
| `agents.synced` | Agent 同步完成 | `operation_id` |
| `agents.sync_failed` | Agent 同步失敗 | `error` |

> 注意：`ooda.phase` 事件由 OODAController 內部廣播，不在本 SPEC 範圍內定義。

---

## 🖥️ 前端訂閱映射（Frontend Subscription Map）

前端透過 WebSocket 訂閱以下事件，並於收到後觸發對應 UI 動作：

| 事件類型 | 訂閱位置 | 處理動作 |
|----------|----------|---------|
| `recon.completed` | `planner/page.tsx` | `refreshTargets()` + 清除掃描指示器 + success toast |
| `recon.failed` | `planner/page.tsx` | 清除掃描指示器 + error toast |
| `ooda.failed` | `planner/page.tsx` | 清除 OODA phase 指示器 + error toast |

---

## 🗄️ DB 狀態機（DB Status State Machine）

**recon_scans.status：**

```
queued → running → completed
                ↘ failed
```

**ooda_iterations：**

無獨立 DB 狀態機。OODA 失敗事件僅透過 WebSocket `ooda.failed` 廣播，不在 DB 持久化失敗狀態。

---

## ⏱️ 前端 API 超時保護（Frontend Timeout Guard）

`frontend/src/lib/api.ts` 的 `request()` 函數使用 `AbortController`，預設逾時 **30 秒**：

- 所有 202-pattern endpoint 在 <200ms 內回應，遠低於 30s 閾值，正常情況不會觸發
- 若後端因例外無法回應，AbortController 於 30s 後自動中斷請求，防止前端永久 pending
- 前端在收到 202 後即可轉為監聽 WebSocket 事件，無需輪詢

---

## ⚠️ 邊界條件（Edge Cases）

| 情境 | 處理方式 |
|------|---------|
| 背景工作中途拋出未捕獲例外 | `except Exception as e` 捕獲，廣播 `*.failed` 事件，DB 更新 `status=failed` |
| WebSocket 廣播失敗（客戶端未連線） | 忽略廣播錯誤，不影響背景工作繼續執行 |
| 同一 operation 並發觸發多次掃描 | 允許並發，各自擁有獨立 `scan_id`，DB 各自記錄 |
| 背景工作完成但前端已離開頁面 | 事件廣播到空集合，無副作用；DB 狀態正確更新 |
| DB 連線於背景工作中斷 | 捕獲例外，廣播 `*.failed`，記錄至 server log |

---

## ✅ 驗收標準（Done When）

- [x] 所有 Critical / High endpoint 回應 <200ms（Tasks 2-6 完成）
- [x] WebSocket 廣播正確的 started / completed / failed 事件（Tasks 2-5 完成）
- [x] 前端訂閱 `recon.completed`、`recon.failed`、`ooda.failed`（已完成）
- [x] `frontend/src/lib/api.ts` 具備 AbortController 30s 超時保護（Task 6 完成）
- [x] 所有後端測試通過（227 tests passing）
- [x] 背景工作使用獨立 DB 連線，不共享 request scope 連線（已確認）

---

## 🚫 禁止事項（Out of Scope）

- 不實作：HTTP long-polling 或輪詢替代方案（WebSocket 為唯一進度推送機制）
- 不修改：WebSocket 連線管理（由既有 `ConnectionManager` 處理）
- 不實作：背景工作佇列（Celery/RQ 等），asyncio.create_task 已足夠
- 不修改：ooda_iterations DB schema（OODA 失敗不寫入 DB）
- 不引入：新的 pip 套件（使用既有 asyncio + aiosqlite）

---

## 📎 參考資料（References）

- 關聯 ADR：ADR-023（非同步長時間操作架構）
- 相關 SPEC：SPEC-019（Recon & Initial Access）、SPEC-007（OODA Loop Engine）
- 實作位置：
  - `backend/app/routers/recon.py` — `POST /recon/scan` 202 pattern
  - `backend/app/routers/ooda.py` — `POST /ooda/trigger` 202 pattern
  - `backend/app/routers/osint.py` — `POST /osint/discover` 202 pattern
  - `backend/app/routers/agents.py` — `POST /agents/sync` 202 pattern
  - `frontend/src/lib/api.ts` — AbortController timeout guard
  - `frontend/src/app/planner/page.tsx` — WebSocket event subscriptions
