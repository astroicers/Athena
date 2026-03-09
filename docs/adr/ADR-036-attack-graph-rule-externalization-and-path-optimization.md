# [ADR-036]: 攻擊圖譜規則外部化與路徑最佳化

| 欄位 | 內容 |
|------|------|
| **狀態** | `Accepted` |
| **日期** | 2026-03-08 |
| **決策者** | Athena Core Team |

---

## 背景（Context）

ADR-028 確立了攻擊圖引擎（Attack Graph Engine），以 prerequisite-rule-based 的方式進行攻擊路徑規劃。經過程式碼審計，發現三個關鍵問題：

### 1. 規則覆蓋率嚴重不足

`attack_graph_engine.py` 第 45-130 行僅硬編碼 13 個 `TechniqueRule` 物件於 `_PREREQUISITE_RULES` 清單中。MITRE ATT&CK 框架包含 500 個以上的技術，目前覆蓋率僅約 2.6%。以下類別完全缺失或近乎缺失：

- **Privilege Escalation**：僅有 T1003.001（LSASS Memory），缺乏 SUID Abuse、Sudo Exploitation、Kernel Exploit、UAC Bypass 等常見提權技術
- **Defense Evasion**：零規則 -- 無任何規避偵測的技術定義
- **Windows/AD 攻擊鏈**：僅有 T1003.001，缺乏 Kerberoasting（T1558.003）、DCSync（T1003.006）、NTDS.dit 擷取、RDP/SMB/WinRM 橫向移動等 Active Directory 核心攻擊技術
- **Exfiltration**：零規則 -- 無資料外洩技術
- **Impact**：零規則 -- 無破壞性行動技術

此覆蓋率缺口直接導致攻擊圖引擎無法為多數真實滲透測試場景產生有意義的路徑規劃。

### 2. Dijkstra 權重公式語意混淆

目前的權重計算公式為：

```
W = 0.5*C + 0.3*IG + 0.2*(1-E)
```

其中 alpha=0.5、beta=0.3、gamma=0.2 為任意選定的係數。此公式計算的是「可取性（desirability）」，然後在 Dijkstra 演算法中以 `cost = 1.0 - W` 反轉為成本值。這種「先算好處再反轉」的做法在語意上令人困惑：

- 開發者難以直覺理解「成本」的實際意義
- 紅隊行動優先考量的是情報收益（information gain）與存取進展（access progress），而非單純追求高 confidence
- 缺乏風險成本（risk cost）維度 -- 高隱蔽性需求的場景無法正確建模
- 係數缺乏實證依據，無法解釋為何 confidence 佔比高達 50%

### 3. 過度激進的死支修剪（Dead-Branch Pruning）

當 T1110.001（Brute Force）執行失敗時，目前的修剪邏輯會移除所有共享 `service.open_port` 前置條件**且**相同 `tactic_id` 的兄弟節點。此邏輯過於激進：

- T1190（Exploit Public-Facing Application）被列為 T1110.001 的替代技術（alternative），且其攻擊向量與暴力破解完全不同（漏洞利用 vs. 密碼猜測）
- 但因 T1190 共享相同的前置條件（`service.open_port`）和戰術類別（Initial Access），被一併修剪
- 這導致在暴力破解失敗後，系統錯誤地放棄了仍然可行的漏洞利用路徑，嚴重影響攻擊圖的路徑完整性

---

## 評估選項（Options Considered）

### 規則儲存方案

#### 選項 A：擴展硬編碼規則（最小變更）

直接在 `attack_graph_engine.py` 的 Python 清單中新增更多 `TechniqueRule` 物件。

- **優點**：
  - 實作最簡單，無需引入新的檔案格式或載入機制
  - 不需額外的檔案 I/O 或解析依賴
- **缺點**：
  - 50 個以上規則寫在 Python 程式碼中極難維護，程式碼檔案將膨脹至數百行純資料定義
  - 無法依平台（Linux/Windows）過濾規則
  - 規則修改需要修改應用程式碼，無法由安全研究人員獨立貢獻
  - Code Review 時規則變更與邏輯變更混雜，難以區分
- **風險**：隨著規則數量增長，維護成本呈線性增加，最終成為開發瓶頸

#### 選項 B：YAML 規則外部化（推薦）

將規則遷移至 `backend/app/data/technique_rules.yaml`，啟動時載入並以 Pydantic 驗證。為 `TechniqueRule` 新增 `platforms` 和 `description` 欄位。

- **優點**：
  - 規則與程式碼分離，易於擴展、審閱和獨立版本控制
  - YAML 格式對安全研究人員友善，降低貢獻門檻
  - 可依平台欄位過濾，支援 Linux-only 或 Windows-only 規則集
  - `description` 欄位提供規則語意說明，提升可維護性
  - PyYAML 已為專案現有依賴，無需引入新套件
