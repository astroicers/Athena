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
    # architecture：多服務 / IaC / K8s 基礎設施
    if [ -f "docker-compose.yml" ] && [ -d "docs/adr" ]; then
        echo "architecture"
    elif ls */Dockerfile &>/dev/null 2>&1 || ls */docker-compose.yml &>/dev/null 2>&1; then
        echo "architecture"  # 多個子目錄有 Dockerfile = 多服務
    elif [ -d "terraform" ] || [ -d "pulumi" ] || [ -f "helmfile.yaml" ] || \
         ls *.tf &>/dev/null 2>&1 || [ -f "skaffold.yaml" ]; then
        echo "architecture"
    # system：有程式碼或建置檔的單一專案
    elif [ -f "go.mod" ] || [ -f "Cargo.toml" ] || [ -f "pom.xml" ] || \
         [ -f "build.gradle" ] || [ -f "build.gradle.kts" ] || \
         [ -f "*.csproj" ] || [ -f "*.sln" ] || [ -f "CMakeLists.txt" ]; then
        echo "system"
    elif [ -f "Dockerfile" ] || [ -f "Makefile" ]; then
        echo "system"
    elif [ -f "requirements.txt" ] || [ -f "pyproject.toml" ] || [ -f "setup.py" ]; then
        echo "system"
    elif [ -f "package.json" ]; then
        echo "system"
    elif [ -f "Gemfile" ] || [ -f "mix.exs" ] || [ -f "composer.json" ]; then
        echo "system"
    # content：以上都沒有
    else
        echo "content"
    fi
}

DETECTED=$(detect_type)
DEFAULT_NAME="$(basename "$(pwd)")"

# 預設開發風格
apply_preset() {
    MODE=single  # 預設 mode，preset 4 會覆蓋
    case "$1" in
        1) # 標準模式
            ENABLE_RAG=n; ENABLE_GUARDRAIL=n; HITL_LEVEL=standard
            ENABLE_DESIGN=n; ENABLE_CODING_STYLE=n; ENABLE_OPENAPI=n
            ENABLE_FRONTEND_QUALITY=n; ENABLE_AUTONOMOUS=n; ENABLE_ORCHESTRATOR=n; ENABLE_AUTOPILOT=n; WORKFLOW=standard ;;
        2) # 高速自主模式
            ENABLE_RAG=n; ENABLE_GUARDRAIL=n; HITL_LEVEL=minimal
            ENABLE_DESIGN=n; ENABLE_CODING_STYLE=n; ENABLE_OPENAPI=n
            ENABLE_FRONTEND_QUALITY=n; ENABLE_AUTONOMOUS=y; ENABLE_ORCHESTRATOR=y; ENABLE_AUTOPILOT=n; WORKFLOW=vibe-coding ;;
        3) # 完整治理模式
            ENABLE_RAG=y; ENABLE_GUARDRAIL=y; HITL_LEVEL=strict
            ENABLE_DESIGN=y; ENABLE_CODING_STYLE=y; ENABLE_OPENAPI=y
            ENABLE_FRONTEND_QUALITY=y; ENABLE_AUTONOMOUS=n; ENABLE_ORCHESTRATOR=n; ENABLE_AUTOPILOT=n; WORKFLOW=standard ;;
        4) # 高速自主+多Agent模式
            ENABLE_RAG=n; ENABLE_GUARDRAIL=n; HITL_LEVEL=minimal
            ENABLE_DESIGN=n; ENABLE_CODING_STYLE=n; ENABLE_OPENAPI=n
            ENABLE_FRONTEND_QUALITY=n; ENABLE_AUTONOMOUS=y; ENABLE_ORCHESTRATOR=y; ENABLE_AUTOPILOT=n; WORKFLOW=vibe-coding; MODE=multi-agent ;;
        *) return 1 ;;
    esac
}

# 偵測是否為互動式（curl | bash 時 stdin 不是 terminal）
if [ -t 0 ]; then
    echo ""
    if [ "$IS_UPGRADE" = true ]; then
        echo "🔄 偵測到已安裝 ASP v${INSTALLED_VERSION}，執行升級"
    fi
    echo "專案類型：  [1] system  [2] content  [3] architecture  （偵測：$DETECTED）"
    read -rp "選擇 (1-3，Enter 使用偵測值): " TYPE_CHOICE
    case "${TYPE_CHOICE:-}" in
        1) PROJECT_TYPE=system ;;
        2) PROJECT_TYPE=content ;;
        3) PROJECT_TYPE=architecture ;;
        *) PROJECT_TYPE="$DETECTED" ;;
    esac
    PROJECT_NAME="$DEFAULT_NAME"

    echo "開發風格：  [1] 標準  [2] 高速自主  [3] 完整治理  [4] 高速自主+多Agent"
    read -rp "選擇 (1-4，Enter 使用 1): " PRESET_CHOICE
    apply_preset "${PRESET_CHOICE:-1}"
