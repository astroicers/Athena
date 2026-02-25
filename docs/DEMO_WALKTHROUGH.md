# Demo 演練：OP-2024-017 PHANTOM-EYE

本文件提供 Athena 平台的完整 Demo 演練指南，以「奪取 Domain Admin」作戰場景為範本，展示 C5ISR 框架、PentestGPT 情報整合與 OODA 循環的核心能力。

---

## 前提：確認服務運行中

在開始 Demo 前，確認後端與前端服務皆已啟動：

```bash
# 確認後端健康狀態
curl http://localhost:8000/api/health
# 預期回應：
# {"status":"ok","version":"0.1.0","services":{"database":"ok","caldera":"ok","pentestgpt":"ok"}}

# 確認前端可存取
curl -s -o /dev/null -w "%{http_code}" http://localhost:3000
# 預期：200
```

種子資料在後端啟動時自動載入，包含：
- 作戰：`OP-2024-017 PHANTOM-EYE`（operation ID：`op-phantom-eye-001`）
- 目標主機：5 台（DC-01、WEB-SRV-01、FILE-SRV-01、DEV-WRK-01、ADMIN-WRK-01）
- 部署 Agent：4 個（alpha、bravo、charlie、delta）
- 任務步驟：4 個（初始存取 → 偵察 → 橫向移動 → 權限提升）

---

## 4 個畫面導覽

### `/c5isr` — C5ISR 指揮看板

指揮官的作戰全局視圖，是 Athena 的核心畫面。

| 元件 | 說明 |
|------|------|
| KPI 卡片 | 顯示作戰目標達成率、Active Agent 數量、已執行技術數、OODA 迭代次數 |
| 六域狀態 | Command / Control / Communications / Computers / Cyber / Intelligence 各域健康度 |
| OODA 指示器 | 即時顯示當前 OODA 階段（Observe / Orient / Decide / Act），觸發循環時依序切換 |
| PentestGPT 推薦 | RecommendCard 顯示最新戰術建議，包含情境評估、信心度與 3 個戰術選項 |

### `/navigator` — MITRE ATT&CK 導航器

視覺化戰術執行狀態，以 MITRE ATT&CK 矩陣呈現。

| 元件 | 說明 |
|------|------|
| 戰術矩陣 | 14 個 MITRE 戰術欄位，已執行技術以顏色標示（成功/失敗/進行中） |
| Kill Chain | 將作戰步驟映射至 Kill Chain 階段，顯示當前推進位置 |
| 技術詳情 | 點擊 MITRECell 展開技術詳情（T-ID、名稱、執行引擎、執行結果） |

### `/planner` — 任務規劃器

作戰計畫的結構化視圖，提供步驟層級的狀態追蹤。

| 元件 | 說明 |
|------|------|
| 任務步驟 | 4 個作戰步驟卡片，顯示技術清單與執行狀態 |
| OODA 時間軸 | 每次 OODA 迭代的歷史記錄，以時間軸呈現 |
| 主機卡片 | 5 台目標主機的當前狀態（未觸及/已偵察/已存取/已控制） |

### `/monitor` — 戰場監控

即時作戰態勢，以 3D 拓樸圖呈現網路全貌。

| 元件 | 說明 |
|------|------|
| 3D 拓樸 | react-force-graph-3d 渲染的互動式網路圖，節點顏色代表主機狀態 |
| Agent 信標 | 4 個 Agent 的最後心跳時間與連線狀態（Online/Offline/Stale） |
| 即時日誌 | 串流顯示執行日誌，包含技術執行、結果與錯誤訊息 |

---

## 手動 Demo：6 步 OODA 循環

以下 6 個步驟完整示範 Athena 的 OODA 循環能力。建議在終端執行 API 指令的同時，在瀏覽器觀察 UI 變化。

---

### Step 1：OBSERVE — 觸發第一輪 OODA 循環