- **缺點**：
  - 啟動時新增檔案 I/O 和 YAML 解析開銷（預估約 50ms）
  - 需要實作 Pydantic schema 驗證邏輯
  - YAML 語法錯誤可能導致啟動失敗（需妥善處理錯誤）
- **風險**：低 -- YAML 解析為成熟技術，Pydantic 驗證可在啟動時即時回報格式錯誤

#### 選項 C：資料庫儲存規則

將規則儲存於 SQLite，透過 API 進行編輯。

- **優點**：
  - 支援執行時期動態修改，可依作戰需求即時調整規則
  - 可實現每個 Operation 的客製化規則集
- **缺點**：
  - 對目前需求而言屬於過度工程（over-engineering）
  - 需要額外的 migration 和 CRUD API 開發
  - 規則應與程式碼一同版本控制，資料庫儲存破壞此原則
  - 規則變更難以追蹤和回溯
- **風險**：增加系統複雜度，且規則脫離版本控制系統後，難以進行 Code Review 和變更審計

---

### Dijkstra 權重公式方案

#### 選項 D：保留「可取性反轉」做法，僅調整係數

維持現有的 `W = desirability` 再 `cost = 1 - W` 的架構，僅微調 alpha/beta/gamma 係數。

- **優點**：
  - 變更最小，不影響現有測試
- **缺點**：
  - 語意混淆的根本問題未解決 -- 「成本」依然是「好處的反面」，開發者仍難以直覺理解
  - 缺乏風險維度的建模能力
- **風險**：技術債持續累積，後續開發者更難理解和維護權重邏輯

#### 選項 E：直接成本公式（推薦）

以直接的成本語意重新設計公式：

```
cost = 0.35 * (1 - confidence) + 0.25 * (1 - information_gain) + 0.25 * risk_cost + 0.15 * effort_norm
```

其中 `risk_cost` 依風險等級對應：

| 風險等級 | risk_cost |
|----------|-----------|
| low | 0.1 |
| medium | 0.3 |
| high | 0.6 |
| critical | 1.0 |

`effort_norm = min(effort / 5.0, 1.0)`

係數設計依據：
- **0.35 confidence**：作戰成功率為首要考量，失敗的技術浪費時間且可能觸發警報
- **0.25 information_gain**：情報探索價值是紅隊行動的核心驅動力，高 IG 技術能開啟更多後續路徑
- **0.25 risk_cost**：隱蔽性對紅隊行動至關重要，高風險技術可能導致被偵測和存取喪失
- **0.15 effort**：時間為次要因素，但在同等條件下應優先選擇低耗時路徑

- **優點**：
  - 語意直觀 -- 數值越低代表越佳路徑，與 Dijkstra 最短路徑演算法天然契合
  - 四維成本模型覆蓋作戰決策的核心面向
  - 係數具備可解釋的設計依據
  - 新增風險維度，支援高隱蔽性場景的正確建模
- **缺點**：
  - 需要修改現有權重計算邏輯和相關測試
  - 係數仍需透過實戰資料持續校準
- **風險**：低 -- 公式變更為純計算層面，不影響圖結構和資料模型

---

### 修剪邏輯方案

#### 選項 F：保護替代技術免於修剪（推薦）

修改修剪邏輯，當修剪失敗節點的兄弟節點時，跳過任何出現在失敗節點 `alternatives` 清單中的技術。同時修改 `_propagate_prune`，在傳播修剪時檢查目標節點是否仍有未被修剪/未失敗的入邊（incoming alternative edge）。

- **優點**：
  - 修改範圍精確，僅影響修剪邏輯的判斷條件
  - 直接解決 T1190 被錯誤修剪的問題
  - 保留死支修剪的效能優勢，同時避免誤殺可行路徑
  - 實作簡單，測試容易驗證
- **缺點**：
  - 無顯著缺點
- **風險**：極低 -- 變更範圍明確，不涉及資料結構修改

---

## 決策（Decision）

我們選擇 **選項 B + 選項 E + 選項 F** 的組合方案，因為：

1. **選項 B（YAML 規則外部化）** 在可維護性與實作複雜度之間取得最佳平衡。規則與程式碼分離使安全研究人員能獨立貢獻新規則，而 Pydantic 驗證確保規則格式的正確性。PyYAML 已為現有依賴，無需引入額外套件。

2. **選項 E（直接成本公式）** 從根本解決語意混淆問題。四維成本模型（confidence、information_gain、risk_cost、effort）完整覆蓋紅隊決策的核心考量，且係數具備可解釋性。

