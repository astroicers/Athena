# 軟體需求規格書 (Software Requirements Specification)

---

| 欄位 | 內容 |
|------|------|
| **專案名稱** | Athena — C5ISR + OODA AI 驅動網路攻擊指揮平台 |
| **版本** | v0.1.0 |
| **最後更新** | 2026-03-25 |
| **狀態** | Draft |
| **授權** | Business Source License 1.1 (BSL-1.1) |
| **聯絡** | azz093093.830330@gmail.com |

---

## 1. 目的與範圍（Purpose & Scope）

### 1.1 文件目的

本文件描述 Athena 的完整軟體需求，作為開發、測試與驗收的基準依據。所有功能需求、非功能需求及使用者故事均應可追溯至本文件。本文件涵蓋 51 份 SPEC 及 44 份 ADR 之需求彙整。

### 1.2 專案範圍

Athena 是一套 AI 驅動的網路攻擊指揮平台，整合 OODA 決策迴圈、C5ISR 六域監控及 Kill Chain 七階段自動化，為紅隊與資安專家提供從偵查到報告的完整滲透測試工作流。

**範圍內（In Scope）：**

- 行動（Operation）完整生命週期管理：目標、交戰、任務
- OODA 引擎：自動迴圈 / 手動模式 / Orient AI / 決策引擎
- C5ISR 六域即時監控與健康映射
- 偵查自動化：Nmap、OSINT、CVE 查詢
- 攻擊執行：DirectSSH、C2（Caldera）、Metasploit RPC
- 視覺化：攻擊圖譜、OODA↔C5ISR 流程圖、網路拓撲
- MCP 工具伺服器管理（nmap / osint / vuln / credential / web-scanner / api-fuzzer / attack-executor）
- 報告產出：攻擊路徑時間線、弱點管理、PoC 追蹤
- Web 終端機與管理端點
- 國際化（en / zh-TW）

**範圍外（Out of Scope）：**

- 使用者認證系統（Phase 2 — 目前為單操作員模式）
- 雲端多租戶架構（另立專案）
- 行動裝置原生 App
- 防禦方工具整合（Blue Team 功能）
- 商業授權管理平台

### 1.3 定義與縮寫

| 術語 | 定義 |
|------|------|
| SRS | Software Requirements Specification，軟體需求規格書 |
| FR | Functional Requirement，功能需求 |
| NFR | Non-Functional Requirement，非功能需求 |
| OODA | Observe-Orient-Decide-Act，決策迴圈模型 |
| C5ISR | Command, Control, Communications, Computers, Cyber, Intelligence Surveillance & Reconnaissance |
| Kill Chain | Lockheed Martin Cyber Kill Chain，網路攻擊七階段模型 |
| MCP | Model Context Protocol，工具整合協定 |
| RoE | Rules of Engagement，交戰規則 |
| OPSEC | Operations Security，作戰安全 |
| C2 | Command & Control，指揮與控制 |
| ATT&CK | MITRE ATT&CK 框架 |
| CVE | Common Vulnerabilities and Exposures |
| NVD | National Vulnerability Database |
| PoC | Proof of Concept，概念驗證 |
| OSINT | Open Source Intelligence，公開來源情報 |
| HITL | Human-in-the-Loop，人工介入點 |

---

## 2. 利害關係人（Stakeholders）

| 角色 | 職責 | 參與階段 |
|------|------|----------|
| 紅隊操作員（Red Team Operator） | 執行滲透測試行動、操作 OODA 迴圈、管理攻擊鏈 | 全程 |
| 資安顧問（Security Consultant） | 規劃行動範疇、審核報告、定義 RoE | 需求、驗收 |
| 軍事/政府使用者 | 大規模 C5ISR 作戰指揮 | 需求、驗收 |
| 企業資安團隊 | 內部紅隊演練、弱點管理 | 實作、測試 |
| 資安研究員 | 工具開發、攻擊技術研究 | 實作 |
| 平台維運 | 部署、監控、效能調校 | 上線、維護 |

---

## 3. 功能需求（Functional Requirements）

> 命名規則：`FR-NNN`，按模組分段（FR-100 行動管理、FR-200 OODA 引擎、FR-300 C5ISR 監控、FR-400 偵查、FR-500 攻擊執行、FR-600 視覺化、FR-700 工具管理、FR-800 報告、FR-900 終端與管理）

### 3.1 行動管理模組（FR-100）

