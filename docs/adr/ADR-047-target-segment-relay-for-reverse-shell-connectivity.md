# [ADR-047]: Target-Segment Relay for Reverse Shell Connectivity

| 欄位 | 內容 |
|------|------|
| **狀態** | `Draft` |
| **日期** | 2026-04-09 |
| **決策者** | Athena Core Team |

---

## 背景（Context）

SPEC-053 實作 Phase 1 diagnostic 時發現一個**基礎設施層面**的限制，阻擋了 Metasploit reverse shell 類 exploit 的真實端到端成功：

### 網路拓撲現況

```
┌─────────────────────────────────────────────────────┐
│ Host (Windows, 192.168.96.83/20)                     │
│                                                       │
│   Docker bridge: athena_default 172.22.0.0/16         │
│   ┌──────────────────────────┐                       │
│   │ athena-backend-1    172.22.0.3                   │
│   │ athena-msf-rpc-1    172.22.0.12                  │
│   │ athena-mcp-*        172.22.0.4-11                │
│   └──────────────────────────┘                       │
│               │                                       │
│       (NAT via host iptables)                        │
└───────────────┼──────────────────────────────────────┘
                ▼
      Target LAN: 192.168.0.0/x
                │
                ▼
       metasploitable2: 192.168.0.26
```

### 單向路由問題

- **Athena → target**：可達。Docker bridge NAT 把 backend `172.22.0.3` 和 msf-rpc `172.22.0.12` 的出站封包 masquerade 為 host `192.168.96.83`，target 看到請求來源是 host。
- **Target → Athena**：**不可達**。target 在 `192.168.0.26`，不認識 `172.22.0.0/16` 網段，callback 封包無路可送。

### Reverse shell 類 exploit 的連動失敗

以下 Metasploit exploit 都需要 target 主動 callback 到 Athena 指定的 LHOST:LPORT：

| Exploit Module | 服務 | Payload | LHOST 需求 |
|---------------|------|---------|-----------|
| `exploit/unix/irc/unreal_ircd_3281_backdoor` | UnrealIRCd (6667) | `cmd/unix/reverse` | 需要 |
| `exploit/multi/samba/usermap_script` | Samba 3.0.20 (139/445) | `cmd/unix/reverse` | 需要 |
| `exploit/unix/misc/distcc_exec` | distccd (3632) | `cmd/unix/reverse` | 需要 |

當 LHOST 被設為 `172.22.0.12`（msf-rpc docker bridge IP）時，target 的 payload 試圖 `connect(172.22.0.12, PORT)` 必然 fail——封包在 target LAN 之外沒有路由。

**唯一例外：bind shell 類 exploit**（例如 `exploit/unix/ftp/vsftpd_234_backdoor` + `cmd/unix/interact`）不需要 callback，但 vsftpd 2.3.4 backdoor 在 metasploitable2 上有**僵屍化問題**：每次 trigger 後 port 6200 上的 shell 只能互動一次，後續 trigger 只會 reopen listener 但 shell 端管道已死。修復僅能透過重開 target 或從現有 shell 把 backdoor process 殺掉——形成「先有 shell 才能修 shell」的雞生蛋僵局。

### 為什麼需要獨立 ADR

這個限制**不是代碼缺陷**，而是部署拓撲決策。解法都涉及跨層面調整：

- 修改 docker network mode（影響服務隔離）
- 新增 host 層的 port forwarding（影響 Windows 宿主機權限與自動化）
- 佈署獨立 relay 節點（新增基礎設施實體 + 維運成本）

SPEC-053 的範圍是**軟體層的 Orient-driven pivot 機制**，不應被強迫承擔基礎設施決策。本 ADR 把這個決策獨立出來，待時機成熟（預計演講前 2-3 週，4 月下旬）再實作對應 SPEC-054。

---

## 評估選項（Options Considered）

### 選項 A：msf-rpc 改用 `network_mode: host`

修改 `docker-compose.yml` 讓 `athena-msf-rpc-1` 直接使用 host 網路命名空間。

- **優點**：
  - 改動最小（一行 docker-compose）
  - msfrpcd 直接持有 host IP `192.168.96.83`，LHOST 設此即可
  - Reverse shell 所有類型都能通
