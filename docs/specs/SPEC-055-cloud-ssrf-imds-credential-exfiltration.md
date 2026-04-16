# SPEC-055：Cloud SSRF-to-IMDS Credential Exfiltration Attack Path

> 結構完整的規格書讓 AI 零確認直接執行。

| 欄位 | 內容 |
|------|------|
| **規格 ID** | SPEC-055 |
| **關聯 ADR** | ADR-048（Accepted 2026-04-16） |
| **估算複雜度** | 中高 |
| **建議模型** | Opus（跨 MCP tool + Orient prompt engineering + engine_router routing + fact schema 四個模組聯動） |
| **HITL 等級** | minimal（沿用 `.ai_profile`） |

---

## 🎯 目標（Goal）

讓 Athena 能端到端執行 **cloud SSRF-to-IMDS credential exfiltration** 攻擊路徑：透過目標 web app 的 proxy endpoint 發送 HTTP request 到 AWS IMDS（`169.254.169.254`），自動偵測並提取 IAM credential，寫入 fact store。為 2026-05-07 資安社群大會的 flAWS.cloud Level 5 demo 提供「AI 指揮官從 SSRF 漏洞一路打到 AWS credential exfiltration」的可重現攻擊敘事。

**Phase 1 範圍限定**：tool 建立 + Orient 推薦 + credential auto-detect + fact 寫入。Phase 2 的 cloud lateral movement（用 credential 執行 `aws` CLI）明確延後。

---

## 🔌 前置條件（Infrastructure Prerequisite）

### MCP web-scanner container

`web_http_fetch` tool 新增於 `tools/web-scanner/server.py`，該 container 已有 `httpx` Python library（現有 `web_http_probe` 使用 httpx CLI binary，但 Python library 也在 image 中）。不需新增依賴。

### 網路可達性

flAWS.cloud Level 5 的 proxy endpoint 位於公網。MCP web-scanner container 必須能存取外部網路（現有 `docker-compose.yml` 的 `mcp-web-scanner` service 無 network 限制，已滿足）。

### 驗證 prerequisite 已滿足

```bash
# 從 mcp-web-scanner container 確認外部網路可達
docker exec athena-mcp-web-scanner-1 python3 -c "import httpx; print(httpx.get('https://httpbin.org/ip').status_code)"
# 預期：200
```

---

## 📥 輸入規格（Inputs）

### 1. `web_http_fetch` MCP tool（新增，`tools/web-scanner/server.py`）

| 參數名稱 | 型別 | 必填 | 限制條件 |
|----------|------|------|----------|
| `url` | `str` | 是 | 必須以 `http://` 或 `https://` 開頭；禁止 `file://`、`gopher://`、`ftp://` |
| `method` | `str` | 否（預設 `"GET"`） | 允許 `GET`、`POST`、`PUT`、`DELETE`、`HEAD`、`OPTIONS`、`PATCH` |
| `headers` | `dict[str, str] \| None` | 否 | 無 |
| `body` | `str \| None` | 否 | 僅在 `POST`/`PUT`/`PATCH` 時有效 |
| `follow_redirects` | `bool` | 否（預設 `True`） | 無 |

### 2. Orient prompt 新增 Rule #10 和 Rule #11

在 `_ORIENT_SYSTEM_PROMPT`（`backend/app/services/orient_engine.py`）Rule #9 之後新增。

**Rule #10: SSRF-to-IMDS Cloud Pivot**

觸發條件讀取自 Orient user prompt 的 Section 6（CATEGORIZED INTELLIGENCE）和 Section 7（ASSET STATUS）。

**Rule #11: Cloud Credential Lateral Movement**

觸發條件讀取自 `cloud.aws.iam_credential` fact 存在性。Phase 1 限制：只推薦，不執行。

### 3. engine_router web exploit routing

`backend/app/services/engine_router.py` 的 `_execute_single` 新增路由分支：當 engine == "mcp" 且 Orient 指定 MCP tool name 為 `web_http_fetch` 時，route 到 MCP web-scanner server。

此路由**不新增 technique prefix 常數**——SSRF exploitation 沿用 T1190，透過 engine="mcp"（而非 engine="metasploit"）區分路由。現有 `_execute_single` 的 MCP route（L339-343）已支援 engine=="mcp" dispatch，只需確保 Orient 推薦時帶 `engine="mcp"` 和 `mcp_tool_name="web_http_fetch"`。

