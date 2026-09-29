"""Chart specs for the surf article (texts/surf.html), read by assets/charts.js.

Reads surf/data/analysis.json (the MFWAM analysis, one record per spot and day) and the rule constants in
surf/data.json, and recomputes fig. 1 exactly as tools/surf_figures.py does: Ericeira, daily max swell, mean period
and mean wind, and the days that clear the surfable rule. The article's figure covers the 92 days from 14 June to
13 September 2026; the analysis file keeps growing, so the window is fixed here. Writes assets/surf/charts.json.

    python3 tools/charts/surf.py
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ANALYSIS = json.loads((ROOT / "surf/data/analysis.json").read_text())["spots"]
RULE = json.loads((ROOT / "surf/data.json").read_text())["surfable_rule"]
OUT = ROOT / "assets/surf/charts.json"

FIRST, LAST = "2026-06-14", "2026-09-13"
HELD = "#1f64ad"  # the accent of the static figure (assets/surf/01-ericeira-92-days.svg)
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]


def n(v: float | None, dp: int, unit: str = "") -> str:
    """Numbers as the article writes them: a real minus sign, units after a space."""
    if v is None:
        return "–"
    return ("−" if v < 0 else "") + f"{abs(v):.{dp}f}" + unit


def offshore(r: dict) -> bool:
    return r.get("wind_dir") is not None and abs(((r["wind_dir"] - RULE["offshore_deg"][0] + 180) % 360) - 180) <= RULE["offshore_deg"][1]


def surf(r: dict) -> bool:
    """The surfable rule, as in tools/surf_figures.py."""
    if r["swell_max"] is None or r["period_mean"] is None:
        return False
    wind_ok = r.get("wind_mean") is None or r["wind_mean"] <= RULE["wind_max_kmh"] or offshore(r)
    return RULE["swell_max_m"][0] <= r["swell_max"] <= RULE["swell_max_m"][1] and r["period_mean"] >= RULE["period_min_s"] and wind_ok


def fails(r: dict) -> list[str]:
    out = []
    lo, hi = RULE["swell_max_m"]
    if not lo <= r["swell_max"] <= hi:
        out.append("height")
    if r["period_mean"] < RULE["period_min_s"]:
        out.append("period")
    if r.get("wind_mean") is not None and r["wind_mean"] > RULE["wind_max_kmh"] and not offshore(r):
        out.append("wind")
    return out


def day_label(d: date) -> str:
    return f"{d.day} {MONTHS[d.month - 1]}"


days = [(date.fromisoformat(k), r) for k, r in sorted(ANALYSIS["ericeira"].items()) if FIRST <= k <= LAST]
assert len(days) == 92, len(days)
ok = [surf(r) for _, r in days]
assert sum(ok) == 5, sum(ok)
assert sum(1 for _, r in days if r["period_mean"] >= RULE["period_min_s"]) == 11


def tip(i: int) -> str:
    d, r = days[i]
    verdict = "clears the rule" if ok[i] else "fails on " + ", ".join(fails(r))
    wind = "wind " + n(r["wind_mean"], 1, " km/h") if r["wind_mean"] is not None else "no wind data"
    return f"{day_label(d)}\nmax swell {n(r['swell_max'], 2, ' m')}\nmean period {n(r['period_mean'], 2, ' s')}\n{wind}\n{verdict}"


def runs(key: str) -> list[list[list[float]]]:
    """Unbroken stretches of a series; a missing value is a gap, as matplotlib draws it."""
    out, cur = [], []
    for i, (_, r) in enumerate(days):
        if r[key] is None:
            if cur:
                out.append(cur)
            cur = []
        else:
            cur.append([i, r[key]])
    if cur:
        out.append(cur)
    return out


def lines(key: str) -> list[dict]:
    return [{"type": "line", "name": key, "c": "ink", "w": 1.5, "notip": True, "pts": pts} for pts in runs(key)]


def hover(key: str) -> dict:
    """Hover targets on every day of a panel, in day order for the arrow keys; drawn under the line so they do not show."""
    return {"type": "dots", "r": 0.01, "o": 0, "c": "ink",
            "pts": [{"x": i, "y": r[key], "tip": tip(i)} for i, (_, r) in enumerate(days) if r[key] is not None]}


def quiet_x(key: str, below: float, width: int = 9) -> int:
    """First day from which the series stays under a threshold for a few days: room for the rule's label."""
    return next(i for i in range(2, N - width) if all(days[j][1][key] is not None and days[j][1][key] < below for j in range(i - 1, i + width)))


