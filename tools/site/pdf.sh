#!/bin/zsh
# Print the Prague, measured pages to assets/pdf/<slug>.pdf with headless Chrome, from a local server of the repo
# root, so the interactive charts and maps are drawn before printing (print styles in a24.css).
#   tools/site/pdf.sh            (needs Google Chrome; starts and stops its own server on a free port)
set -e
cd "$(dirname "$0")/../.."
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
PORT=$(python3 -c 'import socket;s=socket.socket();s.bind(("",0));print(s.getsockname()[1])')
python3 -m http.server $PORT >/dev/null 2>&1 & SRV=$!
trap 'kill $SRV 2>/dev/null' EXIT
for i in {1..50}; do  # about 15 s; a server that never answers must not hang the script
  curl -s -m 2 -o /dev/null "http://localhost:$PORT/texts/prague-measured.html" && break
  [ $i -eq 50 ] && { echo "the local server on port $PORT did not answer" >&2; exit 1; }
  sleep 0.3
done
for slug in prague-measured prague-council prague-rings prague-districts prague-housing prague-parking; do
  "$CHROME" --headless=new --disable-gpu --no-pdf-header-footer --virtual-time-budget=12000 \
    --print-to-pdf="assets/pdf/$slug.pdf" "http://localhost:$PORT/texts/$slug.html" 2>/dev/null
  size=$(wc -c < "assets/pdf/$slug.pdf")
  [ "$size" -gt 200000 ] || { echo "assets/pdf/$slug.pdf is only $size bytes: the page did not print" >&2; exit 1; }
  echo "assets/pdf/$slug.pdf $(du -h assets/pdf/$slug.pdf | cut -f1)"
done
