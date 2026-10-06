"""Figures for part 4 (Prague, Vienna, Warsaw), drawn onto paper; accent = the blue the article's photograph holds.

Reads assets/praha/cities.json (tools/praha/cities.py); writes SVGs to assets/praha/.

Usage:
    uv run --with matplotlib python tools/praha/figures_cities.py
"""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[2]
DIR = ROOT / "assets" / "praha"
INK, GREY, LIGHT, GRID = "#111111", "#666666", "#b5b5b0", "#e6e6e3"
PAL = json.loads((Path(__file__).resolve().parents[2] / "assets" / "palette.json").read_text())  # entity colours, as the live charts
PRG, VIE, WAW = (PAL["entity"][c] for c in ("Prague", "Vienna", "Warsaw"))
plt.rcParams.update({
    "font.family": "monospace", "font.size": 9, "svg.fonttype": "none", "axes.edgecolor": GREY,
    "axes.labelcolor": GREY, "xtick.color": GREY, "ytick.color": GREY, "axes.spines.top": False,
    "axes.spines.right": False, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8,
    "axes.axisbelow": True, "figure.facecolor": "white", "axes.facecolor": "white",
})


def per_1000(c: dict) -> None:
    ys = c["years"]
    fig, ax = plt.subplots(figsize=(8, 3.6))
    for key, label, col, lw in [("warsaw", "Warsaw", WAW, 2), ("vienna", "Vienna (new buildings)", VIE, 1.8),
                                ("prague", "Prague", PRG, 2.4)]:
        vals = [c[key][str(y)]["per_1000"] for y in ys]
        ax.plot(ys, vals, color=col, lw=lw, marker="o", ms=3)
        ax.text(ys[-1] + 0.25, vals[-1], label, va="center", color=col if col != LIGHT else GREY)
    ax.set_xlim(ys[0] - 0.3, ys[-1] + 3.2)
    ax.set_ylim(0, 14)
    ax.set_xticks(ys[::2])
    ax.set_ylabel("dwellings completed per 1 000 residents")
    ax.grid(axis="x", visible=False)
    fig.tight_layout()
    fig.savefig(DIR / "05-completions.svg")
    plt.close(fig)


def builders(c: dict) -> None:
    v, w = c["builders_2024"]["vienna"], dict(c["builders_2024"]["warsaw"])
    wa = c["warsaw"]["2024"]  # the share from the counts (0.645 %), not the 4-decimal share that rounds to 0.7 %
    w["municipal_and_tbs_share"] = (wa["municipal"] + wa["tbs"]) / wa["completed"]
    rows = [("Vienna", [(v["non_profit_share"], "non-profit", INK), (v["public_share"], "public sector", GREY),
                        (v["companies_share"], "companies", LIGHT), (v["private_persons_share"], "private persons", GRID)]),
            ("Warsaw", [(w["municipal_and_tbs_share"], "municipal and TBS", INK),
                        (1 - w["municipal_and_tbs_share"], "everyone else", LIGHT)])]
    fig, ax = plt.subplots(figsize=(8, 2.2))
    for i, (city, parts) in enumerate(rows[::-1]):
        left = 0
        for share, label, col in parts:
            ax.barh(i, 100 * share, left=left, color=col, height=0.55, edgecolor="white", linewidth=1)
            if share > 0.08 or label in ("non-profit", "municipal and TBS"):
                ax.text(left + 100 * share / 2 if share > 0.08 else left + 100 * share + 1, i,
                        f"{100 * share:.1f} %" if share < 0.08 else f"{label}\n{100 * share:.0f} %",
                        va="center", ha="center" if share > 0.08 else "left", fontsize=8,
                        color="white" if col in (INK, GREY) and share > 0.08 else INK)
            left += 100 * share
    ax.set_yticks([0, 1], [r[0] for r in rows[::-1]], color=INK)
    ax.set_xlim(0, 100)
    ax.set_xlabel("dwellings completed in 2024, by builder (%)")
    ax.grid(axis="y", visible=False)
    fig.tight_layout()
    fig.savefig(DIR / "06-builders.svg")
    plt.close(fig)


def main() -> None:
    c = json.loads((DIR / "cities.json").read_text())
    per_1000(c)
    builders(c)
    print("wrote 05-completions.svg, 06-builders.svg")


if __name__ == "__main__":
    main()
