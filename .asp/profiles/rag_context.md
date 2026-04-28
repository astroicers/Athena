# Local RAG Context Profile

<!-- requires: global_core -->
<!-- optional: guardrail -->

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
| Postmortem | `docs/postmortems/PM-*.md` | `make postmortem-new` 後 |
| Profiles | `.asp/profiles/*.md` | `make rag-rebuild` |
| 架構文件 | `docs/architecture.md` | git commit 後（hook）|
| Changelog | `CHANGELOG.md` | git commit 後（hook）|

---

## 索引策略

| 指令 | 行為 |
|------|------|
| `make rag-index` | 增量更新（預設）：只重建有變更的檔案 |
| `make rag-rebuild` | 全量重建：刪除索引後完整重建 |

**增量更新原理**：透過檔案 SHA-256 hash manifest（`.rag/index/index_manifest.json`）追蹤每個檔案的最後索引版本。只有 hash 變更或新增/刪除的檔案會被重新向量化。

**ADR 狀態感知**：索引 metadata 包含 ADR 狀態（`adr_status`）。查詢結果包含 Deprecated 狀態的 ADR 時，應提醒使用者該決策已被取代。

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

使用 `.asp/hooks/rag-auto-index.sh`（取代直接內嵌在 .git/hooks/ 中）：

```bash
# 安裝方式
cp .asp/hooks/rag-auto-index.sh .git/hooks/post-commit
chmod +x .git/hooks/post-commit
```

```bash
chmod +x .git/hooks/post-commit
```

---

## .asp-fact-check.md 整合（v3.7）

> `.asp-fact-check.md` 是 Fact Verification Gate（見 `global_core.md`）的驗證日誌，
> 記錄每次外部事實查證的來源與結果。

### 自動餵入 RAG

當 `rag: enabled` 時，`.asp-fact-check.md` 應納入 RAG 索引，供後續查詢複用：

```bash
# 確認 fact-check log 已加入索引範圍
make rag-index   # 自動掃描所有 .asp-*.md（含 fact-check log）
```

**查詢用途：**
- `make rag-search Q="axios 版本"` → 找出之前驗證過的版本記錄，避免重複查證
- `make rag-search Q="GDPR 第 17 條"` → 查詢是否已有法規驗證記錄（含驗證日期）

### 過期清理策略

| 條件 | 處置 |
|------|------|
| 驗證日期超過 30 天 | 重新查證（技術文件更新速度快）|
| 驗證日期超過 90 天 | 標注 `[STALE]`，下次用到時強制重新驗證 |
| 驗證結果為 ⚠️ 或 ❌ | 保留至問題解決，不納入自動清理 |

```bash
# 查詢需要重新驗證的項目
make rag-search Q="fact-check STALE"
```
