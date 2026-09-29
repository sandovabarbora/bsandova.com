"""The interactive map of Part 4 (texts/prague-housing.html): Prague's 1 km squares of the metro test (H5).

For each of the 524 squares of tools/praha/housing_data.py it gives the flats completed between 1 January 2012 and
census day, 25 March 2021, counted exactly as h5_counts() in tools/praha/housing_extended.py counts them (RÚIAN
building points with flats, not flagged nespravny, completion date in the window, assigned to the square that
contains the point); the same count per 1 000 residents of the square in 2011 (GEOSTAT 2011, the population the
test holds equal); and the distance from the square's centroid to the nearest metro station open in 2012, as
housing_data.py computes it (the 2015 line A extension left out, a floor of 100 m).

Reads (tools/data, gitignored):
    praha4x/prague_cells.parquet            the squares, their 2011 population, distance and districts
    praha4x/prague/buildings.parquet        RÚIAN building points (flats, completion date)
    praha4x/prague/prague.parquet           the city boundary, to clip the squares for drawing
    praha4x/prague/city_districts.parquet   names of the 57 city districts
    assets/praha/housing_extended.json      the published H5 result, to check the count of squares and flats
    assets/praha/metro_lines.json           metro lines and stations for the overlay
Writes:
    assets/praha/map-housing.json           the map spec read by assets/map.js
    assets/praha/map-housing.svg         the static fallback: the default view with a legend

Usage:
    uv run --no-project --with pandas --with numpy --with shapely --with pyproj --with pyarrow \
        python tools/maps/housing.py
"""

import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
from pyproj import Transformer
from shapely import STRtree, wkb
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import transform

ROOT = Path(__file__).resolve().parents[2]
DATA = Path(os.environ.get("DATA", ROOT / "tools" / "data"))
RAW = DATA / "praha4x"
ASSETS = ROOT / "assets" / "praha"
OUT = ASSETS / "map-housing.json"
SVG = ASSETS / "map-housing.svg"
HELD = "#1f5fa8"  # tools/praha/figures_housing_extended.py
START, END = "2012-01-01", "2021-03-25"  # the H5 window of housing_extended.py
LINE_A_2015 = {"Bořislavka", "Nádraží Veleslavín", "Petřiny", "Nemocnice Motol"}  # as in housing_data.py
DEJVICKA = "Dejvická"  # line A's western end until April 2015

VIEWS = [
    {"key": "per1k", "label": "flats per 1 000 residents", "fmt": {"dp": 0}, "scale": "seq",
     "domain": [0, 200], "note": "darkest: 200 or more"},
    {"key": "flats", "label": "new flats", "fmt": {"dp": 0}, "scale": "seq", "domain": [0, 600],
     "note": "darkest: 600 or more"},
    {"key": "metro", "label": "metro distance", "fmt": {"dp": 1, "unit": " km"}, "scale": "seq",
     "domain": [0, 10], "note": "darkest: 10 km or more"},
]


def fmt_int(x: float) -> str:
    return f"{int(round(x)):,}".replace(",", "\u00a0")


def counts(cells: pd.DataFrame) -> np.ndarray:
    """h5_counts(cells, START, END) of housing_extended.py, without its heavy imports."""
    b = pd.read_parquet(RAW / "prague" / "buildings.parquet")
    b = b[b.nespravny.isna() | (b.nespravny.astype(str).str.strip() == "")]
    done = pd.to_datetime(b.dokonceni, unit="ms", errors="coerce")
    b = b[(done >= START) & (done <= END)]
    tree = STRtree([wkb.loads(g) for g in cells.geom_wkb])
    cell_of = np.array([(h[0] if len(h) else -1) for h in (tree.query(Point(x, y), predicate="within")
                                                           for x, y in zip(b.x, b.y))])
    ok = cell_of >= 0
    return np.bincount(cell_of[ok], weights=b.pocetbytu.to_numpy()[ok], minlength=len(cells))


def rings(g, to_wgs) -> list:
    polys = [g] if isinstance(g, Polygon) else list(g.geoms)
    out = []
    for p in polys:
        p = transform(to_wgs, p)
        ring = [[round(x, 4), round(y, 4)] for x, y in p.exterior.coords[:-1]]
        ring = [pt for i, pt in enumerate(ring) if i == 0 or pt != ring[i - 1]]
        if len(ring) >= 3:
            out.append(ring)
    return out


def metro_2012() -> dict:
    """The network as it ran 2012 to 2021: without the four stations of 2015 and line A cut at Dejvická."""
    m = json.loads((ASSETS / "metro_lines.json").read_text())
    st = [s for s in m["stations"] if s[2] not in LINE_A_2015]
    dej = next(s for s in m["stations"] if s[2] == DEJVICKA)
    lines = []
    for ln in m["lines"]:
        if any(abs(x - 14.3413) < 1e-4 and abs(y - 50.0753) < 1e-4 for x, y in ln[:1]):  # starts at Nemocnice Motol
            i = min(range(len(ln)), key=lambda k: (ln[k][0] - dej[0]) ** 2 + (ln[k][1] - dej[1]) ** 2)
            ln = ln[i:]
        lines.append([[round(x, 4), round(y, 4)] for x, y in LineString(ln).simplify(0.0002).coords])
    return {"lines": lines, "points": [[s[0], s[1]] for s in st]}