3. **選項 F（保護替代技術）** 以最小變更修復修剪邏輯缺陷，確保暴力破解失敗不會錯誤地排除漏洞利用等替代攻擊路徑。

### YAML 規則格式

```yaml
version: "1.0"
rules:
  - technique_id: "T1595.001"
    tactic_id: "TA0043"
    required_facts: []
    produced_facts: ["network.host.ip", "service.open_port"]
    risk_level: "low"
    base_confidence: 0.95
    information_gain: 0.9
    effort: 1
    enables: ["T1595.002", "T1190", "T1110.001"]
    alternatives: []
    platforms: ["linux", "windows"]
    description: "Active Scanning: Scanning IP Blocks"
```

各欄位說明：

| 欄位 | 類型 | 說明 |
|------|------|------|
| `technique_id` | string | MITRE ATT&CK 技術 ID |
| `tactic_id` | string | MITRE ATT&CK 戰術 ID |
| `required_facts` | list[string] | 執行此技術所需的前置情報 |
| `produced_facts` | list[string] | 此技術成功後產生的情報 |
| `risk_level` | string | 風險等級：low / medium / high / critical |
| `base_confidence` | float | 基礎成功信心分數 (0.0-1.0) |
| `information_gain` | float | 預期情報收益 (0.0-1.0) |
| `effort` | int | 估計 OODA 迭代數 |
| `enables` | list[string] | 成功後啟用的後續技術 ID |
| `alternatives` | list[string] | 替代技術 ID（修剪時保護） |
| `platforms` | list[string] | 適用平台：linux / windows |
| `description` | string | 規則的語意說明 |

### 規則載入機制

模組層級的 `_load_rules()` 函式在應用啟動時執行：

1. 讀取 `backend/app/data/technique_rules.yaml`
2. 以 Pydantic model 驗證每條規則的欄位類型和值域
3. 建構 `_RULE_BY_TECHNIQUE: dict[str, TechniqueRule]` 快取字典
4. 驗證失敗時拋出明確的錯誤訊息，包含行號和欄位名稱

### 直接成本公式

```python
RISK_COST_MAP = {
    "low": 0.1,
    "medium": 0.3,
    "high": 0.6,
    "critical": 1.0,
}

def compute_edge_cost(target_node: AttackNode) -> float:
    """
    直接成本公式 -- 數值越低代表越佳路徑。

    cost = 0.35*(1-confidence) + 0.25*(1-information_gain)
         + 0.25*risk_cost + 0.15*effort_norm
    """
    risk_cost = RISK_COST_MAP.get(target_node.risk_level, 0.3)
    effort_norm = min(target_node.effort / 5.0, 1.0)
    return (
        0.35 * (1.0 - target_node.confidence)
        + 0.25 * (1.0 - target_node.information_gain)
        + 0.25 * risk_cost
        + 0.15 * effort_norm
    )
```

### 修剪邏輯修正

修改 `_prune_siblings()` 和 `_propagate_prune()` 的行為：

1. **`_prune_siblings()`**：遍歷共享相同前置條件和戰術類別的兄弟節點時，若該兄弟節點的 `technique_id` 出現在失敗節點的 `alternatives` 清單中，則跳過修剪
2. **`_propagate_prune()`**：在向下傳播修剪時，檢查目標節點是否仍有至少一條來自未被修剪/未失敗節點的入邊。若有，則該節點不應被修剪

### 規則擴展優先順序

目標：從 13 條規則擴展至 50 條以上，覆蓋至少 5 個 MITRE 戰術類別。

**P1 -- Windows/Active Directory（新增約 15 條）**：
- Kerberoasting（T1558.003）
- DCSync（T1003.006）
- NTDS.dit 擷取（T1003.003）
- RDP 橫向移動（T1021.001）
- SMB 橫向移動（T1021.002）
- WinRM 橫向移動（T1021.006）
- UAC Bypass（T1548.002）
- Registry Run Keys 持久化（T1547.001）
- Scheduled Task 持久化（T1053.005）
- Pass the Hash（T1550.002）
- Pass the Ticket（T1550.003）
- Golden Ticket（T1558.001）
- Silver Ticket（T1558.002）
- Windows Service 建立（T1543.003）
- DCOM 橫向移動（T1021.003）

**P2 -- Linux 提權（新增約 10 條）**：
- SUID/SGID Abuse（T1548.001）
- Sudo Exploitation（T1548.003）
- Kernel Exploit（T1068）
- Cron Job 持久化（T1053.003）
- SSH Key 持久化（T1098.004）
- LD_PRELOAD Hijacking（T1574.006）
- Shared Library Injection（T1574.001）
- /etc/passwd 修改（T1136.001）
- Capabilities Abuse（T1548.001 變體）
- Container Escape（T1611）

