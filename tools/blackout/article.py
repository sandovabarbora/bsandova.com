"""The blackout case study: figures, map and the article, every number from the results, screen and post-hoc files.

Reads docs/research/blackout-{results,screen,posthoc}.json and the PID timetable's stop positions (tools/site/tram_geo.py),
writes assets/blackout/ (charts.json, map.json, 01-service.svg, 02-delay.svg, 03-restart.svg, 04-map.svg, results.json,
posthoc.json) and texts/blackout.html from tools/blackout/template.html.

    uv run --no-project --with numpy --with pandas --with pyarrow --with matplotlib --with duckdb \
        python tools/blackout/article.py
"""
from __future__ import annotations

import json
import math
import shutil
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "tools" / "site"))
from article_kit import GREY, HELD, LIGHT, n, render, results_reader, use_article_style  # noqa: E402
from tram_geo import offset_line, tram_stops  # noqa: E402

plt = use_article_style()
R, A = ROOT / "docs" / "research", ROOT / "assets" / "blackout"
CORAL = "#c0503f"
START = 10 * 60
MODES = {"tramvaj": ("trams", HELD), "metro": ("metro", CORAL), "autobus": ("buses", GREY)}


def clock(i: int) -> str:
    m = START + 10 * i
    return f"{m // 60:02d}:{m % 60:02d}"


def minute(s: str) -> int:
    h, m = s.split(":")
    return int(h) * 60 + int(m)


def pts(series: list, upto: int = 72) -> list:
    return [[START + 10 * i, v] for i, v in enumerate(series[:upto]) if v is not None]


TIME_AXIS = {"kind": "linear", "domain": [START, 22 * 60], "ticks": [600, 720, 840, 960, 1080, 1200, 1320],
             "tickLabels": {str(t): f"{t // 60}:00" for t in range(600, 1321, 60)},
             "tipLabels": {str(START + 10 * i): clock(i) for i in range(73)}, "label": "4 July 2025, local time"}
EVENTS = [{"type": "rule", "axis": "x", "v": 12 * 60, "c": "ink", "dash": "dot", "label": "11:59 grid collapses"},
          {"type": "rule", "axis": "x", "v": 13 * 60 + 1, "c": "grey", "dash": "dot", "label": "13:01 last substation",
           "dy": 24}]


def service_chart(res: dict) -> dict:
    marks = [*EVENTS, {"type": "rule", "axis": "y", "v": 1, "c": "light"}]
    for mode, (label, c) in MODES.items():
        marks.append({"type": "line", "pts": pts(res["curves"][mode]["R"]), "c": c, "name": label, "end": label,
                      "fmt": {"dp": 2}})
    rows = [[clock(i)] + [res["curves"][m]["R"][i] for m in MODES] for i in range(72)]
    return {"alt": "Passes per ten minutes on 4 July 2025 as a share of ordinary Fridays, for trams, metro and buses: "
                   "trams fall to about a quarter at noon and climb back over the afternoon; buses stay near one.",
            "panels": [{"h": 260, "padRight": 60, "x": TIME_AXIS,
                        "y": {"kind": "linear", "domain": [0, 1.2], "ticks": [0, 0.25, 0.5, 0.75, 1],
                              "fmt": {"dp": 2}, "label": "passes ÷ ordinary Friday"}, "marks": marks}],
            "table": {"cols": ["bin", *[MODES[m][0] for m in MODES]], "rows": rows},
            "data": ["results.json"]}


