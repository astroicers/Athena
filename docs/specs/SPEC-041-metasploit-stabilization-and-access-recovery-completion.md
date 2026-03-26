# SPEC-041：Metasploit Stabilization & Access Recovery Completion

> 結構完整的規格書讓 AI 零確認直接執行。

| 欄位 | 內容 |
|------|------|
| **規格 ID** | SPEC-041 |
| **關聯 ADR** | ADR-033 |
| **前置 SPEC** | SPEC-037（Phase 1-3 已完成，本 SPEC 為其延伸） |
| **估算複雜度** | M（Metasploit S + Recovery M） |

---

## 目標（Goal）

> 完成兩項尚未解決的技術債：(1) 替換 `metasploit_client.py` 中的 `await asyncio.sleep(2)` magic number 為具有指數退避的 shell 輸出讀取機制，並新增 session health check；(2) 延伸 `_handle_access_lost()` 為三階段存取恢復流程（targeted re-scan、alternative protocol、pivot discovery），將結果以 fact 形式寫入供 Orient 階段 AI 推薦。

---

## 輸入規格（Inputs）

### 4.4 Metasploit Shell Interaction

| 參數名稱 | 型別 | 來源 | 限制條件 |
|----------|------|------|----------|
| shell | ShellSession | `client.sessions.session(sid)` | Metasploit RPC session 物件 |
| command | str | 呼叫端 | 要在 shell 中執行的指令（如 `id\n`） |

**指數退避參數：**

| 參數 | 值 | 說明 |
|------|----|------|
| `start_interval` | 0.3s | 首次 poll 間隔 |
| `backoff_factor` | 2 | 每次退避倍率 |
| `max_interval` | 5.0s | 最大 poll 間隔上限 |
| `timeout` | 15s | 整體讀取超時 |

### 4.8 Access Recovery

| 參數名稱 | 型別 | 來源 | 限制條件 |
|----------|------|------|----------|
| operation_id | str (UUID) | operations | 當前 operation |
| target_id | str (UUID) | targets | 失去存取的 target |
| target_ip | str | targets.ip_address | 目標 IP |
| db | aiosqlite.Connection | — | 資料庫連線 |

---

## 輸出規格（Expected Output）

### 4.4 — `_read_shell_output()` 回傳

| 條件 | 回傳值 |
|------|--------|
| 正常讀取到 shell 輸出 | `str`（完整 output） |
| Prompt 偵測（`$`, `#`, `>`） | 提前結束讀取，回傳已累積 output |
| 連續空讀 >=2 次（在已有 output 之後） | 判定輸出完成，回傳已累積 output |
| 超時（15s） | 回傳已累積的部分 output（可能為空字串） |

### 4.4 — `_check_session_health()` 回傳

| 條件 | 回傳值 |
|------|--------|
| session_id 存在於 `sessions.list` 且 type 為 `shell` 或 `meterpreter` | `True` |
| session_id 不存在或 type 不匹配 | `False` |

### 4.8 — Access Recovery Facts 產出

| Phase | 觸發條件 | 寫入的 fact trait | fact value 格式 |
|-------|----------|-------------------|-----------------|
| Phase 1 | access.lost 觸發後 | `access.recovery_candidate` | `rescan:{target_ip}:ports={open_ports}` |
| Phase 2 | SSH 失敗 | `access.alternative_available` | `{protocol}:{target_ip}:{port}` |
| Phase 3 | 有其他已 compromised 主機 | `access.pivot_candidate` | `pivot:{source_ip}->{target_ip}:via={service}` |

---

## 實作細節（Implementation）

### 4.4 Metasploit Shell Interaction — 指數退避 Polling

#### 修改檔案

`backend/app/clients/metasploit_client.py`

#### `_read_shell_output()` 完整實作

