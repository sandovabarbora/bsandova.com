"""Figures for texts/silent-detector.html from assets/detector/detector.json (written by
quaesitor/method/src/detector.py). Site palette; nothing typed.   .venv/bin/python tools/detector_figures.py"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
D = json.loads((ROOT / "assets/detector/detector.json").read_text())
OUT = ROOT / "assets/detector"
BG, FG, FG2, LINE = "#161616", "#DCDCD6", "#8A8A84", "#3A3A36"
ACID, BUS, MINT, VIOLET = "#D6FF3A", "#FF6A3D", "#7ED9A6", "#B78CFF"
plt.rcParams.update({
    "figure.facecolor": BG, "axes.facecolor": BG, "savefig.facecolor": BG,
    "axes.edgecolor": LINE, "axes.labelcolor": FG2, "xtick.color": FG2, "ytick.color": FG2,
    "text.color": FG, "grid.color": LINE, "grid.alpha": 0.6, "axes.grid": True,
    "axes.spines.top": False, "axes.spines.right": False,
    "font.family": "monospace", "font.size": 9, "legend.frameon": False,
    "figure.constrained_layout.use": False, "svg.fonttype": "none",
})
LABEL = {"agreement": "agreement across repeats", "sql": "shape of the SQL", "run": "model · pack · language", "all": "everything above"}


def fig1():
    names = ["agreement", "sql", "run", "all"]
    lg = [D["models"][f"{n}/logistic"]["auc"] for n in names]
    gb = [D["models"][f"{n}/gbm"]["auc"] for n in names]
    fig, a = plt.subplots(figsize=(10.5, 3.6))
    y = np.arange(len(names))
    a.barh(y - 0.18, lg, height=0.34, color=FG2, label="logistic regression")
    a.barh(y + 0.18, gb, height=0.34, color=ACID, label="gradient boosting")
    a.axvline(0.5, color=BUS, lw=1, ls=(0, (3, 2)))
    a.text(0.505, 3.62, "0.5 = coin flip", color=BUS, fontsize=8)
    a.axvline(D["baseline"]["auc"], color=VIOLET, lw=1, ls=(0, (1, 2)))
    a.text(D["baseline"]["auc"] + 0.005, 3.85, f"rule: repeats agree · {D['baseline']['auc']:.2f}", color=VIOLET, fontsize=8)
    for i, (l, g) in enumerate(zip(lg, gb)):
        a.text(l + 0.005, i - 0.18, f"{l:.2f}", va="center", color=FG2, fontsize=8)
        a.text(g + 0.005, i + 0.18, f"{g:.2f}", va="center", color=ACID, fontsize=8)
    a.set_yticks(y); a.set_yticklabels([LABEL[n] for n in names]); a.invert_yaxis()
    a.set_xlim(0.3, 1.0); a.set_xlabel("AUC, held-out questions (GroupKFold by question)")
    a.set_title(f"can run-time evidence tell a silently wrong number from a correct one?  {D['trained_on']:,} answers, {D['questions']} questions".replace(",", " "), loc="left", color=FG2)
    a.legend(loc="lower right", fontsize=8)
    fig.savefig(OUT / "01-auc.svg", bbox_inches="tight")


def fig2():
    tr = D["transfer_sql_gbm_auc"]; packs = list(tr)
    M = np.array([[tr[a][b] for b in packs] for a in packs])
    fig = plt.figure(figsize=(10.5, 4.0))
    a = fig.add_axes([0.14, 0.12, 0.34, 0.78])
    a.grid(False)
    im = a.imshow(M, cmap="Greys_r", vmin=0.0, vmax=1.0)
    for i in range(len(packs)):
        for j in range(len(packs)):
            a.text(j, i, f"{M[i, j]:.2f}", ha="center", va="center", color=ACID if M[i, j] >= 0.6 else (BUS if M[i, j] < 0.45 else FG), fontsize=11)
    a.set_xticks(range(len(packs))); a.set_xticklabels([f"tested on\n{p}" for p in packs])
    a.set_yticks(range(len(packs))); a.set_yticklabels([f"trained on\n{p}" for p in packs])
    a.set_title("SQL-shape model, AUC across warehouses", loc="left", color=FG2)
    fig.text(0.52, 0.72, "diagonal: held-out questions within the pack\noff-diagonal: trained on the row, scored on the column\n\nbelow 0.5 (orange): the learned pattern\npoints the wrong way on the other warehouse", color=FG2, fontsize=9, va="top")
    fig.savefig(OUT / "02-transfer.svg")


fig1(); fig2(); print("ok")