### 4. fact schema 擴充

`backend/app/services/fact_collector.py` 的 `_category_from_trait` 新增 `cloud` prefix mapping。

---

## 📤 輸出規格（Expected Output）

### 1. `web_http_fetch` 成功回傳（一般 HTTP response）

```json
{
  "facts": [
    {
      "trait": "web.http.response",
      "value": "http://target/proxy/169.254.169.254/latest/meta-data/|200|text/plain|flaws\nflaws2..."
    }
  ],
  "raw_output": "<response body truncated to 4KB>"
}
```

### 2. `web_http_fetch` 成功回傳（IMDS credential auto-detected）

```json
{
  "facts": [
    {
      "trait": "web.http.response",
      "value": "http://target/proxy/169.254.169.254/.../flaws|200|application/json|{\"Code\":\"Success\"...}"
    },
    {
      "trait": "cloud.aws.iam_credential",
      "value": "flaws|ASIAIOSFODNN7EXAMPLE|2017-05-17T15:09:54Z"
    }
  ],
  "raw_output": "<full credential JSON truncated to 4KB>"
}
```

`cloud.aws.iam_credential` value 格式：`{role_name}|{AccessKeyId}|{Expiration}`。

**不存完整 SecretAccessKey 和 Token 到 fact value**——只存 key ID + 過期時間作為索引。完整 credential JSON 保留在 `raw_output` 中供後續 Phase 2 使用。

### 3. `web_http_fetch` 失敗回傳

| 錯誤類型 | 回傳 |
|----------|------|
| URL scheme 不允許 | `{"error": "Unsupported URL scheme: file://", "facts": []}` |
| HTTP 請求超時 | `{"error": "Request timeout after {N}s", "facts": [{"trait": "web.http.response", "value": "{url}\|timeout\|N/A\|"}]}` |
| 連線失敗 | `{"error": "Connection failed: {detail}", "facts": [{"trait": "web.http.response", "value": "{url}\|error\|N/A\|{detail}"}]}` |

### 4. Orient 推薦 SSRF-to-IMDS pivot 的 JSON 輸出

```json
{
  "situation_assessment": "Target has a proxy endpoint at /proxy/ (discovered via web_dir_enum). Cloud environment detected — IMDS at 169.254.169.254 is likely reachable via SSRF.",
  "recommended_technique_id": "T1190",
  "confidence": 0.85,
  "reasoning_text": "SSRF-to-IMDS pivot: use web_http_fetch via proxy endpoint to enumerate IAM roles from IMDS metadata service.",
  "options": [
    {
      "technique_id": "T1190",
      "engine": "mcp",
      "mcp_tool_name": "web_http_fetch",
      "target_id": "<target_id>",
      "parameters": {
        "url": "http://<target>/proxy/169.254.169.254/latest/meta-data/iam/security-credentials/"
      }
    }
  ]
}
```

### 5. fact_collector `_category_from_trait` 對 cloud trait 的 mapping

```python
# 輸入: "cloud.aws.iam_credential"
# 輸出: FactCategory.CREDENTIAL
```

---

## 🔄 Data Model 變更

**無 DB schema 變更。** 不需要 migration。

- `cloud.aws.iam_credential` 使用現有 `facts` 表的 `trait` / `value` 欄位
- `FactCategory.CREDENTIAL` 已存在，不需新增 enum 值
- `fact_collector._category_from_trait` 新增 `cloud` prefix → `FactCategory.CREDENTIAL` mapping（code change only）

---

## 🔗 副作用與連動（Side Effects）

| 副作用 | 觸發條件 | 影響模組 | 驗證方式 |
|--------|---------|---------|---------|
| `web.http.response` fact 寫入 | 每次 `web_http_fetch` 呼叫成功 | fact store、Orient context（Section 6） | T01：assert fact 存在 |
| `cloud.aws.iam_credential` fact 自動寫入 | response body 包含 IMDS credential pattern | fact store、Orient Rule #11 觸發 | T02：assert auto-detect 正確 |
| Orient prompt token 增加約 400 tokens | Rule #10 + #11 加入 system prompt | LLM API 成本 | 記錄 token usage 對比 |
| engine_router MCP dispatch 路由到 `web_http_fetch` | Orient 推薦 engine="mcp" + mcp_tool_name="web_http_fetch" | `engine_router._execute_mcp` 既有路徑 | T03：assert MCP tool 被正確呼叫 |
| `_category_from_trait` 回傳 `CREDENTIAL` for `cloud.*` | `cloud.aws.iam_credential` fact 被收集 | fact_collector、War Room Timeline 顯示分類 | B01：unit test |

