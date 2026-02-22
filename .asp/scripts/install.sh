#!/usr/bin/env bash
# AI-SOP-Protocol 安裝腳本
# 用途：在新專案或現有專案中快速植入 ASP

set -euo pipefail

PROTOCOL_REPO="https://github.com/astroicers/AI-SOP-Protocol"
PROTOCOL_DIR=".asp-tmp"

# 跨平台 sed
SED_INPLACE() {
    if [ "$(uname)" = "Darwin" ]; then
        sed -i '' "$@"
    else
        sed -i "$@"
    fi
}

echo ""
echo "🤖 AI-SOP-Protocol 安裝程式"
echo "=============================="

# 自動偵測專案類型
detect_type() {
    if [ -f "go.mod" ] || [ -f "Dockerfile" ] || [ -f "docker-compose.yml" ]; then
        echo "system"
    elif [ -f "requirements.txt" ] || [ -f "pyproject.toml" ]; then
        echo "system"
    elif [ -f "package.json" ] && grep -qE '"react"|"vue"|"next"' package.json 2>/dev/null; then
        echo "system"
    else
        echo "content"
    fi
}

DETECTED=$(detect_type)
DEFAULT_NAME="$(basename "$(pwd)")"

# 偵測是否為互動式（curl | bash 時 stdin 不是 terminal）
if [ -t 0 ]; then
    echo ""
    echo "🔍 自動偵測專案類型：$DETECTED"
    read -rp "確認類型（Enter 使用偵測值，或輸入 system/content/architecture）: " PROJECT_TYPE
    PROJECT_TYPE="${PROJECT_TYPE:-$DETECTED}"

    read -rp "專案名稱（Enter 使用目錄名 $DEFAULT_NAME）: " PROJECT_NAME
    PROJECT_NAME="${PROJECT_NAME:-$DEFAULT_NAME}"

    echo ""
    read -rp "啟用 RAG 知識庫？（y/N）: " ENABLE_RAG
    ENABLE_RAG="${ENABLE_RAG:-n}"

    read -rp "啟用 Guardrail 護欄？（y/N）: " ENABLE_GUARDRAIL
    ENABLE_GUARDRAIL="${ENABLE_GUARDRAIL:-n}"

    read -rp "HITL 等級（minimal/standard/strict，Enter 使用 standard）: " HITL_LEVEL
    HITL_LEVEL="${HITL_LEVEL:-standard}"
else
    echo ""
    echo "📋 非互動模式，使用自動偵測值："
    PROJECT_TYPE="$DETECTED"
    PROJECT_NAME="$DEFAULT_NAME"
    ENABLE_RAG="n"
    ENABLE_GUARDRAIL="n"
    HITL_LEVEL="standard"
    echo "  type: $PROJECT_TYPE | name: $PROJECT_NAME | hitl: $HITL_LEVEL"
fi

echo ""
echo "📥 安裝 AI-SOP-Protocol..."

# 建立必要目錄
mkdir -p docs/adr docs/specs

# 複製核心檔案
if git ls-remote "$PROTOCOL_REPO" &>/dev/null 2>&1; then
    git clone --depth=1 "$PROTOCOL_REPO" "$PROTOCOL_DIR" 2>/dev/null
    if [ -f "CLAUDE.md" ]; then
        if grep -q "AI-SOP-Protocol" CLAUDE.md; then
            echo "ℹ️  CLAUDE.md 已包含 ASP 引用，跳過"
        else
            cp CLAUDE.md CLAUDE.md.pre-asp
            { printf '# AI-SOP-Protocol (ASP) — 行為憲法\n\n'; \
              printf '> 本專案遵循 ASP 協議。讀取順序：本區塊 → `.ai_profile` → 對應 `.asp/profiles/`（按需）\n'; \
              printf '> 鐵則與 Profile 對應表請見：.asp/profiles/global_core.md\n\n---\n\n'; \
              cat CLAUDE.md; } > CLAUDE.md.tmp && mv CLAUDE.md.tmp CLAUDE.md
            echo "⚠️  已在現有 CLAUDE.md 頂部插入 ASP 引用（原檔備份於 CLAUDE.md.pre-asp）"
        fi
    else
        cp "$PROTOCOL_DIR/CLAUDE.md" ./CLAUDE.md
    fi
    # 清理舊版 ASP（根目錄散落的檔案）
    for OLD_DIR in profiles templates scripts/rag advanced; do
        if [ -d "$OLD_DIR" ] && [ ! -d ".asp" ]; then
            echo "🔄 偵測到舊版 ASP，清理根目錄 $OLD_DIR/"
            rm -rf "$OLD_DIR"
        fi
    done

    # 清理舊的 .asp/ 避免 cp -r 嵌套
    rm -rf .asp/profiles .asp/templates .asp/scripts .asp/advanced
    mkdir -p .asp

    # 支援新結構（.asp/）和舊結構（根目錄）
    if [ -d "$PROTOCOL_DIR/.asp/profiles" ]; then
        SRC="$PROTOCOL_DIR/.asp"
    else
        SRC="$PROTOCOL_DIR"
    fi
    cp -r "$SRC/profiles" ./.asp/profiles
    cp -r "$SRC/templates" ./.asp/templates
    cp -r "$SRC/scripts" ./.asp/scripts
    cp -r "$SRC/advanced" ./.asp/advanced

    # Makefile: 新安裝時複製，升級時更新
    if [ ! -f "Makefile" ]; then
        cp "$PROTOCOL_DIR/Makefile" ./Makefile
    elif grep -q "cp templates/ADR_Template" Makefile 2>/dev/null; then
        echo "🔄 偵測到舊版 Makefile，更新為新版"
        cp "$PROTOCOL_DIR/Makefile" ./Makefile
    fi
    [ ! -f ".gitignore" ] && cp "$PROTOCOL_DIR/.gitignore" ./.gitignore
    rm -rf "$PROTOCOL_DIR"
    echo "✅ 從 GitHub 安裝完成"
