"""Chart specs for the sonification article (texts/delayed.html), read by assets/charts.js.

Reads tools/data/sonification_days.json (the player's embedded aggregates, the same file tools/figures/delayed_figures.py
draws assets/delayed/01-five-days.svg from) and recomputes that figure exactly: the event-weighted mean of bus, tram
and trolleybus delay per 5-minute window, a five-window moving average (numpy's convolve 'same', zeros at the edges),
and the chorus where the smoothed value exceeds 68 % of the day's maximum.

Writes assets/delayed/five-days.json (the derived surface series behind the figure, linked as the chart's data) and
assets/delayed/charts.json.

    python3 tools/charts/delayed.py
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
A = ROOT / "assets/delayed"
D = json.loads((ROOT / "tools/data/sonification_days.json").read_text())
NB = " "
HELD = "#b3202c"  # the article's held colour (tools/site/paper_figures.py), the chorus fill in the static figure
SURF = ["autobus", "tramvaj", "trolejbus"]
ORDER = ["easter", "summer", "school", "typical", "meltdown"]


def n(v: float, dp: int = 0, unit: str = "") -> str:
    """Numbers as the article writes them: a space between thousands, a real minus sign."""
    s = f"{abs(v):,.{dp}f}".replace(",", NB)
    return ("−" if round(v, dp) < 0 else "") + s + unit


def clock(i: int) -> str:
    return f"{i * 5 // 60:02d}:{i * 5 % 60:02d}"


def series(day: dict) -> tuple[list[float], list[float], list[float]]:
    """As delayed_figures.series: event-weighted surface delay, its 5-window smoothing, and the event count."""
    m = day["modes"]
    cnt = [float(sum(m[s]["n"][i] for s in SURF)) for i in range(288)]
    w = [float(sum(m[s]["n"][i] * m[s]["delay"][i] for s in SURF)) for i in range(288)]
    d = [w[i] / max(cnt[i], 1) if cnt[i] > 0 else 0.0 for i in range(288)]
    sm = [sum(d[j] for j in range(i - 2, i + 3) if 0 <= j < 288) / 5 for i in range(288)]
    return d, sm, cnt


days = sorted(D["days"], key=lambda d: next((k for k, o in enumerate(ORDER) if o in d["id"]), 9))
panels, rows, dump = [], [], []
for k, day in enumerate(days):
    d, sm, cnt = series(day)
    thr = 0.68 * max(sm)
    chorus = [v > thr for v in sm]
    mean = sum(a * max(c, 1) for a, c in zip(d, cnt)) / sum(max(c, 1) for c in cnt)
    lo, hi = min(0.0, min(d)), max(d)
    step = next(s for s in (25, 50, 100, 200, 250, 500) if hi / s <= 4)
    top = step * -(-(hi * 1.04) // step)
    bottom = -step * -(-(-lo) // step) if lo < 0 else 0
    t = [i / 12 for i in range(288)]
    marks = []
    # chorus: filled from 0 up to the delay over each contiguous run of windows, as fill_between(where=chorus) does
    i = 0
    while i < 288:
        if chorus[i]:
            j = i
            while j + 1 < 288 and chorus[j + 1]:
                j += 1
            marks.append({"type": "area", "name": "chorus", "c": HELD, "o": 0.35, "notip": True,
                          "pts": [[round(t[q], 4), 0, round(d[q], 1)] for q in range(i, j + 1)]})
            i = j + 1
        else:
            i += 1
    marks.append({"type": "rule", "axis": "y", "v": round(thr, 1), "c": "grey", "dash": "dot"})
    marks.append({"type": "line", "name": "surface delay", "c": "ink", "w": 1.2, "notip": True,
                  "pts": [[round(x, 4), round(v, 1)] for x, v in zip(t, d)]})
    # one hover target per window, drawn as an invisible diamond so the tooltip can give the clock time
    marks.append({"type": "dots", "c": "transparent", "shape": "d",
                  "pts": [{"x": round(t[q], 4), "y": round(d[q], 1),
                           "tip": f"{day['label']} · {clock(q)}–{clock(q + 1) if q < 287 else '24:00'}\n"
                                  f"surface delay {n(d[q], 0, ' s')}\nsmoothed {n(sm[q], 0, ' s')}"
                                  f"{' · chorus' if chorus[q] else ''} (threshold {n(thr, 0, ' s')})\n{n(cnt[q])} surface stop events"}
                          for q in range(288)]})
    last = k == len(days) - 1
    panels.append({"h": 150 + (24 if last else 0),
                   "title": f"{day['label']} · {day['disc']} · {n(day['total'])} events",
                   "x": {"kind": "linear", "domain": [0, 24], "ticks": list(range(0, 25, 3)), "fmt": {"dp": 0},
                         **({"label": "hour of day"} if last else {})},
                   "y": {"kind": "linear", "domain": [bottom, top], "ticks": list(range(int(bottom), int(top) + 1, step)),
                         "label": "s late" if k == 0 else None, "tickfmt": {"dp": 0}},
                   "marks": marks})
    rows.append([day["label"], day["disc"], n(day["total"]), n(mean, 0, " s"), n(thr, 0, " s"), n(sum(chorus) * 5, 0, " min")])
    dump.append({"id": day["id"], "label": day["label"], "disc": day["disc"], "total": day["total"],
                 "mean_surface_delay_s": round(mean, 1), "chorus_threshold_s": round(thr, 1), "chorus_minutes": sum(chorus) * 5,
                 "windows": [{"start": clock(q), "surface_events": int(cnt[q]), "surface_delay_s": round(d[q], 1),
                              "smoothed_s": round(sm[q], 1), "chorus": chorus[q]} for q in range(288)]})
# the static figure shares its x axis: pad shorter y tick labels with invisible spaces so every plot starts at the same x
wide = max(len(str(t)) for p in panels for t in p["y"]["ticks"])
for p in panels:
    if p["y"]["label"] is None:
        del p["y"]["label"]
    pad = wide - max(len(str(t)) for t in p["y"]["ticks"])
    if pad:
        p["y"]["tickfmt"]["pre"] = NB * pad

charts = {"five-days": {
    "alt": "Five stacked line charts of surface transit delay over 24 hours for the five days on the record, with chorus regions shaded where the smoothed delay exceeds 68 percent of the day's maximum.",
    "layout": "rows",
    "legend": [{"label": "surface delay, event-weighted (bus, tram, trolleybus)", "c": "ink"},
               {"label": "chorus", "c": HELD, "shape": "box", "o": 0.35},
               {"label": "68 % of the day's maximum smoothed delay", "c": "grey", "dash": "dot"}],
    "panels": panels,
    "table": {"cols": ["day", "date", "stop events", "mean surface delay", "chorus threshold", "chorus"], "rows": rows},
    "data": ["../assets/delayed/five-days.json"],
}}

(A / "five-days.json").write_text(json.dumps({"source": "tools/data/sonification_days.json (the player's embedded aggregates, derived from Golemio / PID open data)",
                                               "method": "event-weighted mean of bus, tram and trolleybus arrival delay per 5-minute window; five-window moving average; chorus where the smoothed value exceeds 68 % of the day's maximum",
                                               "days": dump}, ensure_ascii=False, separators=(",", ":")))
(A / "charts.json").write_text(json.dumps(charts, ensure_ascii=False, separators=(",", ":")))
for r in rows:
    print(r)