N = len(days)
ticks = [i for i, (d, _) in enumerate(days) if d.day == 1]  # month starts; the caption gives the first and last day
x = {"kind": "linear", "domain": [-0.5, N - 0.5], "ticks": ticks, "tickLabels": {str(i): f"{days[i][0].day} {MONTHS[days[i][0].month - 1][:3]}" for i in ticks},
     }  # period and wind ticks carry a leading space so all three panels share one left margin
lo, hi = RULE["swell_max_m"]
charts = {
    "ericeira-92-days": {
        "alt": "Three panels over 92 days at Ericeira: daily maximum swell height with the 1.0–2.5 m band and five surfable days marked; mean period with the 8-second line; wind with the 25 km/h line.",
        "layout": "rows",
        "legend": [{"label": "clears the rule", "c": HELD, "shape": "o"},
                   {"label": f"height band {n(lo, 1)}–{n(hi, 1)} m", "c": HELD, "shape": "box", "o": 0.25},
                   {"label": "rule threshold", "c": "grey", "dash": "dot"}],
        "panels": [
            {"title": "daily max swell · m", "h": 230, "x": x, "y": {"kind": "linear", "domain": [0, 3], "ticks": [0, 1, 2, 3], "tickfmt": {"dp": 1}},
             "marks": [{"type": "area", "name": "band", "c": HELD, "o": 0.1, "notip": True, "pts": [[-0.5, lo, hi], [N - 0.5, lo, hi]]},
                       hover("swell_max"),
                       *lines("swell_max"),
                       {"type": "dots", "c": HELD, "r": 4.5,
                        "pts": [{"x": i, "y": days[i][1]["swell_max"], "tip": tip(i)} for i in range(N) if ok[i]]}]},
            {"title": "mean period · s", "h": 130, "x": x, "y": {"kind": "linear", "domain": [3, 11], "ticks": [4, 6, 8, 10], "tickfmt": {"dp": 0, "pre": " "}},
             "marks": [hover("period_mean"), *lines("period_mean"),
                       {"type": "rule", "axis": "y", "v": RULE["period_min_s"], "c": "grey", "dash": "dot", "w": 1.2},
                       {"type": "text", "x": quiet_x("period_mean", RULE["period_min_s"] - 0.8), "y": RULE["period_min_s"] + 0.35,
                        "s": f"{n(RULE['period_min_s'], 0)} s", "c": "grey"}]},
            {"title": "wind · km/h", "h": 130, "x": x, "y": {"kind": "linear", "domain": [0, 30], "ticks": [0, 10, 20, 30], "tickfmt": {"dp": 0, "pre": " "}},
             "marks": [hover("wind_mean"), *lines("wind_mean"),
                       {"type": "rule", "axis": "y", "v": RULE["wind_max_kmh"], "c": "grey", "dash": "dot", "w": 1.2,
                        "label": f"{n(RULE['wind_max_kmh'], 0)} km/h", "anchor": "start"}]},
        ],
        "table": {"cols": ["day", "max swell (m)", "mean period (s)", "wind (km/h)", "rule"],
                  "rows": [[day_label(d), n(r["swell_max"], 2), n(r["period_mean"], 2), n(r["wind_mean"], 1),
                            "clears" if ok[i] else "fails: " + ", ".join(fails(r))] for i, (d, r) in enumerate(days)]},
        "data": ["../surf/data/analysis.json", "../surf/data.json"],
    }
}

OUT.write_text(json.dumps(charts, ensure_ascii=False, indent=1) + "\n")
print(f"wrote {OUT.relative_to(ROOT)}: {', '.join(charts)}")