| ID | 需求描述 | 優先級 | 驗收標準 |
|----|----------|--------|----------|
| FR-101 | 系統應支援 Operation CRUD，包含代號（codename）、戰略意圖、自動化模式、任務輪廓 | Must Have | 建立行動後可查詢；狀態含 planning/active/paused/completed/aborted |
| FR-102 | 系統應支援 Target CRUD，包含 IP/主機名/範圍、作業系統、存取狀態追蹤 | Must Have | Target 建立後關聯至 Operation；存取狀態含 active/lost/unknown |
| FR-103 | 系統應支援 Engagement 管理，將 Technique 綁定至 Target 並追蹤執行結果 | Must Have | Engagement 記錄攻擊技術、Kill Chain 階段、風險等級 |
| FR-104 | 系統應支援 Mission 工作流，定義多步驟自動化任務序列 | Must Have | Mission 步驟狀態含 queued/running/completed/failed/skipped |
| FR-105 | 系統應支援 Objective 管理，追蹤行動目標達成率 | Should Have | Objective 可關聯至多個 Technique 與 Target |
| FR-106 | 行動應支援 Mission Profile 模式切換：SR（隱匿偵查）/ CO（秘密作戰）/ SP（標準滲透）/ FA（全面攻擊） | Must Have | 切換 Profile 後自動調整噪音閾值與 OPSEC 規則 |

### 3.2 OODA 引擎模組（FR-200）

| ID | 需求描述 | 優先級 | 驗收標準 |
|----|----------|--------|----------|
| FR-201 | 系統應實作 OODA 四階段（Observe → Orient → Decide → Act）自動迴圈 | Must Have | 迴圈可自動推進至下一階段；每次迭代有完整紀錄 |
| FR-202 | Observe 階段應自動彙整偵查結果、Agent 回報、Fact 更新 | Must Have | 產出 observe_summary，涵蓋本輪新增情報 |
| FR-203 | Orient 階段應整合 Claude API（Anthropic）進行威脅態勢分析 | Must Have | 呼叫 Claude API 產出 orient_summary，含建議行動方案 |
| FR-204 | Decide 階段應依 Orient 分析與 Constraint 規則產出可執行建議 | Must Have | 建議含 Technique ID、Target ID、風險評估 |
| FR-205 | Act 階段應自動或經人工確認後執行選定技術 | Must Have | auto_full 模式自動執行；semi_auto / manual 需 HITL 確認 |
| FR-206 | 系統應支援 OODA 手動模式，操作員可手動下達指令（Directive） | Must Have | Directive 長度 1-2000 字元；可覆蓋 AI 建議 |
| FR-207 | 系統應支援 Fact 收集引擎，自動歸類情報至 credential/host/network/osint/service/vulnerability/file/poc/web/defense 類別 | Must Have | Fact 自動關聯 Operation 與 Source |
| FR-208 | 系統應支援最大迭代次數限制（max_iterations），0 為無上限 | Should Have | 達上限時自動暫停迴圈 |

### 3.3 C5ISR 監控模組（FR-300）

| ID | 需求描述 | 優先級 | 驗收標準 |
|----|----------|--------|----------|
| FR-301 | 系統應實作六域（Command / Control / Communications / Computers / Cyber / ISR）即時狀態監控 | Must Have | 各域狀態含 operational/active/nominal/engaged/scanning/degraded/offline/critical |
| FR-302 | 系統應提供 C5ISR 健康映射，將六域狀態視覺化為整體態勢圖 | Must Have | 健康映射即時更新，degraded/critical 域觸發告警 |
| FR-303 | 系統應實作 Constraint 引擎，定義與驗證作戰限制規則 | Must Have | 違反 critical constraint 時阻止攻擊執行 |
| FR-304 | 系統應實作 OPSEC 監控，偵測噪音過高、認證失敗、爆量請求等事件 | Must Have | OPSEC 事件類型含 burst/auth_failure/high_noise/artifact/detection |
| FR-305 | OPSEC 事件觸發時應依嚴重度（info/warning/critical）自動調整行動節奏 | Should Have | critical 事件自動暫停 OODA 迴圈 |

### 3.4 偵查模組（FR-400）

| ID | 需求描述 | 優先級 | 驗收標準 |
|----|----------|--------|----------|
| FR-401 | 系統應整合 Nmap 進行主機掃描、Port 掃描與服務偵測 | Must Have | 掃描結果自動入庫為 Fact（host/service 類別） |
| FR-402 | 系統應整合 OSINT 來源（crt.sh、subfinder、DNS 查詢）進行被動偵查 | Must Have | 子域名、憑證、DNS 紀錄自動入庫 |
| FR-403 | 系統應實作範圍驗證（Scope Validation），確保掃描目標在 RoE 允許範圍內 | Must Have | 超出範圍的掃描自動阻擋並記錄 OPSEC 事件 |
| FR-404 | 系統應整合 NVD API 進行 CVE 查詢與弱點匹配 | Must Have | CVE 結果關聯至對應 Target 與 Service |
| FR-405 | 系統應支援 Web 掃描器（web-scanner MCP 工具）進行 Web 應用偵查 | Should Have | 掃描結果含 URL、狀態碼、發現之弱點 |
| FR-406 | 系統應支援 API Fuzzer（api-fuzzer MCP 工具）進行 API 端點模糊測試 | Should Have | Fuzzing 結果含異常回應、潛在弱點 |

