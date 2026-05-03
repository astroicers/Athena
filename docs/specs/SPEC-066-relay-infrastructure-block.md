# SPEC-066：relay_available Infrastructure Block 規格

| 欄位 | 內容 |
|------|------|
| **規格 ID** | SPEC-066 |
| **關聯 ADR** | ADR-047（Target Relay，已 Superseded）、ADR-005（OODA 架構） |
| **估算複雜度** | 低 |
| **建議模型** | Haiku |
| **HITL 等級** | standard |
| **狀態** | ✅ 已實作（補文件） |
| **完成日期** | 2026-05-02 |

---

## 🎯 目標

記錄 `orient_engine.py` 中 `_format_relay_infrastructure()` 函數的完整行為規格，以及它產生的 Section 7.9 "INFRASTRUCTURE" 區塊如何影響 LLM 的 exploit 推薦決策（SPEC-054 relay-aware exploit selection）。

ADR-047 雖已 Superseded，但其核心行為（relay port forwarding、LHOST 注入）已移入 orient_engine 和 docker-compose，需要獨立文件記錄。

---

## 背景

Athena 部署在容器化環境中。當攻擊目標與 Athena 不在同一網段時，reverse shell payload（如 UnrealIRCd backdoor）無法直接回呼 Athena（因為 NAT/防火牆阻擋）。

解法是使用中繼機器（Relay）：
1. Relay 機器在攻擊目標同一網段，且有 SSH 可達 Athena
2. Athena 在 Relay 上建立 SSH reverse tunnel，把 Relay:4444 轉發到 msf-rpc container:4444
3. Metasploit 的 LHOST 設為 `settings.RELAY_IP`（Relay 的 IP）
4. Reverse shell 連回 Relay:4444 → tunnel → msf-rpc，Metasploit 取得 session

---

## 規格

### 1. `_format_relay_infrastructure()` 函數

**位置**：`backend/app/services/orient_engine.py:33-63`

**輸入**：`settings.RELAY_IP`（環境變數，預設 `""`）

**輸出格式**：

```
Relay Host: <RELAY_IP>
relay_available: true
Relay LHOST: <RELAY_IP>
Note: Reverse-shell exploits are viable. Metasploit LHOST is set to <RELAY_IP>.
```

或（無 relay 時）：

```
Relay Host: (not configured)
relay_available: false
Note: No relay configured. Avoid reverse-shell payloads. Prefer bind-shell or credential techniques.
```

**判斷邏輯**：
```python
relay_available = bool(settings.RELAY_IP and settings.RELAY_IP.strip())
```

### 2. LLM 決策影響（Rule #8 壓縮版）

Section 7.9 向 LLM 傳遞 `relay_available` 狀態。Rule #8 的 relay 相關規則為：

- `relay_available: false` → 避免 reverse-shell payload（UnrealIRCd、Samba usermap、distccd）；優先 bind-shell（vsftpd 2.3.4）或憑證技術
- `relay_available: true` → Reverse-shell exploit 可用；LHOST 自動注入，LLM 可正常推薦

### 3. Docker 配置（SPEC-054 實作）

```yaml
# docker-compose.yml msf-rpc service
ports:
  - "127.0.0.1:55553:55553"  # msfrpcd RPC — localhost only
  - "0.0.0.0:4444:4444"       # SPEC-054 reverse-shell handler — relay tunnel endpoint
```

Port 4444 綁定 `0.0.0.0` 使 SSH reverse tunnel 可連入。RPC port 55553 限制為 localhost。

### 4. 環境變數

| 變數 | 說明 | 預設值 |
|------|------|--------|
| `RELAY_IP` | Relay 機器的 IP（攻擊目標網段可達） | `""` （空字串 = 無 relay） |
| `MSF_LPORT` | Metasploit listener port | `4444` |

---

## 測試矩陣

| 場景 | 設定 | 驗證方式 | 通過條件 |
|------|------|---------|---------|
| 有 relay | RELAY_IP=10.0.0.99 | 呼叫 _format_relay_infrastructure() | relay_available: true，Relay LHOST: 10.0.0.99 |
| 無 relay | RELAY_IP="" | 呼叫 _format_relay_infrastructure() | relay_available: false |
| Docker port mapping | docker-compose.yml | 確認 msf-rpc ports 區塊 | 0.0.0.0:4444:4444 存在 |
| LLM relay 感知 | orient_engine 整合測試 | Section 7.9 包含 relay_available | relay_available 關鍵字出現 |

---

## 相依性

- `backend/app/config.py:settings.RELAY_IP` — 環境變數讀取
- `docker-compose.yml` — msf-rpc port 4444 映射
- `orient_engine.py:_format_relay_infrastructure()` — 格式化函數
- Rule #8（系統提示）— relay-aware exploit selection

---

## 驗收條件

- [ ] `_format_relay_infrastructure()` 在 RELAY_IP 非空時回傳 `relay_available: true`
- [ ] `_format_relay_infrastructure()` 在 RELAY_IP 為空時回傳 `relay_available: false`
- [ ] `docker-compose.yml` msf-rpc service 包含 `0.0.0.0:4444:4444` port mapping
- [ ] Orient Engine Section 7.9 包含 relay_available 狀態
- [ ] 系統提示 Rule #8 relay 區塊 < 250 chars（SPEC-064 token 最佳化）
