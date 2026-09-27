#!/usr/bin/env bash
# Stamp asset links with the current git short sha so no cache (GitHub Pages, Cloudflare edge) serves a stale sheet.
# Portable sed: runs on macOS and in the deploy workflow on Ubuntu.
set -euo pipefail
cd "$(dirname "$0")"
v=$(git rev-parse --short HEAD 2>/dev/null || date +%s)
for f in $(find . -name '*.html' -not -path './variants/*' -not -path './node_modules/*' -not -path './.venv/*' -not -path './tools/*' -not -path './.git/*'); do
  sed -E "s#(href=\"[./]*(style|text|a24)\.css)(\?v=[^\"]*)?\"#\1?v=$v\"#g" "$f" > "$f.tmp" && mv "$f.tmp" "$f"
done
python3 tools/changelog.py
echo "stamped ?v=$v"
