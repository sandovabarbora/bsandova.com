"""The interactive map of the Eurovision article: average televote minus jury points from Czechia and from Germany
to each performer, 2016–2025, pairs met in at least three rounds.

Same numbers as fig. 3 (assets/eurovision/pairs.csv); writes assets/eurovision/map.json for assets/map.js.

    uv run --with pandas --with shapely --with matplotlib --with pyarrow python tools/eurovision/map_json.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
from shapely.geometry import box, shape

sys.path.insert(0, str(Path(__file__).resolve().parent))
from article import CORAL, HELD, NAMES, A, D  # noqa: E402

FRAME = box(-12, 34, 45, 68)  # the window of the static fig. 3
VOTERS = ("CZ", "DE")


def rings(geom, tol: float = 0.04) -> list[list[list[float]]]:
    g = geom.intersection(FRAME).simplify(tol, preserve_topology=True)
    return [[[round(x, 3), round(y, 3)] for x, y in p.exterior.coords]
            for p in getattr(g, "geoms", [g]) if p.geom_type == "Polygon" and not p.is_empty]


def main() -> None:
    pairs = pd.read_csv(A / "pairs.csv")
    gj = json.loads((D / "geo" / "ne_50m_admin_0_countries.geojson").read_text())
    feats = []
    for ft in gj["features"]:
        iso = ft["properties"].get("ISO_A2_EH") or ft["properties"].get("ISO_A2")
        if iso not in NAMES:
            continue
        r = rings(shape(ft["geometry"]))
        if not r:
            continue
        v = {}
        for voter in VOTERS:
            g = pairs[(pairs.i == voter) & (pairs.j == iso) & (pairs.n >= 3)]
            v[voter] = round(float(g.gap.iloc[0]), 2) if len(g) else None
        feats.append({"id": iso, "name": NAMES[iso], "r": r, "v": v})
    views = [{"key": voter, "label": f"{NAMES[voter]}'s televote minus its jury", "scale": "div", "domain": [-8, 8],
              "fmt": {"dp": 1, "sign": True, "unit": " pts"}, "note": "average points, 2016–2025",
              "mark": {"id": voter, "label": NAMES[voter] + ", the voter"}} for voter in VOTERS]
    spec = {"held": HELD, "neg": CORAL, "lat0": 51.3, "features": feats, "views": views,
            "note": "hatched: fewer than three rounds together",
            "hint": "hover, tap or use the arrow keys for a country", "data": ["pairs.csv"]}
    (A / "map.json").write_text(json.dumps(spec, ensure_ascii=False, separators=(",", ":")))
    print(len(feats), "countries;", {voter: sum(f["v"][voter] is not None for f in feats) for voter in VOTERS})


if __name__ == "__main__":
    main()
