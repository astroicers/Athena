---
name: asp-audit
description: |
  Use when checking project health, running audits, or before major releases.
  Runs 7-dimension health audit and classifies issues as Blocker/Warning/Info.
  Triggers: audit, health check, health audit, project health, project status,
  審計, 健康審計, 健康檢查, 專案健康, 審查專案狀態, 跑審計, run audit,
  check health, how healthy is this project.
---

# ASP Audit — 健康審計

## 適用場景

用戶想了解專案健康狀態，或在大型功能前/後做完整盤點。

---

## 選擇審計深度

詢問用戶（或根據上下文判斷）：

| 深度 | 指令 | 適用場景 |
|------|------|---------|
| 快速掃描 | `make audit-quick` | 只需確認無 blocker |
| 完整審計 | `make audit-health` | 完整 7 維度分析 |
| 文件新鮮度 | `make doc-audit` | 只關心文件是否過期 |
| Tech Debt | `make tech-debt-list` | 只看技術債 |

若用戶未指定，執行**完整審計**。

---

## 完整審計：7 個維度

```bash
make audit-health
```

### 維度說明與判斷標準

| # | 維度 | Blocker 條件 | Warning 條件 |
|---|------|-------------|-------------|
| 1 | **測試覆蓋** | 核心模組無測試 | 覆蓋率低於基線 |
| 2 | **SPEC 覆蓋** | 功能有實作但無 SPEC | SPEC 欄位不完整 |
| 3 | **ADR 合規** | Draft ADR 有對應生產代碼 | ADR 引用的模組已變更 |
| 4 | **文件完整** | README 嚴重過期 | 文件缺少關鍵章節 |
| 5 | **程式碼衛生** | `tech-debt: HIGH` 逾期 | `tech-debt: MED` 積壓 >5 個 |
| 6 | **依賴健康** | 已知高危 CVE | 依賴版本嚴重落後 |
| 7 | **文件新鮮度** | 核心設計文件 >90 天未驗證 | 輔助文件 >180 天未驗證 |

---

## 解析輸出並分類

將 `make audit-health` 的輸出整理為：

```
🏥 專案健康審計報告
================================

🔴 Blocker（必須修復才能繼續開發）
  - [維度] 問題描述
    建議：make spec-new TITLE="AUDIT-FIX: 問題簡述"

🟡 Warning（建議處理，不阻擋）
  - [維度] 問題描述

🟢 Info（資訊，無需立即行動）
  - [維度] 觀察項目

================================
總覽：🔴 N blockers | 🟡 N warnings | 🟢 N info

健康評分：[A/B/C/D/F]
  A: 0 blocker, ≤2 warning
  B: 0 blocker, ≤5 warning
  C: 1-2 blocker
  D: 3+ blocker
  F: 核心模組無測試 或 ADR 嚴重違規
```

---

## Blocker 處理流程

對每個 Blocker，建議：

```bash
make spec-new TITLE="AUDIT-FIX: [問題簡述]"
```

在 SPEC 的 Goal 填入修復目標，Done When 填入可驗證的修復條件。

---

## 快速審計模式

```bash
make audit-quick
```

只輸出 Blocker 清單，適合每日確認無阻擋：

```
🔍 快速審計（僅 Blocker）
================================
✅ 無 Blocker — 可繼續開發
或
🔴 發現 N 個 Blocker：
  1. [問題]
  2. [問題]
================================
建議下一步：make audit-health 查看完整報告
```

---

## Tech Debt 專項分析

```bash
make tech-debt-list
```

按優先級輸出，格式：

```
📊 Tech Debt 彙總
================================
🔴 HIGH（N 個）
  - [CATEGORY] description (DUE: YYYY-MM-DD) [逾期/剩 N 天]

🟡 MED（N 個）
  - [CATEGORY] description (DUE: YYYY-MM-DD)

🟢 LOW（N 個）
  - [CATEGORY] description

================================
⚠️  逾期 HIGH tech-debt 視為 Blocker
```

---

## 常用搭配

```bash
make audit-quick          # 每日確認
make audit-health         # 週期性完整審計
make doc-audit            # 文件新鮮度
make tech-debt-list       # Tech Debt 彙總
make spec-list            # SPEC 覆蓋率確認
make adr-list             # ADR 狀態確認
```
