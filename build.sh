#!/usr/bin/env bash
# Deploy-only: turns the committed tree into the served one, in place, on the throwaway CI checkout.
# The stamps (?v=<sha> on every page, the author's name in titles, each article's JSON-LD, feed, sitemap, changelog)
# never belong in a commit, so this refuses to run in a working tree unless told to (./build.sh --in-place).
# ?v=<sha> keeps the edge cache (Cloudflare) from serving a stale sheet. Portable sed: macOS and Ubuntu.
set -euo pipefail
cd "$(dirname "$0")"
if [ -z "${CI:-}" ] && [ "${1:-}" != "--in-place" ]; then
  echo "build.sh stamps every page in place for the deploy; run it in a throwaway copy, or pass --in-place" >&2
  exit 1
fi
# the editorial standard is a gate, not a document: a page that breaks a hard rule stops the deploy
python3 tools/site/check_standard.py
v=$(git rev-parse --short HEAD 2>/dev/null || date +%s)
for f in $(find . -name '*.html' -not -path './node_modules/*' -not -path './.venv/*' -not -path './tools/*' -not -path './.git/*'); do
  sed -E "s#(href=\"[./]*(style|text|a24)\.css)(\?v=[^\"]*)?\"#\1?v=$v\"#g" "$f" > "$f.tmp" && mv "$f.tmp" "$f"
done
python3 tools/site/titles.py
python3 tools/site/paper_figures.py
python3 tools/site/changelog.py
python3 tools/site/sitemap.py
python3 tools/site/feed.py
echo "stamped ?v=$v"
