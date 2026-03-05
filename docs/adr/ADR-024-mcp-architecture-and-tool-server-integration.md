# [ADR-024]: MCP Architecture and Tool Server Integration

| 欄位 | 內容 |
|------|------|
| **狀態** | `Accepted` |
| **日期** | 2026-03-05 |
| **決策者** | Athena Core Team |

---

## 背景（Context）

Athena 需要一個可擴展的工具執行層，用於偵察（Recon）、OSINT、弱點查詢（Vuln Lookup）、憑證檢查等操作。工具需要：

1. **隔離性**：各工具依賴不同系統工具（nmap、dnspython 等），不應汙染後端核心環境
2. **可擴展性**：新工具應能快速加入，不修改核心 engine 代碼
3. **容錯性**：工具服務當機不應拖垮 OODA 循環
4. **統一資料流**：工具產出必須轉換為 `facts` 表記錄，供 Orient 引擎分析

既有執行引擎（SSH、C2、Metasploit）透過 `engine_router.py` 統一調度，MCP 層需融入此架構。

---

## 評估選項（Options Considered）

### 選項 A：直接函數呼叫（in-process）

- **優點**：零網路延遲、簡單除錯
- **缺點**：工具依賴汙染後端環境、單一工具崩潰拖垮整個 backend、無法獨立擴展
- **風險**：nmap 等系統工具需 root 權限，影響後端安全邊界

### 選項 B：MCP 協議 + 容器化工具伺服器

- **優點**：進程隔離、標準化通訊協議、支援 HTTP/stdio 雙傳輸、自動工具發現（`list_tools()`）、Docker profile 可選啟用
- **缺點**：增加 Docker image 數量、HTTP 傳輸增加 ~50ms 延遲
- **風險**：MCP 協議仍在演進，API 可能變動

### 選項 C：自建 gRPC 工具協議

- **優點**：完全掌控協議、強型別
- **缺點**：需自行維護協議定義、缺乏生態系支援、開發成本高
- **風險**：與 Claude Code / Anthropic 生態系不相容

---

## 決策（Decision）

選擇 **選項 B：MCP 協議 + 容器化工具伺服器**。

### 傳輸策略

- **Auto 模式**（預設）：優先探測 HTTP 端點（1s 超時），不可達時退回 stdio
- **HTTP**：適用 Docker 容器化部署（`streamablehttp_client`）
- **stdio**：適用本地開發或輕量部署（`StdioServerParameters`）

### 容器化

- 每個工具伺服器獨立 Dockerfile，繼承 `athena-mcp-base:latest` 共用基底
- Docker Compose `--profile mcp` 可選啟用，不影響核心服務
- 工具配置集中於 `mcp_servers.json`，後端只讀掛載

### 工具調度

- 整合至 `engine_router.py` 的統一調度鏈，MCP 為最高優先級（偵察類工具）
- 優先序：MCP → Metasploit → WinRM → Persistent SSH → SSH → C2

### 生命週期管理（`MCPClientManager`）

- **啟動**：解析 `mcp_servers.json` → 連線各伺服器 → `list_tools()` 自動發現 → 同步至 `tool_registry` DB 表
- **容錯**：每伺服器獨立 Circuit Breaker（CLOSED → OPEN → HALF_OPEN），指數退避（最大 60s）
- **健康檢查**：背景任務每 30s 探測，OPEN 電路冷卻後自動重連
- **關閉**：取消健康檢查、斷開所有 session、soft-delete 工具記錄

### Fact 擷取（`MCPFactExtractor`）

三層 fallback：
1. **結構化 Facts**（首選）：`{"facts": [{"trait": "service.open_port", "value": "22/tcp/ssh"}]}`
2. **扁平 Dict**：`{"trait_name": "value"}` 直接映射
3. **純文字 Fallback**：包裝為 `mcp.output` fact（500 字元上限）

---

## 後果（Consequences）

**正面影響：**
- 工具新增只需 `make new-tool NAME=xxx` + 實作 `server.py`，無需修改核心代碼
- Circuit Breaker 防止工具當機拖垮 OODA 循環
- 三層 Fact 擷取容許工具輸出格式差異，降低耦合
- 與 Claude Code MCP 生態系相容，可直接複用社群工具

**負面影響 / 技術債：**
- Docker image 數量增加（目前 4 個工具 + 1 base = 5 images）
- `mcp_servers.json` 為靜態配置，不支援執行時動態註冊（需重啟）
- HTTP 傳輸比 stdio 多 ~50ms 延遲（對偵察工具可接受）

**後續追蹤：**
- [x] Phase 1-4：基礎建設、偵察伺服器、Docker profile、健康/超時
- [x] Phase 5：OODA 自動路由 + tool-registry dispatch + enrichment hook
- [x] Phase 6：NVD rate limiter + credential-checker + 前端狀態卡
- [x] Phase 7：移除直接工具執行，MCP-only 架構

---

## 成功指標（Success Metrics）

| 指標 | 目標值 | 驗證方式 | 檢查時間 |
|------|--------|----------|----------|
| 工具發現延遲 | < 3s / 伺服器 | `make test` + 整合測試 | 實作完成時 |
| Circuit Breaker 恢復 | < 30s（OPEN → HALF_OPEN） | 手動故障注入 + 日誌 | 部署後 |
| Fact 擷取覆蓋率 | 三層 fallback 覆蓋 4 個伺服器 | MCPFactExtractor 單元測試 | 每次新增工具 |
| MCP-only 執行 | OODA Decide/Act 可呼叫任一註冊工具 | E2E: 觸發 OODA → 驗證 nmap facts 入庫 | 整合測試 |
| 無工具不影響核心 | `mcp_servers.json` 為空時後端正常啟動 | `EXECUTION_ENGINE=ssh` 模式測試 | CI |

---

## 關聯（Relations）

- 取代：無
- 被取代：無
- 延伸：ADR-006（執行引擎抽象層）、ADR-015（Recon Kill Chain）
- 參考：ADR-023（非同步操作）、SPEC-025（Tool Registry 管理 UI）
