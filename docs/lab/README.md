# Athena AD 靶場建置指南

> Windows Server 2012 R2 x3 + VMware Workstation + WSL2 (Athena attacker)
> 目標：讓 Athena 自動打穿完整 AD 攻擊鏈，同時支援邊打邊修 code
> 參考 plan：`.claude/plans/pdf-attack-active-directory-pdf-vmware-inherited-fountain.md`

---

## 一張圖概覽

```
Windows 11 主機
├─ WSL2 (mirrored networking)
│   └─ Athena at /home/ubuntu/Athena
│       ├─ Docker: backend + frontend + 20 MCP 工具 (bridge 網路)
│       └─ Docker: responder / ntlm-relay / coercion  (host 網路, 看到 VMnet19)
└─ VMware Workstation 17
    └─ VMnet19 (Host-only, 10.10.10.0/24, Windows 主機介面設 10.10.10.1)
        ├─ DC01       10.10.10.10   (PDC + DNS + CA + DHCP)
        ├─ WEB01      10.10.10.20   (IIS, domain member)
        └─ ACCT-DB01  10.10.10.30   (MSSQL, domain member)

Athena 攻擊時的 attacker IP = 10.10.10.2 (WSL 內手動設在鏡射介面 eth4)
Windows 主機 VMnet19 adapter IP = 10.10.10.1 (當 gateway 用，不是攻擊來源)
```

---

## 一次性前置工作

### A. Windows 主機

1. **確認 Win11 22H2+**：`winver` 顯示 `22621` 或更高
2. **WSL2 ≥ 2.0**：`wsl --version`
3. **安裝 VMware Workstation Pro 17**（17.5+ 跟 Hyper-V 相容性最好）
4. **建 VMnet19**：Virtual Network Editor → Add Network → `VMnet19`
    - Type: **Host-only**
    - Subnet: `10.10.10.0 / 255.255.255.0`
    - DHCP: **取消勾選**（DC01 自己發）
    - Host virtual adapter: **勾選**
5. **`ncpa.cpl`**：`VMware Network Adapter VMnet19` → Properties → IPv4 → 設成 `10.10.10.1 / 255.255.255.0`（沒有 gateway, DNS 留空）
6. **WSL2 設 mirrored**：`C:\Users\<you>\.wslconfig`
    ```ini
    [wsl2]
    networkingMode=mirrored
    dnsTunneling=true
    firewall=true
    autoProxy=false
    memory=16GB
    processors=8
    ```
    然後 `wsl --shutdown`
7. **Windows 主機不能佔用 445 / 80**：
    ```powershell
    Stop-Service LanmanServer; Set-Service LanmanServer -StartupType Disabled
    Stop-Service W3SVC -EA 0; Set-Service W3SVC -StartupType Disabled -EA 0
    ```
8. **開 Defender Firewall 給 WSL 綁 port**（完整指令在 plan 的 Phase 2.5）
9. **不要讓主機睡覺**：`powercfg /change standby-timeout-ac 0`

### B. WSL2 端 (Athena)

1. `/etc/wsl.conf`
    ```ini
    [network]
    generateResolvConf = false
    ```
2. `/etc/resolv.conf`
    ```
    nameserver 10.10.10.10
    nameserver 1.1.1.1
    search corp.athena.lab
    ```
