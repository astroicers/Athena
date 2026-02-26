# SPEC-011：開源發佈準備（Phase 7.2~7.4）

> 涵蓋開源合規、GitHub Repository 設定、首次發佈。

| 欄位 | 內容 |
|------|------|
| **規格 ID** | SPEC-011 |
| **關聯 ADR** | ADR-003（授權策略）、ADR-011（部署） |
| **估算複雜度** | 中 |
| **建議模型** | Sonnet |
| **HITL 等級** | standard |

---

## 🎯 目標（Goal）

> 完成 Athena POC 的開源發佈準備，包括授權合規、社群文件、CI/CD 管線，以及 v0.1.0 標記。

---

## 📋 範圍（Phase 7.2 ~ 7.4）

### 7.2 開源合規

- [x] 選定授權條款（Apache 2.0 — 與核心平台一致）
- [x] 所有原始碼檔案加上 License Header
- [x] `LICENSE` 檔案放置於根目錄
- [x] `SECURITY.md` — 負責任揭露政策
- [x] `CONTRIBUTING.md` — 貢獻指南（開發環境設定、PR 流程、Coding Style）
- [x] 驗證 Shannon AGPL-3.0 API 隔離合規性（僅 HTTP 呼叫，無 import）

### 7.3 GitHub Repository

- [ ] Repository 描述 + Topics 標籤（c5isr, mitre-attack, penetration-testing, ooda-loop, ai-security）
- [x] GitHub Actions CI（lint + type-check + build）
- [x] Issue 模板（Bug 回報、功能請求）
- [x] PR 模板
- [ ] README 截圖（4 個畫面 + 3D 拓樸）

### 7.4 首次發佈

- [x] 標記 `v0.1.0` — POC 版本
- [ ] GitHub Release 含 Changelog（從 CHANGELOG.md 擷取）
- [ ] Demo 影片 / GIF 展示 OODA 循環運作

---

## ⚠️ 邊界條件（Edge Cases）

- License Header 不適用於 `.json`、`.yml`、`.md` 等非原始碼檔案
- Shannon 客戶端程式碼必須僅包含 HTTP 呼叫，絕不 import Shannon 套件
- CI 不需要 Caldera 或外部服務 — 使用 `MOCK_LLM=True` + `MOCK_CALDERA=True`

---

## ✅ 驗收標準（Done When）

- [x] `LICENSE` 檔存在且為 Apache 2.0
- [x] `SECURITY.md` 存在，包含揭露流程
- [x] `CONTRIBUTING.md` 存在，包含開發設定步驟
- [x] 所有 `.py` 和 `.ts/.tsx` 檔案含 License Header
- [x] GitHub Actions CI 於 push 時自動執行
- [x] `git tag v0.1.0` 已建立
- [ ] GitHub Release 頁面包含 Changelog 內容
- [x] 已更新 `CHANGELOG.md`

---

## 🚫 禁止事項（Out of Scope）

- 不要修改核心業務邏輯（backend/app/services/、frontend/src/app/）
- 不要引入新的 runtime 依賴
- 不要加入正式環境部署配置（Kubernetes、Helm 等屬 Phase 8）

---

## 📎 參考資料（References）

- ADR-003：授權策略（Apache 2.0 核心 + AGPL API 隔離）
- ADR-011：部署架構
- docs/ROADMAP.md Phase 7.2~7.4
- CLAUDE.md 授權邊界段落
