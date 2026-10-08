"""Where is delay born on Prague's trams: figures, the map and the article, every number from the result files.

Reads docs/research/delay-origins-{results,screen,describe}.json, tools/data/late/segments.parquet and the PID GTFS stops
(tools/data/praha2/gtfs/); writes assets/late/ (charts.json, map.json, 01-map.svg, 02-top.svg, 03-stops.svg,
04-checks.svg, results.json, segments.json) and texts/delay-origins.html from tools/late/template.html. Chart
helpers are the rain article's.

    uv run --with matplotlib --with pandas --with pyarrow --with duckdb --with pyfixest python tools/late/article.py
"""
from __future__ import annotations

import importlib.util
import json
import math
import re
import shutil
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("rain_article", ROOT / "tools" / "rain" / "article.py")
ra = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ra)
plt, n = ra.plt, ra.n

R, A, D = ROOT / "docs" / "research", ROOT / "assets" / "late", ROOT / "tools" / "data" / "late"
GTFS = ROOT / "tools" / "data" / "praha2" / "gtfs"
PROD, REC, GREY = "#c0503f", "#2a7f86", "#666666"  # coral: delay made; teal: delay made up
PEAK, MIDDAY = set(range(7, 9)) | set(range(15, 18)), set(range(10, 14))
OFFSET = 0.00011  # degrees: the two directions of a segment drawn side by side, each on its right


def load() -> dict:
    j = lambda name: json.loads((R / f"delay-origins-{name}.json").read_text())  # noqa: E731
    return {"res": j("results"), "scr": j("screen"), "desc": j("describe")}


def tram_stops() -> pd.DataFrame:
    """Mean position of the platforms of each stop name that trams serve, from the PID GTFS."""
    con = duckdb.connect()
    return con.execute(f"""
        WITH tram AS (SELECT DISTINCT st.stop_id
                      FROM read_csv('{GTFS}/stop_times.txt', all_varchar = true) st
                      JOIN read_csv('{GTFS}/trips.txt', all_varchar = true) t USING (trip_id)
                      JOIN read_csv('{GTFS}/routes.txt', all_varchar = true) r USING (route_id)
                      WHERE r.route_type = '0')
        SELECT s.stop_name AS name, avg(CAST(s.stop_lat AS DOUBLE)) AS lat, avg(CAST(s.stop_lon AS DOUBLE)) AS lon
        FROM read_csv('{GTFS}/stops.txt', all_varchar = true) s JOIN tram USING (stop_id)
        GROUP BY 1""").df()


def segment_table() -> pd.DataFrame:
    s = pd.read_parquet(D / "segments.parquet")
    s = s[s["mode"] == "tram"].copy()
    wd = pd.to_datetime(s["date"]).dt.weekday < 5
    views = {"all": s, "peak": s[wd & s["hour"].isin(PEAK)], "midday": s[wd & s["hour"].isin(MIDDAY)]}
    t = None
    for k, v in views.items():
        g = v.groupby(["seg_from", "seg_to"])[["gsum", "n"]].sum()
        g[k] = g["gsum"] / g["n"]
        if k == "all":
            g["hours"], g["passes"] = g["gsum"] / 3600, g["n"]
            run = v.groupby(["seg_from", "seg_to"])[["gsum_run", "n_run"]].sum()
            g["run"] = run["gsum_run"] / run["n_run"].where(run["n_run"] > 0)
            t = g[["all", "hours", "passes", "run"]]
        else:
            t = t.join(g[[k]], how="left")
    return t.reset_index()


def offset_line(a: tuple, b: tuple) -> list:
    (x0, y0), (x1, y1) = a, b
    k = math.cos(math.radians(50.08))
    dx, dy = (x1 - x0) * k, y1 - y0
    L = math.hypot(dx, dy) or 1
    ox, oy = dy / L * OFFSET / k, -dx / L * OFFSET  # to the right of the direction of travel
    return [[round(x0 + ox, 5), round(y0 + oy, 5)], [round(x1 + ox, 5), round(y1 + oy, 5)]]


