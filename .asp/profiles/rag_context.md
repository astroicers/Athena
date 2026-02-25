# Local RAG Context Profile

適用：已建立本地向量知識庫的專案。
載入條件：`rag: enabled`

> **設計動機**：解決 CLAUDE.md 靜態 Profile import 的根本限制。
> AI 可在任何時間點主動查詢最新的規格、ADR、架構文件，
> 不依賴人工貼入，也不受 context 視窗限制。

---

## 查詢決策流程

```
FUNCTION answer_project_question(question, project_scope, knowledge_base):

  // 範疇判斷 — 非專案問題委派 guardrail 處理
  IF NOT question.is_within(project_scope):
    RETURN CALL guardrail.handle_question(question)

  // 查詢知識庫 — 回答前必須先查
  results = EXECUTE("make rag-search Q='{question.keywords}'")

  IF results.has_matches:
    best = results.top(1)
    RETURN format_answer(
      content    = best.content,
      source     = best.file_path,
      similarity = best.score,
      template   = "根據 {source}（相似度 {similarity}），{content}\n\n"
                 + "來源：{source}（相似度 {similarity}）"
    )
  ELSE:
    RETURN suggest_create(
      message = "知識庫找不到相關規格",
      options = [
        "make spec-new TITLE='...'",
        "make adr-new TITLE='...'"
      ]
    )

  // ─── 不可違反的約束 ───
  INVARIANT: never_use_training_memory_for(project_architecture)
  // 原因：訓練記憶可能與當前 ADR 決策衝突
```

---

## 知識庫組成

| 文件類型 | 路徑 | 向量化時機 |
|----------|------|-----------|
| 規格書 | `docs/specs/SPEC-*.md` | `make spec-new` 後 |
| ADR | `docs/adr/ADR-*.md` | `make adr-new` 後 |
| Profiles | `.asp/profiles/*.md` | `make rag-rebuild` |
| 架構文件 | `docs/architecture.md` | git commit 後（hook）|
| Changelog | `CHANGELOG.md` | git commit 後（hook）|

---

## 推薦技術棧

```
嵌入模型：all-MiniLM-L6-v2（~90MB，本地執行）
向量 DB：ChromaDB 或 SQLite-vec（零配置）
索引體積：~13MB / 1,300 份文件（實測）
查詢速度：< 100ms（本地）
```

安裝：`pip install chromadb sentence-transformers`

---

## Git Hook 自動更新

`.git/hooks/post-commit`：

```bash
#!/usr/bin/env bash
if git diff --name-only HEAD~1 HEAD 2>/dev/null | grep -q "^docs/"; then
    echo "📚 docs/ 有異動，更新 RAG 索引..."
    make rag-index --silent
fi
```

```bash
chmod +x .git/hooks/post-commit
```
