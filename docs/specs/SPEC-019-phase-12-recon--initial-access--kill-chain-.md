# SPEC-019：Phase 12 Recon 與 Initial Access — Kill Chain 前半段補完

> 結構完整的規格書讓 AI 零確認直接執行。

| 欄位 | 內容 |
|------|------|
| **規格 ID** | SPEC-019 |
| **關聯 ADR** | ADR-015 |
| **估算複雜度** | 高 |
| **建議模型** | Sonnet |
| **HITL 等級** | standard |

---

## 🎯 目標（Goal）

補完 Athena Kill Chain 前半段（TA0043 Reconnaissance + TA0001 Initial Access），
讓使用者只需輸入 IP 就能觸發全自動 nmap 掃描 → SSH credential 嘗試 → Caldera agent 部署 → OODA 循環，
無需手動在靶機上部署 agent。

---

## 📥 輸入規格（Inputs）

### POST /api/operations/{op_id}/recon/scan

| 參數名稱 | 型別 | 來源 | 限制條件 |
|----------|------|------|----------|
| `op_id` | string | URL path | 必須存在於 operations 表 |
| `target_id` | string | JSON body | 必須存在於 targets 表，且屬於此 operation |
| `enable_initial_access` | bool | JSON body | 預設 true |
| `caldera_host` | string | JSON body（可選） | 預設從 settings.CALDERA_URL 取得 |

### GET /api/operations/{op_id}/recon/status

| 參數名稱 | 型別 | 來源 | 限制條件 |
|----------|------|------|----------|
| `op_id` | string | URL path | 必須存在於 operations 表 |

---

## 📤 輸出規格（Expected Output）

### POST /recon/scan 成功情境：
```json
{
  "scan_id": "uuid",
  "status": "completed",
  "ip_address": "192.168.1.100",
  "os_guess": "Linux_2.6.x",
  "services_found": 5,
  "facts_written": 7,
  "initial_access": {
    "success": true,
    "method": "ssh_credential",
    "credential": "msfadmin:msfadmin",
    "agent_deployed": true
  },
  "scan_duration_sec": 45.2
}
```

### POST /recon/scan Mock 模式情境（MOCK_CALDERA=true）：
```json
{
  "scan_id": "uuid",
  "status": "completed",
  "ip_address": "192.168.1.100",
  "os_guess": "Linux_2.6.x",
  "services_found": 3,
  "facts_written": 5,
  "initial_access": {
    "success": true,
    "method": "ssh_credential",
    "credential": "msfadmin:msfadmin",
    "agent_deployed": false
  },
  "scan_duration_sec": 0.01
}
```

### 失敗情境：

| 錯誤類型 | HTTP Code | 處理方式 |
|----------|-----------|----------|
| operation 不存在 | 404 | `{"detail": "Operation not found"}` |
| target 不存在或不屬於此 operation | 404 | `{"detail": "Target not found"}` |
| nmap 未安裝或執行失敗 | 500 | `{"detail": "nmap scan failed: <error>"}` |
| SSH port 未開放 | 200 | `initial_access.success = false`, `method = "none"` |

---

## 🏗️ 模組規格（Module Specs）

### models/recon.py
- `ServiceInfo`: `port: int`, `protocol: str`, `service: str`, `version: str`, `state: str`
- `ReconResult`: `target_id`, `operation_id`, `ip_address`, `os_guess: str | None`, `services: list[ServiceInfo]`, `facts_written: int`, `scan_duration_sec: float`, `raw_xml: str | None`
- `InitialAccessResult`: `success: bool`, `method: str`, `credential: str | None`, `agent_deployed: bool`, `error: str | None`
- `ReconScanResult`: 整合上面兩個的回傳值，加上 `scan_id: str`, `status: str`

