# [ADR-040]: C5ISR Reverse OODA Influence and OPSEC Monitoring Architecture

| 欄位 | 內容 |
|------|------|
| **狀態** | `Accepted` |
| **日期** | 2026-03-10 |
| **決策者** | 架構師 / 專案負責人 |

---

## 背景（Context）

Athena 目前的 C5ISR 是**被動報告**——彙整 6 域健康度供儀表板顯示，但不影響 OODA 循環的行為。OPSEC（操作安全）也沒有獨立追蹤機制。這導致：

1. **C5ISR 無反向影響**：即使 Comms 域健康度為 0%（所有工具離線），OODA 仍會嘗試執行需要這些工具的技術
2. **無 OPSEC 監控**：不追蹤操作噪音、偵測風險、曝露事件，指揮官缺乏態勢感知
3. **C5ISR 指標粗糙**：每域僅 1-2 個統計值，無法精確反映紅隊作戰能力
4. **無歷史時序**：C5ISR 只有當前快照（UPSERT），無法追蹤趨勢和回顧
5. **無約束傳遞機制**：OODA 各服務（Orient/Decide/ACT）間無統一的約束傳遞結構

紅隊軍事顧問角度：C5ISR 不只是「顯示板」，它是指揮官的**態勢感知基礎**。C5ISR 健康度應主動影響 OODA 決策——這是本次架構重構的核心目標。

---

## 評估選項（Options Considered）

### D1. C5ISR 反向影響機制

#### 選項 A：僅提供建議（soft constraints）

- **優點**：不限制 OODA 行為，指揮官自行判斷
- **缺點**：建議容易被忽略；危急情況下（工具全掛）仍會執行無效操作

#### 選項 B：僅硬限制（hard constraints）

- **優點**：強制保護，避免無效操作
- **缺點**：過於僵硬，指揮官無法依戰場判斷覆寫

#### 選項 C：雙層閾值（WARNING + CRITICAL）+ Override（推薦）

- **優點**：WARNING 觸發建議（soft），CRITICAL 觸發硬限制（hard），指揮官可 Override
- **缺點**：實作較複雜，需 Override 審計追蹤
- **風險**：閾值設定不當可能過度/不足限制，需依任務類型動態調整

### D2. OPSEC 定位

#### 選項 A：作為 C5ISR 第 7 域

- **優點**：統一框架，顯示在同一面板
- **缺點**：概念混淆——C5ISR 六域是「作戰能力」（越高越好），OPSEC 是「作戰約束」（偵測風險越低越好）

#### 選項 B：獨立面板 + 跨域 Penalty（推薦）

- **優點**：保持概念清晰；OPSEC 的 detection_risk 作為 penalty 影響所有 C5ISR 域的健康度
- **缺點**：前端需額外面板空間
- **風險**：跨域 penalty 係數需校準

---

## 決策（Decision）

### D1. 選擇選項 C：雙層閾值 + Override

**Constraint Engine 架構**：

每輪 OODA 循環開始前，`constraint_engine.evaluate()` 讀取 C5ISR 六域健康度 + OPSEC 狀態 -> 產生 `OperationalConstraints` 物件 -> 傳遞給 Orient/Decide/ACT。

```
trigger_cycle(operation_id)
  |
  +- [PRE] constraint_engine.evaluate(operation_id, mission_profile)
  |        -> 讀取 c5isr_statuses (6 域) + opsec_monitor 指標
  |        -> 比對 mission_profile.c5isr_thresholds
  |        -> 檢查 active overrides
  |        -> 產生 OperationalConstraints
  |
  +- OBSERVE -> ORIENT -> DECIDE -> ACT
  |  (各階段接收 constraints，依規則調整行為)
  |
  +- [POST-ACT] opsec_monitor.evaluate()
  |
  +- C5ISR update + OPSEC penalty
```

