# SPEC-021: Attack Path Timeline — Navigator 頁統一攻擊路徑視圖

| 欄位 | 內容 |
|------|------|
| **SPEC-ID** | SPEC-021 |
| **標題** | Attack Path Timeline — Navigator 頁統一攻擊路徑視圖 |
| **狀態** | ✅ 完成（commit: feat: Attack Path Timeline + DirectSSHEngine） |
| **優先度** | High |
| **相關 ADR** | ADR-003（OODA 引擎）、ADR-017（DirectSSHEngine） |
| **日期** | 2026-03-02 |

---

## 動機

MITRE ATT&CK 的 Reconnaissance → Resource Development → Initial Access → ... → Impact 路徑目前分散在不同頁面，沒有統一的「攻擊路徑 + MITRE 標籤」一體視圖。指揮官需要一眼看出 kill chain 推進到哪個階段，哪些技術成功/失敗。

---

## 功能需求

| ID | 需求 | 驗收條件 |
|----|------|---------|
| F1 | 14 欄水平時序，對應 MITRE ATT&CK 14 個 tactics（TA0043→TA0040） | 欄位順序正確，標頭顯示 tactic 縮寫 + tactic_id |
| F2 | 已執行 techniques 以 pill 呈現於對應 tactic 欄（以 tactic_id 分組） | Pill 出現在正確 tactic 欄 |
| F3 | pill 顯示 status 圓點和 MITRE ID | ● 綠=success, ✗ 紅=failed, ⟳ 青=running/queued |
| F4 | hover tooltip 顯示 technique_name、engine、duration_sec、target_ip | Hover 顯示完整資訊 |
| F5 | 最遠達到欄底部有 accent 亮邊框 | `border-b-2 border-athena-accent` 在正確欄 |
| F6 | WebSocket `execution.update` 事件觸發即時刷新 | 執行後不需 refresh 頁面即更新 |
| F7 | 空欄顯示灰色虛線 | `border-dashed opacity-30` 風格 |
| F8 | loading 狀態顯示 shimmer skeleton | `animate-pulse` placeholder |

---

## API 需求

**新增 endpoint：** `GET /api/operations/{operation_id}/attack-path`

**Response schema：**
```json
{
  "operation_id": "string",
  "entries": [
    {
      "execution_id": "string",
      "mitre_id": "string",
      "technique_name": "string",
      "tactic": "string",
      "tactic_id": "string",
      "kill_chain_stage": "string",
      "risk_level": "string",
      "status": "queued|running|success|partial|failed",
      "engine": "string",
      "started_at": "ISO8601 | null",
      "completed_at": "ISO8601 | null",
      "duration_sec": "number | null",
      "result_summary": "string | null",
      "error_message": "string | null",
      "facts_collected_count": "number",
      "target_hostname": "string | null",
      "target_ip": "string | null"
    }
  ],
  "highest_tactic_idx": "number (0-13)",
  "tactic_coverage": {"TA0043": 2, "TA0001": 1}
}
```

---

## 實作位置

| 元件 | 檔案 |
|------|------|
| 後端 models | `backend/app/models/api_schemas.py` — `AttackPathEntry`, `AttackPathResponse` |
| 後端 endpoint | `backend/app/routers/techniques.py` — `GET /attack-path` |
| 前端 types | `frontend/src/types/attackPath.ts` |
| 前端 API | `frontend/src/lib/api.ts` — `getAttackPath()` |
| 前端 元件 | `frontend/src/components/mitre/AttackPathTimeline.tsx` |
| 前端 整合 | `frontend/src/app/navigator/page.tsx` |

---

## 驗證結果

- ✅ `python3 -m pytest tests/ -q` — 95 passed, 6 skipped（0 regression）
- ✅ `npx tsc --noEmit` — 0 TypeScript errors
- ✅ 14 欄正確對應 TACTIC_ORDER_IDS（TA0043→TA0040）
- ✅ WebSocket `execution.update` 觸發即時刷新
