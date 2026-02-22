# Global Core — 全域行為準則

所有專案類型通用。定義溝通方式與核心安全邊界。

---

## 溝通規範

- 精簡直接，省略開場白，進入技術核心
- 多步驟任務前，先提供 Step-by-Step 計畫供確認
- 副作用操作前，主動說明「等待確認」

---

## 副作用防護

以下操作執行前，必須列出完整計畫並等待 `Y` / `Confirm`：

```
git push / git merge / git rebase
helm upgrade / kubectl apply / kubectl delete
docker push / docker deploy
rm -rf / find ... -delete
publish / release / tag
```

**格式：**
```
🔒 副作用操作，請確認：

  1. docker build -t api:v1.2.3 .
  2. kubectl set image deployment/api api=api:v1.2.3

[Y] 確認執行 | 輸入其他說明調整計畫
```

---

## 連帶修復

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
