# Athena — 偵察工具擴展路線圖

> 版本：1.0 | 更新日期：2026-03-03
> 來源：從已歸檔的 [recon-pocket](https://github.com/astroicers/recon-pocket) 專案遷移

---

## 背景

Athena 的前身 Dark Nebula 系列專案（dark-nebula、dark-nebula-backend、dark-nebula-frontend）
及獨立偵察工具 recon-pocket 已全部歸檔（archived），功能整合至 Athena。

本文件記錄 Athena 目前已整合的偵察工具，以及從 recon-pocket 繼承的待整合工具優先級排序。

---

## 目前已整合

| 工具 / 服務 | 對應模組 | 功能 |
|-------------|---------|------|
| nmap (-sV -O -script=banner) | `ReconEngine` | Port 掃描 + 服務版本偵測 + OS 指紋 |
| crt.sh (SSL 透明度日誌) | `OSINTEngine` | 被動子域名枚舉 |
| subfinder | `OSINTEngine` | 被動子域名枚舉（多來源） |
| dnspython | `OSINTEngine` | DNS 解析（A/AAAA/CNAME） |
| NVD NIST v2 API | `VulnLookupService` | CVE 關聯查詢（28 個 CPE 映射） |

---

## 待整合工具（按優先級）

### P0 — Phase A 加強

當前 Phase A（Enterprise External Pentest）的能力缺口，應優先補足。

| 工具 | 類別 | 用途 | 整合方式建議 |
|------|------|------|-------------|
| nuclei | Web 漏洞掃描 | 基於模板的快速漏掃（7000+ 模板） | Docker subprocess，結果寫入 `vuln.cve` facts |
| enum4linux | SMB 枚舉 | 列舉 SMB 共享、使用者、群組 | Shell subprocess，結果寫入 `service.*` facts |

### P1 — Phase B 橫向移動

Phase B（Lateral Movement + Persistence）的偵察支援工具。

| 工具 | 類別 | 用途 | 整合方式建議 |
|------|------|------|-------------|
| smbclient | SMB 存取 | 連線 SMB 共享、列舉/下載檔案 | asyncio subprocess |
| smbmap | SMB 存取 | SMB 共享權限映射 | asyncio subprocess |
| snmpwalk | SNMP 枚舉 | 網路設備資訊收集（OID 遍歷） | asyncio subprocess |
| onesixtyone | SNMP 枚舉 | SNMP community string 暴力猜測 | asyncio subprocess |
| whatweb | Web 指紋 | Web 技術識別（CMS、框架、版本） | Docker subprocess |
| wafw00f | Web 指紋 | WAF 偵測與識別 | pip install + subprocess |

### P2 — 未來擴展

完善全面偵察能力的進階工具。

| 工具 | 類別 | 用途 |
|------|------|------|
| dirsearch | Web 目錄枚舉 | 常見路徑與檔案探測 |
| gobuster | Web 目錄枚舉 | 高效能目錄/DNS/vhost 暴力枚舉 |
| nikto | Web 漏掃 | 傳統 Web 伺服器弱點掃描 |
| wapiti | Web 漏掃 | 黑箱 Web 應用程式漏掃 |
| sqlmap | SQL 注入 | 自動化 SQL 注入檢測與利用 |
| xsstrike | XSS | 反射/儲存型 XSS 檢測 |
| feroxbuster | Web 目錄枚舉 | Rust 高效能遞迴目錄探測 |
| amass | 子域名枚舉 | OWASP 大規模子域名發現 |
| dnsrecon | DNS 枚舉 | DNS 紀錄枚舉 + Zone Transfer |
| sslscan | TLS 分析 | SSL/TLS 配置安全性檢測 |

---

## recon-pocket 原始工作流程參考

```
Domain → Whois → Subdomain Discovery → Live/Dead 分類
  → Service Detection (nmap)
    → HTTP(S) → Web 指紋 → 目錄枚舉 → 漏掃 → 參數發現 → 注入測試
    → SMB → enum4linux / smbclient / smbmap
    → SNMP → snmpwalk / onesixtyone
```

此工作流程已部分實現於 Athena 的 `OSINTEngine → ReconEngine → InitialAccessEngine` 流程中。

---

## 歸檔的相關 Repo

| Repo | 狀態 | 說明 |
|------|------|------|
| [dark-nebula](https://github.com/astroicers/dark-nebula) | Archived | K8s + Argo 編排（被 Athena Docker Compose 取代） |
| [dark-nebula-backend](https://github.com/astroicers/dark-nebula-backend) | Archived | Express.js API（被 Athena FastAPI 取代） |
| [dark-nebula-frontend](https://github.com/astroicers/dark-nebula-frontend) | Archived | Nuxt 3 前端（被 Athena Next.js 取代） |
| [recon-pocket](https://github.com/astroicers/recon-pocket) | Archived | 偵察工具集（核心功能整合至 Athena） |
