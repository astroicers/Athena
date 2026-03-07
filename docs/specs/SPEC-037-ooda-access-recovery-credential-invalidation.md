# SPEC-037：OODA Access Recovery & Credential Invalidation

> 結構完整的規格書讓 AI 零確認直接執行。

| 欄位 | 內容 |
|------|------|
| **規格 ID** | SPEC-037 |
| **關聯 ADR** | ADR-033 |
| **估算複雜度** | 中 |

---

## 🎯 目標（Goal）

> 當 OODA Act 階段的 SSH 執行因認證失敗而失敗時，系統自動偵測存取中斷、標記憑證為失效、回退目標狀態，使後續迭代能正確切換至替代攻入路徑。

---

## 📥 輸入規格（Inputs）

| 參數名稱 | 型別 | 來源 | 限制條件 |
|----------|------|------|----------|
| result.error | string | ExecutionResult | SSH/MCP executor 回傳的錯誤訊息 |
| target_id | string (UUID) | technique_executions | 執行對象的 target ID |
| operation_id | string (UUID) | operations | 當前 operation ID |

**認證失敗關鍵字清單（觸發條件）：**

```python
_AUTH_FAILURE_KEYWORDS = [
    "authentication failed",
    "permission denied",
    "login incorrect",
    "access denied",
    "invalid credentials",
    "connection refused",
    "no route to host",
    "connection timed out",
    "host unreachable",
]
```

比對方式：`any(kw in (result.error or "").lower() for kw in _AUTH_FAILURE_KEYWORDS)`

---

## 📤 輸出規格（Expected Output）

**觸發 `_handle_access_lost()` 後的狀態變動：**

| 資料表 | 欄位 | 變更前 | 變更後 |
|--------|------|--------|--------|
| targets | is_compromised | 1 | 0 |
| targets | access_status | 'active' / 'unknown' | 'lost' |
| targets | privilege_level | 'User' / 'root' | NULL |
| facts | trait (credential) | 'credential.ssh' | 'credential.ssh.invalidated' |
| facts | (new row) | — | trait='access.lost', value='ssh_auth_failed:{target_ip}' |

**Orient Prompt 格式變更：**

```
# Before:
- target-001 (192.168.0.23) [server] OS=Linux COMPROMISED User

# After (access lost):
- target-001 (192.168.0.23) [server] OS=Linux ACCESS_LOST (was: User)
  ⚠ WARNING: Access lost — credential invalidated. Prioritize re-entry via alternative services.

# After (normal compromised):
- target-001 (192.168.0.23) [server] OS=Linux COMPROMISED(ACTIVE) User
```

---

## 🔗 副作用與連動（Side Effects）

| 本功能的狀態變動 | 受影響的既有功能 | 預期行為 |
|-----------------|----------------|---------|
| targets.is_compromised → 0 | DecisionEngine target 選擇 | 不再優先選擇已失去存取的 target |
| targets.access_status → 'lost' | Orient prompt targets 區塊 | 顯示 ACCESS_LOST 狀態 + 警告 |
| credential trait → invalidated | engine_router 憑證查詢 | 排除已失效憑證，避免重複使用 |
| credential trait → invalidated | Attack Graph fact_traits | 依賴該 credential 的節點回退為 UNREACHABLE |
| credential trait → invalidated | Orient categorized facts | 已失效的 credential 不再出現在 CREDENTIAL INTELLIGENCE |
| access.lost fact 插入 | Orient observe_summary | 提供 access lost 事件給 LLM 分析 |

---

## ⚠️ 邊界條件（Edge Cases）

- **Case 1**：同一 target 有多組 credential（ssh + winrm）— 只 invalidate 失敗的 trait 類型
- **Case 2**：網路暫時中斷（非密碼更改）— `connection refused` / `timed out` 也觸發 access_lost，但後續迭代重新取得存取時會自動恢復（`_mark_target_compromised` 會重設 is_compromised=1）
- **Case 3**：Swarm 並行執行中多個 task 同時認證失敗 — `_handle_access_lost` 需要冪等（多次呼叫結果相同）
- **Case 4**：target 重新取得存取（例如透過 vsftpd backdoor 拿到 root shell）— 現有 `_mark_target_compromised()` 會設回 `is_compromised=1`，需同時更新 `access_status='active'`

### 回退方案（Rollback Plan）

- **回退方式**：revert commit
- **不可逆評估**：此變更完全可逆。`access_status` 欄位有 DEFAULT 值，DROP 後不影響既有資料
- **資料影響**：回退後已 invalidated 的 credential trait 不會自動恢復，但可透過手動 SQL 修正

---

## ✅ 驗收標準（Done When）

- [ ] `_handle_access_lost()` 在 SSH 認證失敗時正確觸發
- [ ] 觸發後 `targets.is_compromised` = 0, `access_status` = 'lost'
- [ ] 觸發後 credential trait 改為 `credential.ssh.invalidated`
- [ ] `_execute_via_mcp_executor` 不使用 invalidated credential
- [ ] Orient prompt 顯示 `ACCESS_LOST` 狀態與警告
- [ ] Attack Graph 將依賴 invalidated credential 的節點標記為 UNREACHABLE
- [ ] 重新取得存取時 `access_status` 恢復為 'active'
- [ ] `make test` 全數通過
- [ ] 單元測試覆蓋所有邊界條件

---

## 🚫 禁止事項（Out of Scope）

- 不要實作主動 Health Check（已在 ADR-033 決策為被動偵測）
- 不要新增 facts 表的 `is_valid` 欄位
- 不要修改 OODA 迭代間隔或 Orient 的 JSON output schema
- 不要引入新依賴

---

## 📎 參考資料（References）

- 相關 ADR：ADR-033、ADR-003、ADR-004
- 現有類似實作：`_mark_target_compromised()` in engine_router.py
- 關鍵檔案：
  - `backend/app/services/engine_router.py` — 主要修改
  - `backend/app/services/orient_engine.py` — prompt 修改
  - `backend/app/services/attack_graph_engine.py` — fact 排除
  - `backend/app/models/enums.py` — AccessStatus enum
  - `backend/app/database.py` — DB migration