def map_spec(t: pd.DataFrame, xy: dict) -> tuple[dict, int]:
    feats = []
    for r in t.sort_values("hours", key=abs).itertuples():
        if r.seg_from in xy and r.seg_to in xy and r.seg_from != r.seg_to:
            v = lambda x: None if pd.isna(x) else round(float(x), 1)  # noqa: E731
            feats.append({"id": f"{r.seg_from} → {r.seg_to}", "name": f"{r.seg_from} → {r.seg_to}",
                          "sub": f"{n(r.passes)} passes", "l": [offset_line(xy[r.seg_from], xy[r.seg_to])],
                          "v": {"all": v(r.all), "peak": v(r.peak), "midday": v(r.midday), "hours": v(r.hours)}})
    pp = {"dp": 1, "unit": " s", "sign": True}
    top = t.sort_values("hours").iloc[-1]
    spec = {"held": PROD, "neg": REC, "base": "../assets/praha-base.json", "features": feats,
            "views": [{"key": "all", "label": "all hours", "fmt": pp, "scale": "div", "domain": [-60, 60],
                       "note": "delay gained per pass, seconds; coral made, teal made up",
                       "mark": {"id": f"{top.seg_from} → {top.seg_to}", "label": "the largest producer"}},
                      {"key": "peak", "label": "weekday peaks", "fmt": pp, "scale": "div", "domain": [-60, 60],
                       "note": "07:00–08:59 and 15:00–17:59, per pass"},
                      {"key": "midday", "label": "weekday middays", "fmt": pp, "scale": "div", "domain": [-60, 60],
                       "note": "10:00–13:59, per pass"},
                      {"key": "hours", "label": "hours in all", "fmt": {"dp": 0, "unit": " h", "sign": True},
                       "scale": "div", "domain": [-1500, 1500], "note": "total delay made (or made up), 15 March – 8 September"}],
            "note": "no data in this view", "hint": "hover, tap or use the arrow keys for a segment; each direction is drawn on its right",
            "data": ["segments.json", "results.json"]}
    return spec, len(feats)


def static_map(spec: dict, path: Path) -> None:
    from matplotlib.collections import LineCollection
    from matplotlib.colors import LinearSegmentedColormap, Normalize
    k = math.cos(math.radians(50.08))
    cmap = LinearSegmentedColormap.from_list("late", [REC, "#e2e2de", PROD])
    norm = Normalize(-60, 60)
    f, ax = plt.subplots(figsize=(7.2, 5.6))
    feats = [x for x in spec["features"] if x["v"]["all"] is not None]
    lines = [[(x * k, y) for x, y in ft["l"][0]] for ft in feats]
    ax.add_collection(LineCollection(lines, colors=[cmap(norm(ft["v"]["all"])) for ft in feats], linewidths=1.8,
                                     capstyle="round", rasterized=True))
    ax.autoscale()
    ax.set_aspect("equal")
    ax.axis("off")
    cb = f.colorbar(plt.cm.ScalarMappable(cmap=cmap, norm=norm), ax=ax, fraction=0.03, pad=0.01)
    cb.set_label("seconds of delay gained per pass", color=GREY)
    f.tight_layout()
    f.savefig(path, dpi=220)
    plt.close(f)


def hbar_chart(rows: list[dict], alt: str, label: str, domain: list, cols: list, table: list) -> dict:
    return {"alt": alt,
            "panels": [{"h": 22 * len(rows) + 30,
                        "x": {"kind": "linear", "domain": domain, "fmt": {"dp": 0, "sign": True}, "label": label},
                        "y": {"kind": "cat", "domain": [r["y"] for r in rows]},
                        "marks": [{"type": "rule", "axis": "x", "v": 0, "c": "grey"}, {"type": "hbar", "rows": rows}]}],
            "table": {"cols": cols, "rows": table}, "data": ["segments.json"]}


