"""Running late, part 4: figures, maps and the article on Zurich, Basel and Bern, every number from the result files.

Reads docs/research/swiss-trams-{results,screen}.json, tools/data/late/swiss_segments.parquet, part 1's
tools/data/late/segments.parquet and the stop positions of swiss_estimate.py; writes assets/late-swiss/ (charts.json,
base-<city>.json from tools/site/basemap_swiss.py, map-<city>.json, 01-s.svg, 02-curves.svg, 03-<city>.svg, results.json, segments.json) and texts/swiss-trams.html
from tools/late/swiss_template.html.

    uv run --no-project --with numpy --with pandas --with pyarrow --with scipy --with matplotlib --with duckdb \
        python tools/late/swiss_article.py
"""
from __future__ import annotations

import json
import math
import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "tools" / "site"))
from article_kit import GREY, HELD, LIGHT, n, render, results_reader, use_article_style  # noqa: E402
from swiss_estimate import swiss_xy  # noqa: E402
from tram_geo import offset_line  # noqa: E402

plt = use_article_style()
R, A, D = ROOT / "docs" / "research", ROOT / "assets" / "late-swiss", ROOT / "tools" / "data" / "late"
PROD, REC = "#c0503f", "#2a7f86"
CITIES = ("Zurich", "Basel", "Bern")
COLOUR = {"Prague": "#111111", "Zurich": HELD, "Basel": PROD, "Bern": REC, "Geneva": LIGHT}


def totals() -> dict[str, pd.DataFrame]:
    """Per segment: delay gained over the season (s) and passes, for Prague (part 1) and the three cities."""
    out = {}
    pr = pd.read_parquet(D / "segments.parquet").query("mode == 'tram'")
    out["Prague"] = pr.groupby(["seg_from", "seg_to"])[["gsum", "n"]].sum().reset_index()
    sw = pd.read_parquet(D / "swiss_segments.parquet")
    for c in CITIES:
        s = sw[(sw.city == c) & (sw.n > 0)]
        out[c] = s.groupby(["seg_from", "seg_to"])[["gsum", "n"]].sum().reset_index()
    return out


def curve(t: pd.DataFrame, points: int = 101) -> list[list[float]]:
    """Share of producers' delay made by the largest producers, against the share of segments."""
    g = np.sort(t["gsum"].to_numpy())[::-1]
    prod = g[g > 0].sum()
    cum = np.concatenate([[0], np.cumsum(g)]) / prod
    xs = np.linspace(0, 1, points)
    return [[round(float(x), 3), round(float(min(1.0, cum[int(round(x * len(g)))])), 4)] for x in xs]


def s_chart(res: dict) -> dict:
    rows, s0 = [], []
    pr = res["prague"]
    entries = [("Prague", pr["S"], pr["S0"]), *[(c, res["cities"][c]["S"], res["cities"][c]["S0"]) for c in CITIES],
               ("Geneva, forecasts kept", res["forecasts_kept"]["Geneva"]["S"], None)]
    for lab, s, z in entries:
        c = COLOUR.get(lab.split(",")[0], GREY)
        rows.append({"y": lab, "lo": s["ci95"][0], "hi": s["ci95"][1], "mid": s["est"], "c": c,
                     "label": f"{100 * s['est']:.1f} %",
                     "tip": f"{lab}: S {100 * s['est']:.1f} % (95 % CI {100 * s['ci95'][0]:.1f} to {100 * s['ci95'][1]:.1f})"})
        if z:
            s0.append({"x": z["median"], "y": lab, "c": "grey", "shape": "d",
                       "tip": f"{lab}: chance level {100 * z['median']:.1f} %"})
    return {"alt": "The share of delay made by the tenth of segments that make the most, with 95 % intervals, for "
                   "Prague, Zurich, Basel, Bern and Geneva, and the share chance alone would give (diamonds): Zurich "
                   "is lowest, Basel and Bern are close to Prague, and every Swiss city sits less far above its chance "
                   "level than Prague does.",
            "panels": [{"h": 34 * len(rows) + 30,
                        "x": {"kind": "linear", "domain": [0.15, 0.6], "ticks": [0.2, 0.3, 0.4, 0.5, 0.6],
                              "fmt": {"dp": 0, "pct": True}, "tickLabels": {str(t): f"{int(round(100 * t))} %" for t in
                                                                            (0.2, 0.3, 0.4, 0.5, 0.6)},
                              "label": "share of delay made by the top tenth of segments"},
                        "y": {"kind": "cat", "domain": [r["y"] for r in rows]},
                        "marks": [{"type": "rule", "axis": "x", "v": 0.5, "c": "grey", "dash": "dot"},
                                  {"type": "dots", "pts": s0}, {"type": "range", "rows": rows}]}],
            "legend": [{"label": "S, 95 % interval", "c": HELD}, {"label": "chance level", "c": "grey", "shape": "d"}],
            "table": {"cols": ["network", "S", "95 % interval", "chance level"],
                      "rows": [[r["y"], r["mid"], f"{r['lo']:.4f} to {r['hi']:.4f}",
                                next((p["x"] for p in s0 if p["y"] == r["y"]), None)] for r in rows]},
            "data": ["results.json"]}


