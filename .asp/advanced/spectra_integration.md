# Advanced: Spectra / OpenSpec 深度整合

> 此文件為**進階選配**，屬於工具整合層，不影響 ASP 核心功能。
> 適用於已熟悉 Binary Shadowing 且需要深度 CLI 整合的使用者。

---

## 什麼是 Binary Shadowing

將自製可執行檔放在 `$PATH` 前端，攔截並強化原版 NPM 工具行為：

```
$PATH 搜尋順序：
  .bin/openspec       ← 你的魔改版（先被找到）
  /usr/local/bin/openspec ← NPM 原版（被跳過）
```

**評估是否需要**：若 `make rag-search` 已滿足需求，不必使用 Binary Shadowing。
只有在「需要讓 Claude Code Skill 直接呼叫 openspec CLI」時才有必要。

---

## Binary Wrapper

`.bin/openspec`：

```bash
#!/usr/bin/env bash
REAL_BIN=$(which -a openspec | grep -v "$(dirname "$0")" | head -1)

case "$1" in
  search)
    shift
    python3 "$(git rev-parse --show-toplevel)/scripts/rag/search.py" "$@"
    ;;
  archive)
    "$REAL_BIN" archive "$@"
    EXIT_CODE=$?
    if [ $EXIT_CODE -eq 0 ]; then
        echo "📚 更新 RAG 索引..."
        make rag-index --silent -C "$(git rev-parse --show-toplevel)"
    fi
    exit $EXIT_CODE
    ;;
  *)
    exec "$REAL_BIN" "$@"
    ;;
esac
```

```bash
mkdir -p .bin && chmod +x .bin/openspec
```

**PATH 設定（加入 `~/.zshrc`）：**
```bash
export PATH="$(git rev-parse --show-toplevel 2>/dev/null)/.bin:$PATH"
```

---

## /opsx:ask Skill（`.claude/commands/opsx-ask.md`）

```markdown
---
name: opsx:ask
description: 查詢本地 RAG 知識庫，召回相關 SPEC/ADR/架構文件
---

當需要確認規格、架構決策或模組邊界時呼叫此 Skill。

執行步驟：
1. `make rag-search Q="$QUERY"`
2. 引用召回片段，標明來源與相似度
3. 若知識庫無結果，說明並建議建立 SPEC 或 ADR

禁止：在未查詢知識庫的情況下，用訓練記憶回答專案架構問題。
```

---

## Upstream Sync 策略

```bash
git remote add upstream https://github.com/openspec/openspec
git fetch upstream
git log upstream/main --oneline -10  # 查看最新 10 個 commit
```

判斷流程：
1. 查看 changelog
2. 確認是否影響你的 wrapper
3. 安全 → cherry pick；有衝突 → 在 ADR 記錄跳過原因

---

## 維護成本提示

| 風險 | 緩解方式 |
|------|----------|
| Upstream breaking change | 固定 Sync + ADR 記錄 |
| 新人不知道 wrapper 存在 | README 說明 + CLAUDE.md 加入提示 |
| CI/CD 環境 PATH 失效 | CI 腳本加入 `.bin` 路徑 |
