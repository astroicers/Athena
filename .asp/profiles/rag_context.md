# Local RAG Context Profile

適用：已建立本地向量知識庫的專案。
載入條件：`rag: enabled`

> **設計動機**：解決 CLAUDE.md 靜態 Profile import 的根本限制。
> AI 可在任何時間點主動查詢最新的規格、ADR、架構文件，
> 不依賴人工貼入，也不受 context 視窗限制。

---

## 查詢優先原則

在 RAG 模式下，**回答任何專案相關問題前必須先查詢知識庫**：

```
收到問題
  ↓
屬於專案範疇？
  ├── 否 → 參考 guardrail.md 處理
  └── 是 → make rag-search Q="問題關鍵字"
              ↓
          找到相關文件？
          ├── 是 → 引用來源後回答（標明文件路徑與相似度）
          └── 否 → 說明「知識庫無此規格」並建議建立 SPEC 或 ADR
```

**禁止**：在未查詢知識庫的情況下，從訓練記憶回答專案架構問題。
原因：訓練記憶可能與當前 ADR 決策衝突。

---

## 引用格式

查詢到內容後，回答必須標明來源：

```
根據 ADR-003（API 閘道選型，Accepted 2024-11-20），
選擇 Kong 的原因是...

來源：docs/adr/ADR-003-api-gateway.md（相似度 0.91）
```

---

## 知識庫缺失的處理

```
❌ 禁止：用訓練記憶猜測專案架構
✅ 正確：「知識庫找不到相關規格，建議：
         make spec-new TITLE="功能名稱"
         或
         make adr-new TITLE="決策標題"」
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
