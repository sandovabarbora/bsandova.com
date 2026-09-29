"""Interactive map of Part 3 (texts/prague-districts.html): Prague's 57 city districts, drawn by assets/map.js.

Reads:
  - tools/data/praha3x/ruian_momc.json: RÚIAN city-district boundaries (S-JTSK, EPSG:5514), as fetched by
    tools/praha/districts_data.py; joined to the data by the district code (kod).
  - assets/praha/districts.json (published by tools/praha/districts.py): residents at the end of 2024, spending per
    resident a year (2022–2024 mean) and the share of income from transfers.
  - the city's own in-year grants, recomputed exactly as tools/praha/districts_robust.py frame() does from
    tools/data/praha3x/grants.csv (city_own rows of the budget-measure lists, dated by resolution, annualised at the
    coalition cuts), divided by residents at the end of year r − 2 (mc_pop.xlsx), mean of the regime-years 2015–2023.
  - tools/data/praha3x/alignment/panel.csv (tools/praha/districts_alignment.py; no names): the registered alignment
    A on 30 June of 2015, 2019 and 2023, one year for each electoral term under its coalition.

Writes:
  - assets/praha/map-districts.json: the map spec for assets/map.js;
  - assets/praha/map-districts.svg: the static fallback, the default view (spending per resident) with a legend.

Usage:
    uv run --no-project --with pandas --with numpy --with openpyxl --with xlrd --with scipy --with pyproj \
        --with shapely python tools/maps/districts.py
"""

import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import shapely
from pyproj import Transformer
from shapely.geometry import Polygon
from shapely.ops import polylabel

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "praha"))
import districts_robust as rb  # noqa: E402

RAW = rb.x.RAW
OUT = ROOT / "assets" / "praha" / "map-districts.json"
SVG = ROOT / "assets" / "praha" / "map-districts.svg"
HELD = "#3f6b2a"  # the accent of the article's figures (assets/praha/03-per-head.svg, charts-districts.json)
TOL = 12.0  # m, coverage simplification (shared borders stay shared)
TERMS = {2015: "2014–18", 2019: "2018–22", 2023: "2022–26"}
CZK = {"dp": 0, "unit": " CZK"}


def grants_per_resident() -> pd.Series:
    """The city's own in-year grants per resident a year, mean of the regime-years 2015–2023 (zeros kept)."""
    y = rb.frame()
    assert y.r.min() == 2015 and y.r.max() == 2023 and len(y) == 57 * 9
    return y.groupby("district").total_pc.mean()


def geometry() -> dict[int, list]:
    src = json.loads((RAW / "ruian_momc.json").read_text())
    feats = src["features"]
    polys = [Polygon(f["geometry"]["rings"][0], f["geometry"]["rings"][1:]) for f in feats]
    simple = shapely.coverage_simplify(polys, TOL)
    tr = Transformer.from_crs(5514, 4326, always_xy=True)
    out = {}
    for f, p in zip(feats, simple):
        polys_ = list(p.geoms) if p.geom_type == "MultiPolygon" else [p]
        rings = []
        for q in polys_:
            for ring in [q.exterior, *q.interiors]:
                xs, ys = np.array(ring.coords).T
                lon, lat = tr.transform(xs, ys)
                pts = []
                for a, b in zip(lon, lat):
                    pt = [round(float(a), 4), round(float(b), 4)]
                    if not pts or pts[-1] != pt:
                        pts.append(pt)
                rings.append(pts[:-1] if pts[0] == pts[-1] else pts)
        pl = polylabel(max(polys_, key=lambda q: q.area), tolerance=5.0)  # in metres, then to lon/lat
        lx, ly = tr.transform(pl.x, pl.y)
        out[f["attributes"]["kod"]] = {"rings": rings, "label": [round(lx, 4), round(ly, 4)]}
    return out


def ramp(t: float) -> str:
    """map.js rampOf(held, 'seq')."""
    h = [int(HELD[i:i + 2], 16) for i in (1, 3, 5)]
    w, k = [246, 244, 238], [17, 17, 17]
    mix = lambda a, b, s: [round(v + (b[i] - v) * s) for i, v in enumerate(a)]  # noqa: E731
    stops = [w, mix(h, w, 0.55), h, mix(h, k, 0.45)]
    u = max(0.0, min(1.0, t)) * 3
    i = min(2, int(u))
    return "rgb({},{},{})".format(*mix(stops[i], stops[i + 1], u - i))


def fmt(v: float, f: dict) -> str:
    x = v * 100 if f.get("pct") else v
    s = f"{abs(x):,.{f.get('dp', 0)}f}".replace(",", " ")
    return ("−" if x < 0 else "") + s + (" %" if f.get("pct") else f.get("unit", ""))


