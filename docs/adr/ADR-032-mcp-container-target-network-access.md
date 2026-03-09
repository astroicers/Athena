# [ADR-032]: MCP 容器目標網路存取策略

| 欄位 | 內容 |
|------|------|
| **狀態** | `Accepted` |
| **日期** | 2026-03-07 |
| **決策者** | Athena Core Team |

---

## 背景（Context）

Athena 的 MCP 工具伺服器以 Docker 容器運行（`docker compose --profile mcp`）。部分工具需要直接連線到滲透測試目標 IP（位於宿主機 LAN），但 Docker 預設的 bridge network 與宿主機 LAN 隔離，導致：

- **nmap-scanner**：掃描完成但所有 port 顯示 filtered → 0 services found
- **credential-checker**：SSH/RDP/WinRM 連線逾時
- **attack-executor**：無法建立 SSH/WinRM session
- **web-scanner**：httpx/nuclei 無法到達目標
- **api-fuzzer**：HTTP fuzzing 無法到達目標 API

而以下工具僅需 Internet 存取（DNS 查詢、外部 API），bridge network 已足夠：

- **osint-recon**：crt.sh、DNS resolver
- **vuln-lookup**：NVD API

---

## 評估選項（Options Considered）

### 選項 A：`network_mode: host`

- **優點**：容器完全共享宿主機網路堆疊，可存取所有目標
- **缺點**：
  - 失去容器間 DNS 解析（`http://mcp-nmap:8080` 不可用，backend 連不到工具）
  - Linux 上所有容器共享 port namespace，7 個 MCP 容器都監聽 8080 會衝突
  - 需為每個容器配置不同 port，增加維護成本
- **風險**：安全邊界降低，容器可存取宿主機所有網路介面

### 選項 B：`extra_hosts` + bridge network（保留）

- **優點**：
  - 保留容器間 DNS（backend → `http://mcp-nmap:8080` 正常）
  - 無 port 衝突（每個容器在自己的 network namespace 中監聽 8080）
  - 最小變更：只加一行 `extra_hosts`
  - 目標可透過 `host.docker.internal` 或原始 IP 存取
- **缺點**：需 Docker 20.10+（`host-gateway` 支援）
- **風險**：WSL2 環境下 `host-gateway` 解析為 WSL2 虛擬閘道器，需確認可路由到 LAN

### 選項 C：自建 Docker network + macvlan

- **優點**：容器直接取得 LAN IP
- **缺點**：需額外網路配置、不同環境（WSL2/Linux/macOS）行為差異大、維護複雜
- **風險**：macvlan 在 WSL2 上不支援

---

## 決策（Decision）

選擇 **選項 B：`extra_hosts` + 保留 bridge network**。

### 適用範圍

需要存取目標 IP 的容器加入 `extra_hosts`：

```yaml
extra_hosts:
  - "host.docker.internal:host-gateway"
```

| 容器 | 加入 extra_hosts | 原因 |
|------|-----------------|------|
| mcp-nmap | ✅ | nmap 掃描目標 port |
| mcp-credential-checker | ✅ | SSH/RDP/WinRM 連線目標 |
| mcp-attack-executor | ✅ | SSH/WinRM 執行指令 |
| mcp-web-scanner | ✅ | httpx/nuclei 探測目標 |
| mcp-api-fuzzer | ✅ | HTTP fuzzing 目標 API |
| mcp-osint | ❌ | 僅 Internet（DNS/crt.sh） |
| mcp-vuln | ❌ | 僅 Internet（NVD API） |

### 工具伺服器行為

工具接收的 `target` 參數為使用者輸入的 IP（如 `192.168.0.23`）。容器內路由表已可透過 Docker bridge 的預設閘道器到達宿主機 LAN，`extra_hosts` 額外提供 `host.docker.internal` 別名作為備用。工具伺服器程式碼不需修改。

---

## 後果（Consequences）

**正面影響：**
- 所有需要目標存取的 MCP 容器可到達宿主機 LAN 上的目標
- 不影響現有容器間通訊（backend ↔ MCP servers）
- 最小侵入性修改：僅 docker-compose.yml 加 `extra_hosts`
- 新增工具時只需判斷是否需要目標存取，決定是否加入 `extra_hosts`

**負面影響 / 技術債：**
- 依賴 Docker 20.10+ 的 `host-gateway` 功能
- WSL2 環境需確認 LAN 路由可達性（WSL2 NAT 可能需額外設定）

**後續追蹤：**
- [ ] 驗證 WSL2 環境下容器到 LAN 目標的路由可達性
- [ ] 文件更新：README 加註 Docker 版本需求

---

## 關聯（Relations）

- 延伸：ADR-010（Docker Compose 部署拓樸）、ADR-024（MCP Architecture）
- 參考：ADR-011（無身份驗證下以 localhost 綁定緩解）
