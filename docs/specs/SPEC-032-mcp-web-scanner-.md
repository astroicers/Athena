# SPEC-032：mcp-web-scanner MCP Tool Server

> 結構完整的規格書讓 AI 零確認直接執行。

| 欄位 | 內容 |
|------|------|
| **規格 ID** | SPEC-032 |
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

建立 `mcp-web-scanner` MCP 工具伺服器（port 58096），封裝 **httpx-toolkit**（HTTP probe / tech fingerprinting / WAF detection）與 **Nuclei**（OWASP Top 10 vulnerability scanning），補齊 Athena OODA 循環在應用層（Web Layer）的偵察與漏洞掃描能力。

當 nmap 偵測到 HTTP/HTTPS 服務時，ReconEngine 自動觸發 `web_http_probe`，將結果作為 Facts 寫入資料庫，供 OrientEngine 進行 cross-fact reasoning 與應用層攻擊路徑推薦。此工具伺服器對 Red Team 操作員有直接價值——填補 Athena 從「網路層偵察」到「應用層深度探測」的能力缺口。

---

## 📥 輸入規格（Inputs）

### MCP Tool 1: `web_http_probe`

HTTP service probe + technology fingerprinting + WAF detection。

| 參數名稱 | 型別 | 來源 | 限制條件 |
|----------|------|------|----------|
| `target` | `str` | MCP tool call | 有效 IP、hostname 或 FQDN；必須通過 ScopeValidator |
| `ports` | `list[int]` | MCP tool call | 每個 port 範圍 1-65535；空 list 時使用預設 `[80, 443, 8080, 8443]`；最多 100 個 ports |

**內部實作：** 呼叫 `httpx -target <target> -ports <ports> -json -tech-detect -status-code -title -web-server -follow-redirects -silent`

### MCP Tool 2: `web_vuln_scan`

OWASP Top 10 vulnerability scanning via Nuclei templates。

| 參數名稱 | 型別 | 來源 | 限制條件 |
|----------|------|------|----------|
| `url` | `str` | MCP tool call | 完整 URL（含 scheme），如 `http://192.168.1.5:8080`；必須通過 ScopeValidator |
| `templates` | `list[str]` | MCP tool call | Nuclei template tags/IDs，預設 `["owasp-top-10"]`；空 list 時掃描所有 high+critical templates |
| `severity` | `str` | MCP tool call | `"critical"` / `"high"` / `"medium"` / `"low"` / `"info"`；預設 `"high"`（掃描該級別及以上） |

**內部實作：** 呼叫 `nuclei -u <url> -tags <templates> -severity <severity>,critical -json -silent -rate-limit <SCAN_RATE_LIMIT> -timeout <SCAN_TIMEOUT_SEC>`

### MCP Tool 3: `web_dir_enum`

Directory and file enumeration via httpx + wordlist。

| 參數名稱 | 型別 | 來源 | 限制條件 |
|----------|------|------|----------|
| `url` | `str` | MCP tool call | 基礎 URL（含 scheme），如 `http://192.168.1.5:8080`；必須通過 ScopeValidator |
| `wordlist` | `str` | MCP tool call | 內建 wordlist 名稱：`"common"` (預設, ~4,700 entries), `"small"` (~900), `"large"` (~220,000)；或容器內自訂絕對路徑 |
| `extensions` | `list[str]` | MCP tool call | 副檔名 list，如 `["php", "asp", "jsp", "html"]`；預設 `["php", "html", "js", "txt", "bak"]`；最多 20 個 |

**內部實作：** 使用 httpx 對 wordlist 中每個路徑 + extension 組合發送 HEAD/GET 請求，過濾 2xx/3xx/403 回應。

**Wordlist 路徑映射：**
- `"common"` -> `/opt/wordlists/common.txt`（SecLists Discovery/Web-Content/common.txt）
- `"small"` -> `/opt/wordlists/small.txt`（SecLists Discovery/Web-Content/directory-list-2.3-small.txt top 900）
- `"large"` -> `/opt/wordlists/large.txt`（SecLists Discovery/Web-Content/directory-list-2.3-medium.txt）

### MCP Tool 4: `web_screenshot`

Web page screenshot capture via httpx screenshot mode。

| 參數名稱 | 型別 | 來源 | 限制條件 |
|----------|------|------|----------|
| `url` | `str` | MCP tool call | 完整 URL（含 scheme）；必須通過 ScopeValidator |