```python
async def _read_shell_output(
    self,
    shell: Any,
    *,
    start_interval: float = 0.3,
    backoff_factor: float = 2.0,
    max_interval: float = 5.0,
    timeout: float = 15.0,
) -> str:
    """Read shell output with exponential backoff polling.

    Replaces fixed `await asyncio.sleep(2)` with adaptive polling that:
    - Starts fast (0.3s) to catch quick responses
    - Backs off exponentially (*2) up to max_interval (5.0s) for slow commands
    - Detects prompt characters ($, #, >) as output-complete signal
    - Treats 2+ consecutive empty reads (after receiving output) as done
    - Hard timeout at 15s to prevent indefinite blocking
    """
    import time

    accumulated = ""
    interval = start_interval
    consecutive_empty = 0
    has_output = False
    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
        await asyncio.sleep(interval)

        chunk = await asyncio.get_running_loop().run_in_executor(
            None, shell.read
        )

        if chunk:
            accumulated += chunk
            has_output = True
            consecutive_empty = 0
            # Reset interval on new data for responsive reading
            interval = start_interval

            # Prompt detection: output ends with shell prompt
            stripped = accumulated.rstrip()
            if stripped and stripped[-1] in ('$', '#', '>'):
                logger.debug("Prompt detected, output complete (%d chars)", len(accumulated))
                break
        else:
            consecutive_empty += 1
            if has_output and consecutive_empty >= 2:
                logger.debug(
                    "2 consecutive empty reads after output, done (%d chars)",
                    len(accumulated),
                )
                break
            # Exponential backoff on empty reads
            interval = min(interval * backoff_factor, max_interval)

    if time.monotonic() >= deadline:
        logger.warning(
            "Shell read timed out after %.1fs (%d chars accumulated)",
            timeout, len(accumulated),
        )

    return accumulated
```

#### `_check_session_health()` 完整實作

```python
async def _check_session_health(
    self,
    client: Any,
    session_id: str,
) -> bool:
    """Verify session is alive before executing commands.

    Checks:
    1. session_id exists in client.sessions.list
    2. Session type is 'shell' or 'meterpreter'

    Returns True if session is healthy, False otherwise.
    """
    try:
        sessions = await asyncio.get_running_loop().run_in_executor(
            None, lambda: client.sessions.list
        )
    except Exception:
        logger.warning("Failed to query Metasploit sessions list")
        return False

    if session_id not in sessions:
        logger.warning("Session %s not found in sessions list", session_id)
        return False

    session_info = sessions[session_id]
    session_type = session_info.get("type", "")
    if session_type not in ("shell", "meterpreter"):
        logger.warning(
            "Session %s has unexpected type '%s' (expected shell/meterpreter)",
            session_id, session_type,
        )
        return False

    return True
```

#### `_run_exploit()` 修改差異

現有程式碼中兩處 `await asyncio.sleep(2)` + `shell.read()` 改為：

```python
# Before (line 107-108, session reuse path):
shell.write("id\n")
await asyncio.sleep(2)
output = shell.read()

# After:
if not await self._check_session_health(client, sid):
    logger.warning("Session %s is unhealthy, skipping reuse", sid)
    continue  # fall through to launch new exploit
shell.write("id\n")
output = await self._read_shell_output(shell)
```

```python
# Before (line 134-136, new session path):
shell.write("id\n")
await asyncio.sleep(2)
output = shell.read()

# After:
shell.write("id\n")
output = await self._read_shell_output(shell)
```

---

### 4.8 Access Recovery Completion — 三階段恢復

#### 修改檔案

`backend/app/services/engine_router.py`

#### 整合進 `_handle_access_lost()`

在現有 `_handle_access_lost()` 結尾（`await db.commit()` 之後）呼叫三階段恢復：

```python
# 在 _handle_access_lost 的 await db.commit() 之後新增：
await self._recovery_phase1_rescan(db, operation_id, target_id, target_ip)
await self._recovery_phase2_alt_protocol(db, operation_id, target_id, target_ip)
await self._recovery_phase3_pivot(db, operation_id, target_id, target_ip)
```

#### Phase 1 — Targeted Re-scan

```python
async def _recovery_phase1_rescan(
    self,
    db: aiosqlite.Connection,
    operation_id: str,
    target_id: str,
    target_ip: str | None,
) -> None:
    """Phase 1: Re-scan lost target to discover new open ports/services.

    Writes `access.recovery_candidate` fact with current open ports
    for Orient to evaluate.
    """
    if not target_ip:
        return

    # Collect currently known open ports for this target
    cursor = await db.execute(
        "SELECT value FROM facts "
        "WHERE operation_id = ? AND source_target_id = ? "
        "AND trait = 'service.open_port'",
        (operation_id, target_id),
    )
    rows = await cursor.fetchall()
    if not rows:
        return

    # Extract port numbers from service.open_port values
    # Format: "22/tcp:ssh:OpenSSH_6.6.1p1" -> "22"
    ports = []
    for row in rows:
        val = row["value"] if isinstance(row, dict) else row[0]
        port_part = val.split("/")[0] if "/" in val else val.split(":")[0]
        if port_part.isdigit():
            ports.append(port_part)

    if not ports:
        return

    fact_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    try:
        await db.execute(
            "INSERT OR IGNORE INTO facts "
            "(id, trait, value, category, source_target_id, operation_id, score, collected_at) "
            "VALUES (?, 'access.recovery_candidate', ?, 'host', ?, ?, 1, ?)",
            (fact_id, f"rescan:{target_ip}:ports={','.join(ports)}",
             target_id, operation_id, now),
        )
        await db.commit()
    except Exception:
        logger.debug("recovery_candidate fact already exists for %s", target_id)
```

