#!/usr/bin/env bash
# AI-SOP-Protocol 安裝腳本
# 用途：在新專案或現有專案中快速植入 ASP（支援升級）

set -euo pipefail

PROTOCOL_REPO="https://github.com/astroicers/AI-SOP-Protocol"
PROTOCOL_DIR=".asp-tmp"

# 失敗時自動清理暫存目錄
cleanup() {
    local exit_code=$?
    if [ $exit_code -ne 0 ] && [ -d "$PROTOCOL_DIR" ]; then
        echo "⚠️  安裝中斷，清理暫存目錄 $PROTOCOL_DIR"
        rm -rf "$PROTOCOL_DIR"
    fi
    exit $exit_code
}
trap cleanup EXIT

# 檢查 jq（Hooks 需要）
if command -v jq &>/dev/null; then
    JQ_AVAILABLE=true
else
    JQ_AVAILABLE=false
fi

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

# 偵測是否為升級
IS_UPGRADE=false
INSTALLED_VERSION="0.0.0"
if [ -f ".asp/VERSION" ]; then
    INSTALLED_VERSION=$(cat ".asp/VERSION" | tr -d '[:space:]')
    IS_UPGRADE=true
elif [ -f ".ai_profile" ]; then
    IS_UPGRADE=true
fi

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
    if [ "$IS_UPGRADE" = true ]; then
        echo "🔄 偵測到已安裝 ASP v${INSTALLED_VERSION}，執行升級"
    fi
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
    echo "📋 非互動模式，使用自動偵測值（可透過環境變數覆寫）："
    PROJECT_TYPE="${ASP_TYPE:-$DETECTED}"
    PROJECT_NAME="${ASP_NAME:-$DEFAULT_NAME}"
    ENABLE_RAG="${ASP_RAG:-n}"
    ENABLE_GUARDRAIL="${ASP_GUARDRAIL:-n}"
    HITL_LEVEL="${ASP_HITL:-standard}"
    echo "  type: $PROJECT_TYPE | name: $PROJECT_NAME | hitl: $HITL_LEVEL | rag: $ENABLE_RAG | guardrail: $ENABLE_GUARDRAIL"
fi

echo ""
echo "📥 安裝 AI-SOP-Protocol..."

# 建立必要目錄
mkdir -p docs/adr docs/specs