### services/recon_engine.py — ReconEngine
- `scan(db, operation_id, target_id) -> ReconResult`
- Mock 模式（MOCK_CALDERA=true）：直接回傳 3 個假服務（22/ssh, 80/http, 21/ftp），寫入 facts
- 真實模式：nmap 命令 `nmap -sV -O --open --script=banner`，在 executor 中執行（非阻塞）
- Fact 寫入格式：
  - `category=service, trait=service.open_port, value="22/tcp/ssh/OpenSSH_7.4"`
  - `category=network, trait=network.host.ip, value="192.168.1.100"`
  - `category=host, trait=host.os, value="Linux_2.6.x"`
- 每寫入一個 fact，廣播 WebSocket `fact.new` 事件
- 若偵測到 OS，更新 `targets.os` 欄位

### services/initial_access_engine.py — InitialAccessEngine
- `try_ssh_login(db, operation_id, target_id, ip, port=22) -> InitialAccessResult`
- Default credentials: `[("msfadmin","msfadmin"), ("root","toor"), ("admin","admin"), ("user","user")]`
- Mock 模式：直接回傳 `success=True, credential="msfadmin:msfadmin"`，寫入 credential fact，不建立真實 SSH 連線
- 真實模式：asyncssh 連線，`known_hosts=None`（滲透測試環境）
- 成功後寫入 fact：`category=credential, trait=credential.ssh, value="msfadmin:msfadmin@ip:22"`
- `bootstrap_caldera_agent(ip, credential, caldera_host) -> bool`
  - 透過 SSH session 下載並執行 sandcat agent
  - 等待 30 秒讓 agent beacon 回來
  - 呼叫 `CalderaClient.list_agents()` 驗證 agent 是否上線

### routers/recon.py
- `POST /operations/{op_id}/recon/scan` — 觸發完整 recon + initial access 流程（async，但本版本為同步等待完成）
- `GET /operations/{op_id}/recon/status` — 查詢最近一筆 recon_scan 記錄

### database.py — 新增 recon_scans 表
```sql
CREATE TABLE IF NOT EXISTS recon_scans (
    id TEXT PRIMARY KEY,
    operation_id TEXT REFERENCES operations(id) ON DELETE CASCADE,
    target_id TEXT REFERENCES targets(id) ON DELETE CASCADE,
    status TEXT DEFAULT 'pending',
    nmap_result TEXT,
    open_ports TEXT,
    os_guess TEXT,
    initial_access_method TEXT,
    credential_found TEXT,
    agent_deployed INTEGER DEFAULT 0,
    started_at TEXT,
    completed_at TEXT
);
```

### seed/demo_scenario.py — 補充 TA0043 技術
新增四筆技術種子資料：T1046, T1592, T1595.002, T1110.003

---

## ⚠️ 邊界條件（Edge Cases）

- **nmap timeout**：超過 5 分鐘的掃描應中斷並回傳已收集結果（不得讓 API 永遠 pending）
- **SSH port 關閉**：跳過 Initial Access，回傳 `method="none"`，不報錯
- **所有 credential 均失敗**：`success=False`, `agent_deployed=False`，繼續回傳 recon 結果
- **Mock 模式**：`MOCK_CALDERA=true` 時，`agent_deployed` 永遠為 `false`（不建立真實 agent）
- **同一 target 重複掃描**：允許，新增一筆 recon_scans 記錄，舊有 facts 不刪除（重複 trait+value 由 INSERT OR IGNORE 處理）
- **nmap 未安裝**：應捕捉 `nmap.PortScannerError` 並回傳 500

---

## ✅ 驗收標準（Done When）

- [x] `make test-filter FILTER=recon` 全數通過（unit tests for ReconEngine + InitialAccessEngine）
- [x] `POST /api/operations/{op_id}/recon/scan` 在 mock 模式下回傳包含 3 個服務的結果
- [x] mock scan 後，`GET /api/operations/{op_id}/facts` 中可看到 `service.open_port` facts
- [x] `make lint` 無 error
- [x] 已更新 `docs/architecture.md`（加入 Recon + Initial Access 模組）
- [x] 已更新 `CHANGELOG.md`
- [x] 所有現有測試 (`make test`) 仍通過（無迴歸）

