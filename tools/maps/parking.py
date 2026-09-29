"""Interactive map for Part 6 (texts/prague-parking.html): Prague's paid parking zones on a 450 m grid.

    uv run --no-project --with numpy --with pyproj python tools/maps/parking.py

Reads
- tools/data/parking6/zps_layer3_snapshot_20260928.json: the city's segment layer (ArcGIS MapServer/3, S-JTSK) as
  snapshotted for Part 6 by tools/parking6/parking6_design.py (layer3). Fields used: PS_ZPS (administrative stalls),
  SHAPE.AREA (m²), TYPZONY (1 resident, 2 mixed, 3 visitor, 7 other regulation), KODMC_T (district), the rings.
- tools/parking6/parking6_design.py: band_width() and classify(), the article's band-width classifier, imported as is.
- assets/praha/metro_lines.json: metro lines and stations, drawn over the map.

Writes
- assets/parking6/map-zones.json: the spec for assets/map.js (one feature per 450 m grid cell holding a segment).
- assets/parking6/map-zones.svg: the static fallback, the default view (stalls) with the same geometry and a legend.

Every segment goes to the cell that holds the centroid of its largest ring, on a 450 m grid in UTM 33N (north-aligned
in Prague). The parallel share is Part 6's ratio estimator at its central values (tools/parking6/parking6_estimate.py,
e1: s = (par·PPV_par + non·(1 − PPV_non) + unc·p_u) / all, with PPV_par 0.9909, PPV_non 0.9575, p_u 0.25), which gives
the article's 59 % for the whole city. Area per stall is gross segment area over administrative stalls, as fig. 13.
No register file is read.
"""
from __future__ import annotations

import json
import math
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from pyproj import Transformer

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/parking6"))
from parking6_design import band_width, classify  # noqa: E402

SNAP = ROOT / "tools/data/parking6/zps_layer3_snapshot_20260928.json"
METRO = ROOT / "assets/praha/metro_lines.json"
OUT_JSON = ROOT / "assets/parking6/map-zones.json"
OUT_SVG = ROOT / "assets/parking6/map-zones.svg"

GRID_M = 450
MIN_STALLS = 10                      # ratios are left blank in cells with fewer stalls than this
PPV_PAR, PPV_NON, P_UNC = 0.9909, 0.9575, 0.25   # central values, parking6_estimate.py e1 (cen)
HELD = "#34507c"
# the one cell in Praha 16 (Radotín, one segment, 18 visitor stalls) lies 4 km south of the rest of the zones; drawn,
# it would add a third to the map's height with nothing in between, so it is left off and the caption says so
OFF_MAP_SOUTH_OF = 50.0                     # tools/parking6/figures.py HELD

to_utm = Transformer.from_crs("EPSG:5514", "EPSG:32633", always_xy=True)
to_wgs = Transformer.from_crs("EPSG:32633", "EPSG:4326", always_xy=True)


def centroid(ring: np.ndarray) -> tuple[float, float]:
    # relative to the first vertex: S-JTSK coordinates near 10^6 m lose about a metre in the shoelace products
    ox, oy = ring[0]
    x, y = ring[:, 0] - ox, ring[:, 1] - oy
    c = x[:-1] * y[1:] - x[1:] * y[:-1]
    a = c.sum() / 2
    if abs(a) < 1e-9:
        return float(x.mean() + ox), float(y.mean() + oy)
    return float(((x[:-1] + x[1:]) * c).sum() / (6 * a) + ox), float(((y[:-1] + y[1:]) * c).sum() / (6 * a) + oy)


