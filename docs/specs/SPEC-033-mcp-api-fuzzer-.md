# SPEC-033：mcp-api-fuzzer MCP Tool Server

> 結構完整的規格書讓 AI 零確認直接執行。

| 欄位 | 內容 |
|------|------|
| **規格 ID** | SPEC-033 |
| **狀態** | Accepted |
| **版本** | 1.0.0 |
| **作者** | Athena Contributors |
| **建立日期** | 2026-03-06 |
| **關聯 ADR** | ADR-029（應用層攻擊能力擴展 Application Layer Attack）、ADR-024（MCP Architecture） |
| **估算複雜度** | 高 |
| **建議模型** | Opus |
| **HITL 等級** | minimal |

---

## 🎯 目標（Goal）

建立 `mcp-api-fuzzer` MCP 工具伺服器（port 58097），封裝 **ffuf**（高效能 HTTP fuzzer）與 **自建 Python API schema detector**，提供 API endpoint discovery、OpenAPI/GraphQL schema 偵測、authentication/authorization bypass testing（BOLA/IDOR）、以及 parameter fuzzing 能力。

此工具伺服器填補 Athena 在 API 安全測試領域的能力缺口。當 mcp-web-scanner 的 `web_http_probe` 偵測到 API endpoint 或 web framework 時，OrientEngine 可推薦使用 api-fuzzer 進行深度 API 探測。結果作為 `api.*` Facts 寫入資料庫，融入 OODA 循環的應用層攻擊路徑分析。

---

## 📥 輸入規格（Inputs）

### MCP Tool 1: `api_schema_detect`

OpenAPI / Swagger / GraphQL endpoint 自動偵測。

| 參數名稱 | 型別 | 來源 | 限制條件 |
|----------|------|------|----------|
| `base_url` | `str` | MCP tool call | 基礎 URL（含 scheme），如 `http://192.168.1.5:8080`；必須通過 ScopeValidator |

**內部實作：** 自建 Python 腳本依序探測常見 schema endpoint：

1. **OpenAPI/Swagger 探測** — 對以下路徑發送 GET 請求，檢查 response content-type 和 body：
   - `/openapi.json`, `/openapi.yaml`
   - `/swagger.json`, `/swagger.yaml`, `/swagger/`
   - `/api-docs`, `/api-docs.json`
   - `/v1/openapi.json`, `/v2/openapi.json`, `/v3/openapi.json`
   - `/api/v1/docs`, `/api/v2/docs`, `/api/v3/docs`
   - `/docs`, `/redoc`

2. **GraphQL 探測** — 對以下路徑發送 POST 請求（introspection query）：
   - `/graphql`, `/graphiql`, `/graphql/console`, `/gql`
   - Introspection query: `{"query": "{ __schema { types { name } } }"}`

3. **Schema 解析** — 偵測到 OpenAPI spec 時，提取 endpoint 數量、版本號、API title。

### MCP Tool 2: `api_endpoint_enum`

API endpoint enumeration via ffuf wordlist + optional schema-based discovery。

| 參數名稱 | 型別 | 來源 | 限制條件 |
|----------|------|------|----------|
| `base_url` | `str` | MCP tool call | 基礎 URL（含 scheme）；必須通過 ScopeValidator |
| `schema_url` | `str \| None` | MCP tool call | OpenAPI spec URL（由 `api_schema_detect` 發現）；`None` 時使用 wordlist-only 模式 |
| `wordlist` | `str` | MCP tool call | 內建 wordlist 名稱：`"api-common"` (預設, ~1,500 API 路徑), `"api-large"` (~5,000)；或容器內自訂絕對路徑 |

**內部實作（兩階段）：**

**階段 1 — Schema-based discovery（若 `schema_url` 提供）：**
- 下載 OpenAPI spec -> 解析所有 `paths` 定義 -> 生成 endpoint list
- 對每個 endpoint 發送對應 HTTP method（GET/POST/PUT/DELETE）驗證可達性
- 記錄每個 endpoint 的 HTTP status code 和 auth 要求（401/403 = auth_required）

**階段 2 — ffuf wordlist-based fuzzing：**
- 呼叫 `ffuf -u <base_url>/FUZZ -w <wordlist> -mc 200,201,204,301,302,307,401,403,405 -of json -o /tmp/ffuf_result.json -rate <FUZZ_RATE_LIMIT> -t 50 -timeout <FUZZ_TIMEOUT_SEC>`
- 過濾 false positives：若 >80% 的請求回傳相同 status code + body size，視為 wildcard response，排除之
- 合併兩階段結果，去重

**Wordlist 路徑映射：**
- `"api-common"` -> `/opt/wordlists/api-common.txt`（包含常見 REST API 路徑：`users`, `admin`, `auth/login`, `api/v1`, etc.）
- `"api-large"` -> `/opt/wordlists/api-large.txt`（SecLists Discovery/Web-Content/api 系列合併）

### MCP Tool 3: `api_auth_test`

Authentication / authorization bypass testing（BOLA / IDOR）。

| 參數名稱 | 型別 | 來源 | 限制條件 |
|----------|------|------|----------|
| `endpoint` | `str` | MCP tool call | 完整 API endpoint URL，如 `http://192.168.1.5:8080/api/v1/users/1`；必須通過 ScopeValidator |
| `method` | `str` | MCP tool call | HTTP method：`"GET"`, `"POST"`, `"PUT"`, `"DELETE"`, `"PATCH"`；預設 `"GET"` |
| `auth_token` | `str \| None` | MCP tool call | Bearer token 或 session cookie；`None` 時測試 unauthenticated access |

