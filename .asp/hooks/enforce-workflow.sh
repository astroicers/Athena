#!/usr/bin/env bash
# ASP Hook: enforce-workflow.sh
# PreToolUse (Edit|Write) — 工作流斷點，依 HITL 等級 deny 攔截檔案修改
#
# 對應規則：
#   - vibe_coding.md「HITL 等級」與「無條件暫停」
#   - system_dev.md「標準開發流程」ADR→設計→測試→實作
#   - global_core.md「連帶修復」

set -euo pipefail

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

[ -z "$FILE_PATH" ] && exit 0

# --- 讀取 HITL 等級 ---
HITL="standard"
PROFILE="${CLAUDE_PROJECT_DIR:-.}/.ai_profile"
if [ -f "$PROFILE" ]; then
    HITL_LINE=$(grep -E '^\s*hitl:\s*' "$PROFILE" 2>/dev/null || true)
    if [ -n "$HITL_LINE" ]; then
        HITL=$(echo "$HITL_LINE" | sed 's/.*hitl:\s*//' | tr -d '[:space:]')
    fi
fi

# 標準化 HITL 值
case "$HITL" in
    minimal|standard|strict) ;;
    *) HITL="standard" ;;
esac

# --- 分類檔案 ---
# 取檔名（不含路徑前綴）— 用於 basename 比對
BASENAME=$(basename "$FILE_PATH")

classify_file() {
    local fp="$1"

    # 敏感模組（unconditional）
    if echo "$fp" | grep -qiE '/(auth|crypto|security|secrets)/'; then
        echo "sensitive"
        return
    fi

    # 共用介面（unconditional）
    if echo "$fp" | grep -qiE '(\.proto|\.graphql|openapi\.|swagger\.)$'; then
        echo "interface"
        return
    fi
    if echo "$fp" | grep -qiE '/(interfaces|contracts)/'; then
        echo "interface"
        return
    fi

    # 文件/設定
    if echo "$fp" | grep -qiE '(^|/)docs/'; then
        echo "doc"
        return
    fi
    if echo "$fp" | grep -qiE '\.(md|txt|rst)$'; then
        echo "doc"
        return
    fi
    if echo "$fp" | grep -qiE '(^|/)(LICENSE|\.ai_profile|\.gitignore)'; then
        echo "doc"
        return
    fi
    if echo "$fp" | grep -qiE '(^|/)\.asp/'; then
        echo "doc"
        return
    fi

    # 測試檔案
    if echo "$fp" | grep -qiE '(^|/)(tests?|__tests__|spec)/'; then
        echo "test"
        return
    fi
    if echo "$fp" | grep -qiE '(_test\.|\.test\.|_spec\.|\.spec\.)[^/]*$'; then
        echo "test"
        return
    fi

    # 其餘皆為原始碼
    echo "source"
}

# --- SPEC 存在性檢查 ---
check_spec_status() {
    local project_dir="${CLAUDE_PROJECT_DIR:-.}"
    local spec_dir="$project_dir/docs/specs"
    local spec_count=0
    local recent_spec=false
    local threshold=3600  # 60 分鐘

    # 計算 SPEC 檔案數量
    if [ -d "$spec_dir" ]; then
        spec_count=$(find "$spec_dir" -maxdepth 1 -name 'SPEC-*.md' 2>/dev/null | wc -l | tr -d ' ')
    fi

    # 檢查是否有近期修改的 SPEC
    if [ "$spec_count" -gt 0 ]; then
        local now
        now=$(date +%s)
        for f in "$spec_dir"/SPEC-*.md; do
            local mtime
            mtime=$(stat -c %Y "$f" 2>/dev/null || stat -f %m "$f" 2>/dev/null || echo 0)
            if [ $((now - mtime)) -le $threshold ]; then
                recent_spec=true
                break
            fi
        done
    fi

    # 回傳狀態：none | stale | recent
    if [ "$spec_count" -eq 0 ]; then
        echo "none"
    elif [ "$recent_spec" = true ]; then
        echo "recent"
    else
        echo "stale"
    fi
}

CATEGORY=$(classify_file "$FILE_PATH")

# --- 偵測刪除操作 ---
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty')
IS_DELETION=false