- **缺點**：
  - 打破既有 docker bridge 隔離——msf-rpc 容器不再與其他 MCP 服務共享內部 DNS 和網段
  - backend 呼叫 msfrpcd 時必須改用 `host.docker.internal` 或 host IP，不能再用 `msf-rpc` 這個 service name
  - Windows Docker Desktop 的 `network_mode: host` 支援有限且不穩定
  - 其他 MCP 容器（attack-executor 等）若未來也需要類似能力，每個都要個別處理
- **風險**：
  - Windows WSL2 環境下 host network mode 的行為可能與 Linux 原生不一致
  - 需要測試 backend 與 msf-rpc 之間的連線是否仍維持 async stability

### 選項 B：Windows host 層 port forwarding

在 Windows host 用 `netsh interface portproxy add v4tov4` 把 `192.168.96.83:4444-4454` 轉發到 `172.22.0.12:4444-4454`，並在 `docker-compose.yml` 把 msf-rpc 的 payload port range 開 port mapping (`ports: - "4444-4454:4444-4454"`)。

- **優點**：
  - 不動既有 docker network 拓撲
  - 可以只開必要的 payload port
- **缺點**：
  - 需要在 Windows host 以管理員權限設定 portproxy
  - demo 機器若換宿主就要重設
  - payload port 必須預先鎖定在固定範圍，限制 metasploit 的彈性
  - Windows firewall 必須開對應 inbound rule
- **風險**：
  - 手動設定易出錯，且 Windows 升級或重啟可能清掉 portproxy 規則
  - 不符合「自動化、可重現」的演講 demo 訴求

### 選項 C：佈署獨立 Target-Segment Relay（推薦）

在 target LAN `192.168.0.0/x` 上佈署一台 relay 節點（Raspberry Pi 或 Kali VM），扮演 Athena 與 target 之間的中介：

```
Athena (172.22.0.12)  ──SSH tunnel──▶  Relay (192.168.0.X)  ──TCP──▶  Target (192.168.0.26)
                                              │
                                         (listens LHOST
                                          on 192.168.0.X)
```

- Athena 透過 SSH reverse tunnel 把 msf-rpc 的 payload listener port 轉發到 relay
- LHOST 設為 relay 的 IP（`192.168.0.X`），target 可直接 callback
- Relay 只跑 `sshd` + optional `ncat`，維運成本低

- **優點**：
  - **架構最乾淨**：docker 網路拓撲不動、Windows host 不動、msfrpcd 行為不動
  - Reverse shell payload 回連正常 TCP 三次握手，無需特殊路由
  - 同一個 relay 可以服務未來所有 target LAN 上的攻擊
  - 符合真實滲透測試「跳板機（jump box）」的 industry practice
  - SSH tunnel 身份驗證、流量加密、自動重連都有既有工具支援
- **缺點**：
  - 需要採購 / 部署新硬體或 VM
  - 需要維護 relay 的 OS / SSH 金鑰 / tunnel persistence
  - Relay 不在線時 metasploit reverse shell 路徑完全不可用（需 fallback 機制或明確降級）
- **風險**：
  - Relay 本身成為攻擊面，身份驗證與隔離須謹慎設計
  - Tunnel 斷線的 race condition 可能導致 session 誤判

---

## 決策（Decision）

**暫定決策（Draft 階段）：傾向選項 C（Target-Segment Relay）**，但正式決策延後到 relay 硬體到位 + SPEC-054 規格完成後再定。

**決策延後理由：**

1. 本 ADR 建立時點（2026-04-09）距離演講（2026-05-07）還有約 4 週，時間允許採購與部署
2. SPEC-053 的軟體面修復（Orient 結構化 failure + Rule #9 pivot + metasploit one-shot）**可以先獨立完成**，提供 demo 敘事骨幹
3. Relay 的決策涉及硬體選型與預算，不應在 SPEC 實作中途做
4. 若演講時間壓力過大，可以降級到選項 A（`network_mode: host`）作為 fallback——**本 ADR 預留此退路**