def curves_chart(tot: dict) -> dict:
    cv = {c: curve(t) for c, t in tot.items()}
    marks = [{"type": "line", "pts": [[0, 0], [1, 1]], "c": "light", "w": 1, "dash": "dash", "name": "equal"},
             {"type": "rule", "axis": "x", "v": 0.1, "c": "grey", "dash": "dot"}]
    marks += [{"type": "line", "pts": cv[c], "c": COLOUR[c], "name": c, "end": c, "fmt": {"dp": 2}} for c in cv]
    return {"alt": "Concentration curves: the share of delay made against the share of segments, largest producers "
                   "first, for Prague, Zurich, Basel and Bern; Zurich's rises least steeply.",
            "panels": [{"h": 280, "padRight": 64,
                        "x": {"kind": "linear", "domain": [0, 1], "ticks": [0, 0.1, 0.25, 0.5, 0.75, 1],
                              "fmt": {"dp": 2}, "label": "share of segments, largest producers first"},
                        "y": {"kind": "linear", "domain": [0, 1.05], "ticks": [0, 0.25, 0.5, 0.75, 1],
                              "fmt": {"dp": 2}, "label": "share of the delay made by producers"},
                        "marks": marks}],
            "table": {"cols": ["share of segments", *cv],
                      "rows": [[cv["Prague"][i][0], *[cv[c][i][1] for c in cv]] for i in range(len(cv["Prague"]))]},
            "data": ["segments.json"]}, cv


def map_spec(city: str, t: pd.DataFrame, xy: dict, lat0: float) -> tuple[dict, int]:
    feats = []
    t = t.assign(per_pass=t.gsum / t.n, hours=t.gsum / 3600)
    for r in t.sort_values("hours", key=abs).itertuples():
        if r.seg_from in xy and r.seg_to in xy:
            feats.append({"id": f"{r.seg_from} → {r.seg_to}", "name": f"{r.seg_from} → {r.seg_to}",
                          "sub": f"{n(r.n)} passes", "l": [offset_line(xy[r.seg_from], xy[r.seg_to])],
                          "v": {"all": round(float(r.per_pass), 1), "hours": round(float(r.hours), 1)}})
    top = t.sort_values("hours").iloc[-1]
    spec = {"held": PROD, "neg": REC, "fit": "features", "lat0": lat0, "features": feats,
            "base": f"../assets/late-swiss/base-{city.lower()}.json",
            "views": [{"key": "all", "label": "per pass", "fmt": {"dp": 0, "unit": " s", "sign": True}, "scale": "div",
                       "domain": [-60, 60], "note": "seconds per pass · coral lost, teal made up",
                       "mark": {"id": f"{top.seg_from} → {top.seg_to}", "label": "largest total"}},
                      {"key": "hours", "label": "hours in all", "fmt": {"dp": 0, "unit": " h", "sign": True},
                       "scale": "div", "domain": [-1500, 1500], "note": "season total"}],
            "hint": "hover, tap or use the arrow keys for a segment; each direction is drawn on its right",
            "data": ["segments.json"]}
    return spec, len(feats)


