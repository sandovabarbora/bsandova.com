"""Added after the results, not registered: the map of the four regions with their registered estimates.

Draws the regions of the design (§2) from the same Natural Earth file and the same construction as the frozen
`regions.py` (imported, nothing there changed), the distance bands around Kaliningrad city and, per region, the
pooled and yearly E, the pooled share D, the degraded-position days and the share of crossings with a position jump,
all read from docs/research/gnss-results.json. Nothing is estimated here.

Writes assets/gnss-interference/{map.json, base.json, 01-map.svg}.

    uv run --no-project --with shapely --with numpy --with matplotlib python -I tools/gnss/map.py
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import shapely
from shapely.geometry import box, shape
from shapely.ops import unary_union

sys.path.insert(0, str(Path(__file__).resolve().parent))
import count as C  # noqa: E402
import regions as R  # noqa: E402

A = R.ROOT / "assets/gnss-interference"
RES = R.ROOT / "docs/research/gnss-results.json"
HELD, GREY, CORAL = "#34507c", "#8a8a86", "#c0503f"
KALININGRAD = (C.KALININGRAD[1], C.KALININGRAD[0])  # lon, lat; count.py keeps lat, lon
BANDS_KM = (300, 600, 900)
VIEW = box(4.5, 44.8, 29.5, 60.8)
TOL = 0.02
NAMES = {"CZ": ("Czechia", "study region"), "PL": ("Poland", "study region"),
         "BALT": ("Estonia, Latvia and Lithuania", "study region, with a 22 km band of sea"),
         "CTRL": ("Austria and Switzerland", "control region, the reference for E")}


def rings(geom, tol: float = TOL) -> list:
    g = geom.simplify(tol, preserve_topology=True)
    out = []
    for p in getattr(g, "geoms", [g]):
        if p.area * 1e4 > 1:  # drop specks under about 0.0001 square degrees
            out.append([[round(x, 3), round(y, 3)] for x, y in p.exterior.coords])
    return out


def circle(km: float) -> list:
    lon0, lat0 = map(math.radians, KALININGRAD)
    d = km / (R.EARTH_R / 1000)
    pts = []
    for t in np.linspace(0, 2 * math.pi, 181):
        lat = math.asin(math.sin(lat0) * math.cos(d) + math.cos(lat0) * math.sin(d) * math.cos(t))
        lon = lon0 + math.atan2(math.sin(t) * math.sin(d) * math.cos(lat0), math.cos(d) - math.sin(lat0) * math.sin(lat))
        pts.append([round(math.degrees(lon), 3), round(math.degrees(lat), 3)])
    return pts


def clip_line(pts: list) -> list:
    g = shapely.LineString(pts).intersection(VIEW)
    return [[[round(x, 3), round(y, 3)] for x, y in l.coords] for l in getattr(g, "geoms", [g]) if not l.is_empty]


def pp(x: float | None, dp: int = 2) -> float | None:
    return None if x is None else round(100 * x, dp)


def main() -> None:
    res = json.loads(RES.read_text(encoding="utf-8"))
    pr, q4, dpd = res["primary"], res["q4"], res["degraded_position_days"]
    features = json.loads(R.ensure_ne().read_text(encoding="utf-8"))["features"]
    geoms = R.build_regions(features)
    region = {"CZ": geoms["CZ"], "PL": geoms["PL"], "BALT": geoms["BALT"], "CTRL": unary_union([geoms["AT"], geoms["CH"]])}

    countries = [shape(f["geometry"]).intersection(VIEW) for f in features if shape(f["geometry"]).intersects(VIEW)]
    countries = [g for g in countries if not g.is_empty and g.area > 0]
    base = {"outline": [r for g in countries for r in rings(g)], "districts": [r for g in countries for r in rings(g)],
            "water": [], "credit": "base: Natural Earth 1:10 m admin 0 countries, v5.1.2 (public domain)"}
    A.mkdir(parents=True, exist_ok=True)
    (A / "base.json").write_text(json.dumps(base, separators=(",", ":")), encoding="utf-8")

    feats = []
    for x, g in region.items():
        name, sub = NAMES[x]
        v = {"e": 0.0 if x == "CTRL" else pp(pr[f"E.{x}"]["est"]), "d": pp(pr[f"D.{x}"]["est"]),
             **{f"y{y}": 0.0 if x == "CTRL" else pp(pr[f"E.{x}.y{y}"]["est"]) for y in range(1, 5)},
             "days": None if x == "CTRL" else sum(d["degraded_position_days"] for d in dpd[x].values()),
             "jumps": pp(q4[f"S.{x}"]["est"], 3)}
        label = "" if x == "CTRL" else f' · {pr[f"E.{x}"]["label"]}'
        feats.append({"id": x, "name": name, "sub": sub + label, "r": rings(g, 0.01), "v": v})

    lines = [l for km in BANDS_KM for l in clip_line(circle(km))]
    labels = [{"at": [KALININGRAD[0] + 0.2, KALININGRAD[1] + 0.35], "s": "Kaliningrad"}]
    short = {"CZ": "Czechia", "PL": "Poland", "BALT": "Baltic states", "CTRL": "control"}
    for x, g in region.items():  # near-zero regions take the ramp's lightest colour, so they are named on the map
        c = g.representative_point()
        labels.append({"at": [round(c.x, 2), round(c.y, 2)], "s": short[x]})
    for km in BANDS_KM:  # each band's edge labelled due south-west of the city, where the map has room
        lon0, lat0 = map(math.radians, KALININGRAD)
        d, t = km / (R.EARTH_R / 1000), math.radians(235)
        lat = math.asin(math.sin(lat0) * math.cos(d) + math.cos(lat0) * math.sin(d) * math.cos(t))
        lon = lon0 + math.atan2(math.sin(t) * math.sin(d) * math.cos(lat0), math.cos(d) - math.sin(lat0) * math.sin(lat))
        labels.append({"at": [round(math.degrees(lon), 2), round(math.degrees(lat), 2)], "s": f"{km} km"})
    yr = {1: "Mar 2023 – Feb 2024", 2: "Mar 2024 – Feb 2025", 3: "Mar 2025 – Feb 2026", 4: "Mar – Oct 2026"}
    pct = {"dp": 2, "unit": " pp", "sign": True}
    spec = {"held": HELD, "base": "base.json", "lat0": 52.5, "fit": "features", "features": feats,
            "overlay": {"lines": lines, "points": [list(KALININGRAD)], "labels": labels},
            "views": [{"key": "e", "label": "E, all years", "fmt": pct, "scale": "seq", "domain": [0, 8],
                       "note": "degraded share minus control's, percentage points"},
                      *[{"key": f"y{y}", "label": f"year {y}", "fmt": pct, "scale": "seq", "domain": [0, 13],
                         "note": f"E in study year {y}, {yr[y]}"} for y in range(1, 5)],
                      {"key": "d", "label": "share D", "fmt": {"dp": 2, "unit": " %"}, "scale": "seq",
                       "domain": [0, 8], "note": "degraded position reports, % of usable reports"},
                      {"key": "days", "label": "degraded days", "fmt": {"dp": 0}, "scale": "seq", "domain": [0, 140],
                       "note": "sampled days with a degraded-position day, of 183; not defined for control"},
                      {"key": "jumps", "label": "position jumps", "fmt": {"dp": 2, "unit": " %"}, "scale": "seq",
                       "domain": [0, 0.5], "note": "crossings with a position jump, % of crossings"}],
            "note": "Registered estimates, read from the results file; circles mark 300, 600 and 900 km from Kaliningrad.",
            "hint": "hover, tap or use the arrow keys for a region",
            "data": ["../assets/gnss-interference/map.json", "../assets/gnss-interference/results.json"]}
    (A / "map.json").write_text(json.dumps(spec, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.family": "Helvetica", "font.size": 9, "svg.fonttype": "none"})
    f, ax = plt.subplots(figsize=(7.2, 6.0))
    for r in base["districts"]:
        ax.fill(*zip(*r), color="#f2f2ef", edgecolor="#c9c9c4", linewidth=0.5)
    shade = {"CZ": "#c9d3e3", "PL": "#7d92b5", "BALT": HELD, "CTRL": "#e2e2de"}
    for ft in feats:
        for r in ft["r"]:
            ax.fill(*zip(*r), color=shade[ft["id"]], edgecolor="white", linewidth=0.6)
        c = region[ft["id"]].representative_point()
        e = ft["v"]["e"]
        txt = "control" if ft["id"] == "CTRL" else f"E {e:+.2f} pp".replace("-", "−")
        ax.annotate(f'{ft["id"]}\n{txt}', (c.x, c.y), ha="center", va="center", fontsize=7.5,
                    color="white" if ft["id"] in ("BALT", "PL") else "#111")
    for l in lines:
        ax.plot(*zip(*l), color="#777", lw=0.8, ls=(0, (4, 3)))
    ax.plot(*KALININGRAD, "o", color="#111", ms=4, mec="white")
    for lb in labels:
        ax.annotate(lb["s"], lb["at"], fontsize=7, ha="center", color="#333")
    x0, y0, x1, y1 = unary_union(list(region.values())).bounds
    ax.set_xlim(x0 - 0.6, x1 + 0.6)
    ax.set_ylim(y0 - 0.4, y1 + 0.4)
    ax.set_aspect(1 / math.cos(math.radians(52.5)))
    ax.set_axis_off()
    f.tight_layout()
    f.savefig(A / "01-map.svg")
    plt.close(f)
    print({ft["id"]: ft["v"] for ft in feats}, "base kB", (A / "base.json").stat().st_size // 1024,
          "map kB", (A / "map.json").stat().st_size // 1024)


if __name__ == "__main__":
    main()
