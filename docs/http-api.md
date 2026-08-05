# HTTP API 參考

Athena 對外提供一組 HTTP 端點來啟動作戰、逐階段驅動 OODA 迴圈、查詢 fact / 知識庫 / 漏洞、跑多智能體 campaign、產報告。本文件記錄**穩定 wire 契約**：每個端點的 method、路徑、以及請求 / 回應的 JSON 形狀（範例為示意，實際欄位以你部署的版本為準）。

## 通則

- **前綴**：所有路徑都在 `/api` 之下。
- **認證**：若部署時設了環境變數 `ATHENA_API_TOKEN`，則**除 `GET /api/health` 外**，所有端點都需帶
  `Authorization: Bearer <token>`。未設 token 時（本機 / 測試）所有端點開放。
- **內容型別**：請求與回應皆為 `application/json`，除非另有標註（SSE / WebSocket）。
- **識別碼**：`op_id`（作戰）與 `campaign_id` 為 UUID 字串。

```bash
# 範例：帶 token 呼叫
curl -s http://localhost:58000/api/status \
  -H "Authorization: Bearer $ATHENA_API_TOKEN"
```

---

## Operations（作戰生命週期）

| Method | 路徑 | 說明 |
|---|---|---|
| `POST` | `/api/operations` | 啟動一次作戰（跑一輪迭代） |
| `GET` | `/api/operations` | 列出作戰 |
| `GET` | `/api/operations/:op_id/status` | 查作戰狀態 |
| `POST` | `/api/operations/:op_id/abort` | 中止作戰 |

**`POST /api/operations`** — 請求 body 全部選填（可送空 `{}`）：

```jsonc
{
  "name": "recon-web-01",
  "target_ip": "203.0.113.10",           // 你擁有 / 授權的目標
  "target_hostname": "host.example.test",
  "mode": "normal",                       // 執行模式（預設 normal）
  "async": false,
  "credentials": [
    { "realm": "203.0.113.0/24", "username": "svc", "secret": "…", "kind": "password" }
  ]
}
```

同步（`async:false`）回應：

```json
{ "op_id": "…", "name": "recon-web-01", "iter_id": "…",
  "facts_collected": 3, "total_facts": 10,
  "target_ip": "203.0.113.10", "target_hostname": null, "mode": "normal" }
```

非同步（`async:true`）回 `202`：`{ "op_id": "…", "status": "running" }`。

**`GET /api/operations/:op_id/status`** → `{ "op_id":"…", "status":"running|completed|failed", "iter_id":"…", "facts_collected":3, "total_facts":10, "error":null }`
**`POST /api/operations/:op_id/abort`** → `{ "aborted": true, "op_id": "…" }`

---

## OODA phases（逐階段驅動）

全部在 `/api/operations/:op_id/` 之下。可整輪跑（`/iterate`），也可逐階段呼叫以觀察每步。

| Method | 路徑尾 | 回應（頂層欄位） |
|---|---|---|
| `POST` | `/iterate` | `{ op_id, iter_id, facts_collected, total_facts, mode }` |
| `POST` | `/observe` | `{ op_id, facts_before }` |
| `GET` | `/observe/summary` | `{ op_id, summary }` |
| `POST` | `/orient` | `{ op_id, iter_id, facts_collected }` |
| `POST` | `/decide` | `{ op_id, opsec_noise, threat_level }` |
| `POST` | `/act` | `{ op_id, iter_id, results }` |
| `POST` | `/approve` | `{ op_id, iter_id, approved_by, facts_collected, total_facts }` |
| `GET` | `/brief` | `{ op_id, brief }` |
| `POST` | `/scope/check` | `{ op_id, in_scope }` |
| `GET` | `/opsec` | `{ op_id, noise_level, budget_remaining, threat_level }` |
| `POST` | `/opsec/consume` | `{ op_id, budget_remaining, threat_level }` |

> ⚠️ 注意 method：`observe/summary`、`brief`、`opsec` 是 **`GET`**（不是 POST）。

請求 body：
- `/iterate` — 選填，同 `POST /api/operations` 的 body。
- `/approve` — 選填 `{ "approved_by": "operator" }`。
- `/scope/check` — `{ "hostname": "…", "ip": "203.0.113.10" }`（兩者皆選填）。
- `/opsec/consume` — `{ "cost": 5 }`（必填整數）。

---

## Scheduler（背景排程迭代）

| Method | 路徑 | body / 回應 |
|---|---|---|
| `POST` | `/api/operations/:op_id/scheduler/start` | body `{ "interval_secs": 60 }` → `{ op_id, started:true, interval_secs }` |
| `DELETE` | `/api/operations/:op_id/scheduler/stop` | → `{ op_id, stopped:true }` |
| `GET` | `/api/scheduler/active` | → `{ "active": [ … ] }` |