```bash
curl -X POST http://localhost:8000/api/operations/op-phantom-eye-001/ooda/trigger
```

**說明：** 系統啟動完整的 Observe → Orient → Decide → Act 循環。後端依序執行：
1. 收集當前情報（Agent 回報、主機狀態、已執行技術）
2. 將情境傳送至 PentestGPT 進行分析
3. 評估並選擇下一步技術
4. 派發執行任務至 Caldera

**預期回應：**
```json
{
  "iteration_number": 1,
  "observe_summary": "收集到 4 個 Agent 回報，3 台主機已完成初始偵察",
  "orient_summary": "PentestGPT 分析：建議優先執行憑證竊取（T1003.001）",
  "decide_summary": "選擇技術 T1003.001，路由至 Caldera 執行引擎",
  "act_summary": "已派發任務至 Agent alpha，預計 30 秒完成",
  "status": "completed"
}
```

**UI 觀察：** 前往 `/c5isr`，OODA 指示器依序點亮 Observe → Orient → Decide → Act。

---

### Step 2：ORIENT — 查看 PentestGPT 推薦

```bash
curl http://localhost:8000/api/operations/op-phantom-eye-001/recommendations
```

**說明：** 取得最新的 PentestGPT 情報分析結果，包含戰術推薦與推理說明。

**預期回應：**
```json
{
  "recommendations": [
    {
      "id": "rec-001",
      "situation_assessment": "已取得初始存取，3 台主機在偵察範圍內。目標 DC-01 尚未接觸，需要橫向移動路徑。",
      "confidence": 0.85,
      "options": [
        {
          "rank": 1,
          "technique": "T1003.001",
          "name": "OS Credential Dumping: LSASS Memory",
          "reasoning": "已確認 Admin 權限，LSASS dump 可快速取得多組憑證",
          "risk_level": "medium",
          "engine": "caldera"
        },
        {
          "rank": 2,
          "technique": "T1134",
          "name": "Access Token Manipulation",
          "reasoning": "較低噪音，適合 EDR 環境，但需要 SeDebugPrivilege",
          "risk_level": "low",
          "engine": "caldera"
        },
        {
          "rank": 3,
          "technique": "T1021.002",
          "name": "Remote Services: SMB/Windows Admin Shares",
          "reasoning": "若憑證取得成功，可直接橫向移動至 DC-01",
          "risk_level": "high",
          "engine": "caldera"
        }
      ],
      "recommended_option": 1
    }
  ]
}
```

**UI 觀察：** `/c5isr` 的 RecommendCard 顯示最新推薦，信心度以百分比呈現，3 個選項以風險等級色彩標示。

---

### Step 3：DECIDE — 審閱 C5ISR 域狀態

```bash
curl http://localhost:8000/api/operations/op-phantom-eye-001/c5isr
```

**說明：** 查看 6 個 C5ISR 域的當前健康度，輔助指揮官做出決策。

**預期回應：**
```json
{
  "domains": [
    {"domain": "command",         "health_pct": 90, "status": "operational"},
    {"domain": "control",         "health_pct": 85, "status": "operational"},
    {"domain": "communications",  "health_pct": 78, "status": "degraded"},
    {"domain": "computers",       "health_pct": 60, "status": "degraded"},
    {"domain": "cyber",           "health_pct": 72, "status": "operational"},
    {"domain": "intelligence",    "health_pct": 88, "status": "operational"}
  ],
  "overall_readiness": 79
}
```

**UI 觀察：** `/c5isr` 的 DomainCard 健康度指示列反映上述數值，degraded 狀態以黃色標示，critical 以紅色標示。

---

### Step 4：ACT — 查看執行結果

```bash
curl http://localhost:8000/api/operations/op-phantom-eye-001/techniques
```

**說明：** 取得所有已排程或執行中的技術列表，確認作戰行動的實際執行狀態。

