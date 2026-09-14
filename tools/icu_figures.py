"""Recompute the ICU P/F-ratio figures from the CSVs, in the site palette. Run: .venv/bin/python tools/icu_figures.py <data_dir>"""
import sys, pathlib
import numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
from scipy import stats
D = pathlib.Path(sys.argv[1]); OUT = pathlib.Path(__file__).resolve().parent.parent / "assets/icu"; OUT.mkdir(exist_ok=True)
BG, FG, FG2, LINE, ACID, BUS, MINT, VIOLET = "#161616", "#DCDCD6", "#8A8A84", "#3A3A36", "#D6FF3A", "#FF6A3D", "#7ED9A6", "#B78CFF"
plt.rcParams.update({"figure.facecolor": BG, "axes.facecolor": BG, "savefig.facecolor": BG, "axes.edgecolor": LINE, "axes.labelcolor": FG2,
  "xtick.color": FG2, "ytick.color": FG2, "text.color": FG, "grid.color": LINE, "grid.alpha": .6, "axes.grid": True, "axes.spines.top": False,
  "axes.spines.right": False, "font.family": "monospace", "font.size": 9, "legend.frameon": False, "figure.constrained_layout.use": True, "svg.fonttype": "none"})
X = pd.read_csv(D / "P-F Ratio.csv"); y = pd.read_csv(D / "outcome.csv")["outcome"]
assert len(X) == len(y) == 622
# integrity: the imputed record (all fourteen values identical)
const = X.nunique(axis=1) == 1; print("constant rows:", list(X.index[const]))
X, y = X[~const].reset_index(drop=True), y[~const].reset_index(drop=True)
# winsorise at Tukey fences on the log scale, per column
L = np.log(X); lo = L.quantile(.25) - 1.5 * (L.quantile(.75) - L.quantile(.25)); hi = L.quantile(.75) + 1.5 * (L.quantile(.75) - L.quantile(.25))
capped = ((L < lo) | (L > hi)).sum().sum(); W = np.exp(L.clip(lo, hi, axis=1)); print("capped readings:", capped, "of", L.size, f"({capped/L.size*100:.2f} %)")
t = np.arange(14); labels = [f"D{i//2+1} {'AM' if i%2==0 else 'PM'}" for i in t]
imp, det = W[y == "Improving"], W[y == "Deteriorating"]
# fig 1: trajectories with 95 % CI
fig, ax = plt.subplots(figsize=(8, 4.4))
for g, col, name in ((imp, ACID, "Improving (n=311)"), (det, BUS, "Deteriorating (n=310)")):
    m = g.mean(); se = g.std(ddof=1) / np.sqrt(len(g)); ax.fill_between(t, m - 1.96*se, m + 1.96*se, color=col, alpha=.15, lw=0); ax.plot(t, m, color=col, lw=2, label=name)
ax.set_xticks(t); ax.set_xticklabels(labels, rotation=45, ha="right"); ax.set_ylabel("P/F ratio (kPa), mean ± 95 % CI"); ax.legend(loc="upper left")
fig.savefig(OUT / "01-trajectories.svg"); plt.close(fig)
# fig 2: Cohen's d by timepoint (equal-n pooled SD)
d = [(det[c].mean() - imp[c].mean()) / np.sqrt((det[c].var(ddof=1) + imp[c].var(ddof=1)) / 2) for c in W.columns]
print("d:", np.round(d, 2))
fig, ax = plt.subplots(figsize=(8, 3.6))
ax.bar(t, d, color=[ACID if v >= .8 else (MINT if v >= .5 else FG2) for v in d], width=.62)
for h, lab in ((.2, "small"), (.5, "medium"), (.8, "large")): ax.axhline(h, color=LINE, lw=1, ls=":"); ax.text(13.45, h + .015, lab, color=FG2, fontsize=8, ha="right")
ax.set_xticks(t); ax.set_xticklabels(labels, rotation=45, ha="right"); ax.set_ylabel("Cohen's d, Deteriorating − Improving")
fig.savefig(OUT / "02-effect-size.svg"); plt.close(fig)
# fig 3: label share by row-order bin
y0 = pd.read_csv(D / "outcome.csv")["outcome"]; bins = np.arange(0, len(y0) + 100, 100)
share = [ (y0[a:b] == "Deteriorating").mean() * 100 for a, b in zip(bins[:-1], bins[1:]) ]
fig, ax = plt.subplots(figsize=(8, 3.2))
ax.bar(range(len(share)), share, color=[BUS if s < 30 else FG2 for s in share], width=.7)
ax.axhline(50, color=LINE, lw=1, ls=":"); ax.set_xticks(range(len(share))); ax.set_xticklabels([f"{a}–{min(b, len(y0))-1}" for a, b in zip(bins[:-1], bins[1:])])
ax.set_ylabel("share labelled Deteriorating, %"); ax.set_xlabel("row position in outcome.csv")
fig.savefig(OUT / "03-row-order.svg"); plt.close(fig)
print("share by bin:", np.round(share, 1))
