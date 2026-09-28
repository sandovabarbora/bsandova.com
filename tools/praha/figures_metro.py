"""Figures for part 2 (Prague votes in rings), drawn onto paper; accent = the ochre the article's photograph holds.

Reads tools/data/praha2/ (written by tools/praha/metro.py and its downloads) and assets/praha/metro2025.json;
writes SVGs to assets/praha/.

Usage:
    uv run --with matplotlib --with pandas --with shapely python tools/praha/figures_metro.py
"""

import json
import zipfile
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.collections import PatchCollection
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import Polygon as MPoly
from shapely.geometry import shape

from metro import metro_stations

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "tools" / "data" / "praha2"
DIR = ROOT / "assets" / "praha"
INK, GREY, LIGHT, GRID, HELD = "#111111", "#666666", "#b5b5b0", "#e6e6e3", "#9a7b0a"
RAMP = LinearSegmentedColormap.from_list("ochre", ["#f6f1dc", "#e0c25a", "#9a7b0a", "#4a3a04"])
plt.rcParams.update({
    "font.family": "monospace", "font.size": 9, "svg.fonttype": "none", "axes.edgecolor": GREY,
    "axes.labelcolor": GREY, "xtick.color": GREY, "ytick.color": GREY, "axes.spines.top": False,
    "axes.spines.right": False, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8,
    "axes.axisbelow": True, "figure.facecolor": "white", "axes.facecolor": "white",
})


def metro_lines() -> list[pd.DataFrame]:
    z = zipfile.ZipFile(RAW / "PID_GTFS.zip")
    routes = pd.read_csv(z.open("routes.txt"))
    trips = pd.read_csv(z.open("trips.txt"), usecols=["route_id", "shape_id"])
    trips = trips[trips.route_id.isin(routes[routes.route_type == 1].route_id)].dropna()
    shapes = pd.read_csv(z.open("shapes.txt"))
    shapes = shapes[shapes.shape_id.isin(set(trips.shape_id))]
    # the shape most trips of each line (A, B, C) follow: the full line, not a depot run or a short turn-back
    best = trips.groupby(["route_id", "shape_id"]).size().sort_values().groupby(level=0).tail(1).reset_index().shape_id
    return [shapes[shapes.shape_id == s].sort_values("shape_pt_sequence") for s in best]


def ano_map() -> None:
    g = json.loads((RAW / "okrsky_praha.geojson").read_text())
    d = pd.read_csv(RAW / "precincts.csv").set_index(["OBEC", "OKRSEK"])
    share = 100 * d.ANO / d.PL_HL_CELK
    patches, vals = [], []
    for f in g["features"]:
        k = (f["properties"]["momc"], f["properties"]["cislo"])
        if k not in share.index:
            continue
        geom = shape(f["geometry"]).simplify(0.00025, preserve_topology=True)
        for poly in getattr(geom, "geoms", [geom]):
            patches.append(MPoly(list(poly.exterior.coords), closed=True))
            vals.append(share[k])
    fig, ax = plt.subplots(figsize=(8, 5.6))
    pc = PatchCollection(patches, cmap=RAMP, edgecolor="white", linewidth=0.15)
    pc.set_array(pd.Series(vals).clip(8, 36).values)
    ax.add_collection(pc)
    for line in metro_lines():
        ax.plot(line.shape_pt_lon, line.shape_pt_lat, color=INK, lw=1.1, solid_capstyle="round")
    st = metro_stations()  # includes Flora, closed after the election
    ax.scatter(st.stop_lon, st.stop_lat, s=6, color="white", edgecolor=INK, linewidth=0.7, zorder=3)
    ax.set_aspect(1 / 0.643)  # cos(50.08°)
    ax.autoscale_view()
    ax.axis("off")
    cb = fig.colorbar(pc, ax=ax, fraction=0.025, pad=0.01)
    cb.set_label("ANO, % of valid votes", color=GREY)
    cb.outline.set_visible(False)
    fig.tight_layout()
    fig.savefig(DIR / "01-ano-map.svg")
    plt.close(fig)


def three_rulers(r: dict) -> None:
    """ANO and the Pirates by metro distance, by distance from the centre and by panel share, one y scale."""
    panels = [("by_metro_distance", "distance to the metro"), ("by_centre_distance", "distance from Můstek"),
              ("by_panel_share", "flats in panel buildings")]
    fig, axes = plt.subplots(1, 3, figsize=(8, 3.1), sharey=True)
    for ax, (key, title) in zip(axes, panels):
        bins = list(r[key])
        for party, col in [("ANO", HELD), ("Piráti", INK)]:
            ys = [100 * r[key][b][party] for b in bins]
            ax.plot(range(len(bins)), ys, color=col, lw=2, marker="o", ms=3.5)
            if key == panels[-1][0]:
                ax.text(len(bins) - 1, ys[-1] + (1.3 if party == "ANO" else -2.6), party, color=col, ha="right")
        ax.set_xticks(range(len(bins)), [b.replace(" km", "").replace(" %", "") for b in bins], fontsize=7.5)
        ax.set_title(title, loc="left", color=INK, fontsize=9)
        ax.set_ylim(0, 30)
        ax.grid(axis="x", visible=False)
    axes[0].set_ylabel("% of valid votes")
    axes[0].set_xlabel("km", fontsize=8)
    axes[1].set_xlabel("km", fontsize=8)
    axes[2].set_xlabel("%", fontsize=8)
    fig.tight_layout()
    fig.savefig(DIR / "02-three-rulers.svg")
    plt.close(fig)


def metro_json() -> None:
    """Metro lines and stations for the interactive map (coordinates rounded to ~10 m)."""
    lines = [[[round(x, 4), round(y, 4)] for x, y in zip(g.shape_pt_lon, g.shape_pt_lat)][::2] for g in metro_lines()]
    st = metro_stations()
    stations = [[round(x, 4), round(y, 4), n] for x, y, n in zip(st.stop_lon, st.stop_lat, st.stop_name)]
    (DIR / "metro_lines.json").write_text(json.dumps({"lines": lines, "stations": stations}, ensure_ascii=False,
                                                     separators=(",", ":")))


def main() -> None:
    DIR.mkdir(parents=True, exist_ok=True)
    metro_json()
    ano_map()
    three_rulers(json.loads((DIR / "metro2025.json").read_text()))
    print("wrote", ", ".join(p.name for p in sorted(DIR.glob("*.svg"))))


if __name__ == "__main__":
    main()