**內部實作：** 呼叫 `httpx -u <url> -screenshot -system-chrome -silent` 或使用 Python headless screenshot fallback（Playwright 不含在 Phase 1，使用 httpx native screenshot）。若無 Chrome binary，fallback 至記錄 page title 的純文字 fact。

---

## 📤 輸出規格（Expected Output）

所有工具遵循 ADR-024 MCPFactExtractor Layer 1 結構化 JSON 格式：

```json
{"facts": [{"trait": "...", "value": "..."}], "raw_output": "..."}
```

### `web_http_probe` 成功回應：

```json
{
  "facts": [
    {
      "trait": "web.http.service",
      "value": "http://192.168.1.5:8080 [200] [Apache/2.4.6] [Welcome to DVWA]"
    },
    {
      "trait": "web.http.technology",
      "value": "PHP/7.2.10"
    },
    {
      "trait": "web.http.technology",
      "value": "Apache/2.4.6"
    },
    {
      "trait": "web.http.technology",
      "value": "jQuery/3.3.1"
    },
    {
      "trait": "web.http.waf",
      "value": "none"
    }
  ],
  "raw_output": "<truncated httpx JSON output, max 4000 chars>"
}
```

**Fact Trait 詳細說明：**

| Trait | 觸發條件 | Value 格式 |
|-------|----------|-----------|
| `web.http.service` | 每個可達的 HTTP 端點產生一筆 | `<url> [<status_code>] [<server>] [<title>]` |
| `web.http.technology` | httpx tech-detect 偵測到的每項技術 | `<tech_name>/<version>` 或 `<tech_name>` (無版本) |
| `web.http.waf` | 必定產生（即使無 WAF） | WAF 名稱（如 `Cloudflare`, `ModSecurity`）或 `none` |

### `web_vuln_scan` 成功回應：

```json
{
  "facts": [
    {
      "trait": "web.vuln.sqli",
      "value": "SQL Injection on http://192.168.1.5:8080/vulnerabilities/sqli/?id=1 (nuclei:sqli-error-based) severity=high confidence=confirmed"
    },
    {
      "trait": "web.vuln.xss",
      "value": "Reflected XSS on http://192.168.1.5:8080/vulnerabilities/xss_r/?name=test (nuclei:reflected-xss) severity=high confidence=confirmed"
    },
    {
      "trait": "web.vuln.ssrf",
      "value": "SSRF on http://192.168.1.5:8080/vulnerabilities/fi/?page=http://evil.com (nuclei:ssrf-detect) severity=critical confidence=confirmed"
    }
  ],
  "raw_output": "<truncated nuclei JSON output, max 4000 chars>"
}
```

**Trait 命名規則：** `web.vuln.<owasp_category>` 其中 category 映射如下：

| Nuclei tag/分類 | Athena Trait | OWASP 2021 對應 |
|-----------------|-------------|-----------------|
| `sqli`, `sql-injection` | `web.vuln.sqli` | A03:2021 Injection |
| `xss`, `cross-site-scripting` | `web.vuln.xss` | A03:2021 Injection |
| `ssrf` | `web.vuln.ssrf` | A10:2021 SSRF |
| `lfi`, `rfi`, `path-traversal` | `web.vuln.path_traversal` | A01:2021 Broken Access Control |
| `rce`, `command-injection` | `web.vuln.rce` | A03:2021 Injection |
| `auth-bypass`, `broken-auth` | `web.vuln.auth_bypass` | A07:2021 Auth Failures |
| `misconfig`, `misconfiguration` | `web.vuln.misconfig` | A05:2021 Security Misconfiguration |
| `exposure`, `sensitive-data` | `web.vuln.exposure` | A02:2021 Cryptographic Failures |
| `deserialization` | `web.vuln.deserialization` | A08:2021 Software & Data Integrity |
| 其他 | `web.vuln.generic` | -- |

### `web_dir_enum` 成功回應：