#### Phase 2 — Alternative Protocol Check

```python
async def _recovery_phase2_alt_protocol(
    self,
    db: aiosqlite.Connection,
    operation_id: str,
    target_id: str,
    target_ip: str | None,
) -> None:
    """Phase 2: Check for alternative access protocols when SSH fails.

    Looks for WinRM (5985), SSH Key, SMB (445) availability in existing
    facts. Writes `access.alternative_available` fact.
    """
    if not target_ip:
        return

    # Map of alternative protocols: (search_pattern_in_port, protocol_name, default_port)
    _ALT_CHECKS: list[tuple[str, str, str]] = [
        ("5985", "winrm", "5985"),
        ("445", "smb", "445"),
        ("5986", "winrm_ssl", "5986"),
    ]

    cursor = await db.execute(
        "SELECT value FROM facts "
        "WHERE operation_id = ? AND source_target_id = ? "
        "AND trait = 'service.open_port'",
        (operation_id, target_id),
    )
    port_rows = await cursor.fetchall()
    port_values = [
        (r["value"] if isinstance(r, dict) else r[0]) for r in port_rows
    ]

    now = datetime.now(timezone.utc).isoformat()

    for search_pattern, protocol, default_port in _ALT_CHECKS:
        for pv in port_values:
            if search_pattern in pv.split("/")[0]:
                fact_id = str(uuid.uuid4())
                try:
                    await db.execute(
                        "INSERT OR IGNORE INTO facts "
                        "(id, trait, value, category, source_target_id, "
                        "operation_id, score, collected_at) "
                        "VALUES (?, 'access.alternative_available', ?, 'host', ?, ?, 1, ?)",
                        (fact_id, f"{protocol}:{target_ip}:{default_port}",
                         target_id, operation_id, now),
                    )
                except Exception:
                    pass
                break  # one match per protocol is enough

    # Also check for SSH key credential (not invalidated)
    key_cursor = await db.execute(
        "SELECT value FROM facts "
        "WHERE operation_id = ? AND source_target_id = ? "
        "AND trait = 'credential.ssh_key'",
        (operation_id, target_id),
    )
    key_row = await key_cursor.fetchone()
    if key_row:
        fact_id = str(uuid.uuid4())
        try:
            await db.execute(
                "INSERT OR IGNORE INTO facts "
                "(id, trait, value, category, source_target_id, "
                "operation_id, score, collected_at) "
                "VALUES (?, 'access.alternative_available', ?, 'host', ?, ?, 1, ?)",
                (fact_id, f"ssh_key:{target_ip}:22",
                 target_id, operation_id, now),
            )
        except Exception:
            pass

    await db.commit()
```

#### Phase 3 — Pivot Discovery