# 複製核心檔案
if git ls-remote "$PROTOCOL_REPO" &>/dev/null 2>&1; then
    git clone --depth=1 "$PROTOCOL_REPO" "$PROTOCOL_DIR" 2>/dev/null

    # 讀取新版本號
    NEW_VERSION="unknown"
    if [ -f "$PROTOCOL_DIR/.asp/VERSION" ]; then
        NEW_VERSION=$(cat "$PROTOCOL_DIR/.asp/VERSION" | tr -d '[:space:]')
    fi

    if [ "$IS_UPGRADE" = true ]; then
        echo "🔄 升級 ASP: v${INSTALLED_VERSION} → v${NEW_VERSION}"
    fi

    # --- CLAUDE.md 處理 ---
    if [ -f "CLAUDE.md" ]; then
        if grep -q "AI-SOP-Protocol" CLAUDE.md; then
            # 升級場景：檢查是否有更新
            if [ "$IS_UPGRADE" = true ] && ! diff -q "$PROTOCOL_DIR/CLAUDE.md" CLAUDE.md &>/dev/null; then
                cp CLAUDE.md CLAUDE.md.pre-upgrade
                cp "$PROTOCOL_DIR/CLAUDE.md" ./CLAUDE.md
                echo "🔄 CLAUDE.md 已更新至 v${NEW_VERSION}（舊版備份於 CLAUDE.md.pre-upgrade）"
            else
                echo "ℹ️  CLAUDE.md 已為最新，跳過"
            fi
        else
            # 首次安裝：在現有 CLAUDE.md 頂部插入 ASP 引用
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

    # --- 清理舊版 ASP（根目錄散落的檔案）---
    for OLD_DIR in profiles templates advanced; do
        if [ -d "$OLD_DIR" ]; then
            # 驗證是否真的是 ASP 目錄（避免誤刪使用者同名目錄）
            if [ -f "$OLD_DIR/global_core.md" ] || [ -f "$OLD_DIR/ADR_Template.md" ] || \
               [ -f "$OLD_DIR/spectra_integration.md" ]; then
                echo "🔄 偵測到舊版 ASP，清理根目錄 $OLD_DIR/"
                rm -rf "$OLD_DIR"
            fi
        fi
    done
    # 特殊處理：scripts/rag（舊版巢狀結構）
    if [ -d "scripts/rag" ] && [ -f "scripts/rag/build_index.py" ]; then
        echo "🔄 清理舊版 scripts/rag/"
        rm -rf "scripts/rag"
        rmdir scripts 2>/dev/null || true
    fi

    # 清理舊的 .asp/ 子目錄避免 cp -r 嵌套
    rm -rf .asp/profiles .asp/templates .asp/scripts .asp/advanced .asp/hooks
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
    if [ -d "$SRC/hooks" ]; then
        cp -r "$SRC/hooks" ./.asp/hooks
        chmod +x .asp/hooks/*.sh 2>/dev/null || true
    fi

    # 複製版本檔案
    if [ -f "$PROTOCOL_DIR/.asp/VERSION" ]; then
        cp "$PROTOCOL_DIR/.asp/VERSION" ./.asp/VERSION
    fi

    # --- Makefile 升級偵測（多層策略）---
    if [ ! -f "Makefile" ]; then
        # 全新安裝
        cp "$PROTOCOL_DIR/Makefile" ./Makefile
    elif grep -q "cp templates/ADR_Template" Makefile 2>/dev/null; then
        # 舊版格式（pre-.asp/ 目錄結構）
        echo "🔄 偵測到舊版 Makefile（legacy 格式），更新為新版"
        CURRENT_APP=$(grep "^APP_NAME" Makefile | head -1 || true)
        cp "$PROTOCOL_DIR/Makefile" ./Makefile
        if [ -n "${CURRENT_APP:-}" ]; then
            SED_INPLACE "s/^APP_NAME.*/$CURRENT_APP/" Makefile
        fi
    elif grep -q "ASP_MAKEFILE_VERSION" Makefile 2>/dev/null; then
        # 有版本標記：比對版本
        INSTALLED_MK_VER=$(grep "ASP_MAKEFILE_VERSION" Makefile | sed 's/.*=//' || true)
        NEW_MK_VER=$(grep "ASP_MAKEFILE_VERSION" "$PROTOCOL_DIR/Makefile" | sed 's/.*=//' || true)
        if [ "${INSTALLED_MK_VER:-}" != "${NEW_MK_VER:-}" ]; then
            CURRENT_APP=$(grep "^APP_NAME" Makefile | head -1 || true)
            cp "$PROTOCOL_DIR/Makefile" ./Makefile
            if [ -n "${CURRENT_APP:-}" ]; then
                SED_INPLACE "s/^APP_NAME.*/$CURRENT_APP/" Makefile
            fi
            echo "🔄 Makefile 已升級 ${INSTALLED_MK_VER:-unknown} → ${NEW_MK_VER:-unknown}（APP_NAME 已保留）"
        fi
    elif [ "$IS_UPGRADE" = true ] && ! grep -q "guardrail-log" Makefile 2>/dev/null; then
        # ASP Makefile 但缺少新版 target（無版本標記的過渡版本）
        echo "🔄 偵測到缺少新版目標的 Makefile，更新為新版"
        CURRENT_APP=$(grep "^APP_NAME" Makefile | head -1 || true)
        cp "$PROTOCOL_DIR/Makefile" ./Makefile
        if [ -n "${CURRENT_APP:-}" ]; then
            SED_INPLACE "s/^APP_NAME.*/$CURRENT_APP/" Makefile
        fi
    fi

    # --- .gitignore 增量合併 ---
    if [ ! -f ".gitignore" ]; then
        cp "$PROTOCOL_DIR/.gitignore" ./.gitignore
    else
        # 逐行補充缺失的條目
        ADDED=0
        while IFS= read -r line; do
            [ -z "$line" ] && continue
            [[ "$line" == \#* ]] && continue
            if ! grep -qF "$line" .gitignore; then
                echo "$line" >> .gitignore
                ADDED=$((ADDED + 1))
            fi
        done < "$PROTOCOL_DIR/.gitignore"
        if [ "$ADDED" -gt 0 ]; then
            echo "✅ 已補充 $ADDED 條 .gitignore 條目"
        fi
    fi

    rm -rf "$PROTOCOL_DIR"
    echo "✅ 從 GitHub 安裝完成"
else
    echo "⚠️  無法連接 GitHub，請手動複製以下目錄："
    echo "   CLAUDE.md / .asp/ / Makefile / .gitignore"
fi

# --- .ai_profile 處理（升級時保留使用者自訂）---
RAG_VAL="disabled"
[ "${ENABLE_RAG,,}" = "y" ] && RAG_VAL="enabled"

GUARDRAIL_VAL="disabled"
[ "${ENABLE_GUARDRAIL,,}" = "y" ] && GUARDRAIL_VAL="enabled"

NEW_PROFILE="type: ${PROJECT_TYPE}
mode: single
workflow: standard
rag: ${RAG_VAL}
guardrail: ${GUARDRAIL_VAL}
hitl: ${HITL_LEVEL}
name: ${PROJECT_NAME}"

if [ -f ".ai_profile" ]; then
    echo "ℹ️  .ai_profile 已存在，保留現有設定"
    # 僅補充缺失欄位
    ADDED_FIELDS=0
    for FIELD in type mode workflow rag guardrail hitl name; do
        if ! grep -q "^${FIELD}:" .ai_profile; then
            DEFAULT_VAL=$(echo "$NEW_PROFILE" | grep "^${FIELD}:" | head -1)
            if [ -n "$DEFAULT_VAL" ]; then
                echo "$DEFAULT_VAL" >> .ai_profile
                echo "  + 補充缺失欄位：$DEFAULT_VAL"
                ADDED_FIELDS=$((ADDED_FIELDS + 1))
            fi
        fi
    done
    if [ "$ADDED_FIELDS" -eq 0 ]; then
        echo "  （所有欄位完整，無需補充）"
    fi
    echo "✅ .ai_profile 已保留（如需重設，請刪除後重跑安裝）"
else
    echo "$NEW_PROFILE" > .ai_profile
    echo "✅ 已建立 .ai_profile"
fi

# 更新 Makefile APP_NAME（僅首次安裝時）
if [ "$IS_UPGRADE" = false ] && [ -f "Makefile" ] && grep -q "APP_NAME ?= app-service" Makefile; then
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

# 設定 Claude Code Hooks（SessionStart: 清理危險 allow 規則）
HOOKS_JSON='{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "\"$CLAUDE_PROJECT_DIR\"/.asp/hooks/clean-allow-list.sh"
          }
        ]
      }
    ]
  }
}'

