"""Clock change and pedestrian crashes: figures, the region map and the article, every number from the results.

Reads docs/research/dst-darkness-results.json and -data.json, tools/data/dst/cells.parquet and the Natural Earth
regions; writes assets/dst/ (charts.json, 01-hours.svg, 02-checks.svg, 03-map.svg, cells.parquet, results.json)
and texts/dst-darkness.html from tools/dst/template.html.

    uv run --with matplotlib --with pandas --with pyarrow --with shapely python tools/dst/article.py
"""
from __future__ import annotations

import json
import re
import shutil
import sys
from datetime import timedelta
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.patches import Polygon as MPoly  # noqa: E402
from shapely.geometry import shape  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from prepare import REGION, change_day  # noqa: E402
from sun import dark_share  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
R = ROOT / "docs" / "research"
A = ROOT / "assets" / "dst"
D = ROOT / "tools" / "data" / "dst"
HELD, INK, GREY, LIGHT = "#34507c", "#111111", "#666666", "#b5b5b0"
NB = " "
NAMES = {"CZ-PR": "Prague", "CZ-ST": "Central Bohemia", "CZ-JC": "South Bohemia", "CZ-PL": "Plzeň",
         "CZ-US": "Ústí nad Labem", "CZ-KR": "Hradec Králové", "CZ-JM": "South Moravia", "CZ-MO": "Moravia-Silesia",
         "CZ-OL": "Olomouc", "CZ-ZL": "Zlín", "CZ-VY": "Vysočina", "CZ-PA": "Pardubice", "CZ-LI": "Liberec",
         "CZ-KA": "Karlovy Vary"}
