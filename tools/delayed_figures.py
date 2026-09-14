"""Five days of Prague transit as the record hears them: surface delay per 5-minute bin, chorus where the smoothed delay exceeds 68 % of the day's maximum."""
import json, pathlib, numpy as np, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
R = pathlib.Path(__file__).resolve().parent.parent; OUT = R / "assets/delayed"; OUT.mkdir(exist_ok=True)
BG, FG, FG2, LINE, ACID, BUS, MINT, VIOLET = "#161616", "#DCDCD6", "#8A8A84", "#3A3A36", "#D6FF3A", "#FF6A3D", "#7ED9A6", "#B78CFF"
plt.rcParams.update({"figure.facecolor": BG, "axes.facecolor": BG, "savefig.facecolor": BG, "axes.edgecolor": LINE, "axes.labelcolor": FG2,
  "xtick.color": FG2, "ytick.color": FG2, "text.color": FG, "grid.color": LINE, "grid.alpha": .5, "axes.grid": True, "axes.spines.top": False,
  "axes.spines.right": False, "font.family": "monospace", "font.size": 8, "legend.frameon": False, "figure.constrained_layout.use": True, "svg.fonttype": "none"})
D = json.load(open(R / "tools/data/sonification_days.json"))
surf = ["autobus", "tramvaj", "trolejbus"]
def series(day):
    m = day["modes"]; n = np.array([sum(m[s]["n"][i] for s in surf) for i in range(288)], float)
    w = np.array([sum(m[s]["n"][i] * m[s]["delay"][i] for s in surf) for i in range(288)], float)
    d = np.where(n > 0, w / np.maximum(n, 1), 0.0)
    k = np.ones(5) / 5; sm = np.convolve(d, k, mode="same")  # light smoothing, as the player does before the chorus test
    return d, sm, n
order = ["easter", "summer", "school", "typical", "meltdown"]
days = sorted(D["days"], key=lambda d: order.index(next((o for o in order if o in d["id"]), "typical")) if any(o in d["id"] for o in order) else 9)
fig, axes = plt.subplots(len(days), 1, figsize=(8, 1.7 * len(days)), sharex=True)
t = np.arange(288) / 12
rows = []
for ax, day in zip(axes, days):
    d, sm, n = series(day); thr = .68 * sm.max(); chorus = sm > thr
    ax.fill_between(t, 0, d, where=chorus, color=BUS, alpha=.35, lw=0, step=None)
    ax.plot(t, d, color=FG, lw=1); ax.axhline(thr, color=LINE, lw=1, ls=":")
    key = day.get("key") or ""
    ax.text(0.2, d.max() * .92, f"{day['label']} · {day['disc']} · {int(day['total']):,} events".replace(",", " "), fontsize=8, color=FG, va="top")
    ax.set_ylabel("s late"); ax.set_xlim(0, 24)
    rows.append((day["label"], day["disc"], int(day["total"]), round(float(np.average(d, weights=np.maximum(n, 1))), 0), int(chorus.sum()) * 5))
axes[-1].set_xticks(range(0, 25, 3)); axes[-1].set_xlabel("hour of day · orange = chorus (smoothed delay above 68 % of the day's maximum)")
fig.savefig(OUT / "01-five-days.svg"); plt.close(fig)
for r in rows: print(r)