---

## ⚠️ 邊界條件（Edge Cases）

1. **Response body 超過 4KB**：截斷至 4KB 寫入 `raw_output` 和 `web.http.response` fact 的 `body_snippet`；IMDS credential detection 在截斷前的完整 body 上執行（IMDS credential JSON 通常 < 1KB，不會被截斷影響）
2. **Non-JSON IMDS response**：某些 IMDS endpoint 回傳 plain text（如 role name list）。credential auto-detect 只在 response body 同時包含 `AccessKeyId` + `SecretAccessKey` + `Token` 三個 key 時觸發。plain text response 只產 `web.http.response` fact
3. **IMDSv2 reject**：IMDSv2 環境要求先 PUT 取 token 再 GET metadata。直接 GET 會被拒（HTTP 401 或 403）。Phase 1 不處理——`web_http_fetch` 會回傳 4xx status + 空 body，不觸發 credential auto-detect。列入 Phase 2
4. **Invalid credential format**：response body 包含 `AccessKeyId` 等 key 但 JSON parse 失敗（malformed JSON）。用 `try/except json.JSONDecodeError` 包住，失敗時只產 `web.http.response` fact + log warning
5. **Timeout**：`httpx.AsyncClient` timeout 複用 `SCAN_TIMEOUT_SEC`（預設 300s）。SSRF proxy 可能回應很慢。timeout 後回傳 error fact + 不觸發 credential detect
6. **Redirect loop**：`follow_redirects=True` 預設最多 30 次 redirect（httpx 預設）。超過後拋 `TooManyRedirects`，回傳 error
7. **URL scheme 攻擊**：`file:///etc/passwd` 等被 scope guard 擋下，回傳 error JSON
8. **Duplicate credential fact**：同一 operation 多次 fetch 同一 IMDS endpoint 會產生重複 `cloud.aws.iam_credential` fact。依賴現有 fact_collector 的 dedup 機制（trait + value 組合 unique per operation）
9. **`web_http_fetch` 被 Orient 濫用**：Orient 可能用此 tool 發大量無意義 request。依賴現有 OPSEC monitor noise budget + tool 層面的 `SCAN_RATE_LIMIT` 限制
10. **flAWS.cloud proxy endpoint 回傳 HTML 包裝**：某些 proxy 會把 IMDS response 包在 HTML 裡。credential auto-detect 在 response body 全文搜尋 pattern，不依賴 content-type header，所以 HTML 包裝不影響偵測

### 🔄 Rollback Plan

| 項目 | 說明 |
|------|------|
| **回滾步驟** | 1) `git revert` SPEC-055 對應 commits<br>2) `docker-compose build mcp-web-scanner && docker-compose up -d --force-recreate mcp-web-scanner`<br>3) `docker-compose build backend && docker-compose up -d --force-recreate backend` |
| **資料影響** | `cloud.aws.iam_credential` 和 `web.http.response` fact 已寫入 DB 的資料不受影響（orphan fact 不影響系統運行） |
| **回滾驗證** | 1) MCP tool registry 不再列出 `web_http_fetch`<br>2) Orient system prompt 不含 Rule #10 / #11<br>3) `_category_from_trait("cloud.aws.iam_credential")` 回傳 `HOST`（fallback）<br>4) SPEC-053/054 所有測試仍 pass |
| **回滾已測試** | ☐ 是：實作完成時以 `git stash` 循環驗證一次 |

---

## 🧪 測試矩陣（Test Matrix）