```json
{
  "facts": [
    {
      "trait": "web.dir.found",
      "value": "http://192.168.1.5:8080/admin/ [301] [text/html] [size=0]"
    },
    {
      "trait": "web.dir.found",
      "value": "http://192.168.1.5:8080/api/ [200] [application/json] [size=47]"
    },
    {
      "trait": "web.dir.sensitive",
      "value": "http://192.168.1.5:8080/.git/config [200] [text/plain] [size=283]"
    },
    {
      "trait": "web.dir.sensitive",
      "value": "http://192.168.1.5:8080/backup.sql.bak [200] [application/octet-stream] [size=1048576]"
    }
  ],
  "raw_output": "Enumerated 4713 paths, found 37 accessible (4 sensitive)"
}
```

**Sensitive 判定規則：** 路徑包含以下 pattern 時標記為 `web.dir.sensitive`：
- `.git/`, `.svn/`, `.hg/`, `.env`, `.htaccess`, `.htpasswd`, `.DS_Store`
- `backup`, `.bak`, `.sql`, `.dump`, `.tar`, `.zip`, `.gz`
- `wp-config.php`, `config.php`, `database.yml`, `settings.py`, `web.config`
- `phpinfo.php`, `server-status`, `server-info`, `elmah.axd`
- `robots.txt`（當 response body 包含 `Disallow` 敏感路徑時）

### `web_screenshot` 成功回應：

```json
{
  "facts": [
    {
      "trait": "web.screenshot",
      "value": "http://192.168.1.5:8080 title='Welcome to DVWA' screenshot_b64_length=124567"
    }
  ],
  "raw_output": "<base64 encoded PNG screenshot, max 500KB>"
}
```

### 失敗情境：

| 錯誤類型 | 回應格式 | 處理方式 |
|----------|----------|----------|
| Target unreachable / DNS failure | `{"facts": [], "raw_output": "CONNECTION_ERROR: <target>:<port> — <error_detail>"}` | 回傳空 facts + error 描述；不 raise exception |
| ScopeValidator violation | `{"facts": [], "raw_output": "SCOPE_VIOLATION: <target> is out of scope for this operation"}` | 不執行掃描，直接回傳 violation 訊息 |
| WAF blocking (429/403) | `{"facts": [{"trait": "web.http.waf", "value": "WAF detected — blocking requests (HTTP 429)"}], "raw_output": "..."}` | 記錄 WAF fact，降低 rate limit 至 25% 重試一次 |
| Scan timeout | `{"facts": [<partial_results>], "raw_output": "TIMEOUT: scan exceeded <N>s, partial results returned"}` | 回傳已收集的部分結果 |
| Nuclei template error | `{"facts": [], "raw_output": "TEMPLATE_ERROR: <nuclei stderr content>"}` | 記錄錯誤，回傳空 facts |
| Huge response body (>5MB) | 截斷 body 至 1MB，fact value 含 `body_truncated=true` | 防止 OOM |
| httpx/nuclei binary missing | `{"facts": [], "raw_output": "DEPENDENCY_ERROR: <binary> not found at expected path"}` | 不影響不依賴該 binary 的其他工具 |

---

## 🔗 副作用與連動（Side Effects）

| 本功能的狀態變動 | 受影響的既有功能 | 預期行為 |
|-----------------|----------------|---------|
| 新增 `web.http.*` / `web.vuln.*` / `web.dir.*` / `web.screenshot` facts 至 `facts` 表 | **OrientEngine** — 讀取 facts 進行 cross-fact reasoning | OrientEngine 接收 web facts 後，可推薦應用層攻擊手法（需後續 ADR-029 Phase 5 擴展 prompt） |
| ReconEngine 在 nmap 偵測到 HTTP service 後自動觸發 `web_http_probe` | **ReconEngine** — `recon_engine.py` 新增 Step 8b | Reconnaissance Chain 延伸：nmap -> web_http_probe -> facts 入庫。失敗時 graceful fallback，不影響 nmap 結果 |
| MCPClientManager 自動發現 4 個新工具，同步至 `tool_registry` | **Tool Registry UI** — `ToolRegistryTable.tsx` | 前端自動顯示 4 個新工具及其連線狀態；無需前端程式碼修改 |
| `mcp_servers.json` 新增 `web-scanner` 配置 | **MCPClientManager startup** | 啟動時自動連線 web-scanner，Circuit Breaker 保護啟用 |
| `docker-compose.yml` 新增 `mcp-web-scanner` service | **Docker 部署流程** | `docker compose --profile mcp up` 自動啟動 web-scanner 容器 |
| WebSocket 廣播 `fact.new` 事件（web.* traits） | **War Room 前端** — fact panel + topology | 即時顯示 Web 偵察結果；現有 `fact.new` handler 自動處理新 trait |

