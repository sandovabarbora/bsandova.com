"""Eras Tour and prices: the event-study chart for Pop, measured part 2, added to assets/pop/taylor-swift/charts.json,
with a static fallback and the published results and series.

    uv run --with matplotlib python tools/eras/figures.py
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
R = ROOT / "docs" / "research"
A = ROOT / "assets" / "pop" / "taylor-swift"
INK, GREY = "#111111", "#666666"
# accommodation, the registered outcome, wears Taylor Swift's colour from assets/palette.json, as in the rest of her part
HELD = json.loads((ROOT / "assets" / "palette.json").read_text())["artist"]["Taylor Swift"]


def main() -> None:
    res = json.loads((R / "eras-inflation-results.json").read_text())
    pw = {k: {r["e"]: r for r in rows_} for k, rows_ in json.loads((R / "eras-inflation-pointwise.json").read_text()).items()
          if isinstance(rows_, list)}   # post-hoc pointwise intervals (9 October 2026)
    for name in ("eras-inflation-results.json", "eras-inflation-hicp.csv", "eras-inflation-pointwise.json"):
        shutil.copy(R / name, A / name.replace("eras-inflation-", "eras-"))
    charts = json.loads((A / "charts.json").read_text())
    rows, lo, hi = [], 0.0, 0.0
    for key, label, c in (("accommodation", "accommodation", HELD), ("restaurants", "restaurants and cafés", "ink")):
        for r in res[key]["event"]:
            x = r["e"] + (-0.15 if key == "accommodation" else 0.15)
            rows.append({"x": x, "lo": r["lo"], "hi": r["hi"], "mid": r["att"], "c": c,
                         "tip": f"{label}, month {r['e']:+d}: {r['att']:+.2f} points against comparison countries (uniform band {r['lo']:.2f} to {r['hi']:.2f}; "
                                f"pointwise {pw[key][r['e']]['lo']:.2f} to {pw[key][r['e']]['hi']:.2f}, post hoc)"})
            lo, hi = min(lo, r["lo"]), max(hi, r["hi"])
    charts["eras"] = {
        "alt": "Event study: the difference in year-on-year inflation in accommodation and in restaurants between host countries "
               "and countries not yet or never visited, by month from six before to six after a country's first Eras Tour show, "
               "with 95 % uniform bands; the accommodation band at month −4 excludes zero.",
        "panels": [{"h": 260, "x": {"kind": "linear", "domain": [-6.6, 6.6], "ticks": list(range(-6, 7)), "fmt": {"dp": 0},
                                    "label": "months from the first show in the country"},
                    "y": {"kind": "linear", "domain": [lo * 1.1, hi * 1.1], "fmt": {"dp": 0},
                          "label": "difference in year-on-year inflation, percentage points"},
                    "marks": [{"type": "rule", "axis": "y", "v": 0, "c": "grey"},
                              {"type": "rule", "axis": "x", "v": -0.5, "c": "grey", "dash": "dash", "label": "show month", "dy": 12},
                              {"type": "vrange", "rows": rows, "w": 2, "r": 3.5}]}],
        "legend": [{"label": "accommodation services", "c": HELD}, {"label": "restaurants, cafés", "c": "ink"}],
        "table": {"cols": ["series", "month", "difference, points", "95 % uniform band", "pointwise 95 % CI (post hoc)"],
                  "rows": [[k, r["e"], round(r["att"], 2), f"{r['lo']:.2f} to {r['hi']:.2f}",
                            f"{pw[k][r['e']]['lo']:.2f} to {pw[k][r['e']]['hi']:.2f}"]
                           for k in ("accommodation", "restaurants", "all_items") for r in res[k]["event"]]},
        "data": ["eras-results.json", "eras-hicp.csv", "eras-pointwise.json"]}
    (A / "charts.json").write_text(json.dumps(charts, ensure_ascii=False))
    f, ax = plt.subplots(figsize=(7.2, 3))
    for key, c, dx in (("accommodation", HELD, -0.15), ("restaurants", INK, 0.15)):
        for r in res[key]["event"]:
            ax.plot([r["e"] + dx] * 2, [r["lo"], r["hi"]], color=c, lw=1.4)
            ax.scatter(r["e"] + dx, r["att"], color=c, s=12, zorder=3)
    ax.axhline(0, color=GREY, lw=0.8); ax.axvline(-0.5, color=GREY, lw=0.8, ls="--")
    ax.set_xlabel("months from the first show in the country"); ax.set_ylabel("difference, percentage points")
    f.tight_layout(); f.savefig(A / "06-eras.svg"); plt.close(f)
    print("written eras chart")


if __name__ == "__main__":
    main()