def delay_chart(res: dict, ph: dict) -> dict:
    cv = res["curves"]["tramvaj"]
    band = [[START + 10 * i, lo, hi] for i, (lo, hi) in enumerate(zip(cv["D_base_min"], cv["D_base_max"]))
            if lo is not None and hi is not None]
    off = ph["curves"]
    pct = lambda s: [None if v is None else round(100 * v, 1) for v in s]  # noqa: E731
    return {"alt": "Two panels for trams on 4 July 2025. Left: the median delay of passes, against the range of ordinary "
                   "Fridays; it swings far below and above the range after the restart. Right: the share of passes more "
                   "than five minutes off the timetable, about four in five in the early afternoon, back to the range of "
                   "ordinary Fridays only around 19:00.",
            "panels": [
                {"title": "median delay, registered", "h": 230, "x": TIME_AXIS,
                 "y": {"kind": "linear", "domain": [-600, 600], "ticks": [-600, -300, 0, 300, 600],
                       "fmt": {"dp": 0, "unit": " s", "sign": True}, "label": "seconds"},
                 "marks": [*EVENTS, {"type": "area", "pts": band, "c": "grey", "name": "ordinary Fridays", "fmt": {"dp": 0}},
                           {"type": "line", "pts": [[t, max(-600, min(600, v))] for t, v in pts(cv["D_event"])],
                            "c": HELD, "name": "4 July", "fmt": {"dp": 0, "unit": " s"}}]},
                {"title": "off by over 5 min, after the results", "h": 230, "x": TIME_AXIS,
                 "y": {"kind": "linear", "domain": [0, 100], "ticks": [0, 25, 50, 75, 100], "fmt": {"dp": 0, "unit": " %"},
                       "label": "share of passes"},
                 "marks": [*EVENTS[:1], {"type": "line", "pts": pts(pct(off["off_base_max"])), "c": "grey", "w": 1.5,
                                         "name": "highest ordinary Friday", "fmt": {"dp": 1, "unit": " %"}},
                           {"type": "line", "pts": pts(pct(off["off_event"])), "c": HELD, "name": "4 July",
                            "fmt": {"dp": 1, "unit": " %"}}]}],
            "legend": [{"label": "4 July", "c": HELD}, {"label": "ordinary Fridays", "c": "grey", "shape": "box"}],
            "table": {"cols": ["bin", "median delay, s", "ordinary low", "ordinary high", "off by >5 min, %",
                               "ordinary highest, %"],
                      "rows": [[clock(i), cv["D_event"][i], cv["D_base_min"][i], cv["D_base_max"][i],
                                pct(off["off_event"])[i], pct(off["off_base_max"])[i]] for i in range(72)]},
            "data": ["results.json", "posthoc.json"]}


def restart_chart(rows: list[dict]) -> tuple[dict, list]:
    lags = [r["after_13_01_min"] for r in rows if r["mapped"] and r["after_13_01_min"] is not None]
    edges = list(range(-40, 170, 10))
    counts = [sum(lo <= x < lo + 10 for x in lags) for lo in edges]
    lab = lambda lo: n(lo, 0, sign=True)  # noqa: E731
    bars = [{"x": lab(lo), "y0": 0, "y1": c, "tip": f"{lab(lo)} to {lab(lo + 10)} min after 13:01: {c} segments"}
            for lo, c in zip(edges, counts)]
    spec = {"alt": "Tram segments that stopped, by when their first tram ran again, in minutes after the last Prague "
                   "substation came back at 13:01: most restarted within an hour after it, a few up to two and a half hours.",
            "panels": [{"h": 220, "x": {"kind": "cat", "domain": [lab(lo) for lo in edges],
                                        "label": "minutes after 13:01, ten-minute bins from"},
                        "y": {"kind": "linear", "domain": [0, max(counts) * 1.15], "fmt": {"dp": 0}, "label": "segments"},
                        "marks": [{"type": "vbar", "c": HELD, "rows": bars}]}],
            "table": {"cols": ["minutes after 13:01, from", "segments"], "rows": [[lo, c] for lo, c in zip(edges, counts)]},
            "data": ["results.json"]}
    return spec, lags


