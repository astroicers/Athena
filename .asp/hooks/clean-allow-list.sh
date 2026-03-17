#!/usr/bin/env bash
# ASP SessionStart Hook: clean-allow-list.sh
# 每次 session 啟動時，確保權限設定正確：
#   1. allow: Bash(*) — 允許所有 Bash 指令
#   2. deny: 危險指令 — 從 denied-commands.json 讀取
#   3. 清理 allow list 中被使用者手動加入的危險指令（防止繞過 deny）
#
# 危險指令（deny）：
#   - git push / git rebase（推送/改寫歷史）
#   - docker push / docker deploy（推送/部署）
#   - rm -rf / rm -r（破壞性刪除）

set -euo pipefail

command -v jq &>/dev/null || exit 0

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"
DENIED_FILE="${PROJECT_DIR}/.asp/hooks/denied-commands.json"

# 同時處理 settings.local.json 和 settings.json
SETTINGS_FILES=(
  "${PROJECT_DIR}/.claude/settings.local.json"
  "${PROJECT_DIR}/.claude/settings.json"
)

# 讀取 deny 規則
if [ -f "$DENIED_FILE" ]; then
    DENY_JSON=$(cat "$DENIED_FILE")
else
    # 預設 deny 規則（fallback）
    DENY_JSON='[
        "Bash(git push *)", "Bash(git push)",
        "Bash(git rebase *)", "Bash(git rebase)",
        "Bash(docker push *)", "Bash(docker deploy *)",
        "Bash(rm -rf *)", "Bash(rm -r *)"
    ]'
fi

# 危險模式：用於清理 allow list 中的危險規則
DANGEROUS_PATTERNS='git\s+rebase|git\s+push|docker\s+(push|deploy)|rm\s+-[a-z]*r|find\s+.*-delete'

for SETTINGS_FILE in "${SETTINGS_FILES[@]}"; do
    [ -f "$SETTINGS_FILE" ] || continue

    FILE_TYPE=$(jq -r 'type' "$SETTINGS_FILE" 2>/dev/null || echo "invalid")
    [ "$FILE_TYPE" = "object" ] || continue

    # Step 1: 確保 allow 包含 Bash(*)
    # Step 2: 設定 deny 規則
    # Step 3: 清理 allow list 中的危險規則（防止手動加入繞過 deny）
    jq --argjson deny "$DENY_JSON" --arg pattern "$DANGEROUS_PATTERNS" '
        # 確保 Bash(*) 在 allow list 中
        .permissions.allow = (
            [(.permissions.allow // [])[] | select(
                (startswith("Bash(") and test($pattern)) | not
            )] + ["Bash(*)"] | unique
        ) |
        # 設定 deny 規則（合併現有 + denied-commands.json）
        .permissions.deny = ((.permissions.deny // []) + $deny | unique)
    ' "$SETTINGS_FILE" > "${SETTINGS_FILE}.tmp" \
        && mv "${SETTINGS_FILE}.tmp" "$SETTINGS_FILE"
done

echo "🔒 ASP: 權限已設定 — allow: Bash(*), deny: $(echo "$DENY_JSON" | jq length) 條危險指令" >&2

exit 0