| # | 類型 | 輸入條件 | 預期結果 | 對應場景 |
|---|------|---------|---------|---------|
| P1 (T01) | ✅ 正向 | `web_http_fetch(url="http://example.com/page")` 回傳 200 + HTML body | `facts` 含 `web.http.response` trait，value 格式 `{url}\|200\|text/html\|{snippet}` | S1 |
| P2 (T02) | ✅ 正向 | `web_http_fetch(url="http://target/proxy/169.254.169.254/.../flaws")` 回傳 IMDS credential JSON | `facts` 含 `web.http.response` + `cloud.aws.iam_credential`，credential value 格式 `flaws\|ASIA...\|2017-...` | S2 |
| P3 (T03) | ✅ 正向 | Orient 看到 `web.dir.found` fact 含 `/proxy/` + cloud 環境線索 | Orient recommendation 含 `technique_id="T1190"` + `engine="mcp"` + `mcp_tool_name="web_http_fetch"` | S3 |
| P4 (T04) | ✅ 正向 | 端到端 flAWS Level 5 flow：recon → dir_enum → 兩次 `web_http_fetch`（role list → credential） | `cloud.aws.iam_credential` fact 存在於 fact store | S4 |
| N1 (T05) | ❌ 負向 | `web_http_fetch(url="file:///etc/passwd")` | 回傳 error JSON `"Unsupported URL scheme: file://"`，`facts` 為空 | 單元 |
| N2 (T06) | ❌ 負向 | `web_http_fetch` 請求超時 | 回傳 timeout error + `web.http.response` fact 帶 `timeout` status | 單元 |
| N3 (T07) | ❌ 負向 | IMDS response 是 HTTP 401（IMDSv2 reject） | `facts` 含 `web.http.response` 帶 status=401，**不**含 `cloud.aws.iam_credential` | 單元 |
| N4 (T08) | ❌ 負向 | Response body 含 `AccessKeyId` 但 JSON parse 失敗 | `facts` 含 `web.http.response`，**不**含 `cloud.aws.iam_credential`，log warning | 單元 |
| B1 (T09) | 🔶 邊界 | `_category_from_trait("cloud.aws.iam_credential")` | 回傳 `FactCategory.CREDENTIAL` | 單元 |
| B2 (T10) | 🔶 邊界 | `_category_from_trait("cloud.gcp.service_account")` | 回傳 `FactCategory.CREDENTIAL`（cloud prefix 通用） | 單元 |
| B3 (T11) | 🔶 邊界 | Response body 恰好 4KB | `raw_output` 不截斷，credential detect 正常運行 | 單元 |
| B4 (T12) | 🔶 邊界 | Response body > 4KB 且 credential 在前 1KB 內 | credential auto-detect 成功（在截斷前執行） | 單元 |

> P = Positive（正向：預期成功的路徑）
> N = Negative（負向：預期失敗/錯誤處理的路徑）
> B = Boundary（邊界：極值、trait mapping、截斷邊界）

---

## 🎭 驗收場景（Acceptance Scenarios）

