"""A shared Prague basemap for assets/map.js: the city outline, the 57 city districts and the Vltava.

Districts are the election precincts of tools/data/praha2/okrsky_praha.geojson dissolved by their city-district code
(momc); the outline is their union. The river is OpenStreetMap's Vltava (ODbL), fetched once into
tools/data/praha2/vltava.json. Writes assets/praha-base.json: {outline, districts, water}, rings and lines in lon/lat.

    uv run --with shapely python tools/site/basemap.py
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from shapely.geometry import LineString, shape
from shapely.ops import linemerge, unary_union

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "tools/data/praha2"
OUT = ROOT / "assets/praha-base.json"


def rings(geom, tol: float) -> list[list[list[float]]]:
    g = geom.simplify(tol, preserve_topology=True)
    return [[[round(x, 4), round(y, 4)] for x, y in p.exterior.coords] for p in getattr(g, "geoms", [g])]


def main() -> None:
    by = defaultdict(list)
    for f in json.loads((SRC / "okrsky_praha.geojson").read_text(encoding="utf-8"))["features"]:
        by[f["properties"]["momc"]].append(shape(f["geometry"]).buffer(0))
    districts = {k: unary_union(v) for k, v in by.items()}
    outline = unary_union(list(districts.values()))
    water = []
    river = SRC / "vltava.json"
    if river.exists():
        lines = [LineString([(p["lon"], p["lat"]) for p in e["geometry"]]) for e in json.loads(river.read_text(encoding="utf-8"))["elements"]]
        merged = linemerge(lines).intersection(outline.buffer(0.01)).simplify(0.0005)
        water = [[[round(x, 4), round(y, 4)] for x, y in l.coords] for l in getattr(merged, "geoms", [merged])]
    base = {"outline": rings(outline, 0.0008), "districts": [r for g in districts.values() for r in rings(g, 0.0008)],
            "water": water, "credit": "base: Prague's city districts from the election precincts; river © OpenStreetMap contributors (ODbL)"}
    OUT.write_text(json.dumps(base, separators=(",", ":")), encoding="utf-8")
    print(len(districts), "districts;", len(water), "river lines;", OUT.stat().st_size // 1024, "kB")


if __name__ == "__main__":
    main()