### 3.5 攻擊執行模組（FR-500）

| ID | 需求描述 | 優先級 | 驗收標準 |
|----|----------|--------|----------|
| FR-501 | 系統應實作 DirectSSH 引擎，透過 asyncssh 對目標執行遠端指令 | Must Have | 支援密碼與金鑰認證；執行結果含 stdout/stderr/exit_code |
| FR-502 | 系統應整合 Caldera C2 框架進行代理部署與操作 | Should Have | Agent 狀態含 alive/dead/pending/untrusted |
| FR-503 | 系統應整合 Metasploit RPC 執行 Exploit | Should Have | 透過 pymetasploit3 呼叫；結果回寫 Engagement |
| FR-504 | 系統應支援多執行引擎切換：SSH / Persistent SSH / C2 / Metasploit / WinRM / MCP / Mock | Must Have | 每個 Engagement 可指定執行引擎 |
| FR-505 | 攻擊執行前必須通過 RoE 驗證與 Constraint 檢查 | Must Have | 違反 RoE 時返回錯誤且不執行 |
| FR-506 | 系統應支援 Technique 管理，對應 MITRE ATT&CK 技術編號 | Must Have | Technique 狀態含 untested/queued/running/success/partial/failed |
| FR-507 | 系統應追蹤 Kill Chain 七階段（Recon → Weaponize → Deliver → Exploit → Install → C2 → Action）進度 | Must Have | 各階段可統計技術數量與成功率 |

### 3.6 視覺化模組（FR-600）

| ID | 需求描述 | 優先級 | 驗收標準 |
|----|----------|--------|----------|
| FR-601 | 系統應提供 3D 攻擊圖譜（基於 force-graph-3d），展示 Target/Technique/Agent 關係 | Must Have | 節點可互動；即時反映攻擊進度 |
| FR-602 | 系統應產出 Mermaid 格式的 OODA↔C5ISR 整合流程圖 | Should Have | 流程圖自動依行動狀態更新 |
| FR-603 | 系統應提供網路拓撲圖，展示已探索的網路結構 | Should Have | 拓撲圖含主機、Port、路由資訊 |
| FR-604 | 系統應提供 Kill Chain 階段視覺化圖表 | Must Have | 七階段進度條含各階段技術統計 |
| FR-605 | 系統應提供 ATT&CK Surface 頁面，展示已使用之 ATT&CK 技術覆蓋面 | Should Have | 以矩陣或熱力圖呈現技術覆蓋 |

### 3.7 工具管理模組（FR-700）

| ID | 需求描述 | 優先級 | 驗收標準 |
|----|----------|--------|----------|
| FR-701 | 系統應實作 MCP 工具伺服器架構，支援動態載入工具 | Must Have | 工具伺服器含 nmap/osint/vuln/credential/web-scanner/api-fuzzer/attack-executor |
| FR-702 | 系統應提供工具註冊表（Tool Registry），管理工具元資料與版本 | Must Have | 工具類別含 reconnaissance/enumeration/vulnerability_scanning/credential_access/exploitation/execution |
| FR-703 | 系統應區分 Tool（單一工具）與 Engine（執行引擎）兩種工具類型 | Should Have | 類型在 Registry 中明確標示 |
| FR-704 | 工具頁面應展示可用工具清單、狀態與執行歷史 | Must Have | 可篩選、搜尋、查看工具詳情 |

### 3.8 報告模組（FR-800）

| ID | 需求描述 | 優先級 | 驗收標準 |
|----|----------|--------|----------|
| FR-801 | 系統應支援報告自動產出，彙整行動歷程、攻擊路徑、發現弱點 | Must Have | 報告含行動摘要、時間線、弱點清單、建議修復 |
| FR-802 | 系統應提供攻擊路徑時間線，依時序展示每一步攻擊行動 | Must Have | 時間線含時間戳、技術、目標、結果 |
| FR-803 | 系統應提供弱點管理功能，追蹤弱點生命週期 | Must Have | 弱點可關聯 CVE、CVSS、Target、PoC |
| FR-804 | 系統應提供 PoC 追蹤功能，記錄概念驗證程式碼與執行結果 | Should Have | PoC 含程式碼、截圖、執行環境、結果 |
| FR-805 | 系統應提供 Playbook 管理，儲存可複用的攻擊劇本 | Should Have | Playbook 可匯入/匯出、版本管理 |