def static_svg(spec: dict) -> str:
    """The default view with map.js's projection (equirectangular at 50.08°, 900 wide) and a legend under it."""
    V = spec["views"][0]
    xs = [p[0] for f in spec["features"] for r in f["r"] for p in r]
    ys = [p[1] for f in spec["features"] for r in f["r"] for p in r]
    k, W = 1 / np.cos(np.radians(50.08)), 900
    s = W / (max(xs) - min(xs))
    H = round((max(ys) - min(ys)) * k * s)
    X = lambda x: round((x - min(xs)) * s, 1)  # noqa: E731
    Y = lambda y: round((max(ys) - y) * k * s, 1)  # noqa: E731
    lo, hi = V["domain"]
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H + 56}" font-family="JetBrains Mono, monospace">',
           f'<rect width="{W}" height="{H + 56}" fill="#fff"/>']
    for f in spec["features"]:
        v = f["v"][V["key"]]
        fill = "#e6e6e3" if v is None else ramp((v - lo) / (hi - lo))
        d = "".join("M" + "L".join(f"{X(a)},{Y(b)}" for a, b in r) + "Z" for r in f["r"])
        out.append(f'<path d="{d}" fill="{fill}" stroke="#fff" stroke-width="0.8"/>')
    for lb in spec["overlay"]["labels"]:
        out.append(f'<text x="{X(lb["at"][0])}" y="{Y(lb["at"][1]) + 3.5}" text-anchor="middle" font-size="10" fill="#111" '
                   f'stroke="#fff" stroke-width="3" paint-order="stroke">{lb["s"]}</text>')
    gy = H + 22
    out.append('<defs><linearGradient id="g">' + "".join(
        f'<stop offset="{t}" stop-color="{ramp(t)}"/>' for t in (0, 0.25, 0.5, 0.75, 1)) + "</linearGradient></defs>")
    a, b = fmt(lo, V["fmt"]), fmt(hi, V["fmt"]) + " · " + V["label"] + " · " + V["note"]
    x0 = 8 * len(a) + 8
    out.append(f'<text x="0" y="{gy + 8}" font-size="11" fill="#666">{a}</text>')
    out.append(f'<rect x="{x0}" y="{gy}" width="180" height="8" fill="url(#g)"/>')
    out.append(f'<text x="{x0 + 188}" y="{gy + 8}" font-size="11" fill="#666">{b}</text>')
    out.append("</svg>")
    return "\n".join(out) + "\n"


def main() -> None:
    districts = json.loads((ROOT / "assets" / "praha" / "districts.json").read_text())["districts"]
    geo = geometry()
    grants = grants_per_resident()
    panel = pd.read_csv(RAW / "alignment" / "panel.csv")
    aligned = panel[panel.r.isin(TERMS)].pivot(index="district", columns="r", values="A")
    assert len(districts) == len(geo) == 57 and set(grants.index) == {d["district"] for d in districts}
    feats = []
    for d in districts:
        n = d["district"]
        v = {"spend": d["per_head"], "transfers": d["income_transfers"], "grants": round(float(grants[n]))}
        for r, term in TERMS.items():
            a = aligned.loc[n, r]
            v[f"al{r}"] = None if pd.isna(a) else int(a)
        feats.append({"id": d["code"], "name": n, "sub": f"{d['population']:,}".replace(",", " ") + " residents",
                      "r": geo[d["code"]]["rings"], "v": v})
    labels = [{"at": geo[d["code"]]["label"], "s": d["district"].split()[1]}
              for d in districts if re.fullmatch(r"Praha \d+", d["district"])]
    views = [
        {"key": "spend", "label": "spent per resident", "fmt": CZK, "scale": "seq", "domain": [7000, 36000],
         "note": "a year, 2022–24"},
        {"key": "transfers", "label": "from transfers", "fmt": {"dp": 0, "pct": True}, "scale": "seq",
         "domain": [0.35, 0.95], "note": "of income, 2022–24"},
        {"key": "grants", "label": "city grants per resident", "fmt": CZK, "scale": "seq", "domain": [0, 22000],
         "note": "a year, 2015–23"},
    ] + [{"key": f"al{r}", "label": f"coalition mayor {term}", "fmt": {"dp": 0}, "scale": "seq",
          "domain": [0, 1], "note": f"30 June {r}", "cats": [{"v": 0, "label": "not in the coalition"}, {"v": 1, "label": "in the city coalition"}]}
         for r, term in TERMS.items()]
    spec = {"held": HELD, "features": feats, "views": views, "overlay": {"labels": labels},
            "note": "Praha 1–22 numbered.", "data": ["../assets/praha/districts.json", "../assets/praha/map-districts.json"]}
    OUT.write_text(json.dumps(spec, ensure_ascii=False, separators=(",", ":")) + "\n")
    SVG.write_text(static_svg(spec))
    # spot checks against the article
    by = {f["name"]: f["v"] for f in feats}
    s = pd.Series({k: v["spend"] for k, v in by.items()})
    print("spend median", s.median(), "Praha 1", by["Praha 1"]["spend"], "Praha 4", by["Praha 4"]["spend"],
          "large range", s[[n for n in s.index if re.fullmatch(r"Praha \d+", n) and
                            next(d for d in districts if d["district"] == n)["population"] > 40000]].agg(["min", "max"]).tolist())
    print("transfers median", pd.Series({k: v["transfers"] for k, v in by.items()}).median())
    print("aligned counts", {r: int(sum(v[f"al{r}"] or 0 for v in by.values())) for r in TERMS},
          "2022:", int(panel[panel.r == 2022].A.sum()))
    print("grants median CZK/resident", grants.median().round(), "size KB", round(OUT.stat().st_size / 1024))


if __name__ == "__main__":
    main()