**內部實作（測試矩陣）：**

1. **Unauthenticated access test** — 不帶任何 auth header 請求 endpoint
   - 若 HTTP 200 + 有效 data -> `api.vuln.auth_bypass`

2. **BOLA/IDOR test**（僅當 URL 含數字 ID pattern 時觸發）：
   - 從 URL 中提取 ID parameter（regex: `/(\d+)(?:/|$|\?)`）
   - 嘗試存取 adjacent IDs（ID-1, ID+1, ID+100, 0, 1）
   - 若使用同一 auth_token 可存取不同 ID 的 data -> `api.vuln.bola`
   - 若不帶 auth 可存取任意 ID -> `api.vuln.idor`

3. **HTTP method tampering** — 嘗試非預期 method：
   - 若 endpoint 為 GET，嘗試 POST/PUT/DELETE
   - 若回傳 200/201/204（非 405 Method Not Allowed）-> `api.vuln.auth_bypass`

4. **Header manipulation test**：
   - 嘗試 `X-Original-URL`, `X-Rewrite-URL` header bypass
   - 嘗試 path traversal: `/api/v1/admin/../users/1`

### MCP Tool 4: `api_param_fuzz`

Parameter fuzzing for injection vulnerabilities。

| 參數名稱 | 型別 | 來源 | 限制條件 |
|----------|------|------|----------|
| `endpoint` | `str` | MCP tool call | 完整 API endpoint URL；必須通過 ScopeValidator |
| `method` | `str` | MCP tool call | HTTP method；預設 `"GET"` |
| `params` | `dict` | MCP tool call | 參數名稱 -> 原始值的 dict，如 `{"id": "1", "search": "test"}`；至少 1 個參數，最多 50 個 |

**內部實作（逐參數 fuzzing）：**

對每個參數逐一注入 fuzz payload（其他參數保持原始值），觀察 response 差異：

**Injection payloads（分類）：**

| 類型 | Payloads | 偵測方式 |
|------|----------|----------|
| SQL Injection | `' OR 1=1--`, `1' UNION SELECT null--`, `'; DROP TABLE--`, `1 AND 1=1`, `1 AND 1=2` | Response body 含 SQL error keywords (`mysql`, `ORA-`, `syntax error`, `SQLSTATE`)；或 `1=1` vs `1=2` response 差異 |
| Command Injection | `` `id` ``, `$(whoami)`, `; ls -la`, `| cat /etc/passwd` | Response body 含 `uid=`, `root:`, command output patterns |
| Path Traversal | `../../../etc/passwd`, `....//....//etc/passwd`, `%2e%2e%2f` | Response body 含 `root:x:0:0:` 或其他 passwd file patterns |
| XSS (Reflected) | `<script>alert(1)</script>`, `"><img src=x onerror=alert(1)>` | Injected payload 出現在 response body（未 encoded） |
| Integer Overflow | `99999999999999999`, `-1`, `0`, `2147483648` | HTTP 500 error 或 unexpected response structure |
| Type Confusion | `[]`, `{}`, `null`, `true`, `["__proto__"]` | HTTP 500 error 或 stack trace in response |

**ffuf 整合（大量參數時）：**
- 當 params dict 包含 >5 個參數時，使用 ffuf 批次 fuzzing 取代 Python httpx 逐一請求：
- `ffuf -u <endpoint>?FUZZ=<payload_file> -w /opt/wordlists/fuzz-params.txt -mc all -of json -rate <FUZZ_RATE_LIMIT>`

---

## 📤 輸出規格（Expected Output）

所有工具遵循 ADR-024 MCPFactExtractor Layer 1 結構化 JSON 格式：

```json
{"facts": [{"trait": "...", "value": "..."}], "raw_output": "..."}
```

### `api_schema_detect` 成功回應：

```json
{
  "facts": [
    {
      "trait": "api.schema.openapi",
      "value": "http://192.168.1.5:8080/api/v1/openapi.json — OpenAPI 3.0.1 — 47 endpoints — title='Juice Shop API'"
    },
    {
      "trait": "api.schema.graphql",
      "value": "http://192.168.1.5:8080/graphql — GraphQL introspection enabled — 23 types"
    }
  ],
  "raw_output": "Probed 18 schema endpoints, found 2 (OpenAPI at /api/v1/openapi.json, GraphQL at /graphql)"
}
```

**Fact Trait 詳細說明：**

| Trait | 觸發條件 | Value 格式 |
|-------|----------|-----------|
| `api.schema.openapi` | 偵測到 OpenAPI/Swagger spec | `<spec_url> — <version> — <endpoint_count> endpoints — title='<api_title>'` |
| `api.schema.graphql` | 偵測到 GraphQL introspection | `<graphql_url> — GraphQL introspection enabled — <type_count> types` |

### `api_endpoint_enum` 成功回應：

```json
{
  "facts": [
    {
      "trait": "api.endpoint.found",
      "value": "GET http://192.168.1.5:8080/api/v1/users [200] [application/json] [size=1847]"
    },
    {
      "trait": "api.endpoint.found",
      "value": "GET http://192.168.1.5:8080/api/v1/products [200] [application/json] [size=5023]"
    },
    {
      "trait": "api.endpoint.auth_required",
      "value": "GET http://192.168.1.5:8080/api/v1/admin/users [401] [application/json] [size=43]"
    },
    {
      "trait": "api.endpoint.auth_required",
      "value": "DELETE http://192.168.1.5:8080/api/v1/users/1 [403] [application/json] [size=28]"
    }
  ],
  "raw_output": "Schema-based: 47 endpoints verified. ffuf wordlist: 12 additional endpoints found. Total unique: 52 (8 auth_required)"
}
```

