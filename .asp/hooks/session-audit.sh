#!/usr/bin/env bash
# ASP SessionStart Hook: session-audit.sh
# 在 clean-allow-list.sh 之後執行
#
# 功能：
#   1. Profile 驗證（A1: 7 rules）
#   2. 檔案結構掃描（A5: 11 rules）
#   3. ADR Draft 掃描 + 動態 deny（A3: 鐵則）
#   4. Tech Debt 過期掃描（A8: 7 rules）
#   5. 依賴健康檢查（A9: 5 rules）
#   6. 健康審計 baseline 檢查（A14: 7 rules）
#   7. 產生 .asp-session-briefing.json + 動態 deny patterns
#
# 此 hook 永遠 exit 0（不阻擋 session 啟動）

set -uo pipefail

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"
BRIEFING_FILE="${PROJECT_DIR}/.asp-session-briefing.json"
SETTINGS_FILE="${PROJECT_DIR}/.claude/settings.json"
PROFILE_FILE="${PROJECT_DIR}/.ai_profile"

# 需要 jq
command -v jq &>/dev/null || {
    echo "⚠️ ASP session-audit: jq 未安裝，跳過審計" >&2
    exit 0
}

# ─── 收集器 ───
BLOCKERS=()
WARNINGS=()
INFOS=()
DYNAMIC_DENY=()

# ─── 輔助函數 ───
get_field() {
    grep "^${1}:" "$PROFILE_FILE" 2>/dev/null | awk '{print $2}' | tr -d '"' | tr -d "'"
}

# ═══════════════════════════════════════════
# 1. Profile 驗證（A1: 7 rules）
# ═══════════════════════════════════════════
if [ -f "$PROFILE_FILE" ]; then
    TYPE=$(get_field "type")
    MODE=$(get_field "mode")
    HITL=$(get_field "hitl")
    AUTONOMOUS=$(get_field "autonomous")
    DESIGN=$(get_field "design")
    FRONTEND_QUALITY=$(get_field "frontend_quality")
    ORCHESTRATOR=$(get_field "orchestrator")
    AUTOPILOT=$(get_field "autopilot")

    # A1.5: type 必填
    if [ -z "$TYPE" ]; then
        BLOCKERS+=("A1.5: .ai_profile 缺少必填欄位 type")
    fi

    # A1.1: design → frontend_quality 依賴
    if [ "$DESIGN" = "enabled" ] && [ "$FRONTEND_QUALITY" != "enabled" ]; then
        WARNINGS+=("A1.3: design: enabled 但 frontend_quality 未啟用")
    fi

    # A1.4: multi-agent → task_orchestrator 依賴
    if [ "$MODE" = "multi-agent" ] && [ "$ORCHESTRATOR" != "enabled" ]; then
        WARNINGS+=("A1.4: mode: multi-agent 但 orchestrator 未啟用")
    fi

    # hitl 值（用於 deny 嚴格度）
    HITL_LEVEL="${HITL:-standard}"
else
    WARNINGS+=("A1: .ai_profile 不存在，僅套用 CLAUDE.md 鐵則")
    TYPE=""
    HITL_LEVEL="standard"
fi

# ═══════════════════════════════════════════
# 2. 檔案結構掃描（A5: 11 rules）
# ═══════════════════════════════════════════
MISSING_FILES=()
[ ! -f "$PROJECT_DIR/README.md" ]    && MISSING_FILES+=("README.md")
[ ! -f "$PROJECT_DIR/CHANGELOG.md" ] && MISSING_FILES+=("CHANGELOG.md")

# Makefile 檢查（A5.9）
if [ ! -f "$PROJECT_DIR/Makefile" ] && [ ! -f "$PROJECT_DIR/.asp/Makefile.inc" ]; then
    MISSING_FILES+=("Makefile")
fi

# Lock file 檢查（A5.3）
if [ -f "$PROJECT_DIR/package.json" ] && [ ! -f "$PROJECT_DIR/package-lock.json" ] && [ ! -f "$PROJECT_DIR/yarn.lock" ] && [ ! -f "$PROJECT_DIR/pnpm-lock.yaml" ]; then
    WARNINGS+=("A5.3: package.json 存在但無 lock file")
fi
if [ -f "$PROJECT_DIR/pyproject.toml" ] && [ ! -f "$PROJECT_DIR/poetry.lock" ] && [ ! -f "$PROJECT_DIR/uv.lock" ]; then
    WARNINGS+=("A5.3: pyproject.toml 存在但無 lock file")
fi

