# SPEC-047：C5ISR Restructure & Constraint Engine

| 欄位 | 內容 |
|------|------|
| **規格 ID** | SPEC-047 |
| **關聯 ADR** | ADR-040 |
| **估算複雜度** | 高 |

---

## 🎯 目標（Goal）

> C5ISR 六域健康度反向影響 OODA 行為：WARNING 觸發建議，CRITICAL 觸發硬限制。
> Constraint Engine 在每輪 OODA 開始前讀取 C5ISR + OPSEC → 產生 OperationalConstraints。
> 指揮官可 override 單域限制（單輪生效）。C5ISR 歷史記錄支援時間序列分析。

---

## ✅ 驗收標準（Done When）

- [ ] constraint_engine.evaluate() 正確讀取 C5ISR 六域健康度
- [ ] 域健康度低於 WARNING → warnings 非空
- [ ] 域健康度低於 CRITICAL → hard_limits 非空
- [ ] Override API 成功解除限制，event_store 有記錄
- [ ] c5isr_status_history 有時間序列記錄
- [ ] OODA controller 在循環開始前呼叫 constraint_engine
- [ ] `make test` 通過，無回歸