### 3.9 終端與管理模組（FR-900）

| ID | 需求描述 | 優先級 | 驗收標準 |
|----|----------|--------|----------|
| FR-901 | 系統應提供 Web 終端機介面，支援對目標執行即時指令 | Must Have | 終端支援 WebSocket 即時互動 |
| FR-902 | 系統應實作指令黑名單（Command Blacklist），阻擋危險指令 | Must Have | 黑名單指令返回錯誤且記錄 OPSEC 事件 |
| FR-903 | 系統應提供管理端點，涵蓋系統健康檢查、日誌查詢 | Must Have | /health 端點回應系統狀態；日誌可依嚴重度篩選 |
| FR-904 | 系統應提供 Dashboard 頁面，彙整行動概覽、C5ISR 狀態、OODA 進度 | Must Have | Dashboard 即時更新，含關鍵指標卡片 |
| FR-905 | 系統應支援 WebSocket 即時推送，將 OODA 事件、Agent 狀態、日誌即時推送至前端 | Must Have | WS 連線穩定；斷線自動重連 |

> **優先級定義：**
> - **Must Have**：核心功能，無此無法進行滲透測試
> - **Should Have**：重要功能，應在初版完成
> - **Nice to Have**：增強功能，可延至後續版本

---

## 4. 非功能需求（Non-Functional Requirements）

| 類別 | 需求 | 目標值 | 驗證方式 |
|------|------|--------|----------|
| **效能** | API 回應時間（P95） | < 500ms | 負載測試（k6） |
| **效能** | OODA 單次迴圈完成時間 | < 30s | 計時器量測（含 Claude API 呼叫） |
| **效能** | Nmap 掃描結果入庫延遲 | < 5s | 端對端測試 |
| **效能** | WebSocket 訊息延遲 | < 200ms | 前端計時量測 |
| **可用性** | 服務正常運行時間（SLA） | 99.9%（月計） | 監控儀表板 |
| **安全性** | 禁止硬編碼憑證 | 零容忍 | 程式碼掃描 + Code Review |
| **安全性** | 攻擊執行前 RoE 驗證 | 100% 執行率 | 整合測試 |
| **安全性** | 指令黑名單覆蓋率 | 涵蓋所有破壞性指令 | 黑名單審查 |
| **安全性** | 傳輸加密 | TLS 1.2+ | SSL Labs 評級 |
| **可維護性** | 後端測試覆蓋率 | > 80% | `pytest --cov` |
| **可維護性** | 前端測試覆蓋率 | > 70% | Vitest coverage |
| **可維護性** | E2E 測試覆蓋率 | 關鍵路徑 100% | Playwright 報告 |
| **可維護性** | 程式碼風格 | Ruff（後端）+ ESLint（前端） | `make lint` |
| **國際化** | 支援語系 | en + zh-TW | `make i18n-check` |
| **國際化** | 翻譯覆蓋率 | 100%（UI 可見文字） | i18n 檢查工具 |
| **擴展性** | 水平擴展 | 無狀態 API + 外部狀態儲存 | 多實例部署驗證 |
| **文件化** | SPEC 文件覆蓋率 | 51 份 SPEC 已建立 | `make spec-list` |
| **文件化** | ADR 覆蓋率 | 44 份 ADR 已建立 | `make adr-list` |

---

## 5. 使用者故事（User Stories）

### 5.1 紅隊操作員（Red Team Operator）

---

**US-101: 建立滲透測試行動**

- **As a** 紅隊操作員
- **I want** 建立新的 Operation 並指定代號、任務輪廓、自動化模式
- **So that** 我可以開始有組織的滲透測試工作

**Acceptance Criteria:**

- [x] 可設定 Operation 代號（codename）、戰略意圖
- [x] 可選擇 Mission Profile（SR/CO/SP/FA）
- [x] 可選擇 Automation Mode（manual/semi_auto/auto_full）
- [x] 建立後自動初始化 C5ISR 六域狀態
- [x] Operation 狀態為 planning

**Maps to:** FR-101, FR-106

---

**US-102: 執行 OODA 自動迴圈**

- **As a** 紅隊操作員
- **I want** 啟動 OODA 自動迴圈，讓系統自動偵查、分析、決策、執行
- **So that** 我可以高效推進滲透測試而不需手動操作每一步