**Fact Trait 詳細說明：**

| Trait | 觸發條件 | Value 格式 |
|-------|----------|-----------|
| `api.endpoint.found` | HTTP 200/201/204/301/302/307 回應 | `<METHOD> <url> [<status>] [<content_type>] [size=<bytes>]` |
| `api.endpoint.auth_required` | HTTP 401/403 回應 | `<METHOD> <url> [<status>] [<content_type>] [size=<bytes>]` |

### `api_auth_test` 成功回應：

```json
{
  "facts": [
    {
      "trait": "api.vuln.bola",
      "value": "BOLA confirmed: GET /api/v1/users/2 accessible with user_1 token (expected 403, got 200 with different user data)"
    },
    {
      "trait": "api.vuln.idor",
      "value": "IDOR confirmed: GET /api/v1/users/1 accessible without authentication (HTTP 200, body contains user PII)"
    },
    {
      "trait": "api.vuln.auth_bypass",
      "value": "Method tampering: DELETE /api/v1/users/1 returns 204 (expected 405 Method Not Allowed)"
    }
  ],
  "raw_output": "Tested 7 auth bypass vectors on GET /api/v1/users/1. Found 3 vulnerabilities: 1 BOLA, 1 IDOR, 1 method_tampering."
}
```

**Fact Trait 詳細說明：**

| Trait | 觸發條件 | Value 格式 |
|-------|----------|-----------|
| `api.vuln.bola` | 使用一個 user 的 token 存取另一個 user 的資源成功 | `BOLA confirmed: <METHOD> <path> accessible with <token_owner> token (expected <expected_status>, got <actual_status> with different user data)` |
| `api.vuln.idor` | 無 auth 可存取具有 ID 的資源 | `IDOR confirmed: <METHOD> <path> accessible without authentication (HTTP <status>, body contains <data_type>)` |
| `api.vuln.auth_bypass` | HTTP method tampering 或 header manipulation 繞過 auth | `<bypass_type>: <METHOD> <path> returns <status> (expected <expected>)` |

### `api_param_fuzz` 成功回應：

```json
{
  "facts": [
    {
      "trait": "api.vuln.injection",
      "value": "SQL Injection in param 'id': GET /api/v1/users?id=' OR 1=1-- returns 200 with SQL error 'You have an error in your SQL syntax'"
    },
    {
      "trait": "api.vuln.injection",
      "value": "Command Injection in param 'filename': POST /api/v1/export?filename=$(whoami) returns 200 with 'www-data' in response"
    },
    {
      "trait": "api.vuln.overflow",
      "value": "Integer Overflow in param 'quantity': POST /api/v1/cart?quantity=99999999999999999 returns 500 Internal Server Error"
    }
  ],
  "raw_output": "Fuzzed 3 parameters with 18 payloads each (54 total requests). Found 3 vulnerabilities: 1 SQLi, 1 CMDi, 1 overflow."
}
```

**Fact Trait 詳細說明：**

| Trait | 觸發條件 | Value 格式 |
|-------|----------|-----------|
| `api.vuln.injection` | Fuzz payload 觸發 SQL error / command output / path traversal / reflected XSS | `<injection_type> in param '<param_name>': <METHOD> <url_with_payload> returns <status> with '<evidence>'` |
| `api.vuln.overflow` | Integer overflow 或 type confusion 觸發 500 error | `<overflow_type> in param '<param_name>': <METHOD> <url> returns <status> <error_message>` |

### 失敗情境：

| 錯誤類型 | 回應格式 | 處理方式 |
|----------|----------|----------|
| Target unreachable / DNS failure | `{"facts": [], "raw_output": "CONNECTION_ERROR: <base_url> — <error_detail>"}` | 回傳空 facts；不 raise exception |
| ScopeValidator violation | `{"facts": [], "raw_output": "SCOPE_VIOLATION: <target> is out of scope for this operation"}` | 不執行任何請求，直接回傳 |
| Rate limiting by target (429) | `{"facts": [<partial_results>], "raw_output": "RATE_LIMITED: target returned HTTP 429 after <N> requests, partial results"}` | 回傳已收集結果，自動降低 rate 重試一次 |
| Fuzz timeout | `{"facts": [<partial_results>], "raw_output": "TIMEOUT: fuzzing exceeded <N>s, <M>/<Total> payloads completed"}` | 回傳已完成的 partial results |
| ffuf binary missing | `{"facts": [], "raw_output": "DEPENDENCY_ERROR: ffuf binary not found at expected path"}` | 不影響不依賴 ffuf 的工具（`api_schema_detect`, `api_auth_test` 不依賴 ffuf） |
| Invalid OpenAPI spec | `{"facts": [], "raw_output": "SCHEMA_ERROR: Failed to parse OpenAPI spec at <url>: <parse_error>"}` | 記錄錯誤，可 fallback 至 wordlist-only mode |
| No API endpoints found | `{"facts": [], "raw_output": "No API endpoints discovered at <base_url>"}` | 非錯誤狀態，OODA 循環繼續 |
| Empty params dict | `{"facts": [], "raw_output": "VALIDATION_ERROR: params dict must contain at least 1 parameter"}` | 參數驗證失敗，不發送任何請求 |
| Huge response (>5MB) | 截斷 body 至 1MB | 防止 OOM |