def static_map(spec: dict, path: Path, lat0: float) -> None:
    from matplotlib.collections import LineCollection
    from matplotlib.colors import LinearSegmentedColormap, Normalize
    k = math.cos(math.radians(lat0))
    cmap = LinearSegmentedColormap.from_list("late", [REC, "#e2e2de", PROD])
    norm = Normalize(-60, 60)
    f, ax = plt.subplots(figsize=(7.2, 5.0))
    base = json.loads((ROOT / spec["base"].removeprefix("../")).read_text(encoding="utf-8"))
    for ring in base["districts"] + base["outline"]:
        ax.plot([x * k for x, _ in ring], [y for _, y in ring], color="#d9d9d4", lw=0.5)
    for ring in base.get("lakes", []):
        ax.fill([x * k for x, _ in ring], [y for _, y in ring], color="#dfe6ec", lw=0)
    for line in base["water"]:
        ax.plot([x * k for x, _ in line], [y for _, y in line], color="#a9c4dc", lw=1.0)
    fs = spec["features"]
    ax.add_collection(LineCollection([[(x * k, y) for x, y in ft["l"][0]] for ft in fs],
                                     colors=[cmap(norm(ft["v"]["all"])) for ft in fs], linewidths=1.8,
                                     capstyle="round", rasterized=True))
    xs = [x * k for ft in fs for x, _ in ft["l"][0]]
    ys = [y for ft in fs for _, y in ft["l"][0]]
    ax.set_xlim(min(xs) - 0.004, max(xs) + 0.004)
    ax.set_ylim(min(ys) - 0.004, max(ys) + 0.004)
    ax.set_aspect("equal")
    ax.axis("off")
    f.tight_layout()
    f.savefig(path, dpi=220)
    plt.close(f)


def static_s(chart: dict, path: Path) -> None:
    p = chart["panels"][0]
    rows = p["marks"][2]["rows"]
    f, ax = plt.subplots(figsize=(7.2, 0.45 * len(rows) + 0.8))
    for i, r in enumerate(reversed(rows)):
        ax.plot([r["lo"], r["hi"]], [i, i], color=r["c"], lw=2.5)
        ax.plot(r["mid"], i, "o", color=r["c"], ms=6, mec="white")
        z = next((q for q in p["marks"][1]["pts"] if q["y"] == r["y"]), None)
        if z:
            ax.plot(z["x"], i, "D", color=GREY, ms=5)
    ax.axvline(0.5, color=GREY, lw=0.8, ls=":")
    ax.set_yticks(range(len(rows)), [r["y"] for r in reversed(rows)])
    ax.set_xlim(0.15, 0.6)
    ax.set_xlabel("share of delay made by the top tenth of segments (diamond: chance level)")
    f.tight_layout()
    f.savefig(path)
    plt.close(f)


def static_curves(cv: dict, path: Path) -> None:
    f, ax = plt.subplots(figsize=(7.2, 3.2))
    ax.plot([0, 1], [0, 1], color=LIGHT, lw=0.8, ls="--")
    for c, pts in cv.items():
        ax.plot([q[0] for q in pts], [q[1] for q in pts], color=COLOUR[c], lw=1.6, label=c)
    ax.axvline(0.1, color=GREY, lw=0.8, ls=":")
    ax.set_xlabel("share of segments, largest producers first")
    ax.set_ylabel("share of producers' delay")
    ax.legend(frameon=False, fontsize=8)
    f.tight_layout()
    f.savefig(path)
    plt.close(f)


def pct(v: float, dp: int = 1) -> str:
    return n(100 * v, dp)