def map_spec(rows: list[dict], res: dict) -> tuple[dict, int]:
    xy = {r.name: (r.lon, r.lat) for r in tram_stops().itertuples()}
    stopped = {(r["from"], r["to"]): r for r in rows}
    segs = set(stopped)
    # every tram segment seen on the baseline days, so the map shows what kept running as well
    base = json.loads((R / "blackout-screen.json").read_text())["baseline_days"]
    import pandas as pd
    p = pd.read_parquet(ROOT / "tools/data/blackout/passes.parquet", columns=["mode", "seg_from", "seg_to", "date"])
    allsegs = set(map(tuple, p[(p["mode"] == "tramvaj") & p.date.isin(base)][["seg_from", "seg_to"]].drop_duplicates()
                      .itertuples(index=False)))
    feats = []
    for a, b in sorted(allsegs | segs):
        if a not in xy or b not in xy:
            continue
        r = stopped.get((a, b))
        lag = r["after_13_01_min"] if r and r["mapped"] else None
        feats.append({"id": f"{a} → {b}", "name": f"{a} → {b}",
                      "sub": (f"stopped · first tram again {r['restart']}" if r and r["restart"] else
                              "stopped · no tram again before 22:00" if r else "kept running or too few trams to tell"),
                      "l": [offset_line(xy[a], xy[b])],
                      "v": {"stopped": 1 if r else 0, "lag": None if lag is None else round(lag)}})
    spec = {"held": CORAL, "base": "../assets/praha-base.json", "fit": "features", "features": feats,
            "views": [{"key": "stopped", "label": "stopped at 12:10–12:30", "scale": "seq", "domain": [0, 1],
                       "cats": [{"v": 0, "label": "trams ran, or too few to tell"}, {"v": 1, "label": "no tram in 12:10–12:30"}],
                       "note": "segments with at least 3 trams in 20 minutes on ordinary Fridays"},
                      {"key": "lag", "label": "restart after 13:01", "fmt": {"dp": 0, "unit": " min", "sign": True},
                       "scale": "seq", "domain": [-30, 150], "note": "minutes from 13:01 to the first tram"}],
            "hint": "hover, tap or use the arrow keys for a segment; each direction is drawn on its right",
            "data": ["results.json"]}
    return spec, len(feats)


def static_lines(chart: dict, path: Path, ylabel: str, ylim: tuple) -> None:
    f, ax = plt.subplots(figsize=(7.2, 3.0))
    for m in chart["panels"][0]["marks"]:
        if m["type"] == "line":
            ax.plot([p[0] for p in m["pts"]], [p[1] for p in m["pts"]], color=m["c"] if m["c"].startswith("#") else GREY,
                    lw=1.6, label=m["name"])
        elif m["type"] == "area":
            ax.fill_between([p[0] for p in m["pts"]], [p[1] for p in m["pts"]], [p[2] for p in m["pts"]], color=LIGHT,
                            alpha=0.5, lw=0, label=m["name"])
    for v in (12 * 60, 13 * 60 + 1):
        ax.axvline(v, color=GREY, lw=0.8, ls=":")
    ax.set_xticks(range(600, 1321, 120), [f"{t // 60}:00" for t in range(600, 1321, 120)])
    ax.set_ylim(*ylim)
    ax.set_ylabel(ylabel)
    ax.legend(frameon=False, fontsize=8)
    f.tight_layout()
    f.savefig(path)
    plt.close(f)


def static_map(spec: dict, path: Path) -> None:
    from matplotlib.collections import LineCollection
    k = math.cos(math.radians(50.08))
    f, ax = plt.subplots(figsize=(7.2, 5.6))
    for stop, c, w in ((0, "#d9d9d4", 1.0), (1, CORAL, 1.8)):
        fs = [x for x in spec["features"] if x["v"]["stopped"] == stop]
        ax.add_collection(LineCollection([[(x * k, y) for x, y in ft["l"][0]] for ft in fs], colors=c, linewidths=w,
                                         capstyle="round", rasterized=True))
    ax.autoscale()
    ax.set_aspect("equal")
    ax.axis("off")
    f.tight_layout()
    f.savefig(path, dpi=220)
    plt.close(f)


