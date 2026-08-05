#!/usr/bin/env bash
# Fail CI if any RELATIVE markdown link points to a file that does not exist.
# External links (http/https/mailto) and pure anchors (#...) are skipped — only
# in-repo document integrity is enforced here.
set -uo pipefail

{
  while IFS= read -r f; do
    dir=$(dirname "$f")
    while IFS= read -r link; do
      case "$link" in
        http://*|https://*|mailto:*|\#*|"") continue ;;
      esac
      target="${link%%#*}"                 # strip #anchor
      [ -z "$target" ] && continue
      [ -e "$dir/$target" ] || echo "BROKEN: $f -> $link"
    done < <(grep -oE '\]\([^)]+\)' "$f" | sed -E 's/^\]\(//; s/\)$//')
  done < <(find . -name '*.md' -not -path './.git/*')
} > /tmp/broken-links

if [ -s /tmp/broken-links ]; then
  echo "::error::broken internal markdown links found:"
  cat /tmp/broken-links
  exit 1
fi
echo "check-links: all internal markdown links resolve."
