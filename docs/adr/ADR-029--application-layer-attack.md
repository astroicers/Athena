# [ADR-029]: 應用層攻擊能力擴展 (Application Layer Attack)

| 欄位 | 內容 |
|------|------|
| **狀態** | `Accepted` |
| **日期** | 2026-03-06 |
| **決策者** | Athena Core Team |

---

## 背景（Context）

Athena 作為 C5ISR 級別的網路作戰指揮平台，其 OODA 循環目前僅覆蓋 **網路層（Network Layer）** 的攻擊能力。現有 5 個 MCP 工具伺服器（nmap-scanner、osint-recon、vuln-lookup、credential-checker、attack-executor）的能力範圍如下：

| 現有能力 | MCP 伺服器 | 對應 ATT&CK |
|----------|-----------|-------------|
| Port scanning + Service detection | nmap-scanner | TA0043 Reconnaissance |
| OSINT（Subdomain enumeration、Certificate Transparency） | osint-recon | TA0043 Reconnaissance |
| CVE lookup（NVD API + CPE mapping） | vuln-lookup | TA0043 Reconnaissance |
| Credential brute-force（SSH、RDP、WinRM） | credential-checker | TA0006 Credential Access |
| Post-compromise technique execution | attack-executor | TA0002 Execution |

**核心問題：應用層攻擊能力完全空白。** 當 nmap 偵測到 HTTP/HTTPS 服務（port 80/443/8080）時，ReconEngine 僅記錄 `service.open_port: 80/tcp/http/Apache_2.4.6` 這一事實，OrientEngine 無法推薦任何 Web/API 層面的攻擊手法，OODA 循環在此處斷裂。

具體缺失的能力包括：

1. **Web Application Scanning**：無法偵測 OWASP Top 10 漏洞（SQLi、XSS、SSRF、Path Traversal、RCE 等）
2. **API Endpoint Discovery**：無法探測 OpenAPI/Swagger、GraphQL introspection、hidden API routes
3. **Authentication/Authorization Testing**：無法測試 BOLA/IDOR、JWT manipulation、OAuth misconfiguration
4. **Business Logic Vulnerability Detection**：無法辨識 rate limiting 缺失、privilege escalation、insecure direct object reference 等邏輯漏洞
5. **Web Fingerprinting**：無法識別 WAF、CDN、Web framework、CMS 版本等應用層指紋

### 業界參考

**Escape.tech** 的 API Security 平台提供了重要啟發：

- **FDSAE（Feedback-Driven Semantic API Exploration）**：不依賴 OpenAPI spec，透過語意分析自動發現 API 端點並理解其行為
- **MetaGraph**：建構 API 關係圖，識別資料流依賴（例如：建立訂單需先取得 auth token → 查詢 user profile → 建立 cart）
- **140+ Attack Scenarios**：涵蓋 REST、GraphQL、gRPC 的專用攻擊向量
- **Business Logic Testing**：透過多步驟交易序列偵測邏輯漏洞

**XBOW** 的 Headless Browser Integration 提供了另一個維度：

- 深度 Web Application Testing 需要 JavaScript rendering
- SPA（Single Page Application）的動態內容無法透過純 HTTP request 探測
- DOM-based XSS 等漏洞需要瀏覽器環境才能驗證

### 與現有架構的關係

根據 ADR-024 確立的 MCP 架構，新增應用層能力應遵循：

- 獨立容器化 MCP 工具伺服器（繼承 `athena-mcp-base:latest`）
- MCPFactExtractor 三層 fallback 擷取結果
- Circuit Breaker 容錯模式
- OrientEngine 自動路由 MCP 工具至 OODA 循環
- `mcp_servers.json` 靜態配置註冊

---

## 評估選項（Options Considered）

### 選項 A：整合現有開源工具 via MCP（Integrate Existing OSS Tools）

新建 MCP 工具伺服器，直接封裝業界成熟的開源工具：

- **Nuclei**（ProjectDiscovery）：YAML template-based vulnerability scanner，5,000+ community templates
- **ffuf**（joohoi）：高效能 HTTP fuzzer，支援 directory/parameter/vhost fuzzing
- **httpx**（ProjectDiscovery）：HTTP probe + tech fingerprinting + status code enumeration
- **katana**（ProjectDiscovery）：Web crawler，支援 JavaScript rendering 的 URL 發現
- **dalfox**（hahwul）：XSS scanner，支援 DOM/Reflected/Stored XSS 偵測