else
    echo "⚠️  無法連接 GitHub，請手動複製以下目錄："
    echo "   CLAUDE.md / .asp/ / Makefile / .gitignore"
fi

# 建立 .ai_profile
RAG_VAL="disabled"
[ "${ENABLE_RAG,,}" = "y" ] && RAG_VAL="enabled"

GUARDRAIL_VAL="disabled"
[ "${ENABLE_GUARDRAIL,,}" = "y" ] && GUARDRAIL_VAL="enabled"

cat > .ai_profile << EOF
type: ${PROJECT_TYPE}
mode: single
workflow: standard
rag: ${RAG_VAL}
guardrail: ${GUARDRAIL_VAL}
hitl: ${HITL_LEVEL}
name: ${PROJECT_NAME}
EOF

echo "✅ 已建立 .ai_profile"

# 更新 Makefile APP_NAME
if [ -f "Makefile" ] && grep -q "APP_NAME ?= app-service" Makefile; then
    SED_INPLACE "s/APP_NAME ?= app-service/APP_NAME ?= ${PROJECT_NAME}/" Makefile
    echo "✅ 已更新 Makefile APP_NAME → ${PROJECT_NAME}"
fi

# 初始化 ADR-001（若不存在）
if ! ls docs/adr/ADR-001-*.md &>/dev/null 2>&1; then
    ADR_FILE="docs/adr/ADR-001-initial-technology-stack.md"
    cp .asp/templates/ADR_Template.md "$ADR_FILE"
    SED_INPLACE "s/ADR-000/ADR-001/g" "$ADR_FILE"
    SED_INPLACE "s/決策標題/初始技術棧選型/g" "$ADR_FILE"
    SED_INPLACE "s/YYYY-MM-DD/$(date +%Y-%m-%d)/g" "$ADR_FILE"
    echo "✅ 已建立 ADR-001（請填入實際技術棧）"
fi

# 初始化 architecture.md（若不存在）
if [ ! -f "docs/architecture.md" ]; then
    cp .asp/templates/architecture_spec.md docs/architecture.md
    SED_INPLACE "s/PROJECT_NAME/${PROJECT_NAME}/g" docs/architecture.md
    echo "✅ 已建立 docs/architecture.md"
fi

# 設定 RAG git hook
if [ "${ENABLE_RAG,,}" = "y" ] && [ -d ".git" ]; then
    HOOK_FILE=".git/hooks/post-commit"
    cat > "$HOOK_FILE" << 'HOOKEOF'
#!/usr/bin/env bash
if git diff --name-only HEAD~1 HEAD 2>/dev/null | grep -q "^docs/"; then
    echo "📚 docs/ 有異動，更新 RAG 索引..."
    make rag-index --silent 2>/dev/null || true
fi
HOOKEOF
    chmod +x "$HOOK_FILE"
    echo "✅ 已設定 RAG git hook（post-commit）"
fi

echo ""
echo "🎉 安裝完成！"
echo ""
echo "啟動 Claude Code，輸入："
echo ""
echo "  請讀取 CLAUDE.md，依照 .ai_profile 載入對應 Profile。"
echo "  然後幫我完成以下初始化："
echo "  1. 確認 .ai_profile 設定是否正確"
echo "  2. 依專案需求調整 Makefile（build / test / deploy targets）"
echo "  3. 填寫 ADR-001 技術棧選型"
echo "  4. 更新 docs/architecture.md"
echo ""
if [ "${ENABLE_RAG,,}" = "y" ]; then
    echo "RAG 已啟用，還需要："
    echo "  pip install chromadb sentence-transformers && make rag-index"
    echo ""
fi
