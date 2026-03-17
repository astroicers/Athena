# Athena 攻擊流程 SOP（標準作業程序）

> 本文件描述 Athena 平台從建立行動到完成攻擊的完整端對端流程。

---

## 一、流程總覽

```
建立行動 → 設定任務組態 → OODA 循環啟動 → 攻擊圖更新 → 持續迭代 → 行動完成
```

**核心架構**：OODA 決策循環 + C5ISR 態勢感知 + MITRE ATT&CK 技術圖譜

---

## 二、階段一：建立行動（Operation）

**入口**：Operations 頁面 → 新增行動

**必填欄位**：

| 欄位 | 說明 | 範例 |
|------|------|------|
| Code | 行動代碼 | `OP-2026-001` |
| Name | 行動名稱 | `內網滲透測試` |
| Codename | 行動代號 | `SHADOW STRIKE` |
| Strategic Intent | 戰略意圖 | `驗證內網橫向移動風險` |
| Mission Profile | 任務組態 | SR / CO / SP / FA（見下方） |

### 任務組態（Mission Profile）選擇指南

| 組態 | 名稱 | 適用情境 | 最大噪音 | 並行上限 | 最低信心值 | 偵測回應 |
|------|------|----------|----------|----------|-----------|----------|
| **SR** | Stealth Recon | 純偵察、不接觸目標 | 低 | 1 | 0.8 | 暫停並通知 |
| **CO** | Covert Operation | APT 模擬、長期潛伏 | 中 | 2 | 0.7 | 暫停並通知 |
| **SP** | Standard Pentest | 標準滲透測試 | 高 | 5 | 0.5 | 僅通知 |
| **FA** | Full Assault | 限時紅藍對抗演練 | 無限制 | 8 | 0.4 | 僅記錄 |

**操作步驟**：
1. 進入 `/operations` 頁面
2. 點擊「新增行動」
3. 填寫行動資訊並選擇適當的 Mission Profile
4. 確認建立 → 行動狀態設為 `planning`
5. 將行動狀態切換為 `active` → 系統導向 War Room

---

## 三、階段二：OODA 循環

行動啟動後，系統進入 OODA 決策循環。可手動觸發或啟用自動排程。

### 2.1 Observe（觀察）

**目的**：蒐集目標情報，建立事實集合

**系統行為**：
1. 從資料庫讀取已知事實（Facts）
2. 識別「稀疏情報」目標（事實數 < 3 的目標）
3. 對稀疏目標自動觸發偵察掃描（每次最多 3 個目標）
4. 透過 MCP 工具執行：
   - `nmap-scanner`：埠掃描、服務偵測、OS 指紋
   - `osint-recon`：子網域列舉、DNS 解析
   - `vuln-lookup`：CVE 查詢、CPE 映射
5. 收集結果寫入事實資料庫

**產出事實類型**：
- `host.alive` — 主機存活
- `port.open` — 開放埠號
- `service.banner` — 服務版本
- `credential.ssh` — SSH 憑證
- `host.session` — 已建立 Session

### 2.2 Orient（定向）

**目的**：基於事實產生戰術建議

**系統行為**：
1. PentestGPT（LLM）接收以下輸入：
   - 當前事實集合
   - 攻擊圖摘要（可用技術節點）
   - Kill Chain 進度（目前所在 MITRE ATT&CK 戰術階段）
   - Mission Profile 限制條件
2. 產生結構化建議：
   - **推薦技術** — MITRE 技術 ID + 信心值
   - **替代方案** — 備選技術、風險等級、理由說明
   - **態勢評估** — 當前戰場概況

### 2.3 Decide（決策）

**目的**：風險評估，決定是否核准執行

**評估維度**：

1. **複合信心值計算**（SPEC-040）：
   - 25% LLM 建議信心值
   - 25% 歷史成功率
   - 20% 攻擊圖節點信心值
   - 15% 目標狀態分數
   - 15% OPSEC 信心因子

2. **噪音 x 風險矩陣**（依 Mission Profile）：
   - SR 模式：僅低噪音 + 低風險自動核准
   - CO 模式：低噪音 + 中風險核准
   - SP 模式：較為寬鬆
   - FA 模式：幾乎全部核准

3. **Kill Chain 順序驗證**：防止跳躍式攻擊（如未完成初始存取就嘗試橫向移動）

4. **C5ISR 約束檢查**：各域健康度是否達閾值

**決策結果**：

| 結果 | 說明 | 操作員動作 |
|------|------|-----------|
| `auto_approved` | 自動核准 | 無需介入，直接執行 |
| `needs_confirmation` | 需確認 | War Room 彈出確認對話框 |
| `needs_manual` | 需人工授權 | 指揮官必須手動核准 |

### 2.4 Act（行動）

**目的**：執行核准的攻擊技術

**執行模式**：

**單一路徑執行**：
```
決策核准 → EngineRouter 路由 → 選擇執行引擎 → 回傳結果
```

**Swarm 並行執行**（SPEC-030）：
```
多個自動核准技術 → SwarmExecutor → 最多 N 個並行任務 → 聚合結果
```
- 並行上限由 Mission Profile 決定（SR=1, CO=2, SP=5, FA=8）
- 單一任務逾時：120 秒

**執行引擎**：

| 引擎 | 用途 |
|------|------|
| SSH Engine | 透過 SSH 直接執行 Shell 指令 |
| C2 Engine | 透過 Metasploit / 自訂 C2 代理執行 |
| MCP Engine | 透過 MCP 工具伺服器執行（nmap, web-scanner 等） |

**可用 MCP 工具**：

