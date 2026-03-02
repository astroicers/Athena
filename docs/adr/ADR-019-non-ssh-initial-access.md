# [ADR-019]: Non-SSH Initial Access — Metasploit RPC 整合

| 欄位 | 內容 |
|------|------|
| **狀態** | `Draft` |
| **日期** | TBD — Phase C 啟動後評估 |
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

## 狀態：Draft — 禁止實作

依據 `CLAUDE.md` 鐵則：「ADR 狀態為 Draft 時，禁止撰寫對應的生產代碼。」

本 ADR 待 Phase C 啟動後評估選型，進入 `Accepted` 狀態前不得撰寫生產代碼。

## 候選方案（評估中，未決定）

### 選項 A：Metasploit RPC（msfrpcd）
- 功能最完整，覆蓋大量 exploit
- 需要外部服務（Metasploit Framework）
- pymetasploit3 Python wrapper 可用

### 選項 B：自研 Exploit Stub
- 僅覆蓋 Metasploitable 2 已知漏洞（vsftpd / UnrealIRCd）
- 高維護成本，非通用
- 不推薦

## 參考

- [ADR-017](ADR-017-direct-ssh-engine.md)：DirectSSHEngine — 需 SSH 的技術債 TD-002
- [ADR-018](ADR-018-technique-playbook-knowledge-base.md)：Technique Playbook 知識庫