else
    echo ""
    echo "📋 非互動模式（可透過環境變數覆寫）"
    PROJECT_TYPE="${ASP_TYPE:-$DETECTED}"
    PROJECT_NAME="$DEFAULT_NAME"
    apply_preset "${ASP_PRESET:-1}"
    echo "  type: $PROJECT_TYPE | preset: ${ASP_PRESET:-1} | hitl: $HITL_LEVEL"
fi

echo ""
echo "📥 安裝 AI-SOP-Protocol..."

# 建立必要目錄
mkdir -p docs/adr docs/specs

# 複製核心檔案
if git ls-remote "$PROTOCOL_REPO" &>/dev/null 2>&1; then
    git clone --depth=1 "$PROTOCOL_REPO" "$PROTOCOL_DIR" 2>/dev/null

    # 讀取新版本號與 commit hash
    NEW_VERSION="unknown"
    NEW_COMMIT="unknown"
    if [ -f "$PROTOCOL_DIR/.asp/VERSION" ]; then
        NEW_VERSION=$(cat "$PROTOCOL_DIR/.asp/VERSION" | tr -d '[:space:]')
    fi
    NEW_COMMIT=$(git -C "$PROTOCOL_DIR" rev-parse --short HEAD 2>/dev/null || echo "unknown")

    if [ "$IS_UPGRADE" = true ]; then
        echo "🔄 升級 ASP: v${INSTALLED_VERSION} → v${NEW_VERSION} (${NEW_COMMIT})"
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

    # --- Makefile 處理（include-based，非破壞性）---
    # ASP targets 放在 .asp/Makefile.inc，專案 Makefile 只需 include
    if [ -f "$PROTOCOL_DIR/.asp/Makefile.inc" ]; then
        cp "$PROTOCOL_DIR/.asp/Makefile.inc" ./.asp/Makefile.inc
    fi

    ASP_INCLUDE_LINE='-include .asp/Makefile.inc'
    if [ ! -f "Makefile" ]; then
        # 全新安裝：使用 stub 範本
        cp "$PROTOCOL_DIR/Makefile" ./Makefile
    elif grep -q "AI-SOP-Protocol" Makefile 2>/dev/null; then
        # ASP 產生的 Makefile（舊版完整式或 stub）：替換為 stub（保留 APP_NAME）
        cp Makefile Makefile.pre-asp-upgrade
        CURRENT_APP=$(grep "^APP_NAME" Makefile | head -1 || true)
        cp "$PROTOCOL_DIR/Makefile" ./Makefile
        if [ -n "${CURRENT_APP:-}" ]; then
            SED_INPLACE "s/^APP_NAME.*/$CURRENT_APP/" Makefile
        fi
        echo "🔄 Makefile 已轉換為 include 模式（ASP targets 移至 .asp/Makefile.inc，舊版備份於 Makefile.pre-asp-upgrade）"
    elif ! grep -qF "$ASP_INCLUDE_LINE" Makefile 2>/dev/null; then
        # 非 ASP Makefile：僅追加 include 指令（不覆蓋原有內容）
        printf '\n# ASP targets（勿刪除此行）\n%s\n' "$ASP_INCLUDE_LINE" >> Makefile
        echo "✅ 已在現有 Makefile 追加 ASP include 指令（原有內容完整保留）"
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

DESIGN_VAL="disabled"
[ "${ENABLE_DESIGN,,}" = "y" ] && DESIGN_VAL="enabled"

CODING_STYLE_VAL="disabled"
[ "${ENABLE_CODING_STYLE,,}" = "y" ] && CODING_STYLE_VAL="enabled"

OPENAPI_VAL="disabled"
[ "${ENABLE_OPENAPI,,}" = "y" ] && OPENAPI_VAL="enabled"

FRONTEND_QUALITY_VAL="disabled"
[ "${ENABLE_FRONTEND_QUALITY,,}" = "y" ] && FRONTEND_QUALITY_VAL="enabled"

AUTONOMOUS_VAL="disabled"
[ "${ENABLE_AUTONOMOUS,,}" = "y" ] && AUTONOMOUS_VAL="enabled"

ORCHESTRATOR_VAL="disabled"
[ "${ENABLE_ORCHESTRATOR,,}" = "y" ] && ORCHESTRATOR_VAL="enabled"

AUTOPILOT_VAL="disabled"
[ "${ENABLE_AUTOPILOT,,}" = "y" ] && AUTOPILOT_VAL="enabled"

NEW_PROFILE="type: ${PROJECT_TYPE}
mode: ${MODE:-single}
workflow: ${WORKFLOW:-standard}
rag: ${RAG_VAL}
guardrail: ${GUARDRAIL_VAL}
hitl: ${HITL_LEVEL}
autonomous: ${AUTONOMOUS_VAL}
orchestrator: ${ORCHESTRATOR_VAL}
autopilot: ${AUTOPILOT_VAL}
design: ${DESIGN_VAL}
coding_style: ${CODING_STYLE_VAL}
openapi: ${OPENAPI_VAL}
frontend_quality: ${FRONTEND_QUALITY_VAL}
name: ${PROJECT_NAME}"

