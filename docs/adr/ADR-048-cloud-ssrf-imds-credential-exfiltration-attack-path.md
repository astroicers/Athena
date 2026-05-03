# [ADR-048]: Cloud SSRF-to-IMDS Credential Exfiltration Attack Path

| 欄位 | 內容 |
|------|------|
| **狀態** | `Accepted` |
| **日期** | 2026-04-16 |
| **決策者** | Athena Core Team |

---

## 背景（Context）

Athena 的攻擊路徑目前完全限於 service-level exploit（Samba/VSFTPD/SSH brute force），**沒有任何 web application 攻擊能力**。要打 AWS-backed service（如 flAWS.cloud Level 5 的 SSRF → IMDS metadata → credential exfiltration），現有工具鏈缺少三個關鍵環節。

### 三個具體限制

**1. MCP web-scanner 沒有 HTTP response body 回傳能力**

`tools/web-scanner/server.py` 提供 4 個 tool：

- `web_http_probe`（L130-209）：httpx probe，回傳 `web.http.service` / `web.http.technology` / `web.http.waf` fact，但**不回傳 response body**
- `web_vuln_scan`（L217-296）：Nuclei 掃描，回傳 `web.vuln.*` fact，但只有 template match metadata
- `web_dir_enum`（L303-431）：目錄枚舉，回傳 `web.dir.found` / `web.dir.sensitive` fact
- `web_screenshot`（L438-535）：截圖 / 取 title

這 4 個 tool 都是偵察型工具（fingerprint + enumerate），沒有一個能讓 Orient agent **發送任意 HTTP request 並讀取 response body**。SSRF 攻擊的核心操作是：透過目標 web app 的 proxy endpoint 請求 `http://169.254.169.254/latest/meta-data/iam/security-credentials/<role>`，然後**從 response body 解析 AWS credential**。現有 tool 無法完成這個操作。

**2. Orient prompt 沒有 cloud/SSRF 相關規則**

`backend/app/services/orient_engine.py` 的 `_ORIENT_SYSTEM_PROMPT`（L157-305）定義了 9 條分析規則：

- Rule #1: Kill Chain Reasoning
- Rule #2: Dead Branch Pruning
- Rule #3: Prerequisite Verification
- Rule #4: Engine Routing
- Rule #5: Risk Calibration
- Rule #6: No Redundant Recommendations
- Rule #7: Attack Graph Awareness
- Rule #8: Recon-to-Initial Access Transition（L209-263）
- Rule #9: Initial Access Exhausted → Exploit Pivot（L245-275）

Rule #8 和 #9 都只處理 service-level exploit pivot（SSH/FTP/Samba → Metasploit）。沒有任何規則指導 LLM：

- 偵測 web app SSRF 漏洞後應該嘗試 IMDS metadata fetch
- 從 IMDS response 中識別 AWS IAM credential pattern
- 拿到 credential 後應該做 cloud lateral movement

**3. engine_router 沒有 web exploit / cloud lateral routing**

`backend/app/services/engine_router.py` 的路由邏輯（L299-407 `_execute_single`）：

- `_RECON_TECHNIQUE_PREFIXES`（L65-72）：T1595, T1590, T1592, T1046, T1018, T1135
- `_INITIAL_ACCESS_TECHNIQUE_PREFIXES`（L75-78）：T1110, T1078
- Metasploit route（L351-366）：T1190 or engine="metasploit"
- MCP route（L339-343）：engine == "mcp"

沒有 web exploit 路由（SSRF exploitation 不是 Metasploit module、也不是 SSH execution），也沒有 cloud lateral movement 路由（拿到 AWS credential 後做 `aws sts get-caller-identity` / `aws s3 ls` 等操作）。

**4. fact schema 沒有 cloud credential trait**