if [ "$TOOL_NAME" = "Edit" ]; then
    NEW_STRING=$(echo "$INPUT" | jq -r '.tool_input.new_string // "non-empty"')
    if [ -z "$NEW_STRING" ] || [ "$NEW_STRING" = "" ]; then
        IS_DELETION=true
    fi
fi

# 刪除操作覆蓋分類（unconditional）
if [ "$IS_DELETION" = true ]; then
    CATEGORY="deletion"
fi

# --- 決策矩陣 ---
# 雙保險攔截：JSON deny + exit 2（Belt-and-Suspenders）
# - JSON deny: 部分環境/版本有效（GitHub #3514: deny 有時不阻止執行）
# - exit 2 + stderr: 官方文件記載的阻止方式，對 Edit/Write 工具也有效
# - "ask" 在 VSCode Extension 中被靜默忽略（GitHub #13339），故使用 "deny"
deny_with_reason() {
    local reason="$1"
    # 方式 1: JSON deny（stdout）
    jq -n --arg reason "$reason" '{
        hookSpecificOutput: {
            hookEventName: "PreToolUse",
            permissionDecision: "deny",
            permissionDecisionReason: $reason
        }
    }'
    # 方式 2: stderr + exit 2（fallback，最可靠的阻止方式）
    echo "$reason" >&2
    exit 2
}

SHORT_PATH=$(echo "$FILE_PATH" | sed "s|.*/\(.*/.*/.*\)|\1|")

case "$CATEGORY" in
    sensitive)
        deny_with_reason "🔒 ASP 斷點：修改 auth/crypto/security 模組 ($SHORT_PATH)，任何 HITL 等級都需確認（vibe_coding.md）"
        ;;
    interface)
        deny_with_reason "🔒 ASP 斷點：修改共用介面/API 合約 ($SHORT_PATH)，任何 HITL 等級都需確認（vibe_coding.md）"
        ;;
    deletion)
        deny_with_reason "⚠️ ASP 斷點：偵測到刪除現有代碼 ($SHORT_PATH)，任何 HITL 等級都需確認（vibe_coding.md）"
        ;;
    source)
        if [ "$HITL" = "standard" ] || [ "$HITL" = "strict" ]; then
            SPEC_STATUS=$(check_spec_status)
            case "$SPEC_STATUS" in
                none)
                    deny_with_reason "$(cat <<MSG
⚠️ ASP SPEC 缺失警告 (hitl: $HITL)：修改原始碼 ($SHORT_PATH)

docs/specs/ 中找不到任何 SPEC 文件。
ASP 標準流程：SPEC → 設計 → 測試 → 實作（system_dev.md）

若為非 trivial 變更，請先執行：
  make spec-new TITLE="功能名稱"

若為 trivial 修改（單行/typo/配置），可覆蓋此警告並說明豁免理由。
MSG
)"
                    ;;
                stale)
                    deny_with_reason "$(cat <<MSG
📋 ASP 工作流檢查點 (hitl: $HITL)：修改原始碼 ($SHORT_PATH)

docs/specs/ 有 SPEC 文件，但近 1 小時內無 SPEC 建立/更新。
若此為新任務，建議先建立或更新對應 SPEC。
  make spec-new TITLE="功能名稱"  |  make spec-list

trivial 修改可覆蓋。（system_dev.md）
MSG
)"
                    ;;
                recent)
                    deny_with_reason "📋 ASP 工作流檢查點 (hitl: $HITL)：修改原始碼 ($SHORT_PATH)。偵測到近期 SPEC 活動，請確認已按流程進行。（system_dev.md）"
                    ;;
            esac
        fi
        ;;
    test)
        if [ "$HITL" = "strict" ]; then
            deny_with_reason "📋 ASP 工作流檢查點 (hitl: strict)：所有檔案修改均需確認 ($SHORT_PATH)"
        fi
        ;;
    doc)
        if [ "$HITL" = "strict" ]; then
            deny_with_reason "📋 ASP 工作流檢查點 (hitl: strict)：所有檔案修改均需確認 ($SHORT_PATH)"
        fi
        ;;
esac

# 未攔截：放行
exit 0