```python
async def _recovery_phase3_pivot(
    self,
    db: aiosqlite.Connection,
    operation_id: str,
    target_id: str,
    target_ip: str | None,
) -> None:
    """Phase 3: Find other compromised hosts that could pivot to the lost target.

    Looks for targets with:
    - is_compromised = 1 AND access_status = 'active'
    - Lateral movement capability (root/sudo privilege or meterpreter session)

    Writes `access.pivot_candidate` fact.
    """
    if not target_ip:
        return

    cursor = await db.execute(
        "SELECT id, ip_address, privilege_level FROM targets "
        "WHERE operation_id = ? AND is_compromised = 1 "
        "AND access_status = 'active' AND id != ?",
        (operation_id, target_id),
    )
    pivot_hosts = await cursor.fetchall()

    if not pivot_hosts:
        return

    now = datetime.now(timezone.utc).isoformat()

    for host in pivot_hosts:
        host_id = host["id"] if isinstance(host, dict) else host[0]
        host_ip = host["ip_address"] if isinstance(host, dict) else host[1]
        host_priv = host["privilege_level"] if isinstance(host, dict) else host[2]

        if not host_ip:
            continue

        # Only consider hosts with elevated privilege (lateral movement capability)
        if host_priv and host_priv.lower() in ("root", "sudo", "system", "administrator"):
            # Check if pivot host has root shell (e.g. Metasploit session)
            svc_cursor = await db.execute(
                "SELECT value FROM facts "
                "WHERE operation_id = ? AND source_target_id = ? "
                "AND trait = 'credential.root_shell'",
                (operation_id, host_id),
            )
            shell_row = await svc_cursor.fetchone()
            via = "root_shell" if shell_row else "elevated_privilege"

            fact_id = str(uuid.uuid4())
            try:
                await db.execute(
                    "INSERT OR IGNORE INTO facts "
                    "(id, trait, value, category, source_target_id, "
                    "operation_id, score, collected_at) "
                    "VALUES (?, 'access.pivot_candidate', ?, 'host', ?, ?, 1, ?)",
                    (fact_id,
                     f"pivot:{host_ip}->{target_ip}:via={via}",
                     target_id, operation_id, now),
                )
            except Exception:
                pass

    await db.commit()
```

---

## 副作用與連動（Side Effects）

| 本功能的狀態變動 | 受影響的既有功能 | 預期行為 |
|-----------------|----------------|---------|
| `asyncio.sleep(2)` 移除 | `_run_exploit()` session reuse + new session path | 使用 `_read_shell_output()` 替代，最快 0.3s 回應、最慢 15s 超時 |
| `_check_session_health()` 新增 | session reuse 路徑 | 不健康的 session 跳過 reuse，改走 launch exploit 路徑 |
| `access.recovery_candidate` fact | Orient prompt observe_summary | AI 看到可恢復存取的候選目標與其已知開放 port |
| `access.alternative_available` fact | Orient prompt CREDENTIAL INTELLIGENCE | AI 看到替代通訊協定可用（WinRM、SMB、SSH Key） |
| `access.pivot_candidate` fact | Orient prompt 攻擊建議 | AI 推薦透過已控制主機進行橫向移動 |

---

## 邊界條件（Edge Cases）

### 4.4 Metasploit Shell

- **Case 1**：shell 已斷線，`shell.read()` 拋出例外 — `run_in_executor` 會捕獲，`_read_shell_output()` 由呼叫端的 `_run_exploit()` try/except 處理
- **Case 2**：指令輸出極大（>1MB） — 累積字串會佔用記憶體，但 pentest 場景下 `id` 等指令輸出不超過數 KB，風險低
- **Case 3**：Meterpreter session 的 read 行為不同 — `_check_session_health()` 接受 `meterpreter` type，但 `_read_shell_output()` 的 prompt 偵測（`$#>`）不適用；此情況下靠 consecutive empty reads 或 timeout 結束
- **Case 4**：`_check_session_health()` 成功但執行指令時 session 已斷線 — TOCTOU 競爭條件，由 `_run_exploit()` 外層 try/except 捕獲

### 4.8 Access Recovery

- **Case 5**：目標沒有任何 `service.open_port` fact — Phase 1 & Phase 2 直接 return，不寫入 fact
- **Case 6**：沒有其他已 compromised 主機 — Phase 3 直接 return
- **Case 7**：recovery fact 已存在（冪等） — 使用 `INSERT OR IGNORE` 避免 IntegrityError
- **Case 8**：多個 OODA 迭代連續觸發 access_lost — 三階段恢復冪等執行，不會產生重複 fact
- **Case 9**：Phase 2 發現替代協定後下一個 Orient 迭代推薦使用 — Orient 從 `access.alternative_available` fact 讀取，由 AI 決策是否嘗試

### 回退方案（Rollback Plan）

- **回退方式**：revert commit
- **不可逆評估**：完全可逆。新增的 `_read_shell_output()` / `_check_session_health()` 為純新增方法；recovery facts 為新 trait，移除後不影響既有功能
- **資料影響**：回退後已寫入的 `access.recovery_candidate` / `access.alternative_available` / `access.pivot_candidate` facts 殘留在 DB 中但不會被任何程式碼讀取，無副作用

---

## 驗收標準（Done When）

### Part A — Metasploit Shell Stabilization（複雜度 S）

