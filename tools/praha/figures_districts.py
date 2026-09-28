"""Figures for part 3 (one city, 57 budgets), drawn onto paper; accent = the green the article's photograph holds.

Reads assets/praha/districts.json (tools/praha/districts.py); writes SVGs to assets/praha/.

Usage:
    uv run --with matplotlib python tools/praha/figures_districts.py
"""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[2]
DIR = ROOT / "assets" / "praha"
INK, GREY, LIGHT, GRID, HELD = "#111111", "#666666", "#b5b5b0", "#e6e6e3", "#3f6b2a"
BIG = 40000
plt.rcParams.update({
    "font.family": "monospace", "font.size": 9, "svg.fonttype": "none", "axes.edgecolor": GREY,
    "axes.labelcolor": GREY, "xtick.color": GREY, "ytick.color": GREY, "axes.spines.top": False,
    "axes.spines.right": False, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8,
    "axes.axisbelow": True, "figure.facecolor": "white", "axes.facecolor": "white",
})


def per_head_vs_size(d: list[dict]) -> None:
    """Spending per resident (2022-2024 mean) against population, every district."""
    fig, ax = plt.subplots(figsize=(8, 3.8))
    for r in d:
        big = r["population"] > BIG or r["district"] == "Praha 1"
        ax.scatter(r["population"], r["per_head"] / 1000, s=34 if big else 18,
                   color=HELD if big else LIGHT, edgecolor="white", linewidth=0.6, zorder=3)
    for name, dx, dy in [("Praha 1", 6, 0), ("Praha 4", -6, -1.6), ("Praha 2", 6, 0.8), ("Praha-Lysolaje", 6, 0)]:
        r = next(x for x in d if x["district"] == name)
        ax.annotate(name, (r["population"], r["per_head"] / 1000), xytext=(dx, dy * 6), textcoords="offset points",
                    color=INK, fontsize=8.5, ha="left" if dx > 0 else "right", va="center")
    ax.set_xscale("log")
    ax.set_xticks([500, 2000, 10000, 50000, 130000], ["500", "2 000", "10 000", "50 000", "130 000"])
    ax.minorticks_off()
    ax.set_xlabel("residents, end of 2024 (log scale)")
    ax.set_ylabel("spent per resident, CZK thousand")
    ax.set_ylim(0, 80)
    fig.tight_layout()
    fig.savefig(DIR / "03-per-head.svg")
    plt.close(fig)


def income_per_head(d: list[dict]) -> None:
    """Where each large district's money comes from, per resident; Praha 1 for comparison."""
    rows = sorted([r for r in d if r["population"] > BIG or r["district"] == "Praha 1"],
                  key=lambda r: r["income_per_head"]["income"])
    fig, ax = plt.subplots(figsize=(8, 4.4))
    for i, r in enumerate(rows):
        left = 0
        for key, col in [("taxes", INK), ("non_tax", LIGHT), ("transfers", HELD)]:
            v = r["income_per_head"][key] / 1000
            ax.barh(i, v, left=left, color=col, height=0.62, edgecolor="white", linewidth=0.8)
            left += v
    ax.set_yticks(range(len(rows)), [r["district"] for r in rows], color=INK)
    ax.set_xlabel("income per resident, CZK thousand, 2022-2024 mean")
    ax.grid(axis="y", visible=False)
    ax.text(0.99, 0.18, "taxes and local fees", transform=ax.transAxes, ha="right", color=INK)
    ax.text(0.99, 0.11, "fees, rents, other non-tax", transform=ax.transAxes, ha="right", color=GREY)
    ax.text(0.99, 0.04, "transfers (city, state)", transform=ax.transAxes, ha="right", color=HELD)
    fig.tight_layout()
    fig.savefig(DIR / "04-income.svg")
    plt.close(fig)


def main() -> None:
    d = json.loads((DIR / "districts.json").read_text())["districts"]
    per_head_vs_size(d)
    income_per_head(d)
    print("wrote 03-per-head.svg, 04-income.svg")


if __name__ == "__main__":
    main()
