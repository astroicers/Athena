# 安全政策 Security Policy

## 支援版本 Supported Versions

| 版本 | 支援狀態 |
|------|---------|
| 0.1.x | :white_check_mark: 安全更新 |

> Athena 目前為 POC（Proof of Concept）階段。安全問題將盡力修復，但不保證即時回應。

---

## 回報漏洞 Reporting a Vulnerability

如果您發現 Athena 的安全漏洞，**請勿**在公開 Issue 中揭露。

### 回報方式

1. **GitHub Security Advisories**（推薦）
   - 前往 [Security Advisories](https://github.com/astroicers/Athena/security/advisories/new)
   - 填寫漏洞描述、影響範圍、重現步驟

2. **Email**
   - 寄信至專案維護者（請透過 GitHub Profile 取得聯絡方式）
   - 主旨格式：`[SECURITY] Athena — 漏洞簡述`

### 請提供以下資訊

- 漏洞類型（如 XSS、SQL Injection、認證繞過等）
- 受影響的檔案或元件路徑
- 重現步驟（越詳細越好）
- 潛在影響評估
- 建議的修復方式（若有）

---

## 回應時間 Response Timeline

| 階段 | 時間 |
|------|------|
| 確認收到 | 48 小時內 |
| 初步評估 | 7 天內 |
| 修復發佈 | 視嚴重度而定（Critical: 7 天 / High: 14 天 / Medium: 30 天） |

---

## 涵蓋範圍 Scope

### 在範圍內

- **Athena 核心平台**（`backend/`、`frontend/`）
- **API 端點**安全問題（認證、授權、注入）
- **Docker 配置**安全問題
- **依賴套件**已知漏洞

### 不在範圍內

- **MITRE Caldera** 本身的漏洞 → 請回報至 [mitre/caldera](https://github.com/mitre/caldera)
- **Shannon** 本身的漏洞 → 請回報至 [KeygraphHQ/shannon](https://github.com/KeygraphHQ/shannon)
- **PentestGPT** 本身的漏洞 → 請回報至 [GreyDGL/PentestGPT](https://github.com/GreyDGL/PentestGPT)
- **Mock 模式**中的假資料或測試行為
- **LLM API** 回應內容（Anthropic/OpenAI 端問題）
- 非安全性的一般 Bug（請使用 Issue 模板）

---

## 揭露政策 Disclosure Policy

我們遵循**負責任揭露**（Responsible Disclosure）原則：

1. 安全研究者回報漏洞
2. 我們確認並評估漏洞
3. 開發並測試修復方案
4. 發佈安全更新
5. **修復後 90 天**公開揭露漏洞細節

在修復發佈前，請勿公開揭露漏洞細節。

---

## 安全設計原則 Security by Design

Athena 的安全設計：

- **授權隔離**：Shannon（AGPL-3.0）僅透過 API 整合，無程式碼匯入
- **環境變數管理**：API 金鑰透過 `.env` 管理，不進入 Git
- **最小權限**：Docker 容器以非 root 使用者運行
- **輸入驗證**：Pydantic v2 模型驗證所有 API 輸入
- **Mock 模式**：無需真實 API 金鑰即可開發與測試

---

*感謝您協助讓 Athena 更安全！*
