# System Development Profile

> 載入條件：`type: system` 或 `type: architecture`

適用：後端服務、微服務、Kubernetes、Docker、API 開發。

---

## ADR 工作流

### 何時必須建立/更新 ADR

| 情境 | 必要性 |
|------|--------|
| 新增微服務或模組 | 🔴 必須 |
| 更換技術棧（DB、框架、協議） | 🔴 必須 |
| 調整核心架構（Auth、API Gateway） | 🔴 必須 |
| 效能優化方向決策 | 🟡 建議 |
| 單一函數邏輯修改 | ⚪ 豁免 |

### ADR 狀態

```
Draft → Proposed → Accepted → Deprecated / Superseded by ADR-XXX
```

### 執行規則

- 提議方案前，先 `make adr-list` 確認是否與現有決策衝突
- ADR 狀態為 `Draft` 時，不應有對應的生產代碼
- `Accepted` ADR 被推翻時，必須建立新 ADR 說明原因，不可直接修改舊 ADR

---

## 標準開發流程

```
ADR（為什麼）→ SDD（如何設計）→ TDD（驗證標準）→ BDD（業務確認）→ 實作 → 文件
```

**允許的簡化路徑（需在回覆中說明）：**

- 緊急 Bug 修復：直接實作 → 測試 → 補 ADR（若涉及架構）
- 原型驗證：實作 → 測試後補（標記 `tech-debt: test-pending`）
- 明確小功能：可跳過 BDD，直接 TDD

---

## 環境管理

以下動作統一使用 Makefile，禁止輸出原生指令：

```
make build    建立 Docker Image
make clean    清理暫存與未使用資源
make deploy   重新部署（需確認）
make test     執行測試套件
make diagram  更新架構圖
make adr-new  建立新 ADR
make spec-new 建立新規格書
```

---

## 部署前檢查清單

```
□ 環境變數完整（對照 .env.example）
□ 所有測試通過（make test）
□ ADR 已標記 Accepted
□ architecture.md 與當前代碼一致
□ Dockerfile 無明顯優化缺失
```

---

## 架構圖維護

- Mermaid 格式，存放於 `docs/architecture.md`
- 核心邏輯變動後必須更新
- 架構圖與代碼不一致 = 技術債，本次任務結束前修正