mkdir -p .claude

if [ "$JQ_AVAILABLE" = true ]; then
    if [ -f ".claude/settings.json" ]; then
        # 升級：移除舊版 ASP hooks（PreToolUse enforce-*），加入新版 SessionStart hook
        EXISTING=$(cat .claude/settings.json)
        echo "$EXISTING" | jq '
            # 移除舊版 ASP PreToolUse hooks
            .hooks.PreToolUse = [(.hooks.PreToolUse // [])[] | select(
                (.hooks // []) | all(.command | test("enforce-(side-effects|workflow)\\.sh$") | not)
            )] |
            # 如果 PreToolUse 為空則移除
            if (.hooks.PreToolUse | length) == 0 then del(.hooks.PreToolUse) else . end |
            # 加入 SessionStart hook（移除舊的 ASP SessionStart hook 後加入）
            .hooks.SessionStart = [
                ((.hooks.SessionStart // [])[] | select(
                    (.hooks // []) | all(.command | test("clean-allow-list\\.sh$") | not)
                )),
                {
                    "hooks": [
                        {
                            "type": "command",
                            "command": "\"$CLAUDE_PROJECT_DIR\"/.asp/hooks/clean-allow-list.sh"
                        }
                    ]
                }
            ]
        ' > .claude/settings.json.tmp \
            && mv .claude/settings.json.tmp .claude/settings.json
        echo "✅ 已將 ASP Hook 合併至 .claude/settings.json（SessionStart: 清理危險 allow 規則）"
    else
        echo "$HOOKS_JSON" | jq '.' > .claude/settings.json
        echo "✅ 已建立 .claude/settings.json（含 ASP SessionStart Hook）"
    fi
else
    if [ ! -f ".claude/settings.json" ]; then
        cat > .claude/settings.json << 'HOOKJSON'
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "\"$CLAUDE_PROJECT_DIR\"/.asp/hooks/clean-allow-list.sh"
          }
        ]
      }
    ]
  }
}
HOOKJSON
        echo "✅ 已建立 .claude/settings.json（含 ASP SessionStart Hook）"
    else
        echo "⚠️  .claude/settings.json 已存在且無 jq 可用，請手動加入 hooks 設定"
        echo "   參考：.asp/hooks/ 目錄內的腳本"
    fi