**OperationalConstraints 結構**：
- `warnings`: 域 + 建議文字
- `hard_limits`: 域 + 限制規則
- `orient_max_options`: 推薦數量上限
- `min_confidence_override`: 信心門檻覆蓋
- `max_parallel_override`: 並行上限覆蓋
- `blocked_targets`: 禁止操作的目標 ID
- `forced_mode`: "recovery" / "recon_first" / None
- `noise_budget_remaining`: OPSEC noise budget 剩餘
- `active_overrides`: 指揮官已 override 的域

**C5ISR 閾值隨任務類型變動**（與 ADR-039 連動）：

| 域 | SR (W/C) | CO (W/C) | SP (W/C) | FA (W/C) |
|---|----------|----------|----------|----------|
| Command | 70/50 | 60/40 | 50/25 | 30/10 |
| Control | 80/60 | 70/50 | 50/25 | 30/10 |
| Comms | 70/50 | 60/40 | 50/25 | 30/10 |
| Computers | 60/40 | 50/30 | 40/20 | 20/5 |
| Cyber | 70/50 | 60/40 | 50/25 | 30/10 |
| ISR | 80/60 | 70/50 | 50/25 | 30/10 |

**各域反應規則**：

| 域 | WARNING 反應（建議） | CRITICAL 反應（硬限制） |
|---|---|---|
| **Command** | Orient 選項縮減為 2 | Orient 只給 1 個, medium risk 不需確認 |
| **Control** | 注入存取流失警告，偏好 persistence/recovery | 禁止對 lost 目標執行, forced_mode="recovery" |
| **Comms** | Decide 排除不可用引擎 | max_parallel=1, 跳過不可用引擎 |
| **Computers** | 注入停滯分析，連續失敗目標降優先 | forced_mode="recon_first" |
| **Cyber** | min_confidence += 0.15 | min_confidence = 0.75 |
| **ISR** | 情報不足目標信心 -0.10 | 禁止對 fact_count<3 目標執行利用技術 |

**Override 機制**：
- API: `POST /operations/{id}/constraints/override` body: `{domain}`
- 單輪 OODA 生效，下一輪自動重新評估
- 需二次確認
- 寫入 event_store（審計追蹤）
- WebSocket: `constraint.override`

### D2. 選擇選項 B：OPSEC 獨立 + 跨域 Penalty

### C5ISR 六域指標重定義（每域 3 指標）

**Command（指揮）**

| 指標 | 權重 | 計算方式 |
|------|------|---------|
| OODA 迭代速度 | 0.35 | 預期 vs 實際完成次數比率 |
| 指揮官決策延遲 | 0.35 | 推薦產生到審批的平均時間差 |
| 推薦採納率 | 0.30 | accepted / (accepted + rejected) |

**Control（控制）**

| 指標 | 權重 | 計算方式 |
|------|------|---------|
| Agent 存活率 | 0.40 | alive / total agents |
| 存取穩定性 | 0.35 | 1 - (lost / total events) |
| 持久化覆蓋率 | 0.25 | has_persistence / compromised |

**Comms（通訊）**

| 指標 | 權重 | 計算方式 |
|------|------|---------|
| MCP 工具可用率 | 0.40 | available / total MCP tools |
| 執行引擎可用性 | 0.35 | available / total engines |
| 工具回應延遲 | 0.25 | 正常化延遲分數 |

**Computers（滲透）**

| 指標 | 權重 | 計算方式 |
|------|------|---------|
| 滲透率 | 0.35 | compromised / total targets |
| 提權覆蓋率 | 0.35 | root_or_system / compromised |
| 高價值目標狀態 | 0.30 | compromised_hvt / total_hvt |

**Cyber（攻防效率）**

| 指標 | 權重 | 計算方式 |
|------|------|---------|
| 整體執行成功率 | 0.35 | successful / total execs |
| 近期趨勢 | 0.40 | 最近 5 次 vs 整體成功率 |
| 技術多樣性 | 0.25 | distinct_tactics / available |

**ISR（情報）**

