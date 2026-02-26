# Vibe Coding — 規格驅動開發策略

適用：以「AI 餵食者 + 品質守門員」角色最大化輸出效率。
載入條件：`workflow: vibe-coding`

---

## 角色分工

```
人類（決策者）              AI（實作者）
─────────────────────────────────────
撰寫 SPEC-002 ────────→  執行 SPEC-001 中
確認設計方案  ←────────  規格複述 + 計畫
驗收成果      ←────────  Done Checklist
撰寫 SPEC-003 ────────→  執行 SPEC-002 中
```

核心原則：人類決策與 AI 實作的節奏**不互相等待**。

---

## AI 執行規則

拿到 SPEC 後：

1. **複述理解**：一段話說明 Goal 和 Done When 的理解
2. **列出計畫**：修改的檔案清單與修改理由
3. **等待確認**（HITL: standard / strict 時）
4. **自我驗收**：執行 Done When 清單並回報結果

**無 SPEC 時的處理：**
- 人類直接描述需求（非提供 SPEC）→ AI 主動建議 `make spec-new TITLE="..."` 並協助填寫
- 至少確認 Goal 和 Done When 後再開始實作
- 對話中可簡化為「口頭 SPEC」：AI 複述 Goal + Done When，人類確認後視為等效

---

## HITL 等級與暫停決策

```yaml
hitl: minimal   # 僅副作用前暫停（適合熟悉任務）
hitl: standard  # 每個實作計畫需確認（預設）
hitl: strict    # 每個檔案修改需確認（涉及生產/安全系統）
```

```
FUNCTION should_pause(operation, hitl_level):

  // Bash 副作用指令 — 由 Claude Code 內建權限系統確認
  // git rebase, docker push/deploy, rm -r*, find -delete, git push
  // → 不依賴此決策樹，內建權限系統彈出確認框

  // 檔案修改 — 依 HITL 等級（AI 自律）
  MATCH hitl_level:
    "minimal"  → RETURN PASS           // 信任 AI 判斷
    "standard" → RETURN ASK            // 每個實作計畫需確認
    "strict"   → RETURN MUST_ASK       // 每個檔案修改需確認
```

---

## Context 切換程序

切換功能模組時：

```
切換前：摘要目前狀態（完成了什麼、未完成什麼）
切換後：讀取新模組的 ADR → 確認測試基線通過
```

長對話管理：超過 50 回合的對話，重新讀取 CLAUDE.md。

---

## 模型選擇策略

| 任務類型 | 建議層級 | 理由 |
|----------|---------|------|
| 架構設計、ADR 撰寫 | 強（Opus/Sonnet） | 需要深度推理 |
| 樣板代碼、重複性生成 | 輕（Haiku） | 省 Token |
| 單元測試 | 中 | 結構化但需理解上下文 |
| 文件整理 | 輕 | 格式化工作 |

---

## Rate Limit 保護

```
FUNCTION on_rate_limit():

  // 觸發 Rate Limit 時 → 切換至文件工作
  SWITCH_TO document_tasks(["寫 SPEC", "更新 ADR", "整理文件"])
  // 此為有效利用等待時間，非浪費

  // 並行準備原則：
  // AI 執行 TASK-A 時，人類已在準備 TASK-B 的 SPEC
  // TASK-A 完成 → 立刻丟入 TASK-B，無等待
```

使用 `make session-checkpoint NEXT="下一個任務描述"` 在切換前儲存進度。
