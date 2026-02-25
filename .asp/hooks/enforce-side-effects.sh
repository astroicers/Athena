#!/usr/bin/env bash
# ASP Hook: enforce-side-effects.sh
# PreToolUse (Bash) — 攔截危險指令，deny 阻止執行並告知原因
#
# 對應規則：
#   - CLAUDE.md 鐵則「副作用防護」
#   - global_core.md「副作用防護」清單
#   - system_dev.md「部署前檢查清單」
#
# 已知限制：
#   - 無法攔截 bash -c "..." / eval "..." / $(...) 等間接執行
#   - Shell 註解中的指令名稱可能誤觸發（低頻）

set -euo pipefail

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')

[ -z "$COMMAND" ] && exit 0

# 雙保險攔截：JSON deny + exit 2（Belt-and-Suspenders）
# - JSON deny: 部分環境/版本有效（GitHub #3514: deny 有時不阻止執行）
# - exit 2 + stderr: 官方文件記載的阻止方式，對 Bash 工具最可靠
# - "ask" 在 VSCode Extension 中被靜默忽略（GitHub #13339），故使用 "deny"
deny() {
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

# --- 部署指令（含檢查清單）---
if echo "$COMMAND" | grep -qiE '(^|\s|&&|\|)(make\s+deploy|docker[[:space:]-]compose\s+up)(\s|$|;)'; then
    deny "$(cat <<'MSG'
🔒 ASP 副作用防護：部署操作需確認

部署前檢查清單（system_dev.md）：
  □ 環境變數完整（對照 .env.example）
  □ 所有測試通過（make test）
  □ ADR 已標記 Accepted
  □ architecture.md 與當前代碼一致
  □ Dockerfile 無明顯優化缺失
MSG
)"
fi

# --- 版本控制副作用（merge/rebase）---
# git push 不由 hook 攔截，改由 Claude Code 內建權限系統處理
# 原因：hook "ask" 在 VSCode 中無效（#13339），"deny" 會截斷對話
# 內建權限系統的 GUI 確認框在 VSCode 中可正常運作
if echo "$COMMAND" | grep -qiE '(^|\s|&&|\|)git\s+(merge|rebase)(\s|$|;)'; then
    deny "🔒 ASP 副作用防護：git 操作（merge/rebase）需確認才能執行（global_core.md）"
fi

# --- 版本發布 ---
if echo "$COMMAND" | grep -qiE '(^|\s|&&|\|)(git\s+tag|npm\s+(publish|version)|yarn\s+publish)(\s|$|;)'; then
    deny "🔒 ASP 副作用防護：版本發布操作（tag/publish）需確認（global_core.md）"
fi

# --- K8s / Helm ---
if echo "$COMMAND" | grep -qiE '(^|\s|&&|\|)(helm\s+upgrade|kubectl\s+(apply|delete))(\s|$|;)'; then
    deny "🔒 ASP 副作用防護：Kubernetes 操作（helm/kubectl）需確認（global_core.md）"
fi

# --- Docker 推送/部署 ---
if echo "$COMMAND" | grep -qiE '(^|\s|&&|\|)docker\s+(push|deploy)(\s|$|;)'; then
    deny "🔒 ASP 副作用防護：Docker 推送/部署操作需確認（global_core.md）"
fi

# --- 破壞性刪除（rm -rf, rm -fr, rm -r, find -delete）---
if echo "$COMMAND" | grep -qiE '(^|\s|&&|\|)rm\s+-[a-z]*r' || echo "$COMMAND" | grep -qiE '(^|\s|&&|\|)find\s+.*-delete'; then
    deny "🔒 ASP 副作用防護：破壞性刪除操作（rm -rf / find -delete）需確認（global_core.md）"
fi

# --- 安全指令：放行 ---
exit 0
