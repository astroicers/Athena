# SPEC-056：Multi-Protocol Credential Spray Extension

> 結構完整的規格書讓 AI 零確認直接執行。

| 欄位 | 內容 |
|------|------|
| **規格 ID** | SPEC-056 |
| **關聯 ADR** | （無新 ADR——泛化 protocol map 架構已存在於 InitialAccessEngine） |
| **估算複雜度** | 中 |
| **建議模型** | Opus |
| **HITL 等級** | minimal |

---

## 🎯 目標（Goal）

擴充 `InitialAccessEngine._PROTOCOL_MAP` 支援 MySQL(3306)、PostgreSQL(5432)、FTP(21) 三個協議的 credential spray，讓 OODA 在 SSH brute force 失敗 + reverse shell exploit 不通（無 relay）時，能**自主 pivot 到其他 credential-based 服務**完成滲透。

解決 metasploitable2 demo 中「所有攻擊路徑封死」的問題——SSH 密碼被改、vsftpd 僵屍、samba reverse shell 無 relay。MySQL root 無密碼和 PostgreSQL postgres 無密碼是 metasploitable2 的已知弱點，OODA 應能自動發現並利用。

---

## 📥 輸入規格（Inputs）

### 1. `protocol_map.yaml` 新增 entry

| port | service_keywords | protocol | mcp_tool | fact_trait | creds_key |
|------|-----------------|----------|----------|------------|-----------|
| 3306 | [mysql] | mysql | mysql_credential_check | credential.mysql | mysql |
| 5432 | [postgresql] | postgresql | postgresql_credential_check | credential.postgresql | postgresql |
| 21 | [ftp] | ftp | ftp_credential_check | credential.ftp | ftp |

### 2. `default_credentials.yaml` 新增 credential lists

| protocol | credentials | 來源 |
|----------|------------|------|
| mysql | root:空、root:root、root:password、mysql:mysql、admin:admin、dbadmin:dbadmin | metasploitable2 預設 + CTF 常見 |
| postgresql | postgres:空、postgres:postgres、postgres:password、admin:admin | metasploitable2 預設 + CTF 常見 |
| ftp | anonymous:空、anonymous:anonymous、ftp:ftp、root:root、admin:admin | RFC 匿名 + CTF 常見 |

### 3. MCP credential-checker 新增 3 個 tool

| tool name | handler | 依賴 | default port |
|-----------|---------|------|-------------|
| mysql_credential_check | pymysql | pymysql>=1.1.0 | 3306 |
| postgresql_credential_check | psycopg2 | psycopg2-binary>=2.9.0 | 5432 |
| ftp_credential_check | ftplib | 標準庫（零依賴） | 21 |

---

## 📤 輸出規格（Expected Output）

**MySQL 成功：**
```json
{"facts": [{"trait": "credential.mysql", "value": "root:@192.168.0.26:3306 (version: 5.0.51a, user: root@%)"}], "raw_output": "MySQL auth success: root@192.168.0.26:3306"}
```

**PostgreSQL 成功：**
```json
{"facts": [{"trait": "credential.postgresql", "value": "postgres:@192.168.0.26:5432 (version: 8.3.7, user: postgres)"}], "raw_output": "PostgreSQL auth success: postgres@192.168.0.26:5432"}
```

**FTP 成功：**
```json
{"facts": [{"trait": "credential.ftp", "value": "anonymous:@192.168.0.26:21 (syst: UNIX)"}], "raw_output": "FTP auth success: anonymous@192.168.0.26:21"}
```

**任何協議失敗：**
```json
{"facts": [], "raw_output": "<PROTOCOL> auth_failure: <user>@<host>:<port>"}
```

---

## 🔗 副作用與連動（Side Effects）