```gherkin
Feature: SPEC-055 — Cloud SSRF-to-IMDS Credential Exfiltration
  作為 一位使用 Athena 的滲透測試指揮官（以及資安演講觀眾）
  我想要 AI 能透過 SSRF 漏洞自動取得 AWS IAM credential
  以便 展示 cloud 環境中從 web 漏洞到 credential exfiltration 的完整攻擊鏈

  Background:
    Given Athena OODA 正在 operation X 上執行
    And MCP web-scanner container 正常運行
    And target 是一個 cloud-hosted web application（如 flAWS.cloud Level 5）

  # --- 正向場景 ---

  Scenario: S1 - web_http_fetch basic functionality
    Given target URL "http://example.com/page" 回傳 200 OK with HTML body
    When web_http_fetch 被呼叫 with url="http://example.com/page"
    Then 回傳 JSON 包含 facts 陣列
    And facts 含一筆 trait="web.http.response"
    And value 格式為 "{url}|{status_code}|{content_type}|{body_snippet}"
    And raw_output 包含 response body（截斷至 4KB）

  Scenario: S2 - IMDS credential auto-detection
    Given target proxy endpoint 回傳 IMDS credential JSON:
      """
      {"Code":"Success","AccessKeyId":"ASIAEXAMPLE","SecretAccessKey":"wJalrXUtnFEMI...","Token":"token...","Expiration":"2017-05-17T15:09:54Z"}
      """
    When web_http_fetch 被呼叫 with url="http://target/proxy/169.254.169.254/latest/meta-data/iam/security-credentials/flaws"
    Then facts 含 trait="web.http.response" with status=200
    And facts 含 trait="cloud.aws.iam_credential" with value="flaws|ASIAEXAMPLE|2017-05-17T15:09:54Z"
    And cloud.aws.iam_credential fact 的 category 為 CREDENTIAL

  Scenario: S3 - Orient Rule #10 triggers SSRF-to-IMDS pivot
    Given target 有 web.dir.found fact 包含 "/proxy/" 路徑
    And target 有 web.http.response fact 顯示 proxy 可回傳外部內容（cloud 環境線索）
    And kill chain position 在 TA0001 或 TA0006
    When OODA 啟動下一輪 Orient iteration
    Then Orient recommendation 包含 technique_id="T1190"
    And engine="mcp"
    And parameters 包含 url 指向 "169.254.169.254" IMDS endpoint 經由 proxy
    And situation_assessment 提到 SSRF-to-IMDS pivot

  Scenario: S4 - End-to-end flAWS.cloud Level 5 attack chain
    Given target 是 flAWS.cloud Level 5 web application
    And nmap recon 已完成，port 80 開放
    And web_dir_enum 已發現 /proxy/ 路徑
    When Orient 推薦 web_http_fetch 經由 proxy 請求 IMDS role list
    And Act 執行 web_http_fetch(url="http://target/proxy/169.254.169.254/latest/meta-data/iam/security-credentials/")
    And response 回傳 role name（如 "flaws"）
    And Orient 推薦第二次 web_http_fetch 請求完整 credential
    And Act 執行 web_http_fetch(url="http://target/proxy/169.254.169.254/latest/meta-data/iam/security-credentials/flaws")
    Then cloud.aws.iam_credential fact 被自動偵測並寫入 fact store
    And War Room Timeline 顯示 cloud credential exfiltration 事件

  # --- 負向場景 ---

  Scenario: S5 - URL scheme guard blocks file:// protocol
    When web_http_fetch 被呼叫 with url="file:///etc/passwd"
    Then 回傳 error JSON 包含 "Unsupported URL scheme: file://"
    And facts 陣列為空
    And 不寫入任何 fact

  Scenario: S6 - IMDSv2 rejects direct GET request
    Given target 在 IMDSv2-only 環境
    When web_http_fetch 經由 proxy 請求 IMDS endpoint
    And IMDS 回傳 HTTP 401 Unauthorized
    Then facts 含 web.http.response with status=401
    And 不觸發 cloud.aws.iam_credential auto-detect
    And 不寫入 credential fact

  Scenario: S7 - Malformed JSON with credential-like keys
    Given response body 包含 "AccessKeyId" 和 "SecretAccessKey" 字串但 JSON 格式錯誤
    When web_http_fetch 處理此 response
    Then facts 含 web.http.response（正常記錄）
    And 不含 cloud.aws.iam_credential（JSON parse 失敗）
    And log 記錄 warning 含 "IMDS credential detection failed: JSON parse error"

  # --- 邊界場景 ---

  Scenario Outline: B - fact_collector cloud trait mapping
    When 呼叫 _category_from_trait("<trait>")
    Then 回傳 "<category>"

    Examples:
      | trait                          | category   |
      | cloud.aws.iam_credential       | credential |
      | cloud.gcp.service_account      | credential |
      | cloud.azure.managed_identity   | credential |
      | web.http.response              | web        |
```

> **場景撰寫規則**：
> - 每個場景有至少 1 個 `Then` 斷言
> - 每個場景有 `Given` 或 `Background` 前置條件
> - S4 是端到端 demo 場景，涉及多輪 OODA iteration

---

## ✅ 驗收標準（Done When）

**強驗收：**

