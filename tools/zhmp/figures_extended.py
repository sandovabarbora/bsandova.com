"""Figures for Part 1, the long version, drawn onto paper; accent = the red the Part 1 photograph holds.

Reads assets/zhmp/council_extended.json; writes SVGs to assets/zhmp/.

Usage:
    uv run --with matplotlib --with pandas python tools/zhmp/figures_extended.py
"""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DIR = ROOT / "assets" / "zhmp"
INK, GREY, LIGHT, GRID, HELD = "#111111", "#666666", "#b5b5b0", "#e6e6e3", "#a8201a"
plt.rcParams.update({
    "font.family": "monospace", "font.size": 9, "svg.fonttype": "none", "axes.edgecolor": GREY,
    "axes.labelcolor": GREY, "xtick.color": GREY, "ytick.color": GREY, "axes.spines.top": False,
    "axes.spines.right": False, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8,
    "axes.axisbelow": True, "figure.facecolor": "white", "axes.facecolor": "white",
})


def within(o: dict) -> None:
    pairs = o["H1"]["by_pair"]
    labs = {"2010->2014": "2010–14 → 2014–18", "2014->2018": "2014–18 → 2018–22", "2018->2022": "2018–22 → 2022–26"}
    fig, ax = plt.subplots(figsize=(8, 2.6))
    for i, (k, lab) in enumerate(labs.items()):
        p = pairs[k]
        lo, hi = np.exp(p["ci95"])
        ax.plot([lo, hi], [i, i], color=HELD, lw=2)
        ax.plot(np.exp(p["mean"]), i, "o", color=HELD, ms=7)
        ax.text(2.25, i, f"{p['n']} people", va="center", ha="right", color=GREY, fontsize=8)
    pooled = o["H1"]["ratio_per_term"]
    ax.axvline(pooled, color=INK, lw=1, ls=(0, (2, 2)))
    ax.text(pooled * 1.04, 2.6, f"all: × {pooled:.2f}", ha="left", color=INK, fontsize=8)
    ax.axvline(1, color=GREY, lw=0.8)
    ax.set_yticks(range(3), list(labs.values()), color=INK)
    ax.set_ylim(-0.5, 2.8)
    ax.set_xscale("log")
    ax.set_xticks([0.1, 0.25, 0.5, 1, 2], ["× 0.1", "× 0.25", "× 0.5", "× 1", "× 2"])
    ax.set_xlim(0.09, 2.3)
    ax.invert_yaxis()
    ax.set_xlabel("same councillor, votes against: next term vs this one (95 % interval)")
    ax.grid(axis="y", visible=False)
    fig.tight_layout()
    fig.savefig(DIR / "04-within.svg")
    plt.close(fig)


def roles(o: dict) -> None:
    r = pd.DataFrame(o["RQ5"])
    r = r[r.status != "interregnum"]
    lists = ["Praha sobě", "ANO", "TOP 09", "ODS", "ČSSD", "Piráti"]
    fig, ax = plt.subplots(figsize=(8, 3.2))
    for i, lst in enumerate(lists):
        g = r[r.list == lst]
        for st, col in [("coalition", HELD), ("opposition", LIGHT)]:
            h = g[g.status == st]
            if len(h):
                y = np.average(h.yes_share, weights=h.votes)
                ax.plot(100 * y, i, "o", color=col, ms=9, zorder=3)
        both = g.groupby("status").apply(lambda h: np.average(h.yes_share, weights=h.votes), include_groups=False)
        if {"coalition", "opposition"} <= set(both.index):
            ax.plot([100 * both["opposition"], 100 * both["coalition"]], [i, i], color=INK, lw=1, zorder=2)
    ax.set_yticks(range(len(lists)), lists, color=INK)
    ax.invert_yaxis()
    ax.set_xlim(40, 100)
    ax.set_xlabel("share of present members voting yes, % (red: while in the coalition; grey: in opposition)")
    ax.grid(axis="y", visible=False)
    fig.tight_layout()
    fig.savefig(DIR / "05-roles.svg")
    plt.close(fig)


def abstentions(o: dict) -> None:
    s = pd.DataFrame(o["H2"]["series"])
    s["t"] = pd.to_datetime(s.t)
    fig, ax = plt.subplots(figsize=(8, 3.0))
    ax.plot(s.t, 100 * s.share, "o", color=HELD, ms=3.5)
    for d in ["2014-11-01", "2018-11-01", "2022-11-01"]:
        ax.axvline(pd.Timestamp(d), color=GREY, lw=0.8, ls=(0, (2, 2)))
    ax.axvline(pd.Timestamp("2020-10-15"), color=INK, lw=0.8)
    ax.text(pd.Timestamp("2020-10-15"), 92, " file changes how\n it counts 'present'", fontsize=7, color=INK, va="top")
    ax.set_ylim(0, 100)
    ax.set_ylabel("abstentions, % of\nabstain + pressed nothing")
    ax.grid(axis="x", visible=False)
    fig.tight_layout()
    fig.savefig(DIR / "06-abstain-sittings.svg")
    plt.close(fig)


def minority(o: dict) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(8, 2.8), sharex=True)
    for ax, term, title in zip(axes, ["2018", "2022"], ["2018–22", "2022–26 (from Feb 2023)"]):
        top = o["H3_minority_clubs"][term]["top"][:5][::-1]
        labels = [t["clubs_not_yes"].replace("(no club; scattered)", "no club as a whole") for t in top]
        vals = [100 * t["share"] for t in top]
        cols = [LIGHT if "no club" in lab else HELD for lab in labels]
        ax.barh(range(len(top)), vals, color=cols, height=0.6)
        ax.set_yticks(range(len(top)), labels, color=INK, fontsize=8)
        ax.set_title(title, loc="left", fontsize=9, color=INK)
        ax.grid(axis="y", visible=False)
    axes[0].set_xlabel("% of contested votes")
    axes[1].set_xlabel("% of contested votes")
    fig.tight_layout()
    fig.savefig(DIR / "07-who-says-no.svg")
    plt.close(fig)


def main() -> None:
    o = json.loads((DIR / "council_extended.json").read_text())
    within(o)
    roles(o)
    abstentions(o)
    minority(o)
    print("wrote 04-within, 05-roles, 06-abstain-sittings, 07-who-says-no")


if __name__ == "__main__":
    main()