| 副作用 | 觸發條件 | 影響的系統/模組 | 驗證方式 |
|--------|---------|----------------|----------|
| credential.mysql fact 寫入 DB | MySQL 認證成功 | facts table、Orient context Section 4 | DB query: `SELECT * FROM facts WHERE trait='credential.mysql'` |
| credential.postgresql fact 寫入 DB | PostgreSQL 認證成功 | 同上 | DB query |
| credential.ftp fact 寫入 DB | FTP 認證成功 | 同上 | DB query |
| Orient Rule #8 推薦範圍擴大 | 有 MySQL/PostgreSQL/FTP open port fact | Orient 推薦 T1110 targeting 新 protocol | Orient summary 檢查 |
| Orient Rule #9 新增 multi-protocol retry | SSH + T1190 都 fail | Orient 推薦重試 T1110 針對其他 protocol | Orient summary 檢查 |

---

## ⚠️ 邊界條件（Edge Cases）

- Case 1：MySQL 開了但不允許遠端 root 登入（`Host 'x.x.x.x' is not allowed`）→ auth_failure
- Case 2：PostgreSQL 的 `pg_hba.conf` 拒絕遠端連線 → connection refused / auth_failure
- Case 3：FTP 不支援 anonymous（530 Login incorrect）→ auth_failure
- Case 4：Port 開了但不是對應服務（例如 3306 是 honeypot）→ connection error / timeout
- Case 5：credential-checker MCP 容器沒有起來 → InitialAccessEngine log skip + continue

### 🔄 Rollback Plan

| 項目 | 說明 |
|------|------|
| **回滾步驟** | 還原 protocol_map.yaml、default_credentials.yaml、server.py。Rebuild credential-checker 容器 |
| **資料影響** | credential.mysql/postgresql/ftp facts 留在 DB 無害，不需清理 |
| **回滾驗證** | `make test` 通過 + 驗證 _PROTOCOL_MAP 只有 SSH/RDP/WinRM |
| **回滾已測試** | ☐ 否（新增功能，回滾 = 還原檔案） |

---

## 🧪 測試矩陣（Test Matrix）

| # | 類型 | 輸入條件 | 預期結果 | 對應場景 |
|---|------|---------|---------|---------|
| T01 | ✅ 正向 | protocol_map.yaml 載入 | 包含 mysql/postgresql/ftp entry | S1 |
| T02 | ✅ 正向 | default_credentials.yaml 載入 | 包含 mysql/postgresql/ftp key | S1 |
| T03 | ✅ 正向 | 服務 `3306/tcp/mysql/MySQL_5.0.51a` | protocol=mysql MATCH | S2 |
| T04 | ✅ 正向 | 服務 `5432/tcp/postgresql/PostgreSQL_8.3` | protocol=postgresql MATCH | S2 |
| T05 | ✅ 正向 | 服務 `21/tcp/ftp/vsftpd_2.3.4` | protocol=ftp MATCH | S2 |
| T06 | ✅ 正向 | Orient prompt text | 包含 MySQL/PostgreSQL/FTP | S3 |
| T07 | ✅ 正向 | SSH fail + T1190 fail context | Orient context 包含 auth_failure + exploit_failed | S3 |
| T08 | ✅ 正向 | MySQL handler 連線成功 | 回 credential.mysql fact | S4 |
| T09 | ❌ 負向 | MySQL handler 連線失敗 | 回空 facts | S5 |
| T10 | ✅ 正向 | PostgreSQL handler 連線成功 | 回 credential.postgresql fact | S4 |
| T11 | ❌ 負向 | PostgreSQL handler 連線失敗 | 回空 facts | S5 |
| T12 | ✅ 正向 | FTP handler anonymous 成功 | 回 credential.ftp fact | S4 |
| T13 | ❌ 負向 | FTP handler 連線失敗 | 回空 facts | S5 |

---

## 🎭 驗收場景（Acceptance Scenarios）