---

## ⚠️ 邊界條件（Edge Cases）

- **Case 1：Target unreachable / DNS resolution failure** — httpx 回傳 connection error，facts 為空 list，`raw_output` 包含 `CONNECTION_ERROR` 前綴與具體錯誤訊息。不 raise exception，允許 OODA 循環繼續其他偵察工作。

- **Case 2：WAF / CDN blocking requests (HTTP 429 / 403 / Captcha page)** — 偵測到 WAF 回應時：(1) 記錄 `web.http.waf` fact 含 WAF 名稱或 `"unknown"`，(2) 自動降低 rate limit 至原始 `SCAN_RATE_LIMIT` 的 25%，(3) 重試一次。若仍被攔截，回傳已收集的 facts 並在 `raw_output` 註明 WAF blocking。不嘗試 WAF bypass（超出本 SPEC 範圍）。

- **Case 3：Rate limiting 與 token bucket 耗盡** — 環境變數 `SCAN_RATE_LIMIT`（預設 100 rps）控制所有工具共享的 token bucket rate limiter。當 token 耗盡時，coroutine 執行 `asyncio.sleep()` 等待 token 補充。不會 raise exception 或丟失請求。

- **Case 4：Huge HTTP response body (>5MB)** — httpx 啟動參數設定 `--max-response-body-size 1048576`（1MB）。超過時 httpx 自動截斷 body。fact value 中加入 `body_truncated=true` 標記供下游參考。

- **Case 5：Self-signed / expired / invalid TLS certificate** — httpx 設定 `-no-verify` 跳過 TLS 驗證（滲透測試場景預設行為），在 `web.http.service` fact 的 value 中記錄 `tls_error=<error_type>`（如 `self_signed`, `expired`, `name_mismatch`）。

- **Case 6：Nuclei scan 無結果（clean target）** — 回傳空 facts list，`raw_output` 為 `"No vulnerabilities found for <url> with severity >= <severity>"`。非錯誤狀態，OODA 循環繼續。

- **Case 7：Nuclei template 不存在或損壞** — 捕獲 Nuclei stderr，回傳 `TEMPLATE_ERROR` 在 `raw_output`，facts 為空。不影響 `web_http_probe`、`web_dir_enum`、`web_screenshot` 的正常運作。

- **Case 8：並發掃描同一 target** — 允許並發。每次掃描產生獨立 fact records（DB UNIQUE index `(trait, value, operation_id, source_target_id)` 自動 dedup）。httpx 與 Nuclei 本身支援並發安全。Rate limiter 確保不會因為並發超出 rps 上限。

- **Case 9：極大量 dir_enum 結果 (>500 entries)** — 截斷 facts 至最多 500 筆。排序優先級：`web.dir.sensitive` 優先，其餘按 HTTP status code 排序（200 > 301 > 403）。`raw_output` 註明 `"truncated: <total_found> results, returning top 500 (sensitive paths prioritized)"`。

- **Case 10：MCP server 容器啟動但 Nuclei/httpx binary 不存在** — 每個工具在執行前檢查對應 binary 是否存在（`shutil.which("nuclei")`）。缺失時回傳 `DEPENDENCY_ERROR`，其他不依賴該 binary 的工具仍可正常運作。Server 啟動本身不會失敗。

- **Case 11：Target 回傳 redirect chain (>10 hops)** — httpx 設定 `--max-redirects 10`，超過時停止 follow，記錄最終 redirect URL 在 `web.http.service` fact 中。

- **Case 12：IPv6 target** — httpx 與 Nuclei 皆支援 IPv6。URL 格式使用 bracket notation `http://[::1]:8080`。MCP tool 參數接受 IPv6 literal。

- **Case 13：空 ports list 傳入 web_http_probe** — 使用預設 ports `[80, 443, 8080, 8443]`。不 raise exception。

- **Case 14：dir_enum wordlist 名稱無效** — 若 wordlist 參數非 `"common"` / `"small"` / `"large"` 且非有效檔案路徑，回傳 `{"facts": [], "raw_output": "INVALID_WORDLIST: <name> not found"}`。

### 回退方案（Rollback Plan）

