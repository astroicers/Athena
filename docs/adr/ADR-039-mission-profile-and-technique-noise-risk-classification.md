# [ADR-039]: Mission Profile and Technique Noise-Risk Classification

| 欄位 | 內容 |
|------|------|
| **狀態** | `Accepted` |
| **日期** | 2026-03-10 |
| **決策者** | 架構師 / 專案負責人 |

---

## 背景（Context）

Athena 的 OODA 循環目前不區分任務類型——無論是隱蔽偵察還是全面攻擊，Orient/Decide 使用相同的參數和推薦邏輯。這導致：

1. **無隱蔽控制**：Orient 可能在隱蔽任務中推薦高噪音技術（如全端口掃描）
2. **無任務適配**：信心門檻、並行度、推薦數量不隨任務需求調整
3. **無噪音預算**：缺乏對操作噪音的量化追蹤和控制
4. **技術無風險標記**：35+ techniques 缺乏被偵測機率和作戰代價的分類

紅隊實際作戰中，任務類型（隱蔽偵察 vs 全面攻擊）對技術選擇有根本性影響。系統需要能根據任務類型自動過濾和調整行為。

---

## 評估選項（Options Considered）

### 選項 A：硬編碼規則（if-else 邏輯）

- **優點**：實作簡單直接
- **缺點**：每次新增任務類型需修改多處程式碼；規則分散在各 service 中難以維護
- **風險**：規則不一致、遺漏更新

### 選項 B：標記制 + YAML 設定檔（推薦）

- **優點**：
  - Technique 標記 `noise_level`，任務類型設定允許的最大 noise -> 自動過濾
  - 所有任務參數集中在 YAML 設定檔，易於調整和擴展
  - 新增任務類型只需加 YAML 條目，不改程式碼
- **缺點**：需建立 YAML loader service
- **風險**：YAML 設定錯誤可能導致過度寬鬆/嚴格的過濾

---

## 決策（Decision）

我們選擇 **選項 B：標記制 + YAML 設定檔**。

### 四種任務類型（Mission Profile）

| 類型 | 代號 | 場景 | OPSEC 要求 | 時間壓力 |
|------|------|------|-----------|---------|
| Stealth Recon | `SR` | 純偵察收集情報 | 極高 | 低 |
| Covert Operation | `CO` | 隱蔽滲透/APT 模擬 | 高 | 低 |
| Standard Pentest | `SP` | 標準滲透測試 | 中 | 中 |
| Full Assault | `FA` | 限時攻防/紅藍協作 | 低 | 高 |

### 各任務類型對 OODA 參數影響

| 參數 | SR | CO | SP | FA |
|------|----|----|----|----|
| max_noise 允許 | low only | low+medium | all | all |
| max_parallel 並行 | 1 | 2 | 5 | 8 |
| min_confidence 門檻 | 0.8 | 0.7 | 0.5 | 0.4 |
| orient_max_options | 2 | 2 | 3 | 3 |
| noise_budget (10min) | 10 pts | 25 pts | 50 pts | unlimited |
| 認證嘗試限制 | 每目標 max 2 | 每目標 max 3 | 每目標 max 5 | 無限制 |
| 偵測事件反應 | 立即暫停+通知 | 暫停+通知 | 通知 | 記錄但不暫停 |

### Technique 雙維度標記

每個 technique 標記兩個獨立維度：
- **noise_level**（被偵測機率）：`low` / `medium` / `high`
- **risk_level**（作戰效益 vs 代價）：`low` / `medium` / `high` / `critical`

### Noise x Risk 決策矩陣

```
                    noise: low       noise: medium      noise: high
                 +----------------+-----------------+----------------+
risk: low        | 隨便做         | 可以做          | FA 才做        |
                 | (DNS enum)     | (banner grab)   | (nmap scan)    |
                 +----------------+-----------------+----------------+
risk: medium     | 值得做         | 要評估          | 慎重           |
                 | (讀 config)    | (exploit app)   | (spray creds)  |
                 +----------------+-----------------+----------------+
risk: high       | 小心做         | 需確認          | 非常危險       |
                 | (dump hash)    | (privesc)       | (lateral+提權) |
                 +----------------+-----------------+----------------+
risk: critical   | 指揮官決定     | 指揮官決定      | 幾乎不做       |
                 | (golden ticket)| (DCSync)        | (worm-like)    |
                 +----------------+-----------------+----------------+
```

任務類型決定可操作範圍：
- **SR**: 左上角（low noise + low risk）
- **CO**: 左半部（low/medium noise）
- **SP**: 大部分格子，critical 需確認
- **FA**: 全部開放

### 實作方案

- `backend/app/data/mission_profiles.yaml`：4 種任務完整參數（含 C5ISR 閾值）
- `backend/app/services/mission_profile_loader.py`：YAML loader，啟動時載入，可熱重載
- `operations` 表新增 `mission_profile VARCHAR(2) DEFAULT 'SP'`
- `techniques` 表新增 `noise_level VARCHAR(10) DEFAULT 'medium'`
- Orient 過濾邏輯：`noise_rank(technique.noise_level) <= noise_rank(profile.max_noise)`
- 35+ techniques seed data 標記 noise_level

---

## 後果（Consequences）

**正面影響：**
- 不同任務類型自動適配 OODA 行為，無需手動調整
- Technique 推薦基於量化的 noise/risk 維度，提升作戰安全性
- YAML 設定集中管理，易於團隊調整和 review

**負面影響 / 技術債：**
- 35+ techniques 的 noise_level 初始標記需人工審核
- YAML 設定變更無即時驗證（依賴 test 覆蓋）

**後續追蹤：**
- [ ] SPEC-046：完整實作規格
- [ ] Seed data 中 35+ techniques noise_level 標記
- [ ] Orient 技術過濾邏輯整合
- [ ] 前端 Operation 建立介面新增任務類型選擇

---

## 成功指標（Success Metrics）

| 指標 | 目標值 | 驗證方式 | 檢查時間 |
|------|--------|----------|----------|
| Mission Profile 載入 | 4 種類型全部正確載入 | 單元測試 | 實作完成時 |
| Orient noise 過濾 | CO 模式不推薦 noise:high 技術 | 整合測試 | 實作完成時 |
| Technique 標記覆蓋率 | 100% techniques 有 noise_level | Seed data 驗證 | 實作完成時 |
| 任務類型參數生效 | SR max_parallel=1, FA=8 | 行為測試 | 實作完成時 |

> 若新增任務類型需修改 Python 程式碼（而非僅 YAML），應重新評估設定檔架構。

---

## 關聯（Relations）

- 取代：無
- 被取代：無
- 參考：ADR-040（C5ISR 閾值隨任務類型變動）、SPEC-046（實作規格）
- 參考：SPEC-064（Orient Engine 規格 — mission_profile 噪音過濾機制 `_filter_options_by_noise` 完整說明）
