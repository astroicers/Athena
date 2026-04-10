# [ADR-047]: Target-Segment Relay for Reverse Shell Connectivity

| 欄位 | 內容 |
|------|------|
| **狀態** | `Accepted` |
| **日期** | 2026-04-09 / 決策簡化 2026-04-10 |
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

**最終決策（2026-04-10）：採用選項 C 的「最小化部署模型」**。

使用者於 2026-04-10 提出簡化方案，取代原先規劃的「autossh + systemd 永久部署」。經評估後確認這個簡化版本保留了選項 C 的核心價值（docker 網路隔離不動、reverse shell 可通），同時大幅降低維運摩擦：

### 簡化決策的五個核心特徵

1. **使用者手動啟動 relay 機器**：不鎖硬體選型（可以是 Raspberry Pi、Kali VM、現有 lab 機器、甚至另一台 host），只要能 SSH 且在 `192.168.0.x` 網段即可
2. **Athena 生成一次性腳本**：`make relay-script` 產出 `tmp/athena-relay.sh`，使用者 `scp` 到 relay 執行
3. **SSH reverse tunnel**：腳本透過 `ssh -R 4444:athena_host:4444 user@relay` 建立 tunnel，Athena 主動出站連線、不需 docker port mapping
4. **固定 LPORT = 4444**：符合 SPEC-053 one-shot 模式的「一次 exploit → probe → release，不並發」語義
5. **Foreground + trap cleanup**：`set -euo pipefail` + `trap cleanup EXIT SIGINT SIGTERM`，Ctrl+C 立即清理、無殘留 process、無 PID file、無 systemd unit

### 為何簡化而非原先的「autossh + systemd」方案

原先規劃裡 autossh + systemd 的目標是「relay 一次部署、永久運行」。但這會引入：
- Systemd unit 維運負擔（enable/disable/status）
- 重新部署 Athena 時的 relay state 同步問題
- 演講 demo 當天若 relay 狀態異常、debug 路徑過長
- 與 SPEC-053 one-shot 精神不符（one-shot = 每次獨立、無跨 iteration state）

簡化版本失去「無人值守 24×7 運行」，但對演講 demo 場景而言完全夠用——演講時使用者會人工啟動腳本 + 全程監看。

### 具體實作由 SPEC-054 定義

- `backend/app/config.py` 新增 `RELAY_IP`, `RELAY_SSH_USER`, `RELAY_SSH_PORT`, `RELAY_LPORT`, `RELAY_ATHENA_HOST` 五個 settings
- `backend/app/clients/metasploit_client.py` 的 `exploit_samba`, `exploit_unrealircd` 從 `settings.RELAY_IP` 讀 LHOST（取代 hardcoded `0.0.0.0`）
- `backend/app/services/orient_engine.py` 新增 Section 7.9 Infrastructure + Rule #8/#9 relay-aware 條件：`RELAY_IP == ""` 時 prompt 引導 LLM 避免推薦 reverse shell 類 exploit
- `backend/app/cli/generate_relay_script.py` 產生腳本的 CLI
- `Makefile` 新增 `relay-script` target
- 完整規格見 **SPEC-054**

---

## 後果（Consequences）

**正面影響：**

- Reverse shell 類 exploit（samba / distccd / UnrealIRCd）真實可打通
- Athena 具備完整的 MITRE ATT&CK TA0001 (Initial Access) 覆蓋能力
- 未來可擴展至跨網段 lateral movement（relay 作為跳板）
- 符合 industry 真實滲透測試架構
- SPEC-053 Deferred 項目（Gherkin S1 / S3）在簡化模型下可解鎖

### 最小化模型的取捨（2026-04-10 簡化決策）

**失去：**

- ❌ 自動重連：relay 機器重啟後需人工重跑腳本
- ❌ 多 relay failover：單點故障可能性存在
- ❌ 無人值守 24×7 運行：演講以外的長期 lab 使用須手動啟動
- ❌ Systemd service 管理：不提供 enable/disable/status 指令

**獲得：**

