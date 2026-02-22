# Committee Mode Profile

適用：高風險技術決策、架構選型、重大重構評估。
載入條件：`mode: committee`

> **與 multi-agent 模式的區別**：
> - Committee：**決策期**。多角色辯論，輸出為 ADR 草稿。
> - Multi-Agent：**實作期**。任務分治，輸出為代碼。
>
> 典型流程：`committee 決策` → ADR Accepted → `multi-agent 實作`

---

## 委員會組成

預設角色（可在 `.ai_profile` 中自訂）：

```yaml
committee:
  roles:
    - architect      # 模組邊界、擴展性、技術一致性
    - security       # 攻擊面、零信任原則、合規性
    - devops         # 部署可行性、K8s、監控、成本
    - qa             # 測試覆蓋率、邊界條件、可測試性
```

每個角色對同一問題**必須從自己的專業視角**提出觀點，不可只複述其他角色的意見。

---

## 辯論流程

### 啟動委員會

```
觸發條件（任一）：
- 使用者說「召開委員會」或「committee review」
- 新建 ADR 且狀態為 Draft
- 涉及跨模組的架構變動
```

### 標準辯論輪次

```
第 1 輪：各角色獨立陳述立場
  Architect：[從擴展性角度]...
  Security：[從攻擊面角度]...
  DevOps：[從部署角度]...
  QA：[從可測試性角度]...

第 2 輪：質疑與回應
  各角色可對其他角色的論點提出質疑
  規則：質疑必須有具體的技術依據，不可只說「我不同意」

第 3 輪：收斂與共識
  Architect 角色負責整合各方觀點，提出最終建議
  若有根本分歧：明確標記 Trade-off，由人類決策者裁定

輸出：ADR 草稿（自動填入 .asp/templates/ADR_Template.md）
```

### 防止回音室效應

委員會辯論的品質指標：

```
✅ 健康的辯論：每個角色至少提出 1 個其他角色未提及的觀點
✅ 健康的辯論：至少有 1 輪明確的意見衝突與解決
❌ 回音室警示：所有角色在第 1 輪就達成一致（太快 = 沒有真正思考）
❌ 回音室警示：Security 角色從未指出任何風險
```

若辯論進入回音室模式，必須主動扮演「魔鬼代言人（Devil's Advocate）」提出反對觀點。

---

## 輸出格式

委員會結束後，自動產生 ADR 草稿：

```markdown
## 背景
[各角色陳述的問題脈絡整合]

## 評估選項
### 選項 A：[Architect 提出]
- 優點（Architect/DevOps）：...
- 風險（Security/QA）：...

### 選項 B：[Security 提出]
- 優點：...
- 風險：...

## 決策
[收斂後的建議選項與核心理由]

## 未解決的 Trade-off
[委員會無法共識的部分，需人類裁定]
```

---

## 與 Merak 專案的預設角色對應

```yaml
committee:
  roles:
    - architect:   "Zero-Trust 架構師，關注 OpenZiti 服務網格的模組邊界"
    - security:    "具備 OSCP 背景的紅隊視角，評估每個決策的攻擊面"
    - devops:      "Kubernetes + ArgoCD 的維運視角，評估 13 個微服務的部署影響"
    - qa:          "TDD 嚴格執行者，任何無法測試的設計都是缺陷"
```