**優點：**
- 工具成熟穩定，社群持續維護 signature/template
- 部署快速，每個工具封裝為獨立 MCP server 即可
- Nuclei 的 template ecosystem 涵蓋大量已知漏洞 pattern
- 各工具的 CLI output 已有標準化格式（JSON mode）

**缺點：**
- 每個工具的 output schema 不同，需要逐一撰寫 parser 映射到 Athena Facts
- 工具間缺乏協調：ffuf 發現的路徑無法自動餵給 Nuclei 做深度掃描
- 無法偵測 business logic 漏洞（純 signature-based）
- MCP 工具伺服器數量暴增（現有 5 個 + 新增 4-5 個 = 9-10 個），管理複雜度上升

**風險：**
- 工具版本管理與 CVE（Nuclei template 需頻繁更新）
- 容器化後的系統資源消耗（Nuclei 掃描時 CPU/memory 峰值高）
- 部分工具（如 katana headless mode）需要 Chromium，Docker image 體積膨脹

### 選項 B：自建 Web 掃描引擎（Custom Web Scanner Engine）

受 Escape.tech FDSAE 啟發，從零建構 Athena 原生的 Web/API 掃描引擎：

- 自建 HTTP client + request mutator
- 實作 FDSAE-like API exploration algorithm
- 建構 MetaGraph-like API relationship model
- 原生整合 Athena Facts / OODA 循環

**優點：**
- 完全掌控掃描行為、精細調整偵測策略
- 與 Athena Facts 表和 OrientEngine 深度整合，無需格式轉換
- 可實作 Escape.tech 風格的 business logic testing
- 單一服務架構，無需管理多個外部工具版本

**缺點：**
- 開發工作量巨大：Escape.tech 歷經數年建構其 FDSAE 引擎
- 需要自行維護漏洞 signature database（相當於重建 Nuclei template 生態系）
- 初期漏洞偵測覆蓋率遠低於 Nuclei 5,000+ templates
- 單一團隊難以匹敵 ProjectDiscovery 社群的更新速度

**風險：**
- 高 — 預估需要 6-12 個月開發週期才能達到基本可用
- 自建引擎的漏洞偵測品質需要長期 field testing 驗證
- 與核心 OODA 功能的開發互相競爭資源

### 選項 C：混合架構 — MCP 工具封裝 + AI 增強分析（Hybrid: MCP Tool Wrappers + AI-Enhanced Analysis）

將方案分為兩層：**底層掃描**使用成熟開源工具（via MCP），**上層分析**由 OrientEngine 的 LLM 增強層處理。

**底層 — 兩個新 MCP 工具伺服器（合併同類工具）：**

1. **mcp-web-scanner**：封裝 Nuclei + httpx，負責 Web 漏洞掃描與 HTTP 偵察
2. **mcp-api-fuzzer**：封裝 ffuf + 自建 API schema detector，負責 API 端點發現與 fuzzing

**上層 — OrientEngine AI 增強：**

- 掃描結果轉為 Facts 後，OrientEngine 進行 **cross-fact reasoning**：
  - 「httpx 偵測到 X-Powered-By: Express + API 端點 /api/v1/users → 可能存在 BOLA」
  - 「Nuclei 發現 SQLi on /search + credential fact 有 admin 帳號 → 嘗試 authenticated SQLi」
- LLM 推薦 **chained attack sequences**（模擬 Escape.tech MetaGraph 的多步驟攻擊鏈）
- Dead Branch Pruning 排除已失敗向量的同類攻擊

**優點：**
- 快速獲得基礎掃描能力（Nuclei + httpx 部署週期 ~1-2 週）
- AI 分析層彌補 signature-based 工具的 business logic 偵測盲區
- 僅新增 2 個 MCP 伺服器（5 → 7），管理負擔可控
- 掃描結果自動融入 OODA 循環，OrientEngine 的 `_ORIENT_SYSTEM_PROMPT` 和 Section 7.8 MCP Tools Summary 已具備路由基礎
- 保留未來擴展空間：可在 mcp-web-scanner 中逐步加入自建偵測邏輯

**缺點：**
- AI 分析層的 business logic inference 品質受限於 LLM 能力和 prompt 品質
- 中等複雜度：需要設計跨工具的 Fact 關聯機制
- Nuclei template 更新需要定期重建 Docker image

**風險：**
- 中等 — 依賴 Nuclei/httpx/ffuf 的穩定性，但有 Circuit Breaker 保底
- AI 增強層可能產生 false positive（需要 confidence threshold 過濾）
- 需確保掃描行為不超出 Engagement ROE（ScopeValidator 需擴展至 URL/path 層級）

