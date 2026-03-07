# [ADR-033]: OODA Access Recovery and Credential Invalidation

| 欄位 | 內容 |
|------|------|
| **狀態** | `Accepted` |
| **日期** | 2026-03-07 |
| **決策者** | Athena Core Team |

---

## 背景（Context）

OODA 循環在 Act 階段透過 SSH 執行攻擊技術時，若受測機器的憑證被更改（例如密碼被修改），系統無法感知存取中斷：

1. `targets.is_compromised` 一旦設為 `1` 永不回退
2. 已失效的 `credential.ssh` fact 持續被查詢使用，導致後續所有 SSH 執行重複失敗
3. Orient 階段的 prompt 僅顯示 `COMPROMISED/SECURE` 二元狀態，無法反映「曾 compromised 但已失去存取」
4. Attack Graph 因 fact 仍存在而將依賴已失效憑證的節點標記為 `PENDING`（應為 `UNREACHABLE`）

實際案例：對 Metasploitable2 進行 OODA 攻擊，Iteration #2 後密碼被更改，Iteration #3、#4 的 Act 階段全數失敗（0/3、2/3 failed），系統未能切換至替代攻入路徑（vsftpd backdoor、Samba exploit）。

---

## 評估選項（Options Considered）

### 選項 A：被動偵測（Act 失敗觸發）

- **優點**：零額外延遲、實作簡單、不增加網路流量
- **缺點**：要到下一次 Act 階段執行 SSH 才會偵測到 access lost（最多延遲一個 OODA 迭代 ~30s）
- **風險**：低——OODA 迭代頻率為 30s，偵測延遲可接受

### 選項 B：主動 Health Check（Observe 階段 probe）

- **優點**：在 Observe 階段即可偵測 access lost，不浪費 Act 階段的執行機會
- **缺點**：每次迭代增加 2-5 秒延遲（SSH connectivity check）、增加網路流量
- **風險**：中——probe 本身可能觸發 IDS/IPS 告警

### 選項 C：憑證失效標記 — trait 重命名

- **優點**：不需 DB schema 變更（facts 表）、向後相容、查詢時用 `NOT LIKE` 即可排除
- **缺點**：trait 名稱語義稍不直觀
- **風險**：低

### 選項 D：憑證失效標記 — 新增 `is_valid` 欄位

- **優點**：語義清晰
- **缺點**：需要 DB migration、影響所有 fact 查詢
- **風險**：中——migration 風險、查詢效能影響

---

## 決策（Decision）

我們選擇 **選項 A（被動偵測）+ 選項 C（trait 重命名）**，因為：

1. 被動偵測的延遲（最多一個 OODA 迭代）在實際場景中可接受
2. trait 重命名不需變更 facts 表 schema，向後相容性最佳
3. 組合方案實作簡單，修改集中在 `engine_router.py`、`orient_engine.py`、`attack_graph_engine.py` 三個檔案

具體機制：
- 在 `_finalize_execution()` 中偵測 SSH 認證失敗（比對錯誤關鍵字）
- 觸發 `_handle_access_lost()`：回退 `is_compromised`、重命名 credential trait、插入 `access.lost` fact
- targets 表新增 `access_status` 欄位追蹤存取狀態
- Orient prompt 顯示 `ACCESS_LOST` 狀態
- Attack Graph 排除 invalidated credential traits

---

## 後果（Consequences）

**正面影響：**
- OODA 循環能在一個迭代內感知 access lost 並切換至替代攻入路徑
- Orient 階段的 LLM 分析有更精確的態勢感知
- Attack Graph 正確反映依賴已失效憑證的節點狀態

**負面影響 / 技術債：**
- targets 表新增 `access_status` 欄位（小幅 schema 擴展）
- trait 重命名方式（`credential.ssh.invalidated`）需要在 fact 相關查詢中加入排除條件

**後續追蹤：**
- [ ] SPEC-037 實作完成
- [ ] 對 Metasploitable2 進行端對端驗證

---

## 成功指標（Success Metrics）

| 指標 | 目標值 | 驗證方式 | 檢查時間 |
|------|--------|----------|----------|
| 認證失敗偵測率 | 100% | 單元測試 | 實作完成時 |
| 憑證失效後替代路徑成功率 | > 0%（至少嘗試） | 整合測試 | 實作完成時 |
| 既有測試通過率 | 100% | `make test` | 實作完成時 |
| OODA 迭代延遲增量 | 0ms（被動偵測） | 計時 | 部署後 |

---

## 關聯（Relations）

- 取代：無
- 被取代：無
- 參考：ADR-003（OODA loop 架構）、ADR-004（semi-auto with manual override）、ADR-027（Agent Swarm）、SPEC-007（OODA loop engine）