`backend/app/models/enums.py:84-94` 的 `FactCategory` 有 `CREDENTIAL`、`HOST`、`NETWORK`、`SERVICE`、`VULNERABILITY`、`WEB` 等，但 fact trait namespace 中沒有 `cloud.aws.iam_credential` 這類 cloud-specific trait。`backend/app/services/fact_collector.py:158-179` 的 `_infer_category` 和 `_category_from_trait` 也沒有 cloud 類別的 inference 邏輯。

### Demo 需求

3 週後（2026-05-07）在資安社群大會的 demo target 是 flAWS.cloud Level 5：

1. Athena 偵測到目標 web app 有 proxy endpoint（SSRF 漏洞）
2. Orient 識別出 SSRF → IMDS pivot 機會
3. 透過 proxy endpoint fetch `http://169.254.169.254/latest/meta-data/iam/security-credentials/`
4. 從 response body 自動偵測並提取 AWS IAM credential（AccessKeyId / SecretAccessKey / Token）
5. Credential 寫入 fact store，War Room Timeline 顯示 cloud pivot

---

## 決策（Decision）

新增 cloud SSRF-to-IMDS credential exfiltration 攻擊路徑，分兩個 Phase 實作。

### Phase 1（本 ADR 範圍，demo 前完成）

**1. mcp-web-scanner 新增 `web_http_fetch` tool**

在 `tools/web-scanner/server.py` 新增第 5 個 MCP tool：

```python
@mcp.tool()
async def web_http_fetch(
    url: str,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    body: str | None = None,
    follow_redirects: bool = True,
) -> str:
    """Fetch an HTTP URL and return the response body with metadata.

    Returns JSON with:
    - web.http.response: "{url}|{status_code}|{content_type}|{body_snippet}"
    - cloud.aws.iam_credential (auto-detected if response contains IMDS pattern)
    """
```

關鍵設計點：

- 用 Python `httpx` library 直接發 HTTP request（不依賴 httpx CLI binary）
- Response body 截斷至 4KB 寫入 `raw_output`，完整 body hash 記錄 audit
- **自動偵測 IMDS credential pattern**：掃描 response body 是否包含 `AccessKeyId` + `SecretAccessKey`，若是則自動產出 `cloud.aws.iam_credential` fact
- Rate limit 與 timeout 複用現有 `SCAN_RATE_LIMIT` / `SCAN_TIMEOUT_SEC` 設定
- Scope guard：只允許 `http://` 和 `https://` scheme，禁止 `file://` / `gopher://`

**2. Orient prompt 新增 Rule #10 和 Rule #11**

在 `backend/app/services/orient_engine.py` 的 `_ORIENT_SYSTEM_PROMPT` 新增：

**Rule #10: SSRF-to-IMDS Cloud Pivot**

觸發條件：
- `web.vuln.ssrf` fact 存在，或 `web.http.response` fact 顯示目標有 proxy/redirect 功能
- 目標在 cloud 環境（可從 IP range 169.254.169.254 可達性推斷）
- Kill chain position 在 Initial Access (TA0001) 或 Credential Access (TA0006)

行為：
- MUST 推薦使用 `web_http_fetch` tool 請求 `http://169.254.169.254/latest/meta-data/iam/security-credentials/` 經由目標 proxy endpoint
- engine 設為 "mcp"
- 若已取得 role name，第二步請求完整 credential JSON

**Rule #11: Cloud Credential Lateral Movement**

觸發條件：
- `cloud.aws.iam_credential` fact 存在
- Kill chain position 在 Credential Access (TA0006) 或之後

行為：
- 推薦 cloud lateral movement：T1078.004 (Cloud Accounts) 或 T1530 (Data from Cloud Storage)
- Phase 1 限制：Orient 只做推薦，實際 cloud CLI 執行標為 Phase 2

**3. engine_router 新增 web exploit routing**

在 `backend/app/services/engine_router.py` 的 `_execute_single`（L299）新增路由分支：

