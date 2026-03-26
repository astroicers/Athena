# SPEC-036：MCP 容器目標網路存取 + Recon Scan 結果修復

> 修復 MCP 工具容器因 Docker 網路隔離無法存取滲透測試目標的問題，並修正 recon scan 結果 modal 顯示不正確的 bug。

| 欄位 | 內容 |
|------|------|
| **規格 ID** | SPEC-036 |
| **關聯 ADR** | ADR-032（MCP 容器目標網路存取策略） |
| **估算複雜度** | 低 |
| **建議模型** | Sonnet |
| **HITL 等級** | minimal |

---

## 目標（Goal）

1. 讓所有需要存取目標 IP 的 MCP 容器能到達宿主機 LAN 上的滲透測試目標
2. 修正 recon scan 結果 modal 中 `facts_written` 永遠顯示 0 的 bug
3. 空掃描結果時增加 warning log 以便除錯

---

## 問題分析（Problem Analysis）

### 問題 1：Docker 網路隔離

MCP 工具容器使用預設 bridge network，無法到達宿主機 LAN IP（如 `192.168.0.23`）。

**受影響容器：**

| 容器 | 用途 | 影響 |
|------|------|------|
| mcp-nmap | nmap 掃描目標 port | 0 services found |
| mcp-credential-checker | SSH/RDP/WinRM 連線 | connection refused |
| mcp-attack-executor | SSH/WinRM 執行指令 | connection refused |
| mcp-web-scanner | httpx/nuclei 探測 | connection refused |
| mcp-api-fuzzer | HTTP fuzzing | connection refused |

**不受影響容器（僅需 Internet）：** mcp-osint、mcp-vuln

### 問題 2：`facts_written` 硬編碼為 0

- `recon_scans` DB 表缺少 `facts_written` 欄位
- `_build_scan_result()` 在 `recon.py:320` 硬編碼 `facts_written=0`
- WS event 帶正確值，但 modal 透過 REST GET 讀取 → 永遠顯示 0

### 問題 3：空結果無 log

nmap 掃描回傳 0 services 時無任何 warning，難以除錯。

---

## 修改規格（Changes）

### 1. docker-compose.yml

為 5 個需存取目標的容器加入 `extra_hosts`：

```yaml
extra_hosts:
  - "host.docker.internal:host-gateway"
```

容器：mcp-nmap, mcp-credential-checker, mcp-attack-executor, mcp-web-scanner, mcp-api-fuzzer

### 2. backend/app/database.py

- CREATE TABLE `recon_scans` 加入 `facts_written INTEGER DEFAULT 0`
- 新增 migration：`ALTER TABLE recon_scans ADD COLUMN facts_written INTEGER DEFAULT 0`

### 3. backend/app/routers/recon.py

- `_run_scan_background()`：UPDATE SQL 加入 `facts_written = ?`
- `_SCAN_SELECT`：加入 `s.facts_written`
- `_build_scan_result()`：`facts_written=row["facts_written"] or 0`

### 4. backend/app/services/recon_engine.py

- `scan()` 中 `_scan_via_mcp()` 回傳後，若 `services` 為空，log warning 含 raw nmap 回應前 500 字

---

## 驗證清單（Verification）

- [ ] `make test` 通過（recon 相關測試全部 PASSED）
- [ ] `docker compose --profile mcp up -d` 重建容器
- [ ] mcp-nmap 容器內 `ping host.docker.internal` 可通
- [ ] 對 LAN 目標執行 recon scan → services > 0
- [ ] Modal 顯示正確的 `facts_written` 和 `services_found`
- [ ] `GET /operations/{op_id}/recon/scans/{scan_id}` 回傳正確 `facts_written`

---

## 關聯（Relations）

- ADR-032（MCP 容器目標網路存取策略）
- ADR-024（MCP Architecture and Tool Server Integration）
- SPEC-019（Recon & Initial Access Kill Chain）
- SPEC-023（Async Scan OODA）

<!-- tech-debt: scenario-pending — v3.2 upgrade: needs test matrix + Gherkin scenarios -->
<!-- tech-debt: observability-pending — v3.3 upgrade: needs observability section -->
