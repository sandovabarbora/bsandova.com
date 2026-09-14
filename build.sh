#!/usr/bin/env bash
# Stamp asset links with the current git short sha so GitHub Pages' 10-minute cache never serves stale CSS/JS.
set -euo pipefail
cd "$(dirname "$0")"
v=$(git rev-parse --short HEAD 2>/dev/null || date +%s)
for f in index.html texts/*.html; do
  [ -f "$f" ] || continue
  sed -i '' -E "s#(href=\"[./]*style\.css)(\?v=[^\"]*)?\"#\1?v=$v\"#g" "$f"
done
echo "stamped ?v=$v"