3. **把 VMnet19 鏡射介面 up + 配 10.10.10.2**（重要，WSL mirrored 對 VMware NIC 不會自動做）
    ```bash
    sudo ./scripts/wsl-vmnet19-up.sh --install   # 一次性，會裝 systemd unit 開機自動跑
    ```
    驗證：`ip -br addr` 應看到某個 `eth*` 有 `10.10.10.2/24`，且 `ping 10.10.10.1` 通。
    ping 失敗 → Windows admin PowerShell 開 Hyper-V firewall：
    ```powershell
    Set-NetFirewallHyperVVMSetting -Name '{40E0AC32-46A5-438A-A0B2-2B479E8F2E90}' `
      -DefaultInboundAction Allow -DefaultOutboundAction Allow
    ```
4. **啟用 Docker override**：`Athena/docker-compose.override.yml` 已把 responder/ntlm-relay/coercion 改 `network_mode: host`，ATTACKER_IP 已設 `10.10.10.2`
5. **確認 mirrored 介面名**：`ip link`，若 mirrored 介面名不是 `loopback0`，更新 `docker-compose.override.yml` 的 `ATHENA_LISTEN_IFACE`
6. **重啟 Athena**：`docker compose --profile mcp down && docker compose --profile mcp up -d`

---

## 建立 3 台 VM

用 VMware Easy Install 各裝一台 Windows Server 2012 R2 Standard：
- 2 vCPU / 4 GB RAM / 60 GB thin disk
- Network: **VMnet19 (Host-only)**
- **不要**裝 Windows Update、不要讓它連外網下載 patch
- 裝完進桌面 → 裝 VMware Tools → **關機 → snapshot `S1: pristine-installed`**

### 上傳 C:\LabSetup\ 內容

三台機器都複製這整個目錄 `Athena/lab/windows/` → `C:\LabSetup\`：

```
C:\LabSetup\
├─ common.psm1
├─ Setup-DC.ps1
├─ Setup-Web.ps1
├─ Setup-DB.ps1
├─ site\
│   └─ index.html
├─ sql\
│   └─ ConfigurationFile.ini
│   + (你另外下載) setup.exe + MSSQL 2019 Express 媒體
└─ prereq\
    └─ (下載) Win8.1AndW2K12R2-KB3191564-x64.msu   (WMF 5.1)
