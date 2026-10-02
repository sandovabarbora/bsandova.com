"""Pop, measured: a world map per part, assets/pop/<slug>/map.svg.

Countries are shaded by Q2, the focal song's days in the national chart against the country's median number one:
blue where it lasted longer, warm grey where shorter, pale where it never charted. Circles mark Q5, the average
ticket in days of the country's income, at the country's label point. Czechia is outlined. Each shape carries its
values in a <title>, read by assets/pop/pop.js for the hover label.

Borders: Natural Earth 1:50m admin-0 countries (public domain), tools/data/maps/ne_50m_admin_0_countries.geojson,
simplified and drawn in the Equal Earth projection.

    uv run --with shapely python tools/pop/maps.py
"""

from __future__ import annotations

import csv
import html
import json
import math
from pathlib import Path

from shapely.geometry import shape

ROOT = Path(__file__).resolve().parents[2]
R = ROOT / "docs" / "research"
GEO = ROOT / "tools" / "data" / "maps" / "ne_50m_admin_0_countries.geojson"
ARTISTS = ["harry-styles", "taylor-swift", "bts", "bad-bunny", "billie-eilish"]
W, H = 960, 470
BLUES = ["#d9e2ef", "#b4c6de", "#8aa6cb", "#5f82b2", "#34507c", "#1f3352"]
GREYS = ["#e7e2d8", "#d3cbbb", "#b9ae98"]
NONE = "#f2f1ed"


def equal_earth(lon: float, lat: float) -> tuple[float, float]:
    """Šavrič, Patterson and Jenny's Equal Earth projection, unit sphere."""
    a1, a2, a3, a4 = 1.340264, -0.081106, 0.000893, 0.003796
    m = math.sqrt(3) / 2
    t = math.asin(m * math.sin(math.radians(lat)))
    t2, t6 = t * t, t ** 6
    x = 2 * math.sqrt(3) * math.radians(lon) * math.cos(t) / (3 * (9 * a4 * t6 * t2 + 7 * a3 * t6 + 3 * a2 * t2 + a1))
    y = t * (a4 * t6 * t2 + a3 * t6 + a2 * t2 + a1)
    return x, y


XMAX = equal_earth(180, 0)[0]
YMAX = equal_earth(0, 90)[1]


def px(lon: float, lat: float) -> tuple[float, float]:
    x, y = equal_earth(lon, lat)
    s = (W / 2) / XMAX
    return W / 2 + x * s, H / 2 - y * s * 1.0 + 18


def ring(coords) -> str:
    pts = [px(lon, lat) for lon, lat in coords]
    return "M" + "L".join(f"{x:.1f},{y:.1f}" for x, y in pts) + "Z"


def path_d(geom) -> str:
    polys = [geom] if geom.geom_type == "Polygon" else list(geom.geoms)
    out = []
    for p in polys:
        if p.area < 0.05:          # drop specks below about 0.05 square degrees
            continue
        out.append(ring(p.exterior.coords))
        out.extend(ring(i.coords) for i in p.interiors)
    return "".join(out)


def shade(ratio: float | None) -> str:
    if ratio is None:
        return NONE
    if ratio >= 1:
        k = min(len(BLUES) - 1, int(math.log2(ratio)))           # 1–2×, 2–4×, … , 32× and more
        return BLUES[k]
    k = min(len(GREYS) - 1, int(-math.log2(ratio)))              # 0.5–1×, 0.25–0.5×, less
    return GREYS[k]


def countries() -> list[dict]:
    data = json.loads(GEO.read_text())
    out = []
    for f in data["features"]:
        p = f["properties"]
        if p["CONTINENT"] == "Antarctica":
            continue
        g = shape(f["geometry"]).simplify(0.12, preserve_topology=True)
        out.append({"iso2": p["ISO_A2_EH"].lower(), "iso3": p["ISO_A3_EH"], "name": p["NAME_EN"],
                    "d": path_d(g), "label": px(p["LABEL_X"], p["LABEL_Y"]), "area": shape(f["geometry"]).area})
    return out


def legend() -> str:
    keys = [(GREYS[2], "under ¼×"), (GREYS[1], "¼–½×"), (GREYS[0], "½–1×"), (BLUES[0], "1–2×"), (BLUES[1], "2–4×"),
            (BLUES[2], "4–8×"), (BLUES[3], "8–16×"), (BLUES[4], "16× +"), (NONE, "not in the chart")]
    x, y, out = 14, H - 22, []
    for c, t in keys:
        out.append(f'<rect x="{x}" y="{y - 9}" width="12" height="10" fill="{c}" stroke="#bbb" stroke-width=".4"/>'
                   f'<text x="{x + 16}" y="{y}">{t}</text>')
        x += 22 + 6.1 * len(t)
    out.append(f'<circle cx="{x + 8}" cy="{y - 4}" r="5" fill="none" stroke="#c2410c" stroke-width="1.4"/>'
               f'<text x="{x + 18}" y="{y}">ticket, days of income</text>')
    return "".join(out)


def draw(slug: str, shapes: list[dict]) -> str:
    q2 = {r["country"]: r for r in csv.DictReader(open(R / f"{slug}-countries.csv", encoding="utf-8"))}
    res = json.loads((R / f"{slug}-results.json").read_text())
    tickets = {c["iso3"]: c for c in res["q5"].get("countries", [])}
    focal = next(p for p in res["q1"]["own"] if p["focal"])["label"].split(" - ", 1)[1]
    # several features can share a code (Australia's small island territories): a circle goes on the largest
    main = {}
    for s in shapes:
        if s["iso3"] not in main or s["area"] > main[s["iso3"]]["area"]:
            main[s["iso3"]] = s
    paths, dots = [], []
    for s in shapes:
        r = q2.get(s["iso2"])
        ratio = None
        if r and r["ones_days"]:
            ones = sorted(int(x) for x in r["ones_days"].split())
            med = (ones[len(ones) // 2] + ones[(len(ones) - 1) // 2]) / 2
            ratio = int(r["focal_days"]) / med if med else None
        t = tickets.get(s["iso3"])
        tip = s["name"] + (f" · {focal}: {int(r['focal_days'])} days, {ratio:.2f}× the median number one" if ratio else
                           " · not in the chart")
        if t:
            tip += f" · ticket ${t['price_usd']:.0f}, {t['days_of_income']:.1f} days of income"
        cz = ' stroke="#111" stroke-width="1.3"' if s["iso2"] == "cz" else ""
        paths.append(f'<path d="{s["d"]}" fill="{shade(ratio)}"{cz}><title>{html.escape(tip)}</title></path>')
        if t and main[s["iso3"]] is s:
            x, y = s["label"]
            dots.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{2.6 * math.sqrt(t["days_of_income"]) + 1.5:.1f}" '
                        f'fill="rgba(194,65,12,.12)" stroke="#c2410c" stroke-width="1.2"><title>{html.escape(tip)}</title></circle>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" role="img" '
            f'aria-label="World map: where {html.escape(focal)} lasted longer than local number ones, and ticket prices in days of income">'
            f'<style>path{{stroke:#fff;stroke-width:.5}}text{{font:400 10px "JetBrains Mono",monospace;fill:#666}}</style>'
            f'<g>{"".join(paths)}</g><g>{"".join(dots)}</g><g>{legend()}</g></svg>')


def main() -> None:
    shapes = countries()
    for slug in ARTISTS:
        out = ROOT / "assets" / "pop" / slug / "map.svg"
        out.write_text(draw(slug, shapes), encoding="utf-8")
        print(slug, f"{out.stat().st_size // 1024} kB")


if __name__ == "__main__":
    main()
