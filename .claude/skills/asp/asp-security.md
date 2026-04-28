---
name: asp-security
description: |
  Security review — OWASP Top 10, credential scanning, attack surface analysis.
  Triggers: security, security review, 安全, 安全審查, 資安
---

# ASP Security — 安全審查

## 前置條件

- 有代碼變更待審查（git diff 或指定範圍）
- 或由品質門 G5 觸發

## 工作流

### Step 1: 確定審查範圍

```bash
git diff --stat HEAD~1  # 或指定的 commit 範圍
```

列出修改的檔案，識別安全相關模組（auth/, api/, middleware/, config/）。

### Step 2: OWASP Top 10 掃描

逐項檢查與修改相關的 OWASP 風險：

| # | 風險類別 | 檢查方式 |
|---|---------|---------|
| A01 | Broken Access Control | 審查 auth middleware, role 檢查 |
| A02 | Cryptographic Failures | 掃描硬編碼密鑰、弱加密算法 |
| A03 | Injection | SQL/NoSQL injection, command injection |
| A04 | Insecure Design | 業務邏輯缺陷 |
| A05 | Security Misconfiguration | CORS, headers, debug mode |
| A06 | Vulnerable Components | 依賴版本已知漏洞 |
| A07 | Auth Failures | 弱密碼規則, session 管理 |
| A08 | Data Integrity Failures | 反序列化, CI/CD 管線 |
| A09 | Logging Failures | 敏感資訊日誌, 缺少審計追蹤 |
| A10 | SSRF | 伺服器端請求偽造 |

### Step 3: 憑證掃描

```bash
grep -rn "password\|secret\|api_key\|token\|credential" --include="*.{go,py,ts,js,java}" . | grep -v test | grep -v vendor | grep -v node_modules
```

檢查結果：
- 硬編碼憑證 🔴 P0 → 立即升級
- 環境變數引用 ✅
- 設定檔引用 ✅（確認不在 git track 中）

### Step 4: 攻擊面分析

- API endpoint 暴露：新增的 public endpoint 是否需要認證？
- 資料流：敏感資料是否在日誌中出現？
- 輸入驗證：外部輸入是否有 sanitization？

### Step 5: 安全判定

| 判定 | 條件 | 動作 |
|------|------|------|
| **PASS** | 無安全風險 | 記錄判定 |
| **WARN** | 低風險，可接受 | 記錄 + 建議改善 |
| **FAIL** | 高風險 | escalate(P0) 或 GATE_FAIL |

## 參考

- Security 角色定義：`.asp/agents/sec.yaml`
- 升級協議：`.asp/profiles/escalation.md`
- 護欄規則：`.asp/profiles/guardrail.md`