**Acceptance Criteria:**

- [x] 一鍵啟動 OODA 迴圈
- [x] Observe 自動彙整偵查結果
- [x] Orient 呼叫 Claude API 產出分析
- [x] Decide 產出推薦行動
- [x] Act 依自動化模式決定是否自動執行
- [x] 迴圈完成後自動進入下一輪

**Maps to:** FR-201 ~ FR-208

---

**US-103: 監控 C5ISR 態勢**

- **As a** 紅隊操作員
- **I want** 即時查看 C5ISR 六域健康狀態
- **So that** 我可以掌握整體作戰態勢並在異常時及時調整

**Acceptance Criteria:**

- [x] 六域狀態以視覺化方式呈現
- [x] degraded/critical 域顯示告警
- [x] OPSEC 事件即時推送
- [x] 可深入查看各域詳情

**Maps to:** FR-301 ~ FR-305

---

**US-104: 偵查目標網路**

- **As a** 紅隊操作員
- **I want** 對目標進行自動化偵查（Nmap 掃描、OSINT、CVE 查詢）
- **So that** 我可以發現目標的弱點與攻擊面

**Acceptance Criteria:**

- [x] 可選擇掃描類型與範圍
- [x] 掃描前自動驗證 RoE 範圍
- [x] 結果自動入庫為 Fact
- [x] CVE 自動匹配已發現之服務

**Maps to:** FR-401 ~ FR-406

---

**US-105: 執行攻擊技術**

- **As a** 紅隊操作員
- **I want** 對目標執行指定的攻擊技術
- **So that** 我可以驗證弱點並推進 Kill Chain

**Acceptance Criteria:**

- [x] 可選擇執行引擎（SSH/C2/Metasploit/MCP）
- [x] 執行前通過 RoE 與 Constraint 驗證
- [x] 執行結果即時回傳並更新 Engagement 狀態
- [x] Kill Chain 階段自動推進

**Maps to:** FR-501 ~ FR-507

---

**US-106: 產出滲透測試報告**

- **As a** 紅隊操作員
- **I want** 自動產出完整的滲透測試報告
- **So that** 我可以向客戶交付專業的評估結果

**Acceptance Criteria:**

- [x] 報告含行動摘要、時間線、弱點清單
- [x] 弱點含 CVE 編號、CVSS 評分、PoC
- [x] 攻擊路徑以時間線展示
- [x] 含修復建議

**Maps to:** FR-801 ~ FR-805

---

### 5.2 資安顧問（Security Consultant）

---

**US-201: 定義交戰規則**

- **As a** 資安顧問
- **I want** 設定 Constraint 與 RoE 規則
- **So that** 行動不會超出授權範圍

**Acceptance Criteria:**

- [x] 可定義 IP 範圍白名單
- [x] 可定義禁止執行的技術
- [x] 違反規則時自動阻擋並記錄
- [x] Constraint 等級含 warning 與 critical

**Maps to:** FR-303, FR-403, FR-505

---

**US-202: 檢視攻擊圖譜**

- **As a** 資安顧問
- **I want** 以 3D 圖譜查看整體攻擊路徑
- **So that** 我可以理解攻擊面並評估風險

**Acceptance Criteria:**

- [x] 3D 圖譜可互動旋轉與縮放
- [x] 節點區分 Target/Technique/Agent
- [x] 邊線顯示攻擊關係
- [x] 即時反映最新狀態

**Maps to:** FR-601 ~ FR-605

---

### 5.3 平台管理員（Admin）

---

**US-301: 管理 MCP 工具**

- **As a** 平台管理員
- **I want** 管理已註冊的 MCP 工具伺服器
- **So that** 我可以確保工具可用且版本正確

**Acceptance Criteria:**

- [x] 工具清單含名稱、類別、狀態
- [x] 可查看工具執行歷史
- [x] 工具異常時顯示告警

**Maps to:** FR-701 ~ FR-704

---

## 6. 使用場景（Use Cases）

### UC-101: OODA 自動攻擊迴圈

**參與者：** 紅隊操作員、OODA 引擎、Claude API、MCP 工具、C5ISR 監控

**前置條件：** Operation 已建立且狀態為 active；至少一個 Target 已定義

**後置條件：** OODA 迭代完成，攻擊進度推進

#### 主要流程（Main Flow）