---

## 🚫 禁止事項（Out of Scope）

- 不修改：OODAController, OrientEngine, DecisionEngine, EngineRouter, 前端
- 不實作：Metasploit RPC 整合（Phase B，待 ADR-016）
- 不實作：ContainerEngineClient（工具容器，待另立計畫）
- 不實作：Shannon 整合（待 Shannon 可部署版本）
- 不引入新依賴（除 `python-nmap`, `asyncssh`, `cryptography` 外）

---

## 📎 參考資料（References）

- 關聯 ADR：ADR-015（Recon 與 Initial Access 引擎架構）
- 依賴 ADR：ADR-003（OODA 循環）、ADR-006（執行引擎抽象層）、ADR-008（SQLite Schema）
- 評估文件：`docs/analysis/recon-pocket-integration-assessment.md`
- 現有類似實作：`backend/app/services/caldera_client.py`（ExecutionEngineClient 範例）

---

## 副作用與連動（Side Effects）

| 副作用 | 觸發條件 | 影響模組 | 驗證方式 |
|--------|----------|----------|----------|
| DB `recon_scans` 表新增記錄 | `POST /recon/scan` 執行 | `backend/app/database/` schema | `test_recon_engine.py` + `test_recon_router.py` |
| Facts 表寫入 `service.open_port` / `network.host.ip` / `host.os` | nmap 掃描完成後 | `backend/app/services/recon_engine.py` → FactCollector | `test_recon_engine.py` 驗證 fact 寫入 |
| `targets.os` 欄位更新 | 偵測到 OS 時 | `backend/app/routers/targets.py`（DB targets 表） | `test_recon_engine.py` 驗證 OS 更新 |
| Credential fact 寫入 | SSH 登入成功 | `backend/app/services/initial_access_engine.py` → facts 表 | `test_initial_access_engine.py` |
| WebSocket `fact.new` 事件廣播 | 每筆 fact 寫入時 | 前端即時更新 | E2E 驗證（`frontend/e2e/full-workflow.spec.ts`） |
| Seed 新增 4 筆技術 | `demo_scenario.py` 執行 | `backend/app/seed/demo_scenario.py` | `make test` 迴歸 |

---

## Rollback Plan

| 回滾步驟 | 資料影響 | 回滾驗證 | 回滾已測試 |
|----------|----------|----------|------------|
| 1. `git revert` Phase 12 commit，移除 recon/initial_access 模組 | `recon_scans` 表資料遺失（可重建） | `make test` 全通過；既有 OODA 流程不受影響 | 是 |
| 2. DROP TABLE `recon_scans` | 掃描歷史遺失 | DB migration rollback | 是 |
| 3. 移除 `python-nmap` / `asyncssh` 依賴 | 無 | `pip install -e .` 成功 | 是 |
| 4. 還原 `demo_scenario.py` 移除新增 techniques | 4 筆 seed 技術消失 | seed 重跑後 techniques 表正常 | 是 |

---

## 測試矩陣（Test Matrix）

| ID | 類型 | 場景 | 輸入 | 預期結果 | 場景參照 |
|----|------|------|------|----------|----------|
| P1 | 正向 | Mock 模式 recon scan 回傳 3 個服務 | `POST /recon/scan` + `MOCK_CALDERA=true` | `services_found=3`, facts 含 `service.open_port` | S1 |
| P2 | 正向 | Mock SSH 登入成功寫入 credential fact | `enable_initial_access=true` + mock | `initial_access.success=true`, credential fact 已寫入 | S1 |
| N1 | 負向 | Operation 不存在 | `POST /recon/scan` + 無效 op_id | 404 + `"Operation not found"` | S2 |
| N2 | 負向 | SSH port 未開放 | target 無 port 22 | `initial_access.success=false`, `method="none"` | S2 |
| B1 | 邊界 | nmap 超時 5 分鐘 | 極慢目標 | 中斷並回傳已收集結果（partial） | S3 |
| B2 | 邊界 | 同一 target 重複掃描 | 連續兩次 POST /recon/scan | 新增第二筆 recon_scans；facts 不重複（INSERT OR IGNORE） | S3 |

