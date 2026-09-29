"""Static SVG fallbacks for texts/lottery.html, drawn from assets/lottery/results.json and the CSVs beside it.

    uv run --with matplotlib --with pandas --with numpy python tools/lottery/figures.py

Writes assets/lottery/01-counts.svg ... 06-importance.svg. Site palette: ink, grey, and the held blue that
assets/charts.js uses for the interactive versions.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

sys.path.insert(0, str(Path(__file__).parent))
from common import A, RESULTS  # noqa: E402

R = json.loads(RESULTS.read_text())
INK, GREY, LIGHT, GRID, HELD = "#111111", "#666666", "#b5b5b0", "#e6e6e3", "#34507c"
plt.rcParams.update({
    "font.family": "monospace", "font.size": 9, "svg.fonttype": "none", "axes.edgecolor": GREY,
    "axes.labelcolor": GREY, "xtick.color": GREY, "ytick.color": GREY, "axes.spines.top": False,
    "axes.spines.right": False, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8,
    "axes.axisbelow": True, "figure.facecolor": "white", "axes.facecolor": "white",
})


def sp(v: float, dp: int = 0) -> str:
    return f"{v:,.{dp}f}".replace(",", " ").replace("-", "−")


def save(fig, name):
    fig.savefig(A / name, bbox_inches="tight")
    plt.close(fig)


def counts():
    F = R["fairness"]
    c = pd.read_csv(A / "sportka_counts.csv")
    lo, hi = F["per_number"]["band"]
    fig, ax = plt.subplots(figsize=(10, 3.4))
    ax.axhspan(lo, hi, color=LIGHT, alpha=0.35, lw=0)
    out = (c["count"] < lo) | (c["count"] > hi)
    ax.bar(c["number"], c["count"] - F["expected"], bottom=F["expected"], color=np.where(out, INK, HELD), width=0.7)
    ax.axhline(F["expected"], color=INK, lw=1)
    ax.set_xlim(0, 50)
    ax.set_ylim(820, 1010)
    ax.set_xticks([1, 5, 10, 15, 20, 25, 30, 35, 40, 45, 49])
    ax.set_xlabel("number")
    ax.set_title(f"times drawn, {sp(F['n_draws'])} draws 1994–2026 (expected {sp(F['expected'], 1)}; grey: 95 % range for one number)",
                 loc="left", color=GREY)
    save(fig, "01-counts.svg")


def hottest():
    F = R["fairness"]
    rows = [(f"Sportka {p['from']}–{p['to']}", p["hottest"], HELD) for p in F["periods"]]
    rows.append(("Sportka 1994–2026", F["hottest_overall"]["number"], HELD))
    rows += [(f"fair simulation, seed {s['seed']}", s["hottest"], GREY) for s in F["seeds"]]
    fig, ax = plt.subplots(figsize=(10, 3.2))
    for i, (lab, n, col) in enumerate(rows):
        ax.plot(n, i, "o", color=col, ms=8)
        ax.text(n + 0.8, i, str(n), va="center", color=col)
    ax.set_yticks(range(len(rows)), [r[0] for r in rows], color=INK)
    ax.invert_yaxis()
    ax.set_xlim(0, 50)
    ax.set_xlabel("most frequent number")
    ax.set_title("the most frequent number, by period and in four fair simulated histories", loc="left", color=GREY)
    save(fig, "02-hottest.svg")


def model():
    M = R["model"]["models"]
    lab = {"logistic": "logistic regression", "boosting": "gradient boosting"}
    fig, ax = plt.subplots(figsize=(10, 2.6))
    ys = 0
    ticks = []
    for k, m in M.items():
        ax.plot(m["auc_train"], ys, "D", color=LIGHT, mec=GREY, ms=7)
        ax.plot([m["auc_lo"], m["auc_hi"]], [ys + 0.35, ys + 0.35], color=HELD, lw=2.5)
        ax.plot(m["auc_test"], ys + 0.35, "o", color=HELD, ms=7)
        ax.text(m["auc_hi"] + 0.003, ys + 0.35, f"{m['auc_test']:.3f}", va="center", color=HELD)
        ax.text(m["auc_train"] + 0.003, ys, f"train {m['auc_train']:.3f}", va="center", color=GREY)
        ticks.append((ys + 0.17, lab[k]))
        ys += 1.2
    ax.axvline(0.5, color=INK, lw=1, ls=(0, (4, 3)))
    ax.set_yticks([t[0] for t in ticks], [t[1] for t in ticks], color=INK)
    ax.set_xlim(0.47, 0.6)
    ax.invert_yaxis()
    ax.set_xlabel("AUC (0.5 = no better than chance); blue: test with 95 % CI, bootstrap by drawing day; grey: training")
    save(fig, "03-model.svg")


def ppc():
    P = R["eurojackpot"]["ppc"]["bins"]
    fig, ax = plt.subplots(figsize=(10, 3.2))
    x = np.arange(len(P))
    for i, b in enumerate(P):
        ax.plot([i, i], [b["pred_lo"], b["pred_hi"]], color=LIGHT, lw=6, solid_capstyle="butt")
        ax.plot(i, b["pred_mean"], "_", color=GREY, ms=18, mew=2)
        ax.plot(i, b["observed"], "o", color=HELD, ms=8)
        ax.text(i + 0.12, b["observed"], f"{b['observed']} of {b['draws']}", va="center", color=HELD)
    ax.set_xticks(x, [f"€{b['bin']} M" for b in P])
    ax.set_ylabel("jackpot wins")
    ax.set_title("observed wins (blue) against the posterior predictive mean (grey bar) and 95 % interval, by jackpot",
                 loc="left", color=GREY)
    save(fig, "04-ppc.svg")


def ev():
    c = pd.read_csv(A / "ej_curves.csv")
    fig, ax = plt.subplots(figsize=(10, 3.4))
    j = c["jackpot_eur"] / 1e6
    ax.fill_between(j, c["ev_lo"], c["ev_hi"], color=HELD, alpha=0.18, lw=0)
    ax.plot(j, c["ev_mean"], color=HELD, lw=2)
    ax.plot(j, c["ev_lower_mean"], color=GREY, lw=1.2, ls=(0, (4, 3)))
    ax.axhline(2, color=INK, lw=1)
    ax.text(12, 1.93, "price of a column, €2", color=INK, va="top")
    ax.text(100, c["ev_lower_mean"].iloc[-1] + 0.05, "lower tiers only", color=GREY)
    ax.set_xlim(10, 120)
    ax.set_ylim(0, 2.1)
    ax.set_xlabel("jackpot, € million")
    ax.set_ylabel("expected payout, €")
    ax.set_title("expected payout of one €2 column by jackpot, posterior mean and 95 % credible band", loc="left", color=GREY)
    save(fig, "05-ev.svg")


def importance():
    I = R["importance"]
    E = I["estimators"]
    fig, ax = plt.subplots(figsize=(10, 3.2))
    for i, e in enumerate(E):
        col = GREY if e["name"].startswith("naive") else HELD
        ax.plot([e["lo"], e["hi"]], [i, i], color=col, lw=2.5)
        ax.plot(e["est"], i, "o", color=col, ms=7)
        ax.text(max(e["hi"], e["est"]) + 0.01, i, f"{e['jackpots']} jackpots", va="center", color=col, fontsize=8)
    ax.axvline(I["delta"], color=INK, lw=1, ls=(0, (4, 3)))
    ax.axvline(0, color=GREY, lw=0.8)
    ax.set_yticks(range(len(E)), [e["name"] for e in E], color=INK)
    ax.invert_yaxis()
    ax.set_xlim(-0.45, 0.55)
    ax.set_xlabel(f"estimated gain of the unpopular combination, € per column (dashed: exact, €{I['delta']:.3f}); 95 % CI")
    save(fig, "06-importance.svg")


for f in (counts, hottest, model, ppc, ev, importance):
    f()
print("ok")
