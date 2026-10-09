"""Are Prague's trams later in rain hours: figures and the article, every number from the result files.

Reads docs/research/rain-delays-results.json, -describe.json, -power-rerun.json, -screen.json, -screen-feed.json, -posthoc.json,
ČHMÚ hourly precipitation and tools/data/rain/segments.parquet; writes assets/rain/ (charts.json, 01-modes.svg,
02-dose.svg, 03-checks.svg, 04-map.svg, 05-rain.svg, results.json) and texts/rain-delays.html from
tools/rain/template.html.

    uv run --with matplotlib --with pandas --with pyarrow --with duckdb --with pyfixest python tools/rain/article.py
"""
from __future__ import annotations

import json
import re
from importlib import metadata
import shutil
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import duckdb  # noqa: E402
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.collections import LineCollection  # noqa: E402
from matplotlib.colors import Normalize  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import power  # noqa: E402
from estimate import DOSE, weather  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
R = ROOT / "docs" / "research"
A = ROOT / "assets" / "rain"
D = ROOT / "tools" / "data" / "rain"
HELD, INK, GREY, LIGHT = "#34507c", "#111111", "#666666", "#b5b5b0"
NB = " "
plt.rcParams.update({"font.family": "Helvetica", "font.size": 9, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": GREY, "xtick.color": GREY, "ytick.color": GREY, "svg.fonttype": "none"})
DOSE_LABEL = {"p0_1_0_5": "0.1–0.5 mm", "p0_5_2": "0.5–2 mm", "p2_5": "2–5 mm", "p5_up": "≥ 5 mm"}


def n(v: float, dp: int = 0, sign: bool = False) -> str:
    s = f"{abs(v):,.{dp}f}".replace(",", NB)
    neg = v < 0 and round(abs(v), dp) != 0
    return ("−" if neg else ("+" if sign and v > 0 else "")) + s


def ci(lo: float, hi: float, dp: int = 1) -> str:
    return f"{n(lo, dp)} to {n(hi, dp)}"


def load() -> dict:
    j = lambda name: json.loads((R / f"rain-delays-{name}.json").read_text())  # noqa: E731
    return {"res": j("results"), "desc": j("describe"), "pow": j("power-rerun"), "scr": j("screen"),
            "feed": j("screen-feed"), "post": j("posthoc")}


def range_rows(items: list[tuple[str, dict, str]]) -> list[dict]:
    return [{"y": lab, "lo": e["ci95"][0], "hi": e["ci95"][1], "mid": e["est_s"], "c": c,
             "tip": f"{lab}: {n(e['est_s'], 1, True)} s ({ci(*e['ci95'])})"} for lab, e, c in items]


def range_chart(rows: list[dict], alt: str, label: str, domain: list[float], ticks: list[float]) -> dict:
    return {"alt": alt,
            "panels": [{"h": 34 * len(rows) + 20,
                        "x": {"kind": "linear", "domain": domain, "ticks": ticks, "fmt": {"dp": 0, "sign": True},
                              "label": label},
                        "y": {"kind": "cat", "domain": [r["y"] for r in rows]},
                        "marks": [{"type": "rule", "axis": "x", "v": 0, "c": "grey"}, {"type": "range", "rows": rows}]}],
            "table": {"cols": ["estimate", "seconds", "95 % interval"],
                      "rows": [[r["y"], round(r["mid"], 2), f"{r['lo']:.2f} to {r['hi']:.2f}"] for r in rows]},
            "data": ["results.json"]}


def static_range(rows: list[dict], path: Path, label: str, xlim: tuple[float, float]) -> None:
    f, ax = plt.subplots(figsize=(7.2, 0.42 * len(rows) + 0.8))
    for i, r in enumerate(reversed(rows)):
        c = {"held": HELD, "ink": INK, "grey": GREY}[r["c"]]
        ax.plot([r["lo"], r["hi"]], [i, i], color=c, lw=2.5, solid_capstyle="round")
        ax.plot(r["mid"], i, "o", color=c, ms=6, mec="white")
    ax.axvline(0, color=GREY, lw=0.8)
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([r["y"] for r in reversed(rows)])
    ax.set_xlim(*xlim)
    ax.set_xlabel(label)
    f.tight_layout()
    f.savefig(path)
    plt.close(f)


def figures(x: dict) -> dict:
    A.mkdir(parents=True, exist_ok=True)
    for name in ("results", "describe", "power-rerun", "posthoc"):
        shutil.copy(R / f"rain-delays-{name}.json", A / f"{name}.json")
    res, desc = x["res"], x["desc"]
    c = res["checks_tram"]
    unit = "seconds of delay gained per trip-hour, rain against dry"
    t, b = res["tram"], res["bus_secondary"]
    modes = range_rows([("trams", {"est_s": t["delta_s"], "ci95": t["ci95"]}, "held"),
                        ("buses (secondary)", {"est_s": b["delta_s"], "ci95": b["ci95"]}, "ink"),
                        ("metro (control)", c["metro"]["rain"], "grey")])
    dose = range_rows([(DOSE_LABEL[k], c["dose"][k], "held") for k, _, _ in DOSE])
    checks = range_rows([
        ("registered estimate", {"est_s": t["delta_s"], "ci95": t["ci95"]}, "held"),
        ("placebo: next hour", c["placebo_lead"]["rain_next"], "ink"),
        ("post-hoc placebo", desc["placebo_posthoc"]["rain_next"], "grey"),
        ("temperature, post-hoc", x["post"]["temperature_bands_2c"], "grey"),
        ("with earlier hours", c["lags"]["rain"], "ink"),
        ("nearest station", c["nearest_station"]["rain_st"], "ink"),
        ("delay level", c["level_instead_of_gain"]["rain"], "ink"),
        ("closures kept", c["disruption_days_kept"]["rain"], "ink"),
        ("closures, literal", c["rule1_literal"]["rain"], "ink")])
    charts = {
        "modes": range_chart(modes, f"Delay gained in a rain hour against a dry hour, with 95 % intervals: trams "
                             f"{n(t['delta_s'], 1, True)} s and buses {n(b['delta_s'], 1, True)} s, both above zero; "
                             f"the metro, underground, {n(c['metro']['rain']['est_s'], 1, True)} s.",
                             unit, [-10, 20], [-10, -5, 0, 5, 10, 15, 20]),
        "dose": range_chart(dose, "Delay gained by trams in an hour by how much rain fell, against dry hours, with "
                            "95 % intervals: the estimate is larger in heavier rain.",
                            "seconds of delay gained per trip-hour, against dry hours", [-5, 60],
                            [0, 10, 20, 30, 40, 50, 60]),
        "checks": range_chart(checks, "The registered tram estimate and its checks, with 95 % intervals: the "
                              "registered placebo lies above zero (it failed); the other checks, including the "
                              "post-hoc temperature control, lie near the estimate.", unit, [-10, 20],
                              [-10, -5, 0, 5, 10, 15, 20]),
    }
    charts["modes"]["panels"][0]["marks"].append(
        {"type": "callout", "x": t["delta_s"], "y": "trams", "s": "supported", "dy": -12})
    (A / "charts.json").write_text(json.dumps(charts, ensure_ascii=False))
    static_range(modes, A / "01-modes.svg", unit, (-10, 20))
    static_range(dose, A / "02-dose.svg", "seconds of delay gained per trip-hour, against dry hours", (-5, 60))
    static_range(checks, A / "03-checks.svg", unit, (-10, 20))
    route_map(desc)
    return rain_days()


def chains(seg: pd.DataFrame) -> list[list[list[float]]]:
    """Join a route's stop-to-stop segments into polylines, end to start, so the map JSON stays small."""
    out_of: dict[tuple, list[tuple]] = {}
    for r in seg.itertuples():
        a, b = (round(r.lon0, 5), round(r.lat0, 5)), (round(r.lon1, 5), round(r.lat1, 5))
        if a != b:
            out_of.setdefault(a, []).append(b)
    lines = []
    for start in list(out_of):
        while out_of.get(start):
            line, cur = [start], start
            while out_of.get(cur):
                cur = out_of[cur].pop()
                line.append(cur)
            lines.append([list(pt) for pt in line])
    return lines


def map_json(desc: dict) -> None:
    seg = pd.read_parquet(D / "segments.parquet")
    est = {r["route"]: r for r in desc["by_route"]}
    feats = []
    for route in sorted(seg["route"].unique(), key=lambda r: (r in est, est.get(r, {}).get("est_s", 0))):
        e = est.get(route)
        if not route.isdigit() or int(route) >= 90:
            continue  # night and special lines: not in the day estimate
        feats.append({"id": route, "name": f"line {route}", "l": chains(seg[seg["route"] == route]),
                      "v": {"est": e["est_s"] if e else None, "lo": e["lo"] if e else None,
                            "hi": e["hi"] if e else None, "units": e["rain_units"] if e else None}})
    top = max(r["est_s"] for r in desc["by_route"])
    spec = {"held": HELD, "base": "../assets/praha-base.json", "features": feats,
            "views": [{"key": "est", "label": "rain estimate", "fmt": {"dp": 1, "unit": " s", "sign": True},
                       "scale": "seq", "domain": [0, round(top + 0.5)], "note": "delay gained per trip-hour, descriptive"},
                      {"key": "lo", "label": "95 % interval, low", "fmt": {"dp": 1, "unit": " s", "sign": True},
                       "scale": "seq", "domain": [0, round(top + 0.5)]},
                      {"key": "units", "label": "rain units", "fmt": {"dp": 0}, "scale": "seq"}],
            "note": f"no estimate: fewer than {desc['min_rain_units_per_route']} rain units",
            "hint": "hover, tap or use the arrow keys for a route",
            "data": ["describe.json"]}
    (A / "map.json").write_text(json.dumps(spec, ensure_ascii=False, separators=(",", ":")))


def route_map(desc: dict) -> None:
    map_json(desc)
    seg = pd.read_parquet(D / "segments.parquet")
    est = {r["route"]: r for r in desc["by_route"]}
    seg = seg[seg["route"].isin(est)]
    cmap, norm = plt.get_cmap("Blues"), Normalize(vmin=0, vmax=max(r["est_s"] for r in est.values()))
    f, ax = plt.subplots(figsize=(7.2, 5.6))
    k = 0.643  # cos(50.08°): keeps Prague's shape
    order = sorted(est, key=lambda r: est[r]["est_s"])
    for route in order:
        s = seg[seg["route"] == route].round(5).drop_duplicates()
        lines = [[(r.lon0 * k, r.lat0), (r.lon1 * k, r.lat1)] for r in s.itertuples()]
        ax.add_collection(LineCollection(lines, colors=[cmap(0.25 + 0.75 * norm(est[route]["est_s"]))], linewidths=1.6,
                                         capstyle="round", rasterized=True))
    ax.autoscale()
    ax.set_aspect("equal")
    ax.axis("off")
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    cb = f.colorbar(sm, ax=ax, fraction=0.03, pad=0.01)
    cb.set_label("seconds per trip-hour, by route (descriptive)", color=GREY)
    f.tight_layout()
    f.savefig(A / "04-map.svg", dpi=220)  # the 11 000 route segments are rasterised; labels stay text
    plt.close(f)


def rain_days() -> pd.DataFrame:
    wx = weather(power.precipitation())
    wx = wx[(wx["date"] >= power.START) & (wx["date"] <= power.END) & wx["hour"].isin(power.HOURS)]
    days = wx.groupby("date").agg(rain=("rain", "sum"), dry=("dry", "sum"))
    excluded = set(json.loads((R / "rain-delays-screen-feed.json").read_text())["rule2_dates_excluded"])
    label = lambda d: f"{d.day} {d.strftime('%b')}"  # noqa: E731
    rows = [{"x": label(d), "y1": int(r["rain"]), "c": "light" if str(d) in excluded else "held",
             "tip": f"{label(d)}: {int(r['rain'])} rain hour{'s' if r['rain'] != 1 else ''}"
                    + (" · excluded, feed gap" if str(d) in excluded else "")} for d, r in days.iterrows() if r["rain"] > 0]
    charts = json.loads((A / "charts.json").read_text())
    charts["rain"] = {
        "alt": "Rain hours per day between 05:00 and 23:59 in Prague, 15 March to 8 September 2025: most days have "
               "none; rain days are scattered, with clusters in late April, June and late July.",
        "panels": [{"h": 200, "x": {"kind": "cat", "domain": [label(d) for d in days.index]},
                    "y": {"kind": "linear", "domain": [0, int(days["rain"].max()) + 1], "fmt": {"dp": 0},
                          "label": "rain hours, 05:00–23:59"},
                    "marks": [{"type": "vbar", "rows": rows}]}],
        "table": {"cols": ["date", "rain hours", "dry hours"],
                  "rows": [[str(d), int(r["rain"]), int(r["dry"])] for d, r in days.iterrows()]},
        "data": ["results.json"]}
    (A / "charts.json").write_text(json.dumps(charts, ensure_ascii=False))
    f, ax = plt.subplots(figsize=(7.2, 2.2))
    for d, r in days.iterrows():
        ax.bar(d, r["rain"], width=0.9, color=LIGHT if str(d) in excluded else HELD)
    ax.set_ylabel("rain hours, 05:00–23:59")
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%B"))
    f.tight_layout()
    f.savefig(A / "05-rain.svg")
    plt.close(f)
    return days


def values(x: dict, days: pd.DataFrame) -> dict:
    res, desc, pw, scr, feed, post = x["res"], x["desc"], x["pow"], x["scr"], x["feed"], x["post"]
    t, b, c = res["tram"], res["bus_secondary"], res["checks_tram"]
    rm = desc["raw_means"]
    routes = desc["by_route"]
    con = duckdb.connect(str(D / "prague_transit.duckdb"), read_only=True)
    records = con.execute("SELECT count(*) FROM stop_times_history_modeling").fetchone()[0]
    v = {
        "d": n(t["delta_s"], 1), "d_lo": n(t["ci95"][0], 1), "d_hi": n(t["ci95"][1], 1),
        "d90_lo": n(t["ci90"][0], 1), "d90_hi": n(t["ci90"][1], 1), "label": t["label"], "se": n(t["se_s"], 1),
        "bd": n(b["delta_s"], 1), "bd_lo": n(b["ci95"][0], 1), "bd_hi": n(b["ci95"][1], 1), "blabel": b["label"],
        "n_units": n(t["n_units"]), "b_units": n(b["n_units"]), "dates": n(t["dates"]), "rain_dates": n(t["rain_dates"]),
        "rain_units": n(t["rain_units"]), "records": n(records),
        "rain_hours": n(pw["rain_hours"]), "dry_hours": n(pw["dry_hours"]),
        "sig_e": n(pw["sigma_e_s"]), "sig_c": n(pw["sigma_c_s"]), "mde": n(pw["mde_s"], 1), "pse": n(pw["se_s"], 1),
        "t_rain": n(rm["tram"]["rain"]["mean_s"], 1), "t_dry": n(rm["tram"]["dry"]["mean_s"], 1),
        "b_rain": n(rm["bus"]["rain"]["mean_s"], 1), "b_dry": n(rm["bus"]["dry"]["mean_s"], 1),
        "m_rain": n(rm["metro"]["rain"]["mean_s"], 1), "m_dry": n(rm["metro"]["dry"]["mean_s"], 1),
        "t_pct": n(100 * t["delta_s"] / rm["tram"]["dry"]["mean_s"]),
        "screen_spans": n(len(scr["spans"])), "cov_pages": n(scr["coverage"]["of_which_with_archived_page"]),
        "cov_listed": n(scr["coverage"]["closures_listed_unique"]), "snapshots": n(scr["coverage"]["list_snapshots"]),
        "excl_tram": n(scr["excluded_line_days"]["tram"]), "excl_tram_lit": n(scr["excluded_line_days_literal"]["tram"]),
        "gap_dates": n(len(feed["rule2_dates_excluded"])),
        "thin_pct": n(100 * feed["rule3_units"]["tramvaj"]["thin_trip_hours"] / feed["rule3_units"]["tramvaj"]["trip_hours"], 1),
        "n_routes": n(len(routes)), "routes_pos": n(sum(r["est_s"] > 0 for r in routes)),
        "routes_sig": n(sum(r["lo"] > 0 for r in routes)), "min_rain_units": n(desc["min_rain_units_per_route"]),
        "pp_n": n(desc["placebo_posthoc"]["next_rain_units"]),
        "rain_days_window": n(int((days["rain"] > 0).sum())), "max_rain_day": str(days["rain"].idxmax().strftime("%-d %B")),
        "max_rain_hours": n(int(days["rain"].max())),
        "pl_pct": n(100 * c["placebo_lead"]["rain_next"]["est_s"] / t["delta_s"]),
        "temp_rain": n(post["mean_temperature_c"]["rain_hours"], 1), "temp_dry": n(post["mean_temperature_c"]["dry_hours"], 1),
    }
    lo_r, hi_r = min(routes, key=lambda r: r["est_s"]), max(routes, key=lambda r: r["est_s"])
    v.update({"r_lo": lo_r["route"], "r_lo_est": n(lo_r["est_s"], 1), "r_hi": hi_r["route"], "r_hi_est": n(hi_r["est_s"], 1)})

    def put(key: str, e: dict) -> None:
        v[key], v[key + "_lo"], v[key + "_hi"] = n(e["est_s"], 1), n(e["ci95"][0], 1), n(e["ci95"][1], 1)

    for key, e in (("pl", c["placebo_lead"]["rain_next"]), ("pp", desc["placebo_posthoc"]["rain_next"]),
                   ("l0", c["lags"]["rain"]), ("l1", c["lags"]["rain_l1"]), ("l2", c["lags"]["rain_l2"]),
                   ("ns", c["nearest_station"]["rain_st"]), ("lv", c["level_instead_of_gain"]["rain"]),
                   ("kept", c["disruption_days_kept"]["rain"]), ("lit", c["rule1_literal"]["rain"]),
                   ("mt", c["metro"]["rain"]), ("tc", post["temperature_bands_2c"]),
                   ("tlin", post["linear_temperature"])):
        put(key, e)
    for k, _, _ in DOSE:
        put(k, c["dose"][k])
    photo = next(p for p in json.loads((ROOT / "assets/photo/sources.json").read_text()) if p["slug"] == "rain-delays")
    v["photo"] = ('<section class="film film-page"><div class="shot" style="view-transition-name:ph-rain-delays;'
                  '--bg:url(../assets/photo/rain-delays.jpg);--bg-s:url(../assets/photo/rain-delays-1200.jpg)"></div>'
                  f'<p class="credit">Photo: <a href="{photo["page"]}">{photo["author"]}</a> · {photo["licence"]}, '
                  'toned</p></section>')
    v["pyfixest"] = metadata.version("pyfixest")
    return v


def main() -> None:
    x = load()
    days = figures(x)
    v = values(x, days)
    t = Path(__file__).with_name("template.html").read_text(encoding="utf-8")
    out = re.sub(r"\{\{(\w+)\}\}", lambda m: str(v[m.group(1)]), t)
    left = re.findall(r"\{\{\w+\}\}", out)
    assert not left, left
    (ROOT / "texts" / "rain-delays.html").write_text(out, encoding="utf-8")
    print(json.dumps({k: v[k] for k in v if k != "photo"}, ensure_ascii=False, indent=0))


if __name__ == "__main__":
    main()