- **回退方式**：revert commit + 移除 `docker-compose.yml` 中 `mcp-web-scanner` service + 移除 `mcp_servers.json` 中 `web-scanner` 配置 + revert `recon_engine.py` 的 auto-trigger 變更。三步驟均為 git revert 即可完成。
- **不可逆評估**：此變更無不可逆部分。新增的 `web.*` facts 會留在資料庫但不影響既有功能（OrientEngine 忽略無對應推理規則的 trait prefix）。若需清理，可執行 `DELETE FROM facts WHERE trait LIKE 'web.%'`。
- **資料影響**：回退後已寫入的 web facts 不會自動刪除，但不影響系統正常運作。`tool_registry` 中的 mcp_discovery 記錄會在 MCPClientManager 偵測到 server 不可用後自動 soft-delete。

---

## ✅ 驗收標準（Done When）

### 檔案建立

- [ ] `tools/web-scanner/server.py` — 4 個 MCP 工具（`web_http_probe`, `web_vuln_scan`, `web_dir_enum`, `web_screenshot`）實作完成
- [ ] `tools/web-scanner/Dockerfile` — 基於 `athena-mcp-base:latest`，安裝 httpx-toolkit + nuclei + nuclei-templates + SecLists wordlists
- [ ] `tools/web-scanner/pyproject.toml` — 包含 `mcp>=1.6.0` 依賴、project metadata
- [ ] `tools/web-scanner/__init__.py` — 空檔案（package marker）

### 檔案修改

- [ ] `mcp_servers.json` — 新增 `"web-scanner"` 配置項（transport: `"stdio"`, http_url: `"http://mcp-web-scanner:8080/mcp"`, tool_prefix: `"web"`, enabled: `true`）
- [ ] `docker-compose.yml` — 新增 `mcp-web-scanner` service（profile: `[mcp]`, ports: `127.0.0.1:58096:8080`, environment: `NUCLEI_TEMPLATES_DIR`, `SCAN_RATE_LIMIT`, `SCAN_TIMEOUT_SEC`）
- [ ] `backend/app/services/recon_engine.py` — 新增 Step 8b: 在 CVE enrichment 之後，檢查 HTTP services -> 自動觸發 `web_http_probe`（graceful fallback pattern，同 Step 8 CVE enrichment）

### 測試

- [ ] `backend/tests/test_mcp_web_scanner.py` — 單元測試覆蓋全部 4 個工具 + 邊界條件
  - [ ] `test_web_http_probe_success` — mock httpx subprocess output，驗證 facts 結構（trait, value 格式）
  - [ ] `test_web_http_probe_multiple_ports` — 多 port probe 產生多筆 `web.http.service` facts
  - [ ] `test_web_http_probe_unreachable` — target 不可達時回傳空 facts、CONNECTION_ERROR raw_output
  - [ ] `test_web_http_probe_waf_detected` — WAF 攔截時記錄 `web.http.waf` fact
  - [ ] `test_web_http_probe_default_ports` — 空 ports list 使用預設值
  - [ ] `test_web_vuln_scan_success` — mock nuclei JSONL output，驗證 vuln facts + trait 映射正確
  - [ ] `test_web_vuln_scan_no_results` — clean target 回傳空 facts
  - [ ] `test_web_vuln_scan_template_error` — template 錯誤時回傳 TEMPLATE_ERROR
  - [ ] `test_web_vuln_scan_timeout` — 掃描超時回傳 partial results
  - [ ] `test_web_vuln_scan_severity_filter` — severity 參數正確傳遞至 nuclei command
  - [ ] `test_web_dir_enum_success` — 發現目錄/檔案，驗證 `web.dir.found` facts
  - [ ] `test_web_dir_enum_sensitive_detection` — `.git/`, `.env`, `.bak` 等 sensitive path 正確標記為 `web.dir.sensitive`
  - [ ] `test_web_dir_enum_truncation` — >500 結果時截斷，sensitive 優先保留
  - [ ] `test_web_dir_enum_invalid_wordlist` — 無效 wordlist 名稱回傳 INVALID_WORDLIST
  - [ ] `test_web_screenshot_success` — 截圖成功回傳 base64 + page title fact
  - [ ] `test_web_screenshot_unreachable` — target 不可達處理
  - [ ] `test_scope_validation_blocks_out_of_scope` — ScopeValidator 阻擋 out-of-scope target
  - [ ] `test_rate_limiter_throttling` — rate limit 生效，超出時 sleep 而非 error
  - [ ] `test_dependency_missing_nuclei` — nuclei binary 不存在時回傳 DEPENDENCY_ERROR
  - [ ] `test_recon_engine_auto_trigger` — ReconEngine Step 8b: nmap 偵測到 HTTP service -> 自動觸發 web_http_probe