**預期回應：**
```json
{
  "techniques": [
    {
      "technique_id": "T1595.001",
      "name": "Active Scanning: Scanning IP Blocks",
      "status": "success",
      "engine": "caldera",
      "executed_at": "2024-01-15T09:15:00Z",
      "result_summary": "發現 5 台主機，12 個開放連接埠"
    },
    {
      "technique_id": "T1003.001",
      "name": "OS Credential Dumping: LSASS Memory",
      "status": "pending",
      "engine": "caldera",
      "executed_at": null,
      "result_summary": null
    },
    {
      "technique_id": "T1068",
      "name": "Exploitation for Privilege Escalation",
      "status": "failed",
      "engine": "caldera",
      "executed_at": "2024-01-15T09:30:00Z",
      "result_summary": "目標系統已修補 CVE-2023-XXXX"
    }
  ]
}
```

**UI 觀察：** `/navigator` 的 MITRECell 依狀態變色：成功為綠色、失敗為紅色、進行中為黃色、未執行為灰色。

---

### Step 5：OBSERVE (Round 2) — 再次觸發 OODA

```bash
curl -X POST http://localhost:8000/api/operations/op-phantom-eye-001/ooda/trigger
```

**說明：** 啟動第二輪 OODA 循環。PentestGPT 將根據 Round 1 的執行結果（包含 T1068 失敗）重新分析，調整戰術建議。

**預期回應：**
```json
{
  "iteration_number": 2,
  "observe_summary": "T1068 失敗，推測目標已部署 EDR；T1595.001 偵察資料已收集",
  "orient_summary": "PentestGPT 重新評估：EDR 環境，建議改用低噪音技術",
  "decide_summary": "選擇 T1134（Token Manipulation），低噪音，規避 EDR",
  "act_summary": "已派發至 Agent bravo，執行橫向移動準備",
  "status": "completed"
}
```

**UI 觀察：** `/c5isr` 的 OODA 迭代計數從 1 更新至 2。`/planner` 的 OODA 時間軸新增第二筆迭代記錄。

---

### Step 6：ORIENT (Round 2) — 查看最終狀態

```bash
# 查看作戰整體狀態
curl http://localhost:8000/api/operations/op-phantom-eye-001
```

```bash
# 查看 OODA 完整時間軸
curl http://localhost:8000/api/operations/op-phantom-eye-001/ooda/timeline
```

**預期（作戰狀態）：**
```json
{
  "id": "op-phantom-eye-001",
  "name": "OP-2024-017 PHANTOM-EYE",
  "status": "active",
  "ooda_iteration_count": 2,
  "objective": "取得 Domain Admin 權限（DC-01）",
  "progress_pct": 45,
  "active_agents": 4
}
```

**預期（OODA 時間軸）：**
```json
{
  "timeline": [
    {
      "iteration": 1,
      "timestamp": "2024-01-15T09:00:00Z",
      "observe": "初始偵察完成",
      "orient":  "推薦 T1003.001",
      "decide":  "批准執行",
      "act":     "派發至 Caldera"
    },
    {
      "iteration": 2,
      "timestamp": "2024-01-15T09:35:00Z",
      "observe": "T1068 失敗，偵測到 EDR",
      "orient":  "調整策略：改用 T1134",
      "decide":  "批准低噪音方案",
      "act":     "派發至 Caldera（Agent bravo）"
    }
  ]
}
```

---

## 自動化 Demo Runner

若要自動執行上述 6 個步驟（適合展示場景），使用內建的 Demo Runner：

```bash
# 標準執行（每步間隔 3 秒）
cd backend && python3 -m app.seed.demo_runner

# 自訂步驟間隔（秒）
DEMO_STEP_DELAY=5 python3 -m app.seed.demo_runner

# 指定作戰 ID
DEMO_OPERATION_ID=op-phantom-eye-001 python3 -m app.seed.demo_runner
```