plt.rcParams.update({"font.family": "Helvetica", "font.size": 9, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": GREY, "xtick.color": GREY, "ytick.color": GREY, "svg.fonttype": "none"})


def n(v: float, dp: int = 0) -> str:
    s = f"{abs(v):,.{dp}f}".replace(",", NB)
    return ("−" if v < 0 and round(abs(v), dp) else "") + s


def pct(r: float, dp: int = 0) -> str:
    """A ratio as a signed percentage change."""
    v = 100 * (r - 1)
    return ("+" if v >= 0 else "−") + n(abs(v), dp)


def hourly(cells: pd.DataFrame) -> pd.DataFrame:
    """Pedestrian crashes per day nationally by clock hour, days −14 … −1 and +1 … +14, mean over the ten years."""
    w = cells[(cells.t >= -14) & (cells.t <= 14)]
    days = w.groupby(w.t > 0).date.nunique()
    h = w.groupby([w.t > 0, "hour"]).ped.sum().unstack(0)
    return pd.DataFrame({"pre": h[False] / days[False], "post": h[True] / days[True]})


def rush_minutes() -> dict:
    """Minutes of 16:00–18:59 after civil dusk at each region's centroid, mean over days −14…−1 and +1…+14, 2025."""
    gj = json.loads((D / "geo" / "ne_10m_admin_1.geojson").read_text())
    out = {}
    c0 = change_day(2025)
    for f in gj["features"]:
        iso = f["properties"].get("iso_3166_2")
        if iso not in REGION.values():
            continue
        geom = shape(f["geometry"])
        lat, lon = geom.centroid.y, geom.centroid.x
        m = {}
        for side, days, off in (("pre", range(-14, 0), 2), ("post", range(1, 15), 1)):
            m[side] = sum(60 * dark_share(c0 + timedelta(days=t), h, off, lat, lon, step_min=1)
                          for t in days for h in (16, 17, 18)) / len(days)
        out[iso] = {"geom": geom, **m}
    return out


def figures(res: dict, cells: pd.DataFrame) -> dict:
    A.mkdir(parents=True, exist_ok=True)
    shutil.copy(D / "cells.parquet", A / "cells.parquet")
    shutil.copy(R / "dst-darkness-results.json", A / "results.json")
    hp = hourly(cells)
    charts = {"hours": {
        "alt": "Pedestrian crashes per day in Czechia by clock hour, two weeks before and two weeks after the autumn "
               "clock change, mean of 2016–2025: the evening peak grows after the change.",
        "panels": [{"h": 260, "x": {"kind": "linear", "domain": [-0.5, 23.5], "ticks": list(range(0, 24, 2)),
                                    "fmt": {"dp": 0}, "label": "clock hour"},
                    "y": {"kind": "linear", "domain": [0, float(hp.max().max()) * 1.15], "fmt": {"dp": 2},
                          "label": "pedestrian crashes per day, Czechia"},
                    "marks": [{"type": "span", "v0": 15.5, "v1": 18.5, "c": "held", "label": "16–19 h"},
                              {"type": "line", "pts": [[int(h), float(v)] for h, v in hp.pre.items()], "c": "grey",
                               "dots": True},
                              {"type": "line", "pts": [[int(h), float(v)] for h, v in hp.post.items()], "c": "held",
                               "dots": True}]}],
        "legend": [{"label": "two weeks before", "c": "grey"}, {"label": "two weeks after", "c": "held"}],
        "table": {"cols": ["hour", "before, per day", "after, per day"],
                  "rows": [[int(h), round(float(a), 3), round(float(b), 3)] for h, (a, b) in hp.iterrows()]},
        "data": ["cells.parquet"]}}
    order = [("primary", "registered estimate"), ("placebo_day_-14", "placebo: fake change two weeks earlier"),
             ("window_7", "window ±7 days"), ("window_21", "window ±21 days"),
             ("no_2020_2021", "without 2020 and 2021"), ("group_trends", "original specification, group trends"),
             ("other_crash_kinds", "crashes without a pedestrian")]
    rows = [{"y": lab, "lo": res[k]["pe"]["lo"], "hi": res[k]["pe"]["hi"], "mid": res[k]["pe"]["ratio"],
             "c": "held" if k == "primary" else "ink",
             "tip": f"{lab}: ×{res[k]['pe']['ratio']:.2f} ({res[k]['pe']['lo']:.2f}–{res[k]['pe']['hi']:.2f})"}
            for k, lab in order]
    charts["checks"] = {
        "alt": "Evening ratio after the clock change, relative to midday, for the registered estimate and each check, "
               "with 95 % intervals; the placebo is near 1, the registered estimate near 1.75.",
        "panels": [{"h": 30 * len(rows), "x": {"kind": "log", "domain": [0.5, 2.6], "ticks": [0.5, 0.75, 1, 1.5, 2, 2.5],
                                               "fmt": {"dp": 2}, "label": "ratio, evening relative to midday, after / before"},
                    "y": {"kind": "cat", "domain": [r["y"] for r in rows]},
                    "marks": [{"type": "rule", "axis": "x", "v": 1, "c": "grey"},
                              {"type": "range", "rows": rows}]}],
        "table": {"cols": ["model", "ratio", "95 % interval"],
                  "rows": [[r["y"], round(r["mid"], 3), f"{r['lo']:.3f} to {r['hi']:.3f}"] for r in rows]},
        "data": ["results.json"]}
    (A / "charts.json").write_text(json.dumps(charts, ensure_ascii=False))

    f, ax = plt.subplots(figsize=(7.2, 2.8))
    ax.axvspan(15.5, 18.5, color=LIGHT, alpha=0.35, lw=0)
    ax.plot(hp.index, hp.pre, color=GREY, marker="o", ms=3, label="two weeks before")
    ax.plot(hp.index, hp.post, color=HELD, marker="o", ms=3, label="two weeks after")
    ax.set_xticks(range(0, 24, 2)); ax.set_xlabel("clock hour"); ax.set_ylabel("pedestrian crashes per day")
    ax.legend(frameon=False); f.tight_layout(); f.savefig(A / "01-hours.svg"); plt.close(f)

    f, ax = plt.subplots(figsize=(7.2, 2.9))
    for i, r in enumerate(reversed(rows)):
        c = HELD if r["c"] == "held" else INK
        ax.plot([r["lo"], r["hi"]], [i, i], color=c, lw=2.5, solid_capstyle="round")
        ax.plot(r["mid"], i, "o", color=c, ms=6, mec="white")
    ax.axvline(1, color=GREY, lw=0.8); ax.set_xscale("log"); ax.set_xticks([0.5, 0.75, 1, 1.5, 2, 2.5])
    ax.set_xticklabels(["0.5", "0.75", "1", "1.5", "2", "2.5"]); ax.xaxis.set_minor_formatter(plt.NullFormatter())
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([r["y"] for r in reversed(rows)]); ax.set_xlabel("ratio, evening relative to midday, after / before")
    f.tight_layout(); f.savefig(A / "02-checks.svg"); plt.close(f)

    rm = rush_minutes()
    f, axs = plt.subplots(1, 2, figsize=(7.2, 2.6))
    cmap = plt.get_cmap("Blues")
    for ax, side, title in ((axs[0], "pre", "two weeks before the change"), (axs[1], "post", "two weeks after")):
        for iso, v in rm.items():
            polys = getattr(v["geom"], "geoms", [v["geom"]])
            for p in polys:
                ax.add_patch(MPoly(list(p.exterior.coords), closed=True, fc=cmap(0.15 + 0.8 * v[side] / 180),
                                   ec="white", lw=0.6))
            c = v["geom"].centroid
            dx, dy = (-0.45, -0.32) if iso == "CZ-ST" else (0, 0)  # keep Central Bohemia's label off Prague
            ax.text(c.x + dx, c.y + dy, f"{v[side]:.0f}", ha="center", va="center", fontsize=7,
                    color="white" if v[side] > 100 else INK)
        ax.set_xlim(12, 19); ax.set_ylim(48.5, 51.1); ax.set_aspect(1 / 0.64); ax.axis("off")
        ax.set_title(title, fontsize=9, color=GREY)
    f.tight_layout(); f.savefig(A / "03-map.svg"); plt.close(f)
    return {"hours": hp, "rush": {k: {"pre": v["pre"], "post": v["post"]} for k, v in rm.items()}}


def values(res: dict, data: dict, cells: pd.DataFrame, fig: dict) -> dict:
    p, c = res["primary"], res
    w = cells[(cells.t >= -14) & (cells.t <= 14)]
    ped_total = int(w.ped.sum())
    ev = w[w.group == "evening"]
    hp = fig["hours"]
    rush = fig["rush"]
    east = max(rush, key=lambda k: rush[k]["post"])
    west = min(rush, key=lambda k: rush[k]["post"])
    v = {
        "ratio": f"{p['pe']['ratio']:.2f}", "ratio_lo": f"{p['pe']['lo']:.2f}", "ratio_hi": f"{p['pe']['hi']:.2f}",
        "ratio_pct": n(100 * (p["pe"]["ratio"] - 1)), "label": res["labels"]["H1"],
        "m_ratio": f"{p['pm']['ratio']:.2f}", "m_lo": f"{p['pm']['lo']:.2f}", "m_hi": f"{p['pm']['hi']:.2f}",
        "m_pct": pct(p["pm"]["ratio"]), "m_label": res["labels"]["H2"],
        "n_ped": n(ped_total), "n_records": n(sum(y["records"] for y in data["prepare"].values())),
        "n_cells": n(len(cells)), "n_ev_pre": n(ev[ev.t < 0].ped.sum()), "n_ev_post": n(ev[ev.t > 0].ped.sum()),
        "per_day": n(ped_total / w.date.nunique(), 1),
        "pk_pre": n(hp.pre.loc[16:18].sum(), 2), "pk_post": n(hp.post.loc[16:18].sum(), 2),
        "pk_hour": str(int(hp.post.idxmax())),
        "miss_ped": n(100 * res["missing_hour"]["ped"]["share"], 1),
        "miss_other": n(100 * res["missing_hour"]["other"]["share"], 0),
        "sun_ev_pre": n(100 * res["sun_dark_share"]["evening_pre"]), "sun_ev_post": n(100 * res["sun_dark_share"]["evening_post"]),
        "sun_mo_pre": n(100 * res["sun_dark_share"]["morning_pre"]), "sun_mo_post": n(100 * res["sun_dark_share"]["morning_post"]),
        "pol_ev_pre": n(100 * res["police_light"]["evening_pre"]["police_dark_share"]),
        "pol_ev_post": n(100 * res["police_light"]["evening_post"]["police_dark_share"]),
        "pol_mo_pre": n(100 * res["police_light"]["morning_pre"]["police_dark_share"]),
        "pol_mo_post": n(100 * res["police_light"]["morning_post"]["police_dark_share"]),
        "h3_b": n(c["H3"]["b_dark"], 3), "h3_lo": n(c["H3"]["lo"], 3), "h3_hi": n(c["H3"]["hi"], 3),
        "h3_pct": n(c["H3"]["pct_of_mean"]), "h3_mean": n(c["H3"]["pre_evening_mean"], 3),
        "h3_pct_lo": n(100 * c["H3"]["lo"] / c["H3"]["pre_evening_mean"]),
        "h3_pct_hi": n(100 * c["H3"]["hi"] / c["H3"]["pre_evening_mean"]),
        "east": NAMES[east], "west": NAMES[west], "east_post": n(rush[east]["post"]), "west_post": n(rush[west]["post"]),
        "east_pre": n(rush[east]["pre"]), "west_pre": n(rush[west]["pre"]),
        "pr_pre": n(rush["CZ-PR"]["pre"]), "pr_post": n(rush["CZ-PR"]["post"]),
        "pyfixest": res["versions"]["pyfixest"],
    }
    for k, key in (("placebo_day_-14", "pl"), ("window_7", "w7"), ("window_21", "w21"), ("no_2020_2021", "nc"),
                   ("group_trends", "gt"), ("other_crash_kinds", "oth")):
        v[key] = f"{c[k]['pe']['ratio']:.2f}"
        v[key + "_lo"], v[key + "_hi"] = f"{c[k]['pe']['lo']:.2f}", f"{c[k]['pe']['hi']:.2f}"
    v["gt_m"] = f"{c['group_trends']['pm']['ratio']:.2f}"
    v["oth_m"] = f"{c['other_crash_kinds']['pm']['ratio']:.2f}"
    v["extra"] = n(int(v["n_ev_post"].replace(NB, "")) * (1 - 1 / p["pe"]["ratio"]))
    v["extra_year"] = n(int(v["n_ev_post"].replace(NB, "")) * (1 - 1 / p["pe"]["ratio"]) / 10)
    photo = next(x for x in json.loads((ROOT / "assets" / "photo" / "sources.json").read_text()) if x["slug"] == "dst-darkness")
    v["photo"] = ('<section class="film film-page"><div class="shot" style="view-transition-name:ph-dst-darkness;'
                  '--bg:url(../assets/photo/dst-darkness.jpg);--bg-s:url(../assets/photo/dst-darkness-1200.jpg)"></div>'
                  f'<p class="credit">Photo: <a href="{photo["page"]}">{photo["author"]}</a> · {photo["licence"]}, toned</p></section>')
    return v


def main() -> None:
    res = json.loads((R / "dst-darkness-results.json").read_text())
    data = json.loads((R / "dst-darkness-data.json").read_text())
    cells = pd.read_parquet(D / "cells.parquet")
    fig = figures(res, cells)
    v = values(res, data, cells, fig)
    t = Path(__file__).with_name("template.html").read_text(encoding="utf-8")
    out = re.sub(r"\{\{(\w+)\}\}", lambda m: str(v[m.group(1)]), t)
    left = re.findall(r"\{\{\w+\}\}", out)
    assert not left, left
    (ROOT / "texts" / "dst-darkness.html").write_text(out, encoding="utf-8")
    print(json.dumps({k: v[k] for k in v if k != "photo"}, ensure_ascii=False, indent=0))


if __name__ == "__main__":
    main()
