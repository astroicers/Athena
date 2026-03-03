#!/usr/bin/env bash
# ASP Hook: rag-auto-index.sh
# 用途：git post-commit hook — 當 docs/ 或 .asp/profiles/ 有異動時自動增量更新 RAG 索引
#
# 安裝方式（二擇一）：
#   1. 複製到 .git/hooks/post-commit
#   2. 使用 git config core.hooksPath 指向 .asp/hooks/
#
# 前置條件：pip install chromadb sentence-transformers

set -euo pipefail

# 檢查是否有相關檔案異動
CHANGED=$(git diff --name-only HEAD~1 HEAD 2>/dev/null || echo "")

if echo "$CHANGED" | grep -qE "^(docs/|\.asp/profiles/)"; then
    echo "📚 docs/ 或 profiles/ 有異動，增量更新 RAG 索引..."
    make rag-index --silent 2>/dev/null || true
fi

exit 0
