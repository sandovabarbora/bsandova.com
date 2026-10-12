"""Engine v2 states per day for the sonification article (texts/delayed.html), from the player's own code.

Loads the player's index.html at a pinned commit in headless Chromium and calls its planV2 for each of the five days
at the default scale (one 5-minute window per beat, so one bar covers 20 minutes of data). Nothing is reimplemented:
the states are the ones the player plays. Writes assets/delayed/v2-states.json and prints the summary the article
quotes (minutes per density and groove state, the highest harmonic rung, the first lifted and extreme bars, and the
peak of the running z).

    uv run --with playwright python tools/charts/delayed_v2.py
"""
from __future__ import annotations

import json
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

COMMIT = "41d61c0"  # sandovabarbora/delayed-all-the-time, PR #2 (engine v2)
URL = f"https://raw.githubusercontent.com/sandovabarbora/delayed-all-the-time/{COMMIT}/index.html"
OUT = Path(__file__).resolve().parents[2] / "assets/delayed/v2-states.json"

JS = """() => DATA.days.map((raw, i) => {
  loadDay(i);
  const P = planV2(cur.v2, cur, 4), BAR = 20, t = b => binTime(b * 4);
  const runs = a => { const r = []; a.forEach((v, b) => { if (v && (b === 0 || !a[b - 1])) r.push([b, b + 1]);
    else if (v) r[r.length - 1][1] = b + 1; }); return r; };
  const count = (arr, k) => [...arr].filter(x => x === k).length * BAR;
  const first = (arr, k) => { const b = [...arr].findIndex(x => x >= k); return b < 0 ? null : t(b); };
  let zmax = -1e9, zbin = 0;
  cur.v2.zr.forEach((z, j) => { if (z > zmax) { zmax = z; zbin = j; } });
  return {
    id: raw.id, label: raw.label, type: cur.v2.type, key: cur.keyName,
    density_min: [0, 1, 2, 3].map(k => count(P.dens, k)),
    groove_min: [0, 1, 2].map(k => count(P.groove, k)),
    top_rung: Math.max(...P.lev),
    first_lifted: first(P.dens, 2), first_extreme: first(P.dens, 3), first_dominant: first(P.lev, 2),
    z_peak: Math.round(zmax * 100) / 100, z_peak_at: binTime(zbin),
    lifted_or_extreme: runs([...P.dens].map(x => x >= 2)).map(([a, b]) => t(a) + "–" + (b * 4 >= 288 ? "24:00" : t(b))),
  };
})"""


def main() -> None:
    html = urllib.request.urlopen(URL, timeout=30).read().decode("utf-8")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_content(html, wait_until="load")
        days = page.evaluate(JS)
        browser.close()
    OUT.write_text(json.dumps({"source": URL, "bar_minutes": 20, "days": days}, ensure_ascii=False, indent=1) + "\n")
    names = ["sparse", "full", "lifted", "extreme"], ["straight", "swung", "half-time"]
    for d in days:
        dens = ", ".join(f"{n} {m} min" for n, m in zip(names[0], d["density_min"]))
        grv = ", ".join(f"{n} {m} min" for n, m in zip(names[1], d["groove_min"]))
        print(f"{d['label']} ({d['type']}, {d['key']}): {dens}; {grv}; top rung {d['top_rung']}; "
              f"lifted {d['first_lifted']}, extreme {d['first_extreme']}, dominant {d['first_dominant']}; "
              f"peak z {d['z_peak']} at {d['z_peak_at']}; lifted or extreme {', '.join(d['lifted_or_extreme'])}")


if __name__ == "__main__":
    main()
