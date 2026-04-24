# Athena 自動打穿靶場 — Playbook

> **場景**：零先驗知識，給 Athena 一個 CIDR，讓它自己找出 `corp.athena.lab` 並拿到 domain credential
> **預計時間**：10-30 分鐘（視 LLM 反應速度）
> **前置**：靶場 S3-clean-vulnerable 快照已就位，見 [LAB_MANUAL.md](LAB_MANUAL.md)

---

## 快速表

| Step | 動作 | 時間 |
|------|------|------|
| 0 | VMware 還原 S3 + verify-lab.sh 14/14 PASS | 2 分 |
| 1 | `docker compose --profile mcp up -d` | 30 秒 |
| 2 | UI → New Operation | 1 分 |
| 3 | UI → Batch Import Targets `192.168.0.0/24` | 30 秒 |
| 4 | 盯 UI OODA 分頁 | 10-30 分 |
| 5 | SQL 驗證 credential.* fact | 10 秒 |

---

## Step 0 — 前置

```bash
# WSL
export PATH="$HOME/.local/bin:$PATH"
export OPENSSL_CONF=/tmp/openssl-legacy.cnf
cd /home/ubuntu/Athena
./scripts/verify-lab.sh
# 確認 14/14 PASS
```

若還沒設 DNS：
```bash
sudo cp /etc/resolv.conf /etc/resolv.conf.bak-20260424
sudo tee /etc/resolv.conf > /dev/null <<'EOF'
nameserver 192.168.0.16
nameserver 8.8.8.8
nameserver 1.1.1.1
search corp.athena.lab
EOF
```

---

## Step 1 — 啟動 Athena

```bash
cd /home/ubuntu/Athena
docker compose --profile mcp up -d
sleep 30
docker compose ps | awk '$4=="Up" || /STATUS/' | head -30
```

瀏覽：**http://localhost:58080**

---

## Step 2 — 建立 Operation

UI 左側 → **Operations** → 右上 **+ New Operation**：

| 欄位 | 值 |
|------|----|
| Code | `LAB-001` |
| Name | `Athena AD Lab Autonomous Attack` |
| Codename | `PHANTOM` |
| Strategic Intent | `Obtain domain credentials from corp.athena.lab via autonomous OODA. Start from CIDR 192.168.0.0/24 with zero prior knowledge.` |
| Mission Profile | `SP` |

Submit → 記下 `op_id`（URL 上的 UUID）。

---

## Step 3 — Batch Import Targets

點 operation 進詳細頁 → **Targets** → **+ Batch Import**：

```
192.168.0.0/24
```

Submit → Athena 自動展開 CIDR 成 254 個 target → **2 秒後 OODA 自動觸發**。

---

## Step 4 — 盯 OODA 跑

### UI 要看的三處

| UI 位置 | 作用 |
|---------|------|
| Operation → **OODA** 分頁 | iteration 卡片，每張 4 phase（O/O/D/A） |
| Operation → **Facts** 分頁 | 累積的事實（開始空 → credential.* → 成功） |
| Operation → **Timeline** 分頁 | WebSocket 即時事件流 |

### 預期 iteration 順序

```
#1 [Observe] auto-recon -> nmap_scan 192.168.0.0/24
   [Orient]  LLM 看到 port 389/445/88 -> 推薦 T1018 或 T1046
   [Decide]  auto_approved (low risk)
   [Act]     nmap-scanner 回: .16/.20/.23 alive
   -> facts: service.smb, service.ldap, service.kerberos on 192.168.0.16

#2 [Observe] DC signature (port 88 + 389 on .16)
   [Orient]  LLM -> T1110.003 password spray
   [Decide]  auto_approved (medium, below threshold)
   [Act]     netexec password_spray 'steve' / Summer2024!, Welcome1, ...
   -> fact: credential.domain_user: CORP\steve:Summer2024!      <-- 成功！

#3 [Observe] 有 credential
   [Orient]  LLM -> T1087.002 BloodHound 全域枚舉
   [Act]     bloodhound-collector -> users/computers/trust paths
   -> +30 facts 包含 legacy_kev flagged AS-REP

#4 [Observe] AS-REP flag
   [Orient]  LLM -> T1558.004
   [Act]     GetNPUsers -> $krb5asrep$legacy_kev hash
   -> fact: credential.asrep_hash
```