def build() -> dict:
    cells = pd.read_parquet(RAW / "prague_cells.parquet")
    y = counts(cells)
    pub = json.loads((ASSETS / "housing_extended.json").read_text())["H5"]
    assert len(cells) == pub["cells"] and int(y.sum()) == pub["flats"], (len(cells), y.sum())
    names = pd.read_parquet(RAW / "prague" / "city_districts.parquet").set_index("kod").nazev
    city = wkb.loads(pd.read_parquet(RAW / "prague" / "prague.parquet").geom_wkb[0]).simplify(40)
    to_wgs = Transformer.from_crs("EPSG:5514", "EPSG:4326", always_xy=True).transform
    metro_km = 2 ** cells.log2_metro_km.to_numpy()  # the registered distance, floored at 100 m
    feats = []
    for i, c in cells.iterrows():
        g = wkb.loads(c.geom_wkb).intersection(city)
        pop = float(c.pop2011)
        feats.append({"id": c.cell, "name": names[c.city_district], "sub": f"{fmt_int(pop)} residents in 2011",
                      "r": rings(g, to_wgs),
                      "v": {"per1k": round(float(y[i]) / pop * 1000, 1) if pop > 0 else None,
                            "flats": int(y[i]), "metro": round(float(metro_km[i]), 2)}})
    return {"held": HELD, "features": feats, "views": VIEWS, "overlay": metro_2012(),
            "note": "Flats completed 1 Jan 2012 to 25 Mar 2021 in Prague's 1 km squares; RÚIAN, GEOSTAT 2011.",
            "data": ["../assets/praha/map-housing.json"],
            "totals": {"cells": len(cells), "flats": int(y.sum()), "pop2011": int(cells.pop2011.sum())}}


# ------------------------------------------------------------------ static fallback, drawn as assets/map.js draws
def ramp(t: float) -> str:
    h = [int(HELD[i:i + 2], 16) for i in (1, 3, 5)]
    w, k = [246, 244, 238], [17, 17, 17]
    mix = lambda a, b, s: [round(a[j] + (b[j] - a[j]) * s) for j in range(3)]  # noqa: E731
    stops = [w, mix(h, w, 0.55), h, mix(h, k, 0.45)]
    u = max(0.0, min(1.0, t)) * 3
    i = min(2, int(u))
    return "rgb({},{},{})".format(*mix(stops[i], stops[i + 1], u - i))


def svg(S: dict) -> str:
    lat0, W = 50.08, 900
    k = 1 / np.cos(np.radians(lat0))
    xs = [p[0] for f in S["features"] for r in f["r"] for p in r]
    ys = [p[1] for f in S["features"] for r in f["r"] for p in r]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    s = W / (x1 - x0)
    H = round((y1 - y0) * k * s)
    X = lambda x: round((x - x0) * s, 1)  # noqa: E731
    Y = lambda y: round((y1 - y) * k * s, 1)  # noqa: E731
    V = S["views"][0]
    lo, hi = V["domain"]
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H + 60}" font-family="Helvetica, Arial, sans-serif">',
           f'<rect width="{W}" height="{H + 60}" fill="#fff"/>']
    for f in S["features"]:
        v = f["v"][V["key"]]
        fill = "#e6e6e3" if v is None else ramp((v - lo) / (hi - lo))
        d = "".join("M" + "L".join(f"{X(x)},{Y(y)}" for x, y in r) + "Z" for r in f["r"])
        out.append(f'<path d="{d}" fill="{fill}" stroke="#fff" stroke-width="0.5"/>')
    for ln in S["overlay"]["lines"]:
        out.append('<path d="M' + "L".join(f"{X(x)},{Y(y)}" for x, y in ln) + '" fill="none" stroke="#111" stroke-width="1.6"/>')
    for x, y in S["overlay"]["points"]:
        out.append(f'<circle cx="{X(x)}" cy="{Y(y)}" r="2.6" fill="#fff" stroke="#111" stroke-width="1"/>')
    ly = H + 22
    out.append(f'<text x="0" y="{ly + 8}" font-size="13" fill="#666">{lo}</text>')
    for j in range(60):
        out.append(f'<rect x="{24 + j * 3}" y="{ly}" width="3.2" height="9" fill="{ramp(j / 59)}"/>')
    out.append(f'<text x="212" y="{ly + 8}" font-size="13" fill="#666">{hi} · {V["label"]} · {V["note"]}</text>')
    out.append(f'<rect x="{W - 190}" y="{ly}" width="12" height="9" fill="#e6e6e3"/>'
               f'<text x="{W - 172}" y="{ly + 8}" font-size="13" fill="#666">no residents in 2011</text>')
    out.append(f'<text x="0" y="{ly + 30}" font-size="13" fill="#666">black: the metro and its stations as they ran 2012–2021</text>')
    out.append("</svg>")
    return "\n".join(out) + "\n"


def main() -> None:
    S = build()
    OUT.write_text(json.dumps(S, ensure_ascii=False, separators=(",", ":")) + "\n")
    SVG.write_text(svg(S))
    t = S["totals"]
    print(f"{OUT.name}: {OUT.stat().st_size / 1024:.0f} KB, {t['cells']} squares, {t['flats']} flats, "
          f"{t['flats'] / t['pop2011'] * 1000:.1f} per 1 000 residents of 2011; {SVG.name}: {SVG.stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    main()