def main() -> None:
    j = results_reader("blackout")
    res, scr, ph = j("results"), j("screen"), j("posthoc")
    A.mkdir(parents=True, exist_ok=True)
    shutil.copy(R / "blackout-results.json", A / "results.json")
    shutil.copy(R / "blackout-posthoc.json", A / "posthoc.json")

    charts = {"service": service_chart(res), "delay": delay_chart(res, ph)}
    charts["restart"], lags = restart_chart(res["Q4_restart"])
    (A / "charts.json").write_text(json.dumps(charts, ensure_ascii=False, separators=(",", ":")))
    static_lines(charts["service"], A / "01-service.svg", "passes ÷ ordinary Friday", (0, 1.2))
    d = charts["delay"]
    static_lines({"panels": [d["panels"][1]]}, A / "02-delay.svg", "% of tram passes off by more than 5 min", (0, 100))
    f, ax = plt.subplots(figsize=(7.2, 2.6))
    ax.hist(lags, bins=range(-40, 170, 10), color=HELD)
    ax.axvline(0, color=GREY, lw=0.8, ls=":")
    ax.set_xlabel("minutes after 13:01")
    ax.set_ylabel("segments")
    f.tight_layout()
    f.savefig(A / "03-restart.svg")
    plt.close(f)
    spec, drawn = map_spec(res["Q4_restart"], res)
    (A / "map.json").write_text(json.dumps(spec, ensure_ascii=False, separators=(",", ":")))
    static_map(spec, A / "04-map.svg")

    t, q1 = res["modes"]["tramvaj"], res["Q1_stopped"]
    plac = lambda key: max(v["share"] for v in q1["placebo"].values())  # noqa: E731
    metro = res["checks"]["metro_control"]
    worst = max(abs(v["miss_min"]) for v in metro.values() if v["miss_min"] is not None)
    early = ph["early_13_30_to_14_10"]
    off = ph["off_schedule_by_hour"]
    rows = res["Q4_restart"]
    never = sum(r["restart"] is None for r in rows)
    pre = res["curves"]["metro"]["R"][10]
    v = {
        "stopped_pct": n(100 * q1["event"]["share"], 0), "stopped_segs": n(q1["event"]["segments_stopped"]),
        "q1_segs": n(q1["event"]["segments"]), "q1_low": n(q1["event"]["low_frequency_excluded"]),
        "stopped_placebo_pct": n(100 * plac("share"), 1),
        "q1_wide_pct": n(100 * res["checks"]["Q1_12_10_to_12_40"]["event"]["share"], 0),
        "t50": t["event"]["T50"], "t90": t["event"]["T90"], "td": t["event"]["TD"],
        "td_mean": res["checks"]["mean_delay"]["event"]["TD"],
        "t90_085": res["checks"]["threshold_0_85"]["event"]["T90"],
        "t90_dep": res["checks"]["departures"]["T90"],
        "bus_t90": res["modes"]["autobus"]["event"]["T90"], "bus_td": res["modes"]["autobus"]["event"]["TD"],
        "metro_t50": res["modes"]["metro"]["event"]["T50"], "metro_td": res["modes"]["metro"]["event"]["TD"],
        "metro_pre": n(pre, 2),
        "metro_a": metro["991"]["estimated"], "metro_b": metro["992"]["estimated"], "metro_c": metro["993"]["estimated"],
        "metro_worst": n(worst, 0),
        "restart_n": n(len(lags)), "restart_all": n(len(rows)), "restart_never": n(never),
        "lag_median": n(statistics.median(lags), 0), "lag_min": n(min(lags), 0, sign=True), "lag_max": n(max(lags), 0),
        "within_hour": n(100 * sum(x <= 60 for x in lags) / len(lags), 0),
        "early_pct": n(100 * early["share_more_than_2_min_early"], 0), "early_n": n(early["passes"]),
        "early_q1": n(-early["delay_quartiles_s"][0] / 60, 0), "early_most_h": n(-early["most_early_s"] / 3600, 0),
        "late_1h": n(scr["event_passes_delay_over_1h"]["tramvaj"]),
        "off_1310": n(100 * off["13:10"]["event"], 0), "off_1410": n(100 * off["14:10"]["event"], 0),
        "off_1610": n(100 * off["16:10"]["event"], 0), "off_1810": n(100 * off["18:10"]["event"], 0),
        "off_1910": n(100 * off["19:10"]["event"], 0), "off_base_1410": n(100 * off["14:10"]["baseline_max"], 0),
        "off_base_max": n(100 * max(x["baseline_max"] for x in off.values()), 0),
        "baseline": ", ".join(d[-2:].lstrip("0") for d in scr["baseline_days"]),
        "map_drawn": n(drawn),
    }
    html = render((HERE / "template.html").read_text(encoding="utf-8"), v)
    (ROOT / "texts" / "blackout.html").write_text(html, encoding="utf-8")
    print(json.dumps(v, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