---

## 🔗 副作用與連動（Side Effects）

| 本功能的狀態變動 | 受影響的既有功能 | 預期行為 |
|-----------------|----------------|---------|
| 新增 `api.schema.*` / `api.endpoint.*` / `api.vuln.*` facts 至 `facts` 表 | **OrientEngine** — 讀取 facts 進行 cross-fact reasoning | OrientEngine 接收 api facts 後，可推薦 API 層面攻擊手法（需後續 ADR-029 Phase 5 擴展 prompt）。例如：`api.schema.openapi` fact 存在 -> 推薦 `api_endpoint_enum`；`api.endpoint.auth_required` -> 推薦 `api_auth_test` |
| MCPClientManager 自動發現 4 個新工具，同步至 `tool_registry` | **Tool Registry UI** — `ToolRegistryTable.tsx` | 前端自動顯示 4 個新工具（api_schema_detect, api_endpoint_enum, api_auth_test, api_param_fuzz）及其連線狀態；無需前端程式碼修改 |
| `mcp_servers.json` 新增 `api-fuzzer` 配置 | **MCPClientManager startup** | 啟動時自動連線 api-fuzzer，Circuit Breaker 保護啟用 |
| `docker-compose.yml` 新增 `mcp-api-fuzzer` service | **Docker 部署流程** | `docker compose --profile mcp up` 自動啟動 api-fuzzer 容器 |
| WebSocket 廣播 `fact.new` 事件（api.* traits） | **War Room 前端** — fact panel + topology | 即時顯示 API 偵察結果；現有 `fact.new` handler 自動處理新 trait |
| 與 mcp-web-scanner 形成協作鏈 | **mcp-web-scanner (SPEC-032)** | web_http_probe 偵測到 API framework (Express/Django/Spring) -> OrientEngine 推薦 api_schema_detect -> api_endpoint_enum -> api_auth_test 的攻擊鏈 |

---

## ⚠️ 邊界條件（Edge Cases）

- **Case 1：Target unreachable / DNS resolution failure** — httpx/ffuf 回傳 connection error，facts 為空，`raw_output` 包含 `CONNECTION_ERROR` 前綴。不 raise exception，允許 OODA 循環繼續。

- **Case 2：Target 回傳 rate limit (HTTP 429)** — 偵測到 429 response 時：(1) 記錄目前已收集的 partial results，(2) 降低 `FUZZ_RATE_LIMIT` 至原始值的 25%，(3) 等待 `Retry-After` header 指定的秒數（無 header 時等待 30s），(4) 重試未完成的部分。若重試仍被 rate limit，回傳 partial results。

- **Case 3：ffuf wildcard response detection（false positive filtering）** — ffuf 掃描時，若 >80% 的探測路徑回傳相同 status code + 相似 body size（+/- 50 bytes），判定為 wildcard/custom 404 response。自動啟用 ffuf `-fw <word_count>` 或 `-fs <body_size>` filter 重新掃描。

- **Case 4：OpenAPI spec 格式異常或損壞** — 使用 Python `json.loads()` 或 `yaml.safe_load()` 解析失敗時，記錄 `SCHEMA_ERROR` 並 fallback 至 wordlist-only endpoint enumeration。不影響其他工具。

- **Case 5：GraphQL introspection disabled** — POST introspection query 回傳 400/403 或 response 不含 `__schema` 時，嘗試 field suggestion attack（發送 partial query 觀察 error message 中的 field hints）。若完全無法探測，記錄 `"GraphQL endpoint detected but introspection disabled"` fact。

- **Case 6：BOLA/IDOR test 的 ID 範圍** — 僅嘗試 5 個 adjacent IDs（original-1, original+1, original+100, 0, 1）。不進行暴力枚舉。每個 ID 僅發送 1 次請求。總計最多 5 次額外請求。

- **Case 7：auth_token 過期或無效** — 若使用 auth_token 的請求回傳 401，記錄 `"AUTH_TOKEN_INVALID: provided token returned 401"` 在 raw_output。仍繼續執行 unauthenticated tests。

- **Case 8：極大量 API endpoint (>500 endpoints in OpenAPI spec)** — 受 `MAX_ENDPOINTS` 環境變數限制（預設 500）。超過時截斷至前 500 個 endpoints（按 path 字母排序），`raw_output` 註明截斷。

- **Case 9：並發 fuzzing 同一 target** — 允許並發。Rate limiter 確保總請求數不超過 `FUZZ_RATE_LIMIT`。多個並發 fuzzing session 共享同一 token bucket。DB UNIQUE index 自動 dedup 重複 facts。

- **Case 10：Parameter fuzzing 觸發 WAF** — 若 injection payload 觸發 WAF blocking（所有 fuzz 請求均回傳 403），記錄 `"WAF_BLOCKING: injection payloads blocked by WAF"` fact，停止該參數的 fuzzing 並繼續下一個參數。

- **Case 11：Target API 需要 Content-Type: application/json** — `api_param_fuzz` 自動檢測 content-type：若原始 response 的 content-type 為 `application/json`，fuzzing 請求使用 JSON body；否則使用 URL query parameters 或 form-encoded body。

