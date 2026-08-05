# Demo Walkthrough — 端到端一次自主 OODA 迭代

本文帶你透過 [HTTP API](http-api.md) 驅動 Athena 跑**一次完整的 OODA 迭代**（Observe → Orient → Decide → Act → Iterate），看它如何自主決定下一步。全程使用**你擁有或已取得書面授權**的目標。

> ⚠️ **僅限授權使用**：以下所有指令只能對你自己的資產、或持有 Rules of Engagement / Statement of Work 的授權靶場執行。未經授權對第三方系統操作屬違法。本文只描述**流程與 API 呼叫**，不針對任何特定目標或交戰。
>
> 📸 截圖 / 錄影稍後補上（materials to follow）。

---

## 前置

- Athena 已啟動、`GET /api/health` 回 `200`。
- 已依 [LLM 配置指南](llm-config.md) 設好一個後端（demo 可先用 `MOCK_LLM=true` 走確定性、免連外）。
- 若設了 `ATHENA_API_TOKEN`，以下每個呼叫都要帶 `Authorization: Bearer <token>`（下方以 `$TOKEN` 表示）。
- 一個**你有權測試**的目標（下方以 `$TARGET` 佔位，例如你自架的靶機）。

```bash
BASE=http://localhost:58000/api
AUTH="Authorization: Bearer $TOKEN"
```

---

## 0. 啟動一次作戰

```bash
curl -s -X POST "$BASE/operations" -H "$AUTH" -H 'Content-Type: application/json' \
  -d "{\"name\":\"demo-run\",\"target_ip\":\"$TARGET\",\"async\":true}"
# → { "op_id": "…", "status": "running" }
```

記下回傳的 `op_id`：

```bash
OP=<回傳的 op_id>
```

> 想一次跑完整輪，直接 `POST $BASE/operations`（`async:false`）即可，Athena 會自動跑 Observe→Orient→Decide→Act。下面**逐階段**呼叫是為了看清楚每一步。

---

## 1. Observe — 態勢感知

蒐集目標現況（開放埠、服務、版本…），轉成 **fact**。

```bash
curl -s -X POST "$BASE/operations/$OP/observe" -H "$AUTH"
# → { "op_id": "…", "facts_before": N }

curl -s "$BASE/operations/$OP/observe/summary" -H "$AUTH"   # 注意：GET
# → { "op_id": "…", "summary": "…（這輪觀測到什麼）" }
```

查目前累積的 fact：

```bash
curl -s "$BASE/operations/$OP/facts/count" -H "$AUTH"       # → { op_id, count }
curl -s "$BASE/operations/$OP/facts"       -H "$AUTH"       # → [ …fact… ]
```

---

## 2. Orient — 決策腦研判

把 fact 交給 LLM 後端研判「這代表什麼、建議下一步打什麼」，並產出風險評分。這一步就是「**下一招哪裡來**」——由決策腦提議、而非人工挑選。

```bash
curl -s -X POST "$BASE/operations/$OP/orient" -H "$AUTH"
# → { "op_id": "…", "iter_id": "…", "facts_collected": M }
```

看人類可讀的作戰簡報：

```bash
curl -s "$BASE/operations/$OP/brief" -H "$AUTH"             # 注意：GET
# → { "op_id": "…", "brief": "…（研判與建議）" }
```

---

## 3. Decide — 合規閘

Orient 的建議**不會直接執行**。先過三重合規閘：目標是否在 scope、opsec 噪音預算是否足夠、RoE 是否允許。**界外一律擋**。

```bash
curl -s -X POST "$BASE/operations/$OP/decide" -H "$AUTH"
# → { "op_id": "…", "opsec_noise": …, "threat_level": … }
```

可單獨檢查 scope 與 opsec：

```bash
curl -s -X POST "$BASE/operations/$OP/scope/check" -H "$AUTH" \
  -H 'Content-Type: application/json' -d "{\"ip\":\"$TARGET\"}"
# → { "op_id": "…", "in_scope": true|false }

curl -s "$BASE/operations/$OP/opsec" -H "$AUTH"             # 注意：GET
# → { "op_id": "…", "noise_level": …, "budget_remaining": …, "threat_level": … }
```

> 若命中高風險 / 可疑蜜罐，會轉入人類審核（HITL）；核可後再以 `POST …/approve` 放行。

---

## 4. Act — 執行 + 觀測回饋

閘放行後才執行，並把結果（是否拿到 shell？是否 root？有無新憑證？）**抽取成新的 fact**，回饋進迴圈。

```bash
curl -s -X POST "$BASE/operations/$OP/act" -H "$AUTH"
# → { "op_id": "…", "iter_id": "…", "results": K }
```

---

## 5. Iterate — 迴圈用新 fact 決定下一步

一次 `iterate` 等於把 Observe→Orient→Decide→Act 再走一輪——但這輪的輸入是**上一輪新抽到的 fact**，所以「下一台打哪、下一招用什麼」是迴圈自己算出來的，不是你逐步下令。

```bash
curl -s -X POST "$BASE/operations/$OP/iterate" -H "$AUTH"
# → { "op_id": "…", "iter_id": "…", "facts_collected": …, "total_facts": …, "mode": "…" }
```

想讓它自己連續迭代，開排程：

```bash
curl -s -X POST "$BASE/operations/$OP/scheduler/start" -H "$AUTH" \
  -H 'Content-Type: application/json' -d '{"interval_secs":60}'
# 停止（注意：DELETE）
curl -s -X DELETE "$BASE/operations/$OP/scheduler/stop" -H "$AUTH"
```

---

## 6. 收尾 — 報告

```bash
curl -s "$BASE/operations/$OP/status" -H "$AUTH"            # → 狀態總覽
curl -s "$BASE/operations/$OP/report/markdown" -H "$AUTH"   # → { op_id, markdown }
```

`report/markdown` 產出可交付的 Markdown 報告（executive summary + findings + remediation）。

---

## 你剛剛看到的

一個完整 OODA 迭代：**觀測 → 研判（決策腦）→ 合規放行 → 執行 → 用新 fact 迭代**。關鍵不是「用了某個 exploit」，而是**下一步是迴圈自己決定的**，且每一步的執行都被三重合規閘框住。想在自己的模組 / 工具上動手，見 [擴充教學](extending.md)。