```gherkin
Feature: Multi-Protocol Credential Spray
  作為 Athena OODA 引擎
  我想要嘗試 MySQL/PostgreSQL/FTP credential spray
  以便在 SSH + reverse shell exploit 都失敗時仍能自主滲透目標

  Background:
    Given target 192.168.0.26 有 11 個 open port (nmap 掃描完成)
    And SSH brute force 已失敗 (failure_category=auth_failure)
    And T1190 Samba exploit 已失敗 (failure_category=exploit_failed, no relay)

  Scenario: S1 - Protocol map 包含新協議
    When 載入 protocol_map.yaml
    Then 包含 port=3306 protocol=mysql entry
    And 包含 port=5432 protocol=postgresql entry
    And 包含 port=21 protocol=ftp entry

  Scenario: S2 - InitialAccessEngine 正確匹配新協議
    Given services 包含 {port: 3306, service: "mysql"}
    When InitialAccessEngine.try_initial_access() 被呼叫
    Then 嘗試 mysql protocol 的 credential spray

  Scenario: S3 - Orient 推薦 multi-protocol credential retry
    Given 失敗記錄包含 T1110 [auth_failure] 和 T1190 [exploit_failed]
    And target 有 MySQL(3306) 和 PostgreSQL(5432) open
    When Orient 執行 situation assessment
    Then 推薦 T1110.001 targeting MySQL/PostgreSQL

  Scenario: S4 - MySQL credential spray 成功
    Given MySQL 允許 root 無密碼遠端登入
    When credential-checker 嘗試 mysql_credential_check(root, "")
    Then 回傳 credential.mysql fact
    And fact value 包含 MySQL version

  Scenario: S5 - MySQL credential spray 失敗
    Given MySQL 不允許 root 遠端登入
    When credential-checker 嘗試 mysql_credential_check(root, "")
    Then 回傳空 facts
    And raw_output 包含 "auth_failure"
```

---

## ✅ 驗收標準（Done When）

- [x] `make test` 全數通過（含 13 個新 test）
- [ ] 實機 OODA：Orient 自主推薦 MySQL/PostgreSQL credential spray（在 SSH + T1190 fail 之後）
- [ ] 實機 OODA：MySQL root 無密碼成功 → credential.mysql fact 寫入 → target compromised
- [ ] `make lint` 無 error

---

## 🔗 追溯性（Traceability）

| 實作檔案 | 測試檔案 | 最後驗證日期 |
|----------|----------|-------------|
| tools/credential-checker/server.py | tools/credential-checker/test_handlers.py | YYYY-MM-DD |
| backend/app/data/protocol_map.yaml | backend/tests/test_spec056_multi_protocol.py | YYYY-MM-DD |
| backend/app/data/default_credentials.yaml | backend/tests/test_spec056_multi_protocol.py | YYYY-MM-DD |
| backend/app/services/orient_engine.py | backend/tests/test_spec056_multi_protocol.py | YYYY-MM-DD |

---

## 📊 可觀測性（Observability）

| 面向 | 說明 |
|------|------|
| **關鍵指標** | credential spray 成功率 per protocol（從 technique_executions 統計） |
| **日誌** | INFO: `Protocol {protocol} credential spray: {success/fail} for {user}@{host}:{port}` |
| **告警** | credential-checker MCP 不可用時 WARN |
| **如何偵測故障** | Orient 推薦了 T1110 但 act_summary 顯示 "via none: failed" → protocol map 沒匹配 |

---

## 🚫 禁止事項（Out of Scope）

- 不加 VNC（graphical session，無法產生 shell fact）
- 不加 Telnet（需要 expect-style interactive handling，複雜度高）
- 不改 InitialAccessEngine 架構（已泛化，只填充 data）
- 不改 Orient Rules 的結構（只擴充 service 列表和 pivot 條件）
- 不改 DB schema（credential.mysql 等是新 fact trait，不需要 migration）

---

## 📎 參考資料（References）

- InitialAccessEngine 泛化設計：`backend/app/services/initial_access_engine.py` L14-15
- credential-checker handler registry：`tools/credential-checker/server.py` L30-47
- Orient Rules #8/#9：`backend/app/services/orient_engine.py` L209-274
- metasploitable2 已知弱點：MySQL root 無密碼、PostgreSQL postgres 無密碼、FTP anonymous