- **Case 12：api_endpoint_enum 的 schema_url 與 base_url host 不匹配** — 驗證 `schema_url` 的 host 必須與 `base_url` 相同或為同一 scope 內的 host。不匹配時回傳 `VALIDATION_ERROR`。

- **Case 13：IPv6 target** — httpx 和 ffuf 皆支援 IPv6。URL 使用 bracket notation `http://[::1]:8080`。

- **Case 14：Container 內 ffuf binary 不存在** — `api_endpoint_enum` 和 `api_param_fuzz`（大量參數模式）需要 ffuf。缺失時 `api_endpoint_enum` fallback 至純 Python httpx 逐一請求（較慢），`api_param_fuzz` 始終使用 Python httpx。`api_schema_detect` 和 `api_auth_test` 完全不依賴 ffuf。

### 回退方案（Rollback Plan）

- **回退方式**：revert commit + 移除 `docker-compose.yml` 中 `mcp-api-fuzzer` service + 移除 `mcp_servers.json` 中 `api-fuzzer` 配置。三步驟均為 git revert 即可完成。注意：此 SPEC 不修改 `recon_engine.py`（auto-trigger 為 SPEC-032 負責），故回退不涉及 ReconEngine。
- **不可逆評估**：此變更無不可逆部分。新增的 `api.*` facts 會留在資料庫但不影響既有功能。若需清理，可執行 `DELETE FROM facts WHERE trait LIKE 'api.%'`。
- **資料影響**：回退後已寫入的 api facts 不會自動刪除，但不影響系統正常運作。`tool_registry` 中的 mcp_discovery 記錄會在 MCPClientManager 偵測到 server 不可用後自動 soft-delete（現有機制）。

---

## ✅ 驗收標準（Done When）

### 檔案建立

- [ ] `tools/api-fuzzer/server.py` — 4 個 MCP 工具（`api_schema_detect`, `api_endpoint_enum`, `api_auth_test`, `api_param_fuzz`）實作完成
- [ ] `tools/api-fuzzer/Dockerfile` — 基於 `athena-mcp-base:latest`，安裝 ffuf + API wordlists + fuzz payload 檔案
- [ ] `tools/api-fuzzer/pyproject.toml` — 包含 `mcp>=1.6.0`、`httpx>=0.27`、`pyyaml>=6.0` 依賴
- [ ] `tools/api-fuzzer/schema_detector.py` — OpenAPI/Swagger/GraphQL schema 偵測模組（被 `server.py` import）
- [ ] `tools/api-fuzzer/auth_tester.py` — BOLA/IDOR/auth bypass 測試模組（被 `server.py` import）
- [ ] `tools/api-fuzzer/param_fuzzer.py` — Parameter fuzzing 模組，含 injection payload 定義（被 `server.py` import）
- [ ] `tools/api-fuzzer/__init__.py` — 空檔案（package marker）
- [ ] `tools/api-fuzzer/payloads/` — Fuzzing payload 目錄
  - [ ] `tools/api-fuzzer/payloads/sqli.txt` — SQL injection payloads
  - [ ] `tools/api-fuzzer/payloads/cmdi.txt` — Command injection payloads
  - [ ] `tools/api-fuzzer/payloads/xss.txt` — XSS payloads
  - [ ] `tools/api-fuzzer/payloads/traversal.txt` — Path traversal payloads
  - [ ] `tools/api-fuzzer/payloads/overflow.txt` — Integer overflow / type confusion payloads

### 檔案修改

- [ ] `mcp_servers.json` — 新增 `"api-fuzzer"` 配置項（transport: `"stdio"`, http_url: `"http://mcp-api-fuzzer:8080/mcp"`, tool_prefix: `"api"`, enabled: `true`）
- [ ] `docker-compose.yml` — 新增 `mcp-api-fuzzer` service（profile: `[mcp]`, ports: `127.0.0.1:58097:8080`, environment: `FUZZ_RATE_LIMIT`, `FUZZ_TIMEOUT_SEC`, `MAX_ENDPOINTS`）

### 測試

