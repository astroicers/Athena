# [ADR-020]: Non-SSH Initial Access — Metasploit RPC 整合

| 欄位 | 內容 |
|------|------|
| **狀態** | `Accepted` |
| **日期** | 2026-03-02 |
| **決策者** | 專案負責人 |

## 背景（Context）

`DirectSSHEngine` 與 `PersistentSSHChannelEngine` 均要求靶機有開放的 SSH 服務作為
初始進入點。以下場景目前無法處理：

| Technique | 原因 |
|-----------|------|
| T1190 vsftpd 2.3.4 backdoor | 透過 FTP 觸發 backdoor，非 SSH |
| T1190 UnrealIRCd exploit | IRC 協定注入，非 SSH |
| T1190 Samba usermap_script | SMB 協定，非 SSH |
| T1021.001 WinRM | Windows 遠端管理，非 SSH |

## 決策（Decision）

選擇 **選項 A：Metasploit RPC（msfrpcd）**，理由：

1. **覆蓋完整**：Metasploit Framework 涵蓋上述所有攻擊場景，無需自研 exploit stub。
2. **可 Mock CI 測試**：`MOCK_METASPLOIT=true`（預設）讓 CI 不依賴真實 Metasploit 服務。
3. **pymetasploit3**：成熟的 Python wrapper，降低整合風險。
4. **可擴展**：未來可透過 `get_exploit_for_service()` 動態路由到更多 module。

## 實作摘要

- `backend/app/clients/metasploit_client.py`：`MetasploitRPCEngine` 類別
- 支援四種 Non-SSH 技術：vsftpd backdoor、UnrealIRCd、Samba usermap_script、WinRM login
- `MOCK_METASPLOIT=true` 時全部回傳 mock success，無需 msfrpcd 服務
- `EngineRouter` 透過 `vuln.cve` fact（`exploit=true`）自動路由至 Metasploit

## 候選方案回顧

### 選項 A：Metasploit RPC（msfrpcd）✅ 選定
- 功能最完整，覆蓋大量 exploit
- 需要外部服務（Metasploit Framework）
- pymetasploit3 Python wrapper 可用

### 選項 B：自研 Exploit Stub ❌ 捨棄
- 僅覆蓋 Metasploitable 2 已知漏洞（vsftpd / UnrealIRCd）
- 高維護成本，非通用
- 不推薦

## 後果（Consequences）

- **正面**：覆蓋 SSH 以外的四種 Non-SSH 初始進入場景，顯著提升自動滲透測試的技術覆蓋率。
- **負面**：
  - 生產模式需要外部 `msfrpcd` 服務（`MOCK_METASPLOIT=false`）。
  - 每次 exploit 嘗試最多等待 30 秒（session 輪詢上限）。
  - 並發多目標時，session 歸屬依賴「新增 session」差分邏輯，非完美關聯。
- **風險**：若 `LHOST` 設為 `0.0.0.0`，反向 shell payload 將無法正確回呼；部署時須設定可路由的 IP。

## 參考

- [ADR-017](ADR-017-direct-ssh-engine.md)：DirectSSHEngine — 技術債 TD-002（本 ADR 解決）
- [ADR-018](ADR-018-technique-playbook-knowledge-base.md)：Technique Playbook 知識庫