# .env.example 檢查（A5.4）
if [ -f "$PROJECT_DIR/.env" ] && [ ! -f "$PROJECT_DIR/.env.example" ]; then
    WARNINGS+=("A5.4: .env 存在但無 .env.example 範本")
fi

if [ ${#MISSING_FILES[@]} -gt 0 ]; then
    WARNINGS+=("A5: 缺失檔案: ${MISSING_FILES[*]}")
fi

# ═══════════════════════════════════════════
# 3. ADR Draft 掃描（A3: 鐵則）
# ═══════════════════════════════════════════
DRAFT_ADRS=()
ADR_DIR=""
for dir in "$PROJECT_DIR/docs/adr" "$PROJECT_DIR/docs/ADR" "$PROJECT_DIR/adr"; do
    [ -d "$dir" ] && ADR_DIR="$dir" && break
done

if [ -n "$ADR_DIR" ]; then
    while IFS= read -r adr_file; do
        [ -f "$adr_file" ] || continue
        if grep -qiE "^Status:\s*(Draft|draft|DRAFT)" "$adr_file" 2>/dev/null; then
            DRAFT_ADRS+=("$(basename "$adr_file")")
        fi
    done < <(find "$ADR_DIR" -name "ADR-*.md" -o -name "adr-*.md" 2>/dev/null)
fi

if [ ${#DRAFT_ADRS[@]} -gt 0 ]; then
    BLOCKERS+=("A3.1 鐵則: ADR Draft 存在 [${DRAFT_ADRS[*]}] — git commit 已被動態阻擋")
    DYNAMIC_DENY+=("Bash(git commit *)" "Bash(git commit)")
fi

# ═══════════════════════════════════════════
# 4. Tech Debt 過期掃描（A8: 7 rules）
# ═══════════════════════════════════════════
OVERDUE_COUNT=0
TODAY=$(date +%Y-%m-%d)

# 掃描 src/ 和根目錄的 tech-debt 標記
while IFS= read -r line; do
    due_date=$(echo "$line" | grep -oP 'DUE:\s*\K\d{4}-\d{2}-\d{2}' || true)
    if [ -n "$due_date" ] && [[ "$due_date" < "$TODAY" ]]; then
        OVERDUE_COUNT=$((OVERDUE_COUNT + 1))
    fi
done < <(grep -rn "tech-debt:.*HIGH.*DUE:" "$PROJECT_DIR/src/" "$PROJECT_DIR/lib/" 2>/dev/null || true)

if [ "$OVERDUE_COUNT" -gt 0 ]; then
    WARNINGS+=("A8.3: $OVERDUE_COUNT 筆 HIGH tech-debt 已逾期")
fi

# ═══════════════════════════════════════════
# 5. 依賴健康檢查（A9: 5 rules）
# ═══════════════════════════════════════════
LOOSE_DEP_COUNT=0
if [ -f "$PROJECT_DIR/package.json" ]; then
    LOOSE_DEP_COUNT=$(grep -cE '"(\*|latest)"' "$PROJECT_DIR/package.json" 2>/dev/null || echo 0)
fi
if [ "$LOOSE_DEP_COUNT" -gt 0 ]; then
    WARNINGS+=("A9.2: package.json 有 $LOOSE_DEP_COUNT 筆鬆散版本（* 或 latest）")
fi

# ═══════════════════════════════════════════
# 6. 健康審計 baseline 檢查（A14: 7 rules）
# ═══════════════════════════════════════════
BASELINE_STALE=false
BASELINE_EXISTS=false
if [ -f "$PROJECT_DIR/.asp-audit-baseline.json" ]; then
    BASELINE_EXISTS=true
    last_audit=$(jq -r '.last_audit // ""' "$PROJECT_DIR/.asp-audit-baseline.json" 2>/dev/null)
    if [ -n "$last_audit" ]; then
        # 計算天數差（相容 GNU date）
        last_ts=$(date -d "$last_audit" +%s 2>/dev/null || echo 0)
        now_ts=$(date +%s)
        if [ "$last_ts" -gt 0 ]; then
            days_old=$(( (now_ts - last_ts) / 86400 ))
            if [ "$days_old" -gt 7 ]; then
                BASELINE_STALE=true
                INFOS+=("A14.2: 健康審計 baseline 已 ${days_old} 天未更新（建議執行 make audit-health）")
            fi
        fi
    fi
else
    INFOS+=("A14.1: .asp-audit-baseline.json 不存在（建議執行 make audit-health）")
fi

# ═══════════════════════════════════════════
# 7. 測試結果檢查（A4.7: commit 前需 test）
# ═══════════════════════════════════════════
TEST_RESULT_EXISTS=false
if [ -f "$PROJECT_DIR/.asp-test-result.json" ]; then
    TEST_RESULT_EXISTS=true
    test_passed=$(jq -r '.passed // false' "$PROJECT_DIR/.asp-test-result.json" 2>/dev/null)
    if [ "$test_passed" != "true" ]; then
        INFOS+=("A4.7: 上次測試未通過，commit 前需重新執行 make test")
    fi
fi

# ═══════════════════════════════════════════
# 8. 產生 briefing JSON
# ═══════════════════════════════════════════
{
    # 用 heredoc 構建 JSON 避免複雜的 jq 參數傳遞
    cat <<JSONEOF
{
  "version": "1.0",
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "hitl_level": "$HITL_LEVEL",
  "profile": {
    "exists": $([ -f "$PROFILE_FILE" ] && echo true || echo false),
    "type": "${TYPE:-null}"
  },
  "blockers": $(if [ ${#BLOCKERS[@]} -gt 0 ]; then printf '%s\n' "${BLOCKERS[@]}" | jq -R . | jq -s .; else echo '[]'; fi),
  "warnings": $(if [ ${#WARNINGS[@]} -gt 0 ]; then printf '%s\n' "${WARNINGS[@]}" | jq -R . | jq -s .; else echo '[]'; fi),
  "infos": $(if [ ${#INFOS[@]} -gt 0 ]; then printf '%s\n' "${INFOS[@]}" | jq -R . | jq -s .; else echo '[]'; fi),
  "draft_adrs": $(if [ ${#DRAFT_ADRS[@]} -gt 0 ]; then printf '%s\n' "${DRAFT_ADRS[@]}" | jq -R . | jq -s .; else echo '[]'; fi),
  "missing_files": $(if [ ${#MISSING_FILES[@]} -gt 0 ]; then printf '%s\n' "${MISSING_FILES[@]}" | jq -R . | jq -s .; else echo '[]'; fi),
  "overdue_tech_debt_count": $OVERDUE_COUNT,
  "loose_dependency_count": $LOOSE_DEP_COUNT,
  "baseline_stale": $BASELINE_STALE,
  "baseline_exists": $BASELINE_EXISTS,
  "test_result_exists": $TEST_RESULT_EXISTS,
  "dynamic_deny": $(if [ ${#DYNAMIC_DENY[@]} -gt 0 ]; then printf '%s\n' "${DYNAMIC_DENY[@]}" | jq -R . | jq -s .; else echo '[]'; fi)
}
JSONEOF
} > "$BRIEFING_FILE" 2>/dev/null || true

# ═══════════════════════════════════════════
# 9. 注入動態 deny 到 settings.json
# ═══════════════════════════════════════════
if [ ${#DYNAMIC_DENY[@]} -gt 0 ] && [ -f "$SETTINGS_FILE" ]; then
    # 備份
    cp "$SETTINGS_FILE" "${SETTINGS_FILE}.bak" 2>/dev/null || true

    for pattern in "${DYNAMIC_DENY[@]}"; do
        jq --arg p "$pattern" '
            .permissions.deny = ((.permissions.deny // []) + [$p] | unique)
        ' "$SETTINGS_FILE" > "${SETTINGS_FILE}.tmp" 2>/dev/null \
            && mv "${SETTINGS_FILE}.tmp" "$SETTINGS_FILE"
    done
fi

# ═══════════════════════════════════════════
# 10. 輸出摘要（SessionStart hook stdout 會被 AI 讀取）
# ═══════════════════════════════════════════
echo ""
echo "## ASP Session Audit"

if [ ${#BLOCKERS[@]} -gt 0 ]; then
    echo "### BLOCKERS"
    for b in "${BLOCKERS[@]}"; do echo "- $b"; done
fi

if [ ${#WARNINGS[@]} -gt 0 ]; then
    echo "### WARNINGS"
    for w in "${WARNINGS[@]}"; do echo "- $w"; done
fi

if [ ${#INFOS[@]} -gt 0 ]; then
    echo "### INFO"
    for i in "${INFOS[@]}"; do echo "- $i"; done
fi

if [ ${#BLOCKERS[@]} -eq 0 ] && [ ${#WARNINGS[@]} -eq 0 ]; then
    echo "All clear."
fi

echo "---"
echo "Briefing: .asp-session-briefing.json | Dynamic deny: ${#DYNAMIC_DENY[@]} patterns"
echo ""

# 永遠成功（不阻擋 session）
exit 0