- [ ] `backend/tests/test_mcp_api_fuzzer.py` — 單元測試覆蓋全部 4 個工具 + 邊界條件
  - [ ] `test_api_schema_detect_openapi_found` — mock HTTP response 含 OpenAPI spec，驗證 `api.schema.openapi` fact
  - [ ] `test_api_schema_detect_graphql_found` — mock GraphQL introspection response，驗證 `api.schema.graphql` fact
  - [ ] `test_api_schema_detect_nothing_found` — 所有 schema endpoint 回傳 404，facts 為空
  - [ ] `test_api_schema_detect_graphql_introspection_disabled` — introspection disabled 時記錄 disabled fact
  - [ ] `test_api_schema_detect_unreachable` — target 不可達時回傳 CONNECTION_ERROR
  - [ ] `test_api_endpoint_enum_schema_based` — 提供 OpenAPI spec URL，驗證 schema-based endpoint discovery
  - [ ] `test_api_endpoint_enum_wordlist_only` — schema_url=None 時使用 wordlist-only mode（ffuf）
  - [ ] `test_api_endpoint_enum_auth_required` — 401/403 endpoint 標記為 `api.endpoint.auth_required`
  - [ ] `test_api_endpoint_enum_wildcard_filter` — ffuf wildcard response 正確過濾
  - [ ] `test_api_endpoint_enum_max_endpoints_truncation` — >500 endpoints 截斷
  - [ ] `test_api_auth_test_bola_detected` — BOLA 漏洞偵測：adjacent ID 存取成功
  - [ ] `test_api_auth_test_idor_detected` — IDOR 漏洞偵測：unauthenticated ID 存取成功
  - [ ] `test_api_auth_test_method_tampering` — HTTP method tampering bypass 偵測
  - [ ] `test_api_auth_test_no_id_in_url` — URL 無數字 ID 時跳過 BOLA/IDOR 測試
  - [ ] `test_api_auth_test_token_expired` — auth_token 無效時正確處理
  - [ ] `test_api_auth_test_all_secure` — 無漏洞時回傳空 facts
  - [ ] `test_api_param_fuzz_sqli_detected` — SQL injection payload 觸發 SQL error
  - [ ] `test_api_param_fuzz_cmdi_detected` — Command injection payload 觸發 command output
  - [ ] `test_api_param_fuzz_xss_detected` — XSS payload reflected in response
  - [ ] `test_api_param_fuzz_overflow_detected` — Integer overflow 觸發 500 error
  - [ ] `test_api_param_fuzz_no_vulns` — 所有 payload 無異常回應時 facts 為空
  - [ ] `test_api_param_fuzz_waf_blocking` — WAF blocking injection payloads 的處理
  - [ ] `test_api_param_fuzz_empty_params` — 空 params dict 回傳 VALIDATION_ERROR
  - [ ] `test_api_param_fuzz_json_content_type` — application/json endpoint 使用 JSON body fuzzing
  - [ ] `test_scope_validation_blocks_out_of_scope` — ScopeValidator 阻擋 out-of-scope URL
  - [ ] `test_rate_limiter_throttling` — rate limit 生效，超出時 sleep 而非 error
  - [ ] `test_dependency_missing_ffuf` — ffuf binary 不存在時 endpoint_enum fallback 至 Python httpx

- [ ] `make test` 全數通過
- [ ] `make lint` 無 error

### Docker 建置

- [ ] `docker compose build mcp-api-fuzzer` 成功（exit code 0）
- [ ] `docker compose --profile mcp up mcp-api-fuzzer` 啟動正常（log 確認 MCP server ready）
- [ ] Container 內 `ffuf -V` 回傳有效版本
- [ ] Container 內 `ls /opt/wordlists/api-common.txt` 確認 wordlist 存在
- [ ] Container 內 `ls /app/payloads/` 確認 fuzz payload 檔案存在
- [ ] Docker image size < 200MB（ffuf 為靜態 Go binary，體積小）

### 整合驗證

- [ ] MCPClientManager 啟動時自動連線 api-fuzzer，`list_tools()` 回傳 4 個工具
- [ ] `tool_registry` DB 表新增 4 筆 `source='mcp_discovery'` 的工具記錄（api_schema_detect, api_endpoint_enum, api_auth_test, api_param_fuzz）
- [ ] WebSocket 廣播 `mcp.server.status` 事件含 `"server": "api-fuzzer"` + `"connected": true`
- [ ] Circuit Breaker 測試：停止 api-fuzzer 容器 -> MCPClientManager circuit OPEN -> 重啟容器 -> 自動 HALF_OPEN -> reconnect 成功 -> circuit CLOSED
- [ ] 與 mcp-web-scanner 協作驗證：web_http_probe 偵測到 API -> 手動呼叫 api_schema_detect -> 發現 OpenAPI spec -> api_endpoint_enum 使用 schema URL 成功列出 endpoints

### 效能

- [ ] `api_schema_detect` 單一 target 回應時間 < 30s（探測 ~18 個 schema 路徑）
- [ ] `api_endpoint_enum` wordlist-only mode（api-common, ~1500 entries）回應時間 < 60s
- [ ] `api_endpoint_enum` schema-based mode（50 endpoints）回應時間 < 30s
- [ ] `api_auth_test` 單一 endpoint 回應時間 < 15s（最多 ~15 個測試請求）
- [ ] `api_param_fuzz` 3 parameters x 18 payloads = 54 requests 回應時間 < 30s

### 文件

- [ ] 已更新 `CHANGELOG.md`

---

## 🚫 禁止事項（Out of Scope）

- **不要** 實作 GraphQL mutation fuzzing — 列為 ADR-029 長期目標
- **不要** 實作 gRPC reflection API fuzzing — 列為 ADR-029 長期目標
- **不要** 修改 OrientEngine system prompt — API 攻擊推薦規則擴展屬於 ADR-029 Phase 5
- **不要** 修改 ScopeValidator 本體 — URL-based 擴展屬於 ADR-029 Phase 6。本 SPEC 使用現有 IP-based ScopeValidator 驗證 target host
- **不要** 修改 ReconEngine — auto-trigger 邏輯由 SPEC-032 負責。api-fuzzer 的觸發由 OrientEngine 推薦或手動調用
- **不要** 修改 MCPFactExtractor — 本 SPEC 的工具直接回傳 Layer 1 結構化 JSON
- **不要** 新增任何 Python 依賴至 backend `pyproject.toml` — 所有新依賴封裝在 `tools/api-fuzzer/` 容器內
- **不要** 實作 session/cookie management — auth_token 由呼叫方（OrientEngine/手動）提供，api-fuzzer 不維護 session state
- **不要** 實作 credential brute-force — 屬於 credential-checker 的職責，api-fuzzer 僅測試 auth bypass
- **不要** 修改前端程式碼 — 現有 Tool Registry UI 和 War Room fact panel 自動適配
- **不要** 實作 Escape.tech FDSAE 風格的語意分析 — 屬於長期演進目標，本期使用 wordlist + schema-based 方式