- [ ] ADR-048 狀態 = Accepted
- [ ] `tools/web-scanner/server.py` 新增 `web_http_fetch` tool，MCP tool registry 可發現
- [ ] `web_http_fetch` scope guard：拒絕非 `http://` / `https://` scheme
- [ ] `web_http_fetch` response body 截斷至 4KB
- [ ] `web_http_fetch` IMDS credential auto-detect：response body 同時含 `AccessKeyId` + `SecretAccessKey` + `Token` 時自動產 `cloud.aws.iam_credential` fact
- [ ] `cloud.aws.iam_credential` fact value 格式：`{role}|{AccessKeyId}|{Expiration}`
- [ ] `backend/app/services/orient_engine.py` `_ORIENT_SYSTEM_PROMPT` 新增 Rule #10（SSRF-to-IMDS Cloud Pivot）和 Rule #11（Cloud Credential Lateral Movement）
- [ ] `backend/app/services/fact_collector.py` `_category_from_trait` 新增 `cloud` prefix → `FactCategory.CREDENTIAL` mapping
- [ ] engine_router 既有 MCP route 能正確 dispatch `web_http_fetch` tool（不需新增路由分支，驗證 engine="mcp" 路徑即可）
- [ ] `make test-filter FILTER=spec055` 全 green（至少 P1-P4 + N1-N4 + B1-B4 共 12 case）
- [ ] Gherkin S1-S7 + 邊界 Outline 通過自動驗證
- [ ] `make lint` 無 new error
- [ ] `make test`（full suite）無 SPEC-053/054 regression
- [ ] Rollback 循環驗證（`git stash` + `git stash pop`）
- [ ] 已更新 `docs/architecture.md`、`docs/SDS.md`、`docs/ROADMAP.md`、`docs/architecture/data-architecture.md`、`README.md`
- [ ] 已更新 `CHANGELOG.md`
- [ ] 文件同步通過 `make doc-audit`

**Deferred 驗收（等 Phase 2 實作後）：**

- [ ] Orient Rule #11 推薦的 cloud lateral movement 實際可執行（需 `cloud_aws_cli` MCP tool）
- [ ] IMDSv2 token-based flow 支援
- [ ] flAWS.cloud Level 5 live demo 端到端成功（演講前 dry run）

---

## 🔗 追溯性（Traceability）

<!-- 實作完成時回填 -->

| 實作檔案 | 測試檔案 | 最後驗證日期 |
|----------|----------|-------------|
| `tools/web-scanner/server.py`（`web_http_fetch` tool） | `backend/tests/test_spec055_web_http_fetch.py` | |
| `backend/app/services/orient_engine.py`（Rule #10, #11） | `backend/tests/test_spec055_orient_cloud_pivot.py` | |
| `backend/app/services/fact_collector.py`（cloud trait mapping） | `backend/tests/test_spec055_fact_collector.py` | |

---

## 📊 非功能需求（Non-Functional Requirements）

| 類別 | 需求 | 驗證方式 |
|------|------|----------|
| 效能 | `web_http_fetch` 單次 request 應在 `SCAN_TIMEOUT_SEC`（預設 300s）內完成 | Integration test with mock server |
| 效能 | Orient prompt token 增加 < 500 tokens/iteration（Rule #10 + #11） | 記錄 Anthropic SDK 回傳的 token usage，對比實作前後 |
| 安全 | `web_http_fetch` 禁止 `file://`、`gopher://` 等非 HTTP scheme | Scope guard unit test |
| 安全 | `cloud.aws.iam_credential` fact value 不含 SecretAccessKey 和 Token | Code review + fact value assertion |
| 安全 | Audit log 記錄每次 `web_http_fetch` 呼叫的 URL + response status | 現有 MCP tool audit logging 機制 |
| 相容性 | 不引入新的 Python dependency（httpx 已在 web-scanner image 中） | `requirements.txt` diff 為空 |
| 相容性 | 不影響現有 4 個 web-scanner tool 的行為 | `make test` full suite regression |

---

## 📊 可觀測性（Observability）

