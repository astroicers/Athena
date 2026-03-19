#!/usr/bin/env bash
# validate-profile.sh — 驗證 .ai_profile 的 Profile 依賴完整性
# 執行：make profile-validate 或直接 bash .asp/scripts/validate-profile.sh

set -uo pipefail

PROFILE_FILE="${1:-.ai_profile}"
ERRORS=0
WARNINGS=0
FIXED=0

echo ""
echo "🔍 ASP Profile 驗證"
echo "================================="

if [ ! -f "$PROFILE_FILE" ]; then
  echo "⚠️  找不到 $PROFILE_FILE"
  echo "   提示：複製 .asp/templates/ 中的範例 profile 開始"
  echo ""
  exit 1
fi

echo "📄 讀取: $PROFILE_FILE"
echo ""

# 讀取各欄位
get_field() {
  grep "^${1}:" "$PROFILE_FILE" 2>/dev/null | awk '{print $2}' | tr -d '"' | tr -d "'"
}

TYPE=$(get_field "type")
MODE=$(get_field "mode")
WORKFLOW=$(get_field "workflow")
HITL=$(get_field "hitl")
AUTONOMOUS=$(get_field "autonomous")
ORCHESTRATOR=$(get_field "orchestrator")
DESIGN=$(get_field "design")
FRONTEND_QUALITY=$(get_field "frontend_quality")
AUTOPILOT=$(get_field "autopilot")
RAG=$(get_field "rag")
OPENAPI=$(get_field "openapi")
CODING_STYLE=$(get_field "coding_style")

echo "── 已設定欄位 ──"
[ -n "$TYPE" ]            && echo "  type:             $TYPE"
[ -n "$MODE" ]            && echo "  mode:             $MODE"
[ -n "$WORKFLOW" ]        && echo "  workflow:         $WORKFLOW"
[ -n "$HITL" ]            && echo "  hitl:             $HITL"
[ -n "$AUTONOMOUS" ]      && echo "  autonomous:       $AUTONOMOUS"
[ -n "$ORCHESTRATOR" ]    && echo "  orchestrator:     $ORCHESTRATOR"
[ -n "$DESIGN" ]          && echo "  design:           $DESIGN"
[ -n "$FRONTEND_QUALITY" ] && echo "  frontend_quality: $FRONTEND_QUALITY"
[ -n "$AUTOPILOT" ]       && echo "  autopilot:        $AUTOPILOT"
[ -n "$RAG" ]             && echo "  rag:              $RAG"
[ -n "$OPENAPI" ]         && echo "  openapi:          $OPENAPI"
[ -n "$CODING_STYLE" ]    && echo "  coding_style:     $CODING_STYLE"
echo ""

echo "── 依賴驗證 ──"

# 規則 1：type 必填
if [ -z "$TYPE" ]; then
  echo "  🔴 ERROR: 缺少必填欄位 type（system | content | architecture）"
  ERRORS=$((ERRORS + 1))
else
  echo "  ✅ type: $TYPE"
fi

# 規則 2：design: enabled → frontend_quality 必須也是 enabled
if [ "$DESIGN" = "enabled" ] && [ "$FRONTEND_QUALITY" != "enabled" ]; then
  echo "  🟡 WARNING: design: enabled 時，frontend_quality 應同時設為 enabled"
  echo "     → 自動補全建議：在 $PROFILE_FILE 加入 frontend_quality: enabled"
  WARNINGS=$((WARNINGS + 1))
  # 自動補全
  if ! grep -q "^frontend_quality:" "$PROFILE_FILE"; then
    sed -i "/^design:/a frontend_quality: enabled" "$PROFILE_FILE"
    echo "     ✅ 已自動加入 frontend_quality: enabled"
    FIXED=$((FIXED + 1))
  fi
else
  [ "$DESIGN" = "enabled" ] && echo "  ✅ design + frontend_quality: 均已啟用"
fi

# 規則 3：autopilot: enabled → autonomous + orchestrator 應為 enabled（自動載入，不強制但建議）
if [ "$AUTOPILOT" = "enabled" ]; then
  echo "  ✅ autopilot: enabled（autonomous + task_orchestrator 會自動載入）"
  if [ "$AUTONOMOUS" = "enabled" ]; then
    echo "  ✅ autonomous: enabled（明確設定，佳）"
  else
    echo "  🟢 INFO: autonomous 未明確設定，autopilot 啟動時會自動載入"
  fi