---

## 📎 參考資料（References）

- 相關 ADR：
  - [ADR-029：Application Layer Attack](/docs/adr/ADR-029--application-layer-attack.md) — 架構決策（選項 C 混合架構）、mcp-api-fuzzer 設計草案、七階段實作計劃
  - [ADR-024：MCP Architecture](/docs/adr/ADR-024-mcp-architecture-and-tool-server-integration.md) — MCP 架構基礎、MCPClientManager、MCPFactExtractor 三層 fallback、Circuit Breaker 設計
- 關聯 SPEC：
  - [SPEC-032：mcp-web-scanner](/docs/specs/SPEC-032-mcp-web-scanner-.md) — 同一 ADR-029 的姊妹 SPEC，負責 HTTP probe + Nuclei scan + ReconEngine auto-trigger
- 現有類似實作：
  - `tools/nmap-scanner/server.py` — MCP 工具伺服器範本（FastMCP + subprocess pattern）
  - `tools/vuln-lookup/server.py` — 外部 API 呼叫 + rate limiting 範例（NVD token bucket）
  - `tools/credential-checker/server.py` — auth testing 類工具參考
  - `tools/nmap-scanner/Dockerfile` — 基於 `athena-mcp-base:latest` 的 Dockerfile 範本
  - `backend/app/services/mcp_client_manager.py` — Circuit Breaker + periodic health check + tool registry sync
  - `backend/app/services/scope_validator.py` — IP/CIDR/hostname scope validation 實作