- ✅ 零部署摩擦：使用者手動啟動機器 + 跑腳本，不需要事先安裝 autossh/systemd/container runtime
- ✅ 零殘留風險：Ctrl+C 即清理，無 PID file、無 systemd unit、無 crontab 殘留
- ✅ 演講 demo 可控性：腳本 foreground 執行，所有狀態在眼前，任何異常即時可見
- ✅ 無跨 iteration state：符合 SPEC-053 one-shot 設計精神
- ✅ 硬體選型不鎖：Raspberry Pi / Kali VM / 現有機器皆可

**負面影響 / 技術債：**

- 新增一個實體部署相依項目（但門檻降到「起一台機器 + 跑腳本」）
- Relay SSH key 需使用者自行管理（不在 Athena 範圍）
- demo 環境的可攜性降低——演講現場必須確認 relay 可達（但比原先 systemd 版本簡單）
- 固定 LPORT 4444 = 不支援 reverse shell 並發（可接受，符合 SPEC-053 one-shot 語義）

**後續追蹤：**

- [x] ~~決定 relay 硬體選型（Raspberry Pi 4B / Kali VM / 現有 lab 機器）~~（使用者自行決定，不鎖硬體）
- [x] ~~採購或部署 relay 節點~~（使用者手動啟動，不需事先部署）
- [x] 建立 **SPEC-054「Relay Port-Forwarding Script Generator for Reverse Shell Exploits」**
- [x] ~~設計 Athena → relay 的 SSH tunnel 自動化（autossh + systemd）~~（簡化為一次性腳本 + trap cleanup）
- [x] 設計 metasploit_client LHOST 動態配置（讀 `settings.RELAY_IP`）— SPEC-054 實作
- [ ] 執行 SPEC-054 實作（7 個測試檔 + 3 個新程式碼檔 + 文件同步）
- [ ] 回填 SPEC-053 的 Deferred 驗收（Gherkin S1 / S3 完整端到端 + 真實 shell）
- [x] Orient 感知 relay 狀態：`settings.RELAY_IP == ""` 時 Rule #8/#9 引導 LLM 避免推 reverse shell — SPEC-054 處理
- [x] ~~短期臨時方案~~（已不需要；SPEC-054 直接實作為最終方案）

---

## 成功指標（Success Metrics）

### ADR-047 Accepted 的前提（已滿足 2026-04-10）

- [x] 決策已簡化：不鎖硬體、不需 autossh/systemd、不需自動重連
- [x] 最小範圍 SPEC 已排程：SPEC-054 規格完成
- [x] 使用者確認承擔手動啟動 relay 的責任
- [x] `settings.RELAY_IP == ""` 時系統仍能運行（degraded mode）

### SPEC-054 實作成功的指標

| 指標 | 目標值 | 驗證方式 | 檢查時間 |
|------|--------|----------|----------|
| 腳本產生時間 | < 100ms | CLI benchmark | SPEC-054 實作完成時 |
| LHOST 從 settings 讀取 | 100% | `test_spec054_relay_lhost.py` | SPEC-054 實作完成時 |
| 腳本零殘留 | 0 個遺留 process / PID file | `test_spec054_script_cleanup.py` subprocess test | SPEC-054 實作完成時 |
| Orient relay awareness | prompt 含 `relay_available: true/false` | `test_spec054_orient_relay_awareness.py` | SPEC-054 實作完成時 |
| Degraded mode：未設 RELAY_IP 時不 crash | 100% | `test_spec054_relay_lhost.py` negative cases | SPEC-054 實作完成時 |
| Reverse shell 類 exploit 真實成功率（deferred） | > 80% | 使用者手動起 relay + 連續 10 次 samba exploit | Relay 部署後的使用者驗證 |

### 不應重新評估的情境

若 SPEC-054 實作完成後 SPEC-053 的 Gherkin S1/S3 仍無法達成，代表問題不在 relay 簡化模型，而在：
- Orient prompt Rule #8/#9（需回 SPEC-053 或發新 ADR）
- metasploit_client 的 exploit module 參數設定（回 metasploit 測試）
- 使用者 relay 機器上的 SSH 服務狀態（使用者環境問題）

在這些情況下**不動本 ADR 的簡化決策**。

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
  - **[SPEC-054]** Relay Port-Forwarding Script Generator for Reverse Shell Exploits（ADR-047 實作 SPEC；取代原計畫的「Target-Segment Relay Integration」全自動方案）