---

## 決策（Decision）

選擇 **選項 C：混合架構 — MCP 工具封裝 + AI 增強分析**。

理由：

1. **時間效益比最優**：利用成熟開源工具快速獲得 80% 覆蓋率，AI 層提升剩餘 20% 的偵測深度
2. **架構一致性**：完全遵循 ADR-024 的 MCP 架構規範，新增工具伺服器即插即用
3. **OODA 閉環**：掃描結果作為 Facts 自動進入 OrientEngine 分析，無需額外整合工作
4. **漸進演進**：未來可在 mcp-web-scanner 中逐步替換 Nuclei 為自建引擎，實現選項 B 的長期願景

### 新增 MCP 工具伺服器設計

#### 1. mcp-web-scanner

**職責：** HTTP 偵察 + Web 漏洞掃描（封裝 httpx + Nuclei）

**MCP 工具列表：**

| Tool Name | 說明 | 輸入參數 | 輸出 Fact Trait |
|-----------|------|----------|----------------|
| `http_probe` | HTTP service probe + tech fingerprint | `target: str, ports: list[int]` | `web.technology`, `web.server`, `web.status_code` |
| `web_vuln_scan` | OWASP Top 10 vulnerability scan (Nuclei) | `target: str, templates: list[str]` | `web.vuln.{severity}`, `web.vuln.cve` |
| `dir_enumerate` | Directory/file enumeration | `target: str, wordlist: str` | `web.path.discovered`, `web.path.sensitive` |
| `waf_detect` | WAF/CDN detection | `target: str` | `web.waf.detected`, `web.cdn.detected` |

**Fact 輸出格式（結構化 JSON，MCPFactExtractor Layer 1）：**

```json
{
  "facts": [
    {
      "trait": "web.technology",
      "value": "Express/4.18.2",
      "category": "web",
      "confidence": 0.95,
      "evidence": "X-Powered-By header"
    },
    {
      "trait": "web.vuln.high",
      "value": "SQL Injection on /api/search?q= (Nuclei: sqli-error-based)",
      "category": "vulnerability",
      "confidence": 0.90,
      "evidence": "MySQL error in response body"
    }
  ]
}
```

**Docker 配置：**

```yaml
mcp-web-scanner:
  build: { context: ./tools/web-scanner }
  profiles: [mcp]
  command: ["python", "-m", "server", "--transport", "streamable-http", "--port", "8080"]
  environment:
    - NUCLEI_TEMPLATES_DIR=/opt/nuclei-templates
    - SCAN_RATE_LIMIT=100          # requests/sec, 避免 DoS 目標
    - SCAN_TIMEOUT_SEC=300
  ports:
    - "127.0.0.1:58096:8080"
  restart: unless-stopped
```

**Nuclei Template 策略：**

- 預裝 OWASP Top 10 核心 templates（~200 條）
- 支援自訂 template 目錄掛載（`/opt/nuclei-templates/custom/`）
- 按 severity 分級執行：`critical` + `high` 為預設，`medium` + `low` 需明確指定
- Template 更新透過 `make update-nuclei-templates` 觸發 Docker image rebuild

#### 2. mcp-api-fuzzer

**職責：** API endpoint discovery + schema detection + authentication bypass testing

**MCP 工具列表：**

| Tool Name | 說明 | 輸入參數 | 輸出 Fact Trait |
|-----------|------|----------|----------------|
| `api_discover` | OpenAPI/Swagger/GraphQL schema detection | `target: str` | `api.schema.openapi`, `api.schema.graphql`, `api.endpoint.discovered` |
| `api_fuzz_endpoints` | API endpoint enumeration (ffuf-based) | `target: str, wordlist: str, method: str` | `api.endpoint.discovered`, `api.endpoint.authenticated` |
| `api_auth_test` | Authentication bypass testing (BOLA/IDOR) | `target: str, endpoints: list[str], token: str` | `api.vuln.bola`, `api.vuln.idor`, `api.vuln.auth_bypass` |
| `api_param_fuzz` | Parameter fuzzing (injection/overflow) | `target: str, endpoint: str, params: dict` | `api.vuln.injection`, `api.vuln.overflow` |

**Fact 輸出格式：**