| 面向 | 說明 |
|------|------|
| **關鍵指標** | 1) `web_http_fetch` 呼叫次數和成功率（MCP tool audit log 統計）<br>2) `cloud.aws.iam_credential` fact 產出次數（`SELECT COUNT(*) FROM facts WHERE trait = 'cloud.aws.iam_credential'`）<br>3) Orient Rule #10 觸發次數（`ooda_iterations.orient_summary ILIKE '%SSRF%IMDS%'`）<br>4) IMDS credential auto-detect false positive 率（log warning 統計） |
| **日誌** | INFO: `web_http_fetch` 呼叫時記錄 URL + method + response status；credential auto-detect 觸發時記錄 role name + key ID prefix<br>WARN: IMDS credential detection JSON parse 失敗；`web_http_fetch` 超時；scheme 被拒絕<br>ERROR: httpx 連線失敗（exception detail） |
| **告警** | 若 `web_http_fetch` 連續 5 次超時 → 可能 target proxy 已下線或網路問題，人工審查 |
| **如何偵測故障** | 1) Orient 推薦 T1190 engine=mcp 但 MCP tool registry 無 `web_http_fetch` → tool 未正確註冊<br>2) Response body 含 IMDS pattern 但 `cloud.aws.iam_credential` fact 未產出 → auto-detect regex 或 JSON parse 異常<br>3) `_category_from_trait("cloud.aws.iam_credential")` 回傳 `HOST` 而非 `CREDENTIAL` → mapping 遺漏 |

---

## 🚫 禁止事項（Out of Scope）

**本 SPEC 範圍外，禁止在實作中順手加入：**

- 不實作 `cloud_aws_cli` MCP tool（Phase 2：用 exfiltrated credential 執行 `aws` CLI）
- 不處理 IMDSv2 token-based flow（Phase 2：需先 PUT 取 token 再 GET metadata）
- 不支援 Azure IMDS（`169.254.169.254` + `Metadata: true` header）或 GCP metadata（`metadata.google.internal`）
- 不新增 FactCategory enum 值（`cloud.aws.iam_credential` 歸入現有 `CREDENTIAL` category）
- 不修改 `constraint_engine.py`（cloud credential 的 noise budget 消耗由既有機制處理）
- 不修改 `attack_graph_engine.py`（attack graph 整合 cloud 路徑為後續工作）
- 不新增 HTTP endpoint（tool 透過 MCP protocol 暴露，不經 REST API）
- 不引入新 Python dependency（`httpx` 已存在、`json` / `re` 為 stdlib）
- 不修改 `docker-compose.yml`（web-scanner container 已有外部網路存取能力）
- 不修改現有 4 個 web-scanner tool（`web_http_probe`、`web_vuln_scan`、`web_dir_enum`、`web_screenshot`）
- 不實作 credential rotation detection（Phase 2）
- 不修改 Rule #1-#9 的核心邏輯（只在 Rule #9 之後新增 Rule #10 和 #11）

---

## 📎 參考資料（References）

- 相關 ADR：
  - **[ADR-048] Cloud SSRF-to-IMDS Credential Exfiltration Attack Path**（本 SPEC 的決策基礎）
  - [ADR-046] Orient-Driven Cross-Category Attack Pivot（Rule 擴充模式參考）
  - [ADR-047] Target-Segment Relay for Reverse-Shell Connectivity
  - [ADR-013] Orient Prompt Engineering Strategy
  - [ADR-020] Non-SSH Initial Access
- 相關 SPEC：
  - [SPEC-053] Orient-Driven Pivot and Metasploit One-Shot Exploit（Rule #8/#9 pattern 參考）
  - [SPEC-054] Relay Port-Forwarding Script Generator（Section 7.9 infrastructure pattern 參考）
- 現有實作：
  - `tools/web-scanner/server.py`：4 個現有 MCP tool（`web_http_probe`、`web_vuln_scan`、`web_dir_enum`、`web_screenshot`）
  - `backend/app/services/orient_engine.py`：`_ORIENT_SYSTEM_PROMPT` Rule #1-#9、`_ORIENT_USER_PROMPT_TEMPLATE` Section 7.9
  - `backend/app/services/engine_router.py`：`_execute_single` MCP route（L339-343）
  - `backend/app/services/fact_collector.py`：`_category_from_trait`（L170-179）
  - `backend/app/models/enums.py`：`FactCategory`（L84-94）
- 外部：
  - AWS IMDS documentation: https://docs.aws.amazon.com/IMDS/latest/UserGuide/
  - flAWS.cloud Level 5: http://level5-d2891f604d2061b6977c2481b0c8333e.flaws.cloud/
  - MITRE ATT&CK T1190 Exploit Public-Facing Application: https://attack.mitre.org/techniques/T1190/
  - MITRE ATT&CK T1552.005 Cloud Instance Metadata API: https://attack.mitre.org/techniques/T1552/005/
