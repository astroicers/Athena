# SPEC-057：PostgreSQL COPY-TO-PROGRAM Shell Escalation

> 結構完整的規格書讓 AI 零確認直接執行。

| 欄位 | 內容 |
|------|------|
| **規格 ID** | SPEC-057 |
| **關聯 ADR** | （無新 ADR——延伸 SPEC-056 multi-protocol 架構） |
| **估算複雜度** | 中 |
| **建議模型** | Opus |
| **HITL 等級** | minimal |

---

## 🎯 目標（Goal）

當 OODA 透過 SPEC-056 取得 PostgreSQL superuser credential 後，**自動嘗試 `COPY TO PROGRAM` 執行 OS 指令**，成功則寫入 `credential.shell` fact，正確觸發 compromise gate（`_SHELL_CAPABLE_TRAITS`）。

解決 metasploitable2 demo 的最後一哩路：SSH 密碼被改、reverse shell 無 relay、但 PostgreSQL `postgres` 帳號無密碼且為 superuser，可透過 `COPY ... TO PROGRAM 'id'` 取得 OS 指令執行能力。

---

## 📥 輸入規格（Inputs）

### 1. MCP credential-checker 新增 tool `postgresql_exec_check`

| 參數 | 型別 | 來源 | 說明 |
|------|------|------|------|
| target | string | InitialAccessEngine | 目標 IP |
| username | string | credential spray 結果 | PostgreSQL 使用者名 |
| password | string | credential spray 結果 | PostgreSQL 密碼（可為空） |
| port | int | protocol_map | 預設 5432 |
| command | string | 固定值 | `id`（驗證 OS exec 能力） |
| timeout | int | 預設 | 10 秒 |

### 2. InitialAccessEngine 觸發條件

在 `_try_mcp_credential_check` 成功（protocol=`postgresql`）後，**自動呼叫** `postgresql_exec_check` 嘗試 `COPY ... TO PROGRAM`。觸發條件：

- protocol == "postgresql"
- credential check 成功（有 `credential.postgresql` fact）
- credential value 包含 `postgres` username（最可能是 superuser）

---

## 📤 輸出規格（Expected Output）

**COPY TO PROGRAM 成功：**
```json
{
  "facts": [{
    "trait": "credential.shell",
    "value": "postgresql_copy_exec:postgres:@192.168.0.26:5432 (uid=0(root) gid=0(root))"
  }],
  "raw_output": "PostgreSQL COPY TO PROGRAM success: id → uid=0(root) gid=0(root)"
}
```

**COPY TO PROGRAM 失敗（非 superuser / 權限不足）：**
```json
{
  "facts": [],
  "raw_output": "PostgreSQL COPY TO PROGRAM denied: must be superuser to COPY to a file"
}
```

**fact trait 選擇**：使用 `credential.shell` — 已在 `_SHELL_CAPABLE_TRAITS` 中，compromise gate 自動觸發。不新增 trait，避免擴散。

---

## 🔗 副作用與連動（Side Effects）

| 副作用 | 觸發條件 | 影響的系統/模組 | 驗證方式 |
|--------|---------|----------------|----------|
| `credential.shell` fact 寫入 DB | COPY TO PROGRAM 成功 | facts table → compromise gate → target 標 compromised | DB query |
| target `is_compromised = TRUE` | `credential.shell` fact 存在 | OODA controller compromise gate | target API check |
| Terminal 可用 | 依賴 SSH credential（本 SPEC 不改 Terminal） | Terminal 仍需 SSH——但 `credential.shell` 提供了 psql 路徑（Phase 2） | 手動確認 |
| Orient 看到成功的 Initial Access | kill chain 從 TA0001 推進 | Orient 推薦 post-exploitation 技術 | Timeline 觀察 |

---

## ⚠️ 邊界條件（Edge Cases）

- Case 1：PostgreSQL 使用者不是 superuser → `COPY TO PROGRAM` 回 permission denied → 不寫 fact，不影響
- Case 2：PostgreSQL 版本 < 9.3（不支援 COPY TO PROGRAM）→ syntax error → 不寫 fact
- Case 3：credential-checker MCP 容器不在線 → skip，log warning
- Case 4：`id` 指令輸出為空 → 嘗試 `whoami` 作為 fallback
- Case 5：PostgreSQL 連線成功但 COPY 被 `pg_hba.conf` 限制 → auth error → 不寫 fact

### 🔄 Rollback Plan

| 項目 | 說明 |
|------|------|
| **回滾步驟** | 還原 server.py（移除 handler）+ initial_access_engine.py（移除 escalation call） |
| **資料影響** | credential.shell facts 留在 DB 無害 |
| **回滾驗證** | `make test` 通過 |

---

## 🧪 測試矩陣（Test Matrix）