1. 操作員啟動 OODA 迴圈（auto_full 或 semi_auto 模式）
2. **Observe**：系統彙整 Fact、Agent 狀態、偵查結果，產出 observe_summary
3. **Orient**：系統呼叫 Claude API，傳入 observe_summary 與行動上下文，產出 orient_summary 含建議行動
4. **Decide**：系統依 orient_summary、Constraint 規則與 Risk Threshold 產出可執行建議（Recommendation）
5. **Act**：auto_full 模式自動執行；semi_auto 模式推送建議至前端待確認
6. 執行結果回寫 Engagement，更新 Fact，推進 Kill Chain 階段
7. C5ISR 監控更新六域狀態
8. 迴圈回到步驟 2（直到達 max_iterations 或操作員暫停）

#### 替代流程（Alternative Flow）

- **A1 - 手動模式：** 操作員直接下達 Directive → 系統略過 Orient/Decide → 直接執行 Directive 指定之技術
- **A2 - semi_auto 確認：** 步驟 5 操作員收到推播 → 確認/修改/拒絕 → 系統依操作員決策執行

#### 異常流程（Exception Flow）

- **E1 - RoE 違規：** 步驟 5 Constraint 檢查失敗 → 記錄 OPSEC 事件 → 跳過該技術 → 繼續迴圈
- **E2 - OPSEC Critical：** C5ISR 偵測到 critical 事件 → 自動暫停迴圈 → 通知操作員
- **E3 - Claude API 逾時：** Orient 階段 API 呼叫失敗 → 重試一次 → 仍失敗則標記 OODA phase 為 failed → 通知操作員

---

### UC-201: 偵查掃描流程

**參與者：** 紅隊操作員、Nmap MCP 工具、OSINT MCP 工具、Fact 引擎

**前置條件：** Target 已定義且在 RoE 範圍內

**後置條件：** Fact 資料庫更新，含主機、服務、弱點資訊

#### 主要流程

1. 操作員或 OODA Act 階段觸發偵查任務
2. 系統驗證目標 IP/範圍在 RoE 允許範圍內
3. 系統透過 Nmap MCP 工具執行掃描
4. 掃描結果自動解析為 Fact（host/service/vulnerability 類別）
5. 系統查詢 NVD API 匹配已發現服務之 CVE
6. CVE 結果關聯至對應 Target 與 Vulnerability
7. C5ISR ISR 域狀態更新為 scanning → operational

#### 異常流程

- **E1 - 範圍違規：** 步驟 2 驗證失敗 → 返回錯誤 → 記錄 OPSEC artifact 事件
- **E2 - 掃描逾時：** Nmap 掃描超過閾值 → 記錄 warning → 返回已取得之部分結果

---

## 7. 資料模型概覽（Data Model）

### 7.1 核心實體（Entities）

| 實體 | 說明 | 主要屬性 | 關聯 |
|------|------|----------|------|
| `Operation` | 滲透測試行動 | id, code, name, codename, strategic_intent, status, current_ooda_phase, automation_mode, mission_profile, risk_threshold | 1:N → Target, 1:N → OODAIteration, 1:N → Engagement |
| `Target` | 攻擊目標 | id, operation_id, ip, hostname, os, access_status | N:1 → Operation, 1:N → Engagement |
| `OODAIteration` | OODA 迭代紀錄 | id, operation_id, iteration_number, phase, observe/orient/decide/act_summary | N:1 → Operation |
| `Engagement` | 攻擊交戰紀錄 | id, operation_id, target_id, technique_id, engine, kill_chain_stage | N:1 → Operation, N:1 → Target |
| `Mission` | 多步驟自動化任務 | id, operation_id, steps, status | N:1 → Operation |
| `Technique` | ATT&CK 攻擊技術 | id, mitre_id, name, kill_chain_stage, status | 1:N → Engagement |
| `Fact` | 情報事實 | id, operation_id, category, key, value, source | N:1 → Operation |
| `C5ISRDomainState` | C5ISR 域狀態 | id, domain, status, health_score | N:1 → Operation |
| `Constraint` | 作戰限制規則 | id, operation_id, rule, level (warning/critical) | N:1 → Operation |
| `OPSECEvent` | OPSEC 事件 | id, operation_id, event_type, severity, detail | N:1 → Operation |
| `Vulnerability` | 弱點紀錄 | id, target_id, cve_id, cvss, description | N:1 → Target |
| `Agent` | C2 代理 | id, operation_id, target_id, status (alive/dead/pending/untrusted) | N:1 → Target |
| `Report` | 報告 | id, operation_id, content, generated_at | N:1 → Operation |
| `ToolRegistry` | 工具註冊表 | id, name, kind (tool/engine), category, version | — |
| `LogEntry` | 系統日誌 | id, operation_id, severity, message, timestamp | N:1 → Operation |
| `Credential` | 憑證 | id, operation_id, username, source, access_level | N:1 → Operation |
| `PoCRecord` | PoC 紀錄 | id, vulnerability_id, code, result | N:1 → Vulnerability |
| `Playbook` | 攻擊劇本 | id, name, steps, tags | — |
| `Recommendation` | AI 建議 | id, ooda_iteration_id, technique_id, risk_assessment | N:1 → OODAIteration |