- [ ] `make test` 全數通過
- [ ] `make lint` 無 error

### Docker 建置

- [ ] `docker compose build mcp-web-scanner` 成功（exit code 0）
- [ ] `docker compose --profile mcp up mcp-web-scanner` 啟動正常（healthcheck 或 log 確認 MCP server ready）
- [ ] Container 內 `httpx -version` 回傳有效版本
- [ ] Container 內 `nuclei -version` 回傳有效版本
- [ ] Container 內 `ls /opt/nuclei-templates/` 確認 templates 目錄非空
- [ ] Container 內 `ls /opt/wordlists/common.txt` 確認 wordlist 存在
- [ ] Docker image size < 500MB（包含 nuclei-templates 和 wordlists）

### 整合驗證

- [ ] MCPClientManager 啟動時自動連線 web-scanner，`list_tools()` 回傳 4 個工具
- [ ] `tool_registry` DB 表新增 4 筆 `source='mcp_discovery'` 的工具記錄（web_http_probe, web_vuln_scan, web_dir_enum, web_screenshot）
- [ ] nmap 偵測到 port 80/443/8080 -> ReconEngine 自動觸發 `web_http_probe` -> web facts 入庫
- [ ] WebSocket 廣播 `fact.new` 事件包含 `web.http.*` traits
- [ ] Circuit Breaker 測試：停止 web-scanner 容器 -> MCPClientManager circuit OPEN -> 重啟容器 -> 自動 HALF_OPEN -> reconnect 成功 -> circuit CLOSED
- [ ] mock mode (`MOCK_C2_ENGINE=true`) 下 ReconEngine 不觸發 web_http_probe（僅 MCP 模式觸發）

### 效能

- [ ] `web_http_probe` 單一 target 4 ports 回應時間 < 15s
- [ ] `web_vuln_scan` 基礎 OWASP scan（high+critical templates）回應時間 < 120s
- [ ] `web_dir_enum` common wordlist (~4700 entries) 回應時間 < 60s
- [ ] `web_screenshot` 單一 URL 回應時間 < 30s

### 文件

- [ ] 已更新 `CHANGELOG.md`

---

## 🚫 禁止事項（Out of Scope）

- **不要** 引入 Playwright / Puppeteer / headless browser — 列為 ADR-029 長期目標
- **不要** 修改 OrientEngine system prompt — Rule 6 Application Layer Reasoning 擴展屬於 ADR-029 Phase 5，由獨立 SPEC 處理
- **不要** 修改 ScopeValidator 本體 — URL-based 擴展屬於 ADR-029 Phase 6。本 SPEC 使用現有 IP-based ScopeValidator 驗證 target host
- **不要** 修改 MCPFactExtractor — 本 SPEC 的工具直接回傳 Layer 1 結構化 JSON，現有 extractor 無需修改
- **不要** 在 Nuclei scan 中使用 `workflow` 模式 — 僅使用 tag-based 和 template-id-based scanning
- **不要** 新增任何 Python 依賴至 backend `pyproject.toml` — 所有新依賴封裝在 `tools/web-scanner/` 容器內
- **不要** 引入自訂 Nuclei templates — 僅使用 projectdiscovery/nuclei-templates 官方倉庫
- **不要** 實作 DOM-based XSS 偵測 — 需 headless browser 環境，超出本期範圍
- **不要** 實作 crawling / spidering 功能 — 未來可由 katana 整合處理，本 SPEC 僅掃描指定 URL
- **不要** 修改前端程式碼 — 現有 Tool Registry UI 和 War Room fact panel 已透過 WebSocket `fact.new` 事件和 `tool_registry` DB sync 自動適配

---

## 📎 參考資料（References）

- 相關 ADR：
  - [ADR-029：Application Layer Attack](/docs/adr/ADR-029--application-layer-attack.md) — 架構決策（選項 C 混合架構）與七階段實作計劃
  - [ADR-024：MCP Architecture](/docs/adr/ADR-024-mcp-architecture-and-tool-server-integration.md) — MCP 架構基礎、MCPClientManager、MCPFactExtractor 三層 fallback、Circuit Breaker 設計