```

### 預先下載的東西

| 檔案 | 放哪 | 下載連結 |
|------|------|----------|
| WMF 5.1 | `C:\LabSetup\prereq\Win8.1AndW2K12R2-KB3191564-x64.msu` | MS Download → KB3191564 |
| MSSQL 2019 Express 完整媒體 | 解壓到 `C:\LabSetup\sql\`（含 `setup.exe`） | MS Download ID=101064，選 "Download Media" |

---

## 執行順序

### 1. DC01 先跑

以 Administrator 開 PowerShell：
```powershell
cd C:\LabSetup
.\Setup-DC.ps1
```

腳本會：
- 跑 Phase A 停 WU
- Phase B 如果 PS < 5 會裝 WMF 5.1 → **自動重啟 → 自動續跑**
- Phase C 改機名 → **自動重啟**
- Phase D 建 forest `corp.athena.lab` → **自動重啟**
- Phase E-O 建 OU/使用者/ACL/AD CS/ESC1/ESC8/Spooler/NullPipes/DHCP/驗證

總時間約 30-40 分鐘（含 3 次重啟）。結尾會列印驗證摘要。

### 2. 到 DC01 成功後 → WEB01

```powershell
cd C:\LabSetup
.\Setup-Web.ps1
```

約 15 分鐘。

### 3. 到 WEB01 成功後 → ACCT-DB01

```powershell
cd C:\LabSetup
.\Setup-DB.ps1
```

約 25 分鐘（MSSQL 安裝慢）。

### 4. 關機 → Snapshot

三台都 Setup 完 → **各自關機** → 在 VMware 對每台做 snapshot 取名 `S2: domain-joined` 或直接 `S3: clean-vulnerable`（如果你不打算調整漏洞配置）。

---

## 驗證（拍 S3 之前必跑）

1. 三台 VM 開機
2. 在 WSL2 Athena：
    ```bash
    cd ~/Athena
    ./scripts/verify-lab.sh
    ```
3. **全部 PASS** 才能關機拍 `S3: clean-vulnerable`
4. 任何 FAIL → 看 transcript（`C:\LabSetup\logs\*.log`）對應修，或重跑對應 phase：
    ```powershell
    # 例：重跑 DC 的 J phase（ESC1）
    Remove-Item C:\LabSetup\.done.J-esc1 -ErrorAction SilentlyContinue
    .\Setup-DC.ps1
    ```

---

## 日常使用

### 開打

1. VMware → 還原 `S3: clean-vulnerable` → 三台開機
2. WSL2 → `docker compose --profile mcp up -d`（若 Athena 停著）
3. 從 Claude Code 觸發 Athena OODA loop
4. Athena 會自動執行 recon → credential access → privilege escalation → persistence

### 邊打邊修 code

1. Athena MCP 工具報錯 → 看 `docker compose logs mcp-<tool>`
2. Claude Code 改 `Athena/tools/<tool>/server.py`
3. `docker compose up -d mcp-<tool>` 只重啟那一個 container（< 10 秒）
4. 叫 Athena 重跑失敗步驟

### 演練結束

VMware → 還原 `S3: clean-vulnerable`，下次從乾淨狀態開始。

---

## 故障排除

| 症狀 | 對策 |
|------|------|
| WSL `ip addr` 看不到 10.10.10.x | 正常 — VMware NIC 被 mirrored 創成 eth2/3/4 但 DOWN。需 `sudo ip link set eth4 up && sudo ip addr add 10.10.10.2/24 dev eth4`（詳見 plan 2.4a） |
| Responder 啟不起來 | Windows 主機還有東西佔 445 → `netstat -abno | findstr :445` 查並關閉 |
| DC `dcpromo` 失敗 | 通常是時鐘：手動 `w32tm /resync /force`；或網卡 DNS 不是 `127.0.0.1` |
| Certipy 找不到 ESC1 | `Restart-Service CertSvc` 在 DC 跑一次；再 `certutil -CATemplates` 確認有 `VulnTemplate1` |
| 密碼噴灑全失敗 | 帳號被鎖了 → DC 跑 `Unlock-ADAccount steve,bob,kevin,alice` |
| Kerberoast 拿不到 hash | `setspn -L CORP\svc_sql` 確認 SPN 在；若缺 → DC 上 `setspn -S MSSQLSvc/acct-db01.corp.athena.lab:1433 CORP\svc_sql` |
| 主機 sleep 醒來 WSL 斷線 | `wsl --shutdown` 再進；長期解決：`powercfg /change standby-timeout-ac 0` |

---

## 漏洞清單（Athena 應能全部打穿）

| # | 漏洞 | 觸發工具 | 位置 |
|---|------|----------|------|
| 1 | 弱密碼 (`steve`, `bob`, `kevin`, `alice`) | netexec-suite (spray) | DC |
| 2 | AS-REP roastable (`legacy_kev`) | impacket-ad (GetNPUsers) | DC |
| 3 | Kerberoastable SPN (`svc_sql`, `svc_backup`) | credential-dumper (kerberoast) | DC/DB |
| 4 | PetitPotam (MS-EFSR) | coercion-tools | DC |
| 5 | PrinterBug (MS-RPRN, Spooler on) | coercion-tools | DC |
| 6 | DFSCoerce (MS-DFSNM) | coercion-tools | DC |
| 7 | AD CS ESC1 (`VulnTemplate1`) | certipy-ad | DC |
| 8 | AD CS ESC8 (Web Enrollment over HTTP, no EPA) | certipy-ad | DC |
| 9 | SMB signing off (WEB01, ACCT-DB01) | ntlm-relay | WEB/DB |
| 10 | LDAP signing not required (DC) | ntlm-relay → LDAP | DC |
| 11 | `HelpDeskAdmins` GenericAll → `Tier0` OU | ad-exploiter (ACL abuse) | DC |
| 12 | `low_user` WriteDacl → `svc_backup` (shadow-creds) | ad-exploiter | DC |
| 13 | `low_user` GenericWrite msDS-AllowedToActOnBehalfOfOtherIdentity → Servers OU (RBCD) | ad-exploiter | DC |
| 14 | Unconstrained delegation on WEB01 | credential-dumper (TGT harvest) | WEB |
| 15 | WDigest cleartext (UseLogonCredential=1) + DA service logon | credential-dumper (LSASS) | WEB/DB |
| 16 | DPAPI credentials cached under da_alice profile | credential-dumper (DPAPI) | WEB/DB |
| 17 | LLMNR / NBT-NS enabled | responder-capture | WEB/DB |
| 18 | MSSQL `xp_cmdshell` on | impacket-ad (mssqlclient post-exploit) | DB |

---

## 安全聲明

此靶場設計**故意包含多個高危漏洞**，僅限：
- Host-only VMnet19 隔離網段
- 不暴露到家用 LAN / 網際網路

**切勿**把 VM 改成 Bridged 或 NAT 模式接到實體網路，`da_alice` 的 DA 密碼會在 LSASS、Responder log、BloodHound 輸出中多次出現。