if [ -f ".ai_profile" ]; then
    echo "ℹ️  .ai_profile 已存在，保留現有設定"
    # 僅補充缺失欄位
    ADDED_FIELDS=0
    for FIELD in type mode workflow rag guardrail hitl autonomous orchestrator autopilot design coding_style openapi frontend_quality name; do
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

# 設定 Claude Code Hooks（SessionStart: 設定權限 — allow all + deny 危險指令）
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
  },
  "permissions": {
    "allow": ["Bash(*)"],
    "deny": [
      "Bash(git push *)", "Bash(git push)",
      "Bash(git rebase *)", "Bash(git rebase)",
      "Bash(docker push *)", "Bash(docker deploy *)",
      "Bash(rm -rf *)", "Bash(rm -r *)"
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

    # --- 設定 deny 規則（從 denied-commands.json 讀取）---
    DENIED_FILE=".asp/hooks/denied-commands.json"
    if [ -f "$DENIED_FILE" ] && [ -f ".claude/settings.json" ]; then
        DENY_JSON=$(cat "$DENIED_FILE")
        jq --argjson deny "$DENY_JSON" '
            .permissions.allow = ((.permissions.allow // []) + ["Bash(*)"] | unique) |
            .permissions.deny = ((.permissions.deny // []) + $deny | unique)
        ' .claude/settings.json > .claude/settings.json.tmp \
            && mv .claude/settings.json.tmp .claude/settings.json
        echo "✅ 已設定權限 — allow: Bash(*), deny: $(echo "$DENY_JSON" | jq length) 條危險指令"
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
  },
  "permissions": {
    "allow": ["Bash(*)"],
    "deny": [
      "Bash(git push *)", "Bash(git push)",
      "Bash(git rebase *)", "Bash(git rebase)",
      "Bash(docker push *)", "Bash(docker deploy *)",
      "Bash(rm -rf *)", "Bash(rm -r *)"
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

# --- 清理 allow list 中的具體危險指令 + 確保 deny 規則存在（安裝時執行一次）---
# 舊版 ASP 可能在 allow list 中有具體危險指令，需要清理
# 新版只需 Bash(*) 在 allow + deny 列表阻擋危險指令
if [ "$JQ_AVAILABLE" = true ]; then
    DANGEROUS_PATTERNS='git\s+rebase|git\s+push|docker\s+(push|deploy)|rm\s+-[a-z]*r|find\s+.*-delete'
    TOTAL_REMOVED=0
    for SETTINGS_FILE in .claude/settings.local.json .claude/settings.json; do
        [ -f "$SETTINGS_FILE" ] || continue
        FILE_TYPE=$(jq -r 'type' "$SETTINGS_FILE" 2>/dev/null || echo "invalid")
        if [ "$FILE_TYPE" != "object" ]; then
            continue
        fi
        BEFORE_COUNT=$(jq -r '[.permissions.allow // [] | .[] | select(startswith("Bash(") and . != "Bash(*)")] | length' "$SETTINGS_FILE" 2>/dev/null || echo 0)
        jq --arg pattern "$DANGEROUS_PATTERNS" '
          .permissions.allow = [
            (.permissions.allow // [])[] |
            select((startswith("Bash(") and . != "Bash(*)" and test($pattern)) | not)
          ]
        ' "$SETTINGS_FILE" > "${SETTINGS_FILE}.tmp" \
            && mv "${SETTINGS_FILE}.tmp" "$SETTINGS_FILE"
        AFTER_COUNT=$(jq -r '[.permissions.allow // [] | .[] | select(startswith("Bash(") and . != "Bash(*)")] | length' "$SETTINGS_FILE" 2>/dev/null || echo 0)
        TOTAL_REMOVED=$((TOTAL_REMOVED + BEFORE_COUNT - AFTER_COUNT))
    done
    if [ "$TOTAL_REMOVED" -gt 0 ]; then
        echo "🔒 已從 allow list 移除 ${TOTAL_REMOVED} 條舊版危險規則"
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
    echo "升級摘要 (v${INSTALLED_VERSION} → v${NEW_VERSION:-unknown} @ ${NEW_COMMIT:-unknown})："
    echo "  ✅ 已更新：.asp/profiles, .asp/templates, .asp/scripts, .asp/hooks"
    echo "  🔒 已保留：.ai_profile, docs/adr/*, docs/specs/*, docs/architecture.md"
    echo ""
else
    echo "🎉 安裝完成！（v${NEW_VERSION:-unknown} @ ${NEW_COMMIT:-unknown}）"
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
echo "💡 建議執行 make audit-health 進行專案健康檢查"
echo ""
