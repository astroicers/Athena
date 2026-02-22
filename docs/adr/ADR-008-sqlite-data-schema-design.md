# [ADR-008]: SQLite 資料模型與 Schema 設計

| 欄位 | 內容 |
|------|------|
| **狀態** | `Accepted` |
| **日期** | 2026-02-23 |
| **決策者** | 專案負責人 |

---

## 背景（Context）

Phase 2 需實作 Athena 的資料持久層：13 個 Enum、12 個 Pydantic Model、12 張 SQLite 資料表、35+ REST API 端點。資料架構設計直接影響前後端型別同步、API 設計、以及未來 PostgreSQL 遷移的難度。

需決策的核心問題：

1. 主鍵策略（UUID vs Auto-increment）
2. 資料隔離策略（作戰級 scope vs 全域共用）
3. 非結構化資料存儲（JSON TEXT vs 正規化）
4. 技術目錄定位（靜態 vs 動態）

---

## 評估選項（Options Considered）

### 主鍵策略

#### 選項 A：UUID（TEXT PRIMARY KEY）

- **優點**：前端可在 POST 前預生成 ID（offline-first friendly）；跨表引用語義清晰（`"OP-2024-017"` vs `42`）；未來遷移 PostgreSQL 原生支援 UUID
- **缺點**：TEXT 主鍵索引效能低於 INTEGER（POC 規模可忽略）
- **風險**：UUID 碰撞機率極低（2^122 空間）

#### 選項 B：Auto-increment INTEGER

- **優點**：SQLite 原生支援，效能最佳
- **缺點**：跨表引用需查詢才能知道 ID；遷移時需建立 UUID 映射；前端無法預生成
- **風險**：POC 可行，但正式版遷移成本高

### 資料隔離策略

#### 選項 A：作戰級 scope（`operation_id` 外鍵）

幾乎所有實體表都以 `operation_id` 為外鍵，資料天然按作戰行動隔離。

- **優點**：多作戰支援（Phase 8.1）不需重構；API 端點自然以 `/operations/{id}/...` 命名；資料查詢自帶 scope 過濾
- **缺點**：跨作戰情報共享需額外邏輯
- **風險**：POC 僅有一個作戰行動，此設計無額外成本但預留擴展性

#### 選項 B：全域共用（無 scope）

- **優點**：更簡單；查詢不需 WHERE operation_id = ?
- **缺點**：多作戰支援需大規模重構；技術執行紀錄混雜不同作戰
- **風險**：Phase 8.1 多作戰需求將觸發全資料庫重構

### 非結構化資料：JSON TEXT vs 正規化

#### 選項 A：JSON TEXT（用於 PentestGPT 推薦的 `options` 欄位）

`recommendations.options` 存儲 `List[TacticalOption]` 為 JSON TEXT。

- **優點**：PentestGPT 輸出結構可能隨 LLM 演進而變化，JSON 提供 schema 靈活性；SQLite 支援 `json_extract()` 查詢；避免為 3 個選項建立關聯表
- **缺點**：無法直接對 option 欄位建索引；Python 端需 json.loads() 反序列化
- **風險**：Pydantic 在 Python 端保證型別安全，SQLite 端不驗證

#### 選項 B：完全正規化（TacticalOption 獨立表）

- **優點**：完全關聯式；可對 technique_id 建索引
- **缺點**：查詢一次 recommendation 需 JOIN TacticalOption；增加 schema 複雜度
- **風險**：過度設計——`options` 永遠以整組讀寫，不需部分查詢

### 技術目錄定位

#### 選項 A：`techniques` 為靜態目錄，`technique_executions` 為作戰級紀錄

- **優點**：MITRE ATT&CK 技術定義不隨作戰改變；`risk_level` 標註在目錄層可跨作戰複用；`technique_executions` 記錄每次具體執行（含目標、引擎、狀態）
- **缺點**：新增 MITRE 技術需更新靜態目錄
- **風險**：MITRE ATT&CK 更新頻率低（季度），POC 可手動維護

#### 選項 B：每個作戰獨立的技術清單

- **優點**：作戰間技術定義可不同
- **缺點**：重複儲存大量 MITRE 定義；`risk_level` 無法跨作戰複用
- **風險**：資料冗餘

---

## 決策（Decision）

每個問題選擇 **選項 A**：

| 決策 | 選擇 | 關鍵理由 |
|------|------|---------|
| 主鍵 | UUID（TEXT） | 語義清晰 + 前端預生成 + PostgreSQL 遷移就緒 |
| 隔離 | 作戰級 scope | 預留 Phase 8 多作戰支援，零額外成本 |
| JSON | `options` 為 JSON TEXT | LLM 輸出彈性 + Pydantic 保證 Python 端型別安全 |
| 目錄 | 靜態 `techniques` + 作戰級 `executions` | MITRE 定義跨作戰複用 + `risk_level` 集中管理 |

關鍵 schema 約束：
- `c5isr_statuses` 使用 `UNIQUE(operation_id, domain)` — 每個作戰每個域僅一筆狀態
- `users` 為最小化 stub（callsign + role，無密碼欄位）— 詳見 ADR-011
- 所有外鍵使用 `ON DELETE CASCADE` 確保作戰刪除時連帶清理

---

## 後果（Consequences）

**正面影響：**

- API 端點自然以 `/operations/{id}/targets`、`/operations/{id}/ooda` 組織
- 前後端型別對映直觀：Python Enum → TypeScript enum、Pydantic Model → TypeScript interface
- SQLite → PostgreSQL 遷移時，UUID TEXT → UUID 原生型別轉換直接

**負面影響 / 技術債：**

- UUID TEXT 主鍵在 SQLite 的索引效能低於 INTEGER（POC 數據量 < 1000 筆，不影響）
- `recommendations.options` JSON TEXT 在 SQLite 端無 schema 驗證（依賴 Pydantic）
- `users` 表為 stub，Phase 8 需擴充為完整身份模型

**後續追蹤：**

- [ ] Phase 2.1：實作 13 個 Enum + 12 個 Pydantic Model
- [ ] Phase 2.2：實作 `database.py`（SQLite 連線）+ 12 張 CREATE TABLE
- [ ] Phase 2.3：載入 seed data 驗證 schema 完整性
- [ ] Phase 8.6：PostgreSQL 遷移時將 TEXT UUID 轉為原生 UUID

---

## 關聯（Relations）

- 取代：（無）
- 被取代：（無）
- 參考：ADR-001（SQLite 選型）、ADR-004（`risk_level` 在 techniques 目錄中）、ADR-011（users 表簡化策略）、ADR-012（c5isr_statuses 表的 C5ISR 框架映射）、docs/architecture/data-architecture.md（完整 Schema 定義）
