# [ADR-110]: russh 作為 SSH 執行後端

| 欄位 | 內容 |
|------|------|
| **狀態** | `Accepted` |
| **日期** | 2026-05-10 |
| **決策者** | Athena Team |

## 背景

需要在 Rust 中執行 SSH 命令作為主要遠端執行引擎。

## 決策

使用 `russh 0.44` + `russh-keys 0.44` 實作 `athena-exec-ssh`。`SshExecutionEngine` 實作 `ExecutionEngine` trait，支援密碼和公鑰認證。

## 後果

- **正面**：純 Rust 實作，無 C 依賴
- **負面**：russh API 較 OpenSSH 低階，需要手動管理 channel lifecycle
- **替換條件**：若 russh 有安全漏洞，可換實作 `ExecutionEngine` trait 的其他 SSH 庫

## 關聯

- 取代：ADR-017（隱含）
