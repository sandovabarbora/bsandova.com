"""Static SVG fallbacks for texts/silent-detector.html from assets/detector/detector.json (written by
quaesitor/method/src/detector.py) and assets/detector/auc.json (tools/detector/auc.py, question-level bootstrap
95 % intervals). Site palette; nothing typed.   uv run --with matplotlib python tools/figures/detector_figures.py"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import sys  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "site"))
from paper_figures import recolour  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
D = json.loads((ROOT / "assets/detector/detector.json").read_text())
C = json.loads((ROOT / "assets/detector/auc.json").read_text())
OUT = ROOT / "assets/detector"
BG, FG, FG2, LINE = "#161616", "#DCDCD6", "#8A8A84", "#3A3A36"
ACID, BUS, VIOLET = "#D6FF3A", "#FF6A3D", "#B78CFF"
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
    err = lambda k: np.array([[C["models"][f"{n}/{k}"]["auc"] - C["models"][f"{n}/{k}"]["lo"] for n in names],
                              [C["models"][f"{n}/{k}"]["hi"] - C["models"][f"{n}/{k}"]["auc"] for n in names]])
    a.barh(y - 0.18, lg, height=0.34, color=FG2, label="logistic regression", xerr=err("logistic"), ecolor=FG, capsize=3)
    a.barh(y + 0.18, gb, height=0.34, color=ACID, label="gradient boosting", xerr=err("gbm"), ecolor=FG, capsize=3)
    a.axvline(0.5, color=BUS, lw=1, ls=(0, (3, 2)))
    a.text(0.505, 3.62, "0.5 = coin flip", color=BUS, fontsize=8)
    a.axvline(D["baseline"]["auc"], color=VIOLET, lw=1, ls=(0, (1, 2)))
    a.text(D["baseline"]["auc"] + 0.005, 3.85, f"rule: repeats agree · {D['baseline']['auc']:.2f}", color=VIOLET, fontsize=8)
    for i, (l, g) in enumerate(zip(lg, gb)):
        a.text(C["models"][f"{names[i]}/logistic"]["hi"] + 0.008, i - 0.18, f"{l:.2f}", va="center", color=FG2, fontsize=8)
        a.text(C["models"][f"{names[i]}/gbm"]["hi"] + 0.008, i + 0.18, f"{g:.2f}", va="center", color=ACID, fontsize=8)
    a.set_yticks(y); a.set_yticklabels([LABEL[n] for n in names]); a.invert_yaxis()
    a.set_xlim(0.3, 1.0); a.set_xlabel("AUC, held-out questions (GroupKFold by question)")
    a.set_title(f"can run-time evidence tell a silently wrong number from a correct one?  {D['trained_on']:,} answers, {D['questions']} questions".replace(",", " "), loc="left", color=FG2)
    a.legend(loc="lower right", fontsize=8)
    fig.savefig(OUT / "01-auc.svg", bbox_inches="tight")


def fig2():
    tr = C["transfer_sql_gbm"]; packs = list(tr)
    name = {"ecommerce": "e-commerce", "saas": "SaaS", "taxi": "taxi"}
    rows = [(a, b, tr[a][b]) for a in packs for b in packs]
    fig, a = plt.subplots(figsize=(10.5, 4.0))
    y = np.arange(len(rows))
    for i, (s_, d_, r) in enumerate(rows):
        c = FG2 if s_ == d_ else ACID
        a.plot([r["lo"], r["hi"]], [i, i], color=c, lw=2)
        a.plot(r["auc"], i, "o", color=c)
        a.text(r["hi"] + 0.01, i, f"{r['auc']:.2f}", va="center", color=c, fontsize=8)
    a.axvline(0.5, color=BUS, lw=1, ls=(0, (3, 2)))
    a.set_yticks(y); a.set_yticklabels([f"{name[s_]}, within pack" if s_ == d_ else f"{name[s_]} → {name[d_]}" for s_, d_, _ in rows])
    a.invert_yaxis(); a.set_xlim(0, 1.08)
    a.set_xlabel("AUC on the scored pack, 95 % CI by question bootstrap (grey: within the pack)")
    a.set_title("SQL-shape model, AUC across warehouses", loc="left", color=FG2)
    fig.savefig(OUT / "02-transfer.svg", bbox_inches="tight")


fig1(); fig2(); print("ok")

recolour("detector")  # on paper, the article's held colour as accent, as published
