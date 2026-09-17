"""Run the golden questions against the live Ask API and write ask/eval.json for the page.

    python ask/eval.py [https://api.bsandova.com]

Scores: answered correctly (expect substring present, or declined when DECLINE), protocol flags from the
trace (numbers without a tool call, unverified quotes), tokens and cost per question. Nothing is typed.
"""

from __future__ import annotations

import json
import sys
import time
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent
API = sys.argv[1] if len(sys.argv) > 1 else "https://api.bsandova.com"


def ask(q: str) -> dict:
    req = urllib.request.Request(f"{API}/ask", data=json.dumps({"question": q}).encode(), headers={"content-type": "application/json", "Origin": "https://bsandova.com"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)


def main() -> None:
    golden = json.loads((ROOT / "golden.json").read_text())["questions"]
    rows = []
    for g in golden:
        try:
            out = ask(g["q"])
        except Exception as e:  # noqa: BLE001
            rows.append({**g, "answer": "", "error": str(e), "ok": False}); print("ERR", g["q"][:50], e); continue
        ans = out.get("answer", ""); tr = out.get("trace", {})
        declined = bool(tr.get("declined"))
        ok = declined if g["expect"] == "DECLINE" else (g["expect"].lower() in ans.lower().replace(" ", "").replace(" ", "") or g["expect"].lower() in ans.lower()) and not declined
        rows.append({**g, "answer": ans, "ok": ok, "declined": declined, "tools": [t["name"] for t in tr.get("tools", [])],
                     "input_tokens": tr.get("input_tokens"), "output_tokens": tr.get("output_tokens"), "cost_usd": tr.get("cost_usd"), "ms": tr.get("ms"),
                     "protocol": tr.get("protocol"), "quotes": tr.get("quotes"), "model": tr.get("model_used")})
        print("OK " if ok else "MISS", g["kind"][:6].ljust(6), g["q"][:60], "→", ans[:80].replace("\n", " "))
        time.sleep(1.0)
    n = len(rows); good = sum(r["ok"] for r in rows)
    by_kind = {}
    for r in rows:
        k = by_kind.setdefault(r["kind"], {"n": 0, "ok": 0}); k["n"] += 1; k["ok"] += int(r["ok"])
    viol = sum(1 for r in rows if (r.get("protocol") or {}).get("numbers_without_tool") or (r.get("protocol") or {}).get("unverified_quote"))
    summary = {"date": date.today().isoformat(), "api": API, "n": n, "correct": good, "by_kind": by_kind, "protocol_violations": viol,
               "cost_usd": round(sum(r.get("cost_usd") or 0 for r in rows), 4), "median_ms": sorted(r.get("ms") or 0 for r in rows)[n // 2],
               "model": next((r.get("model") for r in rows if r.get("model")), None)}
    (ROOT / "eval.json").write_text(json.dumps({"summary": summary, "rows": rows}, indent=1, ensure_ascii=False) + "\n")
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