```json
{
  "facts": [
    {
      "trait": "api.schema.openapi",
      "value": "/api/v1/docs — OpenAPI 3.0.1 — 47 endpoints",
      "category": "web",
      "confidence": 1.0,
      "evidence": "HTTP 200 on /api/v1/openapi.json"
    },
    {
      "trait": "api.vuln.bola",
      "value": "GET /api/v1/users/{id} — IDOR confirmed (accessed user 2 with user 1 token)",
      "category": "vulnerability",
      "confidence": 0.85,
      "evidence": "HTTP 200 with different user data"
    }
  ]
}
```

**Docker 配置：**

```yaml
mcp-api-fuzzer:
  build: { context: ./tools/api-fuzzer }
  profiles: [mcp]
  command: ["python", "-m", "server", "--transport", "streamable-http", "--port", "8080"]
  environment:
    - FUZZ_RATE_LIMIT=50           # requests/sec
    - FUZZ_TIMEOUT_SEC=180
    - MAX_ENDPOINTS=500            # 防止 endpoint 爆炸
  ports:
    - "127.0.0.1:58097:8080"
  restart: unless-stopped
```

### mcp_servers.json 新增配置

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
  },
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

### OrientEngine 整合

新增 Fact category `web` 和 `vulnerability` 進入 OrientEngine prompt context 後，System Prompt 需擴展以下推理規則：

**Rule 6: Application Layer Reasoning（新增）**

```
When web.technology or web.server facts are present, consider application-layer attack vectors:
- web.technology: Express/Django/Spring → check for framework-specific CVEs
- web.vuln.* facts → chain with existing credentials for authenticated exploitation
- api.schema.openapi → recommend api_fuzz_endpoints for comprehensive coverage
- api.vuln.bola/idor → escalate to data exfiltration if sensitive endpoints confirmed

PREFER MCP web-scanner and api-fuzzer tools when HTTP services (port 80/443/8080/8443)
are detected in service.open_port facts.
```

### ReconEngine 整合

ReconEngine（`backend/app/services/recon_engine.py`）目前僅觸發 nmap scan。擴展後，當 nmap 偵測到 HTTP service 時，自動觸發 web-scanner 的 `http_probe`：

```python
# 在 _write_facts() 之後，檢查是否有 HTTP service
http_services = [s for s in services if s.service in ("http", "https", "http-proxy")]
if http_services and settings.MCP_ENABLED:
    manager = get_mcp_manager()
    if manager and manager.is_connected("web-scanner"):
        for svc in http_services:
            await manager.call_tool(
                "web-scanner", "http_probe",
                {"target": ip_address, "ports": [svc.port]}
            )
```

### Scope Validation 擴展

ScopeValidator 需從 IP-based 擴展至 URL/path-based，確保 Web 掃描不超出 Engagement ROE：

- 新增 `scope_urls` 欄位至 operations 表（允許的 URL pattern，如 `https://target.com/api/*`）
- `validate_url(db, operation_id, url)` 方法驗證掃描目標 URL 在 scope 內
- Wildcard 掃描（如 dir_enumerate）需要明確的 `scope_urls` 白名單

### 實作階段

| Phase | 範圍 | 預估工期 | 依賴 |
|-------|------|---------|------|
| **Phase 1** | mcp-web-scanner：httpx probe + tech fingerprint + waf detect | 1 週 | athena-mcp-base image |
| **Phase 2** | mcp-web-scanner：Nuclei integration + OWASP Top 10 templates | 1 週 | Phase 1 |
| **Phase 3** | mcp-api-fuzzer：OpenAPI/GraphQL schema detection + endpoint enumeration | 1 週 | athena-mcp-base image |
| **Phase 4** | mcp-api-fuzzer：authentication bypass testing (BOLA/IDOR) + parameter fuzzing | 1 週 | Phase 3 |
| **Phase 5** | OrientEngine prompt 擴展 + ReconEngine HTTP service 自動觸發 | 3 天 | Phase 1-4 |
| **Phase 6** | ScopeValidator URL-based 擴展 + E2E integration testing | 3 天 | Phase 5 |
| **Phase 7** | 以 DVWA + Juice Shop 執行完整驗證測試 | 2 天 | Phase 6 |

---

## 後果（Consequences）

**正面影響：**