fi

# --- 清理 settings.local.json 中的危險 allow 規則（安裝時執行一次）---
if [ "$JQ_AVAILABLE" = true ] && [ -f ".claude/settings.local.json" ]; then
    DANGEROUS_PATTERNS='git\s+rebase|git\s+push|docker\s+(push|deploy)|rm\s+-[a-z]*r|find\s+.*-delete'
    BEFORE_COUNT=$(jq -r '[.permissions.allow // [] | .[] | select(startswith("Bash("))] | length' .claude/settings.local.json 2>/dev/null || echo 0)
    jq --arg pattern "$DANGEROUS_PATTERNS" '
      .permissions.allow = [
        (.permissions.allow // [])[] |
        select((startswith("Bash(") and test($pattern)) | not)
      ]
    ' .claude/settings.local.json > .claude/settings.local.json.tmp \
        && mv .claude/settings.local.json.tmp .claude/settings.local.json
    AFTER_COUNT=$(jq -r '[.permissions.allow // [] | .[] | select(startswith("Bash("))] | length' .claude/settings.local.json 2>/dev/null || echo 0)
    REMOVED_COUNT=$((BEFORE_COUNT - AFTER_COUNT))
    if [ "$REMOVED_COUNT" -gt 0 ]; then
        echo "🔒 已從 allow list 移除 ${REMOVED_COUNT} 條危險規則（git rebase/push, docker push, rm -r 等）"
    fi
fi

# 設定 RAG git hook（增量插入，不破壞現有 hooks）
ASP_RAG_MARKER_START="# --- ASP RAG HOOK START ---"
ASP_RAG_MARKER_END="# --- ASP RAG HOOK END ---"

if [ "${ENABLE_RAG,,}" = "y" ] && [ -d ".git" ]; then
    HOOK_FILE=".git/hooks/post-commit"

    ASP_RAG_BLOCK="$ASP_RAG_MARKER_START
if git diff --name-only HEAD~1 HEAD 2>/dev/null | grep -q \"^docs/\"; then
    echo \"📚 docs/ 有異動，更新 RAG 索引...\"
    make rag-index --silent 2>/dev/null || true
fi
$ASP_RAG_MARKER_END"

    if [ -f "$HOOK_FILE" ]; then
        # 移除舊的 ASP RAG 區塊（如存在）
        if grep -q "$ASP_RAG_MARKER_START" "$HOOK_FILE"; then
            SED_INPLACE "/$ASP_RAG_MARKER_START/,/$ASP_RAG_MARKER_END/d" "$HOOK_FILE"
        fi
        # 附加新區塊
        printf '\n%s\n' "$ASP_RAG_BLOCK" >> "$HOOK_FILE"
    else
        printf '#!/usr/bin/env bash\n\n%s\n' "$ASP_RAG_BLOCK" > "$HOOK_FILE"
    fi
    chmod +x "$HOOK_FILE"
    echo "✅ 已設定 RAG git hook（post-commit）— 保留現有 hooks"
fi

# --- 安裝/升級完成 ---
echo ""
if [ "$IS_UPGRADE" = true ]; then
    echo "🎉 升級完成！"
    echo ""
    echo "升級摘要 (v${INSTALLED_VERSION} → v${NEW_VERSION:-unknown})："
    echo "  ✅ 已更新：.asp/profiles, .asp/templates, .asp/scripts, .asp/hooks"
    echo "  🔒 已保留：.ai_profile, docs/adr/*, docs/specs/*, docs/architecture.md"
    echo ""
else
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
fi
if [ "${ENABLE_RAG,,}" = "y" ]; then
    echo "RAG 已啟用，還需要："
    echo "  pip install chromadb sentence-transformers && make rag-index"
    echo ""
fi
