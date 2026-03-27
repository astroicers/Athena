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

---

## 🔗 副作用與連動（Side Effects）

| 說明 | 觸發條件 | 受影響模組 | 驗證方式 |
|------|---------|-----------|---------|
| MCP 容器獲得宿主機 LAN 存取 | docker-compose 重建容器 | mcp-nmap, mcp-credential-checker, mcp-attack-executor, mcp-web-scanner, mcp-api-fuzzer | 容器內 `ping host.docker.internal` |
| `recon_scans` 表結構變更（新增 `facts_written` 欄位） | DB migration 執行 | REST GET `/operations/{op_id}/recon/scans/{scan_id}`、WS scan 事件 | API 回傳 `facts_written` 數值正確 |
| `_build_scan_result()` 讀取 DB 欄位取代硬編碼 | 任何 recon scan 完成 | Recon modal 顯示 | Modal 中 `facts_written` 與實際寫入 fact 數量一致 |
| 空掃描結果新增 warning log | nmap 回傳 0 services | 日誌系統 | `grep "WARNING" backend logs` 可見 raw nmap 回應 |

---

## Rollback Plan

| 項目 | 內容 |
|------|------|
| **回退步驟** | 1. Revert commit 2. `docker compose --profile mcp up -d` 重建容器 3. 手動 `ALTER TABLE recon_scans DROP COLUMN facts_written`（若需清理） |
| **資料影響** | `facts_written` 欄位有 DEFAULT 0，DROP 後不影響既有資料；`extra_hosts` 移除後容器恢復預設網路隔離 |
| **驗證方式** | `make test` 通過 + recon scan 功能回歸測試 |
| **已測試** | 否（bug fix 為低風險變更） |

---

## 🧪 測試矩陣（Test Matrix）

| ID | 類型 | 場景 | 預期結果 | 參考場景 |
|----|------|------|---------|---------|
| P1 | 正向 | 對 LAN 目標執行 recon scan，services > 0 | Modal 正確顯示 services_found 和 facts_written | S1 |
| P2 | 正向 | REST GET scan 結果 | API 回傳正確 facts_written 值 | S1 |
| N1 | 負向 | 目標 IP 不存在 / 不可達 | scan 完成但 services = 0，log 含 warning | S2 |
| N2 | 負向 | DB migration 前查詢 facts_written | 回傳 DEFAULT 0，不 crash | S2 |
| B1 | 邊界 | 目標只有 1 個 open port | facts_written = 對應寫入數 | S1 |
| B2 | 邊界 | 大量 services（>100 ports） | 結果正確截斷或完整顯示 | S1 |

---

## 🎬 驗收場景（Acceptance Scenarios）

```gherkin
Feature: MCP 容器網路存取與 Recon Scan 結果修復
  Background:
    Given 已部署 MCP 容器（mcp-nmap, mcp-credential-checker, mcp-attack-executor, mcp-web-scanner, mcp-api-fuzzer）
    And docker-compose 配置包含 extra_hosts host.docker.internal
    And 存在一個活躍的 operation 和 LAN 目標 192.168.0.23

  Scenario: mcp-nmap 容器可存取 LAN 目標並正確回傳 scan 結果
    When 使用者對目標 192.168.0.23 發起 recon scan
    Then mcp-nmap 容器成功掃描目標
    And scan 結果中 services_found > 0
    And REST GET /operations/{op_id}/recon/scans/{scan_id} 回傳的 facts_written 與實際寫入數一致
    And Modal 顯示的 facts_written 與 API 回傳值相同

  Scenario: 空掃描結果產生 warning log
    Given 目標 IP 為不可達的位址 10.255.255.1
    When 使用者對該目標發起 recon scan
    Then scan 完成且 services_found = 0
    And 後端日誌包含 WARNING 級別訊息
    And WARNING 訊息包含 raw nmap 回應的前 500 字元
```

---

## 📎 追溯性（Traceability）

| 類型 | 路徑 | 說明 | 日期 |
|------|------|------|------|
| 後端實作 | `backend/app/routers/recon.py` | `_build_scan_result()` 修正 facts_written | 2026-03-26 |
| 後端實作 | `backend/app/services/recon_engine.py` | 空結果 warning log | 2026-03-26 |
| 後端實作 | `backend/app/database/manager.py` | DB migration：ALTER TABLE recon_scans | 2026-03-26 |
| 基礎設施 | `docker-compose.yml` | extra_hosts 設定 | 2026-03-26 |
| 後端測試 | `backend/tests/test_recon_engine.py` | recon engine 單元測試 | 2026-03-26 |
| 後端測試 | `backend/tests/test_recon_router.py` | recon router API 測試 | 2026-03-26 |
| 後端測試 | `backend/tests/test_recon_mcp_integration.py` | MCP 整合測試 | 2026-03-26 |
| E2E 測試 | `frontend/e2e/full-workflow.spec.ts` | 完整工作流含 recon scan | 2026-03-26 |

---

## 📊 可觀測性（Observability）

| 層級 | 項目 | 說明 |
|------|------|------|
| 後端 Metrics | `recon_scan_facts_written` | 每次 scan 的 facts_written 計數（可透過 log 統計） |
| 後端 Logs | `WARNING: nmap scan returned 0 services` | 空掃描結果 warning，含 raw 回應前 500 字 |
| 後端 Logs | `INFO: recon scan completed` | scan 完成 log，含 services_found 和 facts_written |
| 後端 Alerts | 連續 3 次 scan 回傳 0 services | 可能的網路隔離問題偵測 |
| 後端故障偵測 | `extra_hosts` 設定缺失 | 容器內 `ping host.docker.internal` 失敗 |
| 前端 | N/A | 本次修復無前端可觀測性需求 |