def build() -> dict:
    feats = json.loads(SNAP.read_text())["features"]
    cells: dict[tuple[int, int], dict] = defaultdict(lambda: {"n": 0, "st": 0, "area": 0.0, "par": 0.0, "non": 0.0,
                                                               "unc": 0.0, "typ": defaultdict(int), "mc": defaultdict(int)})
    tot = {"n": 0, "st": 0, "area": 0.0, "par": 0.0, "non": 0.0, "unc": 0.0, "typ": defaultdict(int)}
    mc_tot: dict[str, list[float]] = defaultdict(lambda: [0.0, 0])
    for f in feats:
        a = f["attributes"]
        st = int(a.get("PS_ZPS") or 0)
        area = float(a.get("SHAPE.AREA") or 0)
        rings = (f.get("geometry") or {}).get("rings") or []
        tot["n"] += 1; tot["st"] += st; tot["area"] += area; tot["typ"][a["TYPZONY"]] += st
        mc_tot[a["KODMC_T"]][0] += area; mc_tot[a["KODMC_T"]][1] += st
        if not rings:
            raise SystemExit(f"segment {a['OBJECTID']} has no geometry")
        ring = np.array(max(rings, key=len), float)
        e, n = to_utm.transform(*centroid(ring))
        c = cells[(math.floor(e / GRID_M), math.floor(n / GRID_M))]
        c["n"] += 1; c["st"] += st; c["area"] += area; c["typ"][a["TYPZONY"]] += st; c["mc"][a["KODMC_T"]] += st or 0
        c["mc"][a["KODMC_T"]] += 1e-6            # a zero-stall cell still gets a district
        if st:                                   # as parking6_estimate.snapshot_classes
            _, _, w = band_width(ring)
            k = {"parallel": "par", "non_parallel": "non", "unclassified": "unc"}[classify(w)]
            c[k] += st; tot[k] += st

    metro = json.loads(METRO.read_text())
    stations = metro["stations"]
    features, off_map = [], []
    for (i, j), c in sorted(cells.items(), key=lambda kv: (-kv[0][1], kv[0][0])):
        corners = [(i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1), (i, j)]
        lon, lat = to_wgs.transform([p[0] * GRID_M for p in corners], [p[1] * GRID_M for p in corners])
        ring = [[round(x, 4), round(y, 4)] for x, y in zip(lon, lat)]
        clon, clat = to_wgs.transform((i + 0.5) * GRID_M, (j + 0.5) * GRID_M)
        near = min(stations, key=lambda s: (s[0] - clon) ** 2 * math.cos(math.radians(50.08)) ** 2 + (s[1] - clat) ** 2)
        dist = math.hypot((near[0] - clon) * 111_320 * math.cos(math.radians(clat)), (near[1] - clat) * 110_570)
        st = c["st"]
        ok = st >= MIN_STALLS
        s_par = (c["par"] * PPV_PAR + c["non"] * (1 - PPV_NON) + c["unc"] * P_UNC) / st if ok else None
        v = {
            "stalls": st,
            "m2": round(c["area"] / st, 2) if ok else None,
            "par": round(s_par, 4) if ok else None,
            "res": round(c["typ"]["1"] / st, 4) if ok else None,
            "mix": round(c["typ"]["2"] / st, 4) if ok else None,
            "vis": round(c["typ"]["3"] / st, 4) if ok else None,
        }
        mc = max(c["mc"], key=c["mc"].get)
        r100 = round(dist / 100) * 100
        dtxt = f"{r100} m" if r100 < 1000 else f"{dist / 1000:.1f} km"
        feat = {"id": f"E{i}N{j}", "name": mc,
                "sub": f"{c['n']} segment{'s' if c['n'] > 1 else ''} · metro {near[2]}, {dtxt}", "r": [ring], "v": v}
        if clat < OFF_MAP_SOUTH_OF:
            off_map.append(feat)
            continue
        features.append(feat)

    # metro, clipped to the map's extent plus a margin, so lines do not run off into the far suburbs
    xs = [p[0] for f in features for p in f["r"][0]]; ys = [p[1] for f in features for p in f["r"][0]]
    m = 0.004
    inside = lambda p: min(xs) - m <= p[0] <= max(xs) + m and min(ys) - m <= p[1] <= max(ys) + m
    lines = []
    for ln in metro["lines"]:
        run = []
        for p in ln:
            if inside(p):
                run.append(p)
            elif run:
                if len(run) > 1: lines.append(run)
                run = []
        if len(run) > 1: lines.append(run)
    points = [[s[0], s[1]] for s in stations if inside(s)]

    pct = {"dp": 0, "pct": True}
    nb = "\u00a0"
    num = lambda x, dp=0: f"{x:,.{dp}f}".replace(",", nb)                  # the article's 1 234 and 0.7 %
    city_s = (tot["par"] * PPV_PAR + tot["non"] * (1 - PPV_NON) + tot["unc"] * P_UNC) / tot["st"]
    share = lambda code, dp=0: f"city {num(100 * tot['typ'][code] / tot['st'], dp)}{nb}%"
    top = max(f["v"]["stalls"] for f in features)
    spec = {
        "held": HELD,
        "features": features,
        "views": [
            {"key": "stalls", "label": "stalls", "fmt": {"dp": 0}, "scale": "seq", "domain": [0, 1000],
             "note": f"per 450 m cell, up to {num(top)}"},
            {"key": "m2", "label": "area per stall", "fmt": {"dp": 1, "unit": nb + "m²"}, "scale": "seq",
             "domain": [12, 17], "note": f"gross; city {num(tot['area'] / tot['st'], 1)}{nb}m²"},
            {"key": "par", "label": "parallel share", "fmt": pct, "scale": "seq", "domain": [0, 1],
             "note": f"band-width rule; city {num(100 * city_s)}{nb}%"},
            {"key": "res", "label": "resident share", "fmt": pct, "scale": "seq", "domain": [0, 1], "note": share("1")},
            {"key": "mix", "label": "mixed share", "fmt": pct, "scale": "seq", "domain": [0, 1], "note": share("2")},
            {"key": "vis", "label": "visitor share", "fmt": {"dp": 1, "pct": True}, "scale": "seq", "domain": [0, 0.5],
             "note": share("3", 1)},
        ],
        "overlay": {"lines": lines, "points": points},
        "note": f"Hatched: cells with fewer than {MIN_STALLS} stalls, where the ratios are left blank. Left off the map: "
                + "; ".join(f"{f['name']}, {f['v']['stalls']} stalls" for f in off_map) + ".",
        "data": ["../assets/parking6/map-zones.json"],
    }

    # ---- spot checks against the article -----------------------------------------------------------------
    s_city = (tot["par"] * PPV_PAR + tot["non"] * (1 - PPV_NON) + tot["unc"] * P_UNC) / tot["st"]
    fs = sum(f["v"]["stalls"] for f in features)
    print(f"segments {tot['n']} (article 16 874) · stalls {tot['st']} (article 168 424) · stalls on map {fs}")
    print(f"classes par {tot['par']:.0f} non {tot['non']:.0f} unc {tot['unc']:.0f} (e1.json 96 316 / 67 893 / 4 215)")
    print(f"parallel share, central estimator {s_city:.4f} (article 59 %)")
    print(f"area per stall {tot['area'] / tot['st']:.3f} m² (fig. 13 city mean 14.25)")
    print("by type", dict(tot["typ"]), {k: round(v / tot["st"], 4) for k, v in tot["typ"].items()})
    print("by district (fig. 13):", {k: round(a / s, 2) for k, (a, s) in mc_tot.items() if s >= 1000})
    print("left off the map:", [(f["name"], f["v"]["stalls"]) for f in off_map])
    print(f"cells {len(features)}, of which < {MIN_STALLS} stalls: {sum(1 for f in features if f['v']['stalls'] < MIN_STALLS)}")
    for key in ("stalls", "m2", "par", "res", "vis"):
        vals = sorted(f["v"][key] for f in features if f["v"][key] is not None)
        print(key, "quantiles 2/10/50/90/98:", [vals[int(q * (len(vals) - 1))] for q in (0.02, 0.1, 0.5, 0.9, 0.98)], "max", vals[-1])
    return spec


