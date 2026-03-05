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
