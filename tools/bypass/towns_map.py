"""Added after the results, not registered: the map of the treated towns and the example town, raw counts only.

For each of the treated towns: its bypass (list row, road, class, construction start, opening), and police-recorded
injury accidents inside the built-up area per year (the Q1 count of `estimate.real_counts`), with the mean per year
before construction and after the opening year. A single town's before and after is a raw count, not an estimate.

The example town is picked by a rule fixed before its counts were looked at: among the treated towns on class I
roads, the one with the most post-opening years in stage A (2016–2025); ties broken by the earliest opening month.

Writes assets/bypass-accidents/{map.json, base-cz.json, 03-map.svg} and docs/research/bypass-towns.json.

    nice -n 20 uv run --no-project --with pandas --with numpy --with pyarrow --with statsmodels --with scipy \
        --with shapely --with pyproj --with geopandas --with pyogrio --with matplotlib python -I tools/bypass/towns_map.py
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import estimate as E  # noqa: E402
import screen as S  # noqa: E402
import towns as T  # noqa: E402

A = T.ROOT / "assets/bypass-accidents"
OUT = T.ROOT / "docs/research/bypass-towns.json"
OBCE = T.ROOT / "tools/data/bypass/ruian/1/OBCE_P.shp"
YEARS = range(T.FIRST_YEAR, T.LAST_YEAR + 1)
DOT_KM = 3.2  # radius of a town's dot, large enough to hover on a country map
HELD, GREY = "#34507c", "#8a8a86"


def rings(geom, tol: float) -> list:
    g = geom.simplify(tol, preserve_topology=True)
    return [[[round(x, 3), round(y, 3)] for x, y in p.exterior.coords] for p in getattr(g, "geoms", [g])]


def dot(lon: float, lat: float) -> list:
    r = DOT_KM / 111.0
    return [[[round(lon + r * math.cos(t) / math.cos(math.radians(lat)), 4), round(lat + r * math.sin(t), 4)]
             for t in np.linspace(0, 2 * math.pi, 17)]]


def mean(xs: list[int]) -> float | None:
    return float(np.mean(xs)) if xs else None


def main() -> None:
    import geopandas as gpd

    b = T.load_list().set_index("id")
    table, _ = S.areas(S.ku_versions(), S.ku_areas(), [f"{y}-01-01" for y in range(T.FIRST_YEAR, T.LAST_YEAR + 2)])
    towns = E.town_table(T.select(b.reset_index(), S.area_change(table)))
    tr = towns[towns["role"] == "treated"].reset_index(drop=True)
    allc = E.real_counts(tr, b.reset_index()).set_index(["town", "year"])
    counts, whole = allc["q1"], allc["q2"]

    obce = gpd.read_file(OBCE)
    obce["KOD"] = obce["KOD"].astype(int)
    wgs = obce.to_crs(4326)
    regions = wgs.dissolve("VUSC_KOD").geometry
    base = {"outline": rings(regions.union_all(), 0.01), "districts": [r for g in regions for r in rings(g, 0.01)],
            "water": [], "credit": "base: the 14 regions from ČÚZK RÚIAN"}
    A.mkdir(parents=True, exist_ok=True)
    (A / "base-cz.json").write_text(json.dumps(base, separators=(",", ":")), encoding="utf-8")
    at = wgs.set_index("KOD").geometry.representative_point()
    name = obce.set_index("KOD")["NAZEV"]

    rows = []
    for t in tr.itertuples():
        row = b.loc[t.row]
        yearly = {y: int(counts.get((t.town, y), 0)) for y in YEARS}
        pre = [yearly[y] for y in YEARS if y < t.start_year]
        post = [yearly[y] for y in YEARS if y > t.open_year]
        rows.append({"town": int(t.town), "name": str(name[t.town]), "row": t.row, "project": row["project_name"],
                     "road": t.road, "class": t.road_class, "start_year": int(t.start_year),
                     "open_year": int(t.open_year), "opened": row["opened_date"], "open_month": t.open_month,
                     "yearly_injury_inside": yearly,
                     "yearly_injury_municipality": {y: int(whole.get((t.town, y), 0)) for y in YEARS}, "pre_years": len(pre), "post_years": len(post),
                     "pre_mean": mean(pre), "post_mean": mean(post),
                     "lon": float(at[t.town].x), "lat": float(at[t.town].y)})

    class_i = [r for r in rows if r["class"] == "I"]
    most = max(r["post_years"] for r in class_i)
    tied = [r for r in class_i if r["post_years"] == most]
    example = min(tied, key=lambda r: (r["opened"], r["town"]))
    OUT.write_text(json.dumps({
        "note": "added after the results, not registered: raw counts per town, not estimates (tools/bypass/towns_map.py)",
        "example_rule": "among the treated towns on class I roads, the most post-opening years in 2016–2025; ties by the "
                        "earliest opening date",
        "example": example["town"], "example_tied": len(tied), "towns": rows}, indent=1, ensure_ascii=False))

    feats = [{"id": str(r["town"]), "name": r["name"],
              "sub": f'{r["project"]} · opened {r["opened"]}',
              "r": dot(r["lon"], r["lat"]),
              "v": {"cls": 1 if r["class"] == "I" else 2, "opened": r["open_year"],
                    "pre": None if r["pre_mean"] is None else round(r["pre_mean"], 2),
                    "post": None if r["post_mean"] is None else round(r["post_mean"], 2),
                    "pre_n": r["pre_years"], "post_n": r["post_years"]}} for r in rows]
    spec = {"held": HELD, "base": "base-cz.json", "lat0": 49.8, "features": feats,
            "views": [{"key": "cls", "label": "road class", "cats": [{"v": 2, "label": "class II"}, {"v": 1, "label": "class I"}]},
                      {"key": "pre", "label": "before works", "fmt": {"dp": 1}, "scale": "seq", "domain": [0, 30],
                       "note": "injury accidents a year, mean of the years before works"},
                      {"key": "post", "label": "after opening", "fmt": {"dp": 1}, "scale": "seq", "domain": [0, 30],
                       "note": "injury accidents a year, mean of the full years after opening"},
                      {"key": "opened", "label": "opened", "fmt": {"dp": 0, "nogroup": True}, "scale": "seq", "domain": [2020, 2024]}],
            "note": "Raw counts inside the built-up area, mean per year; one town's before and after is not an estimate.",
            "hint": "hover, tap or use the arrow keys for a town",
            "data": ["../assets/bypass-accidents/map.json", "../assets/bypass-accidents/towns.json"]}
    (A / "map.json").write_text(json.dumps(spec, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    (A / "towns.json").write_text(OUT.read_text(encoding="utf-8"), encoding="utf-8")

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.family": "Helvetica", "font.size": 9, "svg.fonttype": "none"})
    f, ax = plt.subplots(figsize=(7.2, 4.0))
    small = regions.simplify(0.01, preserve_topology=True)
    small.plot(ax=ax, color="#f2f2ef", edgecolor="#ffffff", linewidth=0.8)
    gpd.GeoSeries([regions.union_all().simplify(0.01)], crs=4326).boundary.plot(ax=ax, color="#c9c9c4", linewidth=0.8)
    for cls, c, lab in (("II", GREY, "class II road"), ("I", HELD, "class I road")):
        pts = [r for r in rows if r["class"] == cls]
        ax.scatter([r["lon"] for r in pts], [r["lat"] for r in pts], s=28, color=c, edgecolor="white", linewidth=0.8,
                   label=f"{lab} ({len(pts)} towns)", zorder=3)
    ax.set_aspect(1 / math.cos(math.radians(49.8)))
    ax.set_axis_off()
    ax.legend(frameon=False, fontsize=8, loc="lower left")
    f.tight_layout()
    f.savefig(A / "03-map.svg")
    plt.close(f)
    print("example", example["name"], example["row"], "tied", len(tied), "post years", most)


if __name__ == "__main__":
    main()
