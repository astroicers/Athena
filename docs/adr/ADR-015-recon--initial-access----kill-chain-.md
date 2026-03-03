# [ADR-015]: Recon 與 Initial Access 引擎架構 — 補完 Kill Chain 前半段

| 欄位 | 內容 |
|------|------|
| **狀態** | `Accepted` |
| **日期** | 2026-02-28 |
| **決策者** | Athena 開發團隊 |

---

## 背景（Context）

Athena 的 OODA 循環從「已有 Caldera agent 在目標機器上」開始，跳過了：
- **TA0043 Reconnaissance** — 主動掃描、服務版本識別
- **TA0001 Initial Access** — 打入目標機器、植入 C2 agent

這導致使用者必須手動部署 agent，無法實現「輸入 IP 清單 → 全自動 Kill Chain」的核心願景。

現有 ADR-003（OODA 循環引擎架構）和 ADR-006（執行引擎抽象層）已定義了 `BaseEngineClient` 介面與 `KillChainStage.RECON` 枚舉，但尚無對應實作。

已評估的工具選項（參見 `docs/analysis/recon-pocket-integration-assessment.md`）：

| 工具 | 評估結果 |
|------|---------|
| AutoRecon | 輸出文字目錄樹，GPL-3.0，整合成本高，不適合 |
| Kali MCP | 設計給 Claude Desktop，非後端程式化整合，不適合 |
| Shannon | 白盒 Web 應用測試（需原始碼），不適合網路滲透 |
| recon-pocket 容器 | 工具層優良但 orchestration 層評分 2/10，需另立計畫 |
| **nmap (python-nmap)** | XML 輸出、Python 原生解析、Apache-compatible（外部呼叫），**選用** |
| **asyncssh** | 原生 async SSH、Metasploitable 標準 credential 測試，**選用** |

---

## 評估選項（Options Considered）

### 選項 A：ContainerEngineClient（recon-pocket 工具容器）

- **優點**：工具種類豐富（14 種），可擴展至 subfinder、nuclei 等
- **缺點**：orchestration 層需完全重寫，需 Docker-in-Docker 或 sibling container 設計，整合複雜度高
- **風險**：增加 Docker socket 暴露面積，開發週期長

### 選項 B：直接整合 nmap + asyncssh（本次決策）

- **優點**：最小依賴、原生 async、輸出結構化、與現有 `facts` 表完全相容
- **缺點**：功能範圍較窄，僅覆蓋 TA0043/TA0001，不含 Web 掃描
- **風險**：nmap 需在 Docker 容器中執行（已在 Dockerfile 安裝），asyncssh 需處理 host key 驗證

### 選項 C：Metasploit RPC（pymetasploit3）

- **優點**：覆蓋 Metasploitable 全部 exploit，業界標準
- **缺點**：需要獨立的 msfrpcd 服務容器，增加部署複雜度
- **風險**：msfrpcd 啟動慢，開發測試週期長

---

## 決策（Decision）

選擇**選項 B**（nmap + asyncssh）作為 Phase 12 實作範圍，以下為分階段策略：

- **Phase A（本次）**：`python-nmap` 執行 nmap `-sV -O --open --script=banner`，`asyncssh` 嘗試 SSH default credentials，成功後 bootstrap Caldera sandcat agent
- **Phase B（後期）**：評估 Metasploit RPC 整合，需另立 ADR-016
- **Phase C（後期）**：評估 ContainerEngineClient，需另立 ADR

### 架構設計

新增三個模組，不修改現有 OODA 核心：

```
backend/app/
├── models/recon.py             # ReconResult, ServiceInfo, InitialAccessResult
├── services/recon_engine.py    # ReconEngine：nmap 掃描 → facts 寫入
├── services/initial_access_engine.py  # InitialAccessEngine：SSH creds + agent bootstrap
└── routers/recon.py            # POST /operations/{id}/recon/scan
```

**Fact 格式（對應現有 FactCollector 類別）：**

| category | trait | value 範例 |
|----------|-------|-----------|
| `service` | `service.open_port` | `22/tcp/ssh/OpenSSH_7.4` |
| `network` | `network.host.ip` | `192.168.1.100` |
| `host` | `host.os` | `Linux_2.6.x` |
| `credential` | `credential.ssh` | `msfadmin:msfadmin@192.168.1.100:22` |

新增輕量追蹤表 `recon_scans`（不破壞現有 schema）。

---

## 後果（Consequences）

**正面影響：**
- 實現「輸入 IP → 全自動 Kill Chain」願景的前半段
- OrientEngine 可直接使用 recon facts 進行更精準的技術推薦
- 零前端改動（C5ISR 頁面已能顯示 facts）

**負面影響 / 技術債：**
- Metasploit RPC 整合（vsftpd backdoor 等 Metasploitable exploit）留至 Phase B
- nmap 需以 root 執行才能做 OS detection（`-O`），Docker 容器中已處理
- asyncssh known_hosts 驗證停用（`known_hosts=None`）適合滲透測試環境，不適合生產
- ✅ 同步阻塞問題已由 ADR-023 解決：`POST /recon/scan` 改為 202 Accepted + 後台執行 + WebSocket 進度推送

**後續追蹤：**
- [ ] ADR-016：Metasploit RPC 整合架構
- [ ] ADR-017：ContainerEngineClient 工具容器編排
- [ ] 更新 Dockerfile 確認 nmap 已安裝
- [ ] 更新 architecture.md 加入 Recon + Initial Access 模組

---

## 關聯（Relations）

- 取代：（無）
- 被延伸：ADR-023（同步阻塞技術債由 ADR-023 解決）
- 依賴：ADR-003（OODA 循環）、ADR-006（執行引擎抽象層）、ADR-008（SQLite Schema）
- 參考：`docs/analysis/recon-pocket-integration-assessment.md`