- 新增 `_WEB_EXPLOIT_TECHNIQUE_PREFIXES`：包含 SSRF 相關 technique（T1190 子類別，透過 Orient 推薦時帶 engine="mcp" 區分）
- 當 engine == "mcp" 且 technique 為 web exploit 類型時，route 到 MCP web-scanner 的 `web_http_fetch` tool
- 保留現有 T1190 → Metasploit 路由不變（透過 engine 欄位區分：engine="metasploit" 走 Metasploit，engine="mcp" 走 web-scanner）

**4. fact schema 新增 cloud credential trait**

- 在 `fact_collector.py` 的 `_category_from_trait` 新增 `cloud` prefix → `FactCategory.CREDENTIAL` mapping
- 新增 trait type `cloud.aws.iam_credential`，value 格式：`{role_name}|{access_key_id}|{expiration}`（不存完整 secret，只存 key ID + 過期時間作為索引，完整 credential 存 encrypted fact store）
- `FactCategory` enum 不需要新增值 — cloud credential 歸入現有 `CREDENTIAL` category

### Phase 2（明確延後）

| 功能 | 觸發條件 |
|------|----------|
| `cloud_aws_cli` MCP tool — 用 exfiltrated credential 執行 `aws` CLI 做 lateral move | Phase 1 demo 成功 + 使用者要求擴充 cloud 攻擊面 |
| Azure / GCP IMDS support（endpoint 不同：Azure 用 header，GCP 用 `metadata.google.internal`） | 有 Azure/GCP target 的演講需求 |
| IMDS v2 (IMDSv2) token-based flow（需先 PUT 取 token 再 GET metadata） | 遇到 IMDSv2-only 環境 |
| Credential rotation detection — 偵測 exfiltrated credential 過期並觸發重新 fetch | 長時間操作需求 |
| Nuclei SSRF template 自動觸發 `web_http_fetch` chain | web-scanner tool 整合度提升需求 |

---

## 替代方案（Alternatives Considered）

### 替代 A：用 Playwright/headless browser 抓頁面

透過 Playwright MCP server（已在 Athena tool registry 中）navigate 到 proxy URL，讀取頁面 DOM 內容。

- **優點**：不需要新增 MCP tool，複用現有 Playwright infra
- **缺點**：
  - Playwright 設計用來做 browser interaction，不是做 HTTP raw fetch — 處理 JSON/plain-text response 需要 `page.evaluate` hack
  - 啟動 browser context 慢（2-5s），SSRF fetch 只需要 <100ms 的 HTTP call
  - Browser sandbox 可能攔截 169.254.169.254 的 request（CORS / mixed content 限制）
  - Response body 的 credential pattern detection 需要在 browser context 裡做 JS 評估，增加 fragility
- **結論**：over-engineered for a simple HTTP fetch + pattern match 需求

### 替代 B：用 curl subprocess 而非 MCP tool

在 `engine_router` 裡直接 `asyncio.create_subprocess_exec("curl", ...)` 發 request。

- **優點**：零新增 tool，實作成本最低（約 20 行）
- **缺點**：
  - 繞過 MCP tool registry，Orient 看不到這個能力（Section 7.8 MCP Tools 不會列出 curl）
  - 沒有 fact auto-extraction — curl output 是 raw text，需要在 engine_router 裡 hardcode IMDS pattern matching
  - 違反 Athena 的 tool composition 架構：所有攻擊能力應該是可發現、可推薦、可審計的 MCP tool
  - Demo 敘事受損：Timeline 不會顯示「使用 web_http_fetch tool」，而是隱藏在 engine 內部
- **結論**：能用但違反架構原則，且 demo 不好看

### 替代 C：擴充 `web_http_probe` 回傳 body（修改現有 tool）

在現有 `web_http_probe` tool 加一個 `include_body: bool` 參數。

- **優點**：不增加 tool 數量，API surface 最小
- **缺點**：
  - `web_http_probe` 的設計意圖是 fingerprint（用 httpx CLI 批次掃描），不是 single-URL fetch
  - httpx CLI 的 `-json` output 不包含 response body（by design，避免 output 膨脹）
  - 強行加 body 需要切換到 httpx Python library 或 fallback 到 curl，把兩種用途塞在一個 tool 裡
  - Tool 語義污染：`web_http_probe` 原本是 recon tool，加上 body fetch 後變成 hybrid