**Demo Runner 行為：**
- 自動依序執行 6 個步驟，每步之間暫停 `DEMO_STEP_DELAY` 秒（預設 3 秒）
- 每步輸出預期結果與實際 API 回應的對比
- 若某步驟失敗，顯示錯誤說明並繼續後續步驟
- 完成後輸出整體 Demo 成功率摘要

**輸出範例：**
```
[DEMO] OP-2024-017 PHANTOM-EYE — 自動 Demo 開始
────────────────────────────────────────────────
[Step 1/6] OBSERVE — 觸發 OODA 循環... ✅ 成功
[Step 2/6] ORIENT  — 查詢 PentestGPT 推薦... ✅ 成功（信心度 85%）
[Step 3/6] DECIDE  — 審閱 C5ISR 域狀態... ✅ 成功（整體戰備 79%）
[Step 4/6] ACT     — 查看技術執行結果... ✅ 成功（3 項技術，1 項成功）
[Step 5/6] OBSERVE — 觸發第 2 輪 OODA... ✅ 成功（迭代 #2）
[Step 6/6] ORIENT  — 查看最終作戰狀態... ✅ 成功（進度 45%）
────────────────────────────────────────────────
[DEMO] 完成：6/6 步驟成功，OODA 迭代 2 次
```

---

## WebSocket 事件驗證

Athena 透過 WebSocket 推送即時事件至前端畫面。在瀏覽器 Console 執行以下指令，即可監聽事件串流：

```javascript
// 在瀏覽器 Console 執行
const ws = new WebSocket('ws://localhost:8000/ws/op-phantom-eye-001');
ws.onopen    = ()  => console.log('[WS] 已連線');
ws.onmessage = (e) => console.log('[WS] 事件：', JSON.parse(e.data));
ws.onerror   = (e) => console.error('[WS] 錯誤：', e);
```

連線後，觸發一次 OODA 循環，觀察以下事件依序出現：

```bash
curl -X POST http://localhost:8000/api/operations/op-phantom-eye-001/ooda/trigger
```

**預期 WebSocket 事件序列：**

| 事件 | 觸發時機 | 影響畫面 | 範例 Payload |
|------|----------|----------|--------------|
| `ooda.phase` | OODA 階段切換 | C5ISR, Planner | `{"phase":"observe","iteration":3}` |
| `recommendation` | PentestGPT 新建議產生 | C5ISR, Navigator | `{"rec_id":"rec-003","confidence":0.9}` |
| `execution.update` | 技術執行狀態變更 | Navigator, Planner | `{"technique":"T1003.001","status":"success"}` |
| `c5isr.update` | C5ISR 域健康度變更 | C5ISR | `{"domain":"cyber","health_pct":80}` |
| `fact.new` | 新情報收集 | C5ISR | `{"fact_type":"credential","host":"FILE-SRV-01"}` |
| `log.new` | 日誌產生 | Monitor | `{"level":"info","message":"T1003.001 執行完成"}` |
| `agent.beacon` | Agent 心跳更新 | Monitor | `{"agent_id":"alpha","last_seen":"..."}` |

**事件流說明：**
1. `ooda.phase` 事件先觸發 4 次（4 個 OODA 階段）
2. `recommendation` 在 Orient 階段結束後觸發
3. `execution.update` 在 Act 階段派發任務後觸發
4. `agent.beacon` 持續每 30 秒觸發（獨立於 OODA 循環）

---

## 下一步

完成 Demo 演練後，可進一步探索：

- **[系統架構](architecture.md)** — 深入了解 C5ISR 框架、三層智慧架構與授權策略
- **[開發路線圖](ROADMAP.md)** — Phase 1-8 的詳細開發計畫，了解 Athena 的未來演進方向

如需整合真實 Caldera 環境，請參閱 `docs/architecture/data-architecture.md` 的 Caldera API 對接說明。

---

*文件版本：v1.0*
*對應 Athena 版本：0.1.0-poc*
*作戰場景：OP-2024-017 PHANTOM-EYE*
*最後更新：2026-02-26*
