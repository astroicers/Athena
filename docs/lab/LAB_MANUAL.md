# Athena AD Lab 使用手冊

> **版本**: 1.0 (建置於 2026-04-24)
> **拓撲**: Windows Server 2012 R2 x3，Bridged 到家 LAN (192.168.0.0/24)
> **網域**: `corp.athena.lab` (NetBIOS `CORP`)
> **Forest/Domain FL**: Win2012R2
> **CA**: `corp-DC01-CA` (Enterprise Root)

**相關文件**：
- 👉 [**ATHENA_PLAYBOOK.md**](ATHENA_PLAYBOOK.md) — 如何讓 Athena 自動打穿這個靶場（零先驗知識演練操作手冊）
- [README.md](README.md) — 靶場建置歷程

---

## 目錄

1. [網路拓撲](#網路拓撲)
2. [憑證清單](#憑證清單)
3. [漏洞與對應攻擊技巧](#漏洞與對應攻擊技巧)
4. [驗證套件](#驗證套件)
5. [快照策略與還原](#快照策略與還原)
6. [常見操作](#常見操作)
7. [已知問題](#已知問題)

---

## 網路拓撲

```
家用路由 (192.168.0.1)
│
├── WSL2 (Athena 攻擊者, 192.168.0.18)
│   └── /home/ubuntu/Athena (code + MCP tools)
│
├── DC01       192.168.0.16  corp.athena.lab (PDC, DNS, CA)
├── WEB01      192.168.0.20  網域成員 (IIS)
└── ACCT-DB01  192.168.0.23  網域成員 (MSSQL 服務半殘 — SPN 已註冊)
```

**網段**: `192.168.0.0/24` (Bridged)
**VMware 設定**: 各 VM Network Adapter → **Bridged: Auto**

---

## 憑證清單

### 本機 Administrator (全部三台)

| 機器 | 帳號 | 密碼 |
|------|------|------|
| DC01 / WEB01 / ACCT-DB01 | `administrator` | `1qaz@WSX` |

### 網域帳號 (對所有機器有效)

> UPN 格式：`<user>@corp.athena.lab`
> Legacy 格式：`CORP\<user>`

| SamAccountName | 密碼 | 成員 / 特殊屬性 | 攻擊用途 |
|----------------|------|-----------------|---------|
| `administrator` | `1qaz@WSX` | Domain Admins | Default DA |
| `da_alice` | `WinterIsComing!2024` | **Domain Admins** | Shadow DA，被 plant 到 WEB01 / DB01 LSASS |
| `steve` | `Summer2024!` | Domain Users | 密碼噴灑起點 |
| `bob` | `Password1!` | Domain Users | 密碼噴灑備案 |
| `kevin` | `Welcome1` | Domain Users | 密碼噴灑備案 |
| `alice` | `P@ssw0rd2024` | Domain Users, HelpDeskAdmins | WEB01 快取憑證替身 |
| `legacy_kev` | `Qwerty123!` | Domain Users, **UF_DONT_REQUIRE_PREAUTH** | AS-REP roast |
| `svc_sql` | `Summer2023` | Domain Users, PasswordNeverExpires, **SPN: MSSQLSvc/acct-db01.corp.athena.lab:1433** | Kerberoast #1 |
| `svc_backup` | `BackupMe!234` | Domain Users, PasswordNeverExpires, **SPN: HTTP/backup.corp.athena.lab** | Kerberoast #2 |
| `low_user` | `Changem3!` | Domain Users | ACL abuse 起點（WriteDacl → svc_backup；RBCD prep on Servers OU） |

### AD 安全結構

| 群組 | 成員 | 特殊權限 |
|------|------|----------|
| `Domain Admins` | administrator, da_alice | (built-in) |
| `HelpDeskAdmins` | alice | **GenericAll on `OU=Tier0`** |

### 關鍵 AD 物件權限

- `low_user` WriteDacl → `svc_backup` (shadow credentials 路徑)
- `low_user` GenericWrite `msDS-AllowedToActOnBehalfOfOtherIdentity` → `OU=Servers` (RBCD)
- `WEB01$` 帳號: **TrustedForDelegation** (unconstrained delegation)

### AD CS 模板

| Template | 狀態 | 漏洞 |
|----------|------|------|
| `VulnTemplate1` | **Published + Enabled** | **ESC1** (Enrollee supplies subject + Client Auth EKU + Domain Users enroll)，**ESC15** (schema v1) |
| Web Enrollment (`/certsrv`) | Enabled | **ESC8** (HTTP + NTLM + no EPA) |

### MSSQL (ACCT-DB01)

> 服務狀態：**半殘** — setup 中途失敗，service 存在但無法正常 connect。
> **SPN 已在 DC 上註冊** → Kerberoast `svc_sql` 仍有效。
> 若需完整 MSSQL，手動登入 ACCT-DB01，執行 `C:\Program Files\Microsoft SQL Server\140\Setup Bootstrap\Log\<最新>\ConfigurationFile.ini` 的 setup 或 GUI 重裝。

### Credential Plants（WEB01 / ACCT-DB01 相同）

| 植入機制 | 帳號 | 觸發條件 |
|---------|------|---------|
| Windows service `LabPlantSvc` (auto-start, ping -n 86400) | `CORP\da_alice` | 開機自動 logon → LSASS 有 DA ticket |
| WDigest `UseLogonCredential=1` | - | 啟用 cleartext password caching |
| Scheduled task `LabDpapiPlant` (ONSTART as `da_alice`) | 呼叫 `cmdkey /add` 存 DPAPI | da_alice 帳號登入時觸發 |

DPAPI 存入的目標（WEB01）：
- `backup.corp.athena.lab` → `CORP\svc_backup / BackupMe!234`
- `acct-db01.corp.athena.lab` → `CORP\svc_sql / Summer2023`

DPAPI 存入的目標（ACCT-DB01）：
- `backup.corp.athena.lab` → `CORP\svc_backup / BackupMe!234`
- `web01.corp.athena.lab` → `CORP\alice / P@ssw0rd2024`

---

## 漏洞與對應攻擊技巧

| # | 漏洞 | MITRE | 觸發工具 | 位置 |
|---|------|-------|----------|------|
| 1 | 弱密碼 (`steve`, `bob`, `kevin`, `alice`) | T1110.003 | netexec-suite | DC |
| 2 | AS-REP roastable (`legacy_kev`) | T1558.004 | GetNPUsers.py | DC |
| 3 | Kerberoastable SPN (`svc_sql`, `svc_backup`) | T1558.003 | GetUserSPNs.py, hashcat | DC |
| 4 | PetitPotam (MS-EFSR RPC pipe accessible) | T1187 | coercion-tools | DC |
| 5 | PrinterBug (Spooler on) | T1187 | coercion-tools | DC |
| 6 | DFSCoerce (MS-DFSNM) | T1187 | coercion-tools | DC |
| 7 | AD CS ESC1 (`VulnTemplate1`) | T1649 | certipy-ad | DC |
| 8 | AD CS ESC8 (Web Enrollment HTTP, no EPA) | T1649 | certipy-ad + ntlmrelayx | DC |
| 9 | AD CS ESC15 (schema v1 + user enrollable) | T1649 | certipy-ad | DC |
| 10 | SMB signing off (WEB01, ACCT-DB01) | T1557.001 | ntlm-relay | WEB/DB |
| 11 | HelpDeskAdmins GenericAll → Tier0 OU | T1098.002 | ad-exploiter | DC |
| 12 | low_user WriteDacl → svc_backup (shadow-creds) | T1098.002 | ad-exploiter | DC |
| 13 | low_user GenericWrite msDS-AllowedToAct → Servers OU (RBCD) | T1098.002 + T1550.003 | ad-exploiter | DC |
| 14 | Unconstrained delegation on WEB01$ | T1550.003 | credential-dumper (TGT harvest) | WEB |
| 15 | WDigest cleartext + DA service logon | T1003.001 | credential-dumper (LSASS) | WEB/DB |
| 16 | DPAPI credentials cached under da_alice | T1555.004 | credential-dumper (DPAPI) | WEB/DB |
| 17 | LLMNR / NBT-NS enabled | T1557.001 | responder-capture | WEB/DB |

---

## 驗證套件

**路徑**: `/home/ubuntu/Athena/scripts/verify-lab.sh`

### 前置需求（WSL 側）

```bash
# Pentest tools (若未裝)
export PATH="$HOME/.local/bin:$PATH"
pip3 install --user --break-system-packages \
    impacket certipy-ad coercer bloodhound

pip3 install --user --break-system-packages \
    git+https://github.com/Pennyw0rth/NetExec

# OpenSSL legacy provider for NTLM (MD4) - 在 Ubuntu 22.04 上必要
cat > /tmp/openssl-legacy.cnf <<'EOF'
openssl_conf = openssl_init
[openssl_init]
providers = provider_sect
[provider_sect]
default = default_sect
legacy  = legacy_sect
[default_sect]
activate = 1
[legacy_sect]
activate = 1
EOF
```

### 執行

```bash
cd /home/ubuntu/Athena
export PATH="$HOME/.local/bin:$PATH"
export OPENSSL_CONF=/tmp/openssl-legacy.cnf

./scripts/verify-lab.sh
```

### 預期輸出（14 全綠）

```
[01] ping DC01                                     PASS
[02] ping WEB01                                    PASS
[03] ping ACCT-DB01                                PASS
[04] nxc smb DC01 (auth check)                     PASS
[05] SMB signing off on WEB01 (via impacket)       PASS
[06] SMB signing off on DB (via impacket)          PASS
[07] password spray finds steve                    PASS
[08] AS-REP: legacy_kev hash obtainable            PASS
[09] Kerberoast: svc_sql hash                      PASS
[10] Kerberoast: svc_backup hash                   PASS
[11] Certipy: VulnTemplate1 vulnerable (ESC1)      PASS
[12] BloodHound: collect runs clean                PASS
[13] PrinterBug: Spooler RPC reachable on DC       PASS
[14] Coercer MS-EFSR pipe accessible on DC         PASS
```

---

## 快照策略與還原

### Snapshot 命名

| Snapshot | 狀態 | 還原場景 |
|----------|------|----------|
| `S2-domain-joined` | 三台加入網域，漏洞未注入 | 想重新調整漏洞組合時用 |
| **`S3-clean-vulnerable`** | **所有漏洞就位、verify-lab 全綠** | **Athena 每次演練的還原點** |

### 還原流程

**VMware GUI**：
1. 對每台 VM 右鍵 → Snapshot → Snapshot Manager
2. 選 `S3-clean-vulnerable` → Go To
3. 確認「revert to snapshot」

**VMware CLI (vmrun) — 推薦腳本化**：
```powershell
# Windows PowerShell，VMware Workstation Pro 17
$vmrun = "C:\Program Files (x86)\VMware\VMware Workstation\vmrun.exe"
$vms = @(
    "C:\path\to\DC01.vmx",
    "C:\path\to\WEB01.vmx",
    "C:\path\to\ACCT-DB01.vmx"
)
foreach ($vmx in $vms) {
    & $vmrun -T ws revertToSnapshot $vmx "S3-clean-vulnerable"
    & $vmrun -T ws start $vmx
}
```

還原後建議等 2-3 分鐘讓服務完整啟動，再跑 `verify-lab.sh` 確認狀態。

### 一般重啟 vs 快照還原

- **演練結束清理** → 還原 `S3`（保證下次從乾淨狀態開始）
- **測 Athena 工具壞了想重來** → 還原 `S3`
- **想改漏洞配置** → 還原 `S2-domain-joined` → 重跑 Stage2-*.ps1

---

## 常見操作

### 從 WSL 查網域資訊

設定 resolv.conf（見本手冊開頭附的指令）後：

```bash
# 查 SRV
nslookup -type=SRV _ldap._tcp.dc._msdcs.corp.athena.lab
# 連 DC LDAP
nxc ldap 192.168.0.16 -u steve -p 'Summer2024!'
# 從 WSL 透過 UPN 連 WinRM
export OPENSSL_CONF=/tmp/openssl-legacy.cnf
python3 -c "
import winrm, os
os.environ['OPENSSL_CONF']='/tmp/openssl-legacy.cnf'
s = winrm.Session('http://dc01.corp.athena.lab:5985/wsman',
    auth=('administrator@corp.athena.lab','1qaz@WSX'), transport='ntlm')
print(s.run_cmd('hostname').std_out.decode())
"
```

### 從 WSL 部署腳本 / 檔案到 VM

統一透過 `/home/ubuntu/Athena/lab/deploy_lab.py`：

```bash
cd /home/ubuntu/Athena/lab
export OPENSSL_CONF=/tmp/openssl-legacy.cnf

# 上傳任意檔案(指定 role: dc/web/db)
python3 deploy_lab.py upload dc

# 上傳 Stage2 材料
python3 deploy_lab.py upload dc web db --stage2

# 在 VM 上 run 任意 PowerShell
python3 deploy_lab.py ps 192.168.0.16 'Get-Process | Select -First 5'

# 檢查 phase 進度（sentinels）
python3 deploy_lab.py phases 192.168.0.16
```

### 解鎖被自鎖的帳號

Stage2-DC 把 `LockoutThreshold=20`，通常噴密碼不會鎖，但如果真的鎖到：

```bash
export OPENSSL_CONF=/tmp/openssl-legacy.cnf
python3 /home/ubuntu/Athena/lab/deploy_lab.py ps 192.168.0.16 '
Import-Module ActiveDirectory
foreach ($u in "steve","bob","kevin","alice","legacy_kev","svc_sql","svc_backup","low_user","da_alice") {
    try { Unlock-ADAccount -Identity $u -EA Stop } catch {}
}
"all unlocked"
'
```

### 重設所有密碼（若漏洞觸發改了密碼）

```bash
# 從 DC 跑
python3 /home/ubuntu/Athena/lab/deploy_lab.py ps 192.168.0.16 '
Import-Module ActiveDirectory
$users = @{
    "steve"      = "Summer2024!"
    "bob"        = "Password1!"
    "kevin"      = "Welcome1"
    "alice"      = "P@ssw0rd2024"
    "legacy_kev" = "Qwerty123!"
    "svc_sql"    = "Summer2023"
    "svc_backup" = "BackupMe!234"
    "low_user"   = "Changem3!"
    "da_alice"   = "WinterIsComing!2024"
}
foreach ($u in $users.Keys) {
    Set-ADAccountPassword -Identity $u -Reset -NewPassword (ConvertTo-SecureString $users[$u] -AsPlainText -Force)
}
"passwords reset"
'
```

---

## 已知問題

### 1. MSSQL 服務半殘（ACCT-DB01）

**症狀**：`MSSQLSERVER` service 存在但無法 connect（login failed）。
**原因**：setup 第二階段因 Windows auth 設定失敗中斷。
**影響**：
- ❌ 無法用 `nxc mssql` / sqlcmd 對服務發指令
- ✅ **Kerberoast `svc_sql` 仍可打** (SPN 在 DC 上註冊)
- ✅ **主機所有其他漏洞不受影響**

**修復**（若需要完整 MSSQL）：
1. RDP 或 console 登入 ACCT-DB01 (administrator / 1qaz@WSX)
2. 先卸載：Control Panel → Programs → Microsoft SQL Server 2016 → Remove
3. 重跑 `C:\LabSetup\sql\extracted\setup.exe` 互動式安裝
4. 在 "Server Configuration" 頁把 `SQL Server Database Engine` 服務帳號改成 `NT AUTHORITY\NETWORK SERVICE`
5. 在 "Database Engine Configuration" 頁把 `administrator` 加入 SQL administrators
6. 完成後 `sqlcmd -S localhost -E -Q "SELECT @@VERSION"` 應可連

### 2. WSL 無法看到 VMware 廣播 (LLMNR/NBT-NS)

**症狀**：從 WSL 跑 Responder 收不到靶機的 LLMNR query。
**原因**：WSL 2.4 mirrored networking **不把 VMware 虛擬網卡鏡射成 UP**。
**對策**：Responder / ntlmrelayx / coercer **放在同網段的 Linux 機器跑**。本 lab 用 Bridged 模式，所以**從同家 LAN 的另一台實體 Linux（或 VMware 裡加一台 Kali）** 可以收廣播。

### 3. NTLM relay 從 WSL 發起不穩

同 #2 — WSL 發 SMB relay 時，靶機回連到 WSL mirrored IP 會被 Windows host 丟掉。**把 Responder / ntlm-relay MCP 工具跑在同網段 Linux VM**。

### 4. Python OpenSSL MD4 問題

在 Ubuntu 22.04+ 用 pywinrm/impacket 對 Windows 發 NTLM 時會看到：
```
ValueError: unsupported hash type md4
```

**修**：`export OPENSSL_CONF=/tmp/openssl-legacy.cnf`（見[驗證套件](#驗證套件)前置需求）

### 5. WEB01 / ACCT-DB01 domain NTLM auth 失敗

**症狀**：從 WSL 用 `CORP\steve` 或 `steve@corp.athena.lab` 對 WEB01/DB01 SMB 認證失敗 (`STATUS_LOGON_FAILURE`)，但對 DC01 成功。
**原因**：推測是 member server 對 domain NTLM passthrough 的 GPO 設定，需進一步研究。
**繞過**：驗證腳本對 WEB/DB 用**本機 administrator 認證**檢查 SMB signing，domain auth 只對 DC 做。

### 6. AthenaLabResume scheduled task 無法 `$MyInvocation.MyCommand.Path` 續跑

**症狀**：腳本觸發 Request-Reboot 後，重啟完 resume task 參數空白（script path 讀不到）。
**對策**：重啟後**手動** `python3 deploy_lab.py run-stage1 <role>` 重入腳本（sentinel 會跳過已完成的 phase）。已文件化在 [deploy_lab.py 常見操作](#從-wsl-部署腳本--檔案到-vm)。

---

## 檔案結構

```
/home/ubuntu/Athena/
├── lab/
│   ├── deploy_lab.py              # WSL → VM 部署 + WinRM 呼叫
│   ├── windows/
│   │   ├── common.psm1            # 共用 PowerShell 函式
│   │   ├── Stage1-DC.ps1          # DC baseline → AD DS forest
│   │   ├── Stage1-Web.ps1         # (未用到 — djoin 方案取代)
│   │   ├── Stage1-DB.ps1          # (未用到)
│   │   ├── Stage1b-Web.ps1        # Offline djoin (bypass SID collision)
│   │   ├── Stage1b-DB.ps1         # Offline djoin
│   │   ├── Stage2-DC.ps1          # 使用者/ACL/AD CS/ESC1/ESC8
│   │   ├── Stage2-Web.ps1         # IIS/SMB off/WDigest/DA plant/DPAPI
│   │   ├── Stage2-DB.ps1          # SMB off/WDigest/DA plant/MSSQL
│   │   ├── web01-djoin.blob       # Offline domain join provisioning
│   │   ├── acctdb01-djoin.blob
│   │   ├── site/index.html        # WEB01 IIS 假首頁
│   │   ├── sql/
│   │   │   ├── ConfigurationFile.ini
│   │   │   └── SQLEXPR_x64_ENU.exe   # SQL 2016 Express full media
│   │   └── prereq/Win8.1AndW2K12R2-KB3191564-x64.msu   # WMF 5.1
└── scripts/
    ├── verify-lab.sh              # 14 項 end-to-end 驗證
    └── wsl-vmnet19-up.sh          # (legacy VMnet19 mirrored helper — 不再使用)

docs/lab/
└── LAB_MANUAL.md                  # 本手冊
```

---

## 附錄 A：演練結束後建議操作

```bash
# 1. 還原三台 VM 到 S3
# (VMware GUI 或 vmrun revertToSnapshot)

# 2. 開機完全啟動（等 DC 起來）
sleep 60

# 3. 驗證狀態
cd /home/ubuntu/Athena
export PATH="$HOME/.local/bin:$PATH"
export OPENSSL_CONF=/tmp/openssl-legacy.cnf
./scripts/verify-lab.sh

# 4. 14 全綠 → 繼續攻擊演練
```

---

## 附錄 B：從零重建到現狀的指令序列

若 S3 快照也壞了，可從 Windows ISO 從頭來：

```bash
cd /home/ubuntu/Athena/lab
export OPENSSL_CONF=/tmp/openssl-legacy.cnf

# 1. 在 VMware 各裝 Windows Server 2012 R2 x3 (Bridged, admin=1qaz@WSX)
# 2. 上傳腳本 + 媒體
python3 deploy_lab.py upload dc web db --stage2

# 3. Stage-1: baseline + WMF + domain join
python3 deploy_lab.py run-stage1 dc
# 等 DC forest 起來 (約 15 分鐘)
python3 deploy_lab.py run-stage1 webb   # offline djoin
python3 deploy_lab.py run-stage1 dbb

# 4. Snapshot: S2-domain-joined

# 5. Stage-2: 注入漏洞
python3 deploy_lab.py run-stage1 dc2
# 等 DC Stage-2 完成 (約 5 分鐘)
python3 deploy_lab.py run-stage1 web2
python3 deploy_lab.py run-stage1 db2

# 6. 驗證 (cd .. 回 Athena root)
cd /home/ubuntu/Athena
./scripts/verify-lab.sh

# 7. Snapshot: S3-clean-vulnerable
```

---

**最後更新**: 2026-04-24