fi

# 規則 4：autonomous: enabled → vibe_coding + system_dev 依賴（提示只，無法驗證 profile 檔本身）
if [ "$AUTONOMOUS" = "enabled" ]; then
  echo "  ✅ autonomous: enabled"
  if [ "$WORKFLOW" = "vibe-coding" ]; then
    echo "  ✅ workflow: vibe-coding（與 autonomous 搭配良好）"
  else
    echo "  🟢 INFO: autonomous 模式建議同時設 workflow: vibe-coding"
  fi
fi

# 規則 5：mode: multi-agent → 提示 orchestrator 建議
if [ "$MODE" = "multi-agent" ] && [ "$ORCHESTRATOR" != "enabled" ]; then
  echo "  🟡 WARNING: mode: multi-agent 時建議設 orchestrator: enabled"
  WARNINGS=$((WARNINGS + 1))
elif [ "$MODE" = "multi-agent" ]; then
  echo "  ✅ mode: multi-agent + orchestrator: enabled"
fi

# 規則 6：rag: enabled → 檢查 RAG index 是否存在
if [ "$RAG" = "enabled" ]; then
  if [ -f ".asp/rag/index.json" ] || [ -d ".asp/rag/" ]; then
    echo "  ✅ rag: enabled（RAG 目錄存在）"
  else
    echo "  🟡 WARNING: rag: enabled 但 .asp/rag/ 不存在，執行 make rag-index 建立索引"
    WARNINGS=$((WARNINGS + 1))
  fi
fi

# 規則 7：hitl 值驗證
if [ -n "$HITL" ] && [ "$HITL" != "minimal" ] && [ "$HITL" != "standard" ] && [ "$HITL" != "strict" ]; then
  echo "  🔴 ERROR: hitl 值無效：「$HITL」（允許值：minimal | standard | strict）"
  ERRORS=$((ERRORS + 1))
fi

# 規則 8：workflow 值驗證
if [ -n "$WORKFLOW" ] && [ "$WORKFLOW" != "standard" ] && [ "$WORKFLOW" != "vibe-coding" ]; then
  echo "  🔴 ERROR: workflow 值無效：「$WORKFLOW」（允許值：standard | vibe-coding）"
  ERRORS=$((ERRORS + 1))
fi

echo ""
echo "── 載入的 Profile 清單 ──"
echo "  必載："

case "$TYPE" in
  system|architecture)
    echo "    • global_core.md"
    echo "    • system_dev.md"
    ;;
  content)
    echo "    • global_core.md"
    echo "    • content_creative.md"
    ;;
  "")
    echo "    （type 未設定，無法列出）"
    ;;
  *)
    echo "    🔴 ERROR: 未知 type 值：$TYPE"
    ERRORS=$((ERRORS + 1))
    ;;
esac

echo "  條件載入："
[ "$MODE" = "multi-agent" ]         && echo "    • multi_agent.md"
[ "$MODE" = "committee" ]           && echo "    • committee.md"
[ "$WORKFLOW" = "vibe-coding" ]     && echo "    • vibe_coding.md"
[ "$RAG" = "enabled" ]              && echo "    • rag_context.md"
[ "$DESIGN" = "enabled" ]           && echo "    • design_dev.md" && echo "    • frontend_quality.md（auto）"
[ "$CODING_STYLE" = "enabled" ]     && echo "    • coding_style.md"
[ "$OPENAPI" = "enabled" ]          && echo "    • openapi.md"
[ "$ORCHESTRATOR" = "enabled" ]     && echo "    • task_orchestrator.md"
[ "$AUTONOMOUS" = "enabled" ]       && echo "    • autonomous_dev.md" && echo "    • task_orchestrator.md（auto）"
[ "$AUTOPILOT" = "enabled" ]        && echo "    • autopilot.md" && echo "    • autonomous_dev.md（auto）" && echo "    • task_orchestrator.md（auto）"

echo ""
echo "================================="
echo "驗證結果：🔴 $ERRORS error | 🟡 $WARNINGS warning | 🔧 $FIXED auto-fixed"

if [ $ERRORS -gt 0 ]; then
  echo "❌ 請修復上述 error 後重新驗證"
  exit 1
elif [ $WARNINGS -gt 0 ]; then
  echo "⚠️  有 warning，建議處理後執行"
else
  echo "✅ 驗證通過"
fi
echo ""