| 工具 | 功能 |
|------|------|
| `nmap-scanner` | 網路偵察 |
| `osint-recon` | OSINT 情蒐 |
| `credential-checker` | 憑證驗證（SSH/RDP/WinRM） |
| `vuln-lookup` | 弱點查詢 |
| `web-scanner` | Web 應用掃描 |
| `api-fuzzer` | API Fuzzing |
| `attack-executor` | 後滲透技術執行 |

### 2.5 Cross-feedback（跨域回饋）

**目的**：更新 C5ISR 態勢感知，為下一輪循環提供回饋

**系統行為**：
1. C5ISR Mapper 根據執行結果更新六大域健康值：
   - **Command**（指揮）
   - **Control**（管控）
   - **Communications**（通訊）
   - **Computers**（計算）
   - **Cyber**（網域）
   - **ISR**（情監偵）
2. 觸發約束引擎（Constraint Engine）檢查：
   - COMMS 健康度 → 影響最大並行任務數
   - Cyber 健康度 → 影響技術風險閾值
   - 噪音預算追蹤
3. 透過 WebSocket 廣播即時更新至 War Room

---

## 四、階段三：攻擊圖管理

### 攻擊圖建構（SPEC-031）

**觸發時機**：每輪 OODA Act 階段結束後自動重建

**建構邏輯**：
1. 讀取 YAML 技術規則（50+ 條規則）
2. 對每條規則檢查先決條件（prerequisite facts）
3. 滿足條件 → 建立 `PENDING` 節點
4. 已執行 → 標記 `EXPLORED`
5. 執行失敗 → 標記 `FAILED` → 剪枝死分支
6. Dijkstra 演算法計算最佳推薦路徑
7. DFS 偵測並消除環路

**節點狀態**：

| 狀態 | 說明 | 顏色 |
|------|------|------|
| `EXPLORED` | 已成功執行 | 綠色 |
| `PENDING` | 可執行、待決策 | 黃色 |
| `IN_PROGRESS` | 執行中 | 藍色 |
| `FAILED` | 執行失敗 | 紅色 |
| `UNREACHABLE` | 無法到達 | 灰色 |
| `PRUNED` | 已剪枝 | 灰色 |

**典型攻擊路徑範例**：
```
T1595.001 (掃描) → T1190 (漏洞利用) → T1078.001 (有效帳號)
                  ↘ T1110.001 (暴力破解) ↗
                                          → T1059.004 (PowerShell)
                                          → T1003.001 (憑證傾印)
```

---

## 五、階段四：OPSEC 監控

**持續監控項目**：

| 監控項 | 說明 |
|--------|------|
| 噪音分數 | 依時間序列追蹤，超過預算時告警 |
| 偵測事件 | 即時記錄防禦端偵測（EDR/IDS） |
| 威脅等級 | 1-10 分，依偵測風險(40%)、噪音(30%)、淪陷數(20%)、代理數(10%) 計算 |

**噪音預算**（每 10 分鐘窗口）：
- SR：10 點
- CO：25 點
- SP：50 點
- FA：無限制

**噪音計點**：低=2、中=5、高=8（每次操作）

---

## 六、階段五：成果彙整

### 弱點管理
**狀態流轉**：`discovered → confirmed → exploited → reported / false_positive`

### PoC 報告
- 記錄成功的概念驗證執行
- 可重現性標記：`reproducible` / `partial` / `not_reproducible`

---

## 七、War Room 操作指南

War Room（`/warroom`）為行動指揮中心，三欄佈局：

| 區域 | 內容 |
|------|------|
| **左欄 -- OODA 狀態** | 四階段卡片（Observe/Orient/Decide/Act）、迭代計數器、活躍階段指示燈 |
| **中欄 -- 決策流 + C5ISR** | OODA 流程圖（Mermaid）、C5ISR 六域健康格（3x2）、約束狀態面板 |
| **右欄 -- 行動日誌** | 即時執行紀錄（最多 30 筆）、嚴重度標示、時間戳記 |

**關鍵操作**：
- **觸發 OODA 循環**：手動按鈕或啟用自動排程
- **約束覆寫**：當 C5ISR 約束阻擋行動時，可點擊 Override（10 分鐘有效窗口）
- **攻擊圖重建**：Attack Graph 頁面的 Rebuild 按鈕

---

## 八、狀態機總覽

```
行動狀態：  planning → active → completed | aborted
OODA 階段： observe → orient → decide → act → (循環)
目標狀態：  alive → compromised → pivot → success
技術狀態：  pending → in_progress → success | failed → (剪枝兄弟節點)
```

---

## 九、API 端點速查

| 端點 | 方法 | 用途 |
|------|------|------|
| `/api/operations` | GET/POST | 行動 CRUD |
| `/api/operations/{id}/attack-graph` | GET/POST | 攻擊圖載入/重建 |
| `/api/operations/{id}/ooda/trigger` | POST | 手動觸發 OODA 循環 |
| `/api/operations/{id}/techniques` | GET | 列出可用技術 |
| `/api/tools` | GET/POST | 工具註冊表 CRUD |
| `/api/tools/{id}/execute` | POST | 直接執行 MCP 工具 |
| `/api/vulnerabilities` | GET | 列出已發現弱點 |
| `/api/recon/scan` | POST | 觸發偵察掃描 |

---

## 十、相關規格文件

| SPEC | 主題 |
|------|------|
| SPEC-007 | OODA Loop Engine |
| SPEC-025 | Tool Registry Management |
| SPEC-026 | Attack Situation Diagram |
| SPEC-030 | AgentSwarm OODA 並行任務排程 |
| SPEC-031 | AttackGraph Engine |
| SPEC-040 | 複合信心值 & Kill Chain Enforcer |
| SPEC-047 | C5ISR 重構 & 約束引擎 |
| SPEC-050 | OODA↔C5ISR Mermaid 流程視覺化 |