- 外部工具文件：
  - [ffuf](https://github.com/ffuf/ffuf) — Fast web fuzzer written in Go
  - [SecLists](https://github.com/danielmiessler/SecLists) — API wordlists（Discovery/Web-Content/api/）
  - [OWASP API Security Top 10](https://owasp.org/API-Security/) — API1:2023 BOLA, API2:2023 Broken Authentication
  - [Escape.tech FDSAE](https://escape.tech/) — 長期參考：Feedback-Driven Semantic API Exploration
  - [OWASP Juice Shop](https://owasp.org/www-project-juice-shop/) — 驗證測試目標（含 REST + GraphQL API）

---

## 附錄 A：`server.py` 架構概要

```python
"""api-fuzzer MCP Server for Athena.

Exposes API schema detection, endpoint enumeration, authentication
bypass testing, and parameter fuzzing as MCP tools.
Returns JSON with {"facts": [{"trait": ..., "value": ...}]}
to integrate with Athena's fact collection pipeline.
"""

import asyncio
import json
import os
import shutil

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

_security = TransportSecuritySettings(
    enable_dns_rebinding_protection=False,
)

mcp = FastMCP("athena-api-fuzzer", transport_security=_security)

# Environment-based configuration
FUZZ_RATE_LIMIT = int(os.environ.get("FUZZ_RATE_LIMIT", "50"))
FUZZ_TIMEOUT_SEC = int(os.environ.get("FUZZ_TIMEOUT_SEC", "180"))
MAX_ENDPOINTS = int(os.environ.get("MAX_ENDPOINTS", "500"))

# Wordlist path mapping
_WORDLISTS = {
    "api-common": "/opt/wordlists/api-common.txt",
    "api-large": "/opt/wordlists/api-large.txt",
}

# Import modular components
from schema_detector import detect_openapi, detect_graphql
from auth_tester import test_bola, test_idor, test_method_tampering, test_header_bypass
from param_fuzzer import fuzz_parameter, load_payloads


@mcp.tool()
async def api_schema_detect(base_url: str) -> str:
    """OpenAPI/Swagger/GraphQL endpoint detection.

    Probes common schema paths to discover API documentation
    and introspection endpoints.
    """
    # 1. Probe OpenAPI/Swagger paths (18+ common paths)
    # 2. Probe GraphQL endpoints with introspection query
    # 3. Parse discovered schemas -> extract endpoint count, version
    # 4. Return structured facts
    ...


@mcp.tool()
async def api_endpoint_enum(
    base_url: str,
    schema_url: str | None = None,
    wordlist: str = "api-common",
) -> str:
    """API endpoint enumeration via wordlist + schema.

    Phase 1: If schema_url provided, parse OpenAPI spec endpoints.
    Phase 2: ffuf wordlist-based fuzzing for additional endpoints.
    """
    # 1. Schema-based discovery (if schema_url provided)
    # 2. ffuf wordlist fuzzing (with wildcard filter)
    # 3. Merge + dedup results
    # 4. Classify auth_required (401/403)
    # 5. Truncate to MAX_ENDPOINTS
    ...


@mcp.tool()
async def api_auth_test(
    endpoint: str,
    method: str = "GET",
    auth_token: str | None = None,
) -> str:
    """Authentication/authorization bypass testing (BOLA/IDOR).

    Tests unauthenticated access, BOLA via adjacent IDs,
    method tampering, and header manipulation bypass.
    """
    # 1. Unauthenticated access test
    # 2. BOLA/IDOR test (if URL contains numeric ID)
    # 3. HTTP method tampering
    # 4. Header manipulation (X-Original-URL, path traversal)
    ...


@mcp.tool()
async def api_param_fuzz(
    endpoint: str,
    method: str = "GET",
    params: dict | None = None,
) -> str:
    """Parameter fuzzing for injection vulnerabilities.

    Injects SQLi, CMDi, XSS, path traversal, and overflow
    payloads into each parameter and observes response diff.
    """
    # 1. Validate params (1-50 parameters)
    # 2. Detect content-type (JSON vs form-encoded)
    # 3. For each param: inject payloads, compare response
    # 4. Classify vulnerabilities based on response analysis
    # 5. Handle WAF blocking gracefully
    ...


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--transport", default="stdio",
                        choices=["stdio", "sse", "streamable-http"])
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()
    mcp.settings.host = args.host
    mcp.settings.port = args.port
    mcp.run(transport=args.transport)
```

## 附錄 B：Dockerfile 概要

```dockerfile
FROM athena-mcp-base:latest

# Install ffuf (Go static binary)
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget unzip && \
    rm -rf /var/lib/apt/lists/*

RUN wget -qO /tmp/ffuf.tar.gz \
    "https://github.com/ffuf/ffuf/releases/latest/download/ffuf_$(uname -s)_$(uname -m).tar.gz" && \
    tar -xzf /tmp/ffuf.tar.gz -C /usr/local/bin/ ffuf && \
    chmod +x /usr/local/bin/ffuf && \
    rm -f /tmp/ffuf.tar.gz

# API-specific wordlists
RUN mkdir -p /opt/wordlists && \
    wget -qO /opt/wordlists/api-common.txt \
      "https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/Web-Content/api/api-endpoints.txt" && \
    wget -qO /opt/wordlists/api-large.txt \
      "https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/Web-Content/api/api-endpoints-res.txt"

# Python dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir .

# Application code + payload files
COPY . .

CMD ["python", "-m", "server"]
```

## 附錄 C：docker-compose.yml 新增 Service

```yaml
mcp-api-fuzzer:
  build: { context: ./tools/api-fuzzer }
  profiles: [mcp]
  command: ["python", "-m", "server", "--transport", "streamable-http", "--port", "8080"]
  environment:
    - FUZZ_RATE_LIMIT=50
    - FUZZ_TIMEOUT_SEC=180
    - MAX_ENDPOINTS=500
  ports:
    - "127.0.0.1:58097:8080"
  restart: unless-stopped
```

## 附錄 D：mcp_servers.json 新增配置

```json
{
  "api-fuzzer": {
    "transport": "stdio",
    "command": "python",
    "args": ["-m", "server"],
    "env": {},
    "http_url": "http://mcp-api-fuzzer:8080/mcp",
    "enabled": true,
    "description": "API endpoint discovery, schema detection, and authentication bypass testing",
    "tool_prefix": "api"
  }
}
```

## 附錄 E：Fuzz Payload 範例

### `payloads/sqli.txt`
```
' OR 1=1--
' OR '1'='1
1' UNION SELECT null--
1' UNION SELECT null,null--
'; DROP TABLE users--
1 AND 1=1
1 AND 1=2
' AND SLEEP(5)--
1; WAITFOR DELAY '0:0:5'--
admin' --
```

### `payloads/cmdi.txt`
```
`id`
$(whoami)
; ls -la
| cat /etc/passwd
& ping -c 3 127.0.0.1
; sleep 5
$((7*7))
`sleep 5`
```

### `payloads/xss.txt`
```
<script>alert(1)</script>
"><img src=x onerror=alert(1)>
'><svg onload=alert(1)>
javascript:alert(1)
<img src="x" onerror="alert(1)">
{{7*7}}
${7*7}
```

### `payloads/traversal.txt`
```
../../../etc/passwd
....//....//....//etc/passwd
%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd
..%252f..%252f..%252fetc/passwd
/etc/passwd%00
....\/....\/....\/etc/passwd
```

### `payloads/overflow.txt`
```
99999999999999999
-1
0
2147483648
-2147483649
[]
{}
null
true
["__proto__"]
NaN
Infinity
```

## 附錄 F：schema_detector.py 模組概要

```python
"""OpenAPI / Swagger / GraphQL schema detection module."""

import httpx
import json
import yaml

# Common OpenAPI/Swagger paths to probe
_OPENAPI_PATHS = [
    "/openapi.json", "/openapi.yaml",
    "/swagger.json", "/swagger.yaml", "/swagger/",
    "/api-docs", "/api-docs.json",
    "/v1/openapi.json", "/v2/openapi.json", "/v3/openapi.json",
    "/api/v1/docs", "/api/v2/docs", "/api/v3/docs",
    "/docs", "/redoc",
    "/.well-known/openapi.json",
    "/api/swagger.json",
    "/api/docs",
]

# Common GraphQL paths
_GRAPHQL_PATHS = ["/graphql", "/graphiql", "/graphql/console", "/gql", "/api/graphql"]

_INTROSPECTION_QUERY = '{"query": "{ __schema { types { name } } }"}'


async def detect_openapi(base_url: str, timeout: float = 10.0) -> list[dict]:
    """Probe for OpenAPI/Swagger specs. Returns list of fact dicts."""
    ...

async def detect_graphql(base_url: str, timeout: float = 10.0) -> list[dict]:
    """Probe for GraphQL introspection endpoints. Returns list of fact dicts."""
    ...

def parse_openapi_spec(spec_data: dict) -> dict:
    """Extract endpoint count, version, title from OpenAPI spec."""
    ...
```

<!-- tech-debt: observability-pending — v3.3 upgrade: needs observability section -->