| 指標 | 權重 | 計算方式 |
|------|------|---------|
| Fact 覆蓋率 | 0.35 | categories_with_facts / 7 |
| 漏洞驗證率 | 0.35 | validated / discovered CVEs |
| 情報新鮮度 | 0.30 | 最新 fact 距今時間正常化 |

### OPSEC 監控（5 指標）

| 指標 | 計算方式 | 權重 |
|------|---------|------|
| Noise Score | 10 分鐘滑動窗口: low=+1, medium=+3, high=+8 pts | 0.35 |
| Dwell Time | per-target: now - first_successful_access | 0.25 |
| Exposure Count | 認證失敗+1, 高噪音+1, burst+1, 異常錯誤+1 | 0.25 |
| Artifact Footprint | 從 technique 類型推斷 | 0.15 |
| Detection Risk | 綜合分數 0-100（上面四項加權） | -- |

**Noise Budget**（每 10 分鐘）：SR=10 pts, CO=25 pts, SP=50 pts, FA=unlimited

**跨域 Penalty**：
- `detection_risk > 60` -> 所有 C5ISR 域 health_pct *= 0.85
- `detection_risk > 80` -> 所有 C5ISR 域 health_pct *= 0.70

**OPSEC -> OODA 整合**：
- Orient: prompt 注入 OPSEC 狀態 + noise budget 剩餘
- Decide: composite confidence 加入 opsec_factor (risk<30=1.0, 30-60=0.7, 60-80=0.4, >80=0.1)
- ACT: noise budget 超支時限制 high noise 技術

### C5ISR 歷史保存

c5isr_mapper 從 UPSERT-only 改為 UPSERT + INSERT history（`c5isr_status_history` 表），支援時序趨勢查詢。

---

## 後果（Consequences）

**正面影響：**
- C5ISR 從被動報告升級為主動約束，真正實現「態勢感知驅動決策」
- 指揮官透過 Override 保留最終決策權（human-in-the-loop）
- OPSEC 跨域 penalty 確保偵測風險影響全局判斷
- 歷史時序支援趨勢分析和事後回顧

**負面影響 / 技術債：**
- 每輪 OODA 增加 constraint_engine.evaluate() 開銷（預期 < 50ms）
- 閾值和 penalty 係數需根據實戰校準
- Override 審計日誌持續增長，需定期清理策略

**後續追蹤：**
- [ ] SPEC-047：C5ISR 六域指標重構 + Constraint Engine
- [ ] SPEC-048：OPSEC 監控服務 + 跨域 Penalty
- [ ] SPEC-049：Dashboard 聚合 API + Time-Series
- [ ] 前端 Override 按鈕 + 二次確認 UI
- [ ] 前端 OPSEC 獨立面板

---

## 成功指標（Success Metrics）

| 指標 | 目標值 | 驗證方式 | 檢查時間 |
|------|--------|----------|----------|
| C5ISR WARNING -> 建議 | constraints.warnings 非空 | 整合測試 | Phase 2 完成時 |
| C5ISR CRITICAL -> 硬限制 | blocked_targets / forced_mode 生效 | 整合測試 | Phase 2 完成時 |
| Override 單輪生效 | Override 後下一輪重新評估 | 行為測試 | Phase 2 完成時 |
| OPSEC detection_risk 計算 | 0-100 範圍，非恆 0 | 單元測試 | Phase 3 完成時 |
| 跨域 Penalty 生效 | risk>60 時 C5ISR health 下降 | 整合測試 | Phase 3 完成時 |
| constraint_engine 延遲 | < 50ms per evaluation | 效能測試 | Phase 2 完成時 |

> 若閾值在實戰中導致過多 false positive（頻繁觸發 CRITICAL），應依據 event_store 數據校準。

---

## 關聯（Relations）

- 取代：無
- 被取代：無
- 參考：ADR-039（任務類型閾值連動）、SPEC-047/048/049（實作規格）
