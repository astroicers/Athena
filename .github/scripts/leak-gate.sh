#!/usr/bin/env bash
# Public-safe leak gate.
#
# Fails CI if any private-core artifact leaks into the published tree. This
# script is the SCANNING SKELETON ONLY: it deliberately contains no
# project-specific denylist terms. The sensitive denylist (private crate
# names, internal hostnames, design-record ids, lab principals, …) lives
# OUTSIDE this public repo and is injected at run time — so the gate can no
# longer leak the very terms it is meant to guard.
#
# Denylist source (first that resolves wins):
#   1. $LEAK_GATE_DENYLIST_B64   base64 of a newline-separated ERE pattern list
#   2. $LEAK_GATE_DENYLIST_FILE  path to a newline-separated ERE pattern list
#   3. ./.leak-gate-denylist     gitignored local file (must never be committed)
# In CI, populate #1 from a repository secret — never from tracked source.
# Blank lines and lines beginning with '#' in the list are ignored.
#
# On a match the offending PATTERN is never echoed (that would re-leak the
# denylist into public CI logs); only a redacted index plus the matched
# file:line is printed. A private-term match is by definition already public
# content, so surfacing its location is safe and actionable.
set -uo pipefail

# --- baseline patterns: generic secret shapes, safe to keep public ----------
# These reveal nothing about the private core; they are the same shapes every
# public secret scanner ships. Kept inline so the gate stays useful even when
# no external denylist is configured.
BASELINE_PATTERNS=(
  'sk-ant-[A-Za-z0-9]{10,}'             # real Anthropic key body (sk-ant-... placeholder stays fine)
  'AKIA[0-9A-Z]{16}'                    # AWS access key id
  '-----BEGIN [A-Z ]*PRIVATE KEY-----'  # PEM private key block
)

# --- private denylist: injected, never stored in this public repo -----------
load_denylist() {
  if [ -n "${LEAK_GATE_DENYLIST_B64:-}" ]; then
    printf '%s' "${LEAK_GATE_DENYLIST_B64}" | base64 -d 2>/dev/null
  elif [ -n "${LEAK_GATE_DENYLIST_FILE:-}" ] && [ -f "${LEAK_GATE_DENYLIST_FILE}" ]; then
    cat "${LEAK_GATE_DENYLIST_FILE}"
  elif [ -f .leak-gate-denylist ]; then
    cat .leak-gate-denylist
  fi
}

PRIVATE_PATTERNS=()
while IFS= read -r line; do
  [ -z "${line}" ] && continue
  case "${line}" in \#*) continue ;; esac
  PRIVATE_PATTERNS+=("${line}")
done < <(load_denylist)

if [ "${#PRIVATE_PATTERNS[@]}" -eq 0 ]; then
  echo "::warning::leak-gate: no private denylist configured (set LEAK_GATE_DENYLIST_B64 from a repo secret); running baseline secret shapes only."
fi

PATTERNS=("${BASELINE_PATTERNS[@]}" "${PRIVATE_PATTERNS[@]}")

# --- scan targets: content surface AND CI config (no self-exemption) --------
# .github is scanned too, so a denylisted term pasted into a workflow, script,
# or issue template can no longer hide from the gate.
TARGETS=()
for t in README.md docs examples ci .github; do
  [ -e "$t" ] && TARGETS+=("$t")
done

if [ "${#TARGETS[@]}" -eq 0 ]; then
  echo "leak-gate: no scan targets present — nothing to check."
  exit 0
fi

status=0
idx=0
for pat in "${PATTERNS[@]}"; do
  idx=$((idx + 1))
  # Never scan the injected denylist file itself; never echo the pattern.
  if hits=$(grep -RInE --binary-files=without-match \
              --exclude='.leak-gate-denylist' \
              "$pat" "${TARGETS[@]}" 2>/dev/null); then
    echo "::error::leak-gate matched forbidden pattern #${idx} (pattern redacted)"
    echo "${hits}"
    status=1
  fi
done

if [ "${status}" -eq 0 ]; then
  echo "leak-gate: clean — no private-core artifacts found in public tree."
fi
exit "${status}"
