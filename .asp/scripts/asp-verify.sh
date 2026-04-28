#!/usr/bin/env bash
# asp-verify.sh — 獨立驗證腳本
# 可由 skill、subagent 或 Makefile 調用
# 執行：test + lint + credential scan + grep scan
# 輸出：JSON verdict

set -uo pipefail

PROJECT_DIR="${1:-.}"
VERDICT="PASS"
ISSUES=()

echo "🔍 ASP Verify — 獨立驗證"
echo "========================="

# ──── 1. Test ────
echo ""
echo "── 1. 測試 ──"
if make -C "$PROJECT_DIR" test 2>&1; then
    echo "  ✅ 測試通過"
else
    VERDICT="FAIL"
    ISSUES+=("測試失敗")
    echo "  🔴 測試失敗"
fi

# ──── 2. Lint ────
echo ""
echo "── 2. Lint ──"
if make -C "$PROJECT_DIR" lint 2>&1; then
    echo "  ✅ Lint 通過"
elif ! make -C "$PROJECT_DIR" -n lint &>/dev/null; then
    echo "  ⏭️  無 lint target，跳過"
else
    VERDICT="FAIL"
    ISSUES+=("Lint 失敗")
    echo "  🔴 Lint 失敗"
fi

# ──── 3. Credential Scan ────
echo ""
echo "── 3. 安全掃描 ──"
CRED_FOUND=0

# 掃描硬編碼密碼
CRED_HITS=$(grep -rn \
    -e 'password\s*=\s*["\x27][^"\x27]\+["\x27]' \
    -e 'api_key\s*=\s*["\x27][^"\x27]\+["\x27]' \
    -e 'secret\s*=\s*["\x27][^"\x27]\+["\x27]' \
    -e 'PRIVATE KEY' \
    --include="*.go" --include="*.ts" --include="*.js" --include="*.py" \
    --include="*.java" --include="*.rb" --include="*.rs" \
    "$PROJECT_DIR/src/" "$PROJECT_DIR/lib/" "$PROJECT_DIR/app/" 2>/dev/null | \
    grep -v '_test\.' | grep -v '.test.' | grep -v 'test_' | grep -v '.env.example' || true)

if [ -n "$CRED_HITS" ]; then
    CRED_FOUND=$(echo "$CRED_HITS" | wc -l)
    VERDICT="FAIL"
    ISSUES+=("發現 $CRED_FOUND 處疑似硬編碼密碼")
    echo "  🔴 發現 $CRED_FOUND 處疑似硬編碼密碼："
    echo "$CRED_HITS" | head -5
else
    echo "  ✅ 無硬編碼密碼"
fi

# 掃描禁止的檔案
FORBIDDEN=$(find "$PROJECT_DIR" -maxdepth 3 \
    \( -name "*.pem" -o -name "*.key" -o -name "*.p12" \) \
    ! -path "*/.git/*" ! -path "*/node_modules/*" 2>/dev/null || true)

if [ -n "$FORBIDDEN" ]; then
    VERDICT="FAIL"
    ISSUES+=("發現禁止追蹤的檔案：$(echo "$FORBIDDEN" | tr '\n' ', ')")
    echo "  🔴 發現禁止檔案："
    echo "$FORBIDDEN"
else
    echo "  ✅ 無禁止檔案"
fi

# ──── 4. Debug Statement Scan ────
echo ""
echo "── 4. Debug 語句掃描 ──"
DEBUG_HITS=$(grep -rn \
    -e 'console\.log(' \
    -e 'fmt\.Print(' \
    -e '^[[:space:]]*print(' \
    --include="*.go" --include="*.ts" --include="*.js" --include="*.py" \
    "$PROJECT_DIR/src/" "$PROJECT_DIR/lib/" "$PROJECT_DIR/app/" 2>/dev/null | \
    grep -v '_test\.' | grep -v '.test.' | grep -v 'test_' || true)

if [ -n "$DEBUG_HITS" ]; then
    DEBUG_COUNT=$(echo "$DEBUG_HITS" | wc -l)
    ISSUES+=("發現 $DEBUG_COUNT 處 debug 語句")
    echo "  ⚠️  發現 $DEBUG_COUNT 處 debug 語句（非阻擋，但建議移除）"
else
    echo "  ✅ 無 debug 語句"
fi

# ──── 輸出 verdict ────
echo ""
echo "========================="
if [ "$VERDICT" = "PASS" ]; then
    echo "✅ VERDICT: PASS"
else
    echo "🔴 VERDICT: FAIL"
    echo ""
    echo "Issues:"
    for issue in "${ISSUES[@]}"; do
        echo "  - $issue"
    done
fi

# 寫入 JSON（如果有 jq）
if command -v jq &>/dev/null; then
    jq -n \
        --arg verdict "$VERDICT" \
        --arg timestamp "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
        --argjson issue_count "${#ISSUES[@]}" \
        '{
            verdict: $verdict,
            timestamp: $timestamp,
            issue_count: $issue_count
        }' > "$PROJECT_DIR/.asp-verify-result.json" 2>/dev/null || true
fi

[ "$VERDICT" = "PASS" ] && exit 0 || exit 1
