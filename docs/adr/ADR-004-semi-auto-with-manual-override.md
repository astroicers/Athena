# [ADR-004]: 半自動化模式與手動覆寫

| 欄位 | 內容 |
|------|------|
| **狀態** | `Accepted` |
| **日期** | 2026-02-23 |
| **決策者** | 專案負責人 |

---

## 背景（Context）

Athena 定位為軍事紅隊顧問的指揮平台，OODA Decide 階段需決定技術執行的自動化程度。目標使用者為 10+ 年經驗的紅隊指揮官，他們需要：

1. 對低風險操作（偵察、掃描）避免重複手動批准
2. 對高風險操作（橫向移動、資料竊取）保留完全控制
3. 可隨時切換為全手動模式

ROADMAP Phase 5.2 定義了自動化邏輯，Phase 0 已在資料架構中設計了 `AutomationMode` 和 `RiskLevel` 列舉。需決定自動化策略及其 UI 互動模式。

---

## 評估選項（Options Considered）

### 選項 A：半自動 + 風險閾值 + HexConfirmModal

```
MANUAL      — 每步都需指揮官批准
SEMI-AUTO   — 依風險等級自動/手動（預設）

風險閾值：
├─ LOW      → 自動執行
├─ MEDIUM   → 自動排入佇列，需指揮官 approve
├─ HIGH     → 強制 HexConfirmModal 確認對話框
└─ CRITICAL → 永遠手動，不可自動化
```

- **優點**：軍事合規（關鍵操作永遠人工決策）；日常偵察不中斷工作流；UI 透過 HexConfirmModal 提供清晰的風險感知；每個技術的固有風險等級可獨立調整
- **缺點**：需為每個 MITRE 技術標註 `risk_level`
- **風險**：風險等級錯標可能導致高風險操作自動執行（透過 CRITICAL 永遠手動 + 指揮官覆寫機制緩解）

### 選項 B：全自動（AI 自主決策）

- **優點**：執行速度最快；展示 AI 自主能力
- **缺點**：軍事場景不可接受——高風險操作無人監督；失去 Athena「指揮官決策」的核心定位
- **風險**：資料竊取、破壞性操作在無人批准下執行，法律與道德風險極高

### 選項 C：全手動（每步批准）

- **優點**：最安全；完全人工控制
- **缺點**：大量低風險偵察操作需重複批准，嚴重降低效率；無法展示 AI 輔助的自動化價值
- **風險**：使用者疲勞導致批准流於形式（approval fatigue），反而降低安全性

---

## 決策（Decision）

我們選擇 **選項 A：半自動 + 風險閾值 + HexConfirmModal**，因為：

1. **軍事合規**：CRITICAL 操作永遠手動，HIGH 操作強制 HexConfirmModal 確認
2. **效率平衡**：LOW 自動執行偵察掃描，不中斷指揮官的戰略思考
3. **核心定位契合**：人類決策 + AI 輔助，非 AI 完全自主
4. **靈活性**：指揮官可隨時切換至 MANUAL 模式；`risk_threshold` 可調整自動化邊界

相關模型欄位：

```python
# Operation 模型
automation_mode: AutomationMode   # "manual" | "semi_auto"
risk_threshold: RiskLevel         # 當前自動化閾值

# Technique 模型
risk_level: RiskLevel             # 每個技術的固有風險等級
```

UI 互動矩陣：

| 風險等級 | Semi-Auto 行為 | UI 元素 |
|----------|---------------|---------|
| LOW | 自動執行，僅日誌通知 | Toast 通知 |
| MEDIUM | 排入佇列，等待 approve | 佇列徽章 + 批准按鈕 |
| HIGH | 強制確認 | HexConfirmModal 對話框 |
| CRITICAL | 永遠手動 | HexConfirmModal + 雙重確認 |

---

## 後果（Consequences）

**正面影響：**

- 指揮官可依作戰階段動態調整自動化程度（初期偵察 → semi-auto；進入橫向移動 → manual）
- HexConfirmModal 提供視覺化風險感知，降低誤操作
- `risk_level` 標註在 MITRE 技術層級，可跨作戰複用

**負面影響 / 技術債：**

- 需為 MITRE ATT&CK 技術目錄中使用的技術手動標註 `risk_level`（可從 MITRE 官方資料推導初始值）
- HexConfirmModal 需前端實作 WebSocket 阻斷/恢復邏輯

**後續追蹤：**

- [ ] Phase 2：在 Technique 模型中加入 `risk_level` 欄位
- [ ] Phase 4：實作 HexConfirmModal 前端元件
- [ ] Phase 5.2：實作 `decision_engine.py` 中的風險閾值邏輯
- [ ] Phase 6：在 Demo 場景中展示 LOW → HIGH 的自動化差異

---

## 關聯（Relations）

- 取代：（無）
- 被取代：（無）
- 參考：ADR-003（OODA 引擎中 Decide 階段）、ADR-005（Orient 引擎 confidence 分數驅動自動化判斷）、ADR-007（HexConfirmModal 需雙向 WebSocket 支援）、CLAUDE.md 自動化模式章節