### 7.2 狀態機（State Machine）

**Operation 狀態：**

```
[Planning] --activate--> [Active]
[Active]   --pause-->    [Paused]
[Paused]   --resume-->   [Active]
[Active]   --complete--> [Completed]
[Active]   --abort-->    [Aborted]
[Paused]   --abort-->    [Aborted]
```

**OODA 迭代狀態：**

```
[Observe] --data_collected--> [Orient]
[Orient]  --analysis_done-->  [Decide]
[Decide]  --decision_made-->  [Act]
[Act]     --executed-->       [Observe]  (next iteration)
[Any]     --error-->          [Failed]
```

**Technique 執行狀態：**

```
[Untested] --queue-->    [Queued]
[Queued]   --start-->    [Running]
[Running]  --success-->  [Success]
[Running]  --partial-->  [Partial]
[Running]  --fail-->     [Failed]
```

**Agent 狀態：**

```
[Pending]    --checkin-->     [Alive]
[Alive]      --lost-->        [Dead]
[Alive]      --suspicious-->  [Untrusted]
[Untrusted]  --verified-->    [Alive]
[Dead]       --reconnect-->   [Alive]
```

### 7.3 重要索引策略

| 資料表 | 索引欄位 | 類型 | 理由 |
|--------|----------|------|------|
| `operations` | `code` | UNIQUE | 行動代號唯一查詢 |
| `operations` | `status` | B-Tree | 依狀態篩選行動 |
| `targets` | `operation_id, ip` | Composite UNIQUE | 同一行動不重複目標 |
| `ooda_iterations` | `operation_id, iteration_number` | Composite | 行動迭代查詢 |
| `facts` | `operation_id, category` | Composite | 依類別查詢情報 |
| `engagements` | `operation_id, target_id` | Composite | 依行動+目標查交戰 |
| `vulnerabilities` | `cve_id` | B-Tree | CVE 查詢 |
| `log_entries` | `operation_id, severity, timestamp` | Composite | 日誌篩選與排序 |

---

## 8. 介面規格（Interface Spec）

### 8.1 頁面清單

| 路由 | 頁面名稱 | 說明 |
|------|----------|------|
| `/` | Dashboard | 行動概覽、C5ISR 狀態、OODA 進度 |
| `/operations` | 行動列表 | Operation CRUD、狀態管理 |
| `/warroom` | 作戰室 | OODA 控制面板、即時態勢、TARGETS 列表與 Markdown 詳情 |
| `/planner` | 規劃器 | 已整合至 War Room |
| `/attack-graph` | 攻擊圖譜 | 3D force-graph 視覺化 |
| `/attack-surface` | ATT&CK 覆蓋面 | MITRE ATT&CK 技術矩陣 |
| `/decisions` | 決策紀錄 | OODA Decide 歷史與 AI 建議 |
| `/vulns` | 弱點管理 | 弱點清單、CVE 關聯、修復追蹤 |
| `/poc` | PoC 管理 | 概念驗證紀錄 |
| `/opsec` | OPSEC 監控 | OPSEC 事件列表與嚴重度篩選 |
| `/tools` | 工具管理 | MCP 工具伺服器狀態與註冊表 |

### 8.2 導航結構

```
Dashboard (/)
├── 行動列表 (/operations)
├── 作戰室 (/warroom)
│   ├── OODA 控制面板
│   ├── C5ISR 六域監控
│   ├── TARGETS 列表 + 詳情
│   └── 終端機（內嵌）
├── 攻擊圖譜 (/attack-graph)
├── ATT&CK 覆蓋面 (/attack-surface)
├── 決策紀錄 (/decisions)
├── 弱點管理 (/vulns)
├── PoC 管理 (/poc)
├── OPSEC 監控 (/opsec)
└── 工具管理 (/tools)
```

### 8.3 設計系統

Athena 採用 **Deep Gemstone v3** 設計系統：

- 深色主題為主（深寶石色調）
- 配色：寶石藍 / 翠綠 / 琥珀警告 / 紅色危險
- 元件庫：基於 Tailwind v4 自訂設計令牌
- 字體：等寬字體用於終端與代碼區塊

---

## 9. 限制與假設（Constraints & Assumptions）

