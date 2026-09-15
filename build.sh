#!/usr/bin/env bash
# Stamp asset links with the current git short sha so no cache (GitHub Pages, Cloudflare edge) serves a stale sheet.
# Portable sed: runs on macOS and in the deploy workflow on Ubuntu.
set -euo pipefail
cd "$(dirname "$0")"
v=$(git rev-parse --short HEAD 2>/dev/null || date +%s)
for f in index.html texts/*.html; do
  [ -f "$f" ] || continue
  sed -E "s#(href=\"[./]*style\.css)(\?v=[^\"]*)?\"#\1?v=$v\"#g" "$f" > "$f.tmp" && mv "$f.tmp" "$f"
done
echo "stamped ?v=$v"