- **結論**：語義不對，應該是獨立 tool

---

## 後果（Consequences）

### 正面

- Athena 獲得 web application 攻擊能力的基礎 — `web_http_fetch` 是通用 HTTP 交互 tool，不只限於 SSRF
- Demo 路徑完整：flAWS.cloud Level 5 可以端到端走通（偵測 SSRF → fetch IMDS → 提取 credential → Timeline 顯示 cloud pivot）
- Orient 的攻擊推薦從 network-service-only 擴展到 web+cloud 領域，Rule #10/#11 為未來 web exploit chain 提供模板
- `cloud.aws.iam_credential` trait 為 cloud 攻擊面建立 fact schema foundation
- IMDS credential auto-detection 在 `web_http_fetch` tool 層做（而不是 Orient prompt 裡做），確保 credential 不會被遺漏

### 負面

- `web_http_fetch` 是功能強大的 tool — 能發任意 HTTP request，需要 scope guard 確保不被濫用（禁 `file://`、限 rate、audit logging）
- Orient prompt 再增加約 400 tokens（Rule #10 + #11），token 成本持續增加
- engine_router 的路由分支再增加一個 web exploit 路徑，複雜度微增
- Phase 1 只做到「取得 credential + 寫 fact」，lateral movement 的完整 demo 需要 Phase 2 的 `cloud_aws_cli` tool

### 風險

| 風險 | 嚴重度 | 緩解 |
|------|--------|------|
| `web_http_fetch` 被 Orient 用來發大量無意義 HTTP request（noise budget 消耗） | Medium | 複用現有 OPSEC monitor 的 noise budget 機制 + Rate limit 在 tool 層面執行 |
| IMDS credential auto-detection 的 regex 產生 false positive | Low | Pattern 要求同時出現 `AccessKeyId` + `SecretAccessKey` + `Token`，三者同時 false positive 機率極低 |
| flAWS.cloud Level 5 的 proxy endpoint 行為變更導致 demo 失敗 | Medium | 演講前一天做 dry run 驗證；準備 local mock 作為備案 |
| IMDSv2 環境下 GET 直接 request 被拒絕（需要先 PUT 取 token） | Low（Phase 1 不處理） | flAWS.cloud 用 IMDSv1；IMDSv2 support 列在 Phase 2 |

---

## 關聯（Relations）

- **取代**：（無）
- **被取代**：（無）
- **參考**：
  - [ADR-046] Orient-Driven Cross-Category Attack Pivot（本 ADR 繼承 Rule 擴充模式）
  - [ADR-047] Target-Segment Relay for Reverse-Shell Connectivity（infrastructure awareness pattern）
  - [ADR-013] Orient Prompt Engineering Strategy
  - [ADR-020] Non-SSH Initial Access
  - [SPEC-053] Orient-Driven Pivot and Metasploit One-Shot Exploit
  - [SPEC-054] Relay-Aware Exploit Selection
  - [SPEC-055] Cloud SSRF-to-IMDS Credential Exfiltration
  - [SPEC-064] Orient Engine 14 條規則規格（Rule #10 SSRF-to-IMDS Cloud Pivot、Rule #11 Cloud Credential Lateral Movement 完整說明）

---

## 實作完成紀錄

| 日期 | 項目 |
|------|------|
| 2026-04-17 | Phase 1 完成：`web_http_fetch` + `web_ssrf_probe` MCP tools, Orient Rule #10/#11, engine_router web exploit routing, fact schema `cloud.aws.*` |
| 2026-04-17 | E2E 驗證通過：flAWS.cloud Level 5 自動 SSRF → IMDS → credential exfiltration (`cloud.aws.iam_credential` fact 成功寫入) |
| 2026-04-17 | Code review: 統一 NOISE_POINTS 常量、IAM role name 格式驗證、decision engine threshold bypass 修正 |