def static_hbar(rows: list[dict], path: Path, label: str) -> None:
    f, ax = plt.subplots(figsize=(7.2, 0.24 * len(rows) + 0.8))
    for i, r in enumerate(reversed(rows)):
        ax.barh(i, r["x1"], color=r["c"], height=0.6)
    ax.set_yticks(range(len(rows)), [r["y"] for r in reversed(rows)], fontsize=7)
    ax.axvline(0, color=GREY, lw=0.8)
    ax.set_xlabel(label)
    f.tight_layout()
    f.savefig(path)
    plt.close(f)


def figures(x: dict, t: pd.DataFrame, xy: dict) -> dict:
    A.mkdir(parents=True, exist_ok=True)
    shutil.copy(R / "delay-origins-results.json", A / "results.json")
    res = x["res"]["tram"]
    (A / "segments.json").write_text(json.dumps(
        [{"from": r.seg_from, "to": r.seg_to, "passes": int(r.passes), "per_pass_s": round(r.all, 2),
          "hours": round(r.hours, 1), "running_time_per_pass_s": None if pd.isna(r.run) else round(r.run, 2),
          "peak_per_pass_s": None if pd.isna(r.peak) else round(r.peak, 2),
          "midday_per_pass_s": None if pd.isna(r.midday) else round(r.midday, 2)} for r in t.itertuples()],
        ensure_ascii=False))
    spec, drawn = map_spec(t, xy)
    (A / "map.json").write_text(json.dumps(spec, ensure_ascii=False, separators=(",", ":")))
    static_map(spec, A / "01-map.svg")

    o = t.sort_values("hours")
    sel = pd.concat([o.tail(15).iloc[::-1], o.head(15)])
    top = [{"y": f"{r.seg_from} → {r.seg_to}", "x0": 0, "x1": round(r.hours), "c": PROD if r.hours > 0 else REC,
            "tip": f"{r.seg_from} → {r.seg_to}: {n(r.hours, 0, True)} h in all, {n(r.all, 1, True)} s per pass, "
                   f"{n(r.passes)} passes"} for r in sel.itertuples()]
    charts = {"top": hbar_chart(top, "The 15 tram segments that made the most delay and the 15 that made up the most, "
                                     "in hours over the season.", "hours of delay, 15 March – 8 September 2025",
                                [-1600, 2100], ["segment", "hours", "seconds per pass", "passes"],
                                [[r["y"], r["x1"], round(float(s.all), 1), int(s.passes)] for r, s in
                                 zip(top, sel.itertuples())])}
    static_hbar(top, A / "02-top.svg", "hours of delay, 15 March – 8 September 2025")

    rows, table = [], []
    for q in x["desc"]["tram"]["large_stops"]:
        m = q["per_pass_s"]
        rows.append({"y": f"{q['stop']} · {q['side']}", "x0": 0, "x1": round(m, 1), "c": PROD if m > 0 else REC,
                     "tip": f"{q['side']} {q['stop']}: {n(m, 1, True)} s per pass over {q['segments']} segments"})
        table.append([q["stop"], q["side"], round(m, 1), q["segments"], q["passes"]])
    charts["stops"] = hbar_chart(rows, "Delay gained per pass on the segments arriving at and leaving six large stops: "
                                       "leaving costs time at all six; at the busiest, trams make time up arriving.",
                                 "seconds of delay gained per pass, weighted by passes", [-50, 70],
                                 ["stop", "segments", "seconds per pass", "segments", "passes"], table)
    charts["stops"]["table"]["cols"] = ["stop", "side", "seconds per pass", "segments", "passes"]
    charts["stops"]["data"] = ["describe.json"]
    shutil.copy(R / "delay-origins-describe.json", A / "describe.json")
    static_hbar(rows, A / "03-stops.svg", "seconds of delay gained per pass")

    c = res["checks"]
    pt = lambda lab, v, col="ink": {"y": lab, "lo": v, "hi": v, "mid": v, "c": col, "tip": f"{lab}: {v:.2f}"}  # noqa: E731
    S = res["S"]
    chk = [{"y": "registered: top 10 %, total", "lo": S["ci95"][0], "hi": S["ci95"][1], "mid": S["est"], "c": "held",
            "tip": f"registered: {S['est']:.3f} ({S['ci95'][0]:.3f} to {S['ci95'][1]:.3f})"},
           pt("top 5 %", c["top_5"]), pt("top 20 %", c["top_20"]), pt("ranked per pass", c["per_pass"]),
           pt("without first and last segments", c["without_terminal_segments"]),
           pt("passes within ±300 s", c["gain_within_300s"]), pt("running time only", c["running_time_only"], "grey")]
    chk += [pt(f"month {m}", v, "grey") for m, v in c["by_month"].items()]
    charts["checks"] = {"alt": "The share of all delay made by the top segments, registered and in every check.",
                        "panels": [{"h": 24 * len(chk) + 30,
                                    "x": {"kind": "linear", "domain": [0, 1], "ticks": [0, 0.25, 0.5, 0.75, 1],
                                          "fmt": {"dp": 2}, "label": "share of all delay made"},
                                    "y": {"kind": "cat", "domain": [r["y"] for r in chk]},
                                    "marks": [{"type": "rule", "axis": "x", "v": 0.5, "c": "grey"},
                                              {"type": "range", "rows": chk}]}],
                        "table": {"cols": ["version", "share", "95 % interval"],
                                  "rows": [[r["y"], round(r["mid"], 3),
                                            f"{r['lo']:.3f} to {r['hi']:.3f}" if r["lo"] != r["hi"] else ""] for r in chk]},
                        "data": ["results.json"]}
    f, ax = plt.subplots(figsize=(7.2, 0.3 * len(chk) + 0.8))
    for i, r in enumerate(reversed(chk)):
        ax.plot([r["lo"], r["hi"]], [i, i], color="#111111", lw=1.2)
        ax.plot(r["mid"], i, "o", color=ra.HELD if r["c"] == "held" else "#111111", ms=4)
    ax.axvline(0.5, color=GREY, lw=0.8)
    ax.set_yticks(range(len(chk)), [r["y"] for r in reversed(chk)], fontsize=7)
    ax.set_xlim(0, 1)
    ax.set_xlabel("share of all delay made")
    f.tight_layout()
    f.savefig(A / "04-checks.svg")
    plt.close(f)
    (A / "charts.json").write_text(json.dumps(charts, ensure_ascii=False))
    return {"drawn": drawn, "stops": table}


