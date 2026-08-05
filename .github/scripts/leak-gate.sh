#!/usr/bin/env bash
# Public-safe leak gate.
#
# Fails CI if any private-core artifact leaked into the public docs. Scans the
# CONTENT surface only (README + docs + examples + ci) and deliberately NOT
# .github/ — this script itself lists the denylisted crate names as patterns.
#
# Allowed public names: athena-sdk, athena-tools, athena-core, athena-tool(.toml).
# Everything matched below must NOT appear in the published docs.
set -uo pipefail

INTERNAL_CRATES='athena-(api|capability|llm-client|config|orchestrator|orient|mcp-client|mcp-server|pentest-kb|vuln|report|types|workspace|db|embedding-client|exec|engine|redirector|scheduler|campaign|kb)\b'

PATTERNS=(
  "$INTERNAL_CRATES"                          # internal crate names
  'ADR-[0-9]'                                 # design-record numbers
  'SPEC-[a-z]'                                # spec ids
  '私有工作區'                                 # "private workspace"
  'core 私有'                                  # "core private"
  '192\.168\.'                                # lab RFC1918
  '10\.0\.[0-9]'                              # lab RFC1918
  'corp\.athena'                              # lab domain
  'krbtgt'                                    # lab principal
  '〈待'                                       # unfilled placeholder
  'sk-ant-[A-Za-z0-9]{10,}'                    # real Anthropic key body (sk-ant-... placeholder is fine)
  'AKIA[0-9A-Z]{16}'                          # AWS access key id
  '-----BEGIN [A-Z ]*PRIVATE KEY-----'        # private key block
)

# Only scan targets that exist (a missing path would make grep exit 2 = error,
# which we must not confuse with "no match").
TARGETS=()
for t in README.md docs examples ci; do
  [ -e "$t" ] && TARGETS+=("$t")
done

status=0
for pat in "${PATTERNS[@]}"; do
  if hits=$(grep -RInE --binary-files=without-match "$pat" "${TARGETS[@]}" 2>/dev/null); then
    echo "::error::leak-gate matched forbidden pattern: ${pat}"
    echo "${hits}"
    status=1
  fi
done

if [ "${status}" -eq 0 ]; then
  echo "leak-gate: clean — no private-core artifacts found in public docs."
fi
exit "${status}"