# ---- static fallback, same projection as assets/map.js -----------------------------------------------------
def ramp(t: float) -> str:
    h = [int(HELD[k:k + 2], 16) for k in (1, 3, 5)]
    W, K = [246, 244, 238], [17, 17, 17]
    mix = lambda a, b, u: [round(x + (y - x) * u) for x, y in zip(a, b)]
    stops = [W, mix(h, W, 0.55), h, mix(h, K, 0.45)]
    u = max(0.0, min(1.0, t)) * 3
    i = min(2, int(u))
    c = mix(stops[i], stops[i + 1], u - i)
    return "#%02x%02x%02x" % tuple(c)


def svg(spec: dict) -> str:
    lat0 = 50.08
    k = 1 / math.cos(math.radians(lat0))
    W = 900
    pts = [p for f in spec["features"] for r in f["r"] for p in r]
    x0, x1 = min(p[0] for p in pts), max(p[0] for p in pts)
    y0, y1 = min(p[1] for p in pts), max(p[1] for p in pts)
    s = W / (x1 - x0)
    H = round((y1 - y0) * k * s)
    X = lambda x: f"{(x - x0) * s:.1f}"
    Y = lambda y: f"{(y1 - y) * k * s:.1f}"
    V = spec["views"][0]
    lo, hi = V["domain"]
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H + 44}" font-family="JetBrains Mono, monospace">',
           f'<rect width="{W}" height="{H + 44}" fill="#fff"/>', '<g stroke="#fff" stroke-width="0.5">']
    for f in spec["features"]:
        d = "".join("M" + "L".join(f"{X(a)},{Y(b)}" for a, b in r) + "Z" for r in f["r"])
        x = f["v"][V["key"]]
        out.append(f'<path d="{d}" fill="{ramp((x - lo) / (hi - lo)) if x is not None else "#e6e6e3"}"/>')
    out.append('</g><g fill="none" stroke="#111" stroke-width="1.6">')
    for ln in spec["overlay"]["lines"]:
        out.append('<path d="M' + "L".join(f"{X(a)},{Y(b)}" for a, b in ln) + '"/>')
    out.append('</g><g fill="#fff" stroke="#111" stroke-width="1">')
    for a, b in spec["overlay"]["points"]:
        out.append(f'<circle cx="{X(a)}" cy="{Y(b)}" r="2.6"/>')
    out.append("</g>")
    gy = H + 16
    out.append('<defs><linearGradient id="g">' + "".join(
        f'<stop offset="{t}" stop-color="{ramp(t)}"/>' for t in (0, 0.25, 0.5, 0.75, 1)) + "</linearGradient></defs>")
    out.append(f'<text x="0" y="{gy + 8}" font-size="11" fill="#666">{lo}</text>')
    out.append(f'<rect x="22" y="{gy}" width="180" height="8" fill="url(#g)"/>')
    top = f"{hi:,}".replace(",", "\u00a0")
    out.append(f'<text x="210" y="{gy + 8}" font-size="11" fill="#666">{top}+ · administrative stalls per 450 m cell · '
               'black: metro</text>')
    out.append("</svg>")
    return "\n".join(out)


def main() -> None:
    spec = build()
    OUT_JSON.write_text(json.dumps(spec, ensure_ascii=False, separators=(",", ":")))
    OUT_SVG.write_text(svg(spec))
    print(f"{OUT_JSON.relative_to(ROOT)} {OUT_JSON.stat().st_size / 1024:.0f} KB · {OUT_SVG.relative_to(ROOT)} "
          f"{OUT_SVG.stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    main()
