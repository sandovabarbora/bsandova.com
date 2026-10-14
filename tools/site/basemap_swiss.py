"""Basemaps of Zurich, Basel and Bern for assets/map.js: the city outline, its districts, rivers and lake shores.

From OpenStreetMap (ODbL) through the Overpass API, fetched once per city into tools/data/late/swiss_base/<city>.json:
the municipalities (admin_level 8) in a box around the tram network, the city's districts (admin_level 9 or 10), and
rivers and lakes.
Writes assets/late-swiss/base-<city>.json: {outline, districts, lakes, water, credit}, rings and lines in lon/lat, as
assets/praha-base.json.

    uv run --no-project --with shapely python tools/site/basemap_swiss.py
"""
from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

from shapely.geometry import LineString, MultiLineString, box
from shapely.ops import linemerge, polygonize, unary_union

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / "tools/data/late/swiss_base"
OUT = ROOT / "assets/late-swiss"
OVERPASS = ("https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter")
# bounding boxes cover each tram network, including lines that run out of the city
CITIES = {"Zurich": ("Zürich", 9, (47.31, 8.42, 47.47, 8.64)), "Basel": ("Basel", 10, (47.37, 7.43, 47.61, 7.79)),
          "Bern": ("Bern", 10, (46.89, 7.29, 47.00, 7.60))}

QUERY = """[out:json][timeout:300][bbox:{bbox}];
(
  rel["boundary"="administrative"]["admin_level"="8"];
  rel["boundary"="administrative"]["admin_level"="{level}"];
  way["waterway"="river"];
  way["natural"="water"]["water"~"lake|river"];
  rel["natural"="water"]["water"~"lake|river"];
);
out geom;"""


def fetch(city: str, name: str, level: int, bbox: tuple) -> dict:
    path = CACHE / f"{city.lower()}.json"
    if not path.exists():
        CACHE.mkdir(parents=True, exist_ok=True)
        q = QUERY.format(name=name, level=level, bbox=",".join(map(str, bbox)))
        data = urllib.parse.urlencode({"data": q}).encode()
        for url in OVERPASS * 3:
            try:
                req = urllib.request.Request(url, data=data, headers={"User-Agent": "bsandova.com research"})
                with urllib.request.urlopen(req, timeout=400) as r:
                    path.write_bytes(r.read())
                break
            except OSError as e:
                print(city, url, e)
                time.sleep(20)
        else:
            raise RuntimeError(f"{city}: Overpass did not answer")
        time.sleep(5)
    return json.loads(path.read_text(encoding="utf-8"))


def lines_of(el: dict) -> list[LineString]:
    if el["type"] == "way":
        return [LineString([(p["lon"], p["lat"]) for p in el["geometry"]])]
    return [LineString([(p["lon"], p["lat"]) for p in m["geometry"]]) for m in el.get("members", [])
            if m.get("type") == "way" and m.get("role") in ("outer", "") and len(m.get("geometry", [])) > 1]


def area_of(el: dict):
    return unary_union(list(polygonize(linemerge(lines_of(el)))))


def rings(geom, tol: float) -> list[list[list[float]]]:
    g = geom.simplify(tol, preserve_topology=True)
    return [[[round(x, 4), round(y, 4)] for x, y in p.exterior.coords] for p in getattr(g, "geoms", [g])]


def coords(geom) -> list[list[list[float]]]:
    parts = getattr(geom, "geoms", [geom])
    return [[[round(x, 4), round(y, 4)] for x, y in p.coords] for p in parts if p.length > 0]


def build(city: str, name: str, level: int, bbox: tuple) -> dict:
    els = fetch(city, name, level, bbox)["elements"]
    tags = lambda e: e.get("tags", {})  # noqa: E731
    frame = box(bbox[1], bbox[0], bbox[3], bbox[2])
    city = next(area_of(e) for e in els if tags(e).get("admin_level") == "8" and tags(e).get("name") == name)
    # the city's own districts, and the neighbouring municipalities the network reaches into
    districts = [area_of(e) for e in els if tags(e).get("admin_level") == str(level)]
    districts = [d for d in districts if not d.is_empty and d.representative_point().within(city)] or [city]  # Basel has none in OSM
    others = [area_of(e) for e in els if tags(e).get("admin_level") == "8" and tags(e).get("name") != name]
    others = [o.intersection(frame) for o in others if not o.is_empty and o.intersects(frame)]
    districts += [o for o in others if not o.is_empty and o.area > 0]
    outline = unary_union([city, *others]).intersection(frame)
    lakes = [area_of(e).intersection(frame) for e in els if tags(e).get("water") == "lake"]
    water = []
    for e in els:
        t = tags(e)
        if t.get("waterway") == "river" or t.get("natural") == "water":
            for ln in lines_of(e):
                clipped = ln.intersection(frame).simplify(0.0003)
                if not clipped.is_empty:
                    water += coords(clipped if isinstance(clipped, (LineString, MultiLineString)) else clipped.boundary)
    return {"outline": rings(outline, 0.0005), "districts": [r for d in districts for r in rings(d, 0.0005) if len(r) > 3],
            "lakes": [r for lk in lakes if not lk.is_empty for r in rings(lk, 0.0003) if len(r) > 3],
            "water": water, "credit": f"base: {name}, its districts and neighbouring municipalities, rivers and lakes © OpenStreetMap contributors (ODbL)"}


def check_frame(city: str, bbox: tuple) -> None:
    """The box must hold every segment of the article's map, or lines run off the basemap."""
    spec = OUT / f"map-{city.lower()}.json"
    if spec.exists():
        pts = [p for f in json.loads(spec.read_text(encoding="utf-8"))["features"] for ln in f["l"] for p in ln]
        lo_y, lo_x, hi_y, hi_x = bbox
        out = [p for p in pts if not (lo_x <= p[0] <= hi_x and lo_y <= p[1] <= hi_y)]
        assert not out, f"{city}: {len(out)} segment points outside the box, e.g. {out[0]}"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for city, (name, level, bbox) in CITIES.items():
        check_frame(city, bbox)
        base = build(city, name, level, bbox)
        path = OUT / f"base-{city.lower()}.json"
        path.write_text(json.dumps(base, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
        print(city, len(base["districts"]), "districts;", len(base["water"]), "water lines;", path.stat().st_size // 1024, "kB")


if __name__ == "__main__":
    main()