def values(x: dict, t: pd.DataFrame, fig: dict) -> dict:
    res, bus, scr = x["res"]["tram"], x["res"]["bus_secondary"], x["scr"]
    c, S, rho = res["checks"], res["S"], res["rho"]
    o = t.sort_values("hours", ascending=False)
    p = lambda r: f"{r.seg_from} → {r.seg_to}"  # noqa: E731
    months = list(c["by_month"].values())
    rem = [v for k, v in scr["removed_share_by_month"].items() if k.startswith("tram")]
    v = {"S": n(100 * S["est"], 1), "S_lo": n(100 * S["ci95"][0], 1), "S_hi": n(100 * S["ci95"][1], 1),
         "S_label": S["label"], "rho": f"{rho['est']:.3f}", "rho_lo": f"{rho['ci95'][0]:.3f}",
         "rho_hi": f"{rho['ci95'][1]:.3f}", "rho_label": rho["label"],
         "segments": n(res["segments"]), "passes_m": n(res["passes"] / 1e6, 1), "dates": n(res["dates"]),
         "top_k": n(math.ceil(0.1 * res["segments"])), "producers": n(res["producers"]),
         "recoverers": n(res["recoverers"]), "made_h": n(res["produced_s"] / 3600),
         "made_up_h": n(abs(res["recovered_s"]) / 3600), "net_h": n((res["produced_s"] + res["recovered_s"]) / 3600),
         "pp": n(100 * c["per_pass"]), "t5": n(100 * c["top_5"]), "t20": n(100 * c["top_20"]),
         "noterm": n(100 * c["without_terminal_segments"]), "g300": n(100 * c["gain_within_300s"]),
         "run": n(100 * c["running_time_only"]), "m_lo": n(100 * min(months)), "m_hi": n(100 * max(months)),
         "jac": f"{c['peak_midday_jaccard']:.2f}", "bjac": f"{bus['checks']['peak_midday_jaccard']:.2f}",
         "run_neg": n(100 * float((t["run"].dropna() < 0).mean())), "run_pos": n(int((t["run"] > 0).sum())),
         "run_seg": n(int(t["run"].notna().sum())),
         "bS": n(100 * bus["S"]["est"], 1), "bS_lo": n(100 * bus["S"]["ci95"][0], 1),
         "bS_hi": n(100 * bus["S"]["ci95"][1], 1), "bS_label": bus["S"]["label"],
         "brho": f"{bus['rho']['est']:.3f}", "brho_label": bus["rho"]["label"], "bseg": n(bus["segments"]),
         "drawn": n(fig["drawn"]), "rare": n(scr["rare_segments"]["tram"]["segments"]),
         "rare_p": n(scr["rare_segments"]["tram"]["passes"]),
         "cl_lo": n(100 * min(r["closure"] for r in rem)), "cl_hi": n(100 * max(r["closure"] for r in rem)),
         "ng_lo": n(100 * min(r["no_gain"] for r in rem)), "ng_hi": n(100 * max(r["no_gain"] for r in rem)),
         "def_off": n(100 * scr["definition_check"]["share_delay_gain_not_delay_difference"], 1),
         "sampled": n(scr["definition_check"]["sampled"])}
    for i, r in enumerate(o.head(4).itertuples(), 1):
        v[f"p{i}"], v[f"p{i}_h"], v[f"p{i}_s"] = p(r), n(r.hours), n(r.all, 0, True)
    for i, r in enumerate(o.tail(2).iloc[::-1].itertuples(), 1):
        v[f"r{i}"], v[f"r{i}_h"], v[f"r{i}_s"] = p(r), n(abs(r.hours)), n(r.all, 0, True)
    pick = lambda a, b: t[(t["seg_from"] == a) & (t["seg_to"] == b)].iloc[0]["all"]  # noqa: E731
    v["vod"], v["vac"] = n(pick("Vodičkova", "Václavské náměstí"), 0, True), n(pick("Václavské náměstí", "Jindřišská"), 0, True)
    st = {(r[0], r[1]): r[2] for r in fig["stops"]}
    v["and_in"], v["and_out"] = n(st[("Anděl", "arriving")], 0, True), n(st[("Anděl", "leaving")], 0, True)
    v["hn_in"], v["hn_out"] = n(st[("Hlavní nádraží", "arriving")], 0, True), n(st[("Hlavní nádraží", "leaving")], 0, True)
    dt = x["desc"]["tram"]
    v["vol"], v["byd"] = n(100 * dt["top_tenth_pass_share"], 1), n(100 * dt["top_tenth_by_delay_pass_share"], 1)
    v["ovl"] = n(100 * dt["overlap_busiest_and_largest_producers"])
    photo = next(q for q in json.loads((ROOT / "assets/photo/sources.json").read_text()) if q["slug"] == "delay-origins")
    v["photo"] = ('<section class="film film-page"><div class="shot" style="view-transition-name:ph-delay-origins;'
                  '--bg:url(../assets/photo/delay-origins.jpg);--bg-s:url(../assets/photo/delay-origins-1200.jpg)"></div>'
                  f'<p class="credit">Photo: <a href="{photo["page"]}">{photo["author"]}</a> · '
                  f'{photo["licence"]}, toned</p></section>')
    return v


def main() -> None:
    x = load()
    t = segment_table()
    xy = {r.name: (r.lon, r.lat) for r in tram_stops().itertuples()}
    fig = figures(x, t, xy)
    v = values(x, t, fig)
    tpl = Path(__file__).with_name("template.html").read_text(encoding="utf-8")
    out = re.sub(r"\{\{(\w+)\}\}", lambda m: str(v[m.group(1)]), tpl)
    left = re.findall(r"\{\{\w+\}\}", out)
    assert not left, left
    (ROOT / "texts" / "delay-origins.html").write_text(out, encoding="utf-8")
    print(json.dumps({k: v[k] for k in v if k != "photo"}, ensure_ascii=False, indent=0))


if __name__ == "__main__":
    main()
