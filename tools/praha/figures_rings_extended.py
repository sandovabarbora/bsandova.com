"""Figures for Part 2, the long version, drawn onto paper; accent = the ochre the Part 2 photograph holds.

Reads assets/praha/rings_extended.json and rings_robust.json; writes SVGs to assets/praha/.

Usage:
    uv run --with matplotlib python tools/praha/figures_rings_extended.py
"""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[2]
DIR = ROOT / "assets" / "praha"
INK, GREY, LIGHT, GRID, HELD = "#111111", "#666666", "#b5b5b0", "#e6e6e3", "#9a7b0a"
plt.rcParams.update({
    "font.family": "monospace", "font.size": 9, "svg.fonttype": "none", "axes.edgecolor": GREY,
    "axes.labelcolor": GREY, "xtick.color": GREY, "ytick.color": GREY, "axes.spines.top": False,
    "axes.spines.right": False, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8,
    "axes.axisbelow": True, "figure.facecolor": "white", "axes.facecolor": "white",
})


def attenuation(e: dict, r: dict) -> None:
    """Panel slope before and after composition, ANO and SPOLU, 2025 and 2021."""
    rows = [
        ("ANO 2025", e["H1_ANO"]["beta0_per10pp"], e["H1_ANO"]["beta1_per10pp"], e["H1_ANO"]["theta"]),
        ("ANO 2025, + age", e["H1_ANO_with_age"]["beta0_per10pp"], e["H1_ANO_with_age"]["beta1_per10pp"],
         e["H1_ANO_with_age"]["theta"]),
        ("ANO 2021", r["H5_2021"]["ANO"]["beta0"], r["H5_2021"]["ANO"]["beta1"], r["H5_2021"]["ANO"]["theta"]),
        ("SPOLU 2025", e["H1_SPOLU"]["beta0_per10pp"], e["H1_SPOLU"]["beta1_per10pp"], e["H1_SPOLU"]["theta"]),
        ("SPOLU 2021", r["H5_2021"]["SPOLU"]["beta0"], r["H5_2021"]["SPOLU"]["beta1"], r["H5_2021"]["SPOLU"]["theta"]),
    ]
    fig, ax = plt.subplots(figsize=(8, 3.3))
    for i, (lab, b0, b1, th) in enumerate(rows[::-1]):
        half = b0 / 2
        ax.plot([half, half], [i - 0.28, i + 0.28], color=INK, lw=1, ls=(0, (2, 2)))
        ax.annotate("", xy=(b1, i), xytext=(b0, i), arrowprops=dict(arrowstyle="-|>", color=HELD, lw=1.8))
        ax.plot(b0, i, "o", color=LIGHT, ms=7, zorder=3)
        ax.plot(b1, i, "o", color=HELD, ms=7, zorder=3)
        ax.text(1.28, i, f"{100 * th:.0f} %", va="center", ha="right", color=INK)
    ax.set_yticks(range(len(rows)), [r[0] for r in rows[::-1]], color=INK)
    ax.axvline(0, color=GREY, lw=0.8)
    ax.set_xlim(-1.0, 1.3)
    ax.text(1.28, len(rows) - 0.35, "explained", ha="right", color=GREY, fontsize=8)
    ax.set_xlabel("points of the party's share per 10 pp more flats in panel buildings")
    ax.grid(axis="y", visible=False)
    fig.tight_layout()
    fig.savefig(DIR / "07-attenuation.svg")
    plt.close(fig)


def steepening(e: dict) -> None:
    ys = e["H3"]["panel_slope_per10pp_by_year"]
    s5, s20 = e["H3_sensitivity"]["tol_5pct"]["by_year"], e["H3_sensitivity"]["tol_20pct"]["by_year"]
    yrs = [2017, 2021, 2025]
    fig, ax = plt.subplots(figsize=(8, 3.0))
    ax.fill_between(yrs, [s5[str(y)] for y in yrs], [s20[str(y)] for y in yrs], color=HELD, alpha=0.15, lw=0)
    ax.plot(yrs, [ys[str(y)] for y in yrs], color=HELD, lw=2.4, marker="o", ms=5)
    for y in yrs:
        ax.text(y, ys[str(y)] + 0.04, f"{ys[str(y)]:.2f}", ha="center", color=INK)
    ax.set_xticks(yrs)
    ax.set_xlim(2016, 2026)
    ax.set_ylim(0, 1.0)
    ax.set_ylabel("ANO points per 10 pp panel")
    ax.grid(axis="x", visible=False)
    fig.tight_layout()
    fig.savefig(DIR / "08-steepening.svg")
    plt.close(fig)


def metro(e: dict, r: dict) -> None:
    rows = [("grid clusters, 2025", e["H2"]["estimate"], *e["H2"]["ci90_used"]),
            ("precincts, 2025", r["precinct_level"]["metro"]["gamma"], *r["precinct_level"]["metro"]["ci90"]),
            ("grid clusters, 2021", r["H5_2021"]["metro"]["gamma"], *r["H5_2021"]["metro"]["ci90"]),
            ("spatial error model", r["spatial"]["sem_metro"],
             r["spatial"]["sem_metro"] - 1.645 * r["spatial"]["sem_se_metro"],
             r["spatial"]["sem_metro"] + 1.645 * r["spatial"]["sem_se_metro"])]
    fig, ax = plt.subplots(figsize=(8, 2.6))
    ax.axvspan(-0.25, 0.25, color=GRID, lw=0)
    ax.axvline(0, color=GREY, lw=0.8)
    for i, (lab, est, lo, hi) in enumerate(rows[::-1]):
        ax.plot([lo, hi], [i, i], color=HELD, lw=2)
        ax.plot(est, i, "o", color=HELD, ms=6)
    ax.set_yticks(range(len(rows)), [r_[0] for r_ in rows[::-1]], color=INK)
    ax.set_xlim(-0.6, 0.4)
    ax.text(0, len(rows) - 0.45, "± 0.25: too small to matter", ha="center", color=GREY, fontsize=8)
    ax.set_xlabel("ANO points per doubling of the distance to the metro, 90 % interval")
    ax.grid(axis="y", visible=False)
    fig.tight_layout()
    fig.savefig(DIR / "09-metro-equivalence.svg")
    plt.close(fig)


def spec_curve(r: dict) -> None:
    rows = sorted(r["robustness"]["14_specification_curve"]["rows"], key=lambda x: x["ANO_theta"])
    fig, ax = plt.subplots(figsize=(8, 2.8))
    for i, x in enumerate(rows):
        col = HELD if x["ANO"] == "place beyond composition" else LIGHT
        ax.plot(i, 100 * x["ANO_theta"], "o", color=col, ms=4.5)
    ax.axhline(50, color=INK, lw=1, ls=(0, (2, 2)))
    ax.text(len(rows) - 1, 52, "half", ha="right", color=INK, fontsize=8)
    ax.set_ylim(0, 60)
    ax.set_xticks([])
    ax.set_xlabel(f"{len(rows)} specifications, sorted")
    ax.set_ylabel("share explained (%)")
    ax.grid(axis="x", visible=False)
    fig.tight_layout()
    fig.savefig(DIR / "10-spec-curve.svg")
    plt.close(fig)


def main() -> None:
    e = json.loads((DIR / "rings_extended.json").read_text())
    r = json.loads((DIR / "rings_robust.json").read_text())
    attenuation(e, r)
    steepening(e)
    metro(e, r)
    spec_curve(r)
    print("wrote 07-attenuation.svg, 08-steepening.svg, 09-metro-equivalence.svg, 10-spec-curve.svg")


if __name__ == "__main__":
    main()