| # | 類型 | 輸入條件 | 預期結果 | 對應場景 |
|---|------|---------|---------|---------|
| T01 | ✅ 正向 | PostgreSQL superuser + COPY TO PROGRAM 成功 | credential.shell fact 寫入 | S1 |
| T02 | ❌ 負向 | PostgreSQL non-superuser + COPY TO PROGRAM 被拒 | 空 facts | S2 |
| T03 | ❌ 負向 | PostgreSQL 版本不支援 COPY TO PROGRAM | 空 facts | S2 |
| T04 | ✅ 正向 | InitialAccessEngine credential 成功後觸發 exec check | postgresql_exec_check 被呼叫 | S3 |
| T05 | ❌ 負向 | credential-checker MCP 不在線 | skip + log warning | S4 |
| T06 | ✅ 正向 | credential.shell fact → compromise gate 觸發 | target is_compromised=TRUE | S5 |
| T07 | 🔶 邊界 | id 指令回空 + whoami fallback | 仍然寫 credential.shell | S1 |

---

## 🎭 驗收場景（Acceptance Scenarios）

```gherkin
Feature: PostgreSQL COPY TO PROGRAM Shell Escalation
  作為 Athena OODA 引擎
  我想要在取得 PostgreSQL superuser credential 後自動嘗試 OS exec
  以便正確判定 target 已被 compromised

  Background:
    Given target 192.168.0.26 有 PostgreSQL 5432 開放
    And PostgreSQL postgres 帳號無密碼（superuser）

  Scenario: S1 - COPY TO PROGRAM 成功取得 shell
    Given credential-checker 已連線
    When InitialAccessEngine 取得 credential.postgresql fact
    And postgresql_exec_check("id") 成功回傳 uid 資訊
    Then 寫入 credential.shell fact
    And target is_compromised = TRUE

  Scenario: S2 - COPY TO PROGRAM 被拒（非 superuser）
    Given PostgreSQL 使用者不是 superuser
    When postgresql_exec_check 嘗試 COPY TO PROGRAM
    Then 回傳空 facts
    And target 維持 is_compromised = FALSE

  Scenario: S3 - InitialAccessEngine 自動觸發 exec check
    Given PostgreSQL credential spray 成功
    When _try_mcp_credential_check 回傳 success
    Then 自動呼叫 postgresql_exec_check
    And 不需要額外 OODA cycle

  Scenario: S4 - credential-checker MCP 不在線
    Given credential-checker 容器停機
    When InitialAccessEngine 嘗試 postgresql_exec_check
    Then skip 並 log warning
    And 不影響 credential.postgresql fact

  Scenario: S5 - Compromise gate 正確觸發
    Given credential.shell fact 已寫入
    When OODA controller 執行 compromise gate check
    Then _SHELL_CAPABLE_TRAITS 匹配 credential.shell
    And target is_compromised = TRUE, access_status = active
```

---

## ✅ 驗收標準（Done When）

- [ ] `make test` 全數通過（含新 test）
- [ ] 實機 OODA：PostgreSQL credential 成功 → COPY TO PROGRAM 成功 → credential.shell fact → compromised
- [ ] `make lint` 無 error
- [ ] CHANGELOG 已更新

---

## 🔗 追溯性（Traceability）

| 實作檔案 | 測試檔案 | 最後驗證日期 |
|----------|----------|-------------|
| tools/credential-checker/server.py | backend/tests/test_spec057_pg_shell.py | YYYY-MM-DD |
| backend/app/services/initial_access_engine.py | backend/tests/test_spec057_pg_shell.py | YYYY-MM-DD |

---

## 📊 可觀測性（Observability）

| 面向 | 說明 |
|------|------|
| **關鍵指標** | COPY TO PROGRAM 成功/失敗率 |
| **日誌** | WARNING: `PostgreSQL COPY TO PROGRAM: {success/denied} for {user}@{host}:{port}` |
| **告警** | 無（非關鍵路徑，失敗只是不升級） |
| **如何偵測故障** | credential.postgresql 存在但 credential.shell 不存在 → COPY 失敗 |

---

## 🚫 禁止事項（Out of Scope）

- 不改 Terminal router（本 SPEC 只做 credential escalation，不做 psql interactive shell）
- 不改 compromise gate（已在 `_SHELL_CAPABLE_TRAITS` 中包含 `credential.shell`）
- 不改 Orient prompt（Orient 已知道 credential.shell 的語意）
- 不新增 DB migration（credential.shell 是普通 fact trait）
- 不加 MySQL COPY 等價能力（MySQL 沒有直接 OS exec 功能，需要 UDF，複雜度太高）

---

## 📎 參考資料（References）

- PostgreSQL COPY TO PROGRAM 文件：https://www.postgresql.org/docs/current/sql-copy.html
- `_SHELL_CAPABLE_TRAITS`：`backend/app/services/ooda_controller.py` L45-55
- SPEC-056：Multi-Protocol Credential Spray Extension
- metasploitable2 PostgreSQL 預設設定：postgres superuser 無密碼 + `pg_hba.conf` trust