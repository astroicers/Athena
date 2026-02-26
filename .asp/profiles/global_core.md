# Global Core — 全域行為準則

所有專案類型通用。定義溝通方式與核心安全邊界。

---

## 溝通規範

- 精簡直接，省略開場白，進入技術核心
- 多步驟任務前，先提供 Step-by-Step 計畫供確認
- 修改原始碼前，先確認對應 SPEC 存在（詳見 system_dev.md「Pre-Implementation Gate」）
- 副作用操作前，主動說明「等待確認」

---

## 副作用防護

以下操作執行前，必須列出完整計畫並等待 `Y` / `Confirm`：

```
git rebase          # 內建權限系統確認（SessionStart hook 清理 allow list）
docker push/deploy  # 內建權限系統確認（SessionStart hook 清理 allow list）
rm -r* / find -delete  # 內建權限系統確認（SessionStart hook 清理 allow list）
git push            # 內建權限系統確認（SessionStart hook 清理 allow list）
```

> **技術執行**：Claude Code 內建權限系統對不在 allow list 的指令彈出「Allow this bash command?」確認框。
> SessionStart hook（`clean-allow-list.sh`）每次 session 啟動時自動清理 allow list 中的危險規則。

---

## 連帶修復

修復 Bug 前：

- **非 trivial Bug**（跨模組、邏輯修正、行為變更）→ 先 `make spec-new TITLE="BUG-..."` 建立 SPEC
- **trivial Bug**（單行修復、typo、配置錯誤）→ 可直接修復，但需說明豁免理由

修復 Bug 後：

1. 判斷 bug 類型
   - **模式性錯誤**（邏輯、型別、邊界）→ 必須 `grep -r` 全專案，找出相似位置一次修復
   - **單點配置錯誤**（環境變數、路徑）→ 可豁免，但需在回覆中說明判斷理由

2. 回覆格式：「已檢查全專案，共 N 處相同問題」或「判斷為單點錯誤，豁免全域掃描，原因：...」

---

## 文件原子化

代碼邏輯變動 **必須** 同步更新（延後需說明理由）：

- 架構異動 → `docs/architecture.md`
- 技術決策 → `docs/adr/ADR-XXX.md`
- 版本紀錄 → `CHANGELOG.md`
- 使用方式異動 → `README.md`

---

## Token 節約

- Shell 指令超過 3 行 → 移入 Makefile，只輸出 `make xxx`
- 重複性操作 → 禁止每次重新輸出完整指令
- `type: content` 的專案 → 跳過所有 Docker、測試、CI/CD 邏輯
