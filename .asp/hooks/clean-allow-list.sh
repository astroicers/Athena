#!/usr/bin/env bash
# ASP SessionStart Hook: clean-allow-list.sh
# 每次 session 啟動時，清理 allow list 中的危險指令
# 確保 Claude Code 內建權限系統能對危險操作彈出確認框
#
# 清理對象（Bash allow 規則）：
#   - git rebase（改寫歷史）
#   - git push（推送到遠端）
#   - docker push / docker deploy（推送/部署）
#   - rm -r* / find -delete（破壞性刪除）
#
# 不清理：
#   - Read / WebFetch / Edit / Write 等非 Bash 規則
#   - 不含危險指令的 Bash 規則（如 echo, git status 等）

set -euo pipefail

command -v jq &>/dev/null || exit 0

# 危險模式：匹配這些 pattern 的 Bash(...) allow 規則會被移除
DANGEROUS_PATTERNS='git\s+rebase|git\s+push|docker\s+(push|deploy)|rm\s+-[a-z]*r|find\s+.*-delete'

# 同時處理 settings.local.json 和 settings.json
SETTINGS_FILES=(
  "${CLAUDE_PROJECT_DIR:-.}/.claude/settings.local.json"
  "${CLAUDE_PROJECT_DIR:-.}/.claude/settings.json"
)

TOTAL_REMOVED=0

for SETTINGS_FILE in "${SETTINGS_FILES[@]}"; do
  [ -f "$SETTINGS_FILE" ] || continue

  # 跳過非 object 的 JSON 檔案（避免損壞檔案導致 jq 錯誤）
  FILE_TYPE=$(jq -r 'type' "$SETTINGS_FILE" 2>/dev/null || echo "invalid")
  [ "$FILE_TYPE" = "object" ] || continue

  BEFORE=$(jq -r '[.permissions.allow // [] | .[] | select(startswith("Bash("))] | length' "$SETTINGS_FILE" 2>/dev/null || echo 0)

  jq --arg pattern "$DANGEROUS_PATTERNS" '
    .permissions.allow = [
      (.permissions.allow // [])[] |
      select(
        (startswith("Bash(") and test($pattern)) | not
      )
    ]
  ' "$SETTINGS_FILE" > "${SETTINGS_FILE}.tmp" \
      && mv "${SETTINGS_FILE}.tmp" "$SETTINGS_FILE"

  AFTER=$(jq -r '[.permissions.allow // [] | .[] | select(startswith("Bash("))] | length' "$SETTINGS_FILE" 2>/dev/null || echo 0)

  REMOVED=$((BEFORE - AFTER))
  TOTAL_REMOVED=$((TOTAL_REMOVED + REMOVED))
done

if [ "$TOTAL_REMOVED" -gt 0 ]; then
    echo "🔒 ASP: 已從 allow list 移除 ${TOTAL_REMOVED} 條危險規則（git rebase/push, docker push, rm -r 等）" >&2
fi

exit 0
