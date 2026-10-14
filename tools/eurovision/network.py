"""Data for the animated vote network of the Eurovision article: which pairs of countries gave each other far more of
their final points than an even split would, over the five contests up to each year, 1979–2025. A description drawn
from the article's vote table, not a registered estimate.

Reads tools/data/eurovision/h3.parquet (share of its final points each voter gave each performer) and the Natural Earth
countries for positions and the base; writes assets/eurovision/network.json for assets/eurovision/network.js and 05-network.svg, its fallback.

    uv run --no-project --with pandas --with pyarrow --with shapely python tools/eurovision/network.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
from shapely.geometry import box, shape

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from article import NAMES  # noqa: E402

D = ROOT / "tools/data/eurovision"
OUT = ROOT / "assets/eurovision/network.json"
FRAME = box(-25, 29, 50, 71)
WINDOW, MIN_SEEN, RATIO = 5, 3, 3.0  # contests per window; contests a direction must be seen in; times an even share
PLACE = {"AU": (-18.0, 33.0), "YU": (20.5, 44.0), "CS": (20.5, 44.0), "MA": (-6.5, 33.0),  # off-map or former states
         "RU": (37.6, 55.8)}  # Moscow: the centre of Russia lies far outside the map
ISO = {"GB": "GB", "YU": "RS", "CS": "RS"}


def positions() -> tuple[dict, list]:
    geo = json.loads((D / "geo/ne_50m_admin_0_countries.geojson").read_text(encoding="utf-8"))
    pos, base = {}, []
    for f in geo["features"]:
        code = f["properties"].get("ISO_A2_EH") or f["properties"].get("ISO_A2")
        g = shape(f["geometry"])
        clipped = g.intersection(FRAME).simplify(0.05, preserve_topology=True)
        if not clipped.is_empty:
            for p in getattr(clipped, "geoms", [clipped]):
                if p.geom_type == "Polygon" and p.area > 0.05:
                    base.append([[round(x, 2), round(y, 2)] for x, y in p.exterior.coords])
        if code:
            main = max(getattr(g, "geoms", [g]), key=lambda p: p.area)  # the mainland, not overseas islands
            pt = main.representative_point()
            pos[code] = (round(pt.x, 2), round(pt.y, 2))
    return pos, base


def windows(h3: pd.DataFrame) -> dict[int, pd.DataFrame]:
    f = h3[h3["r"] == "final"].copy()
    n = f.groupby(["year", "i"])["j"].transform("count")
    f["ratio"] = f["share"] * n  # 1 is an even split of a voter's points over the performers it could vote for
    years = sorted(f["year"].unique())
    out = {}
    for k in range(WINDOW - 1, len(years)):
        span = years[k - WINDOW + 1:k + 1]
        w = f[f["year"].isin(span)].groupby(["i", "j"])["ratio"].agg(["mean", "count"]).reset_index()
        w = w[w["count"] >= MIN_SEEN]
        both = w.merge(w, left_on=["i", "j"], right_on=["j", "i"], suffixes=("", "_back"))
        both = both[both["i"] < both["j"]]
        both["mutual"] = (both["mean"] + both["mean_back"]) / 2
        out[int(years[k])] = both[both["mutual"] >= RATIO][["i", "j", "mutual"]]
    return out


def static(nodes: dict, base: list, links: list, path: Path) -> None:
    """The fallback image: the last window's arcs."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    f, ax = plt.subplots(figsize=(7.2, 5.6))
    for ring in base:
        ax.fill([x for x, _ in ring], [y for _, y in ring], color="#f3f2ee", ec="white", lw=0.6)
    for a, b, r in links:
        (x1, y1), (x2, y2) = (nodes[a]["x"], nodes[a]["y"]), (nodes[b]["x"], nodes[b]["y"])
        ax.plot([x1, x2], [y1, y2], color="#c0503f", lw=1 + r / 2, alpha=0.75)
        for c in (a, b):
            ax.text(nodes[c]["x"], nodes[c]["y"] + 0.6, nodes[c]["name"], fontsize=6, ha="center")
    ax.set_xlim(-25, 50)
    ax.set_ylim(29, 71)
    ax.set_aspect(1.6)
    ax.axis("off")
    f.tight_layout()
    f.savefig(path)
    plt.close(f)


def main() -> None:
    h3 = pd.read_parquet(D / "h3.parquet")
    pos, base = positions()
    ws = windows(h3)
    codes = sorted(set(h3["i"]) | set(h3["j"]))
    nodes = {}
    for c in codes:
        p = PLACE.get(c) or pos.get(ISO.get(c, c))
        if p:
            nodes[c] = {"name": NAMES.get(c, c), "x": p[0], "y": p[1]}
    years = sorted(ws)
    frames, notes = [], []
    for y in years:
        links = [[r.i, r.j, round(float(r.mutual), 2)] for r in ws[y].itertuples() if r.i in nodes and r.j in nodes]
        frames.append(links)
        top = max(links, key=lambda l: l[2]) if links else None
        notes.append(f"{len(links)} pairs over {RATIO:g}× an even share, five contests to {y}"
                     + (f" · strongest: {nodes[top[0]]['name']} and {nodes[top[1]]['name']}, {top[2]:.1f}×" if top else ""))
    active = [sorted({c for l in fr for c in l[:2]}) for fr in frames]
    static(nodes, base, frames[-1], OUT.with_name("05-network.svg"))
    OUT.write_text(json.dumps({"years": years, "nodes": nodes, "frames": frames, "active": active, "notes": notes,
                               "base": base, "ratio": RATIO}, ensure_ascii=False, separators=(",", ":")))
    print(len(years), "years;", len(nodes), "countries;", OUT.stat().st_size // 1024, "kB")


if __name__ == "__main__":
    main()