- Athena OODA 循環從「網路層偵察 → 直接利用」擴展為「網路層偵察 → 應用層深度探測 → 精準利用」，攻擊路徑顯著豐富
- OrientEngine 能夠推薦 OWASP Top 10 + API-specific 攻擊手法，Kill Chain 覆蓋從 TA0043 延伸至 TA0001（Initial Access via Web Exploit）
- Nuclei 5,000+ community templates 提供即時的漏洞偵測能力，無需從零建構 signature database
- 新增工具完全遵循 ADR-024 MCP 架構，MCPClientManager Circuit Breaker 自動保護，工具故障不影響核心 OODA 循環
- ReconEngine 自動觸發 Web 偵察形成 **Reconnaissance Chain**：nmap → httpx probe → Nuclei scan → API discovery，無需手動操作

**負面影響 / 技術債：**

- Docker image 數量從 7（backend + frontend + 5 MCP）增加至 9，CI/CD pipeline 建構時間增加 ~2-3 分鐘
- Nuclei templates 需要定期更新（建議每週），否則漏洞偵測能力會落後於最新 CVE
- `mcp_servers.json` 仍為靜態配置（ADR-024 技術債），新增 2 個伺服器需重啟 backend 生效
- AI 增強層的 business logic inference 為 best-effort，false positive rate 需要持續監控和 prompt tuning
- Scope validation 擴展至 URL-based 後，operations 表 schema 變更需 migration script
- `tech-debt: test-pending` — headless browser integration（XBOW 風格）暫不納入，列為 Phase 2 長期目標

**後續追蹤：**

- [ ] Phase 1-2：mcp-web-scanner 完整實作與 Nuclei 整合
- [ ] Phase 3-4：mcp-api-fuzzer 完整實作與 BOLA/IDOR 測試
- [ ] Phase 5：OrientEngine Rule 6 prompt 擴展
- [ ] Phase 6：ScopeValidator URL-based 擴展
- [ ] Phase 7：DVWA + Juice Shop 驗證測試
- [ ] 長期：評估 headless browser integration（Playwright/Puppeteer）用於 DOM-based 漏洞偵測
- [ ] 長期：評估 GraphQL introspection + mutation fuzzing 專用模組
- [ ] 長期：評估 gRPC reflection API fuzzing 能力

---

## 成功指標（Success Metrics）

| 指標 | 目標值 | 驗證方式 | 檢查時間 |
|------|--------|----------|----------|
| OWASP Top 10 漏洞偵測覆蓋率 | >= 80%（至少覆蓋 8/10 類別） | 對照 DVWA + OWASP Juice Shop 的已知漏洞清單 | Phase 7 完成時 |
| API 端點發現率 | >= 90%（已知 OpenAPI spec 目標） | 掃描結果 vs. Swagger/OpenAPI spec 端點數量 | Phase 4 完成時 |
| 新增 MCP 工具伺服器數量 | 2（web-scanner + api-fuzzer） | `docker compose --profile mcp ps` | Phase 4 完成時 |
| 新增 MCP 工具數量 | 8（4 per server） | `tool_registry` DB 表 | Phase 4 完成時 |
| Fact 擷取成功率 | >= 95%（結構化 JSON Layer 1） | MCPFactExtractor unit tests | 每次 CI |
| OrientEngine Web 攻擊推薦率 | 當 HTTP service facts 存在時，>= 70% 的推薦包含 Web 攻擊選項 | 整合測試：注入 HTTP service facts → 驗證推薦結果 | Phase 5 完成時 |
| Scan 不超出 Scope | 0 次 scope violation（URL-based） | ScopeValidator unit tests + E2E | Phase 6 完成時 |
| 單次 Web scan latency | < 120s（standard scan profile） | `make test` + integration benchmark | Phase 2 完成時 |
| 測試通過率 | 100% | `make test` | 每個 Phase 完成時 |
| False positive rate | < 15%（Nuclei high/critical findings） | 人工驗證 DVWA/Juice Shop 掃描結果 | Phase 7 完成時 |

> 重新評估條件：若 Nuclei 專案停止維護、或 false positive rate 持續 > 25%，應重新評估選項 B（自建引擎）的可行性。

---

## 關聯（Relations）

- 取代：無
- 被取代：無
- 依賴：ADR-024（MCP Architecture — 提供工具伺服器基礎架構、MCPClientManager、MCPFactExtractor）
- 參考：ADR-025（Exploit Validation Layer — 漏洞驗證可套用於 Web 漏洞確認）
- 參考：ADR-028（Attack Graph Engine — Web 攻擊節點可納入攻擊路徑圖）
- 啟發：Escape.tech FDSAE Algorithm、Escape.tech MetaGraph、XBOW Headless Browser Integration
- 延伸：SPEC-025（Tool Registry 管理 UI — 需更新以顯示 Web/API 工具狀態）