**等 relay 採購/部署確定後，將：**
- 把本 ADR 從 `Draft` 改為 `Accepted`
- 建立 SPEC-054「Target-Segment Relay Integration for Reverse Shell Exploits」
- 實作 relay 自動偵測、SSH tunnel 自動建立、LHOST 動態配置
- 把 SPEC-053 Deferred 驗收清單全部跑過

---

## 後果（Consequences）

**正面影響（Accepted 後）：**

- Reverse shell 類 exploit（samba / distccd / UnrealIRCd）真實可打通
- Athena 具備完整的 MITRE ATT&CK TA0001 (Initial Access) 覆蓋能力
- 未來可擴展至跨網段 lateral movement（relay 作為跳板）
- 符合 industry 真實滲透測試架構

**負面影響 / 技術債：**

- 新增一個實體部署相依項目
- Relay 的身份驗證、連線穩定性、故障偵測都需要規格化
- demo 環境的可攜性降低——演講現場必須確認 relay 可達

**後續追蹤：**

- [ ] 決定 relay 硬體選型（Raspberry Pi 4B / Kali VM / 現有 lab 機器）
- [ ] 採購或部署 relay 節點
- [ ] 建立 SPEC-054「Target-Segment Relay Integration」
- [ ] 設計 Athena → relay 的 SSH tunnel 自動化（建議用 autossh + systemd）
- [ ] 設計 metasploit_client LHOST 動態配置（讀 `settings.RELAY_IP`）
- [ ] 回填 SPEC-053 的 Deferred 驗收（Gherkin S1 / S3 完整端到端 + 真實 shell）
- [ ] 考慮 fallback：若 relay 不可達，Orient 應把 reverse shell 類 exploit 標為 `service_unreachable` 避免誤推
- [ ] **短期臨時方案（本 ADR 作為等待期的記錄載體）**：SPEC-053 先以「Orient 推 T1190 但預期 exploit fail」為驗收標準；relay 到位後補做端到端

---

## 成功指標（Success Metrics）

**本 ADR 被 Accepted 的前提：**

- Relay 硬體或 VM 已可用
- SSH tunnel 到 relay 的 latency < 100ms
- 從 msf-rpc 容器透過 tunnel 到 relay 的 LHOST 可 bind 任意 payload port

**SPEC-054 實作成功的指標：**

| 指標 | 目標值 | 驗證方式 | 檢查時間 |
|------|--------|----------|----------|
| Reverse shell 類 exploit 成功率 | > 80% | 連續 10 次觸發 samba/distccd exploit 的 session 建立率 | SPEC-054 實作完成時 |
| LHOST 動態配置 | 100% 自動 | 不需要人工設 LHOST 即可觸發 reverse exploit | SPEC-054 實作完成時 |
| Relay 斷線偵測 | < 10s | relay 關掉後，metasploit exploit 回 `service_unreachable` 而非 silent timeout | SPEC-054 實作完成時 |
| Relay 身份驗證 | SSH key only | 禁用 SSH password auth | 部署時 |

**不應重新評估的情境：** 若 relay 實作完成後 Gherkin S1/S3 仍無法達成，代表問題不在 relay 而在 Orient prompt 或 metasploit_client——回到 SPEC-053 debug，不動本 ADR。

---

## 關聯（Relations）

- **取代**：（無）
- **被取代**：（無）
- **參考**：
  - [ADR-003] OODA Loop Engine Architecture
  - [ADR-020] Non-SSH Initial Access（metasploit engine 的設計基礎）
  - [ADR-024] MCP Architecture and Tool Server Integration（定義既有 docker bridge 拓撲）
  - [ADR-032] MCP Container Target Network Access（既有的 target 可達性設計）
  - [ADR-046] Orient-Driven Cross-Category Attack Pivot（本 ADR 解決其範圍外的網路限制）
  - [SPEC-041] Metasploit Stabilization and Access Recovery Completion
  - [SPEC-053] Orient-Driven Pivot and Metasploit One-Shot Exploit（本 ADR 解決其 Deferred 驗收項目的基礎設施前提）
  - **[SPEC-054]** Target-Segment Relay Integration for Reverse Shell Exploits（未來實作 SPEC，等 relay 部署後建立）