- 現有類似實作：
  - `tools/nmap-scanner/server.py` — MCP 工具伺服器範本（FastMCP + `asyncio.create_subprocess_exec` pattern）
  - `tools/vuln-lookup/server.py` — 外部 API 呼叫 + rate limiting 範例（NVD token bucket）
  - `tools/nmap-scanner/Dockerfile` — 基於 `athena-mcp-base:latest` 的 Dockerfile 範本
  - `tools/_template/Dockerfile` — 通用 MCP 工具 Dockerfile 骨架
  - `backend/app/services/mcp_client_manager.py` — Circuit Breaker + periodic health check + tool registry sync
  - `backend/app/services/recon_engine.py` — Step 8 CVE enrichment graceful fallback pattern（auto-trigger 模板）
  - `backend/app/services/scope_validator.py` — IP/CIDR/hostname scope validation 實作
- 外部工具文件：
  - [httpx-toolkit](https://github.com/projectdiscovery/httpx) — HTTP probe + tech detection + screenshot + WAF detection
  - [Nuclei](https://github.com/projectdiscovery/nuclei) — Template-based vulnerability scanner（YAML DSL）
  - [Nuclei Templates](https://github.com/projectdiscovery/nuclei-templates) — 5,000+ community-maintained vulnerability templates
  - [SecLists](https://github.com/danielmiessler/SecLists) — Discovery/Web-Content wordlists for directory enumeration

---

## 附錄 A：`server.py` 架構概要

```python
"""web-scanner MCP Server for Athena.

Exposes HTTP probing, vulnerability scanning, directory enumeration,
and screenshot capture as MCP tools.
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

mcp = FastMCP("athena-web-scanner", transport_security=_security)

# Environment-based configuration
SCAN_RATE_LIMIT = int(os.environ.get("SCAN_RATE_LIMIT", "100"))
SCAN_TIMEOUT_SEC = int(os.environ.get("SCAN_TIMEOUT_SEC", "300"))
NUCLEI_TEMPLATES_DIR = os.environ.get("NUCLEI_TEMPLATES_DIR", "/opt/nuclei-templates")

_DEFAULT_PORTS = [80, 443, 8080, 8443]
_DEFAULT_EXTENSIONS = ["php", "html", "js", "txt", "bak"]

# Wordlist path mapping
_WORDLISTS = {
    "common": "/opt/wordlists/common.txt",
    "small": "/opt/wordlists/small.txt",
    "large": "/opt/wordlists/large.txt",
}

# Token bucket rate limiter (shared across all tools)
_rate_lock = asyncio.Lock()
_rate_tokens: list[float] = []

# Nuclei tag -> Athena trait mapping
_VULN_TRAIT_MAP = {
    "sqli": "web.vuln.sqli",
    "sql-injection": "web.vuln.sqli",
    "xss": "web.vuln.xss",
    "cross-site-scripting": "web.vuln.xss",
    "ssrf": "web.vuln.ssrf",
    "lfi": "web.vuln.path_traversal",
    "rfi": "web.vuln.path_traversal",
    "path-traversal": "web.vuln.path_traversal",
    "rce": "web.vuln.rce",
    "command-injection": "web.vuln.rce",
    "auth-bypass": "web.vuln.auth_bypass",
    "misconfig": "web.vuln.misconfig",
    "exposure": "web.vuln.exposure",
    "deserialization": "web.vuln.deserialization",
}

# Sensitive path patterns for dir_enum
_SENSITIVE_PATTERNS = [
    ".git/", ".svn/", ".hg/", ".env", ".htaccess", ".htpasswd",
    "backup", ".bak", ".sql", ".dump", ".tar", ".zip", ".gz",
    "wp-config.php", "config.php", "database.yml", "settings.py",
    "phpinfo.php", "server-status", "server-info", "web.config",
]


@mcp.tool()
async def web_http_probe(target: str, ports: list[int] | None = None) -> str:
    """HTTP service probe + tech fingerprinting + WAF detection.
    ...
    """

@mcp.tool()
async def web_vuln_scan(url: str, templates: list[str] | None = None, severity: str = "high") -> str:
    """OWASP Top 10 vulnerability scanning via Nuclei templates.
    ...
    """

@mcp.tool()
async def web_dir_enum(url: str, wordlist: str = "common", extensions: list[str] | None = None) -> str:
    """Directory and file enumeration.
    ...
    """

@mcp.tool()
async def web_screenshot(url: str) -> str:
    """Web page screenshot capture.
    ...
    """


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

# Install dependencies for downloading Go binaries
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget unzip && \
    rm -rf /var/lib/apt/lists/*

# httpx-toolkit (ProjectDiscovery)
RUN wget -qO /tmp/httpx.zip \
    "https://github.com/projectdiscovery/httpx/releases/latest/download/httpx_$(uname -s)_$(uname -m).zip" && \
    unzip /tmp/httpx.zip -d /usr/local/bin/ && \
    chmod +x /usr/local/bin/httpx && \
    rm -f /tmp/httpx.zip

# nuclei (ProjectDiscovery)
RUN wget -qO /tmp/nuclei.zip \
    "https://github.com/projectdiscovery/nuclei/releases/latest/download/nuclei_$(uname -s)_$(uname -m).zip" && \
    unzip /tmp/nuclei.zip -d /usr/local/bin/ && \
    chmod +x /usr/local/bin/nuclei && \
    rm -f /tmp/nuclei.zip

# nuclei templates (official repository)
RUN nuclei -update-templates -ud /opt/nuclei-templates

# SecLists wordlists for directory enumeration
RUN mkdir -p /opt/wordlists && \
    wget -qO /opt/wordlists/common.txt \
      "https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/Web-Content/common.txt" && \
    wget -qO /opt/wordlists/small.txt \
      "https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/Web-Content/directory-list-2.3-small.txt" && \
    wget -qO /opt/wordlists/large.txt \
      "https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/Web-Content/directory-list-2.3-medium.txt"

COPY pyproject.toml .
RUN pip install --no-cache-dir .

COPY . .

CMD ["python", "-m", "server"]
```

## 附錄 C：docker-compose.yml 新增 Service

```yaml
mcp-web-scanner:
  build: { context: ./tools/web-scanner }
  profiles: [mcp]
  command: ["python", "-m", "server", "--transport", "streamable-http", "--port", "8080"]
  environment:
    - NUCLEI_TEMPLATES_DIR=/opt/nuclei-templates
    - SCAN_RATE_LIMIT=100
    - SCAN_TIMEOUT_SEC=300
  ports:
    - "127.0.0.1:58096:8080"
  restart: unless-stopped
```

## 附錄 D：mcp_servers.json 新增配置

```json
{
  "web-scanner": {
    "transport": "stdio",
    "command": "python",
    "args": ["-m", "server"],
    "env": {},
    "http_url": "http://mcp-web-scanner:8080/mcp",
    "enabled": true,
    "description": "Web vulnerability scanning (httpx + Nuclei) and HTTP reconnaissance",
    "tool_prefix": "web"
  }
}
```

## 附錄 E：ReconEngine 自動觸發邏輯

在 `backend/app/services/recon_engine.py` 的 `scan()` 方法中，Step 8（CVE enrichment）之後新增 Step 8b：

```python
# ------------------------------------------------------------------
# Step 8b: Web reconnaissance (graceful fallback — never breaks recon)
# ------------------------------------------------------------------
http_services = [
    s for s in services
    if s.service in ("http", "https", "http-proxy", "http-alt")
]
if http_services and settings.MCP_ENABLED:
    try:
        from app.services.mcp_client_manager import get_mcp_manager
        manager = get_mcp_manager()
        if manager and manager.is_connected("web-scanner"):
            http_ports = [s.port for s in http_services]
            probe_result = await manager.call_tool(
                "web-scanner", "web_http_probe",
                {"target": ip_address, "ports": http_ports}
            )
            # Parse probe result and write web facts
            await self._write_web_facts(
                db=db,
                operation_id=operation_id,
                target_id=target_id,
                probe_result=probe_result,
            )
    except Exception:
        logger.warning(
            "Web reconnaissance failed for %s, continuing without web data",
            ip_address,
        )
```

新增 helper method `_write_web_facts()` 遵循與 `_write_facts()` 相同的 pattern — parse MCP JSON response、寫入 facts 表、broadcast WebSocket event。

<!-- tech-debt: scenario-pending — v3.2 upgrade: needs test matrix + Gherkin scenarios -->
<!-- tech-debt: observability-pending — v3.3 upgrade: needs observability section -->