> ⚠️ 停止排程是 **`DELETE`**（不是 POST）。

---

## Facts（作戰蒐集到的事實）

| Method | 路徑 | 回應 |
|---|---|---|
| `GET` | `/api/operations/:op_id/facts` | fact 物件陣列 |
| `GET` | `/api/operations/:op_id/facts/count` | `{ op_id, count }` |

---

## Knowledge Base（內建攻防知識庫）

| Method | 路徑 | 回應 |
|---|---|---|
| `GET` | `/api/kb/search?q=<text>&limit=<n>` | 條目陣列 |
| `GET` | `/api/kb/:id` | 單一條目（找不到回 `404`） |
| `GET` | `/api/kb/category/:category` | 條目陣列 |

- 搜尋參數是 **`q`**（`limit` 預設 10）。
- 條目形狀：`{ "id":"…", "title":"…", "category":"…", "tags":[], "platform":[], "content":"…", "commands":[], "references":[] }`。
- `:category` 例：`privilege_escalation`、`lateral_movement`、`initial_access`、`persistence`、`defense_evasion`、`credential_access`、`discovery`、`exfiltration`。

---

## Vuln（CVE 查詢）

| Method | 路徑 | 回應 |
|---|---|---|
| `GET` | `/api/vuln/search?keyword=<text>&limit=<n>` | CVE 陣列 |
| `GET` | `/api/vuln/cve/:cve_id` | 單一 CVE |

- ⚠️ 漏洞搜尋參數是 **`keyword`**（不是 `q`）。
- CVE 形狀：`{ "cve_id":"CVE-2024-1234", "cvss_score":7.5, "description":"…", "published":"2024-01-01T00:00:00Z" }`。

---

## Campaign（多智能體編排）

| Method | 路徑 | 回應 |
|---|---|---|
| `POST` | `/api/campaign` | `202` → `{ campaign_id, op_id, status:"running" }` |
| `GET` | `/api/campaign/:id` | **SSE 串流**（`text/event-stream`）— 即時狀態事件 |
| `GET` | `/api/campaign/:id/poll` | 單筆 JSON 狀態快照 |
| `GET` | `/api/campaign/:id/graph` | 圖快照 JSON（未就緒回 `202`） |
| `GET` | `/api/campaign/:id/facts/search?q=<text>&limit=<n>` | `{ "results": [ … ] }` |

**`POST /api/campaign`** 請求 body：

```jsonc
{
  "description": "…（上限 1000 字）",
  "targets": ["203.0.113.10"],          // 不可為空
  "max_agents": 4,
  "max_adaptive_rounds": 3,
  "time_budget_secs": 600
}
```

> ⚠️ `GET /api/campaign/:id` 是 **SSE 串流**，不是普通 JSON GET；要單筆 JSON 快照請用 `/api/campaign/:id/poll`。
> 錯誤：目標為空或 `description` 超過 1000 字回 `400`；編排器未配置回 `503`。

狀態快照形狀：`{ "campaign_id":"…", "op_id":"…", "status":"running|completed|failed", "tasks_completed":3, "tasks_failed":0, "adaptive_rounds":2, "total_facts":10, "error":null }`。

---

## Report（作戰報告）

| Method | 路徑 | 回應 |
|---|---|---|
| `GET` | `/api/operations/:op_id/report` | 結構化報告 JSON |
| `GET` | `/api/operations/:op_id/report/markdown` | `{ op_id, markdown }` |

報告 JSON 形狀：

```json
{ "op_id":"…", "title":"…", "executive_summary":"…",
  "findings":[ { "id":"…", "title":"…",
                 "severity":"critical|high|medium|low|informational",
                 "description":"…", "remediation":"…" } ],
  "generated_at":"2026-01-01T00:00:00Z" }
```

---

## Status / Health

| Method | 路徑 | 認證 | 回應 |
|---|---|---|---|
| `GET` | `/api/health` | 免認證 | `{ "status":"ok", "version":"…", "service":"athena" }` |
| `GET` | `/api/status` | 需 token（若有設） | 合規閘 + 子系統就緒摘要 |

`GET /api/status` 回傳一份**執行期健康摘要**——合規閘（scope / opsec）狀態與各子系統就緒情形。用於部署後健檢；示意：

```json
{ "scope": "strict", "opsec": "strict" }
```

（`/status` 需認證、供部署後健檢；`/health` 是唯一免認證端點、且是唯一回 `status`/`version` 的端點，適合當 liveness probe。）
