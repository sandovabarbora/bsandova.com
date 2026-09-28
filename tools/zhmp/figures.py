"""Figures for the council series, drawn straight onto paper: ink, grey, and the red the article's photograph holds.

Reads assets/zhmp/votes2022.json and terms.json (tools/zhmp/votes.py, terms.py); writes SVGs to assets/zhmp/.

Usage:
    uv run --with matplotlib python tools/zhmp/figures.py
"""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[2]
DIR = ROOT / "assets" / "zhmp"
INK, GREY, LIGHT, GRID, HELD = "#111111", "#666666", "#b5b5b0", "#e6e6e3", "#a8201a"
COALITION = {"SPOLU", "Piráti", "STAN"}
plt.rcParams.update(
    {
        "font.family": "monospace",
        "font.size": 9,
        "svg.fonttype": "none",
        "axes.edgecolor": GREY,
        "axes.labelcolor": GREY,
        "xtick.color": GREY,
        "ytick.color": INK,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "grid.color": GRID,
        "grid.linewidth": 0.8,
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "axes.axisbelow": True,
    }
)


def agreement_bars(v: dict) -> None:
    """How often each club takes the same side as SPOLU, the mayor's club."""
    rows = sorted(((c, a) for c, a in v["agreement"]["SPOLU"].items() if c != "SPOLU"), key=lambda r: r[1])
    fig, ax = plt.subplots(figsize=(8, 3.2))
    for i, (c, a) in enumerate(rows):
        col = INK if c in COALITION else (HELD if c == "Praha sobě" else LIGHT)
        ax.barh(i, 100 * a, color=col, height=0.62)
        ax.text(100 * a + 1, i, f"{100 * a:.0f} %", va="center", color=INK)
    ax.set_yticks(range(len(rows)), [f"{c}{' (coalition)' if c in COALITION else ''}" for c, _ in rows])
    ax.set_xlim(0, 108)
    ax.set_xticks([0, 25, 50, 75, 100])
    ax.grid(axis="y", visible=False)
    ax.set_xlabel("votes on which the club took the same side as SPOLU (%)")
    fig.tight_layout()
    fig.savefig(DIR / "01-with-spolu.svg")
    plt.close(fig)


def quarters(v: dict) -> None:
    """The three opposition clubs and the non-affiliated member against SPOLU, quarter by quarter."""
    q = {k: x for k, x in v["agreement_with_spolu_by_quarter"].items() if k >= "2023Q1"}
    xs = list(q)
    fig, ax = plt.subplots(figsize=(8, 3.4))
    for c, col, lw in [("Praha sobě", HELD, 2.2), ("ANO", INK, 1.6), ("SPD", LIGHT, 1.6)]:
        ys = [100 * q[k][c] for k in xs]
        ax.plot(range(len(xs)), ys, color=col, lw=lw)
        ax.text(len(xs) - 0.8, ys[-1], c, va="center", color=col if col != LIGHT else GREY)
    ax.set_xticks(range(0, len(xs), 2), [xs[i] for i in range(0, len(xs), 2)])
    ax.set_xlim(-0.3, len(xs) + 1.2)
    ax.set_ylim(0, 105)
    ax.set_ylabel("same side as SPOLU (%)")
    ax.grid(axis="x", visible=False)
    fig.tight_layout()
    fig.savefig(DIR / "02-opposition-by-quarter.svg")
    plt.close(fig)


def terms(t: dict) -> None:
    """How present members who did not vote yes recorded it, per 100 present, on passed votes, four terms."""
    names = list(t)
    panels = [
        ("against", "against_per_100_present", HELD),
        ("abstained", "abstain_per_100_present", INK),
        ("pressed nothing", "no_vote_per_100_present", LIGHT),
    ]
    fig, axes = plt.subplots(1, 3, figsize=(8, 2.9), sharey=False)
    for ax, (label, key, col) in zip(axes, panels):
        ys = [t[n]["passed"][key] for n in names]
        ax.bar(range(len(names)), ys, color=col, width=0.62)
        for i, y in enumerate(ys):
            ax.text(i, y, f"{y:.1f}", ha="center", va="bottom", color=INK, fontsize=8)
        ax.set_xticks(range(len(names)), [n[2:4] + "–" + n[7:9] for n in names])
        ax.set_title(label, loc="left", color=INK, fontsize=9)
        ax.set_ylim(0, max(ys) * 1.25)
        ax.grid(axis="x", visible=False)
    axes[0].set_ylabel("per 100 members present")
    fig.tight_layout()
    fig.savefig(DIR / "03-dissent-by-term.svg")
    plt.close(fig)


def main() -> None:
    v = json.loads((DIR / "votes2022.json").read_text())
    agreement_bars(v)
    quarters(v)
    terms(json.loads((DIR / "terms.json").read_text()))
    print("wrote", ", ".join(p.name for p in sorted(DIR.glob("*.svg"))))


if __name__ == "__main__":
    main()
