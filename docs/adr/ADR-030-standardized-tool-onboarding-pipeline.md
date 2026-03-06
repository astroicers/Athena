# [ADR-030]: Standardized Tool Onboarding Pipeline

| 欄位 | 內容 |
|------|------|
| **狀態** | `Accepted` |
| **日期** | 2026-03-06 |
| **決策者** | Athena Core Team |

---

## 背景（Context）

ADR-024 確立了 MCP 協議 + 容器化工具伺服器的架構，解決了工具隔離、容錯和統一資料流的問題。然而，ADR-024 聚焦於**運行時架構**，未定義**新工具的加入流程**。

### 現狀問題

目前加入一個新工具需要手動操作 4 個分散的設定點：

```
make new-tool NAME=xxx          ← Step 1: scaffold（自動）
編輯 tools/xxx/server.py        ← Step 2: 實作（手動）
編輯 mcp_servers.json           ← Step 3: 註冊 MCP（手動，易漏）
編輯 docker-compose.yml         ← Step 4: 加 service（手動，port 易衝突）
POST /api/tools                 ← Step 5: 註冊 registry（手動，或靠自動發現）
```

具體缺口：

| 問題 | 現狀 | 影響 |
|------|------|------|
| `mcp_servers.json` 手動編輯 | 開發者需自行寫 JSON entry | 格式錯誤、欄位遺漏 |
| `docker-compose.yml` 手動編輯 | 需手動加 service block + 分配 port | port 衝突（現有 58091-58095）、格式不一致 |
| Template 與 production 不一致 | `_template/server.py` 缺 argparse + TransportSecuritySettings | 新工具容器化後 HTTP transport 無法啟動 |
| 無工具 metadata 標準 | MITRE mapping、risk_level、output_traits 散落於 DB 和 API 呼叫中 | 無 single source of truth |
| 無本地開發流程 | 必須 build Docker image 才能測試 | 開發迭代慢 |
| README 步驟不完整 | `_template/README.md` 列出 3 步但實際需 5 步 | 新人無法自助完成 |

### 規模考量

隨著 OODA 循環擴展（ADR-027 Agent Swarm、ADR-029 Application Layer Attack），預計工具數量將從目前 5 個增長到 10-15 個。手動流程的維護成本將線性增長。

---

## 評估選項（Options Considered）

### 選項 A：維持現狀 + 加強文件

- **做法**：不改代碼，只更新 `_template/README.md` 和 wiki，詳列所有手動步驟
- **優點**：零代碼改動、零維護成本
- **缺點**：仍靠人工執行、容易遺漏步驟、格式不一致無法自動驗證
- **風險**：新人反覆犯相同錯誤（漏改 mcp_servers.json、port 衝突等）

### 選項 B：`tool.yaml` metadata + 自動化 scaffold 腳本

- **做法**：每個工具目錄下放一份 `tool.yaml` 描述工具 metadata（MITRE mapping、risk_level、MCP 配置、Docker 設定）。`make new-tool` 改為呼叫 Python script，自動：(1) 複製 template (2) 替換佔位符 (3) 注入 `mcp_servers.json` (4) 注入 `docker-compose.yml`（自動分配 port）
- **優點**：單一 source of truth（tool.yaml）、可程式化、CI 可 lint 驗證、冪等（重跑不會重複註冊）
- **缺點**：需維護 scaffold 腳本（~150 行 Python）
- **風險**：`tool.yaml` schema 設計需合理，不宜過度膨脹

### 選項 C：互動式 CLI 精靈

- **做法**：寫一支 `athena-tool init` CLI，用互動問答引導開發者填寫工具名稱、類型、MITRE mapping 等，自動產生所有設定
- **優點**：引導式體驗、不易漏欄位、可加輸入驗證
- **缺點**：過度工程（對 5-15 個工具的專案而言）、需額外依賴（click/typer）、CI 中無法使用互動 CLI
- **風險**：CLI 本身成為需維護的產品，偏離核心目標

---

## 決策（Decision）

選擇 **選項 B：`tool.yaml` metadata + 自動化 scaffold 腳本**。

理由：
1. **務實平衡**：比選項 A 多投入約 150 行腳本代碼，但消除了所有手動步驟
2. **不過度工程**：比選項 C 簡單許多，無額外依賴，Makefile + Python script 足矣
3. **CI 友善**：`tool.yaml` 可被 schema 驗證，scaffold 可在 CI 中測試
4. **向後相容**：現有工具補上 `tool.yaml` 即可，不需改動現有 `server.py` 或 Dockerfile

### 設計規格

#### 1. `tool.yaml` Schema