- [ ] `_read_shell_output()` 方法存在於 `MetasploitRPCEngine`，參數預設值為 `start_interval=0.3, backoff_factor=2.0, max_interval=5.0, timeout=15.0`
- [ ] `_run_exploit()` 中不再有任何 `await asyncio.sleep(2)` 硬編碼
- [ ] `_check_session_health()` 在 session reuse 路徑中被呼叫；不健康的 session 跳過 reuse
- [ ] 單元測試：mock shell 回傳 3 次空、第 4 次回傳 `uid=0(root)` — `_read_shell_output()` 正確累積並回傳
- [ ] 單元測試：mock shell 回傳 `root@target#` — prompt 偵測提前結束
- [ ] 單元測試：mock shell 永遠回傳空 — 15s timeout 後回傳空字串
- [ ] 單元測試：`_check_session_health()` — session 存在且 type=shell — True
- [ ] 單元測試：`_check_session_health()` — session 不存在 — False
- [ ] 單元測試：`_check_session_health()` — session 存在但 type=unknown — False

### Part B — Access Recovery Completion（複雜度 M）

- [ ] `_recovery_phase1_rescan()` 存在，從 `service.open_port` facts 組裝 `access.recovery_candidate` fact
- [ ] `_recovery_phase2_alt_protocol()` 存在，檢查 WinRM(5985)、SMB(445)、SSH Key 可用性並寫入 `access.alternative_available` fact
- [ ] `_recovery_phase3_pivot()` 存在，查找同 operation 中 `is_compromised=1 AND access_status='active'` 的其他主機，寫入 `access.pivot_candidate` fact
- [ ] `_handle_access_lost()` 在現有邏輯後呼叫三個 phase 方法
- [ ] 單元測試：觸發 access_lost — DB 中出現 `access.recovery_candidate` fact
- [ ] 單元測試：target 有 5985 port — DB 中出現 `access.alternative_available` = `winrm:{ip}:5985`
- [ ] 單元測試：target 有 `credential.ssh_key` fact — DB 中出現 `access.alternative_available` = `ssh_key:{ip}:22`
- [ ] 單元測試：同 operation 有另一台 root shell 主機 — DB 中出現 `access.pivot_candidate` fact
- [ ] 單元測試：同 operation 沒有其他 compromised 主機 — 不寫入 pivot fact
- [ ] 單元測試：重複觸發 `_handle_access_lost()` — 不產生重複 fact（INSERT OR IGNORE）
- [ ] `make test` 全數通過

---

## 禁止事項（Out of Scope）

- 不要實作主動 Health Check（OODA Observe 階段的 probe — ADR-033 已排除）
- 不要實際執行 nmap rescan（Phase 1 僅從現有 facts 收集資訊；真正的 rescan 由下一個 OODA Observe 階段自動執行）
- 不要自動執行 pivot（Phase 3 僅寫入 fact，由 Orient AI 決策是否執行橫向移動）
- 不要修改 facts 表 schema
- 不要引入新依賴

---

## 檔案變更清單

| 檔案 | 變更類型 | 說明 |
|------|----------|------|
| `backend/app/clients/metasploit_client.py` | 修改 | 新增 `_read_shell_output()`、`_check_session_health()`；修改 `_run_exploit()` 移除 `sleep(2)` |
| `backend/app/services/engine_router.py` | 修改 | 新增 `_recovery_phase1_rescan()`、`_recovery_phase2_alt_protocol()`、`_recovery_phase3_pivot()`；修改 `_handle_access_lost()` 呼叫三階段 |
| `backend/tests/test_metasploit_shell.py` | 新增 | `_read_shell_output()` 和 `_check_session_health()` 的單元測試 |
| `backend/tests/test_access_recovery_phases.py` | 新增 | 三階段 recovery 的單元測試 |

---

## 參考資料（References）

- 相關 ADR：ADR-033（Access Recovery 決策）、ADR-003（OODA loop 架構）、ADR-019（Metasploit RPC）
- 前置 SPEC：SPEC-037（Phase 1-3 已完成，本 SPEC 延伸其範圍）
- 關鍵檔案：
  - `backend/app/clients/metasploit_client.py` — 現有 `_run_exploit()` 含 `sleep(2)` magic number（line 107, 135）
  - `backend/app/services/engine_router.py` — 現有 `_handle_access_lost()`（line 517-562）
  - `backend/tests/test_access_recovery.py` — 既有 26 個 access recovery 測試

<!-- tech-debt: scenario-pending — v3.2 upgrade: needs test matrix + Gherkin scenarios -->
<!-- tech-debt: observability-pending — v3.3 upgrade: needs observability section -->