**P3 -- 補足缺失類別（新增約 12 條）**：
- DNS Exfiltration（T1048.001）
- HTTPS Exfiltration（T1048.002）
- Data Staged（T1074.001）
- Service Stop（T1489）
- Data Encrypted for Impact（T1486）
- Account Discovery（T1087.001）
- Permission Groups Discovery（T1069.001）
- Network Share Discovery（T1135）
- Remote System Discovery（T1018）
- System Information Discovery（T1082）
- File and Directory Discovery（T1083）
- Process Discovery（T1057）

---

## 後果（Consequences）

**正面影響：**

- **規則可擴展性大幅提升** -- YAML 外部化使新增規則僅需編輯資料檔案，無需修改應用程式碼。安全研究人員可透過 Pull Request 獨立貢獻新規則，降低協作門檻
- **路徑品質改善** -- 直接成本公式消除語意混淆，四維模型（confidence、information_gain、risk_cost、effort）使 Dijkstra 演算法能更準確地反映紅隊決策邏輯
- **修剪行為正確化** -- 替代技術保護機制確保暴力破解失敗不會誤殺漏洞利用路徑，攻擊圖保留所有可行的攻擊向量
- **平台感知能力** -- `platforms` 欄位使引擎能依目標作業系統過濾規則，避免在 Linux 目標上建議 Windows-only 攻擊技術
- **規則覆蓋率從 2.6% 提升至 10%+** -- 50 條以上規則覆蓋至少 5 個 MITRE 戰術類別，顯著改善攻擊圖的路徑規劃能力

**負面影響 / 技術債：**

- **YAML 檔案維護成本** -- `technique_rules.yaml` 成為需要持續維護的資料檔案，隨 MITRE ATT&CK 版本更新需同步調整
- **啟動時間微增** -- YAML 載入和 Pydantic 驗證增加約 50ms 啟動時間（在可接受範圍內）
- **權重公式變更影響既有測試** -- 從「可取性反轉」切換至「直接成本」需更新所有與權重計算相關的測試案例
- **係數校準為持續工作** -- 0.35/0.25/0.25/0.15 係數雖有設計依據，但仍需透過實戰資料持續校準以達最佳效果

**後續追蹤：**

- [ ] 建立 `backend/app/data/technique_rules.yaml`，遷移現有 13 條硬編碼規則
- [ ] 實作 Pydantic 驗證 schema 和 `_load_rules()` 載入函式
- [ ] 重構 `compute_edge_weight()` 為 `compute_edge_cost()` 直接成本公式
- [ ] 修改 `_prune_siblings()` 和 `_propagate_prune()` 加入替代技術保護邏輯
- [ ] 依 P1/P2/P3 優先順序擴展規則至 50 條以上
- [ ] 更新所有受影響的單元測試和整合測試
- [ ] 驗證修剪修正：T1110.001 失敗後 T1190 不被修剪

---

## 成功指標（Success Metrics）

| 指標 | 目標值 | 驗證方式 | 檢查時間 |
|------|--------|----------|----------|
| YAML 規則載入 | 啟動時無錯誤完成載入 | `_load_rules()` 單元測試 + 整合測試 | 實作完成時 |
| 規則數量 | >= 50 條規則 | `len(_RULE_BY_TECHNIQUE)` 斷言 | 規則擴展完成時 |
| MITRE 戰術覆蓋 | >= 5 個戰術類別 | 統計規則中不重複的 `tactic_id` 數量 | 規則擴展完成時 |
| Dijkstra 路徑品質 | 優先選擇高 IG + 高 confidence 路徑，而非僅低風險路徑 | 建構測試場景：兩條路徑分別為「低風險低 IG」和「中風險高 IG」，驗證後者被優先推薦 | 公式重構完成時 |
| 修剪正確性 | T1110.001 失敗不修剪 T1190 | 單元測試：brute force 失敗後驗證 exploit 節點狀態仍為 pending | 修剪修正完成時 |
| 既有測試相容性 | 現有攻擊圖測試全數通過 | `make test-filter FILTER=attack_graph` | 全部變更完成時 |
| 啟動時間影響 | YAML 載入 < 100ms | `time.perf_counter()` 量測 | 實作完成時 |

> **重新評估觸發條件**：若規則數量超過 200 條且 YAML 檔案維護成本顯著增加，應評估是否遷移至結構化資料庫或引入自動化規則生成工具。

---

## 關聯（Relations）

- 部分取代：ADR-028（規則儲存方式和權重計算公式 -- 從硬編碼改為 YAML 外部化，從可取性反轉改為直接成本公式）
- 參考：ADR-028（攻擊圖引擎的核心架構和資料結構維持不變）
- 參考：SPEC-031（攻擊圖規格書）