```yaml
# tools/<tool-name>/tool.yaml
tool_id: "dns-enum"                      # 唯一識別符（slug 格式）
name: "DNS Enumerator"                   # 顯示名稱
description: "DNS subdomain enumeration" # 工具描述
category: "reconnaissance"               # reconnaissance | credential_access | execution | lateral_movement | collection
risk_level: "low"                        # low | medium | high | critical
mitre_techniques: ["T1595.002"]          # MITRE ATT&CK technique IDs
output_traits: ["network.subdomain"]     # Athena fact traits this tool produces

# MCP Server 配置（自動注入 mcp_servers.json）
mcp:
  transport: "stdio"
  command: "python"
  args: ["-m", "server"]
  http_url: "http://mcp-dns-enum:8080/mcp"
  tool_prefix: "dns"

# Docker Compose 配置（自動注入 docker-compose.yml）
docker:
  port: 0                                # 0 = 自動分配下一個 5809x port
  environment: {}                        # 額外環境變數
```

#### 2. 升級 `tools/_template/server.py`

對齊 production tools 的完整模式（以 nmap-scanner 為參考）：
- 加入 `TransportSecuritySettings(enable_dns_rebinding_protection=False)`
- 加入 `argparse` 區塊支援 `--transport`, `--host`, `--port` 參數
- 保留 example tool function 作為示範

#### 3. `scripts/scaffold_tool.py` 自動化腳本

輸入：tool name（slug 格式）
行為：
1. 若 `tools/<name>/` 已存在 → 報錯退出
2. 複製 `tools/_template/` → `tools/<name>/`
3. 替換所有 `{{TOOL_NAME}}` 佔位符
4. 讀取 `mcp_servers.json`，加入新 server entry（若 key 不存在）
5. 讀取 `docker-compose.yml`，加入新 service block：
   - 自動掃描現有 `5809x` port，分配下一個可用 port
   - 使用 `profile: [mcp]`、標準 command 和 build context
6. 輸出操作摘要

冪等性保證：每步操作前檢查是否已存在，避免重複。

#### 4. Makefile 新增 targets

```makefile
new-tool:    # 升級：呼叫 scaffold_tool.py（取代現有 sed 方式）
dev-tool:    # 新增：本地 stdio 模式啟動
dev-tool-http: # 新增：本地 HTTP 模式啟動
```

#### 5. 現有工具回填 `tool.yaml`

為 5 個現有工具補建 `tool.yaml`，資料來源為 `mcp_servers.json` 和 `docker-compose.yml` 中的現有配置：
- `nmap-scanner`：category=reconnaissance, T1046, output_traits=[service.open_port, network.host.ip, host.os]
- `osint-recon`：category=reconnaissance, T1595.002, output_traits=[network.subdomain]
- `vuln-lookup`：category=reconnaissance, T1592, output_traits=[vuln.cve]
- `credential-checker`：category=credential_access, T1110, output_traits=[credential.ssh, credential.rdp, credential.winrm]
- `attack-executor`：category=execution, T1059, output_traits=[execution.result]

---

## 後果（Consequences）

**正面影響：**
- 新工具加入只需 `make new-tool NAME=xxx` → 編輯 `server.py` → 編輯 `tool.yaml`，不需手動改其他檔案
- `tool.yaml` 作為工具 metadata 的 single source of truth，可被 CI lint 驗證
- `make dev-tool` 提供快速本地開發迴圈，不需 Docker build
- 升級後的 template 與 production 一致，新工具開箱即可容器化

**負面影響 / 技術債：**
- `scripts/scaffold_tool.py` 需解析 `docker-compose.yml` YAML 結構，YAML 寫入需保留格式（使用 `ruamel.yaml` 或手動字串拼接）
- `tool.yaml` schema 初期較簡單，未來可能需擴展（如 resource limits、health check 配置）

**後續追蹤：**
- [ ] Phase 1：升級 `tools/_template/`（server.py + tool.yaml + README.md）
- [ ] Phase 2：實作 `scripts/scaffold_tool.py`
- [ ] Phase 3：升級 Makefile（new-tool, dev-tool, dev-tool-http）
- [ ] Phase 4：回填現有 5 工具的 `tool.yaml`
- [ ] Phase 5：驗證端到端流程（scaffold → dev → build → deploy → auto-discover）

---

## 成功指標（Success Metrics）

| 指標 | 目標值 | 驗證方式 | 檢查時間 |
|------|--------|----------|----------|
| 新工具加入手動步驟數 | 3 步（new-tool → 編輯 server.py → 編輯 tool.yaml） | 實際操作計數 | 實作完成時 |
| Scaffold 冪等性 | 重複執行不產生重複 entry | `make new-tool` 二次執行測試 | 實作完成時 |
| 現有工具回歸 | `make build-mcp` 5 個工具全部 build 成功 | Docker build | 實作完成時 |
| Port 自動分配 | 不與現有 58091-58095 衝突 | Scaffold 測試工具後驗證 | 實作完成時 |
| 本地開發可用性 | `make dev-tool NAME=xxx` stdio 正常啟動 | 手動測試 | 實作完成時 |

> 重新評估條件：若工具數量超過 20 個，或需支援非 Python 工具伺服器，應重新評估是否需要更完整的 CLI 工具（選項 C）。

---

## 關聯（Relations）

- 取代：無
- 被取代：無
- 延伸：ADR-024（MCP Architecture and Tool Server Integration）
- 參考：ADR-006（執行引擎抽象層）、ADR-027（Parallel Agent Swarm — 預期工具數量增長）