### 9.1 技術限制

- **後端框架**：Python 3.11+ / FastAPI / asyncpg / SQLAlchemy 2.0 / PostgreSQL
- **前端框架**：Next.js 14 / React 18 / Tailwind v4 / next-intl
- **AI 引擎**：Anthropic Claude API（anthropic SDK >= 0.49.0）
- **MCP 協定**：mcp SDK >= 1.6.0
- **瀏覽器支援**：最新兩個版本的 Chrome、Firefox、Safari、Edge
- **網路需求**：需可存取目標網路及外部 API（NVD、Claude）

### 9.2 業務限制

- **授權模式**：BSL-1.1，商業使用需另行授權
- **法規合規**：使用者需自行確保滲透測試行為合法且有授權
- **RoE 強制**：平台強制 RoE 驗證，但最終法律責任由使用者承擔

### 9.3 假設

- 假設使用者具備滲透測試專業知識，熟悉 ATT&CK 框架與 Kill Chain 模型
- 假設 Claude API 可用性達 99.5% 以上（Orient 階段降級策略：API 不可用時切換為手動 Orient）
- 假設目標網路已取得合法授權進行測試
- 假設 PostgreSQL 資料庫在單一行動中之 Fact 總量不超過 100 萬筆

### 9.4 依賴項目

| 外部依賴 | 用途 | 備用方案 |
|----------|------|----------|
| Anthropic Claude API | OODA Orient AI 分析 | 降級為手動分析模式 |
| NVD API | CVE 弱點查詢 | 本地 CVE 資料庫快取 |
| Caldera | C2 框架整合 | 降級為 DirectSSH 執行 |
| Metasploit RPC | Exploit 執行 | 降級為手動 Exploit |
| crt.sh / subfinder | OSINT 子域名偵查 | DNS 暴力列舉 |
| PostgreSQL | 主要資料庫 | 無備用（核心依賴） |

---

## 10. 追溯矩陣（Traceability Matrix）

| FR ID | 描述 | US ID | 相關 SPEC 範圍 | 相關 ADR 範圍 |
|-------|------|-------|----------------|---------------|
| FR-101 ~ FR-106 | 行動管理 | US-101 | SPEC-001 ~ SPEC-010 | ADR-001 ~ ADR-005 |
| FR-201 ~ FR-208 | OODA 引擎 | US-102 | SPEC-011 ~ SPEC-020 | ADR-006 ~ ADR-012 |
| FR-301 ~ FR-305 | C5ISR 監控 | US-103 | SPEC-021 ~ SPEC-028 | ADR-013 ~ ADR-018 |
| FR-401 ~ FR-406 | 偵查 | US-104 | SPEC-029 ~ SPEC-035 | ADR-019 ~ ADR-024 |
| FR-501 ~ FR-507 | 攻擊執行 | US-105 | SPEC-036 ~ SPEC-042 | ADR-025 ~ ADR-032 |
| FR-601 ~ FR-605 | 視覺化 | US-202 | SPEC-043 ~ SPEC-046 | ADR-033 ~ ADR-036 |
| FR-701 ~ FR-704 | 工具管理 | US-301 | SPEC-047 ~ SPEC-048 | ADR-037 ~ ADR-039 |
| FR-801 ~ FR-805 | 報告 | US-106 | SPEC-049 ~ SPEC-050 | ADR-040 ~ ADR-042 |
| FR-901 ~ FR-905 | 終端與管理 | US-101 | SPEC-051 | ADR-043 ~ ADR-044 |

> 完整 SPEC 列表：SPEC-001 至 SPEC-051（執行 `make spec-list` 查看）
> 完整 ADR 列表：ADR-001 至 ADR-044（執行 `make adr-list` 查看）

---

## 附錄

### A. 變更歷史

| 版本 | 日期 | 變更摘要 | 作者 |
|------|------|----------|------|
| v0.1.0 | 2026-03-25 | 初版建立，涵蓋 9 大功能模組、NFR、資料模型 | Athena Team + Claude |

### B. 相關文件

- [`docs/adr/`](./adr/) — 架構決策記錄（ADR-001 ~ ADR-044）
- [`docs/specs/`](./specs/) — 規格書（SPEC-001 ~ SPEC-051）
- [`docs/architecture.md`](./architecture.md) — 系統架構文件
- [`docs/ROADMAP.md`](./ROADMAP.md) — 專案路線圖
- [`docs/GETTING_STARTED.md`](./GETTING_STARTED.md) — 快速入門指南
- [`docs/SOP-攻擊流程.md`](./SOP-攻擊流程.md) — 攻擊流程標準作業程序