def values(res: dict, scr: dict, drawn: dict) -> dict:
    pr = res["prague"]
    v = {"pr_s": pct(pr["S"]["est"]), "pr_s0": pct(pr["S0"]["median"]), "pr_e": pct(pr["S"]["est"] - pr["S0"]["median"]),
         "pr_len": pct(pr["checks"]["length"]["S_length"]), "pr_gini": n(pr["checks"]["gini"], 2),
         "geneva_s": pct(res["forecasts_kept"]["Geneva"]["S"]["est"]),
         "geneva_segs": n(res["forecasts_kept"]["Geneva"]["segments"]),
         "ties": n(scr["stops_dropped_as_ties"])}
    for c in CITIES:
        r, k = res["cities"][c], c.lower()
        ch = r["checks"]
        v |= {f"{k}_segs": n(r["segments"]), f"{k}_passes": n(r["passes"] / 1e6, 1),
              f"{k}_s": pct(r["S"]["est"]), f"{k}_lo": pct(r["S"]["ci95"][0]), f"{k}_hi": pct(r["S"]["ci95"][1]),
              f"{k}_label": r["S"]["label"], f"{k}_rho": f"{r['rho']['est']:.3f}", f"{k}_rho_label": r["rho"]["label"],
              f"{k}_s0": pct(r["S0"]["median"]), f"{k}_e": pct(r["E"]),
              f"{k}_d": n(100 * r["D"]["est"], 1, sign=True), f"{k}_d_lo": n(100 * r["D"]["ci95"][0], 1, sign=True),
              f"{k}_d_hi": n(100 * r["D"]["ci95"][1], 1, sign=True), f"{k}_d_label": r["D"]["label"],
              f"{k}_de": n(100 * r["D_E"]["est"], 1, sign=True), f"{k}_de_label": r["D_E"]["label"],
              f"{k}_len": pct(ch["length"]["S_length"]), f"{k}_gini": n(ch["gini"], 2),
              f"{k}_pp": pct(ch["per_pass"]), f"{k}_t5": pct(ch["top_5"]), f"{k}_t20": pct(ch["top_20"]),
              f"{k}_noterm": pct(ch["without_terminal_segments"]), f"{k}_300": pct(ch["gain_within_300s"]),
              f"{k}_mlo": pct(min(ch["by_month"].values())), f"{k}_mhi": pct(max(ch["by_month"].values())),
              f"{k}_jac": n(ch["peak_midday_jaccard"], 2), f"{k}_well": pct(ch["well_measured_segments"]["S"]),
              f"{k}_rec": pct(r["recoverer_share"], 0), f"{k}_drawn": n(drawn[c]),
              f"{k}_kept_real": pct(1 - scr["low_real_segments"][c]["share_of_passes"], 2)}
    b = res["cities"]["Basel"]["checks"]["basel"]
    v |= {"basel_bvb": pct(b["BVB_only_S"]), "basel_bvb_p": pct(b["S_BVB_passes"]), "basel_blt_p": pct(b["S_BLT_passes"])}
    p1 = json.loads((R / "delay-origins-results.json").read_text())["tram"]
    pc = p1["checks"]
    v |= {"pr_dates": n(p1["dates"]), "pr_pp": pct(pc["per_pass"]), "pr_t5": pct(pc["top_5"]), "pr_t20": pct(pc["top_20"]),
          "pr_noterm": pct(pc["without_terminal_segments"]), "pr_300": pct(pc["gain_within_300s"]),
          "pr_mlo": pct(min(pc["by_month"].values())), "pr_mhi": pct(max(pc["by_month"].values())),
          "pr_jac": n(pc["peak_midday_jaccard"], 2), "pr_rec": pct(p1["recoverers"] / p1["segments"], 0)}
    for c in CITIES:
        v[f"{c.lower()}_kept_formed"] = pct(scr["kept"][c]["passes"] / scr["passes_formed"][c])
        v[f"{c.lower()}_s0_lo"] = pct(res["cities"][c]["S0"]["range95"][0])
        v[f"{c.lower()}_s0_hi"] = pct(res["cities"][c]["S0"]["range95"][1])
        v[f"{c.lower()}_de_hi"] = n(100 * res["cities"][c]["D_E"]["ci95"][1], 1, sign=True)
    v["bern_d_abs"] = n(-100 * res["cities"]["Bern"]["D"]["est"], 1)
    return v


def main() -> None:
    j = results_reader("swiss-trams")
    res, scr = j("results"), j("screen")
    A.mkdir(parents=True, exist_ok=True)
    shutil.copy(R / "swiss-trams-results.json", A / "results.json")
    tot = totals()
    (A / "segments.json").write_text(json.dumps(
        {c: [{"from": r.seg_from, "to": r.seg_to, "passes": int(r.n), "delay_s": round(float(r.gsum))}
             for r in t.itertuples()] for c, t in tot.items() if c != "Prague"}, ensure_ascii=False))
    charts = {"s": s_chart(res)}
    charts["curves"], cv = curves_chart(tot)
    (A / "charts.json").write_text(json.dumps(charts, ensure_ascii=False, separators=(",", ":")))
    static_s(charts["s"], A / "01-s.svg")
    static_curves(cv, A / "02-curves.svg")
    xy = swiss_xy()
    drawn = {}
    for c, lat0 in (("Zurich", 47.38), ("Basel", 47.56), ("Bern", 46.95)):
        spec, drawn[c] = map_spec(c, tot[c], xy, lat0)
        (A / f"map-{c.lower()}.json").write_text(json.dumps(spec, ensure_ascii=False, separators=(",", ":")))
        static_map(spec, A / f"03-{c.lower()}.svg", lat0)
    v = values(res, scr, drawn)
    html = render((HERE / "swiss_template.html").read_text(encoding="utf-8"), v)
    (ROOT / "texts" / "swiss-trams.html").write_text(html, encoding="utf-8")
    print(json.dumps(v, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