**看到 `credential.domain_user` 或 `credential.asrep_hash` 就算成功**（用戶定義最低標）。

---

## Step 5 — SQL 驗證

```bash
# 查所有 credential facts
docker exec athena-postgres-1 psql -U athena -d athena -c "
SELECT created_at, trait, substring(value, 1, 80) as value
FROM facts
WHERE operation_id = (SELECT id FROM operations WHERE code = 'LAB-001')
  AND trait LIKE 'credential.%'
ORDER BY created_at DESC;"

# 查 OODA iteration 進度
docker exec athena-postgres-1 psql -U athena -d athena -c "
SELECT iteration_number, phase, technique_id, status
FROM ooda_iterations
WHERE operation_id = (SELECT id FROM operations WHERE code = 'LAB-001')
ORDER BY iteration_number, phase;"
```

---

## 卡住了怎麼辦

| 症狀 | 處理 |
|------|------|
| Act 一直 `queued` 不動 | UI → technique → **Approve** 手動推 |
| MCP tool 回 empty | 從 WSL `./scripts/verify-lab.sh` 重確認 lab 健康 |
| Orient LLM null | `docker compose logs backend --tail 50` 看 LLM API error |
| 帳號被鎖 | DC 上 `Unlock-ADAccount` (見 LAB_MANUAL Common Operations) |
| OODA 永在 recon | backend `.env` 加 `MIN_FACTS_PER_TARGET=1`，`docker compose restart backend` |
| LLM 推 MSSQL 相關 technique | 預期會失敗（MSSQL 服務半殘），Athena 該標 failed 繼續下個 iteration |

---

## 邊打邊修 — 發現 MCP 工具 bug 時

```bash
# 1. 看日誌
docker compose logs mcp-<tool> --tail 100

# 2. 改 code (VS Code / Claude Code)
#    /home/ubuntu/Athena/tools/<tool>/server.py

# 3. 重啟單一 container
docker compose up -d --build mcp-<tool>

# 4. UI → 失敗的 technique → Retry
```

**目標**：bug → 修 → 再跑 < 1 分鐘。

---

## 重新開始

```bash
# Windows PowerShell — revert 三台
$vmrun = "C:\Program Files (x86)\VMware\VMware Workstation\vmrun.exe"
& $vmrun -T ws revertToSnapshot "C:\...\DC01.vmx" "S3-clean-vulnerable"
& $vmrun -T ws revertToSnapshot "C:\...\WEB01.vmx" "S3-clean-vulnerable"
& $vmrun -T ws revertToSnapshot "C:\...\ACCT-DB01.vmx" "S3-clean-vulnerable"
# 再各自 start

# WSL — 清 Athena 這次的 operation state (選擇性，保留歷史可略)
docker exec athena-postgres-1 psql -U athena -d athena -c "
DELETE FROM facts WHERE operation_id IN (SELECT id FROM operations WHERE code = 'LAB-001');
DELETE FROM technique_executions WHERE operation_id IN (SELECT id FROM operations WHERE code = 'LAB-001');
DELETE FROM ooda_iterations WHERE operation_id IN (SELECT id FROM operations WHERE code = 'LAB-001');
DELETE FROM operations WHERE code = 'LAB-001';"
```

---

## 進階：升級成功目標到 Domain Admin

最低成功標達到後，若想繼續觀察完整攻擊鏈：

1. 手動 Approve 後續的 Kerberoast / ESC1 / DCSync techniques
2. 或降 confidence threshold 讓更多 technique auto-approve
3. 期望最終 fact：`credential.domain_admin_hash` 或 `credential.krbtgt_hash`

預計 6-10 iterations，30-60 分鐘。

---

## 關鍵檔案（debug 時參考）

| 檔案 | 作用 |
|------|------|
| [backend/app/services/ooda_controller.py](../../backend/app/services/ooda_controller.py) | OODA 主流程 |
| [backend/app/services/decision_engine.py](../../backend/app/services/decision_engine.py) | auto-approve 邏輯 |
| [backend/app/services/engine_router.py](../../backend/app/services/engine_router.py) | technique → MCP 路由 |
| [mcp_servers.json](../../mcp_servers.json) | MCP tool 設定 |
| [LAB_MANUAL.md](LAB_MANUAL.md) | 靶場憑證/漏洞/還原 |