---

## 驗收場景（Acceptance Scenarios）

```gherkin
Feature: Phase 12 Recon 與 Initial Access Kill Chain

  Background:
    Given 後端服務已啟動（MOCK_CALDERA=true）
    And 作戰 "op-0001" 已建立
    And target "target-001" 已加入作戰且 IP 為 "192.168.1.100"

  Scenario: S1 — Mock 模式下完整 recon + initial access 流程
    When 發送 POST /api/operations/op-0001/recon/scan with target_id="target-001"
    Then 回傳 200 且 status 為 "completed"
    And services_found 為 3
    And facts_written 大於 0
    And initial_access.success 為 true
    And initial_access.credential 為 "msfadmin:msfadmin"
    And GET /api/operations/op-0001/facts 包含 "service.open_port" trait

  Scenario: S2 — Target 不存在時回傳 404
    When 發送 POST /api/operations/op-0001/recon/scan with target_id="nonexistent"
    Then 回傳 404
    And response body 包含 "Target not found"

  Scenario: S3 — 重複掃描同一 target 不產生重複 facts
    Given target "target-001" 已執行過一次 recon scan
    When 再次發送 POST /api/operations/op-0001/recon/scan with target_id="target-001"
    Then 回傳 200 且新增一筆 recon_scans 記錄
    And facts 表中 service.open_port 的 target-001 記錄無重複
```

---

## 追溯性（Traceability）

| 項目 | 路徑 / 識別碼 | 狀態 |
|------|---------------|------|
| 規格文件 | `docs/specs/SPEC-019-phase-12-recon--initial-access--kill-chain-.md` | Done |
| 關聯 ADR | `docs/adr/ADR-015` | Accepted |
| ReconEngine | `backend/app/services/recon_engine.py` | 已實作 |
| InitialAccessEngine | `backend/app/services/initial_access_engine.py` | 已實作 |
| Recon Router | `backend/app/routers/recon.py` | 已實作 |
| Recon Models | `backend/app/models/recon.py` | 已實作 |
| Demo Scenario Seed | `backend/app/seed/demo_scenario.py` | 已更新 |
| 單元測試 — Recon | `backend/tests/test_recon_engine.py` | 通過 |
| 單元測試 — Initial Access | `backend/tests/test_initial_access_engine.py` | 通過 |
| Router 測試 | `backend/tests/test_recon_router.py` | 通過 |
| MCP 整合測試 | `backend/tests/test_recon_mcp_integration.py` | 通過 |
| 更新日期 | 2026-03-26 | — |

---

## 可觀測性（Observability）

| 面向 | 內容 |
|------|------|
| **指標（Metrics）** | `recon.scan.duration_seconds`（histogram）、`recon.scan.services_found`（histogram）、`recon.scan.success_total` / `recon.scan.error_total`（counter）、`initial_access.attempt_total`（counter, label: method=ssh/none）、`initial_access.success_total`（counter） |
| **日誌（Logs）** | Recon scan 開始/完成（含 target IP、duration）、nmap 命令與參數、SSH 登入嘗試（含 credential pair，密碼遮罩）、Caldera agent 部署結果、fact 寫入筆數 |
| **告警（Alerts）** | nmap scan 超過 5 分鐘（timeout）、SSH 登入全部失敗（所有 credential pair 耗盡）、recon_scans 狀態停留 pending 超過 10 分鐘 |
| **故障偵測（Fault Detection）** | `nmap.PortScannerError` 偵測（nmap 未安裝或權限不足）、asyncssh 連線異常（網路不可達 vs 認證失敗 分類）、fact 寫入失敗（DB constraint error） |
