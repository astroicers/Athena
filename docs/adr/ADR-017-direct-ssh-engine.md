# [ADR-017]: DirectSSHEngine — SSH 直接執行引擎

| 欄位 | 內容 |
|------|------|
| **狀態** | `Accepted` |
| **日期** | 2026-03-02 |
| **決策者** | 專案負責人 |

---

## 背景（Context）

Phase B 確認 Caldera 執行引擎存在根本架構矛盾：
- Caldera 要求「先部署 alive agent → 才能執行 technique」
- Athena 的設計哲學是「SSH 憑證取得 → 立即推進 kill chain」
- 兩者順序倒置，導致 OODA Act 階段無法自動化

額外問題：
1. sandcat agent 不支援 Linux kernel 2.6.x（Metasploitable 2 等老式靶機）
2. WSL2/NAT 環境下 callback URL 設定複雜，30s beacon timeout 不可靠
3. 所有測試均使用 `MOCK_CALDERA=true`，Caldera 路徑從未真實跑通

---

## 評估選項（Options Considered）

### 選項 A：補強 Caldera bootstrap 測試

補充 `bootstrap_caldera_agent()` 的 unit tests + 修正 WSL2 callback URL。

- **優點**：保持現有架構
- **缺點**：根本矛盾（順序倒置）仍存在；kernel 版本限制無法解決

### 選項 B：DirectSSHEngine（SSH 直接執行）

SSH 憑證取得後，直接用 asyncssh 執行 MITRE technique 對應的 Shell 命令。

- **優點**：無需 C2 部署；任何 SSH 可達靶機均支援；OODA 自動化真正閉環
- **缺點**：初期命令映射需人工維護（13 個，可擴充）

### 選項 C：Metasploit RPC 整合

透過 Metasploit Framework 的 RPC API 執行 exploit。

- **優點**：覆蓋更廣的漏洞利用
- **缺點**：複雜度高，依賴 Metasploit 安裝；留待 Phase C

---

## 決策（Decision）

選擇 **選項 B：DirectSSHEngine**。

實作 `BaseEngineClient` 介面（`app/clients/__init__.py`），以 asyncssh 直接執行 MITRE technique 對應的 Shell 命令：

```
app/clients/direct_ssh_client.py
├── TECHNIQUE_EXECUTORS: dict[str, str]  — MITRE ID → shell command
├── TECHNIQUE_FACT_TRAITS: dict[str, list[str]]  — MITRE ID → fact traits
├── DirectSSHEngine.execute()  — SSH connect + run + parse facts
├── DirectSSHEngine.list_abilities()  — return supported MITRE IDs
└── DirectSSHEngine.is_available()  — always True
```

新增設定：
```python
EXECUTION_ENGINE: str = "ssh"   # "ssh" | "caldera" | "mock"
CALDERA_MOCK_BEACON: bool = False
```

---

## Technique Playbook（初始 13 個）

| MITRE ID | 用途 | 產出 fact traits |
|----------|------|-----------------|
| T1592 | 系統資訊收集 | host.os, host.user |
| T1046 | 網路服務發現 | service.open_port |
| T1059.004 | Shell 命令執行 | host.process |
| T1003.001 | 密碼雜湊讀取 | credential.hash |
| T1087 | 帳號枚舉 | host.user |
| T1083 | 敏感設定檔發現 | host.file |
| T1190 | Web 服務探測 | service.web |
| T1595.001 | 主動掃描（服務版本） | network.host.ip |
| T1595.002 | 主動掃描（漏洞腳本） | vuln.cve |
| T1021.004 | SSH 橫向移動 | host.session |
| T1078.001 | 有效帳號驗證 | credential.ssh |
| T1110.001 | 密碼暴力破解 | credential.ssh |
| T1110.003 | 憑證噴灑 | credential.ssh |

---

## 後果（Consequences）

**正面影響：**
- 無需部署外部 C2（Caldera server + sandcat agent），架構大幅簡化
- 任何能 SSH 的 Linux 靶機都能測試（不受 kernel 版本限制）
- SSH 憑證取得後可立即推進 kill chain，OODA 自動化閉環
- Technique 命令庫可獨立擴充（見 ADR-018）

**技術債：**
- 目前僅支援 Linux/SSH，Windows（WinRM/SMB）留待 Phase C
- 命令注入防護：所有 `{command}` 參數必須白名單驗證
- asyncssh 連線池未實作（每次 technique 建立新連線）

---

## 關聯（Relations）

- 取代：Caldera 為必要執行引擎的設計假設
- 被取代：（無）
- 參考：ADR-006（BaseEngineClient 介面）、ADR-018（Technique Playbook 知識庫）、ADR-015（Recon & Initial Access）
